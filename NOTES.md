# Notes

Plain-English notes on what changed and why. Newest at the top.

## 2026-11-22 — Security round 1

**1. Codes are never shown on screen.** Registration, staff sign-up, password
reset and the Email settings page only ever email the code. If the email can't
be sent, the person is told to try again later. The code is also no longer
written to the server's log. (`auth.py`, `site_settings.py`, `server.py`,
`landing.html`, `office.html`; the `SHOW_CODE` setting no longer exists.)
Registration and reset codes go to the university address typed, even if
`MAIL_ALLOW_ALL` is off.

**2. The chain's records are private.** `/api/chain` now shows anyone only the
fingerprints (block number, previous hash, hash), enough to check nothing was
changed and nothing about anyone. The full records (`?full=1`), the list of
chain copies (`/api/peers`) and the copy program (`/api/peer-code`) are only
for the office or a chain copy holding the shared `PEER_KEY`. A copy saying
hello (`/api/peers/hello`) must have the key. `peer.py` sends the key, read
from the `PEER_KEY` setting or a `peer_key.txt` file next to it.

**3. Only the site's own pages and photos can be downloaded.** Everything else
(code, databases, notes, tests, `START.bat`, folder listings) answers "Not
available", also for tricks like `/photos/../server.py` and HEAD requests.
The server no longer tells visitors its Python version. (`server.py`:
`PAGES`, `may_download`.)

**4. Security headers on every answer** (`server.py`: `SECURITY_HEADERS`):
Content-Security-Policy, X-Frame-Options, X-Content-Type-Options,
Referrer-Policy, Strict-Transport-Security, Permissions-Policy. API answers are
never cached.

**5. Bangladesh time.** New `clock.py`: "what day is it" is always asked in
Bangladesh time (UTC+6). Render's clock is UTC, so between midnight and 6 AM
the site used to think it was still yesterday.

**6. Text people type is always made safe before it is shown.** The `esc()`
helper on every page now also escapes quote marks (a name with `"` could break
out of a form field). The student page now escapes the teacher's reason, the
objection notes, the closing note, the student's own name and parents' names.
Batch names must look like `2026–27`.

**7. Wrong passwords lock the device, not the account.** 5 wrong tries lock
that device for 15 minutes; a stranger can't lock a student out from their own
phone any more. 25 wrong tries from all devices together still lock the
account, to stop password guessing. If the email has no account, the message
says to register first.

**Tests:** checks 2, 2b, 2c, 3b, 15b, 24, 25 are new; check 4 and 23 now read
codes from a test-only outbox file (`MAIL_OUTBOX`) instead of the screen; the
mark-change email is checked in 12. 29 checks, on SQLite and Postgres.

## 2026-11-22 — The office sets where its emails go (Email settings)

**What you see (office page):** a new **Email settings** item in the sidebar.
It shows where emails to the office (tamper alerts, complaints) and to the
chairman (complaints) go, and lets the office change them:
1. Type the new address, press **Send a code to this address**.
2. Open that inbox, type the 6-digit code, press **Confirm and change**.
3. The old address gets an email saying it was changed (for an office change,
   the chairman is told too). The change is a block on the chain, and it is
   listed under "Changes so far".

**Why:** these addresses used to live only in Render's settings
(`OFFICE_EMAIL`, `CHAIRMAN_EMAIL`). If the site is adopted and an address
changes years from now, the office won't know Render exists. Now they change
it themselves. A typo can't send complaints into nowhere (the code must come
from the new inbox), and nobody can quietly redirect complaints (the old
address is told, and the chain keeps every change).

**What changed:**
- `site_settings.py` (new): the two settings, the code step, the warning
  emails, the chain block (`email_setting_changed`). Two new tables:
  `email_settings`, `email_settings_pending`.
- `mailer.py`: `office_address()` and the new `chairman_address()` read the
  website's setting first; `OFFICE_EMAIL` / `CHAIRMAN_EMAIL` on the server are
  now only the starting values. `send()` / `send_later()` got `trusted=True`
  for the settings page's own emails (a new address isn't on the allow-list
  yet).
