# Notes

Plain-English notes on what changed and why. Newest at the top.

## 2026-11-23 09:25 — Softer yellow everywhere

From Sabrin's colour chat. The yellow is now a soft, faded light gold `#E5D3A1` (hover/deeper
`#D9C38E` / `#CDB57E`) instead of the panels' `#D6B06A` and the homepage's bright `#F1C45D`.
Changed in `theme.css`, the four panel pages, `landing.html` and `signin.html` (buttons, labels, the
line under headings, the current-semester tags).

## 2026-11-23 09:20 — Panels: charcoal sidebar, duller darker maroon

From Sabrin's colour chat, straight after the entry below.

- **Sidebar** on the student, teacher, office and examiner pages is now charcoal `#302B31`, not maroon.
- **Maroon** on those pages is now `#602933`: the homepage maroon `#7E2233` made a little duller
  and darker (hover `#4A2028`). The homepage and sign-in page keep `#7E2233`.

## 2026-11-23 09:15 — Student, teacher, office and examiner pages use the homepage colours

From Sabrin's colour chat. Only colours changed; layout is the same.

- **Maroon:** every maroon on the four panels (`#501315`, `#7A2A2D`, `#A4343F`, `#8A1E2E`) is now the
  homepage maroon `#7E2233`; the darker hover shade `#3B0D0F` is now the homepage's `#651B29`.
- **Light maroon tints:** pale rose backgrounds and lines now use the homepage's (`#F4E8EA`, `#F6E3E7`,
  `#EBC8CF`). The thin maroon-on-maroon lines in the sidebar are now soft white lines.
- **Dark / near-black:** all near-black text (`#1C1A19`, `#1D181C`) and black shadows are now the
  homepage charcoal `#302B31`. The printed fee slip in `app.html` stays black ink on purpose.
- **Fonts:** already Plus Jakarta Sans through `theme.css`; headings now use the homepage's tighter
  letter spacing (-0.025em). Gold `#D6B06A` and the cream page background are unchanged.
- Files: `theme.css` (Najah's area — the header note says what changed), `app.html`, `teacher.html`,
  `office.html`, `exam.html`.

## 2026-11-23 07:30 — Homepage: role cards, news beside the photo, maroon back

From Sabrin's homepage chat, on top of b7ec38b.

- **Maroon:** back to `#7E2233` (the colour the site had before `#500000`), homepage and sign-in page.
- **News:** the section title now sits beside the photo, with the post under it; smaller text.
  Changes every 3 seconds while it's on screen (no longer pauses under the mouse).
- **"What this website gives you":** a maroon panel (fading lighter) on the left; on the right
  a stack of photo cards (Students, Teachers, Office, Examiners) that swipe or drag to the back,
  with ← → buttons, and move on by themselves every 3.5 s. New photos: `photos/what-*.jpg`.
- **Faculty:** five cards across on a laptop; photos a little darker.
- **VLSIthon:** the photo on the stage again (`site_content.py`).
- **Section colours:** news: white behind the photo, charcoal behind the writing (on phones, photo on white above, writing on charcoal below; yellow label stays, on charcoal); "Around the department"
  is white (lab names maroon, text dark); "What this website gives you" is maroon on the text half and
  white on the card half (sharp edge just right of the text; on phones maroon on top, white below), with
  a bigger heading and bigger, more spaced text. The cards stay white.
- **Fonts and spacing after BRAC University's site:** Plus Jakarta Sans (Google Fonts) on section
  titles, news, role cards, faculty cards and the numbers; slightly stronger text; less empty space
  between sections. Top bar, hero and footer keep their fonts for now.
- **Centred headings and more room:** section headings and their short intro lines are centred (news
  title, Around the department, What this website gives you, Faculty); long text, lists and cards stay
  left. About 2.5 cm of space on the left and right (`--gut`, up to 104px) and above each section
  (88px) on a laptop; less on phones. Hero, numbers row, Alumni and footer layout unchanged.
- **Same gap on both sides:** in "What this website gives you" the maroon ends exactly as far to the
  right of the text as the text starts from the left edge; the paragraph is justified so both edges are
  straight. In the news, the photo and the writing each have the same gap on their left and right.
- **Other pages get the same font:** `theme.css` now loads Plus Jakarta Sans and uses it for the
  student, teacher, office and examiner pages (body text a bit heavier, headings bold); Arial stays as
  the fallback. `signin.html`'s form side uses it too. (`theme.css` is Najah's area — she has been told
  in the change log.) `alumni.html` is unchanged.

