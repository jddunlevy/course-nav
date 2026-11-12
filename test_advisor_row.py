"""Tests for the advisee row's depth study and recent phrases (Story 7.7, FR28).

The five acceptance criteria are mostly about honesty of copy, so they are
checked against RENDERED HTML rather than against the view's return value: the
defect this guards is a field that silently renders empty. Jinja2's default
Undefined does that without raising -- `{{ row.recent_phrase }}`, singular and
misspelled, prints nothing and the page still returns 200. That is how the
result page claimed "0 ranked courses" above 55 matches for two commits, so the
last test here re-renders every page with StrictUndefined.

Expectations come from the database, not from the story file, so a fixture that
drifts fails the test instead of quietly agreeing with it.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_advisor_row.py
"""

import os
import re

os.environ.setdefault("NAVIGATOR_RANKER", "tfidf")

import app as appmod
import db

ADVISOR_ID = 1


def check(name, got, want):
    ok = got == want
    print("{:4s} {:60s} got {!r}".format("PASS" if ok else "FAIL", name, got))
    return ok


def cell_of(html, student_name):
    """The Student cell for one advisee, as rendered."""
    m = re.search(
        r"<td>\s*<strong>" + re.escape(student_name) + r"</strong>(.*?)</td>",
        html, re.S)
    return m.group(1) if m else ""


def field(cell, label):
    """The values rendered under one meta label, and which class carried them."""
    m = re.search(
        r'<span class="meta-label">' + re.escape(label) + r"</span>(.*?)</div>",
        cell, re.S)
    if not m:
        return None
    return re.findall(r'<span class="(own-words|not-recorded)">([^<]*)</span>',
                      m.group(1))


