"""
A teacher's weekly schedule, shown on the teacher's home page.

Two parts:
1. Real classes from the published routine (the `timetable` table, which is
   the 5th-semester routine for session 2023–24). A teacher sees every routine
   slot for a course they have an approved class in, for that session.
2. Sample classes for other semesters (table `teacher_schedule`), because only
   one semester's routine is in the prototype. They are marked "sample" on the
   page. The demo teacher (sabrina.demo) gets a few, so her week shows what a
   real one would look like: classes with the 3rd, 5th and 7th semesters.

Days: 6 = Sunday, 0 = Monday … 3 = Thursday (the department's week).
"""

import db
from ledger import connect

ROUTINE_SEMESTER = 5           # the routine in the `timetable` table
ROUTINE_SESSION = "2023–24"    # the batch that is in 5th semester now
DAYS = {6: "Sunday", 0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday"}
WEEK_ORDER = [6, 0, 1, 2, 3]

# a mock week for the demo teacher, in slots that don't clash with her
# 5th-semester classes (EEE 513, EEE 514 in the routine)
SAMPLE = [
    # teacher_id, weekday, start, finish, code, semester, session, room
    ("teacher:sabrina.demo", 6, "09:00", "09:45", "EEE 313", 3, "2024–25", "R-210"),
    ("teacher:sabrina.demo", 6, "14:00", "16:30", "EEE 314", 3, "2024–25", "Lab-2"),
    ("teacher:sabrina.demo", 0, "09:00", "09:45", "EEE 711", 7, "2022–23", "R-310"),
    ("teacher:sabrina.demo", 0, "11:30", "12:15", "EEE 313", 3, "2024–25", "R-210"),
    ("teacher:sabrina.demo", 1, "09:45", "10:30", "EEE 313", 3, "2024–25", "R-210"),
    ("teacher:sabrina.demo", 1, "14:00", "16:30", "EEE 712", 7, "2022–23", "DSP Lab"),
    ("teacher:sabrina.demo", 2, "11:30", "12:15", "EEE 711", 7, "2022–23", "R-310"),
    ("teacher:sabrina.demo", 3, "09:45", "10:30", "EEE 711", 7, "2022–23", "R-310"),
    ("teacher:sabrina.demo", 3, "11:30", "12:15", "EEE 313", 3, "2024–25", "R-210"),
]


def init():
    con = connect()
    con.execute("""CREATE TABLE IF NOT EXISTS teacher_schedule (
        teacher_id TEXT, weekday INTEGER, start TEXT, finish TEXT,
        code TEXT, semester INTEGER, session TEXT, room TEXT)""")
    con.commit()
    have = con.execute("SELECT COUNT(*) FROM teacher_schedule WHERE teacher_id=?",
                       ("teacher:sabrina.demo",)).fetchall()[0][0]
    if not have:
        for row in SAMPLE:
            con.execute("INSERT INTO teacher_schedule VALUES (?,?,?,?,?,?,?,?)", row)
        con.commit()
    con.close()
    if hasattr(db, "forget_tables"):
        db.forget_tables()


def _is_lab(start, finish, code):
    """Labs are the long afternoon/three-hour slots; lab course codes end in an even number."""
    long_slot = int(finish[:2]) - int(start[:2]) >= 2
    return long_slot or int(code.split()[-1]) % 2 == 0


def week(teacher_id, classes):
    """Every class this teacher has in a week, in day and time order.
    `classes` are the teacher's approved classes (code, title, session, semester)."""
    con = connect()
    titles = dict(con.execute("SELECT code, title FROM courses").fetchall())
    out = []

    # 1. real slots from the routine
    mine = {c["code"] for c in classes
            if c["session"] == ROUTINE_SESSION and c["semester"] == ROUTINE_SEMESTER}
    for weekday, start, finish, codes, is_ct, room in con.execute(
            "SELECT weekday, start, finish, codes, is_ct, room FROM timetable").fetchall():
        for code in codes.split("|"):
            if code in mine:
                out.append({"weekday": weekday, "day": DAYS.get(weekday, ""), "start": start,
                            "finish": finish, "code": code, "title": titles.get(code, ""),
                            "semester": ROUTINE_SEMESTER, "session": ROUTINE_SESSION,
                            "room": room, "ct": bool(is_ct),
                            "lab": _is_lab(start, finish, code), "sample": False})

    # 2. sample classes for the other semesters
    for weekday, start, finish, code, semester, session, room in con.execute(
            "SELECT weekday, start, finish, code, semester, session, room FROM teacher_schedule "
            "WHERE teacher_id=?", (teacher_id,)).fetchall():
        out.append({"weekday": weekday, "day": DAYS.get(weekday, ""), "start": start,
                    "finish": finish, "code": code, "title": titles.get(code, ""),
                    "semester": semester, "session": session, "room": room, "ct": False,
                    "lab": _is_lab(start, finish, code), "sample": True})
    con.close()

    out.sort(key=lambda c: (WEEK_ORDER.index(c["weekday"]) if c["weekday"] in WEEK_ORDER else 9,
                            c["start"]))
    return out
