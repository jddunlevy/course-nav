"""Tests that every record route is scoped to the signed-in user (Story 1.6).

The criterion that shapes the rest is AC 5: a refusal must not reveal whether
the id exists. If a forbidden-but-real student returned 403 while a nonexistent
one returned 404, the pair would be an enumeration oracle -- a classmate could
map which student ids are real by reading status codes. So every refusal must
be indistinguishable from a missing record, and that is asserted here by
comparing the two responses byte for byte rather than by checking that both
happen to be refusals.

AC 6 is the quiet one: before this story the persisted `actor_user_id` was
resolved from the id in the URL, so a search an advisor ran on a student's
behalf recorded the student as the actor. That is the single case where "who is
this page about" and "who asked for it" differ, and the one the audit trail
most needs right.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_scoping.py
"""

import os

os.environ.setdefault("NAVIGATOR_RANKER", "tfidf")
os.environ.setdefault("NAVIGATOR_SECRET_KEY", "testsuite-" + "a1b2c3d4" * 8)

import app as appmod
import db

PASSWORD = "navigator"
MISSING_STUDENT = 9999
MISSING_ADVISOR = 9999


def check(name, got, want):
    ok = got == want
    print("{:4s} {:64s} got {!r}".format("PASS" if ok else "FAIL", name, got))
    return ok


def client_for(username):
    c = appmod.app.test_client()
    c.post("/signin", data={"username": username, "password": PASSWORD})
    return c


