"""
What the office puts on the landing page: the pictures that scroll in
"Around the department", and the achievement cards (with a photo and a
link to the real post).

Uploaded pictures are saved with db.save_file, so online they are also
kept in Postgres and put back on disk after every Render restart.
"""

import hashlib
import json
import os
import datetime as dt

import clock

import db
from ledger import connect
from contract import Refused, MAX_UPLOAD

FOLDER = os.path.join("photos", "uploads")     # served as /photos/uploads/...
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp")


def init():
    """Older databases have no link column on achievements: add it once."""
    con = connect()
    try:
        con.execute("SELECT link FROM achievements LIMIT 1")
    except Exception:
        con.rollback()
        con.execute("ALTER TABLE achievements ADD COLUMN link TEXT")
        con.commit()
    # where each of the first real posts can be read in full. Only fills a
    # link that is still empty, so a link the office sets later always wins.
    for title, link in SOURCE_LINKS:
        con.execute("UPDATE achievements SET link=? WHERE title=? AND (link IS NULL OR link='')",
                    (link, title))
    # better pictures for the first posts: only where the picture is still empty or the
    # old poster, so a picture the office chose later always wins
    for title, old, new_image in SOURCE_IMAGES:
        con.execute("UPDATE achievements SET image=? WHERE title=? AND "
                    "(image IS NULL OR image='' OR image=?)", (new_image, title, old))
    con.commit()
    # news added from here, once: never again if the office has removed it
    # (its "achievement_add" stays on the chain, so it is not put back)
    new = []
    for title, detail, year, link, image in SEED_POSTS:
        there = con.execute("SELECT 1 FROM achievements WHERE title=?", (title,)).fetchone()
        added_before = con.execute(
            "SELECT 1 FROM blocks WHERE entry_type='achievement_add' AND payload LIKE ?",
            ('%"title":' + json.dumps(title) + '%',)).fetchone()
        if not there and not added_before:
            con.execute("INSERT INTO achievements (title, detail, year, image, added_by, link) "
                        "VALUES (?, ?, ?, ?, 'office:seed', ?)", (title, detail, year, image, link))
            new.append((title, year, link, image))
    con.commit()
    con.close()
    for title, year, link, image in new:
        _log("achievement_add", {"title": title, "year": year, "image": image, "link": link}, "seed")
    db.forget_tables()


SOURCE_IMAGES = [
    ("Symposium: Winter Symposium on Silicon Photonics and Nanofabrication", "",
     "photos/winter-symposium-2026.jpg"),
    ("Champions of VLSIthon 3.0", "photos/vlsithon3.png", "photos/vlsithon3-winners.jpg"),
]

SEED_POSTS = [
    ("Symposium: Winter Symposium on Silicon Photonics and Nanofabrication",
     "Organised by the Optica Student Chapter, University of Chittagong · 11 November 2026, "
     "auditorium of the Faculty of Marine Sciences and Fisheries, CU · about 150 students, "
     "researchers and teachers from six universities in Chittagong · talks on light on a chip, "
     "silicon photonics for biosensing, thin-film materials and nanofabrication, with hands-on "
     "tutorials on Ansys Lumerical INTERCONNECT, GPU-accelerated FDTD and Tidy3D · speakers "
     "included Sumit Majumder, Ariful Islam and Mohammad Shuhrawardy",
     2026,
     "https://www.facebook.com/ictcu/posts/1554550206708224/", "photos/winter-symposium-2026.jpg"),
    ("Award: Best Stall in the IT category, CUCSU National Research Festival 2026",
     "Students of the Department of EEE won the Best Stall award in the IT category "
     "at the CUCSU National Research Festival 2026",
     2026, "", "photos/cucsu-best-stall-2026.jpg"),
]


SOURCE_LINKS = [
    ("Champions of VLSIthon 3.0",
     "https://www.dhakatribune.com/feature/youth/419078/ulkasemi%E2%80%99s-vlsithon-3.0-ends-with-cu%E2%80%99s-%E2%80%98deviation%E2%80%99"),
    ("Alumnus: Dr. Hafizul Islam Chowdhury", "https://ece.charlotte.edu/?p=6101"),
    ('Seminar: "Integrated Photonics for Next-Generation Optical Communication and Sensing"',
     "https://www.facebook.com/IEEESBCU/"),
    ('Seminar: "Autonomous Biomedical Machines"', "https://www.facebook.com/IEEESBCU/"),
]


