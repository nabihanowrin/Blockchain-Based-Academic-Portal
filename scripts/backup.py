"""
Nightly backup: a full copy of the live database, saved to Google Drive.

Run by GitHub every night (.github/workflows/backup.yml). It:
  1. asks Postgres (Supabase) for a full copy with pg_dump (every table: records,
     the chain, accounts, uploaded files),
  2. checks the copy can be read back,
  3. uploads it to the folder "EEE Records backups" in the project Google Drive
     (the job makes the folder itself the first time),
  4. deletes copies older than 30 days, always keeping at least the newest 7.

Settings (GitHub -> Settings -> Secrets and variables -> Actions):
  BACKUP_DATABASE_URL   the same as DATABASE_URL on Render
  GDRIVE_CLIENT_ID      the same as GMAIL_CLIENT_ID
  GDRIVE_CLIENT_SECRET  the same as GMAIL_CLIENT_SECRET
  GDRIVE_REFRESH_TOKEN  from the OAuth Playground, scope drive.file

drive.file means this job can only see and touch files it created itself.

To put a backup back (on a computer with PostgreSQL's tools):
  pg_restore --clean --if-exists --no-owner --dbname "<database address>" <file>.dump
If it complains about "transaction_timeout", ignore that one line: newer tools
add that setting and an older database skips it. Then run the chain check.
"""

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

FOLDER = "EEE Records backups"
KEEP_DAYS = 30
KEEP_AT_LEAST = 7
TOKEN_URL = os.environ.get("GDRIVE_TOKEN_URL", "https://oauth2.googleapis.com/token")
API = os.environ.get("GDRIVE_API", "https://www.googleapis.com")      # changed only by the tests
SETTINGS = ("BACKUP_DATABASE_URL", "GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN")


def say(text):
    print(text, flush=True)


# ------------------------------------------------------------------
# 1-2. the copy of the database
# ------------------------------------------------------------------
def dump_database(url, folder):
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=6))).strftime("%Y-%m-%d_%H%M")
    path = os.path.join(folder, f"eee-records_{stamp}_BD.dump")
    # custom format: compressed, and pg_restore can put back all or part of it
    done = subprocess.run(["pg_dump", "--dbname", url, "--format=custom", "--no-owner",
                           "--no-privileges", "--file", path], capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit("pg_dump failed:\n" + done.stderr.replace(url, "<database address>")[-2000:])
    listing = subprocess.run(["pg_restore", "--list", path], capture_output=True, text=True)
    tables = sum(1 for line in listing.stdout.splitlines() if " TABLE DATA " in line)
    if listing.returncode != 0 or tables == 0:
        raise SystemExit("The copy could not be read back, so it was not uploaded.")
    say(f"Copied the database: {tables} tables, {os.path.getsize(path) / 1e6:.2f} MB.")
    return path


# ------------------------------------------------------------------
# 3-4. Google Drive
# ------------------------------------------------------------------
def access_token():
    form = urllib.parse.urlencode({
        "client_id": os.environ["GDRIVE_CLIENT_ID"],
        "client_secret": os.environ["GDRIVE_CLIENT_SECRET"],
        "refresh_token": os.environ["GDRIVE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=form), timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        hint = (" The Drive refresh token has expired or was revoked: make a new one in the "
                "OAuth Playground (scope drive.file) and update GDRIVE_REFRESH_TOKEN.") \
            if "invalid_grant" in detail else ""
        raise SystemExit(f"Google refused the Drive sign-in (HTTP {e.code}).{hint}")


def drive(token, method, path, body=None, data=None, headers=None):
    h = {"Authorization": "Bearer " + token, **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json; charset=UTF-8"
    req = urllib.request.Request(API + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
            return (json.loads(raw) if raw else {}), r.headers
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Google Drive said no to {method} {path.split('?')[0]} "
                         f"(HTTP {e.code}): {e.read().decode('utf-8', 'replace')[:300]}")


def query(**parts):
    """Builds the part after ? in an address, with every space and quote made safe."""
    return urllib.parse.urlencode(parts, quote_via=urllib.parse.quote)


def backup_folder(token):
    found, _ = drive(token, "GET", "/drive/v3/files?" + query(
        q=f"name = '{FOLDER}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        fields="files(id)", spaces="drive"))
    if found.get("files"):
        return found["files"][0]["id"]
    made, _ = drive(token, "POST", "/drive/v3/files?fields=id",
                    body={"name": FOLDER, "mimeType": "application/vnd.google-apps.folder"})
    say(f'Made the folder "{FOLDER}" in the Drive.')
    return made["id"]


def upload(token, folder_id, path):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    # resumable upload: first say what is coming, then send the bytes
    _, headers = drive(token, "POST", "/upload/drive/v3/files?uploadType=resumable&fields=id",
                       body={"name": name, "parents": [folder_id]},
                       headers={"X-Upload-Content-Type": "application/octet-stream",
                                "X-Upload-Content-Length": str(size)})
    where = headers["Location"]
    with open(path, "rb") as f:
        req = urllib.request.Request(where, data=f.read(), method="PUT",
                                     headers={"Content-Type": "application/octet-stream"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            uploaded = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"The upload failed (HTTP {e.code}).")
    say(f"Uploaded {name} to the Drive.")
    return uploaded["id"]


def tidy(token, folder_id):
    found, _ = drive(token, "GET", "/drive/v3/files?" + query(
        q=f"'{folder_id}' in parents and trashed = false", orderBy="createdTime desc",
        fields="files(id,name,createdTime)", pageSize=1000))
    files = found.get("files", [])
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=KEEP_DAYS)
    removed = 0
    for f in files[KEEP_AT_LEAST:]:                      # never touch the newest 7
        made = dt.datetime.fromisoformat(f["createdTime"].replace("Z", "+00:00"))
        if made < cutoff:
            drive(token, "DELETE", f"/drive/v3/files/{f['id']}")
            removed += 1
    say(f"The folder now holds {len(files) - removed} backups ({removed} older than {KEEP_DAYS} days removed).")


def main():
    have = [n for n in SETTINGS if os.environ.get(n, "").strip()]
    if not have:
        say("Backups aren't set up yet (no secrets in GitHub). Nothing to do.")
        return
    missing = [n for n in SETTINGS if n not in have]
    if missing:
        raise SystemExit("Some backup secrets are missing in GitHub: " + ", ".join(missing))
    with tempfile.TemporaryDirectory() as folder:
        path = dump_database(os.environ["BACKUP_DATABASE_URL"], folder)
        token = access_token()
        folder_id = backup_folder(token)
        upload(token, folder_id, path)
        tidy(token, folder_id)
    say("Backup done.")


if __name__ == "__main__":
    sys.exit(main())