- `complaints.py`: uses `mailer.chairman_address()`.
- `server.py`: `/api/office/settings`, `/api/office/settings/start`,
  `/api/office/settings/finish` (office only).
- `office.html`: the Email settings page.
- `tests/test_site.py`: check 23. The tests can also run against Postgres
  (`TEST_DATABASE_URL`, an empty test database), and GitHub now runs them on
  both SQLite and Postgres.

**Tip for the real thing:** use role addresses like `chairman.eee@cu.ac.bd`
and an office address on the university domain, not someone's personal Gmail,
so they don't need changing when people change.

## 2026-11-22 — Teachers can take back a class; wrong batches are refused

**What you see (teacher page):**
- **Remove this class** under a class card, as long as no marks or attendance
  have been entered in it. The office's list then shows that request as
  "removed by the teacher".
- **Withdraw request** under a request the office hasn't answered yet.
- In "Add a class", each batch shows its semester, e.g. "2023–24 (5th
  semester now)", and picking a course selects the right batch by itself.
- The sidebar shows the batch next to each class (CSE 517 · 2023–24).

**Why:** CSE 517 was asked for under 2025–26 (the list started with the newest
batch). 2025–26 is in its 1st semester, so the approved class had no students,
and there was no way to undo it. Also, if a teacher had the same course for two
batches, clicking either one always opened the first.

**What changed:**
- `contract.py`: `request_class` refuses a batch with no students in that
  course and says which batch is in that semester now. New `withdraw_request`,
  `class_in_use` and `remove_class`. Nothing is deleted from the chain: a
  withdrawal is a new `class_decision` block, a removal is a new
  `class_removed` block; only the quick-lookup `teaching` table loses the row.
  A class with marks or attendance in it can't be removed.
- `server.py`: new `/api/teach/withdraw` and `/api/teach/remove`; the teacher
  home now sends each batch's semester and whether each class can be removed.
- `teacher.html`: the buttons, the batch picker, and classes opened by position
  instead of by course code.
- `office.html`: shows "withdrawn" and "removed by the teacher".
- `tests/test_site.py`: checks 20–22, plus the wrong-batch check in check 8.

## 2026-11-22 — Automatic check-up on every upload

**What you see:** On GitHub, every upload now gets a green tick (all checks
passed) or a red cross (something broke). Click it to see which check failed
and why, in plain words.

**Why:** Bugs like the office "No such request" one only showed up when
someone clicked the button on the live site. Now a robot clicks through the
site after every upload, before anyone else has to.

**What changed:**
- `tests/test_site.py` (new): copies the project into a throwaway folder,
  starts the site there, makes its own test teacher/office accounts, and acts
  out the main jobs: student sign-up, a teacher asking for a class, the office
  approving and turning down, marks and corrections, an objection, attendance,
  the chain check, an insider edit being caught, 30 people at once, and a typo
  check on every page's JavaScript. 19 checks. It never touches the real
  database.
- `.github/workflows/tests.yml` (new): tells GitHub to run that file on every
  upload.
- Run it yourself: `python -m unittest discover -s tests -v`

**The rule from now on:** every bug we find gets its own check in
`tests/test_site.py`, so it can't come back. The office bug is already check 9.

**Still to do (Nabiha):** Render → eeerecords → Settings → Auto-Deploy →
"After CI Checks Pass", so a red cross never goes live.

## 2026-11-22 — Office can approve and turn down class requests again

**What you see:** On the office page, Approve and Turn down on a teacher's
class request now work. Before, Approve said "No such request" and Turn down
did nothing.

**Why it broke:** The office page looks for each request's number in a field
called `id`, but the server only sent it as `request_id`. So the page sent no
number at all, and the server could not find the request.

**What changed in `server.py`:** in `office_requests()`, each request card now
also carries `id` (the same number). One line.

