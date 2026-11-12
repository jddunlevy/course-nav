"""Tests for sign-in with a credential (Story 1.5, D-33).

The criterion worth testing hardest is the first one: with no session, no route
may leak student or advisor data. A guard that merely returns a non-200 passes a
lazy test while still rendering a student's name in the <title>, so this asserts
the absence of every seeded person's name from the whole body of every
unauthenticated response -- including a search URL with a query string, which is
the one most likely to be bookmarked and shared.

The others are about not leaking by accident: that an unknown username and a
wrong password are indistinguishable, and that no plaintext password reaches the
database or the session cookie.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_auth.py
"""

import os
import re

os.environ.setdefault("NAVIGATOR_RANKER", "tfidf")
# A real-shaped secret so the suite runs without a .env. The boot refusal this
# story adds rejects short and placeholder values, which is itself tested below
# in a subprocess -- it cannot be tested in-process, because by the time this
# module imports `app` the check has already run.
os.environ.setdefault("NAVIGATOR_SECRET_KEY",
                      "testsuite-" + "a1b2c3d4" * 8)

import app as appmod
import auth
import config
import db

PASSWORD = "navigator"


def check(name, got, want):
    ok = got == want
    print("{:4s} {:62s} got {!r}".format("PASS" if ok else "FAIL", name, got))
    return ok


def sign_in(username=None, password=PASSWORD):
    c = appmod.app.test_client()
    if username:
        c.post("/signin", data={"username": username, "password": password})
    return c


