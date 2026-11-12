"""Tests for sign-out (Story 1.7).

The criterion with teeth is AC 2's second clause: "the signed-in response was
not marked cacheable". That is a requirement on every page served WHILE signed
in, not on the sign-out response. The threat the story names is a shared
advising-office machine, and clearing the session only stops the server
answering -- a page already in the browser's cache is served by the browser,
so the next person presses Back and reads the record without a request ever
reaching Flask. So the header is asserted on a signed-in page.

AC 3 looks like it is about stored state, and is not: the acting-as view is a
URL, so the only way it can survive a sign-out is through the `next` parameter
Story 1.5 added. The test signs out from the acting-as page and then signs in
as a DIFFERENT user, which is the case that would actually hurt.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_signout.py
"""

import os

os.environ.setdefault("NAVIGATOR_RANKER", "tfidf")
os.environ.setdefault("NAVIGATOR_SECRET_KEY", "testsuite-" + "a1b2c3d4" * 8)

import app as appmod
import db

PASSWORD = "navigator"


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
    jordan = conn.execute("SELECT * FROM app_user WHERE username='jreyes'").fetchone()
    advisee = db.advisees(conn, dana["advisor_id"])[0]["student_id"]

    # ---- AC 1: sign-out clears the session and serves the sign-in page ----
    c = client_for("dwhitfield")
    passed &= check("AC1 signed in to start with",
                    c.get("/advisor/{}".format(dana["advisor_id"])).status_code, 200)
    out = c.post("/signout")
    passed &= check("AC1 sign-out redirects", out.status_code, 302)
    landed = c.get(out.headers["Location"])
    body = landed.get_data(as_text=True)
    passed &= check("AC1 the sign-in page is served", landed.status_code, 200)
    passed &= check("AC1 it carries the sign-in form", 'name="password"' in body, True)
    passed &= check("AC1 and confirms the sign-out happened",
                    "You are signed out" in body, True)
    passed &= check("AC1 the session is actually cleared",
                    c.get("/advisor/{}".format(dana["advisor_id"])).status_code, 401)

    # ---- AC 2: the session is dead, and the pages were never cacheable ----
    c2 = client_for("jreyes")
    signed_in = c2.get("/student/{}".format(jordan["student_id"]))
    passed &= check("AC2 a student view renders while signed in",
                    signed_in.status_code, 200)
    cache = signed_in.headers.get("Cache-Control", "")
    passed &= check("AC2 the signed-in response is marked no-store",
                    "no-store" in cache, True)
    passed &= check("AC2 and is marked private", "private" in cache, True)
    search = c2.get("/student/{}?q=climate+policy".format(jordan["student_id"]))
    passed &= check("AC2 a search result page is no-store too",
                    "no-store" in search.headers.get("Cache-Control", ""), True)
    c2.post("/signout")
    again = c2.get("/student/{}".format(jordan["student_id"]))
    passed &= check("AC2 the student view is refused after sign-out", again.status_code, 401)
    passed &= check("AC2 and serves the sign-in page",
                    'name="password"' in again.get_data(as_text=True), True)
    passed &= check("AC2 no student name survives in it",
                    conn.execute("SELECT name FROM student WHERE student_id = ?",
                                 (jordan["student_id"],)).fetchone()["name"]
                    in again.get_data(as_text=True), False)
    # The stylesheet is not private and is deliberately left cacheable.
    passed &= check("AC2 /static is not forced no-store",
                    "no-store" in appmod.app.test_client().get(
                        "/static/style.css").headers.get("Cache-Control", ""), False)

    # ---- AC 3: the acting-as state does not survive into the next sign-in -
    c3 = client_for("dwhitfield")
    acting = c3.get("/advisor/{}/student/{}".format(dana["advisor_id"], advisee))
    passed &= check("AC3 the advisor is acting for a student", acting.status_code, 200)
    passed &= check("AC3 the acting-as banner is on that page",
                    "You are acting as" in acting.get_data(as_text=True), True)
    out = c3.post("/signout")
    passed &= check("AC3 sign-out goes to a bare /signin with no next",
                    "next" in out.headers.get("Location", ""), False)
    signin_page = c3.get(out.headers["Location"]).get_data(as_text=True)
    passed &= check("AC3 the sign-in page carries no hidden next field",
                    'name="next"' in signin_page, False)
    # The case that would actually hurt: a different person signs in next.
    nxt = c3.post("/signin", data={"username": "jreyes", "password": PASSWORD})
    passed &= check("AC3 the next sign-in lands on their OWN view",
                    nxt.headers.get("Location"),
                    "/student/{}".format(jordan["student_id"]))
    after = c3.get("/advisor/{}/student/{}".format(dana["advisor_id"], advisee))
    passed &= check("AC3 and they cannot reach the previous acting-as URL",
                    after.status_code, 404)

    # ---- sign-out itself must not be reachable by GET ---------------------
    c4 = client_for("dwhitfield")
    get_out = c4.get("/signout")
    passed &= check("GET /signout is not allowed", get_out.status_code, 405)
    passed &= check("and it did not sign anyone out",
                    c4.get("/advisor/{}".format(dana["advisor_id"])).status_code, 200)

    # ---- the control is on every signed-in page, acting-as included -------
    for url in ["/advisor/{}".format(dana["advisor_id"]),
                "/student/{}".format(advisee),
                "/advisor/{}/student/{}".format(dana["advisor_id"], advisee)]:
        passed &= check("a sign-out control renders on {}".format(url),
                        'action="/signout"' in c4.get(url).get_data(as_text=True), True)
    passed &= check("but not on the sign-in page itself",
                    'action="/signout"' in appmod.app.test_client().get(
                        "/signin").get_data(as_text=True), False)

    conn.close()
    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
