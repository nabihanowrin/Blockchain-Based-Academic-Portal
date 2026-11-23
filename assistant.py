"""
The student's assistant: a chat box on the student page, answered by Google's
Gemini AI through its API.

How one message travels:
  student types  ->  our server (/api/assistant): checks who is asking, adds THAT
  student's own timetable, courses and class-test dates  ->  Gemini  ->  answer
  ->  back to the chat box.

What the AI is given:
  - about the student: first name, semester, lab group, this semester's courses
    and teachers, the weekly routine and upcoming class tests;
  - about the department (public information, the same for everyone): who to
    contact for what, the faculty with emails and official profile links, how
    fees are paid, the complaint box, how the website works, alumni stories.
What it is NOT given: marks, GPA, attendance, parents' names, anyone else's data.
(Gemini's free tier may use what it is sent to improve Google's products, so
nothing more personal than a timetable goes there.)

It can only talk. It can't change any record.

Settings (Render -> Environment):
  GEMINI_API_KEY     from Google AI Studio. Without it the assistant says it is off.
  AI_MODEL           which Gemini model (default below)
  AI_DAILY_LIMIT     messages per student per day (default 30), so the free quota lasts
"""

import datetime as dt
import json
import os
import urllib.error
import urllib.request

import clock
from contract import Refused
from ledger import connect

MODEL = os.environ.get("AI_MODEL", "gemini-3.8-flash").strip()
DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT") or 30)
MAX_MESSAGE = 800          # characters in one question
MAX_TURNS = 8              # earlier messages sent along, so it remembers the conversation
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

RULES = """You are the assistant inside EEE Records, the academic records website of the
Department of Electrical and Electronic Engineering, University of Chittagong.
You are talking to one student. Below is THEIR schedule (courses, weekly routine,
upcoming class tests) and the DEPARTMENT's public information. Today's date is given.

What you help with:
- Their day and week: what's on today or tomorrow, rooms, labs, the next class
  test, planning study time around classes.
- Procedures: how to pay a fee, where to go, who to contact or email about a
  problem, how to use this website.
- Research and contacts: which teachers to approach for a thesis or project, and
  which alumni work in a field the student is interested in.

Rules:
- Use ONLY the information below for facts: names, emails, rooms, dates, fees,
  links. If something isn't there, say you don't have it and say where they could
  find out (e.g. the teacher's official profile link, the department office).
  Never invent an email, a phone number, a research interest or an alumni contact.
- Teachers' research interests are not in your information unless listed. If asked
  which teacher fits a topic, say that, and give the teachers' official profile
  links so the student can check their research, rather than guessing.
- For alumni, share only what is listed (name, role, field, batch, link).
- You are not a tutor. If asked to teach course content, answer in one or two
  lines at most and suggest the course teacher or the course's Resources tab.
- You can't see marks, GPA or attendance (point them to the course page) and you
  can't change anything on the website.
- Keep answers short and plain. Use the student's language (English or Bangla)."""


def enabled():
    return bool(os.environ.get("GEMINI_API_KEY", "").strip()) or os.environ.get("AI_FAKE") == "1"


def init():
    con = connect()
    con.execute("CREATE TABLE IF NOT EXISTS assistant_usage (roll TEXT, day TEXT, count INTEGER, "
                "PRIMARY KEY (roll, day))")
    con.commit()
    con.close()


def _count_today(roll):
    """Adds one to today's count for this student; refuses past the daily limit."""
    day = clock.today().isoformat()
    con = connect()
    row = con.execute("SELECT count FROM assistant_usage WHERE roll=? AND day=?", (roll, day)).fetchone()
    used = row[0] if row else 0
    if used >= DAILY_LIMIT:
        con.close()
        raise Refused(f"You've used today's {DAILY_LIMIT} questions. The assistant is back tomorrow.")
    con.execute("INSERT OR REPLACE INTO assistant_usage VALUES (?,?,?)", (roll, day, used + 1))
    con.commit()
    con.close()
    return DAILY_LIMIT - used - 1


def about_student(name, view):
    """The student's own schedule, as plain text for the AI. view = server.semester_view(roll)."""
    now = clock.now()
    current = view["semester"]
    sem = next((s for s in view["semesters"] if s["n"] == current), None)
    lines = [f"Today: {now.strftime('%A %d %B %Y')}, {now.strftime('%H:%M')} (Bangladesh time).",
             f"Student's first name: {(name or '').split(' ')[0]}.",
             f"Semester: {current}. Lab group: {view.get('group') or 'unknown'}."]
    codes = set()
    if sem:
        lines.append("This semester's courses:")
        for c in sem["courses"]:
            codes.add(c["code"])
            if c.get("lab"):
                codes.add(c["lab"])
            lab = f" (with lab {c['lab']})" if c.get("lab") else ""
            teacher = f", teacher: {c['teacher']}" if c.get("teacher") else ""
            lines.append(f"- {c['code']}: {c['title']}{lab}{teacher}")
    if current == view.get("routine_semester") and view.get("timetable"):
        lines.append("Weekly routine (Sunday to Thursday):")
        for t in view["timetable"]:
            kind = " (class test)" if t.get("ct") else ""
            lines.append(f"- {t['day']} {t['start']}-{t['finish']}: {' / '.join(t['codes'])}{kind}, room {t['room']}")
    else:
        lines.append("Weekly routine: not published on the website for this semester.")
    upcoming = [c for c in view.get("cts", [])
                if c["code"] in codes and c["date"] >= clock.today().isoformat()]
    if upcoming:
        lines.append("Upcoming class tests:")
        for c in upcoming[:15]:
            lines.append(f"- {c['date']}: {c['code']} {c['label']}")
    else:
        lines.append("Upcoming class tests: none listed.")
    return "\n".join(lines)


