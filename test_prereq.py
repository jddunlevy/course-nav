"""Tests for the prerequisite screen (rank.py) and its toggle on the result page.

What is worth testing here is not that a regex matches. It is the three places
this feature can quietly lie:

  1. a FALSE from has_prerequisite() means "nothing said so", and the page must
     not present it as "no prerequisite" -- so the wording is asserted, not just
     the behaviour;
  2. the prerequisite belongs to the COURSE while sectionText is per-section,
     and rank()'s dedup picks a representative on relevance alone -- so a course
     must look the same whichever of its CRNs sorts first;
  3. the screen runs before grouping and before the display cap, so the counts
     on the page have to describe the screened set and not the unscreened one.

No API key, no network. Needs the seeded database for the route checks.

    python test_prereq.py
"""
import os, re
os.environ["NAVIGATOR_RANKER"] = "tfidf"
os.environ.setdefault("NAVIGATOR_SECRET_KEY", "testsuite-" + "a1b2c3d4" * 8)

import rank
import app as appmod

PASS, FAIL = [], []


def check(desc, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(desc)
    print("%-4s %-62s got %r" % ("PASS" if ok else "FAIL", desc[:62], got))
    return ok


def offering(oid, subject, number, title, section_text="", description="A course."):
    return {
        "offering_id": oid, "crn": str(10000 + oid), "subject": subject,
        "course_number": number, "title": title,
        "description": description, "section_text": section_text,
        "schedule_type": "Lecture", "open_section": 1, "topic_uncertain": 0,
        "buckets": [],
    }


class FixedIndex:
    def __init__(self, offerings, sims):
        self.offerings, self._sims = offerings, list(sims)

    def similarity(self, phrase):
        return list(self._sims)


OUTSTANDING = []  # no open requirements: isolates the screen from bucket closure


# ---------------------------------------------------------------- 1. detection
print("1  has_prerequisite -- each pattern the catalog actually uses")

for text in ["Prerequisite: Minimum grade of C- in BSC 300",
             "Prerequisites:  BSC 109 or BSC 114 & 115",
             "Prereq: HD 202 & HD 205",
             "Instructor Permission Required.",
             "permission of the director of undergraduate English studies",
             "Prerequisites for the course are graduate standing",
             "Placement and two units of college-preparatory mathematics",
             "formal application, and a satisfactory interview",
             "consent of professor for any student not enrolled"]:
    check("detects %r" % text[:38], rank.has_prerequisite({"section_text": text}), True)

check("clean section text is not a hit",
      rank.has_prerequisite({"section_text": "Restricted to Main Campus Students only."}),
      False)
check("empty offering is not a hit", rank.has_prerequisite({}), False)
check("None fields do not raise",
      rank.has_prerequisite({"section_text": None, "description": None}), False)
check("reads the description too, not only sectionText",
      rank.has_prerequisite({"description": "The prerequisite for this course is MUS 100."}),
      True)
check("case-insensitive",
      rank.has_prerequisite({"section_text": "PREREQUISITE: SEE DEPARTMENT"}), True)

# The documented failure mode, asserted so it cannot be forgotten: a course with
# a real prerequisite and no prose about it reads as clean.
check("undetectable prerequisite reads clean (the known gap)",
      rank.has_prerequisite({"section_text": "", "description":
                             "Calculus of functions of one variable."}), False)


# ------------------------------------------------------------------ 2. the flag
print()
print("2  rank() carries has_prereq, per course rather than per section")

A = [offering(1, "GY", "302", "Climatology"),
     offering(2, "BSC", "403", "Research", section_text="Prerequisites: BSC 114")]
rows = rank.rank(FixedIndex(A, [1.0, 0.9]), OUTSTANDING, "climate")
check("every row has the flag", all("has_prereq" in r for r in rows), True)
check("clean course flagged False", rows[0]["has_prereq"], False)
check("prerequisite course flagged True", rows[1]["has_prereq"], True)

# Same course, two CRNs, only one of which says so. Whichever section sorts
# first, the course must come out flagged.
TWO = [offering(3, "HD", "203", "Medical Terminology", section_text=""),
       offering(4, "HD", "203", "Medical Terminology",
                section_text="Prerequisites: BSC 109")]
for sims, which in [([1.0, 0.5], "clean section first"),
                    ([0.5, 1.0], "prereq section first")]:
    rows = rank.rank(FixedIndex(TWO, sims), OUTSTANDING, "anatomy")
    check("one row per course (%s)" % which, len(rows), 1)
    check("course-level OR holds (%s)" % which, rows[0]["has_prereq"], True)


# ---------------------------------------------------------------- 3. the filter
print()
print("3  filter_no_prereq -- what it keeps and what it reports")

rows = rank.rank(FixedIndex(A, [1.0, 0.9]), OUTSTANDING, "climate")
kept, hidden = rank.filter_no_prereq(rows)
check("keeps the clean course", [r["offering"]["subject"] for r in kept], ["GY"])
check("reports the hidden count", hidden, 1)
check("does not mutate its argument", len(rows), 2)
check("empty in, empty out", rank.filter_no_prereq([]), ([], 0))
allclean, hidden = rank.filter_no_prereq(
    rank.rank(FixedIndex([offering(5, "NEW", "335", "Wildlife")], [1.0]),
              OUTSTANDING, "wildlife"))
check("nothing to hide reports 0", hidden, 0)
check("nothing to hide keeps everything", len(allclean), 1)


# ----------------------------------------------------------------- 4. the route
print()
print("4  the toggle on the result page, for both roles")

client = appmod.app.test_client()
client.post("/signin", data={"username": "dwhitfield", "password": "navigator"})


def get(path):
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    return r.get_data(as_text=True)


def total(body):
    """The 'N courses fit' headline -- the pre-cap count the screen must move."""
    m = re.search(r"(\d+) courses? fit", body)
    return int(m.group(1)) if m else None


PHRASE = "q=climate+policy"
plain = get("/advisor/1/student/2?" + PHRASE)
screened = get("/advisor/1/student/2?%s&no_prereq=1" % PHRASE)

check("checkbox is on the page", 'name="no_prereq"' in plain, True)
check("unchecked by default", 'value="1" checked' in plain, False)
check("checked when the toggle is on", 'value="1" checked' in screened, True)
check("the caveat only shows when screening",
      ("not a prerequisite check" in plain, "not a prerequisite check" in screened),
      (False, True))
check("label says LISTED, not 'without prerequisites'",
      "<strong>listed</strong> prerequisite" in screened, True)
check("the screen reduces the headline count", total(screened) <= total(plain), True)
check("the screen does not empty the page", total(screened) > 0, True)
check("recent-phrase links carry the toggle", "no_prereq=1" in screened, True)

# Students reach the same handler by a different route, so the control must be
# there too -- that was the whole of the ask.
sclient = appmod.app.test_client()
sclient.post("/signin", data={"username": "rdelgado", "password": "navigator"})
sbody = sclient.get("/student/2?%s&no_prereq=1" % PHRASE).get_data(as_text=True)
check("student route serves the toggle", 'name="no_prereq"' in sbody, True)
check("student route applies it", "not a prerequisite check" in sbody, True)

print()
print("%d assertions, %d passed, %d failed" % (len(PASS) + len(FAIL), len(PASS), len(FAIL)))
raise SystemExit(1 if FAIL else 0)
