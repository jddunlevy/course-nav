"""Tests for the open-requirement link and the ?req= filter it carries.

Each outstanding requirement on the advisor roster and on the result page links
to the sections offered this term that CLOSE it, ranked against the student's
own depth-study words. A student with no label gets no link, because there is
nothing to rank against and a link to an unranked list would be indistinguish-
able from one to a ranked one.

Three things can go wrong quietly, so each is checked against the DATABASE
rather than against a fixture written out here:

  1. the filter keeps a course that closes something else, which would make the
     page's own heading false;
  2. the counts keep describing the unfiltered set, which is the D-21 failure
     mode -- stated totals that belong to a different list than the one shown;
  3. the narrowed list stays in closure order, which is the one ordering that
     says nothing once every row closes the same requirement.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_req_link.py
"""

import html as htmlmod
import os
import re

os.environ.setdefault("NAVIGATOR_RANKER", "tfidf")
os.environ.setdefault("NAVIGATOR_SECRET_KEY",
                      "testsuite-" + "a1b2c3d4" * 8)

import app as appmod
import db
import rank

ADVISOR_ID = 1


def check(name, got, want):
    ok = got == want
    print("{:4s} {:62s} got {!r}".format("PASS" if ok else "FAIL", name, got))
    return ok


def row_of(html, student_name):
    """One advisee's whole <tr>, as rendered."""
    m = re.search(r"<tr>\s*<td>\s*<strong>" + re.escape(student_name)
                  + r"</strong>.*?</tr>", html, re.S)
    return m.group(0) if m else ""


def links_in(fragment):
    """(href, text) for every anchor in a fragment, HTML-unescaped."""
    return [(htmlmod.unescape(h), htmlmod.unescape(t).strip())
            for h, t in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>',
                                   fragment, re.S)]


def cards_of(html):
    """Every rendered result card's inner HTML, unescaped."""
    return [htmlmod.unescape(c) for c in
            re.findall(r'<li class="[^"]*">(.*?)</li>', html, re.S)]


def headline(html):
    m = re.search(r"(\d+) courses? fit", html)
    return int(m.group(1)) if m else None


