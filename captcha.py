"""
"Not a robot" check for creating an account (students and staff).

The page asks for a small sum, like "What is 7 + 5?". The answer never goes to the
browser: the page only gets a signed ticket that holds the answer's fingerprint and
an expiry time. When the form is sent, the server checks the answer against the
ticket. Each ticket works once and lasts 10 minutes.

No outside service and no account are needed. It stops simple bots from filling the
form again and again (which would also flood people's inboxes with codes).
"""
import hashlib
import hmac
import os
import random
import threading
import time

from contract import Refused

LIFE = 600                                   # seconds a ticket stays valid
_KEY = (os.environ.get("CAPTCHA_SECRET") or "").encode() or os.urandom(32)
_used = {}                                   # ticket -> expiry, so each ticket works once
_lock = threading.Lock()


def _sign(answer, until, salt):
    msg = f"{answer}|{until}|{salt}".encode()
    return hmac.new(_KEY, msg, hashlib.sha256).hexdigest()


def new():
    """A fresh question and its ticket."""
    a, b = random.randint(2, 9), random.randint(2, 9)
    if random.random() < .5:
        question, answer = f"{a} + {b}", a + b
    else:
        a, b = max(a, b) + 5, min(a, b)
        question, answer = f"{a} − {b}", a - b
    until = int(time.time()) + LIFE
    salt = os.urandom(6).hex()
    return {"question": f"What is {question}?", "ticket": f"{until}.{salt}.{_sign(answer, until, salt)}"}


def check(ticket, answer):
    """Raises Refused unless the answer matches the ticket (and the ticket is fresh and unused)."""
    try:
        until_s, salt, sig = str(ticket or "").split(".")
        until = int(until_s)
        given = int(str(answer).strip())
    except (ValueError, TypeError):
        raise Refused("Please answer the 'not a robot' question.")
    now = int(time.time())
    # every try uses the ticket up, right or wrong, so guessing means asking for a new question each time
    with _lock:
        for t, exp in list(_used.items()):   # forget old tickets
            if exp < now:
                del _used[t]
        if ticket in _used:
            raise Refused("That 'not a robot' question was already used. Answer the new one.")
        _used[ticket] = until
    if until < now:
        raise Refused("The 'not a robot' question timed out. Answer the new one.")
    if not hmac.compare_digest(sig, _sign(given, until, salt)):
        raise Refused("That answer to the 'not a robot' question isn't right. Try the new one.")
