"""
The department's own fees, paid at the department office (not at Sonali Bank):
the Development Fund and the EEE Somitee Fund.

The office types each amount once on its "Department fees" page. The same
amount then holds for every semester, shows on each student's Payment page,
and is printed on the money receipt form the student takes to the office.

Every change is a block on the chain: who changed it, when, old -> new.
"""

import datetime as dt

from ledger import connect, add_entry
from contract import Refused

# key -> how it is named on screen and on the receipt
FUNDS = {"development": "Development Fund",
         "somitee": "EEE Somitee Fund"}
MAX_AMOUNT = 100000            # Tk; anything above this is surely a typo


# starting amounts, used once if the office hasn't set that fee yet (the office's own
# amount always wins, and a starting amount is never put back once it has been changed)
START = {"development": 750}


def init():
    con = connect()
    con.execute("""CREATE TABLE IF NOT EXISTS dept_fees (
        fund TEXT PRIMARY KEY, amount INTEGER, changed_at TEXT, changed_by TEXT)""")
    con.commit()
    missing = [f for f in START
               if not con.execute("SELECT 1 FROM dept_fees WHERE fund=?", (f,)).fetchone()]
    con.close()
    for fund in missing:
        set_amount("seed", fund, START[fund])


def amounts():
    """{fund: amount or None} for every fund."""
    con = connect()
    found = dict(con.execute("SELECT fund, amount FROM dept_fees").fetchall())
    con.close()
    return {k: found.get(k) for k in FUNDS}


def overview():
    con = connect()
    found = {f: (a, at, by) for f, a, at, by in
             con.execute("SELECT fund, amount, changed_at, changed_by FROM dept_fees").fetchall()}
    con.close()
    return {"funds": [{"key": k, "label": label,
                       "amount": found.get(k, (None,))[0],
                       "changed_at": found.get(k, (None, None))[1],
                       "changed_by": found.get(k, (None, None, None))[2]}
                      for k, label in FUNDS.items()]}


def set_amount(who, fund, amount):
    if fund not in FUNDS:
        raise Refused("No such fee.")
    try:
        amount = int(str(amount).strip().replace(",", ""))
    except ValueError:
        raise Refused("Type the amount as a number of taka, like 700.")
    if amount < 0 or amount > MAX_AMOUNT:
        raise Refused(f"The amount must be between 0 and {MAX_AMOUNT:,} taka.")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    con = connect()
    old = con.execute("SELECT amount FROM dept_fees WHERE fund=?", (fund,)).fetchone()
    if old:
        con.execute("UPDATE dept_fees SET amount=?, changed_at=?, changed_by=? WHERE fund=?",
                    (amount, now, who, fund))
    else:
        con.execute("INSERT INTO dept_fees (fund, amount, changed_at, changed_by) VALUES (?, ?, ?, ?)",
                    (fund, amount, now, who))
    con.commit()
    con.close()
    block_no, _ = add_entry("dept_fee_set", {"fund": fund, "old": old[0] if old else None, "new": amount},
                            f"office:{who}")
    return block_no
