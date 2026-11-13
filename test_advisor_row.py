"""Tests for the advisee row's working depth study (Story 7.7, FR28).

The row no longer shows what a student searched for: that field was removed
from the advisor screen, and the phrase criteria that went with it are gone
from this file. What remains is checked against RENDERED HTML rather than
against the view's return value, because the defect it guards is a field that
silently renders empty. Jinja2's default Undefined does that without raising --
a misspelled `{{ row.depth_study }}` prints nothing and the page still returns
200. That is how the result page claimed "0 ranked courses" above 55 matches
for two commits, so the last test here re-renders every page with
StrictUndefined.

Expectations come from the database, not from the story file, so a fixture that
drifts fails the test instead of quietly agreeing with it.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_advisor_row.py
"""

import os
import re

os.environ.setdefault("NAVIGATOR_RANKER", "tfidf")
# Story 1.5: every route needs a session now, and the app refuses to boot
# without a real secret. Set one for the suite, then sign in below.
os.environ.setdefault("NAVIGATOR_SECRET_KEY",
                      "testsuite-" + "a1b2c3d4" * 8)

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
    # Story 1.5 (D-33): unauthenticated requests are served the sign-in
    # page, so the suite signs in as the advisor whose screen it tests.
    client.post("/signin",
                data={"username": "dwhitfield", "password": "navigator"})

    r = client.get("/advisor/{}".format(ADVISOR_ID))
    passed &= check("advisor page renders", r.status_code, 200)
    html = r.get_data(as_text=True)

    advisees = db.advisees(conn, ADVISOR_ID)
    passed &= check("every advisee has a row",
                    all(cell_of(html, s["name"]) for s in advisees), True)

    # The fixture this story added. Asserted rather than assumed: AC 2 is
    # unreachable without an advisee who has no label, and if a future seed
    # gives that student one the criterion stops being exercised.
    labelled = [s for s in advisees if s["depth_study_label"]]
    unlabelled = [s for s in advisees if not s["depth_study_label"]]
    passed &= check("fixture: at least one advisee has a label", bool(labelled), True)
    passed &= check("fixture: at least one advisee has none", bool(unlabelled), True)

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

    # AC 2 -- a missing label is stated, not blank, and nothing stands in for
    # it: completed coursework must not be rendered as a guess at the label.
    for s in unlabelled:
        cell = cell_of(html, s["name"])
        passed &= check("AC2 {}: missing label is stated".format(s["name"]),
                        field(cell, "Working depth study"),
                        [("not-recorded", "not recorded")])
        done = conn.execute(
            "SELECT subject, course_number FROM completed_course WHERE student_id = ?",
            (s["student_id"],)).fetchall()
        leaked = [c for c in done
                  if "{} {}".format(c["subject"], c["course_number"]) in cell]
        passed &= check("AC2 {}: no label inferred from coursework".format(
            s["name"]), leaked, [])

    # The screen must not report what a student searched for.
    passed &= check("no search history on the advisor screen",
                    "last searched" in html.lower(), False)

    # AC 5 -- no ROW asserts a fit. Scoped to the rendered cells rather than to
    # the whole page: the result page the rows link to is allowed to talk about
    # what fits a phrase, and this criterion is about the roster, not that.
    claim = re.compile(r"\b(fits|matches|aligns with|recommended|suited|"
                       r"on track|good match|appropriate for)\b", re.I)
    for s in advisees:
        cell = cell_of(html, s["name"])
        passed &= check("AC5 {}: row asserts no fit".format(s["name"]),
                        claim.findall(cell), [])

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
            # "/" is a 302 to the signed-in user's own view since Story 1.5
            # removed the picker; it renders no template of its own.
            ok = (302,) if path == "/" else (200,)
            if got.status_code not in ok:
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
