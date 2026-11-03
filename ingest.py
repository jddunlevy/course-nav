"""Load one term of Banner sections into the database.

Input is the CSV written by C:\\dev\\ua-classes\\ua_classes.py.

    python ingest.py --csv C:\\dev\\ua-classes\\spring2027.csv --term 202710 --reset

Note on HTML entities: ua_classes.py now unescapes at the source, but older CSVs
(spring2027.csv included) still carry `&amp;`, which breaks the attribute split
because the entity itself ends in a semicolon. We unescape defensively on read.
That is safe here -- the file contains zero double-escaped values, so unescaping
once is idempotent.
"""

import argparse
import csv
import html
import re

import db

SPECIAL_TOPICS_ATTR = "Special Topics Course"

# D-27: a rotating-topic course whose description is the shared generic blurb
# cannot be ranked on phrase relevance. These are the catalog's tells.
GENERIC_DESC_PATTERNS = [
    r"\bmay be (taken|repeated)\b",
    r"\bselected (topics|problems|readings)\b",
    r"\bvaries? (by|with|each) (term|semester|topic|instructor)\b",
    r"\btopics? (vary|will vary)\b",
    r"\bdifferent topics\b",
]
GENERIC_DESC_RE = re.compile("|".join(GENERIC_DESC_PATTERNS), re.I)


def clean(v):
    return html.unescape(v).strip() if v else ""


def split_attributes(raw):
    """Banner joins attributes with '; '. Unescape FIRST -- see module docstring."""
    return [p.strip() for p in clean(raw).split(";") if p.strip()]


def to_num(v, cast=float):
    try:
        return cast(v)
    except (TypeError, ValueError):
        return None


def load(conn, csv_path, term):
    buckets = db.bucket_map(conn)
    courses = {}
    n_sections = 0
    n_attr = 0
    n_bucket_attr = 0
    n_special = 0

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("term") and row["term"] != term:
                continue
            subject = clean(row["subject"])
            number = clean(row["courseNumber"])
            if not subject or not number or not row.get("crn"):
                continue

            key = (subject, number)
            if key not in courses:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO course (subject, course_number, title)"
                    " VALUES (?, ?, ?)", (subject, number, clean(row["title"])))
                if cur.lastrowid:
                    courses[key] = cur.lastrowid
                else:
                    courses[key] = conn.execute(
                        "SELECT course_id FROM course WHERE subject = ? AND course_number = ?",
                        (subject, number)).fetchone()[0]

            attrs = split_attributes(row.get("attributes"))
            is_special = 1 if SPECIAL_TOPICS_ATTR in attrs else 0
            n_special += is_special

            cur = conn.execute("""
                INSERT OR IGNORE INTO course_offering
                    (course_id, term, crn, section, credits, days, begin_time,
                     end_time, building, room, schedule_type, instructional_method,
                     campus, part_of_term, instructors, max_enrollment, enrollment,
                     seats_available, open_section, section_text, is_special_topics)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                courses[key], term, clean(row["crn"]), clean(row["section"]),
                to_num(row.get("credits")), clean(row.get("days")),
                clean(row.get("beginTime")), clean(row.get("endTime")),
                clean(row.get("building")), clean(row.get("room")),
                clean(row.get("scheduleType")), clean(row.get("instructionalMethod")),
                clean(row.get("campus")), clean(row.get("partOfTerm")),
                clean(row.get("instructors")),
                to_num(row.get("maxEnrollment"), int), to_num(row.get("enrollment"), int),
                to_num(row.get("seatsAvailable"), int),
                1 if str(row.get("openSection")).lower() == "true" else 0,
                clean(row.get("sectionText")), is_special,
            ))
            if not cur.lastrowid:
                continue
            offering_id = cur.lastrowid
            n_sections += 1

            for a in attrs:
                bid = buckets.get(a)
                conn.execute(
                    "INSERT OR IGNORE INTO offering_attribute (offering_id, attribute, bucket_id)"
                    " VALUES (?, ?, ?)", (offering_id, a, bid))
                n_attr += 1
                if bid:
                    n_bucket_attr += 1

    conn.commit()
    return {
        "courses": len(courses), "sections": n_sections, "attributes": n_attr,
        "bucket_attributes": n_bucket_attr, "special_topics_sections": n_special,
    }


def mark_topic_uncertain(conn):
    """Set course.topic_uncertain per D-27.

    A course is topic-uncertain only if BOTH hold:
      1. at least one of its sections carries the Special Topics Course attribute
      2. its description is missing, or reads as the generic rotating blurb

    Condition 2 is what keeps the 136 Legends sections out: they carry the
    attribute but are a known First-Year Compass requirement, so once their real
    description is cached they rank normally.
    """
    rows = conn.execute("""
        SELECT c.course_id, c.description
        FROM course c
        WHERE EXISTS (SELECT 1 FROM course_offering o
                      WHERE o.course_id = c.course_id AND o.is_special_topics = 1)
    """).fetchall()
    flagged = 0
    for r in rows:
        desc = r["description"] or ""
        uncertain = 1 if (not desc.strip() or GENERIC_DESC_RE.search(desc)) else 0
        conn.execute("UPDATE course SET topic_uncertain = ? WHERE course_id = ?",
                     (uncertain, r["course_id"]))
        flagged += uncertain
    conn.commit()
    return {"special_topics_courses": len(rows), "topic_uncertain": flagged}


def main():
    ap = argparse.ArgumentParser(description="Load a Banner CSV into navigator.db")
    ap.add_argument("--csv", default=r"C:\dev\ua-classes\spring2027.csv")
    ap.add_argument("--term", default="202710")
    ap.add_argument("--reset", action="store_true", help="drop and rebuild the db")
    args = ap.parse_args()

    conn = db.create(drop=True) if args.reset else db.connect()
    stats = load(conn, args.csv, args.term)
    stats.update(mark_topic_uncertain(conn))
    for k, v in stats.items():
        print("{:26s} {}".format(k, v))


if __name__ == "__main__":
    main()