def main():
    passed = True
    conn = db.connect()

    people = [r["name"] for r in conn.execute(
        "SELECT name FROM student UNION SELECT name FROM advisor")]
    users = conn.execute("SELECT * FROM app_user ORDER BY user_id").fetchall()
    advisor_u = next(u for u in users if u["role"] == "advisor")
    student_u = next(u for u in users if u["role"] == "student")

    # ---- AC 1: nothing is served to a caller with no session ---------------
    anon = appmod.app.test_client()
    routes = ["/", "/student/1", "/advisor/1", "/advisor/1/student/2",
              "/student/2?q=climate+policy", "/advisor/1?q=del"]
    for url in routes:
        r = anon.get(url)
        body = r.get_data(as_text=True)
        passed &= check("AC1 {} is not served".format(url), r.status_code, 401)
        passed &= check("AC1 {} leaks no person's name".format(url),
                        [n for n in people if n in body], [])
        passed &= check("AC1 {} offers the sign-in form".format(url),
                        'name="password"' in body, True)
    passed &= check("AC1 the sign-in page itself is reachable",
                    anon.get("/signin").status_code, 200)
    passed &= check("AC1 the stylesheet is reachable, or the page is unstyled",
                    anon.get("/static/style.css").status_code, 200)

    # ---- AC 2: a valid credential opens that user's own view ---------------
    for u in (student_u, advisor_u):
        c = appmod.app.test_client()
        r = c.post("/signin", data={"username": u["username"], "password": PASSWORD})
        endpoint, kwargs = auth.home_endpoint_for(u)
        want = "/student/{}".format(u["student_id"]) if u["role"] == "student" \
            else "/advisor/{}".format(u["advisor_id"])
        passed &= check("AC2 {} is redirected to their own view".format(u["username"]),
                        (r.status_code, r.headers.get("Location")), (302, want))
        passed &= check("AC2 {} can then load it".format(u["username"]),
                        c.get(want).status_code, 200)
    c = sign_in(advisor_u["username"])
    passed &= check("AC2 / dispatches to the signed-in user's view",
                    c.get("/").headers.get("Location"),
                    "/advisor/{}".format(advisor_u["advisor_id"]))
    passed &= check("AC2 a next= path is honoured",
                    appmod.app.test_client().post("/signin", data={
                        "username": advisor_u["username"], "password": PASSWORD,
                        "next": "/advisor/1?q=del"}).headers.get("Location"),
                    "/advisor/1?q=del")
    passed &= check("AC2 next= cannot be turned into an open redirect",
                    appmod.app.test_client().post("/signin", data={
                        "username": advisor_u["username"], "password": PASSWORD,
                        "next": "//evil.example/x"}).headers.get("Location"),
                    "/advisor/{}".format(advisor_u["advisor_id"]))

    # ---- AC 3: failure says nothing about which half was wrong -------------
    wrong_pw = appmod.app.test_client().post(
        "/signin", data={"username": student_u["username"], "password": "nope"})
    no_user = appmod.app.test_client().post(
        "/signin", data={"username": "nosuchperson", "password": "nope"})

    def alert(resp):
        m = re.search(r'class="callout gap"[^>]*>(.*?)</div>',
                      resp.get_data(as_text=True), re.S)
        return " ".join(m.group(1).split()) if m else None

    passed &= check("AC3 a wrong password does not open a view", wrong_pw.status_code, 200)
    passed &= check("AC3 an unknown user does not open a view", no_user.status_code, 200)
    passed &= check("AC3 both failures give the identical message",
                    alert(wrong_pw), alert(no_user))
    passed &= check("AC3 the message is actually shown",
                    bool(alert(wrong_pw)) and "failed" in alert(wrong_pw).lower(), True)
    passed &= check("AC3 the message does not name which half was wrong",
                    bool(re.search(r"no such user|unknown user|wrong password|"
                                   r"incorrect password|user not found",
                                   alert(wrong_pw) or "", re.I)), False)
    passed &= check("AC3 a failed attempt establishes no session",
                    wrong_pw.headers.get("Location"), None)

    # ---- AC 4: the header names the signed-in user and their role ----------
    c = sign_in(advisor_u["username"])
    head = c.get("/advisor/{}".format(advisor_u["advisor_id"])).get_data(as_text=True)
    head = head[head.find("<header"):head.find("</header>") + 9]
    passed &= check("AC4 the header names the signed-in user",
                    advisor_u["display_name"] in head, True)
    passed &= check("AC4 the header names their role", advisor_u["role"] in head, True)
    # An advisor acting on a student's behalf is two identities at once (FR29):
    # the header must still say who is SIGNED IN, not who is being viewed.
    acting = c.get("/advisor/1/student/2").get_data(as_text=True)
    acting_head = acting[acting.find("<header"):acting.find("</header>") + 9]
    passed &= check("AC4 acting-as still names the signed-in advisor",
                    advisor_u["display_name"] in acting_head, True)
    passed &= check("AC4 the signed-out state exists on the sign-in page",
                    "not signed in" in appmod.app.test_client().get(
                        "/signin").get_data(as_text=True), True)

    # ---- AC 5: no usable secret, no boot -----------------------------------
    # In a subprocess: the in-process check already passed at import time.
    import subprocess
    import sys

    def boots_with(value):
        env = dict(os.environ)
        if value is None:
            env.pop("NAVIGATOR_SECRET_KEY", None)
        else:
            env["NAVIGATOR_SECRET_KEY"] = value
        # Point the .env loader at a path that does not exist, or it would
        # supply the developer's real key and the refusal would never fire.
        env["NAVIGATOR_ENV_FILE"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".env.does-not-exist")
        p = subprocess.run([sys.executable, "-c", "import app"],
                           env=env, capture_output=True, text=True,
                           cwd=os.path.dirname(os.path.abspath(__file__)))
        return p.returncode

    passed &= check("AC5 refuses to boot with no secret set", boots_with(None) != 0, True)
    passed &= check("AC5 refuses to boot on an empty secret", boots_with("") != 0, True)
    for placeholder in ("dev", "change-me", "secret", "CHANGEME"):
        passed &= check("AC5 refuses to boot on the default {!r}".format(placeholder),
                        boots_with(placeholder) != 0, True)
    passed &= check("AC5 refuses a secret that is too short to be generated",
                    boots_with("abc123") != 0, True)
    passed &= check("AC5 boots on a real secret", boots_with("f" * 64), 0)

    # ---- AC 6: pbkdf2 with a per-user salt, and no plaintext anywhere ------
    passed &= check("AC6 every user has a hash, a salt and an iteration count",
                    [u["username"] for u in users
                     if not (u["password_hash"] and u["password_salt"]
                             and u["password_iterations"])], [])
    passed &= check("AC6 salts are unique per user",
                    len({u["password_salt"] for u in users}), len(users))
    passed &= check("AC6 the same password yields different hashes",
                    len({u["password_hash"] for u in users}), len(users))
    passed &= check("AC6 no plaintext password is stored",
                    [u["username"] for u in users
                     if PASSWORD in " ".join(str(x) for x in tuple(u))], [])
    passed &= check("AC6 the stored hash is pbkdf2_hmac of the password",
                    auth.verify_password(PASSWORD, student_u["password_hash"],
                                         student_u["password_salt"],
                                         student_u["password_iterations"]), True)
    passed &= check("AC6 a wrong password does not verify",
                    auth.verify_password("nope", student_u["password_hash"],
                                         student_u["password_salt"],
                                         student_u["password_iterations"]), False)
    passed &= check("AC6 iterations are a real work factor",
                    student_u["password_iterations"] >= 100_000, True)
    # The session is a signed cookie the user holds: it must carry an id, not a
    # credential.
    c = appmod.app.test_client()
    c.post("/signin", data={"username": student_u["username"], "password": PASSWORD})
    cookies = "; ".join(
        "{}={}".format(k.key, k.value) for k in c._cookies.values()
    ) if hasattr(c, "_cookies") else ""
    passed &= check("AC6 the session cookie carries no plaintext password",
                    PASSWORD in cookies, False)
    passed &= check("AC6 the session stores the user id only",
                    PASSWORD in str(c.get("/").headers), False)

    # ---- AC 7: the hashing added no dependency -----------------------------
    reqs = open("requirements.txt", encoding="utf-8").read()
    passed &= check("AC7 requirements.txt still names one hard dependency",
                    [ln for ln in reqs.splitlines()
                     if ln.strip() and not ln.strip().startswith("#")], ["Flask>=3.0"])
    passed &= check("AC7 no hashing library was added",
                    bool(re.search(r"bcrypt|argon|passlib|werkzeug.security|scrypt",
                                   reqs, re.I)), False)
    # AC 7 is about dependencies, not about importing nothing: auth.py imports
    # the project's own `db` and Flask, which was already the one hard
    # dependency. What must not appear is a third-party hashing library.
    LOCAL = {"db", "config", "rank", "rank_llm", "auth"}
    STDLIB = {"hashlib", "hmac", "os", "re", "sqlite3", "secrets", "base64"}
    auth_src = open("auth.py", encoding="utf-8").read()
    imported = set(re.findall(r"^import (\w+)", auth_src, re.M)) | set(
        re.findall(r"^from (\w+) import", auth_src, re.M))
    passed &= check("AC7 auth.py imports nothing beyond stdlib, Flask and this project",
                    sorted(imported - STDLIB - LOCAL - {"flask"}), [])
    passed &= check("AC7 the hashing itself is stdlib pbkdf2_hmac",
                    "hashlib.pbkdf2_hmac" in auth_src, True)

    # ---- the picker is gone, not merely unlinked ---------------------------
    passed &= check("the role picker template is deleted",
                    os.path.exists("templates/home.html"), False)
    passed &= check("no route lists every app_user any more",
                    bool(re.search(r"SELECT[^\"']*FROM app_user\s*\n?\s*LEFT JOIN",
                                   open("app.py", encoding="utf-8").read())), False)
    passed &= check("the Werkzeug debugger is off",
                    "debug=True" in open("app.py", encoding="utf-8").read(), False)

    conn.close()
    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
