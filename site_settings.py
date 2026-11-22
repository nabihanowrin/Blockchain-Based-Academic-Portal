"""
Where the site's own emails go: the office and the chairman.

The office can change these from its "Email settings" page, so nobody has to
open Render (or whatever server the site runs on) when an address changes.

- Each address is either set on the website, or taken from the server's
  starting value (OFFICE_EMAIL / CHAIRMAN_EMAIL), or not set at all.
  The website's own setting always wins.
- A change only takes effect after a code sent to the NEW address is typed
  in, so a typo can't send complaints into nowhere.
- The OLD address is told about the change, so a wrong change gets noticed.
- Every change is a block on the chain: who changed it, when, old -> new.
"""

import datetime as dt
import hashlib
import hmac
import os
import re
import secrets

from ledger import connect, add_entry
from contract import Refused

# setting -> (server starting value, how it is named on screen)
KEYS = {"office": ("OFFICE_EMAIL", "the office"),
        "chairman": ("CHAIRMAN_EMAIL", "the chairman")}
CODE_MINUTES = 15
MAX_TRIES = 5
LOOKS_LIKE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def init():
    con = connect()
    con.execute("""CREATE TABLE IF NOT EXISTS email_settings (
        setting TEXT PRIMARY KEY, address TEXT, changed_at TEXT, changed_by TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS email_settings_pending (
        setting TEXT PRIMARY KEY, address TEXT, code_hash TEXT, expires TEXT,
        tries INTEGER, asked_by TEXT)""")
    con.commit()
    con.close()


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _hash(code):
    return hashlib.sha256((code or "").strip().encode()).hexdigest()


def _check_key(key):
    if key not in KEYS:
        raise Refused("No such email setting.")


def current(key):
    """(address, where it comes from): 'website', 'server' or 'none'."""
    _check_key(key)
    try:
        con = connect()
        row = con.execute("SELECT address FROM email_settings WHERE setting=?", (key,)).fetchone()
        con.close()
    except Exception:          # table not made yet (e.g. a script run before the server)
        row = None
    if row and row[0]:
        return row[0], "website"
    start = (os.environ.get(KEYS[key][0]) or "").strip().lower()
    return (start, "server") if start else (None, "none")


def address(key):
    """The address to email right now, or None."""
    return current(key)[0]


def overview():
    """What the office's Email settings page shows."""
    out = []
    for key, (_, label) in KEYS.items():
        addr, source = current(key)
        con = connect()
        waiting = con.execute("SELECT address, expires FROM email_settings_pending WHERE setting=?",
                              (key,)).fetchone()
        con.close()
        out.append({"key": key, "label": label, "address": addr, "source": source,
                    "waiting_for": waiting[0] if waiting and waiting[1] > _now().isoformat() else None})
    return {"settings": out, "history": history()}


def history():
    import json
    con = connect()
    rows = con.execute("SELECT block_no, payload, actor, created_at FROM blocks "
                       "WHERE entry_type='email_setting_changed' ORDER BY block_no DESC").fetchall()
    con.close()
    out = []
    for block_no, text, actor, at in rows:
        p = json.loads(text)
        out.append({"block_no": block_no, "key": p.get("setting"),
                    "label": KEYS.get(p.get("setting"), ("", p.get("setting")))[1],
                    "old": p.get("old"), "new": p.get("new"), "by": actor, "at": at})
    return out


def start_change(office_email, key, new):
    """Step 1: send a code to the new address. The code is never shown on screen."""
    _check_key(key)
    new = (new or "").strip().lower()
    if not LOOKS_LIKE_EMAIL.match(new):
        raise Refused("That doesn't look like an email address.")
    if new == address(key):
        raise Refused(f"That is already the address for {KEYS[key][1]}.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = (_now() + dt.timedelta(minutes=CODE_MINUTES)).isoformat()
    con = connect()
    con.execute("INSERT OR REPLACE INTO email_settings_pending VALUES (?,?,?,?,?,?)",
                (key, new, _hash(code), expires, 0, office_email))
    con.commit()
    con.close()

    import mailer
    status, _ = mailer.send(new, "Confirm this address for EEE Records",
                            f"Someone at the EEE office ({office_email}) asked for emails to "
                            f"{KEYS[key][1]} to come to this address.\n\n"
                            f"Your code is {code}\n\nIt works for {CODE_MINUTES} minutes. "
                            "If you didn't expect this, ignore it and nothing changes.",
                            trusted=True)
    if status != "sent":
        _forget(key)
        print(f"  [settings] code for the {key} address could not be emailed ({status})", flush=True)
        raise Refused("We couldn't email a code to that address right now. "
                      "Check the address, or try again in a few minutes.")
    return status


def finish_change(office_email, key, code):
    """Step 2: the code from the new inbox. Saves it, records it, warns the old address."""
    _check_key(key)
    con = connect()
    row = con.execute("SELECT address, code_hash, expires, tries FROM email_settings_pending "
                      "WHERE setting=?", (key,)).fetchone()
    con.close()
    if not row:
        raise Refused("Start again: no code was sent for this setting.")
    new, code_hash, expires, tries = row
    if expires < _now().isoformat():
        _forget(key)
        raise Refused("That code has expired. Start again for a new one.")
    if not hmac.compare_digest(_hash(code), code_hash):
        tries += 1
        if tries >= MAX_TRIES:
            _forget(key)
            raise Refused("Too many wrong codes. Start again for a new one.")
        con = connect()
        con.execute("UPDATE email_settings_pending SET tries=? WHERE setting=?", (tries, key))
        con.commit()
        con.close()
        left = MAX_TRIES - tries
        raise Refused(f"Wrong code. {left} tr{'ies' if left != 1 else 'y'} left.")

    old = address(key)
    block_no, _ = add_entry("email_setting_changed",
                            {"setting": key, "old": old, "new": new}, f"office:{office_email}")
    con = connect()
    con.execute("INSERT OR REPLACE INTO email_settings VALUES (?,?,?,?)",
                (key, new, _now().isoformat(), office_email))
    con.commit()
    con.close()
    _forget(key)

    # tell the old address, and the chairman, so a wrong change gets noticed
    import mailer
    note = (f"Emails to {KEYS[key][1]} from EEE Records now go to {new} instead of "
            f"{old or '(no address)'}.\nChanged by {office_email}. The change is recorded on the "
            f"chain (block #{block_no}).\n\nIf this is wrong, the office can change it back "
            "on its Email settings page.")
    for to in {old, address("chairman") if key == "office" else None} - {None, new}:
        mailer.send_later(to, f"EEE Records: the address for {KEYS[key][1]} was changed", note,
                          trusted=True)
    return block_no


def _forget(key):
    con = connect()
    con.execute("DELETE FROM email_settings_pending WHERE setting=?", (key,))
    con.commit()
    con.close()
