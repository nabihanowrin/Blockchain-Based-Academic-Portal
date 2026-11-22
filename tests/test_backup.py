"""
The nightly backup (scripts/backup.py), tested against a stand-in for Google
Drive and a real, empty Postgres database. Runs only where TEST_DATABASE_URL
and PostgreSQL's tools are available (the "postgres" job on GitHub).

It checks: the copy is made, the folder is created once, the file is uploaded,
copies older than 30 days are removed while the newest 7 always stay, and the
uploaded copy can be put back into an empty database with the chain still valid.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAKE_DRIVE = 'import json, sys, uuid, datetime as dt\nfrom http.server import BaseHTTPRequestHandler, HTTPServer\nfrom urllib.parse import urlparse, parse_qs\nFILES = {}   # id -> {name, parents, mime, createdTime, size}\nold = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=40)).isoformat() + "Z"\nclass H(BaseHTTPRequestHandler):\n    def log_message(self,*a): pass\n    def send(self, code, body=None, headers=None):\n        raw = json.dumps(body).encode() if body is not None else b""\n        self.send_response(code)\n        for k,v in (headers or {}).items(): self.send_header(k,v)\n        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)\n    def body(self):\n        n=int(self.headers.get("Content-Length",0)); return self.rfile.read(n)\n    def do_POST(self):\n        u=urlparse(self.path); q=parse_qs(u.query)\n        if u.path=="/token":\n            f=parse_qs(self.body().decode()); assert f["grant_type"]==["refresh_token"]\n            return self.send(200, {"access_token":"fake-access","expires_in":3600})\n        assert self.headers["Authorization"]=="Bearer fake-access"\n        if u.path=="/drive/v3/files":\n            meta=json.loads(self.body()); i=uuid.uuid4().hex\n            FILES[i]={**meta,"createdTime":dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()+"Z"}\n            if meta["name"]=="EEE Records backups":   # pretend 9 very old backups exist, to test tidying\n                for k in range(9): FILES[uuid.uuid4().hex]={"name":f"old{k}.dump","parents":[i],"createdTime":old}\n            return self.send(200, {"id":i})\n        if u.path=="/upload/drive/v3/files" and q.get("uploadType")==["resumable"]:\n            meta=json.loads(self.body()); sid=uuid.uuid4().hex; FILES["pending-"+sid]=meta\n            return self.send(200, None, {"Location": f"http://127.0.0.1:{PORT}/up/{sid}"})\n    def do_PUT(self):\n        sid=self.path.rsplit("/",1)[1]; data=self.body(); meta=FILES.pop("pending-"+sid); i=uuid.uuid4().hex\n        FILES[i]={**meta,"size":len(data),"createdTime":dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()+"Z"}\n        open(sys.argv[2],"wb").write(data)\n        return self.send(200, {"id":i})\n    def do_GET(self):\n        u=urlparse(self.path); q=parse_qs(u.query)["q"][0]\n        if "mimeType" in q:\n            res=[{"id":i} for i,f in FILES.items() if f.get("mimeType")=="application/vnd.google-apps.folder"]\n        else:\n            pid=q.split("\'")[1]\n            res=sorted([{"id":i,"name":f["name"],"createdTime":f["createdTime"]} for i,f in FILES.items() if pid in f.get("parents",[])], key=lambda x:x["createdTime"], reverse=True)\n        return self.send(200, {"files":res})\n    def do_DELETE(self):\n        FILES.pop(self.path.rsplit("/",1)[1]); return self.send(204)\nPORT=int(sys.argv[1]); HTTPServer(("127.0.0.1",PORT),H).serve_forever()\n'


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL") and shutil.which("pg_dump") and shutil.which("pg_restore"),
                     "needs TEST_DATABASE_URL and PostgreSQL's tools")
class TestBackup(unittest.TestCase):

    def test_backup_upload_and_restore(self):
        """A nightly copy reaches 'Drive', old copies are tidied, and the copy restores with a valid chain."""
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        work = tempfile.mkdtemp(prefix="eee-backup-")
        fake = os.path.join(work, "fake_drive.py")
        uploaded = os.path.join(work, "uploaded.dump")
        with open(fake, "w") as f:
            f.write(FAKE_DRIVE)
        drive = subprocess.Popen([sys.executable, "-W", "ignore", fake, str(port), uploaded])
        try:
            time.sleep(1)
            url = os.environ["TEST_DATABASE_URL"]
            # the database needs at least one table: build it with the site's own setup
            subprocess.run([sys.executable, "-c", "import server; server.prepare_database()"],
                           cwd=ROOT, env={**os.environ, "DATABASE_URL": url}, check=True,
                           capture_output=True)
            env = {**os.environ, "BACKUP_DATABASE_URL": url, "GDRIVE_CLIENT_ID": "x",
                   "GDRIVE_CLIENT_SECRET": "y", "GDRIVE_REFRESH_TOKEN": "z",
                   "GDRIVE_API": f"http://127.0.0.1:{port}", "GDRIVE_TOKEN_URL": f"http://127.0.0.1:{port}/token"}
            run = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "backup.py")],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("Made the folder", run.stdout)
            self.assertIn("Uploaded", run.stdout)
            self.assertIn("now holds 7 backups", run.stdout, "old copies weren't tidied, or too many were")
            self.assertTrue(os.path.getsize(uploaded) > 0)

            # put it back into a brand-new database and check the chain there
            parts = urllib.parse.urlsplit(url)
            fresh = urllib.parse.urlunsplit(parts._replace(path="/eee_restore_check"))
            admin = urllib.parse.urlunsplit(parts._replace(path="/postgres"))
            subprocess.run(["psql", admin, "-c", "DROP DATABASE IF EXISTS eee_restore_check"], capture_output=True)
            subprocess.run(["psql", admin, "-c", "CREATE DATABASE eee_restore_check"], check=True, capture_output=True)
            restored = subprocess.run(["pg_restore", "--no-owner", "--dbname", fresh, uploaded],
                                      capture_output=True, text=True)
            self.assertEqual(restored.returncode, 0, restored.stderr[-1500:])
            check = subprocess.run([sys.executable, "-c", "from ledger import verify_chain; print(verify_chain()[0])"],
                                   cwd=ROOT, env={**os.environ, "DATABASE_URL": fresh}, capture_output=True, text=True)
            self.assertEqual(check.stdout.strip(), "True", "the restored copy's chain isn't valid: " + check.stderr[-800:])
        finally:
            drive.terminate()
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
