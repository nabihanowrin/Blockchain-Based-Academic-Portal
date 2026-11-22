"""
The student's assistant: a chat box on the student page, answered by Google's
Gemini AI through its API.

How one message travels:
  student types  ->  our server (/api/assistant): checks who is asking, adds THAT
  student's own timetable, courses and class-test dates  ->  Gemini  ->  answer
  ->  back to the chat box.

What the AI is given: the student's first name, semester, lab group, this
semester's courses and teachers, the weekly routine and upcoming class tests.
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

RULES = """You are the study assistant inside EEE Records, the academic records website of the
Department of Electrical and Electronic Engineering, University of Chittagong.
You are talking to one student. Below is THEIR information: their courses, weekly
routine and upcoming class tests (CTs). Today's date is given too.

- Help with their schedule: what's on today or tomorrow, when the next CT is, which
  room, how to plan their week. Use only the information below for facts about
  their classes; if something isn't there, say you don't have it.
- You can also explain study topics from their courses in simple words.
- You can't see marks, GPA or attendance; for those, point them to the course page.
- You can't change anything on the website.
- Keep answers short and plain. Use the student's language (English or Bangla).
- Never make up dates, rooms or teachers."""


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
    context = about_student(name, view)

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
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  [assistant] could not reach Gemini: {e}", flush=True)
        raise Refused("The assistant couldn't be reached just now. Please try again later.")

    parts = (((answer.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise Refused("The assistant didn't have an answer for that. Try asking another way.")
    return {"text": text, "left_today": left}