def about_department():
    """The department's public information, the same for every student."""
    import faculty
    lines = ["DEPARTMENT (public information):",
             f"Department: {faculty.CONTACT['address']}.",
             f"Department phone: {faculty.CONTACT['phone']}. Department website: {faculty.CONTACT['website']}.",
             f"Chairman: {faculty.CHAIRMAN}, email {faculty.CONTACT['email']}."]
    try:
        import site_settings
        office = site_settings.address("office")
        if office:
            lines.append(f"Academic office email (for records, accounts, tamper alerts): {office}.")
    except Exception:
        pass

    lines.append("Faculty (name, designation, email, official profile with their research):")
    for t in faculty.listing():
        leave = " (on study leave)" if t["on_leave"] else ""
        profile = f", profile {t['profile']}" if t["profile"] else ""
        lines.append(f"- {t['name']}, {t['designation']}{leave}, {t['email']}{profile}")

    lines += [
        "Paying fees:",
        "- Semester final exam fee: paid online through Sonali Bank, link "
        "https://billpay.sonalibank.com.bd/cufee . The amount for each semester is on the student's Payment page.",
        "- Department fees (Development Fund, EEE Somitee Fund): paid at the department office, not the bank. "
        "The amounts are on the Payment page, which also prints the money receipt form to take to the office.",
        "Problems with department facilities (rooms, fans, lights, toilets, labs): use the Complaint box in the "
        "sidebar. It goes to the chairman and the office without the student's name. It is not for complaints "
        "about teachers.",
        "A mark looks wrong: open the course, open the mark's history, and choose 'No, I want to raise this'. "
        "The teacher answers there.",
        "Account: forgot password -> 'Forgot password' on the sign-in page (a code is emailed). "
        "Delete account -> bottom of the Home page; marks stay with the department.",
    ]
    try:
        import alumni
        people = alumni.listing()
    except Exception:
        people = []
    if people:
        lines.append("Alumni (former students; share only what is listed):")
        for a in people[:40]:
            bits = [a["name"], a["headline"], a["batch"]]
            field = f" [field: {a['field']}]" if a["field"] else ""
            link = f", link {a['link']}" if a["link"] else ""
            lines.append("- " + ", ".join(b for b in bits if b) + field + link)
    return "\n".join(lines)


def _clean_history(history):
    out = []
    for turn in (history or [])[-MAX_TURNS:]:
        role = turn.get("role")
        text = str(turn.get("text") or "")[:1500]
        if role in ("user", "model") and text.strip():
            out.append({"role": role, "parts": [{"text": text}]})
    return out


def reply(roll, name, view, message, history=None):
    """One answer from the assistant. Raises Refused with a message the student can read."""
    message = (message or "").strip()
    if not message:
        raise Refused("Type a question first.")
    if len(message) > MAX_MESSAGE:
        raise Refused(f"Please keep a question under {MAX_MESSAGE} characters.")
    if not enabled():
        raise Refused("The assistant isn't switched on yet.")
    left = _count_today(roll)
    context = about_student(name, view) + "\n\n" + about_department()

    if os.environ.get("AI_FAKE") == "1":           # the automatic tests: no real AI is called
        return {"text": f"(test assistant) You asked: {message}\n\nWhat I was told:\n{context}",
                "left_today": left}

    body = {
        "system_instruction": {"parts": [{"text": RULES + "\n\n" + context}]},
        "contents": _clean_history(history) + [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {"maxOutputTokens": 700, "temperature": 0.4},
    }
    req = urllib.request.Request(API.format(model=MODEL), data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "x-goog-api-key": os.environ["GEMINI_API_KEY"].strip()})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            answer = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        print(f"  [assistant] Gemini said HTTP {e.code}: {detail}", flush=True)
        if e.code == 429:
            raise Refused("The assistant is busy right now (the free limit for this minute or day is used up). "
                          "Please try again a little later.")
        raise Refused("The assistant couldn't answer just now. Please try again later.")
    except Exception as e:
        # anything else on the way to Google and back: the connection dropped, timed
        # out, or the answer wasn't readable. Log it for us; tell the student plainly.
        print(f"  [assistant] could not get an answer from Gemini: {type(e).__name__}: {e}", flush=True)
        raise Refused(f"The assistant couldn't be reached just now ({type(e).__name__}). Please try again later.")

    parts = (((answer.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise Refused("The assistant didn't have an answer for that. Try asking another way.")
    return {"text": text, "left_today": left}