def main():
    passed = True
    conn = db.connect()

    dana = conn.execute("SELECT * FROM app_user WHERE username='dwhitfield'").fetchone()
    marcus = conn.execute("SELECT * FROM app_user WHERE username='mbell'").fetchone()
    jordan = conn.execute("SELECT * FROM app_user WHERE username='jreyes'").fetchone()
    dana_advisees = [s["student_id"] for s in db.advisees(conn, dana["advisor_id"])]
    marcus_advisees = [s["student_id"] for s in db.advisees(conn, marcus["advisor_id"])]
    outsider = marcus_advisees[0]
    passed &= check("fixture: the two advisors share no advisee",
                    set(dana_advisees) & set(marcus_advisees), set())
    passed &= check("fixture: Jordan is Dana's advisee, not Marcus's",
                    (jordan["student_id"] in dana_advisees,
                     jordan["student_id"] in marcus_advisees), (True, False))

    cd, cm, cj = client_for("dwhitfield"), client_for("mbell"), client_for("jreyes")

    # ---- AC 1: a student cannot read another student ----------------------
    other = next(s for s in dana_advisees if s != jordan["student_id"])
    own = cj.get("/student/{}".format(jordan["student_id"]))
    theirs = cj.get("/student/{}".format(other))
    passed &= check("AC1 a student can read their own record", own.status_code, 200)
    passed &= check("AC1 a student cannot read another student", theirs.status_code, 404)
    other_name = conn.execute("SELECT name FROM student WHERE student_id = ?",
                              (other,)).fetchone()["name"]
    passed &= check("AC1 the refusal carries none of that student's data",
                    other_name in theirs.get_data(as_text=True), False)

    # ---- AC 2: an advisor opens their own advisee -------------------------
    for sid in dana_advisees:
        passed &= check("AC2 Dana opens advisee {}".format(sid),
                        cd.get("/advisor/{}/student/{}".format(
                            dana["advisor_id"], sid)).status_code, 200)
    passed &= check("AC2 and the plain student route too",
                    cd.get("/student/{}".format(dana_advisees[0])).status_code, 200)

    # ---- AC 3: an advisor cannot read someone else's advisee --------------
    passed &= check("AC3 Dana cannot open Marcus's advisee",
                    cd.get("/student/{}".format(outsider)).status_code, 404)
    passed &= check("AC3 nor through her own advisor segment",
                    cd.get("/advisor/{}/student/{}".format(
                        dana["advisor_id"], outsider)).status_code, 404)
    passed &= check("AC3 nor by naming Marcus's advisor id",
                    cd.get("/advisor/{}/student/{}".format(
                        marcus["advisor_id"], outsider)).status_code, 404)
    passed &= check("AC3 the refusal names no one",
                    conn.execute("SELECT name FROM student WHERE student_id = ?",
                                 (outsider,)).fetchone()["name"]
                    in cd.get("/student/{}".format(outsider)).get_data(as_text=True),
                    False)
    passed &= check("AC3 Marcus still opens his own advisee",
                    cm.get("/student/{}".format(outsider)).status_code, 200)

    # ---- AC 4: a student cannot reach an advisor route --------------------
    for url in ["/advisor/{}".format(dana["advisor_id"]),
                "/advisor/{}".format(marcus["advisor_id"]),
                "/advisor/{}/student/{}".format(dana["advisor_id"],
                                                jordan["student_id"])]:
        r = cj.get(url)
        passed &= check("AC4 student refused {}".format(url), r.status_code, 404)
        passed &= check("AC4 no advisee list renders at {}".format(url),
                        "close your outstanding requirements"
                        in r.get_data(as_text=True), False)

    # ---- AC 5: refusals must not reveal whether the id exists -------------
    # Byte-identical, not merely both-refused: a difference of any kind is the
    # oracle this criterion exists to remove.
    pairs = [
        ("student, forbidden vs nonexistent",
         cj.get("/student/{}".format(other)), cj.get("/student/{}".format(MISSING_STUDENT))),
        ("advisor, forbidden vs nonexistent",
         cd.get("/advisor/{}".format(marcus["advisor_id"])),
         cd.get("/advisor/{}".format(MISSING_ADVISOR))),
        ("advisee route, forbidden vs nonexistent",
         cd.get("/advisor/{}/student/{}".format(dana["advisor_id"], outsider)),
         cd.get("/advisor/{}/student/{}".format(dana["advisor_id"], MISSING_STUDENT))),
        ("student hitting an advisor route, real vs nonexistent",
         cj.get("/advisor/{}".format(dana["advisor_id"])),
         cj.get("/advisor/{}".format(MISSING_ADVISOR))),
    ]
    for label, real, missing in pairs:
        passed &= check("AC5 {}: same status".format(label),
                        real.status_code, missing.status_code)
        passed &= check("AC5 {}: identical body".format(label),
                        real.get_data() == missing.get_data(), True)

    # An advisee who exists and is readable must still differ from both, or the
    # check above would pass trivially on a route that refuses everything.
    allowed = cd.get("/student/{}".format(dana_advisees[0]))
    passed &= check("AC5 a permitted request is still distinguishable",
                    allowed.status_code != pairs[0][1].status_code, True)

    # ---- AC 6: the actor on a saved search is the signed-in user ----------
    before = conn.execute("SELECT MAX(request_id) m FROM search_request").fetchone()["m"] or 0
    sid = dana_advisees[0]
    cd.get("/advisor/{}/student/{}?q=climate+policy".format(dana["advisor_id"], sid))
    row = conn.execute(
        "SELECT student_id, actor_user_id FROM search_request"
        " WHERE request_id > ? ORDER BY request_id DESC LIMIT 1", (before,)).fetchone()
    passed &= check("AC6 an advisor's search is recorded", row is not None, True)
    if row:
        passed &= check("AC6 the actor is the signed-in advisor",
                        row["actor_user_id"], dana["user_id"])
        passed &= check("AC6 the search is still about the student",
                        row["student_id"], sid)
        student_user = conn.execute(
            "SELECT user_id FROM app_user WHERE student_id = ?", (sid,)).fetchone()
        # The whole point: before this story the actor WAS the student's own
        # user row, because it was looked up from the id in the path.
        passed &= check("AC6 the actor is NOT the student being searched for",
                        row["actor_user_id"] == student_user["user_id"], False)

    before = conn.execute("SELECT MAX(request_id) m FROM search_request").fetchone()["m"] or 0
    cj.get("/student/{}?q=storytelling".format(jordan["student_id"]))
    row = conn.execute(
        "SELECT actor_user_id FROM search_request WHERE request_id > ?"
        " ORDER BY request_id DESC LIMIT 1", (before,)).fetchone()
    passed &= check("AC6 a student's own search records the student",
                    row and row["actor_user_id"], jordan["user_id"])

    # ---- the rule itself, independent of the routes -----------------------
    import auth
    passed &= check("may_view_student: a student sees only themselves",
                    [s for s in dana_advisees
                     if auth.may_view_student(conn, jordan, s)],
                    [jordan["student_id"]])
    passed &= check("may_view_student: an advisor sees exactly their advisees",
                    sorted(s for s in dana_advisees + marcus_advisees
                           if auth.may_view_student(conn, dana, s)),
                    sorted(dana_advisees))
    passed &= check("may_view_student: nobody is not allowed",
                    auth.may_view_student(conn, None, dana_advisees[0]), False)
    passed &= check("may_view_advisor: only that advisor",
                    (auth.may_view_advisor(dana, dana["advisor_id"]),
                     auth.may_view_advisor(dana, marcus["advisor_id"]),
                     auth.may_view_advisor(jordan, dana["advisor_id"]),
                     auth.may_view_advisor(None, dana["advisor_id"])),
                    (True, False, False, False))

    # The identity-by-assertion query this story removed must not come back.
    src = open("app.py", encoding="utf-8").read()
    passed &= check("the actor is no longer looked up from the URL",
                    "SELECT user_id FROM app_user WHERE" in src, False)

    conn.close()
    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