## 2026-11-22 — Payment is one item in the sidebar

**What you see:** Payment now sits once in the sidebar, right under Complaint
box. It is no longer repeated inside every semester. The semesters still show
Courses and Timetable as before.

**Why:** The payment page already lists every semester's fee in one table, so
one button is enough.

**What changed in `app.html`:** in `drawNav()`, a Payment button was added
under the Complaint box button, and the Payment button inside each semester
was removed. The payment page itself did not change.

## 2026-09-24 — Three laptops, three copies

**What happens now.** The other two laptops each run `peer.py`. Every ten
seconds it asks this laptop for the whole chain — the records, not just their
fingerprints — checks every record itself, and saves its own copy. Each copy
also serves what it holds, so the laptops ask *each other*, not only the writer.

**It does not trust what it is given.** It recomputes every fingerprint from
the record itself, and it never overwrites a record it already holds. If a
record it saved yesterday comes back different, it keeps its own copy, says
REFUSED, and writes it in its diary.

**Nobody gets sent the file twice.** `peer.py` updates itself from this laptop
each time it starts. To set a laptop up the first time, one line:

    iwr http://10.43.199.128:8000/api/peer-code -OutFile peer.py; py peer.py najah

**Watching it.** Each copy shows itself at http://localhost:8100 — how many
records it holds, its last fingerprint, and whether the other laptops match.
The office's Chain check page lists the copies from this side.

**Tested, both ways:** with a clean chain the copy took all 26 records and said
so. With one mark changed straight inside the database, the copy refused it and
named the record — without ever being told anything was wrong.

## 2026-09-24 — The office keeps the register: batches and students

**Office sidebar** now has Home, Class requests, Chain check, then a list of
batches, then "Add a new batch".

**Add a new batch** — a name like 2026–27 and which semester it is in now.