## 2026-11-23 — Groq fixed (it was blocked by name), Groq goes first, 4 models

What you saw: the first question was answered, the second wasn't. The log showed
Gemini "high demand" (503) on both Gemini models and Groq "HTTP 403: error code: 1010".
Why: 1010 is Cloudflare (Groq's front door) refusing requests that introduce
themselves as "Python-urllib", Python's default name. Our server never said who
it was, so Groq turned us away before even reading the key.
What changed (`assistant.py`):
- Every request now sends `User-Agent: EEE-Records/1.0 (+https://eeerecords.onrender.com)`.
- Groq is tried FIRST (it is fast, and Gemini has been overloaded). New setting
  `AI_ORDER` ("groq,gemini" default, or "gemini,groq").
- Groq has a second model too (`GROQ_BACKUP_MODEL`, default `openai/gpt-oss-20b`).
  Chain now: Groq 120b → Groq 20b → Gemini main (again if busy) → Gemini Flash-Lite.
- Tests: the fake AI refuses Python's default name, so this can't come back
  unnoticed; new checks for Groq's second model and the Groq-first order.

## 2026-11-23 — The assistant has backups: Gemini → Gemini Flash-Lite → Groq

What you saw: "The assistant couldn't be reached just now (TimeoutError)". The
Render log showed Google's free Gemini model saying HTTP 503 "high demand", and
then timing out.
Why: we depended on ONE free model. When it was busy, the student got nothing.
What changed (`assistant.py`):
- The server now tries, in order: the main Gemini model (asked a second time if
  Google says "busy"), then Gemini's lighter model `gemini-3.1-flash-lite`, then
  Groq (a different company, free plan). The first real answer goes to the
  student. Only if all fail do they see "busy, try again in a minute".
- Each AI gets 15 seconds (`AI_WAIT_SECONDS`), not 60.
- A question only counts towards the student's 30-a-day limit if it was answered.
- Every failure is logged as `[assistant] <which AI> failed: ...`.
- New settings in Render: `GROQ_API_KEY` (needed for the Groq backup),
  optional `AI_BACKUP_MODEL`, `GROQ_MODEL`, `AI_WAIT_SECONDS`.
- New tests (`tests/test_assistant_backup.py`) run a fake Gemini and a fake Groq
  and check each case: busy, too slow, empty answer, all down, Groq key only.

## 2026-11-23 — The assistant says WHY it failed instead of "Something went wrong"

What you saw: every question got "Something went wrong. Please try again."
Why: that message only appeared when the page got back something that was not
our JSON answer (for example Render's own error page, or a dropped connection),
so it hid the real reason.
What changed:
- `app.html`: the chat now reads the server's status. If the answer isn't JSON
  it says "The server sent back an error page (502)…" with the number; if the
  internet is down it says that.
- `assistant.py`: any failure talking to Google (not only "can't connect") is
  caught, written to the Render log as `[assistant] could not get an answer from
  Gemini: ...`, and shown to the student as a plain sentence.
- `server.py`: if a connection drops while answering, it is logged and the page
  still gets a JSON answer.

## 2026-11-23 — The assistant knows the department, not just the routine

Besides the student's own routine and class tests, the assistant is now given
the department's PUBLIC information (`assistant.about_department()`): the
address, phone, website, the chairman and his email, the academic office's email
(from the Email settings page), every teacher with designation, email, study
leave and official CU profile link, how each fee is paid (exam fee online via
Sonali Bank; Development and Somitee funds at the office with the receipt
form), the complaint box, how to object to a mark, password reset and account
deletion, and the alumni stories (name, role, field, batch, link).

New rules for it: help with the day and week, procedures (who to contact, where
to go, how to pay) and research contacts (teachers for a thesis, alumni in a
field). Never invent an email, phone number, research interest or alumni
contact; if research interests aren't listed (they aren't yet), give the
teachers' official profile links instead of guessing. It's not a tutor: course
content gets a line or two and a pointer to the teacher or Resources.

Still no marks, GPA, attendance or parents' names. The panel's guide and example
questions changed to match. Check 32.

**To check:** Dr. Mohammad Arif Iftakher Mahmood's email in `faculty.py`
(arif.iftakher@gmail.com) was a guess; the assistant now gives it out.
**Later:** when Sabrin's teacher profiles have research interests, add them to
`about_department()` so the assistant can match teachers to thesis topics.

## 2026-11-23 — The AI panel shows what it can and can't do

Under the welcome message the panel lists what the assistant can help with
(routine, rooms, labs, upcoming class tests, who teaches what, planning the
week, explaining a topic) and what it can't (marks/GPA/attendance, changing
anything, anyone else's information, remembering the chat), says English or
Bangla both work, and has four example questions that send when tapped
(`askTry` in `app.html`).

## 2026-11-23 — The AI button: an oval "Ask our AI?" and a panel on the right

The button is now an oval with a soft shadow at the bottom right, saying
"✦ Ask our AI?". It always shows. Clicking it slides a full-height chat panel
in from the right, starting with "Hi! What can I help you with?"; × or Esc
closes it. If the AI key isn't in Render yet, the panel says so. The oval is
the one deliberate exception to theme.css's square corners (`#askBtn` in
`app.html`).

