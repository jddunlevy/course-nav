"""Fetch course descriptions from Banner and cache them in the database.

Verified live on 2026-11-02: POST /searchResults/getCourseDescription with
`term` and `courseReferenceNumber`, after start_session(), returns an HTML
fragment with the catalog description. 5/5 test CRNs returned HTTP 200 with
real prose (162-628 chars). This closes the handoff's open item.

Descriptions are COURSE level, not section level -- every AAST 395 section
returns the same blurb -- so we fetch once per subject+number using any one of
its CRNs. 3,324 unique courses in spring 2027, roughly 25 minutes at the
0.3s pause. Resumable: already-cached courses are skipped.

    python descriptions.py --from-csv                   # load the cache that ships in data/
    python descriptions.py --term 202710                # re-crawl Banner (~25 min)
    python descriptions.py --term 202710 --limit 50     # sample first

Crawling needs the Banner scraper (`ua_classes.py`, a separate project) on the
path; loading from CSV does not, which is why the cache ships in `data/`.
"""

import argparse
import csv
import html
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import db

DEFAULT_DESC_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "data", "course-descriptions.csv")
SCRAPER_PATH = r"C:\dev\ua-classes"

TAG_RE = re.compile(r"(?s)<[^>]+>")
SCRIPT_RE = re.compile(r"(?is)<(script|style).*?</\1>")
WS_RE = re.compile(r"\s+")


def strip_html(s):
    s = SCRIPT_RE.sub(" ", s)
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)          # Banner escapes these too (&rsquo;, &amp;)
    return WS_RE.sub(" ", s).strip()


def fetch_one(opener, term, crn):
    body = urllib.parse.urlencode({
        "term": term, "courseReferenceNumber": crn}).encode()
    req = urllib.request.Request(
        ua.BASE + "/searchResults/getCourseDescription", data=body)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    with opener.open(req, timeout=60) as r:
        return strip_html(r.read().decode("utf-8", "replace"))


def run(conn, term, limit=None, pause=0.3):
    rows = conn.execute("""
        SELECT c.course_id, c.subject, c.course_number, MIN(o.crn) AS crn
        FROM course c
        JOIN course_offering o ON o.course_id = c.course_id AND o.term = ?
        WHERE c.description IS NULL OR c.description = ''
        GROUP BY c.course_id
        ORDER BY c.subject, c.course_number
    """, (term,)).fetchall()
    if limit:
        rows = rows[:limit]

    print("{} courses need a description".format(len(rows)), file=sys.stderr)

    # Imported here, not at module scope: loading the shipped CSV must work on a
    # machine that has no scraper checkout.
    sys.path.insert(0, SCRAPER_PATH)
    import ua_classes as ua

    opener = ua.make_opener()
    ua.start_session(opener, term)

    ok = empty = failed = 0
    for i, r in enumerate(rows, 1):
        try:
            text = fetch_one(opener, term, r["crn"])
        except Exception as e:
            failed += 1
            print("  [{}/{}] {} {} FAILED {}".format(
                i, len(rows), r["subject"], r["course_number"], e), file=sys.stderr)
            time.sleep(pause)
            continue
        if text:
            ok += 1
        else:
            empty += 1
        conn.execute(
            "UPDATE course SET description = ?,"
            " description_fetched_at = datetime('now') WHERE course_id = ?",
            (text, r["course_id"]))
        if i % 50 == 0:
            conn.commit()
            print("  [{}/{}] cached (ok {} empty {} failed {})".format(
                i, len(rows), ok, empty, failed), file=sys.stderr)
        time.sleep(pause)

    conn.commit()
    print("\nok {}  empty {}  failed {}".format(ok, empty, failed), file=sys.stderr)
    return {"ok": ok, "empty": empty, "failed": failed}


def load_csv(conn, path):
    """Load a previously dumped description cache. No network, no scraper."""
    loaded = missing = 0
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cur = conn.execute("""
                UPDATE course SET description = ?, description_fetched_at = ?
                WHERE subject = ? AND course_number = ?
            """, (row["description"], "from-csv",
                  row["subject"], row["course_number"]))
            if cur.rowcount:
                loaded += 1
            else:
                missing += 1
    conn.commit()
    print("loaded {} descriptions, {} not in this term's catalog".format(loaded, missing),
          file=sys.stderr)
    return loaded


def main():
    ap = argparse.ArgumentParser(description="Cache Banner course descriptions.")
    ap.add_argument("--term", default="202710")
    ap.add_argument("--limit", type=int, help="only fetch the first N (for a sample run)")
    ap.add_argument("--pause", type=float, default=0.3)
    ap.add_argument("--from-csv", nargs="?", const=DEFAULT_DESC_CSV, metavar="PATH",
                    help="load a dumped cache instead of crawling Banner "
                         "(default: the copy in data/)")
    args = ap.parse_args()

    conn = db.connect()
    if args.from_csv:
        load_csv(conn, args.from_csv)
    else:
        run(conn, args.term, args.limit, args.pause)

    # descriptions change the D-27 verdict, so recompute it
    import ingest
    print(ingest.mark_topic_uncertain(conn), file=sys.stderr)


if __name__ == "__main__":
    main()
