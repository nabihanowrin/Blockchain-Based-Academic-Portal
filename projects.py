"""
A student's own projects: editing them, and the pictures and PDFs on each one.

A project is self-reported, so it lives in ordinary tables, not on the chain.
Only each file's fingerprint (SHA-256) goes on the chain, the same as every
other upload, so a file that is later swapped on the server can be caught.

Only the student who owns a project can change it, add files to it or delete
it. Every function here takes the signed-in student's roll and checks it.

If a teacher had verified a project and the student then changes its title,
summary or year, the "verified" tag is taken off: the teacher confirmed the
old wording, not the new one. Adding or removing pictures keeps the tag.
"""

import datetime as dt
import hashlib
import os

import db
from ledger import connect, add_entry
from contract import Refused, check_project, MAX_UPLOAD, IMAGE_TYPES, DOC_TYPES

MAX_FILES = 8            # pictures + PDFs on one project


def init():
    con = connect()
    con.execute("""CREATE TABLE IF NOT EXISTS project_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, roll TEXT,
        name TEXT, path TEXT, kind TEXT, size INTEGER, added_at TEXT)""")
    con.commit()
    # a project made before this file existed may already have one picture
    # (projects.image). Give it a row here too, so it can be shown and removed.
    old = con.execute("SELECT id, roll, image FROM projects WHERE image IS NOT NULL AND image != ''").fetchall()
    for pid, roll, url in old:
        path = _path_of(url)
        if not path:
            continue
        there = con.execute("SELECT 1 FROM project_files WHERE project_id=? AND path=?", (pid, path)).fetchall()
        if not there:
            con.execute("INSERT INTO project_files (project_id, roll, name, path, kind, size, added_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (pid, roll, "picture" + os.path.splitext(path)[1], path, "image",
                         os.path.getsize(path) if os.path.isfile(path) else 0, _now()))
    con.commit()
    con.close()
    if hasattr(db, "forget_tables"):
        db.forget_tables()


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _url_of(path):
    return "/api/file?path=" + path.replace(os.sep, "/")


def _path_of(url):
    prefix = "/api/file?path="
    return url[len(prefix):] if url and url.startswith(prefix) else None


def _own(con, roll, project_id):
    """The project row, only if it belongs to this student."""
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        raise Refused("No such project.")
    found = con.execute("SELECT id, title, summary, year, image, verified_by FROM projects "
                        "WHERE id=? AND roll=?", (project_id, roll)).fetchall()
    if not found:
        raise Refused("No such project.")
    return found[0]


def files_of(roll):
    """{project_id: [files]} for one student, for the home page."""
    con = connect()
    out = {}
    for fid, pid, name, path, kind, size in con.execute(
            "SELECT id, project_id, name, path, kind, size FROM project_files "
            "WHERE roll=? ORDER BY id", (roll,)).fetchall():
        out.setdefault(pid, []).append({"id": fid, "name": name, "url": _url_of(path),
                                        "kind": kind, "size": size})
    con.close()
    return out


def edit(roll, project_id, title, summary, year):
    """Change the words of a project. Returns True if the verified tag came off."""
    title, summary, year = check_project(title, summary, year)
    con = connect()
    pid, old_title, old_summary, old_year, _, verified_by = _own(con, roll, project_id)
    changed = (title, summary, year) != (old_title, old_summary or "", old_year)
    unverified = bool(changed and verified_by)
    if unverified:
        con.execute("UPDATE projects SET title=?, summary=?, year=?, verified_by=NULL, verified_at=NULL "
                    "WHERE id=? AND roll=?", (title, summary, year, pid, roll))
    else:
        con.execute("UPDATE projects SET title=?, summary=?, year=? WHERE id=? AND roll=?",
                    (title, summary, year, pid, roll))
    con.commit()
    con.close()
    if unverified:
        add_entry("project_unverified", {"project_id": pid, "roll": roll,
                                         "why": "the student changed the project's text"}, f"student:{roll}")
    return unverified