## 2026-11-22 — Study assistant (AI) on the student page

**What you see:** an **Ask** button at the bottom right of the student page
(only when the assistant is switched on). It opens a chat: "What's my next
class test?", "Which room is my Thursday lab?", "Explain Fourier series simply".

**How it works:** the student's message goes to our server
(`/api/assistant`), which checks it's a signed-in student, adds THAT student's
own timetable, courses, teachers and upcoming class tests, and sends it to
Google's Gemini AI. The answer comes back into the chat. The API key stays on
the server (Render), never in the browser or on GitHub.

**What the AI is given:** first name, semester, lab group, this semester's
courses and teachers, the weekly routine, upcoming class tests, today's date.
**Not:** marks, GPA, attendance, parents' names, anyone else's data. (Gemini's
free tier may use what it's sent to improve Google's products, so nothing more
personal than a timetable goes there.) It can only talk; it can't change any
record. The conversation isn't stored anywhere.

**Limits:** 30 questions per student per day (`AI_DAILY_LIMIT`), 800 characters
per question; the last 8 messages are sent along so it remembers the
conversation.

**Switching it on (Render → Environment):** `GEMINI_API_KEY` = a key from
Google AI Studio. Optional: `AI_MODEL` (default `gemini-3.8-flash`).

**Files:** `assistant.py` (new, explained at the top), `server.py`
(`/api/assistant`, `/api/me` says if it's on), `app.html` (the chat box at the
bottom of the file). Tests: checks 30 and 31 (a stand-in assistant, `AI_FAKE=1`,
so no real AI is called).

## 2026-11-22 — Nightly backups to Google Drive

**What happens:** every night at 3:13 AM (Bangladesh), GitHub makes a full copy
of the live database (every table: records, the chain, accounts, uploaded
files) and saves it to the folder **"EEE Records backups"** in the project
Google Drive. Copies older than 30 days are deleted, but the newest 7 always
stay. The copy is checked before it is uploaded.

**Files:** `scripts/backup.py` (the job, explained at the top) and
`.github/workflows/backup.yml` (when it runs). Run it by hand: GitHub →
Actions → "Nightly database backup" → Run workflow.

**Settings (GitHub → Settings → Secrets and variables → Actions):**
`BACKUP_DATABASE_URL` (same as `DATABASE_URL` on Render), `GDRIVE_CLIENT_ID`,
`GDRIVE_CLIENT_SECRET` (same as the Gmail ones), `GDRIVE_REFRESH_TOKEN` (OAuth
Playground, scope `drive.file`: the job can only see files it made itself).
Until they are set, the job does nothing and says so.