def _save_picture(filename, data):
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in IMAGE_TYPES:
        raise Refused("Only JPG, PNG and WEBP pictures can be uploaded.")
    if not data:
        raise Refused("That file is empty.")
    if len(data) > MAX_UPLOAD:
        raise Refused("The picture must be under 5 MB.")
    path = os.path.join(FOLDER, hashlib.sha256(data).hexdigest()[:16] + ext)
    db.save_file(path, data)
    return path.replace(os.sep, "/")


def _drop_picture(path):
    """Delete an uploaded picture, unless something else still uses it.
    Pictures that came with the site (photos/...) are never deleted."""
    if not path or not path.startswith(FOLDER.replace(os.sep, "/") + "/"):
        return
    con = connect()
    used = (con.execute("SELECT COUNT(*) FROM gallery WHERE image=?", (path,)).fetchone()[0]
            + con.execute("SELECT COUNT(*) FROM achievements WHERE image=?", (path,)).fetchone()[0])
    con.close()
    if not used:
        db.delete_file(path)


def _log(kind, payload, who):
    from ledger import add_entry
    add_entry(kind, payload, f"office:{who}")


# ---------------- Around the department ----------------
def gallery_list():
    con = connect()
    found = con.execute("SELECT id, image, caption FROM gallery ORDER BY id").fetchall()
    con.close()
    return [{"id": i, "image": img, "caption": cap or "",
             "missing": not os.path.exists(img)} for i, img, cap in found]


def gallery_add(who, filename, data, caption):
    path = _save_picture(filename, data)
    caption = (caption or "").strip()[:140]
    con = connect()
    con.execute("INSERT INTO gallery (image, caption) VALUES (?, ?)", (path, caption))
    con.commit()
    con.close()
    _log("gallery_add", {"image": path, "caption": caption}, who)
    return path


def gallery_remove(who, pic_id):
    con = connect()
    found = con.execute("SELECT image FROM gallery WHERE id=?", (pic_id,)).fetchone()
    if not found:
        con.close()
        raise Refused("That picture is not in the gallery.")
    con.execute("DELETE FROM gallery WHERE id=?", (pic_id,))
    con.commit()
    con.close()
    _drop_picture(found[0])
    _log("gallery_remove", {"id": pic_id, "image": found[0]}, who)


# ---------------- Achievements ----------------
def achievements_list():
    con = connect()
    found = con.execute("SELECT id, title, detail, year, image, link FROM achievements "
                        "ORDER BY year DESC, id DESC").fetchall()
    con.close()
    return [{"id": i, "title": t, "detail": d or "", "year": y, "image": img or "", "link": l or ""}
            for i, t, d, y, img, l in found]


def _clean_link(link):
    link = (link or "").strip()
    if link and not link.lower().startswith(("http://", "https://")):
        raise Refused("The link must start with http:// or https://")
    return link[:500]


def achievement_add(who, title, detail, year, link, filename=None, data=None):
    title = (title or "").strip()
    if not title:
        raise Refused("Give the achievement a title.")
    try:
        year = int(year or clock.today().year)
    except ValueError:
        raise Refused("The year must be a number, like 2026.")
    link = _clean_link(link)
    path = _save_picture(filename, data) if data else ""
    con = connect()
    con.execute("INSERT INTO achievements (title, detail, year, image, added_by, link) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (title[:200], (detail or "").strip()[:600], year, path, who, link))
    con.commit()
    con.close()
    _log("achievement_add", {"title": title, "year": year, "image": path, "link": link}, who)


def achievement_set_link(who, ach_id, link):
    link = _clean_link(link)
    con = connect()
    if not con.execute("SELECT 1 FROM achievements WHERE id=?", (ach_id,)).fetchone():
        con.close()
        raise Refused("That achievement is not on the list.")
    con.execute("UPDATE achievements SET link=? WHERE id=?", (link, ach_id))
    con.commit()
    con.close()
    _log("achievement_link", {"id": ach_id, "link": link}, who)


def achievement_remove(who, ach_id):
    con = connect()
    found = con.execute("SELECT title, image FROM achievements WHERE id=?", (ach_id,)).fetchone()
    if not found:
        con.close()
        raise Refused("That achievement is not on the list.")
    con.execute("DELETE FROM achievements WHERE id=?", (ach_id,))
    con.commit()
    con.close()
    _drop_picture(found[1])
    _log("achievement_remove", {"id": ach_id, "title": found[0]}, who)