def main():
    passed = True
    conn = db.connect()
    client = appmod.app.test_client()
    client.post("/signin",
                data={"username": "dwhitfield", "password": "navigator"})

    advisees = db.advisees(conn, ADVISOR_ID)
    labelled = [s for s in advisees if s["depth_study_label"]]
    unlabelled = [s for s in advisees if not s["depth_study_label"]]
    passed &= check("fixture: an advisee with a label", bool(labelled), True)
    passed &= check("fixture: an advisee without one", bool(unlabelled), True)

    roster = client.get("/advisor/{}".format(ADVISOR_ID)).get_data(as_text=True)

    # 1 -- every open requirement on the roster is a link, and it carries BOTH
    # the student's own words and the requirement it was clicked from.
    for s in labelled:
        open_reqs = [r for r in db.outstanding_buckets(conn, s["student_id"])
                     if not r["satisfied"]]
        got = [(h, t) for h, t in links_in(row_of(roster, s["name"]))
               if "req=" in h]
        passed &= check("{}: every open requirement links".format(s["name"]),
                        len(got), len(open_reqs))
        passed &= check("{}: link text is the requirement name".format(s["name"]),
                        [t for _, t in got],
                        [r["name"] for r in open_reqs])
        want_q = "q=" + s["depth_study_label"].replace(" ", "+")
        passed &= check("{}: every link carries their own words".format(s["name"]),
                        all(want_q in h for h, _ in got), True)
        passed &= check("{}: every link carries the requirement code".format(s["name"]),
                        sorted(re.search(r"req=([^&]+)", h).group(1) for h, _ in got),
                        sorted(r["code"] for r in open_reqs))

    # 2 -- no label, no sorted search. The names are still shown.
    for s in unlabelled:
        row = row_of(roster, s["name"])
        open_reqs = [r for r in db.outstanding_buckets(conn, s["student_id"])
                     if not r["satisfied"]]
        passed &= check("{}: no label, no link".format(s["name"]),
                        [h for h, _ in links_in(row) if "req=" in h], [])
        passed &= check("{}: the requirement names are still listed".format(s["name"]),
                        all(r["name"] in htmlmod.unescape(row) for r in open_reqs),
                        True)

    # 3 -- the same link on the result page, for both roles, and never on a
    # requirement that is already satisfied.
    student = labelled[0]
    sid = student["student_id"]
    reqs = db.outstanding_buckets(conn, sid)
    satisfied = [r for r in reqs if r["satisfied"]]
    for role, path in [("advisor", "/advisor/{}/student/{}".format(ADVISOR_ID, sid)),
                       ("student", "/student/{}".format(sid))]:
        page = client.get(path).get_data(as_text=True)
        names = re.findall(r'<span class="req-name">(.*?)</span>', page, re.S)
        linked = [htmlmod.unescape(n) for n in names if "<a href=" in n]
        passed &= check("{} view: one link per open requirement".format(role),
                        len(linked), len([r for r in reqs if not r["satisfied"]]))
        passed &= check("{} view: links point at this student".format(role),
                        all("student/{}".format(sid) in n for n in linked), True)
        passed &= check("{} view: satisfied requirements are not links".format(role),
                        [r["name"] for r in satisfied
                         if any(r["name"] in n for n in linked)], [])

    # 4 -- following a link. Checked on the requirement with the most open
    # buckets, which is the one most likely to drag in a course that closes
    # something else.
    target = max((r for r in reqs if not r["satisfied"]),
                 key=lambda r: len(r["buckets"]))
    url = "/advisor/{}/student/{}?q={}&req={}".format(
        ADVISOR_ID, sid, student["depth_study_label"].replace(" ", "+"),
        target["code"])
    r = client.get(url)
    passed &= check("the link resolves", r.status_code, 200)
    page = r.get_data(as_text=True)
    text = htmlmod.unescape(page)
    passed &= check("the page names the requirement it is showing",
                    target["name"] in text, True)

    bucket_names = {b["name"] for b in target["buckets"]}
    cards = cards_of(page)
    passed &= check("the filtered page is not empty", bool(cards), True)
    off_target = [c for c in cards
                  if not any(b in c for b in bucket_names)]
    passed &= check("every rendered course closes that requirement",
                    off_target, [])

    # The counts have to describe the filtered set, so they are recomputed the
    # way the view does and compared against what the page says.
    idx = appmod.get_index()
    results = rank.rank(idx, reqs, student["depth_study_label"])
    kept, hidden = rank.filter_requirement(results, target["code"])
    groups = rank.group_results(kept, order_by_relevance=True)
    passed &= check("the headline count is the filtered count",
                    headline(page), groups["counts"]["relevant"])
    passed &= check("the page offers the way out of the narrowing",
                    "Show every result" in text, True)
    passed &= check("the narrowing actually removed something",
                    hidden > 0, True)

    # 5 -- ordering. Inside one requirement, relevance is the only key left.
    rel = [x["relevance_score"] for x in groups["requirement_only"]]
    passed &= check("group 3 is ordered on relevance alone",
                    rel, sorted(rel, reverse=True))
    passed &= check("the page says so rather than claiming it is unranked",
                    ("Ordered by relevance" in text,
                     "Not ranked against" in text), (True, False))
    shown = [float(x) for x in re.findall(r'title="relevance ([0-9.]+)', page)]
    passed &= check("the displayed relevance scores descend",
                    shown, sorted(shown, reverse=True))

    # 6 -- an unknown or satisfied code filters nothing AND claims nothing.
    plain = client.get("/advisor/{}/student/{}?q=public+health".format(
        ADVISOR_ID, sid)).get_data(as_text=True)
    for label, code in ([("unknown code", "NOT_A_CODE")]
                        + ([("satisfied code", satisfied[0]["code"])] if satisfied else [])):
        bogus = client.get("/advisor/{}/student/{}?q=public+health&req={}".format(
            ADVISOR_ID, sid, code)).get_data(as_text=True)
        passed &= check("{}: the result set is untouched".format(label),
                        headline(bogus), headline(plain))
        passed &= check("{}: the page claims no narrowing".format(label),
                        "Only courses that close" in bogus, False)

    # 7 -- filter_requirement on its own.
    passed &= check("filter_requirement partitions the set",
                    len(kept) + hidden, len(results))
    passed &= check("every kept row closes the requirement",
                    all(any(b["requirement_code"] == target["code"]
                            for b in x["buckets_closed"]) for x in kept), True)
    passed &= check("no dropped row closed it",
                    [x for x in results if x not in kept
                     and any(b["requirement_code"] == target["code"]
                             for b in x["buckets_closed"])], [])
    passed &= check("an unknown code keeps nothing",
                    rank.filter_requirement(results, "NOT_A_CODE"),
                    ([], len(results)))
    passed &= check("empty in, empty out", rank.filter_requirement([], "X"), ([], 0))

    # 8 -- the silent-Undefined guard, on the new URLs.
    import jinja2
    appmod.app.config["PROPAGATE_EXCEPTIONS"] = True
    appmod.app.jinja_env.undefined = jinja2.StrictUndefined
    appmod.app.jinja_env.cache = {}
    strict = []
    paths = ["/advisor/{}".format(ADVISOR_ID), url,
             "{}&no_prereq=1".format(url),
             "/student/{}?q={}&req={}".format(
                 sid, student["depth_study_label"].replace(" ", "+"),
                 target["code"])]
    # meta.fallback_from is the project's one deliberate optional: on the
    # TF-IDF path meta has no such key and the template leans on Undefined
    # being falsy. test_result_page's X2 allows for it by name; so does this.
    BENIGN = "has no attribute 'fallback_from'"
    for p in paths:
        try:
            got = client.get(p)
            if got.status_code != 200:
                strict.append("{} -> {}".format(p, got.status_code))
        except jinja2.UndefinedError as e:
            if BENIGN not in str(e):
                strict.append("{} -> {}".format(p, e))
    passed &= check("no undefined field on any filtered page", strict, [])

    conn.close()
    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
