"""
The student's assistant: a chat box on the student page, answered by an AI
through its API: Google's Gemini first, Groq as the backup.

How one message travels:
  student types  ->  our server (/api/assistant): checks who is asking, adds THAT
  student's own timetable, courses and class-test dates  ->  the AI  ->  answer
  ->  back to the chat box.

The backup chain (free AIs are sometimes busy, so we never rely on just one):
  1. Gemini, the main model (AI_MODEL). If Google says "busy", ask it once more.
  2. Gemini's lighter model (AI_BACKUP_MODEL), same key.
  3. Groq, a different company (GROQ_API_KEY, GROQ_MODEL).
Each one gets a short wait (AI_WAIT_SECONDS). The first real answer wins. Only if
all of them fail does the student see "busy, try again in a minute".

What the AI is given:
  - about the student: first name, semester, lab group, this semester's courses
    and teachers, the weekly routine and upcoming class tests;
  - about the department (public information, the same for everyone): who to
    contact for what, the faculty with emails and official profile links, how
    fees are paid, the complaint box, how the website works, alumni stories.
What it is NOT given: marks, GPA, attendance, parents' names, anyone else's data.
(Free AI tiers may use what they are sent to improve their products, so nothing
more personal than a timetable goes to them.)

It can only talk. It can't change any record.

Settings (Render -> Environment):
  GEMINI_API_KEY     from Google AI Studio.
  GROQ_API_KEY       from console.groq.com (the backup company).
                     With neither key the assistant says it is off.
  AI_MODEL           the main Gemini model (default below)
  AI_BACKUP_MODEL    Gemini's lighter backup model (default below)
  GROQ_MODEL         which Groq model (default below)
  AI_WAIT_SECONDS    how long to wait for each AI before trying the next (default 15)
  AI_DAILY_LIMIT     messages per student per day (default 30), so the free quota lasts
"""

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request

import clock
from contract import Refused
from ledger import connect

MODEL = os.environ.get("AI_MODEL", "gemini-3.8-flash").strip()
BACKUP_MODEL = os.environ.get("AI_BACKUP_MODEL", "gemini-3.1-flash-lite").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip()
WAIT = float(os.environ.get("AI_WAIT_SECONDS") or 15)
DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT") or 30)
MAX_MESSAGE = 800          # characters in one question
MAX_TURNS = 8              # earlier messages sent along, so it remembers the conversation
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

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


def _key(name):
    return os.environ.get(name, "").strip()


def enabled():
    return bool(_key("GEMINI_API_KEY") or _key("GROQ_API_KEY")) or os.environ.get("AI_FAKE") == "1"


def init():
    con = connect()
    con.execute("CREATE TABLE IF NOT EXISTS assistant_usage (roll TEXT, day TEXT, count INTEGER, "
                "PRIMARY KEY (roll, day))")
    con.commit()
    con.close()


def _used_today(roll):
    """How many questions this student has had answered today; refuses past the daily limit."""
    day = clock.today().isoformat()
    con = connect()
    row = con.execute("SELECT count FROM assistant_usage WHERE roll=? AND day=?", (roll, day)).fetchone()
    con.close()
    used = row[0] if row else 0
    if used >= DAILY_LIMIT:
        raise Refused(f"You've used today's {DAILY_LIMIT} questions. The assistant is back tomorrow.")
    return used


def _count_one(roll, used):
    """Adds one to today's count. Called only AFTER an answer, so a failed try costs nothing."""
    con = connect()
    con.execute("INSERT OR REPLACE INTO assistant_usage VALUES (?,?,?)",
                (roll, clock.today().isoformat(), used + 1))
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
    used = _used_today(roll)
    context = about_student(name, view) + "\n\n" + about_department()

    if os.environ.get("AI_FAKE") == "1":           # the automatic tests: no real AI is called
        text = f"(test assistant) You asked: {message}\n\nWhat I was told:\n{context}"
    else:
        text = ask_ai(RULES + "\n\n" + context, _clean_history(history), message)
    return {"text": text, "left_today": _count_one(roll, used)}


class Busy(Exception):
    """One AI couldn't answer (busy, slow, broken). The chain moves on to the next."""


def _post(url, body, headers):
    """Sends one request and returns the JSON answer. Any failure becomes Busy, with a log line."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=WAIT) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = " ".join(e.read().decode("utf-8", "replace").split())[:200]
        raise Busy(f"HTTP {e.code}: {detail}", e.code)
    except Exception as e:                       # timed out, connection dropped, unreadable answer
        raise Busy(f"{type(e).__name__}: {e}", None)


def _gemini(model, system, history, message):
    answer = _post(os.environ.get("AI_GEMINI_URL", GEMINI_URL).format(model=model), {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": history + [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {"maxOutputTokens": 700, "temperature": 0.4},
    }, {"x-goog-api-key": _key("GEMINI_API_KEY")})
    parts = (((answer.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    return "".join(p.get("text", "") for p in parts).strip()


def _groq(system, history, message):
    # Groq speaks the "chat completions" format: a list of {role, content}.
    # Gemini calls the AI's turns "model"; here they are "assistant".
    messages = [{"role": "system", "content": system}]
    for turn in history:
        messages.append({"role": "assistant" if turn["role"] == "model" else "user",
                         "content": turn["parts"][0]["text"]})
    messages.append({"role": "user", "content": message})
    answer = _post(os.environ.get("AI_GROQ_URL", GROQ_URL), {
        "model": GROQ_MODEL, "messages": messages, "temperature": 0.4,
        "max_completion_tokens": 1500,          # room for its thinking AND the answer
        "reasoning_effort": "low", "reasoning_format": "hidden",   # don't show its thinking
    }, {"Authorization": "Bearer " + _key("GROQ_API_KEY")})
    return (((answer.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def _chain():
    """The AIs to try, in order, as (name, function). Only the ones with a key."""
    tries = []
    if _key("GEMINI_API_KEY"):
        main = lambda s, h, m: _gemini(MODEL, s, h, m)
        tries += [(f"Gemini {MODEL}", main), (f"Gemini {MODEL} (again)", main)]
        if BACKUP_MODEL and BACKUP_MODEL != MODEL:
            tries.append((f"Gemini {BACKUP_MODEL}", lambda s, h, m: _gemini(BACKUP_MODEL, s, h, m)))
    if _key("GROQ_API_KEY"):
        tries.append((f"Groq {GROQ_MODEL}", _groq))
    return tries


def ask_ai(system, history, message):
    """Tries each AI in turn; returns the first real answer. Raises Refused if none answer."""
    try_again = False
    for name, call in _chain():
        if name.endswith("(again)"):
            # ask the main model a second time ONLY if it said "busy" quickly (503/429);
            # after a timeout, waiting again would only keep the student waiting longer
            if not try_again:
                continue
            time.sleep(1)
        try:
            text = call(system, history, message)
        except Busy as e:
            detail, code = e.args
            print(f"  [assistant] {name} failed: {detail}", flush=True)
            try_again = name == f"Gemini {MODEL}" and code in (429, 500, 503)
            continue
        try_again = False
        if text:
            return text
        print(f"  [assistant] {name} gave an empty answer", flush=True)
    raise Refused("The assistant is busy right now. Please try again in a minute.")
