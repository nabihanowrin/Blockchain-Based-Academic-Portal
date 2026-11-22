"""
Alumni stories on the homepage: former students of the department and what
they do now. The office adds and removes them on its "Alumni stories" page.

Each story: the person's name, a one-line headline, their batch or degree
years, a short story, a date, an optional link to the source (a profile page,
a news report) and an optional photo. Every add and remove is a block on the
chain. Only real, checkable stories belong here, with the source linked.
"""

import datetime as dt

from ledger import connect, add_entry
from contract import Refused
import site_content


def init():
    con = connect()
    con.execute("""CREATE TABLE IF NOT EXISTS alumni_stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, headline TEXT, batch TEXT,
        story TEXT, story_date TEXT, link TEXT, image TEXT, added_by TEXT, added_at TEXT, field TEXT)""")
    con.commit()
    con.close()
    _seed()


# where a story's person works now: the "topics" row on the homepage filters by these
FIELDS = ("academia", "industry", "research", "entrepreneurship", "government")


# the first stories, from each person's own LinkedIn profile (screenshots sent by
# Sabrin, 22 Nov 2026). Added once; if the office removes one, it is not put back.
SEED = [
    {"name": "Jannatul Naima",
     "headline": "Lecturer, Department of Computer and Communication Engineering, International Islamic University Chittagong (IIUC)",
     "batch": "B.Sc. and M.Sc. in EEE, University of Chittagong", "field": "academia",
     "story": "Her research is on semiconductor devices and 3-D MMIC technology: GaAs, microwave and "
              "mm-wave frequencies, HEMT and pHEMT devices, and transmission lines in MMICs. She received "
              "the ICT Fellowship from the ICT Division of the Government of Bangladesh for her Master's "
              "thesis, and the UGC Merit Scholarship for her undergraduate results."},
    {"name": "Dr. Hafizul Islam Chowdhury",
     "headline": "Assistant Professor, Electrical and Computer Engineering, UNC Charlotte",
     "batch": "B.Sc. 2017 and M.Sc. 2019 in EEE, University of Chittagong", "field": "academia",
     "story": "After his B.Sc. and M.Sc. here, he earned his Ph.D. at the University of Central Florida "
              "in 2024 and stayed there as a postdoctoral fellow, before joining UNC Charlotte. His "
              "research covers computer architecture, secure processors, AI/ML and hardware security.",
     "link": "https://ece.charlotte.edu/?p=6101"},
    {"name": "Momshad Dinury",
     "headline": "Software Engineer, Brain Station 23",
     "batch": "EEE, University of Chittagong", "field": "industry",
     "story": "A software engineer focused on Flutter and mobile development, and a contributor to "
              "open-source projects. He leads the Flutter Bangladesh community, organising events and "
              "mentoring developers."},
]


def _seed():
    import json
    con = connect()
    todo = []
    for s in SEED:
        there = con.execute("SELECT 1 FROM alumni_stories WHERE name=?", (s["name"],)).fetchone()
        before = con.execute("SELECT 1 FROM blocks WHERE entry_type IN ('alumni_add','alumni_remove') "
                             "AND payload LIKE ?", ('%"name":' + json.dumps(s["name"]) + '%',)).fetchone()
        if not there and not before:
            todo.append(s)
    con.close()
    for s in todo:
        add("seed", s["name"], s["headline"], s["batch"], s["story"], "2026-11-22", s.get("link", ""),
            field=s.get("field", ""))


def listing():
    con = connect()
    found = con.execute("SELECT id, name, headline, batch, story, story_date, link, image, field "
                        "FROM alumni_stories ORDER BY story_date DESC, id DESC").fetchall()
    con.close()
    return [{"id": i, "name": n, "headline": h or "", "batch": b or "", "story": s or "",
             "date": d or "", "link": l or "", "image": img or "", "field": f or ""}
            for i, n, h, b, s, d, l, img, f in found]


def _clean_date(text):
    text = (text or "").strip()
    if not text:
        return dt.date.today().isoformat()
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError:
        raise Refused("The date must look like 2026-11-22.")


def add(who, name, headline, batch, story, story_date, link, filename=None, data=None, field=""):
    name = (name or "").strip()
    if not name:
        raise Refused("Give the alumnus or alumna's name.")
    headline = (headline or "").strip()
    if not headline:
        raise Refused("Give the story a headline, e.g. their current position.")
    link = site_content._clean_link(link)
    field = (field or "").strip().lower()
    if field and field not in FIELDS:
        raise Refused("Choose where they work now from the list.")
    story_date = _clean_date(story_date)
    path = site_content._save_picture(filename, data) if data else ""
    con = connect()
    con.execute("INSERT INTO alumni_stories (name, headline, batch, story, story_date, link, image, "
                "added_by, added_at, field) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name[:120], headline[:200], (batch or "").strip()[:80], (story or "").strip()[:1200],
                 story_date, link, path, who, dt.datetime.now(dt.timezone.utc).isoformat(), field))
    con.commit()
    con.close()
    add_entry("alumni_add", {"name": name, "headline": headline, "date": story_date,
                             "image": path, "link": link}, f"office:{who}")


def remove(who, story_id):
    con = connect()
    found = con.execute("SELECT name, image FROM alumni_stories WHERE id=?", (story_id,)).fetchone()
    if not found:
        con.close()
        raise Refused("That story is not on the list.")
    con.execute("DELETE FROM alumni_stories WHERE id=?", (story_id,))
    con.commit()
    con.close()
    site_content._drop_picture(found[1])
    add_entry("alumni_remove", {"id": story_id, "name": found[0]}, f"office:{who}")