**Putting a backup back** (needs PostgreSQL's tools): download the `.dump`
file from the Drive, then
`pg_restore --clean --if-exists --no-owner --dbname "<database address>" <file>.dump`.
Tested: a copy put back into an empty database had the same 96 blocks and a
valid chain. If pg_restore complains about `transaction_timeout`, ignore it:
newer tools add that setting and an older database skips it; the rest is
restored. Afterwards, open the site and run the chain check.

**Test:** `tests/test_backup.py` runs the job against a stand-in for Google
Drive and checks the copy restores with a valid chain (in the Postgres job on
GitHub).

## 2026-11-22 — Security round 2, and Delete my account

**1. The site stays up when the database is down.** (What happened this
morning when Supabase paused.) The server now opens anyway: pages show "The
records are not reachable right now" and try again every 30 seconds, the API
answers 503, and the moment the database is back the site works normally by
itself. If something unexpected goes wrong while answering, the visitor gets a
plain message and the error goes to the server log, never to the screen.
(`server.py`: `prepare_database`, `keep_trying_database`, `guarded`.)

**2. Keep the database awake.** `.github/workflows/keep-awake.yml` visits the
live site every 3 days, so Supabase never sees a quiet week. GitHub switches
scheduled jobs off after 60 days without commits; it emails the owner, and
"Enable" on the Actions tab turns it back on.

**3. Many people at once.** The server answers each visitor in their own thread
(`ThreadingHTTPServer`), with at most 8 doing work at once (`MAX_AT_ONCE`) to
protect the free database, and room for 128 waiting to be let in. Blocks are
written one at a time (`ledger._WRITE_LOCK`), so two saves at the same moment
can never get the same block number. SQLite waits for another writer instead of
failing.

**4. Pressing a button twice.** The same complaint within 10 minutes is refused;
saving a mark that is already that mark is refused (no duplicate correction).

**5. Codes can't flood an inbox.** At most 5 codes an hour to one address and
15 an hour from one device, for registration, staff sign-up, password reset
and the Email settings page (`auth.limit_codes`, new table `code_requests`).

**6. The chain check button.** However often anyone presses it, the full check
runs at most once a minute; in between, everyone gets the latest result. A new
block or the insider-edit demo makes the next press check for real.

**7. Delete my account** (bottom of the student home page). Needs the
password. Deletes the sign-in only: marks, attendance and their history belong
to the roll number, so they stay with the teacher and on the chain. The
deletion is a block on the chain, the student is emailed, and registering again
with the same email brings everything back. Staff accounts can't be deleted
here. (`auth.delete_account`, `/api/account/delete`, `app.html`.)

**Tests:** 17b, 27, 28, 29 and the database-down check are new; 11 and 24 check
double presses. 35 checks, on SQLite and Postgres.

## 2026-11-22 — The loading screen plays on every move between the homepage and an account

**What you see:** Nabiha's logo loading screen now plays:
- after signing in, on the homepage, before the account page opens (as before);
- when the account is opened **in a new tab** (no "Remember me"): it plays in
  the new tab first, then fades into the account page;
- when **signing out** of any account page: it plays first, then the homepage
  opens.

**Why it was missing:** the loading screen only existed inside `landing.html`.
Sign-ins without "Remember me" open the account in a new tab, and that page had
no loading screen; signing out also went straight to the homepage.

**What changed:**
- `loader.js` (new): the loading screen moved out of `landing.html` unchanged
  (same look, same animation), so every page can load it with
  `<script src="loader.js"></script>`. It also gives `eeeGo(url)`: play the
  screen, then go to url. One line was added: it stops the previous animation
  loop before playing again, because a page can now play it twice (arriving in
  a new tab, then signing out).
- `landing.html`: loads `loader.js`; "Open in a new tab" adds `#intro` to the
  address so the new tab plays it.
- `app.html`, `teacher.html`, `office.html`, `exam.html`: load `loader.js`;
  signing out uses `eeeGo('landing.html#enter')`.
- `server.py`: `/loader.js` added to the files a browser may download.
- `tests/test_site.py`: check 26.

**Not covered:** the browser's own Back button. A page can't play anything
before the browser leaves it that way.

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