def main():
    passed = True
    conn = db.connect()
    client = appmod.app.test_client()

    r = client.get("/advisor/{}".format(ADVISOR_ID))
    passed &= check("advisor page renders", r.status_code, 200)
    html = r.get_data(as_text=True)

    advisees = db.advisees(conn, ADVISOR_ID)
    phrases = db.recent_phrases(conn, [s["student_id"] for s in advisees])
    passed &= check("every advisee has a row",
                    all(cell_of(html, s["name"]) for s in advisees), True)

    # The fixture this story added. Asserted rather than assumed: AC 2 and AC 4
    # are unreachable without an advisee who has neither field, and if a future
    # seed gives this student a label the criteria stop being exercised.
    labelled = [s for s in advisees if s["depth_study_label"]]
    unlabelled = [s for s in advisees if not s["depth_study_label"]]
    searched = [s for s in advisees if phrases.get(s["student_id"])]
    never = [s for s in advisees if not phrases.get(s["student_id"])]
    passed &= check("fixture: at least one advisee has a label", bool(labelled), True)
    passed &= check("fixture: at least one advisee has none", bool(unlabelled), True)
    passed &= check("fixture: at least one advisee has searched", bool(searched), True)
    passed &= check("fixture: at least one advisee never has", bool(never), True)

    # AC 1 -- the label is the student's own working label, not a programme.
    for s in labelled:
        cell = cell_of(html, s["name"])
        passed &= check("AC1 {}: label rendered as own words".format(s["name"]),
                        field(cell, "Working depth study"),
                        [("own-words", s["depth_study_label"])])
    passed &= check("AC1 the field is headed as a WORKING label",
                    "Working depth study" in html, True)
    passed &= check("AC1 nothing calls it a programme/major/degree",
                    bool(re.search(r"programme of study|major|declared degree",
                                   html, re.I)), False)

    # AC 2 -- a missing label is stated, not blank.
    for s in unlabelled:
        cell = cell_of(html, s["name"])
        passed &= check("AC2 {}: missing label is stated".format(s["name"]),
                        field(cell, "Working depth study"),
                        [("not-recorded", "not recorded")])

    # AC 3 -- most recent phrases, attributed to the student.
    for s in searched:
        cell = cell_of(html, s["name"])
        want = [("own-words", p) for p in phrases[s["student_id"]]]
        passed &= check("AC3 {}: recent phrases, newest first".format(s["name"]),
                        field(cell, "They last searched for"), want)
    passed &= check("AC3 the phrases are attributed to the student",
                    "They last searched for" in html, True)
    passed &= check("AC3 the page says they are the student's own words",
                    "own words" in html, True)

    # AC 4 -- never searched is said, and nothing is inferred from coursework.
    for s in never:
        cell = cell_of(html, s["name"])
        passed &= check("AC4 {}: never-searched is stated".format(s["name"]),
                        field(cell, "They last searched for"),
                        [("not-recorded", "has not searched yet")])
        # Their completed courses must not be used as a stand-in for interest.
        done = conn.execute(
            "SELECT subject, course_number FROM completed_course WHERE student_id = ?",
            (s["student_id"],)).fetchall()
        leaked = [c for c in done
                  if "{} {}".format(c["subject"], c["course_number"]) in cell]
        passed &= check("AC4 {}: no interest inferred from coursework".format(
            s["name"]), leaked, [])

    # AC 5 -- no ROW asserts a fit. Scoped to the rendered cells on purpose: the
    # note above the table uses "fits" to DENY that any judgment is being made
    # ("nothing here judges ... whether any course fits either"), so a page-wide
    # word search would fail on the very sentence that satisfies the criterion.
    claim = re.compile(r"\b(fits|matches|aligns with|recommended|suited|"
                       r"on track|good match|appropriate for)\b", re.I)
    for s in advisees:
        cell = cell_of(html, s["name"])
        passed &= check("AC5 {}: row asserts no fit".format(s["name"]),
                        claim.findall(cell), [])
    passed &= check("AC5 the page hands the judgment to the advisor",
                    "stays yours" in html, True)
    passed &= check("AC5 the note denies judging fit rather than asserting one",
                    "Nothing here judges" in html, True)

    # The N+1 this story was told not to make worse: one query for every
    # advisee's phrases, regardless of how many advisees there are.
    one = db.recent_phrases(conn, [s["student_id"] for s in advisees])
    passed &= check("recent_phrases covers the whole set in one call",
                    sorted(one), sorted(s["student_id"] for s in advisees
                                        if phrases.get(s["student_id"])))
    passed &= check("recent_phrases omits never-searched students",
                    [s["student_id"] for s in never if s["student_id"] in one], [])
    passed &= check("recent_phrases on an empty set does not query",
                    db.recent_phrases(conn, []), {})

    # A student who searched the same words twice has said one thing, not two.
    dupe = conn.execute("SELECT student_id, phrase FROM search_request"
                        " LIMIT 1").fetchone()
    if dupe:
        conn.execute("INSERT INTO search_request"
                     " (student_id, actor_user_id, term, phrase)"
                     " SELECT student_id, actor_user_id, term, phrase"
                     " FROM search_request WHERE student_id = ? LIMIT 1",
                     (dupe["student_id"],))
        got = db.recent_phrases(conn, [dupe["student_id"]])[dupe["student_id"]]
        passed &= check("repeated phrases are not listed twice",
                        len(got), len(set(got)))
        conn.rollback()

    # The silent-Undefined guard. A misspelled field renders empty and returns
    # 200; StrictUndefined turns that into a failure instead.
    import jinja2
    appmod.app.config["PROPAGATE_EXCEPTIONS"] = True
    appmod.app.jinja_env.undefined = jinja2.StrictUndefined
    appmod.app.jinja_env.cache = {}
    strict = []
    for path in ["/", "/advisor/{}".format(ADVISOR_ID)] + [
            "/advisor/{}/student/{}".format(ADVISOR_ID, s["student_id"])
            for s in advisees] + [
            "/student/{}".format(s["student_id"]) for s in advisees]:
        try:
            got = client.get(path)
            if got.status_code != 200:
                strict.append("{} -> {}".format(path, got.status_code))
        except jinja2.UndefinedError as e:
            strict.append("{} -> {}".format(path, e))
    passed &= check("no undefined field on any advisor or student page",
                    strict, [])

    conn.close()
    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