**Inside a batch** — add a student (roll number, name, student ID, and the
parents' names), change any of those details on the spot, or remove someone
from the register with a reason.

A new student is automatically enrolled in every course up to the semester
their batch has reached, so their courses appear straight away. A roll number
is digits only, because it becomes their email: roll@std.cu.ac.bd.

**On the chain:** adding a batch, adding a student, changing a student, and
removing one. The parents' names are *not* written to the chain — it records
that a record was added or changed, not what is inside it. Removing a student
deletes their row and their sign-in, but anything already on the chain stays
there for good, with the reason for the removal beside it.

## 2026-09-23 — Class tests, CATM and the class chart

**Class tests tab.** The same grid shape as attendance: students down the side,
tests across the top. Type a number, or `A` for absent, or leave it blank.
Enter jumps to the next student. Nothing saves until you press "Save to the
chain", which first shows you the list of what is about to change. A mark that
is already in cannot be changed without a reason, and the review screen asks
for one on that line.

**Out-of.** Each test's out-of sits in its column header and can be edited
until that test's first mark is saved. After that it is fixed, because changing
it later would silently change everyone's percentage.

**CATM tab.** Pick a student and see it top to bottom: attendance percent,
attendance marks, each test with counted or dropped, the best-n rule, and the
total out of 21. A lab shows quiz and viva, practical and reports, attendance,
and the lab total instead.

**Class chart.** One chart, 0 to 100, across the term: the class average in
each test in maroon, and how much of the class was present in green.

**Teachers still never see final exam marks** — the rules refuse a final item,
and the teacher views leave finals out entirely.

## 2026-09-23 — Attendance: the register is one block

**The rule (contract.py).** A register is what a teacher signs on paper: the
whole class in one entry. `save_register` writes one `attendance_register`
block per class. It refuses a class that hasn't happened, a student who isn't
on the class list, a lab group that doesn't come that day, and a second
register for the same class. Changing a tick afterwards is
`correct_attendance`: its own block, with a reason the student can read, and it
records what the tick was before.

Space was the worry, and it isn't one: about 7,600 per-student ticks a term
would be 2.4 MB, and one block per class instead of one per student makes the
chain about 50 times shorter, which keeps the pages fast — every page replays
the chain to work its numbers out.

**The grid (teacher.html).** Students down the left in a sticky column, class
dates across the top. A cell cycles blank → present → absent → blank, and
nothing is written until you press Save on that date. "✓ all" fills a column.
A saved column turns read-only; clicking a saved cell asks for a reason and
writes a correction. Future dates are locked, and on a paired lab the group
that isn't due that day shows dashes.

**Worth knowing:** the seed only wrote attendance for the four demo students,
so on the nine already-saved classes the other 50 students show "–", meaning
they were never on that register.

## 2026-09-23 — All four roles can sign in, and four tabs at once

**What you see:** the landing page now has three doors — Student, Teacher and
Admin. Office and examiner both use Admin, and the server sends each to its own
page. Two new pages exist: `teacher.html` (her classes) and `office.html`
(approvals and a chain check).

**Signing in hands the page to a new tab.** After a sign-in with "Remember me"
unticked, a button appears: "Open my records in a new tab". You click it, the
new tab gets its own copy of the ticket, and the landing tab goes back to being
a plain sign-in form. That is how four roles stay open side by side on one
laptop. The button exists because a browser only allows a new tab during a real
click, not after a reply comes back from the server.

- Each page now reads *its own tab's* ticket first, and a remembered one only as
  a fallback, so the four tabs never fight over one sign-in.
- "Use this tab for another sign-in" lets go of the ticket here only.
  "Sign out" ends that ticket everywhere it was opened from here.

**Classes are approved on the chain.** A teacher asks for a class (a course plus
a session — there is no student count to type, it is counted from the class
list). The office approves or turns it down. Both the asking and the answer are
blocks, because who is allowed to enter marks is part of the record.

**New files:** `teacher.html`, `office.html`, `seed_staff.py` (add-only: it
creates the teacher and office demo accounts and never deletes anything).

**Demo logins:** student 24702045@std.cu.ac.bd / eee-demo-2026 · teacher
sabrina.demo@cu.ac.bd / teacher-demo-2026 · office office.demo@cu.ac.bd /
office-demo-2026 · examiner examiner.demo@cu.ac.bd / exam-demo-2026

## 2026-09-23 — The sidebar is a flat list again

**What you see:** The sidebar no longer has an expanding tree of all eight
semesters. It now shows: Home, a "SEMESTER n" label, Timetable, Courses, the
course codes for that semester, and Payment. You switch semesters from the
cards on the Home page, the same as before.

**Why:** The tree grew taller than the screen and was fiddly to use. The flat
list fits without scrolling.

**What changed in `app.html`:**
- `drawNav()` was rewritten to draw one flat list for the semester in
  `VIEW_SEM`, instead of a fold-out row for each of the eight semesters.
- `toggleSem()` is gone, and so are the `OPEN` and `COURSES_OPEN` variables
  that remembered what was unfolded. Nothing unfolds anymore.
- The CSS for the tree (`.nav .sub`, `.nav .sub.deep`, `.nav .semrow`,
  `.nav .caret`) was replaced by one rule, `.nav .code`, for the course-code
  buttons.
- The line under your name now reads "Semester 5 · Lab group B".

**A bug this also fixed:** the sidebar rows used the class name `semrow`, which
the Home page's semester-card strip also uses. The Home page style leaked into
the sidebar and gave every row its own tiny scrollbar arrows.

## 2026-09-22 — The sidebar keeps its colour and scrolls inside itself

**What you see:** With many items in the sidebar, the list now scrolls inside
the dark panel instead of spilling onto the cream page.

**Why:** The sidebar is exactly one screen tall (`height:100vh`). A taller list
had nowhere to go, so it overflowed.

**What changed in `app.html`:** the nav list got `min-height:0` (so it is
allowed to shrink) and `overflow-y:auto` (so it scrolls), plus 22px of space
above and below, because the curved cream corners of the selected tab stick out
that far and a scrolling box cuts off anything outside it.