def add_file(roll, project_id, filename, data):
    """Add one picture or PDF to a project. The first picture becomes the cover."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    if ext not in IMAGE_TYPES | DOC_TYPES:
        raise Refused("Only pictures (JPG, PNG, WEBP) and PDFs can be added to a project.")
    if not data:
        raise Refused("That file is empty.")
    if len(data) > MAX_UPLOAD:
        raise Refused("That file is over 5 MB.")

    con = connect()
    pid, _, _, _, cover, _ = _own(con, roll, project_id)
    count = con.execute("SELECT COUNT(*) FROM project_files WHERE project_id=?", (pid,)).fetchall()[0][0]
    if count >= MAX_FILES:
        con.close()
        raise Refused(f"A project can have up to {MAX_FILES} files. Remove one first.")
    con.close()

    digest = hashlib.sha256(data).hexdigest()
    path = os.path.join("uploads", roll, digest[:16] + ext)
    db.save_file(path, data)                 # on disk, and in Postgres when online
    kind = "pdf" if ext in DOC_TYPES else "image"
    name = os.path.basename(filename)[:120]

    con = connect()
    cur = con.cursor()
    cur.execute("INSERT INTO project_files (project_id, roll, name, path, kind, size, added_at) "
                "VALUES (?,?,?,?,?,?,?)", (pid, roll, name, path, kind, len(data), _now()))
    new_id = cur.lastrowid
    if kind == "image" and not cover:
        con.execute("UPDATE projects SET image=? WHERE id=? AND roll=?", (_url_of(path), pid, roll))
    con.commit()
    con.close()

    add_entry("upload", {"roll": roll, "kind": "project_file", "project_id": pid,
                         "file": _url_of(path), "sha256": digest, "size": len(data)}, f"student:{roll}")
    return new_id


def remove_file(roll, file_id):
    con = connect()
    found = con.execute("SELECT project_id, path FROM project_files WHERE id=? AND roll=?",
                        (file_id, roll)).fetchall()
    if not found:
        con.close()
        raise Refused("No such file.")
    pid, path = found[0]
    con.execute("DELETE FROM project_files WHERE id=? AND roll=?", (file_id, roll))
    # if that picture was the cover, the next picture (if any) becomes the cover
    cover = con.execute("SELECT image FROM projects WHERE id=?", (pid,)).fetchall()[0][0]
    if cover == _url_of(path):
        nxt = con.execute("SELECT path FROM project_files WHERE project_id=? AND kind='image' "
                          "ORDER BY id LIMIT 1", (pid,)).fetchall()
        con.execute("UPDATE projects SET image=? WHERE id=?", (_url_of(nxt[0][0]) if nxt else None, pid))
    still_used = con.execute("SELECT 1 FROM project_files WHERE path=? LIMIT 1", (path,)).fetchall() or \
                 con.execute("SELECT 1 FROM profile WHERE photo=? LIMIT 1", (_url_of(path),)).fetchall()
    con.commit()
    con.close()
    if not still_used:                       # the same picture may be used twice; keep it then
        db.delete_file(path)


def set_cover(roll, file_id):
    con = connect()
    found = con.execute("SELECT project_id, path, kind FROM project_files WHERE id=? AND roll=?",
                        (file_id, roll)).fetchall()
    if not found or found[0][2] != "image":
        con.close()
        raise Refused("Only a picture can be the cover.")
    pid, path, _ = found[0]
    con.execute("UPDATE projects SET image=? WHERE id=? AND roll=?", (_url_of(path), pid, roll))
    con.commit()
    con.close()


def delete(roll, project_id):
    """Delete a project and its files."""
    con = connect()
    pid = _own(con, roll, project_id)[0]
    ids = [i for (i,) in con.execute("SELECT id FROM project_files WHERE project_id=? AND roll=?",
                                     (pid, roll)).fetchall()]
    con.close()
    for fid in ids:
        remove_file(roll, fid)
    con = connect()
    con.execute("DELETE FROM projects WHERE id=? AND roll=?", (pid, roll))
    con.commit()
    con.close()
