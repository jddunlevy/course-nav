"""SQLite access for the Course Navigator.

One module, one connection helper, and the queries the views need. No ORM:
the schema is the deliverable and it should stay readable as SQL.
"""

import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "navigator.db")
SCHEMA = os.path.join(HERE, "schema.sql")
REFERENCE = os.path.join(HERE, "reference_data.sql")


def connect(path=DB_PATH, timeout=10.0):
    conn = sqlite3.connect(path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Make a writer wait for the lock rather than raise immediately. Without
    # this, a search run during descriptions.py dies with "database is locked".
    # Journal mode is set once in create(); switching it needs an exclusive
    # lock, so it cannot be done from an ordinary connection.
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def create(path=DB_PATH, drop=False):
    """Build an empty database with reference data loaded."""
    if drop and os.path.exists(path):
        os.remove(path)
    conn = connect(path)
    # WAL lets readers keep working while a writer holds the lock -- e.g. a
    # search during a descriptions.py run. Set once, at creation; it persists.
    conn.execute("PRAGMA journal_mode = WAL")
    with open(SCHEMA, encoding="utf-8") as f:
        conn.executescript(f.read())
    with open(REFERENCE, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    return conn


def bucket_map(conn):
    """Banner attribute description -> bucket_id, for the 12 allowlisted only."""
    return {r["banner_attribute"]: r["bucket_id"]
            for r in conn.execute("SELECT banner_attribute, bucket_id FROM gen_ed_bucket")}


def outstanding_buckets(conn, student_id):
    """Buckets the student still needs, with hours remaining.

    A requirement is satisfied by hours anywhere in its bucket union (D-28), so
    remaining hours are computed per requirement and then attributed to every
    bucket in that union. A section tagged with any of those buckets can close it.

    The must-include clauses (one Literature, one History) are tracked separately:
    a bucket stays outstanding while its own min_hours is unmet even if the pool
    total is already satisfied.
    """
    rows = conn.execute("""
        SELECT r.requirement_id, r.code, r.name, r.hours_needed, r.min_courses,
               r.lab_hours_needed,
               -- DISTINCT matters: a course carrying two buckets from the SAME
               -- requirement's union (SPA 101 is both World Language and
               -- Humanities) would otherwise have its credits counted twice and
               -- overstate progress -- marking a requirement satisfied and
               -- hiding a course the student still needs.
               COALESCE((
                   SELECT SUM(credits) FROM (
                       SELECT DISTINCT cc.completed_id, cc.credits
                       FROM completed_course cc
                       JOIN completed_course_bucket ccb
                            ON ccb.completed_id = cc.completed_id
                       JOIN requirement_bucket rb2 ON rb2.bucket_id = ccb.bucket_id
                       WHERE cc.student_id = ?
                         AND rb2.requirement_id = r.requirement_id
                   )
               ), 0) AS hours_done
        FROM requirement r
        WHERE r.rule_kind = 'bucket'
        ORDER BY r.system, r.code
    """, (student_id,)).fetchall()

    out = []
    for r in rows:
        needed = r["hours_needed"]
        done = r["hours_done"] or 0
        if needed is not None:
            remaining = max(needed - done, 0)
            satisfied = remaining == 0
        else:
            satisfied = done > 0
            remaining = 0 if satisfied else (r["min_courses"] or 1) * 3

        buckets = conn.execute("""
            SELECT b.bucket_id, b.code, b.name, rb.is_must_include, rb.min_hours,
                   COALESCE((
                       SELECT SUM(cc.credits)
                       FROM completed_course cc
                       JOIN completed_course_bucket ccb ON ccb.completed_id = cc.completed_id
                       WHERE cc.student_id = ? AND ccb.bucket_id = b.bucket_id
                   ), 0) AS bucket_hours_done
            FROM requirement_bucket rb
            JOIN gen_ed_bucket b ON b.bucket_id = rb.bucket_id
            WHERE rb.requirement_id = ?
        """, (student_id, r["requirement_id"])).fetchall()

        open_buckets = []
        for b in buckets:
            must_unmet = (b["is_must_include"]
                          and (b["bucket_hours_done"] or 0) < (b["min_hours"] or 0))
            if not satisfied or must_unmet:
                open_buckets.append({
                    "bucket_id": b["bucket_id"],
                    "code": b["code"],
                    "name": b["name"],
                    "must_include": bool(b["is_must_include"]),
                    "must_unmet": bool(must_unmet),
                })

        out.append({
            "requirement_id": r["requirement_id"],
            "code": r["code"],
            "name": r["name"],
            "hours_needed": needed,
            "hours_done": done,
            "hours_remaining": remaining,
            "lab_hours_needed": r["lab_hours_needed"],
            "satisfied": satisfied and not any(b["must_unmet"] for b in open_buckets),
            "buckets": open_buckets,
        })
    return out


def numeric_progress(conn, student_id):
    """Hours-total requirements. Displayed only; never ranked on."""
    rows = conn.execute(
        "SELECT * FROM requirement WHERE rule_kind = 'numeric' ORDER BY code").fetchall()
    out = []
    for r in rows:
        if r["min_course_level"]:
            done = conn.execute("""
                SELECT COALESCE(SUM(credits), 0) FROM completed_course
                WHERE student_id = ?
                  AND CAST(REPLACE(course_number, '-', '') AS INTEGER) >= ?
            """, (student_id, r["min_course_level"])).fetchone()[0]
        else:
            done = conn.execute(
                "SELECT COALESCE(SUM(credits), 0) FROM completed_course WHERE student_id = ?",
                (student_id,)).fetchone()[0]
        out.append({
            "code": r["code"], "name": r["name"],
            "hours_needed": r["hours_needed"], "hours_done": done,
            "note": r["note"],
            # depth-study rules need a depth-study flag we do not collect in v1
            "approximate": r["code"].startswith("NC_"),
        })
    return out


def offerings_for_term(conn, term):
    """Every offered section with its text and its allowlisted buckets."""
    rows = conn.execute("""
        SELECT o.offering_id, o.crn, o.term, o.section, o.credits, o.days,
               o.begin_time, o.end_time, o.schedule_type, o.instructors,
               o.seats_available, o.open_section, o.is_special_topics,
               o.section_text,
               c.subject, c.course_number, c.title, c.description,
               c.topic_uncertain
        FROM course_offering o
        JOIN course c ON c.course_id = o.course_id
        WHERE o.term = ?
    """, (term,)).fetchall()

    buckets = {}
    for r in conn.execute("""
        SELECT oa.offering_id, b.bucket_id, b.code, b.name
        FROM offering_attribute oa
        JOIN gen_ed_bucket b ON b.bucket_id = oa.bucket_id
        WHERE oa.bucket_id IS NOT NULL
    """):
        buckets.setdefault(r["offering_id"], []).append(
            {"bucket_id": r["bucket_id"], "code": r["code"], "name": r["name"]})

    out = []
    for r in rows:
        d = dict(r)
        d["buckets"] = buckets.get(r["offering_id"], [])
        out.append(d)
    return out


def get_student(conn, student_id):
    return conn.execute("""
        SELECT s.*, a.name AS advisor_name
        FROM student s LEFT JOIN advisor a ON a.advisor_id = s.advisor_id
        WHERE s.student_id = ?
    """, (student_id,)).fetchone()


def advisees(conn, advisor_id):
    return conn.execute(
        "SELECT * FROM student WHERE advisor_id = ? ORDER BY name",
        (advisor_id,)).fetchall()


def save_search(conn, student_id, actor_user_id, term, phrase, results):
    """Persist one search and its ranked results."""
    cur = conn.execute(
        "INSERT INTO search_request (student_id, actor_user_id, term, phrase)"
        " VALUES (?, ?, ?, ?)",
        (student_id, actor_user_id, term, phrase))
    request_id = cur.lastrowid
    for i, r in enumerate(results, 1):
        cur = conn.execute("""
            INSERT INTO recommendation
                (request_id, offering_id, rank, score, bucket_score,
                 relevance_score, flag, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (request_id, r["offering_id"], i, r["score"], r["bucket_score"],
              r["relevance_score"], r["flag"], r["reason"]))
        rec_id = cur.lastrowid
        for b in r["buckets_closed"]:
            conn.execute(
                "INSERT INTO recommendation_bucket (recommendation_id, bucket_id)"
                " VALUES (?, ?)", (rec_id, b["bucket_id"]))
    conn.commit()
    return request_id
