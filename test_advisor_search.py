"""Tests for finding an advisee by name (Story 7.6, FR28 extended to a search).

Two criteria here are not about what renders, and both are easy to fake:

  AC 3 -- a student who is not this advisor's advisee must not appear, and the
  response must not reveal that they exist. Checked by querying another
  advisor's real student and asserting the response is byte-identical in its
  empty state to a query for a name nobody has. A page that said "not your
  advisee" would pass a weaker test and leak the student's existence.

  AC 6 -- non-matching advisees must not cost a requirement roll-up.
  `outstanding_buckets` is ten SELECTs per student, so this is measured by
  counting statements on the connection, not by reading the code and trusting it.
  Filtering the list after the loop would satisfy AC 2 and silently fail this.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_advisor_search.py
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

DANA = 1          # advisor 1, four advisees
MARCUS = 2        # advisor 2, one advisee -- the AC 3 fixture


def check(name, got, want):
    ok = got == want
    print("{:4s} {:60s} got {!r}".format("PASS" if ok else "FAIL", name, got))
    return ok


def names_in(html):
    """Advisee names rendered as rows, in order."""
    return re.findall(r"<td>\s*<strong>([^<]+)</strong>", html)


def empty_state(html):
    m = re.search(r'<div class="empty">\s*<b>([^<]*)</b>(.*?)</div>', html, re.S)
    return (m.group(1), " ".join(m.group(2).split())) if m else None


def count_selects(client, url):
    """SELECTs issued while serving one request."""
    seen = []
    real = db.connect

    def traced(*a, **k):
        conn = real(*a, **k)
        conn.set_trace_callback(
            lambda s: seen.append(s) if s.lstrip().upper().startswith("SELECT") else None)
        return conn

    db.connect = traced
    try:
        client.get(url)
    finally:
        db.connect = real
    return len(seen)


def main():
    passed = True
    conn = db.connect()
    client = appmod.app.test_client()
    # Story 1.5 (D-33): unauthenticated requests are served the sign-in
    # page, so the suite signs in as the advisor whose screen it tests.
    client.post("/signin",
                data={"username": "dwhitfield", "password": "navigator"})

    dana = db.advisees(conn, DANA)
    marcus = db.advisees(conn, MARCUS)
    passed &= check("fixture: advisor 1 has advisees", len(dana) >= 2, True)
    passed &= check("fixture: a second advisor has one of their own",
                    len(marcus) >= 1, True)
    outsider = marcus[0]["name"]
    passed &= check("fixture: that student is not advisor 1's",
                    outsider in [s["name"] for s in dana], False)

    # AC 1 -- no query renders the full list, unchanged.
    full = client.get("/advisor/{}".format(DANA))
    passed &= check("AC1 unsearched page renders", full.status_code, 200)
    full_html = full.get_data(as_text=True)
    passed &= check("AC1 every advisee is listed",
                    names_in(full_html), [s["name"] for s in dana])
    passed &= check("AC1 open-requirement counts still render",
                    bool(re.search(r'<span class="count">\d+</span>', full_html)), True)
    passed &= check("AC1 no empty state on the full list", empty_state(full_html), None)

    # AC 2 -- a query narrows to matching advisees, each still linking through.
    target = dana[0]
    frag = target["name"].split()[-1][:3].lower()
    hit = client.get("/advisor/{}?q={}".format(DANA, frag)).get_data(as_text=True)
    want = [s["name"] for s in db.advisees(conn, DANA, frag)]
    passed &= check("AC2 query narrows to matching advisees", names_in(hit), want)
    passed &= check("AC2 the query is a strict subset of the full list",
                    set(want) < set(s["name"] for s in dana), True)
    for s in db.advisees(conn, DANA, frag):
        passed &= check("AC2 {} links to the advisor-for-student view".format(s["name"]),
                        "/advisor/{}/student/{}".format(DANA, s["student_id"]) in hit, True)
    passed &= check("AC2 matching is case-insensitive",
                    names_in(client.get("/advisor/{}?q={}".format(
                        DANA, frag.upper())).get_data(as_text=True)), want)

    # AC 3 -- scoping half. The enforcement half needs a session; see the story.
    leak = client.get("/advisor/{}?q={}".format(DANA, outsider.split()[0]))
    leak_html = leak.get_data(as_text=True)
    passed &= check("AC3 the other advisor's student is not listed",
                    names_in(leak_html), [])
    passed &= check("AC3 the response never names them",
                    outsider in leak_html, False)
    passed &= check("AC3 nor their surname",
                    outsider.split()[-1] in leak_html, False)
    # Indistinguishable from a name that belongs to nobody: if the two empty
    # states differed, the difference would itself confirm the student exists.
    nobody = client.get("/advisor/{}?q=qqzzxx".format(DANA)).get_data(as_text=True)
    a = empty_state(leak_html)
    b = empty_state(nobody)
    passed &= check("AC3 empty state is the same shape for a real non-advisee",
                    (a is not None and b is not None and a[1] == b[1]), True)
    passed &= check("AC3 nothing says the name belongs to someone else",
                    bool(re.search(r"not your advisee|another advisor|belongs to|"
                                   r"exists|different advisor", leak_html, re.I)), False)

    # AC 4 -- the empty state names the query and states the scope.
    passed &= check("AC4 empty state names the query back",
                    "qqzzxx" in (b[0] if b else ""), True)
    passed &= check("AC4 empty state states the search is advisees-only",
                    "your own advisees only" in (b[1] if b else ""), True)

    # AC 5 -- the URL reproduces the query and the results.
    url = "/advisor/{}?q={}".format(DANA, frag)
    first = client.get(url).get_data(as_text=True)
    second = client.get(url).get_data(as_text=True)
    passed &= check("AC5 the same URL reproduces the same rows",
                    names_in(first), names_in(second))
    passed &= check("AC5 the query is echoed back into the input",
                    'name="q" value="{}"'.format(frag) in first, True)
    passed &= check("AC5 the query lives in the query string, not a POST",
                    'method="get"' in first.lower(), True)

    # AC 6 -- non-matching advisees must not cost a roll-up. Ten SELECTs each.
    PER_ADVISEE = 10
    all_q = count_selects(client, "/advisor/{}".format(DANA))
    one_q = count_selects(client, "/advisor/{}?q={}".format(DANA, frag))
    none_q = count_selects(client, "/advisor/{}?q=qqzzxx".format(DANA))
    matched = len(want)
    # Story 1.6 scopes /advisor/<id> to that advisor, so Marcus's page has to
    # be measured as Marcus -- as Dana it is now a 404 and costs nothing.
    marcus_client = appmod.app.test_client()
    marcus_client.post("/signin", data={"username": "mbell", "password": "navigator"})
    passed &= check("AC6 one advisee costs ten roll-up SELECTs",
                    count_selects(marcus_client, "/advisor/{}".format(MARCUS)) - none_q,
                    PER_ADVISEE)
    passed &= check("AC6 a narrowed search skips the non-matching roll-ups",
                    all_q - one_q, PER_ADVISEE * (len(dana) - matched))
    passed &= check("AC6 a search matching nobody does no per-advisee work at all",
                    all_q - none_q, PER_ADVISEE * len(dana))
    passed &= check("AC6 cost scales with matches, not with advisee count",
                    one_q < all_q, True)

    # Scoping is in the SQL, not applied afterwards -- the property AC 3 rests on.
    passed &= check("db.advisees cannot return another advisor's student",
                    db.advisees(conn, DANA, outsider), [])
    passed &= check("db.advisees wildcards are escaped, not matched",
                    db.advisees(conn, DANA, "%"), [])
    passed &= check("db.advisees underscore is escaped too",
                    db.advisees(conn, DANA, "_"), [])
    passed &= check("db.advisees with no query is unchanged",
                    [s["name"] for s in db.advisees(conn, DANA, None)],
                    [s["name"] for s in dana])

    # The silent-Undefined guard, extended to the new query URLs.
    import jinja2
    appmod.app.config["PROPAGATE_EXCEPTIONS"] = True
    appmod.app.jinja_env.undefined = jinja2.StrictUndefined
    appmod.app.jinja_env.cache = {}
    strict = []
    # /advisor/<MARCUS> is fetched with Marcus's client: Story 1.6 makes it a
    # 404 for anyone else, which would say nothing about undefined fields.
    for path, who in [("/advisor/{}".format(DANA), client),
                      ("/advisor/{}?q={}".format(DANA, frag), client),
                      ("/advisor/{}?q=qqzzxx".format(DANA), client),
                      ("/advisor/{}".format(MARCUS), marcus_client),
                      ("/advisor/{}?q=%25".format(DANA), client)]:
        try:
            got = who.get(path)
            if got.status_code != 200:
                strict.append("{} -> {}".format(path, got.status_code))
        except jinja2.UndefinedError as e:
            strict.append("{} -> {}".format(path, e))
    passed &= check("no undefined field on any advisor search page", strict, [])

    conn.close()
    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
