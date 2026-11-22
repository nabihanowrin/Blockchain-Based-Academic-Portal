"""
The site's automatic check-up.

What it does, in order:
  1. Copies the project into a throwaway folder, so the real database is never touched.
  2. Starts the website there (SQLite, no email, nothing secret needed).
  3. Makes its own test teacher and test office accounts with random passwords.
  4. Acts like real people: registers a student, the teacher asks for a class,
     the office approves it, marks go in and get corrected, the student objects,
     the chain gets checked, an insider edit gets caught, and so on.
  5. After every step, checks the answer is what it should be.

If any check fails, the whole run fails. On GitHub that shows as a red cross,
and Render (set to "After CI Checks Pass") will not put that version live.

Run it yourself:   python -m unittest discover -s tests -v
Against Postgres:  set TEST_DATABASE_URL to an EMPTY test database first
                   (never the real Supabase one).

The rule: every bug we find gets its own test here, so it can never come back.
"""

import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDENT_ROLL = "99999001"               # a roll number no real student has
STUDENT_EMAIL = STUDENT_ROLL + "@std.cu.ac.bd"


def free_port():
    """Ask the computer for a port nobody is using."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Site:
    """A tiny browser: sends a request, gives back (status code, answer)."""

    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}"

    def call(self, path, body=None, token=None, extra=None):
        headers = {"Content-Type": "application/json", **(extra or {})}
        if token:
            headers["Authorization"] = "Bearer " + token
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, self._read(resp)
        except urllib.error.HTTPError as e:
            return e.code, self._read(e)

    @staticmethod
    def _read(resp):
        raw = resp.read()
        try:
            return json.loads(raw)
        except ValueError:
            return raw.decode("utf-8", "replace")


class TestSite(unittest.TestCase):
    """The tests run in name order (test_01, test_02 ...) and share what they make."""

    # ------------------------------------------------------------------
    # start and stop the throwaway website
    # ------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.mkdtemp(prefix="eee-test-")
        shutil.copytree(ROOT, cls.folder, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "records.db", "uploads",
                                                      "__pycache__", "tests"))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("DATABASE_URL", "GMAIL_", "MAIL_", "OFFICE_EMAIL", "CHAIRMAN_EMAIL"))}
        port = free_port()
        cls.outbox = os.path.join(cls.folder, "outbox.jsonl")
        env.update({"PORT": str(port), "DEMO_TAMPER": "1",
                    "MAIL_OUTBOX": cls.outbox,      # emails go to this file, nothing is sent
                    "MAIL_ALLOW_ALL": "1",
                    "PEER_KEY": secrets.token_urlsafe(16),
                    "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"})
        if os.environ.get("TEST_DATABASE_URL"):      # an empty Postgres, like Supabase
            env["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
        cls.env = env
        cls.log = open(os.path.join(cls.folder, "server-test.log"), "w")
        cls.server = subprocess.Popen([sys.executable, "server.py"], cwd=cls.folder, env=env,
                                      stdout=cls.log, stderr=subprocess.STDOUT)
        cls.site = Site(port)

        # wait until the site answers (or give up after 90 seconds)
        for _ in range(180):
            if cls.server.poll() is not None:
                raise RuntimeError("The server stopped while starting.\n" + cls.server_log())
            try:
                if cls.site.call("/api/landing")[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("The server never answered.\n" + cls.server_log())

        # test staff accounts, with passwords made up fresh for this run
        cls.passwords = {"teacher": secrets.token_urlsafe(12), "office": secrets.token_urlsafe(12),
                         "student": secrets.token_urlsafe(12)}
        cls.emails = {"teacher": "ci.teacher@cu.ac.bd", "office": "ci.office@cu.ac.bd"}
        make = ("import auth, sys\n"
                "auth.create_staff_account(sys.argv[1], 'teacher', sys.argv[2])\n"
                "auth.create_staff_account(sys.argv[3], 'office', sys.argv[4])\n")
        subprocess.run([sys.executable, "-c", make, cls.emails["teacher"], cls.passwords["teacher"],
                        cls.emails["office"], cls.passwords["office"]],
                       cwd=cls.folder, env=env, check=True)
        cls.tokens = {}

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.server.kill()
        cls.log.close()
        if os.environ.get("KEEP_TEST_FOLDER") != "1":
            shutil.rmtree(cls.folder, ignore_errors=True)

    @classmethod
    def server_log(cls):
        cls.log.flush()
        with open(cls.log.name, encoding="utf-8", errors="replace") as f:
            return f.read()[-4000:]

    # small helpers --------------------------------------------------------
    def emails_to(self, address, about="", wait=8):
        """Emails the site 'sent' to this address (from the test outbox), oldest first.
        about: only those whose subject contains this. Waits a little, because
        some emails are sent in the background."""
        found = []
        for _ in range(int(wait * 10)):
            if os.path.exists(self.outbox):
                with open(self.outbox, encoding="utf-8") as f:
                    found = [json.loads(line) for line in f if line.strip()]
                found = [m for m in found if m["to"].lower() == address.lower() and about in m["subject"]]
                if found:
                    return found
            time.sleep(0.1)
        return found

    def code_sent_to(self, address):
        """The newest 6-digit code emailed to this address."""
        mails = self.emails_to(address, about="code" if "@std." in address else "")
        self.assertTrue(mails, f"no email reached {address}")
        codes = re.findall(r"\b(\d{6})\b", mails[-1]["body"])
        self.assertTrue(codes, f"the last email to {address} has no code")
        return codes[0]

    def call(self, path, body=None, who=None):
        return self.site.call(path, body, self.tokens.get(who) if who else None)

    def ok(self, path, body=None, who=None, what=""):
        """Call, and fail the test (with the site's own words) unless it worked."""
        status, answer = self.call(path, body, who)
        self.assertEqual(status, 200, f"{what or path}: got {status} {answer}")
        if isinstance(answer, dict) and "ok" in answer:
            self.assertTrue(answer["ok"], f"{what or path}: {answer}")
        return answer

    def refused(self, path, body=None, who=None, status=None, what=""):
        """Call, and fail the test unless the site said no."""
        got, answer = self.call(path, body, who)
        if status:
            self.assertEqual(got, status, f"{what or path}: expected {status}, got {got} {answer}")
        self.assertFalse(isinstance(answer, dict) and answer.get("ok") is True and got == 200,
                         f"{what or path}: should have been refused, but it worked: {answer}")
        return answer

    # ------------------------------------------------------------------
    # 1. public pages
    # ------------------------------------------------------------------
    def test_01_public_pages_open(self):
        """The landing page and every role's page open."""
        for page in ("/landing.html", "/app.html", "/teacher.html", "/office.html", "/exam.html"):
            status, _ = self.call(page)
            self.assertEqual(status, 200, f"{page} did not open")
        landing = self.ok("/api/landing")
        self.assertTrue(landing.get("batches"), "the landing page has no batches to sign up for")

    def test_02_private_files_stay_hidden(self):
        """Only the site's pages and photos can be downloaded: no code, databases, notes or folder lists."""
        for path in ("/server.py", "/auth.py", "/records.db", "/demo_records.db", "/NOTES.md",
                     "/START.bat", "/requirements.txt", "/.github/workflows/tests.yml",
                     "/photos/", "/tests/", "/.github/", "/photos/uploads/", "/uploads/",
                     "/photos/../server.py", "/photos/..%2fserver.py", "/%2e%2e/server.py",
                     "/photos/logo.webp/../../auth.py", "/peer_key.txt", "/outbox.jsonl"):
            status, body = self.call(path)
            self.assertEqual(status, 404, f"{path} could be downloaded or listed")
            self.assertNotIn("Directory listing", str(body))
        # HEAD asks "does this exist and how big is it?": same answer
        req = urllib.request.Request(self.site.base + "/server.py", method="HEAD")
        with self.assertRaises(urllib.error.HTTPError, msg="HEAD /server.py answered"):
            urllib.request.urlopen(req, timeout=10)
        status, _ = self.call("/photos/building-wide.jpg")
        self.assertEqual(status, 200, "a landing-page photo didn't load")

    def test_02b_security_headers(self):
        """Every answer carries the security headers and doesn't name the server's Python version."""
        for path in ("/landing.html", "/api/landing", "/nope"):
            try:
                resp = urllib.request.urlopen(self.site.base + path, timeout=10)
            except urllib.error.HTTPError as e:
                resp = e
            headers = resp.headers
            for name in ("Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options",
                         "Referrer-Policy", "Strict-Transport-Security"):
                self.assertTrue(headers.get(name), f"{path} has no {name} header")
            self.assertNotIn("Python", headers.get("Server", ""), f"{path} tells visitors the Python version")

    def test_02c_bangladesh_time(self):
        """The site's 'today' is Bangladesh's date (UTC+6), whatever the server's own clock says."""
        sys.path.insert(0, ROOT)
        import clock
        import datetime as dt
        self.assertEqual(clock.now().utcoffset(), dt.timedelta(hours=6))
        utc = dt.datetime.now(dt.timezone.utc)
        self.assertEqual(clock.today(), (utc + dt.timedelta(hours=6)).date())

    # ------------------------------------------------------------------
    # 2. signing in and registering
    # ------------------------------------------------------------------
    def test_03_staff_sign_in(self):
        """Teacher and office can sign in; a wrong password is refused."""
        self.refused("/api/signin", {"email": self.emails["teacher"], "password": "wrong-password"},
                     status=400, what="wrong password")
        for role in ("teacher", "office"):
            answer = self.ok("/api/signin", {"email": self.emails[role], "password": self.passwords[role]})
            self.assertEqual(answer["role"], role)
            self.tokens[role] = answer["token"]

    def test_03b_wrong_passwords_lock_only_that_device(self):
        """5 wrong passwords from one device lock that device, not the teacher on their own device."""
        email = self.emails["teacher"]
        stranger = {"X-Forwarded-For": "203.0.113.7"}
        for _ in range(5):
            status, _ = self.site.call("/api/signin", {"email": email, "password": "guess"}, extra=stranger)
            self.assertEqual(status, 400)
        status, answer = self.site.call("/api/signin", {"email": email, "password": self.passwords["teacher"]},
                                        extra=stranger)
        self.assertEqual(status, 400, "the stranger's device should be locked now")
        self.assertIn("Too many wrong tries", answer["why"])
        status, answer = self.site.call("/api/signin", {"email": email, "password": self.passwords["teacher"]},
                                        extra={"X-Forwarded-For": "198.51.100.20"})
        self.assertEqual(status, 200, f"the teacher was locked out by someone else's wrong tries: {answer}")
        self.tokens["teacher"] = answer["token"]

    def test_04_student_registers(self):
        """A student registers with a university email; bad emails and wrong codes are refused."""
        batches = self.ok("/api/landing")["batches"]
        TestSite.batch = next((b["name"] for b in batches if b.get("semester") == 5), None) \
            or batches[0]["name"]
        form = {"email": STUDENT_EMAIL, "name": "Test Student", "father": "Test Father",
                "mother": "Test Mother", "batch": self.batch}

        self.refused("/api/register/start", {**form, "email": "someone@gmail.com"},
                     status=400, what="non-university email")
        self.refused("/api/register/start", {**form, "email": "abc@std.cu.ac.bd"},
                     status=400, what="roll that isn't a number")
        self.refused("/api/register/start", {**form, "name": ""}, status=400, what="no name")

        start = self.ok("/api/register/start", form)
        self.assertNotIn("code", start, "the registration code must never be shown on screen")
        code = self.code_sent_to(STUDENT_EMAIL)
        self.refused("/api/register/finish", {"email": STUDENT_EMAIL, "code": "000000" if code != "000000" else "111111",
                                              "password": self.passwords["student"]},
                     status=400, what="wrong code")
        self.refused("/api/register/finish", {"email": STUDENT_EMAIL, "code": code,
                                              "password": "short"}, status=400, what="short password")
        done = self.ok("/api/register/finish", {"email": STUDENT_EMAIL, "code": code,
                                                "password": self.passwords["student"]})
        self.assertEqual(done["role"], "student")
        self.tokens["student"] = done["token"]

        self.refused("/api/register/start", form, status=400, what="registering the same email twice")

    # ------------------------------------------------------------------
    # 3. who may open what
    # ------------------------------------------------------------------
    def test_05_everyone_stays_in_their_own_pages(self):
        """Signed-out people, students, teachers and the office only reach their own pages."""
        self.refused("/api/home", status=401, what="student page while signed out")
        self.refused("/api/teach/home", who="student", status=403, what="student opening teacher page")
        self.refused("/api/office/requests", who="student", status=403, what="student opening office page")
        self.refused("/api/office/requests", who="teacher", status=403, what="teacher opening office page")
        self.refused("/api/teach/home", who="office", status=403, what="office opening teacher page")
        self.refused("/api/home", who="teacher", status=403, what="teacher opening student page")
        self.refused("/api/exam/sessions", who="teacher", status=403, what="teacher opening examiner page")
        self.refused("/api/home", who=None, status=401)

    def test_06_student_pages_load(self):
        """Every student page loads."""
        me = self.ok("/api/me", who="student")
        self.assertEqual(me["roll"], STUDENT_ROLL)
        for path in ("/api/home", "/api/semester", "/api/payments", "/api/complaints"):
            self.ok(path, who="student")
        fees = self.ok("/api/payments", who="student")["fees"]
        semesters = [f["semester"] for f in fees]
        self.assertEqual(semesters, sorted(set(semesters)), "a semester's fee is listed twice")

    def test_07_office_pages_load(self):
        """Every office page loads."""
        for path in ("/api/office/requests", "/api/office/batches", "/api/office/faculty",
                     "/api/office/complaints", "/api/office/gallery", "/api/office/achievements",
                     "/api/office/demo"):
            self.ok(path, who="office")
        self.ok("/api/office/students?session=" + urllib.request.quote(self.batch), who="office")

    # ------------------------------------------------------------------
    # 4. the office gives a teacher a class
    # ------------------------------------------------------------------
    def test_08_teacher_asks_for_classes(self):
        """The teacher asks for two classes; asking for the same one twice is refused."""
        home = self.ok("/api/teach/home", who="teacher")
        semester = self.ok("/api/semester", who="student")["semester"]
        mine = [c for c in home["courses"] if c["semester"] == semester]
        self.assertGreaterEqual(len(mine), 3, "not enough courses in the student's semester")
        TestSite.course, TestSite.other_course = mine[0]["course_id"], mine[1]["course_id"]
        TestSite.spare_course = mine[2]["course_id"]

        # Bug of 22 Nov 2026: CSE 517 (5th semester) was asked for under 2025-26, a batch
        # in its 1st semester, so the approved class had no students. Now it is refused.
        wrong = next((b["name"] for b in self.ok("/api/landing")["batches"]
                      if b.get("semester") != semester), None)
        if wrong:
            why = self.refused("/api/teach/request", {"course_id": self.course, "session": wrong},
                               who="teacher", status=400, what="asking for a class under the wrong batch")
            self.assertIn("No students of", why.get("why", ""))

        self.refused(f"/api/teach/class?course_id={self.course}&session={urllib.request.quote(self.batch)}",
                     who="teacher", status=403, what="opening a class before the office gives it")
        for course in (self.course, self.other_course):
            self.ok("/api/teach/request", {"course_id": course, "session": self.batch}, who="teacher")
        self.refused("/api/teach/request", {"course_id": self.course, "session": self.batch},
                     who="teacher", status=400, what="asking for the same class twice")
        self.refused("/api/teach/request", {"course_id": "NOPE-0000", "session": self.batch},
                     who="teacher", status=400, what="asking for a course that doesn't exist")

    def test_09_office_approves_and_turns_down(self):
        """The office approves one request and turns down the other, using the number the office page shows.

        Bug of 22 Nov 2026: the office page reads the number from "id", the server only sent
        "request_id", so every Approve said "No such request" and Turn down did nothing.
        """
        waiting = [r for r in self.ok("/api/office/requests", who="office")["requests"]
                   if r["status"] == "waiting"]
        by_course = {r["course_id"]: r for r in waiting}
        for course in (self.course, self.other_course):
            self.assertIn(course, by_course, f"the office can't see the request for {course}")
            self.assertIsNotNone(by_course[course].get("id"),
                                 "the request has no 'id', so the office page can't approve it")

        # exactly what office.html sends: decide(r.id, true/false)
        self.ok("/api/office/decide", {"request_id": by_course[self.course]["id"], "approve": True,
                                       "note": ""}, who="office", what="Approve")
        self.ok("/api/office/decide", {"request_id": by_course[self.other_course]["id"], "approve": False,
                                       "note": "test"}, who="office", what="Turn down")

        now = {r["course_id"]: r["status"] for r in self.ok("/api/office/requests", who="office")["requests"]
               if r["id"] in (by_course[self.course]["id"], by_course[self.other_course]["id"])}
        self.assertEqual(now, {self.course: "approved", self.other_course: "rejected"})

        self.refused("/api/office/decide", {"request_id": 99999999, "approve": True, "note": ""},
                     who="office", status=400, what="deciding a request that doesn't exist")
        self.refused("/api/office/decide", {"approve": True, "note": ""},
                     who="office", status=400, what="deciding with no request number")
        self.refused("/api/office/decide", {"request_id": by_course[self.course]["id"], "approve": False,
                                            "note": ""}, who="office", status=400,
                     what="deciding the same request a second time")
        self.refused("/api/office/decide", {"request_id": by_course[self.course]["id"], "approve": True},
                     who="teacher", status=403, what="a teacher approving their own request")

    def test_10_teacher_opens_the_class(self):
        """After approval the teacher sees the class, with the new student in it."""
        cls = self.ok(f"/api/teach/class?course_id={self.course}&session={urllib.request.quote(self.batch)}",
                      who="teacher")
        rolls = [s["roll"] for s in cls["students"]]
        self.assertIn(STUDENT_ROLL, rolls, "the registered student is missing from the class")
        self.assertTrue(cls["items"], "the class has no marks items")
        TestSite.item = cls["items"][-1]
        TestSite.dates = cls["dates"]
        self.refused(f"/api/teach/class?course_id={self.other_course}&session={urllib.request.quote(self.batch)}",
                     who="teacher", status=403, what="opening the class the office turned down")

    # ------------------------------------------------------------------
    # 5. marks, corrections, objections, attendance
    # ------------------------------------------------------------------
    def entry(self, value, reason=""):
        return {"course_id": self.course, "session": self.batch,
                "entries": [{"roll": STUDENT_ROLL, "item_id": self.item["item_id"],
                             "value": value, "reason": reason}]}

    def test_11_marks_follow_the_rules(self):
        """A mark above the out-of is refused; a change needs a reason; with one it goes through."""
        out_of = self.item["out_of"]
        answer = self.call("/api/teach/marks", self.entry(out_of + 50), "teacher")[1]
        self.assertFalse(answer["ok"], "a mark above the out-of was accepted")
        self.assertFalse(self.call("/api/teach/marks", self.entry(-1), "teacher")[1]["ok"],
                         "a negative mark was accepted")

        first = self.ok("/api/teach/marks", self.entry(out_of - 3, "First entry"), who="teacher")
        self.assertTrue(first["results"][0]["ok"])
        no_reason = self.call("/api/teach/marks", self.entry(out_of - 2), "teacher")[1]
        self.assertFalse(no_reason["ok"], "a mark was changed without a reason")
        self.ok("/api/teach/marks", self.entry(out_of - 2, "Re-checked the script"), who="teacher")
        again = self.call("/api/teach/marks", self.entry(out_of - 2, "Re-checked the script"), "teacher")[1]
        self.assertFalse(again["ok"], "pressing Save twice wrote the same correction twice")

        # a teacher can't put marks into a class they don't have
        other = {**self.entry(1, "x"), "course_id": self.other_course}
        self.assertFalse(self.call("/api/teach/marks", other, "teacher")[1]["ok"],
                         "a teacher entered marks in a class the office turned down")

    def test_12_student_sees_the_change_and_its_history(self):
        """The student sees the new mark, and the history keeps the old one with the reason."""
        course = self.ok(f"/api/course?course_id={self.course}", who="student")
        item = next(i for i in course["main"]["items"] if i["item_id"] == self.item["item_id"])
        self.assertEqual(item["value"], self.item["out_of"] - 2, "the student doesn't see the corrected mark")

        history = self.ok(f"/api/history?course_id={self.course}&item_id={self.item['item_id']}",
                          who="student")["marks"]
        values = [h["detail"].get("value") for h in history]
        self.assertIn(self.item["out_of"] - 3, values, "the history lost the old mark")
        self.assertIn(self.item["out_of"] - 2, values, "the history doesn't show the new mark")
        self.assertIn("Re-checked the script", json.dumps(history), "the reason isn't in the history")

        # the student is emailed about the change, with the reason
        changed = self.emails_to(STUDENT_EMAIL, about="was changed")
        self.assertTrue(changed, "the student wasn't emailed about the changed mark")
        self.assertIn("Re-checked the script", changed[-1]["body"])

    def test_13_objection_round_trip(self):
        """The student raises an objection; the teacher answers it; it shows in the history."""
        self.ok("/api/object", {"course_id": self.course, "item_id": self.item["item_id"],
                                "note": "I think it was higher"}, who="student")
        cls = self.ok(f"/api/teach/class?course_id={self.course}&session={urllib.request.quote(self.batch)}",
                      who="teacher")
        self.assertTrue(any(o.get("roll") == STUDENT_ROLL for o in cls["objections"]),
                        "the teacher can't see the objection")
        self.ok("/api/teach/objection/close", {"course_id": self.course, "roll": STUDENT_ROLL,
                                               "item_id": self.item["item_id"],
                                               "outcome": "Checked again, the mark stands"}, who="teacher")
        threads = self.ok(f"/api/history?course_id={self.course}&item_id={self.item['item_id']}",
                          who="student")["threads"]
        self.assertTrue(threads, "the objection is missing from the history")

    def test_14_attendance_register(self):
        """The teacher saves a register for a past class."""
        past = next((d for d in self.dates if not d["future"] and not d["cancelled"]), None)
        if past is None:
            self.skipTest("this class has no past dates yet")
        self.ok("/api/teach/attendance", {"course_id": self.course, "session": self.batch,
                                          "session_id": past["session_id"],
                                          "marks": {STUDENT_ROLL: True}}, who="teacher")

    # ------------------------------------------------------------------
    # 6. the chain
    # ------------------------------------------------------------------
    def test_15_chain_is_valid(self):
        """After all of that, the chain checks out."""
        result = self.ok("/api/verify", who="student")
        chain = self.ok("/api/chain")
        self.assertTrue(chain["ok"], chain["message"])
        self.assertGreater(chain["count"], 0)

    def test_15b_chain_records_are_private(self):
        """Anyone sees only fingerprints; the records go only to the office and to copies with the peer key."""
        public = self.ok("/api/chain")
        self.assertTrue(public["blocks"])
        leaked = {k for b in public["blocks"] for k in b} - {"block_no", "prev_hash", "hash"}
        self.assertFalse(leaked, f"the public chain shows {leaked}")
        self.assertNotIn(STUDENT_ROLL, json.dumps(public), "a roll number is visible in the public chain")

        for path in ("/api/chain?full=1", "/api/peers", "/api/peer-code"):
            self.refused(path, status=403, what=f"{path} without signing in")
            self.refused(path, who="student", status=403, what=f"{path} as a student")
            self.refused(path, who="teacher", status=403, what=f"{path} as a teacher")
        self.assertEqual(self.site.call("/api/chain?full=1", extra={"X-Peer-Key": "wrong"})[0], 403,
                         "a wrong peer key got the full records")
        self.refused("/api/peers/hello", {"name": "fake", "count": 1, "ok": True}, status=403,
                     what="a fake chain copy saying hello without the key")

        office = self.ok("/api/chain?full=1", who="office")
        self.assertIn("payload", office["blocks"][-1], "the office should see the full records")
        status, copy = self.site.call("/api/chain?full=1", extra={"X-Peer-Key": self.env["PEER_KEY"]})
        self.assertEqual(status, 200, "a chain copy with the right key was refused")
        self.assertIn("payload", copy["blocks"][-1])
        status, _ = self.site.call("/api/peers/hello", {"name": "ci-copy", "port": 8100, "count": 1, "ok": True},
                                   extra={"X-Peer-Key": self.env["PEER_KEY"]})
        self.assertEqual(status, 200, "a real chain copy couldn't say hello")

    def test_16_insider_edit_is_caught(self):
        """An edit made straight in the database is caught, and putting it back makes the chain whole."""
        self.ok("/api/office/demo-tamper", {}, who="office", what="simulate an insider edit")
        try:
            self.assertFalse(self.call("/api/chain")[1]["ok"], "the chain didn't notice the insider edit")
        finally:
            self.ok("/api/office/demo-undo", {}, who="office", what="put it back")
        self.assertTrue(self.call("/api/chain")[1]["ok"], "the chain is still broken after putting it back")

    # ------------------------------------------------------------------
    # 7. many people at once
    # ------------------------------------------------------------------
    def test_17_many_people_at_once(self):
        """30 requests arrive at the same moment; every one gets an answer."""
        jobs = [("/api/landing", None)] * 10 + [("/api/home", "student")] * 10 \
            + [("/api/teach/home", "teacher")] * 10
        started = time.time()
        with ThreadPoolExecutor(max_workers=30) as pool:
            statuses = list(pool.map(lambda j: self.call(j[0], who=j[1])[0], jobs))
        self.assertEqual(statuses, [200] * len(jobs), f"some requests failed: {statuses}")
        self.assertLess(time.time() - started, 60, "30 requests at once took over a minute")

    def test_17b_many_saves_at_once_keep_the_chain_whole(self):
        """20 mark changes saved at the same moment: every one gets its own block, and the chain stays valid."""
        cls_ = self.ok(f"/api/teach/class?course_id={self.course}&session={urllib.request.quote(self.batch)}",
                       who="teacher")
        rolls = [st["roll"] for st in cls_["students"] if st["roll"] != STUDENT_ROLL][:20]
        item = cls_["items"][0]
        before = self.ok("/api/chain")["count"]

        def save(roll):
            body = {"course_id": self.course, "session": self.batch,
                    "entries": [{"roll": roll, "item_id": item["item_id"], "value": 1, "reason": "parallel test"}]}
            return self.call("/api/teach/marks", body, "teacher")[1]

        with ThreadPoolExecutor(max_workers=20) as pool:
            answers = list(pool.map(save, rolls))
        blocks = [r["block_no"] for a in answers for r in a["results"] if r["ok"]]
        self.assertEqual(len(blocks), len(rolls), f"some saves failed: {answers}")
        self.assertEqual(len(set(blocks)), len(blocks), "two saves got the same block number")
        chain = self.ok("/api/chain")
        self.assertTrue(chain["ok"], chain["message"])
        self.assertEqual(chain["count"], before + len(rolls))

    # ------------------------------------------------------------------
    # 8. the pages' own code
    # ------------------------------------------------------------------
    def test_18_page_scripts_have_no_typos(self):
        """The JavaScript inside every page can be read without a syntax error."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed here")
        for page in sorted(f for f in os.listdir(ROOT) if f.endswith(".html")):
            with open(os.path.join(ROOT, page), encoding="utf-8") as f:
                html = f.read()
            scripts = []
            for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", html, re.S | re.I):
                if re.search(r"\bsrc=", attrs, re.I) or not body.strip():
                    continue
                kind = re.search(r"""\btype=["']?([^"'\s>]+)""", attrs, re.I)
                kind = kind.group(1).lower() if kind else "text/javascript"
                if kind.endswith("json"):          # search-engine info: must be valid JSON
                    try:
                        json.loads(body)
                    except ValueError as e:
                        self.fail(f"{page} has broken JSON in a {kind} block: {e}")
                elif kind in ("text/javascript", "application/javascript", "module"):
                    scripts.append(body)
            if not scripts:
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as js:
                js.write("\n;\n".join(scripts))
            try:
                done = subprocess.run([node, "--check", js.name], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, f"{page} has a JavaScript error:\n{done.stderr[-1500:]}")
            finally:
                os.unlink(js.name)

    # ------------------------------------------------------------------
    # 9. taking a class back
    # ------------------------------------------------------------------
    def test_20_teacher_withdraws_a_waiting_request(self):
        """The teacher withdraws a request before the office answers; the office can't approve it after."""
        asked = self.ok("/api/teach/request", {"course_id": self.spare_course, "session": self.batch},
                        who="teacher")["request_id"]
        self.ok("/api/teach/withdraw", {"request_id": asked}, who="teacher")
        status = {r["id"]: r["status"] for r in self.ok("/api/office/requests", who="office")["requests"]}
        self.assertEqual(status.get(asked), "withdrawn")
        self.refused("/api/teach/withdraw", {"request_id": asked}, who="teacher", status=400,
                     what="withdrawing the same request twice")
        self.refused("/api/office/decide", {"request_id": asked, "approve": True, "note": ""},
                     who="office", status=400, what="approving a withdrawn request")

    def test_21_teacher_removes_an_unused_class(self):
        """An approved class with nothing entered yet can be removed, and asked for again later."""
        asked = self.ok("/api/teach/request", {"course_id": self.spare_course, "session": self.batch},
                        who="teacher")["request_id"]
        self.ok("/api/office/decide", {"request_id": asked, "approve": True, "note": ""}, who="office")
        home = self.ok("/api/teach/home", who="teacher")
        card = next(c for c in home["classes"] if c["course_id"] == self.spare_course)
        self.assertTrue(card["removable"], "an unused class should show the Remove button")

        self.ok("/api/teach/remove", {"course_id": self.spare_course, "session": self.batch}, who="teacher")
        quoted = urllib.request.quote(self.batch)
        self.refused(f"/api/teach/class?course_id={self.spare_course}&session={quoted}", who="teacher",
                     status=403, what="opening a class after removing it")
        status = {r["id"]: r["status"] for r in self.ok("/api/office/requests", who="office")["requests"]}
        self.assertEqual(status.get(asked), "removed", "the office should see the class was removed")
        self.assertTrue(self.ok("/api/chain")["ok"], "removing a class broke the chain")
        self.ok("/api/teach/request", {"course_id": self.spare_course, "session": self.batch},
                who="teacher", what="asking again after removing")

    def test_22_class_with_marks_stays(self):
        """A class with marks already in it can't be removed, and others can't remove it either."""
        home = self.ok("/api/teach/home", who="teacher")
        card = next(c for c in home["classes"] if c["course_id"] == self.course)
        self.assertFalse(card["removable"], "a class with marks should not offer Remove")
        self.refused("/api/teach/remove", {"course_id": self.course, "session": self.batch},
                     who="teacher", status=400, what="removing a class that has marks")
        self.refused("/api/teach/remove", {"course_id": self.course, "session": self.batch},
                     who="office", status=403, what="the office using the teacher's remove button")

    # ------------------------------------------------------------------
    # 10. the office's Email settings page
    # ------------------------------------------------------------------
    def test_23_email_settings(self):
        """The office changes the chairman's address: code to the new inbox first, then it's on the chain."""
        before = {s["key"]: s for s in self.ok("/api/office/settings", who="office")["settings"]}
        self.assertEqual(set(before), {"office", "chairman"})
        self.assertEqual(before["chairman"]["source"], "none", "the test server should start with no address")

        self.refused("/api/office/settings", who="teacher", status=403, what="a teacher opening email settings")
        self.refused("/api/office/settings/start", {"key": "chairman", "address": "x@cu.ac.bd"},
                     who="student", status=403, what="a student changing email settings")
        self.refused("/api/office/settings/start", {"key": "chairman", "address": "not-an-email"},
                     who="office", status=400, what="a badly typed address")
        self.refused("/api/office/settings/start", {"key": "nobody", "address": "x@cu.ac.bd"},
                     who="office", status=400, what="a setting that doesn't exist")
        self.refused("/api/office/settings/finish", {"key": "chairman", "code": "123456"},
                     who="office", status=400, what="confirming before any code was sent")

        start = self.ok("/api/office/settings/start", {"key": "chairman", "address": "Test.Chair@cu.ac.bd"},
                        who="office")
        self.assertNotIn("code", start, "the code must never be shown on screen")
        code = self.code_sent_to("test.chair@cu.ac.bd")
        wrong = "000000" if code != "000000" else "111111"
        self.refused("/api/office/settings/finish", {"key": "chairman", "code": wrong},
                     who="office", status=400, what="a wrong code")
        still = {s["key"]: s for s in self.ok("/api/office/settings", who="office")["settings"]}
        self.assertIsNone(still["chairman"]["address"], "the address changed before the code was confirmed")

        self.ok("/api/office/settings/finish", {"key": "chairman", "code": code}, who="office")
        after = self.ok("/api/office/settings", who="office")
        chair = next(s for s in after["settings"] if s["key"] == "chairman")
        self.assertEqual((chair["address"], chair["source"]), ("test.chair@cu.ac.bd", "website"))
        self.assertEqual(after["history"][0]["new"], "test.chair@cu.ac.bd")
        self.refused("/api/office/settings/start", {"key": "chairman", "address": "test.chair@cu.ac.bd"},
                     who="office", status=400, what="changing to the address it already has")
        self.assertTrue(self.ok("/api/chain")["ok"], "changing an email setting broke the chain")

    def test_24_complaint_goes_to_the_addresses_on_the_settings_page(self):
        """A complaint is emailed to the chairman address the office set, without the student's name."""
        self.ok("/api/complaint", {"what": "Fan in room 214 is broken", "why": "It is very hot",
                                   "fix": "Repair the fan"}, who="student")
        self.refused("/api/complaint", {"what": "Fan in room 214 is broken", "why": "It is very hot",
                                        "fix": "Repair the fan"}, who="student", status=400,
                     what="sending the same complaint twice")
        mails = self.emails_to("test.chair@cu.ac.bd", about="Fan in room 214")
        self.assertTrue(mails, "the complaint didn't reach the chairman address set on the settings page")
        self.assertNotIn("Test Student", mails[-1]["body"], "the complaint email shows the student's name")
        self.assertNotIn(STUDENT_ROLL, mails[-1]["body"], "the complaint email shows the roll number")

    def test_25_password_reset(self):
        """Forgot password: code to the inbox (never on screen), wrong codes refused, new password works."""
        self.refused("/api/password/start", {"email": "nobody99@std.cu.ac.bd"}, status=400,
                     what="resetting an email with no account")
        start = self.ok("/api/password/start", {"email": STUDENT_EMAIL})
        self.assertNotIn("code", start, "the reset code must never be shown on screen")
        code = self.code_sent_to(STUDENT_EMAIL)
        new_password = secrets.token_urlsafe(12)
        self.refused("/api/password/finish", {"email": STUDENT_EMAIL, "code": "000000" if code != "000000" else "111111",
                                              "password": new_password}, status=400, what="a wrong reset code")
        self.refused("/api/password/finish", {"email": STUDENT_EMAIL, "code": code, "password": "short"},
                     status=400, what="a too-short new password")
        old_token = self.tokens["student"]
        done = self.ok("/api/password/finish", {"email": STUDENT_EMAIL, "code": code, "password": new_password})
        self.assertEqual(self.site.call("/api/home", token=old_token)[0], 401,
                         "an old sign-in still works after the password was reset")
        self.refused("/api/signin", {"email": STUDENT_EMAIL, "password": self.passwords["student"]},
                     status=400, what="the old password after a reset")
        self.tokens["student"] = done["token"]
        self.passwords["student"] = new_password
        self.ok("/api/home", who="student", what="signing in with the new password")
        self.refused("/api/password/finish", {"email": STUDENT_EMAIL, "code": code, "password": new_password},
                     status=400, what="using the same reset code twice")

    def test_26_loading_screen_on_every_page(self):
        """Every page loads the shared loading screen, and sign-out and new tabs play it."""
        status, js = self.call("/loader.js")
        self.assertEqual(status, 200, "loader.js can't be downloaded, so no page can show the loading screen")
        self.assertIn("eeeLoader", js)
        for page in ("landing.html", "app.html", "teacher.html", "office.html", "exam.html"):
            with open(os.path.join(ROOT, page), encoding="utf-8") as f:
                html = f.read()
            self.assertIn('<script src="loader.js"></script>', html, f"{page} doesn't load the loading screen")
            if page != "landing.html":
                self.assertIn("eeeGo('landing.html#enter')", html, f"signing out of {page} skips the loading screen")
        with open(os.path.join(ROOT, "landing.html"), encoding="utf-8") as f:
            self.assertIn("'#intro'", f.read(), "an account opened in a new tab won't play the loading screen")
        node = shutil.which("node")
        if node:
            done = subprocess.run([node, "--check", os.path.join(ROOT, "loader.js")], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, f"loader.js has a JavaScript error:\n{done.stderr[-1500:]}")

    def test_27_codes_cant_flood_an_inbox(self):
        """Asking for codes again and again stops after a few, so nobody's inbox can be flooded."""
        email = "99999077@std.cu.ac.bd"
        form = {"email": email, "name": "Flood Test", "father": "F", "mother": "M", "batch": self.batch}
        results = [self.call("/api/register/start", form)[0] for _ in range(7)]
        self.assertEqual(results[:5], [200] * 5)
        self.assertEqual(results[5:], [400, 400], "more than 5 codes an hour went to one address")
        self.assertLessEqual(len(self.emails_to(email, about="code")), 5)

    def test_28_chain_check_button(self):
        """Pressing "check the chain" many times re-uses the recent result; a new block makes it check again."""
        first = self.ok("/api/verify", who="office")
        again = self.ok("/api/verify", who="office")
        self.assertTrue(again.get("remembered"), "the full check ran again straight away")
        self.ok("/api/office/demo-tamper", {}, who="office")
        try:
            status, caught = self.call("/api/verify", who="office")
            self.assertEqual(status, 200)
            self.assertFalse(caught["ok"], "after the insider edit, the check still said everything was fine")
        finally:
            self.ok("/api/office/demo-undo", {}, who="office")
        self.assertTrue(self.ok("/api/verify", who="office")["ok"])

    def test_29_delete_account_keeps_the_marks(self):
        """A student deletes their login; the marks stay; registering again brings everything back."""
        item_id = self.item["item_id"]
        mark_before = next(i["value"] for i in self.ok(f"/api/course?course_id={self.course}", who="student")
                           ["main"]["items"] if i["item_id"] == item_id)
        self.refused("/api/account/delete", {"password": "wrong-password"}, who="student", status=400,
                     what="deleting with the wrong password")
        self.refused("/api/account/delete", {"password": self.passwords["teacher"]}, who="teacher", status=403,
                     what="a teacher using the student delete button")
        old_token = self.tokens["student"]
        self.ok("/api/account/delete", {"password": self.passwords["student"]}, who="student")

        self.assertEqual(self.site.call("/api/home", token=old_token)[0], 401, "still signed in after deleting")
        self.refused("/api/signin", {"email": STUDENT_EMAIL, "password": self.passwords["student"]},
                     status=400, what="signing in to a deleted account")
        self.assertTrue(self.emails_to(STUDENT_EMAIL, about="account was deleted"),
                        "the student wasn't told their account was deleted")
        # the teacher still sees the student and the mark
        cls_ = self.ok(f"/api/teach/class?course_id={self.course}&session={urllib.request.quote(self.batch)}",
                       who="teacher")
        self.assertIn(STUDENT_ROLL, [st["roll"] for st in cls_["students"]], "the student vanished from the class")
        self.assertEqual(cls_["marks"][STUDENT_ROLL][item_id]["value"], mark_before, "the mark changed or vanished")
        self.assertTrue(self.ok("/api/chain")["ok"])

        # registering again: same email, the parents' names the office already has
        self.ok("/api/register/start", {"email": STUDENT_EMAIL, "name": "Test Student", "father": "Test Father",
                                        "mother": "Test Mother", "batch": self.batch})
        code = self.code_sent_to(STUDENT_EMAIL)
        done = self.ok("/api/register/finish", {"email": STUDENT_EMAIL, "code": code,
                                                "password": self.passwords["student"]})
        self.tokens["student"] = done["token"]
        mark_after = next(i["value"] for i in self.ok(f"/api/course?course_id={self.course}", who="student")
                          ["main"]["items"] if i["item_id"] == item_id)
        self.assertEqual(mark_after, mark_before, "the old mark didn't come back after registering again")

    def test_99_server_had_no_crashes(self):
        """The server stayed up the whole time and wrote no Python errors."""
        self.assertIsNone(self.server.poll(), "the server stopped during the tests")
        self.assertNotIn("Traceback", self.server_log(), "the server hit an error:\n" + self.server_log())


class TestDatabaseDown(unittest.TestCase):
    """22 Nov 2026: Supabase paused, the server crashed at start-up, and the whole site
    showed Render's "Application loading" forever. Now it must open anyway."""

    def test_site_opens_and_says_the_records_are_unreachable(self):
        """With no database, pages explain the problem, the API answers 503, and nothing crashes."""
        folder = tempfile.mkdtemp(prefix="eee-nodb-")
        shutil.copytree(ROOT, folder, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "records.db", "__pycache__", "tests"))
        port = free_port()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GMAIL_", "MAIL_"))}
        env.update({"PORT": str(port), "DB_RETRY_SECONDS": "60", "PYTHONUNBUFFERED": "1",
                    "DATABASE_URL": "postgresql://nobody:nothing@127.0.0.1:1/none"})   # nothing listens there
        log = open(os.path.join(folder, "server.log"), "w")
        server = subprocess.Popen([sys.executable, "server.py"], cwd=folder, env=env,
                                  stdout=log, stderr=subprocess.STDOUT)
        site = Site(port)
        try:
            for _ in range(120):
                self.assertIsNone(server.poll(), "the server crashed because the database is down")
                try:
                    status, page = site.call("/landing.html")
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                self.fail("the server never opened")
            self.assertEqual(status, 503)
            self.assertIn("not reachable", page)
            status, answer = site.call("/api/landing")
            self.assertEqual((status, answer.get("offline")), (503, True))
            self.assertEqual(site.call("/loader.js")[0], 200, "the loading screen should still load")
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
