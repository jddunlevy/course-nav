"""Tests the result page against Story 3.6's thirteen acceptance criteria.

Written during 3.6's review as a throwaway harness and committed afterwards,
because the thing that let 3.6 ship broken was that nobody could re-run the
checks: a status said the page worked, the page did not, and no committed test
disagreed. Stories 3.5 and 8.6 went stale the same way.

Every expected value is recomputed from `rank.py` and `db.py` here rather than
copied from the story, so a fixture that drifts fails the test instead of
quietly agreeing with it. Two checks exist for defect classes rather than for
criteria: X1 renders all twelve student/phrase pages, and X2 re-renders every
page under `jinja2.StrictUndefined` -- Jinja's default Undefined renders `0`
for `{{ x|length }}` without raising, which is how the page claimed "0 ranked
courses" above 55 matches for two commits.

Needs the seeded database (python seed.py). No API key, no pytest.

    python test_result_page.py
"""
import os, re, sys, html
os.environ["NAVIGATOR_RANKER"] = "tfidf"
os.environ.setdefault("NAVIGATOR_SECRET_KEY", "testsuite-" + "a1b2c3d4" * 8)

import app as appmod
import db, rank

PASS, FAIL = [], []


def check(cid, desc, ok, evidence):
    (PASS if ok else FAIL).append((cid, desc, evidence))
    print("%-4s %-4s %-56s %s" % ("PASS" if ok else "FAIL", cid, desc[:56], evidence))


client = appmod.app.test_client()
# Story 1.5: routes require a session now. Sign in as the student whose
# pages these checks render (advisor 1 can act for any of them).
client.post("/signin", data={"username": "dwhitfield", "password": "navigator"})


def get(path):
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    return r.get_data(as_text=True)


OL = re.compile(r'<ol class="results( unranked)?">(.*?)</ol>', re.S)
ROW = re.compile(r'<li class="([^"]*)">(.*?)</li>', re.S)


def rowsof(body):
    rows = []
    for m in ROW.finditer(body):
        cls, inner = m.group(1), m.group(2)
        code = re.search(r'<span class="r-code">([^<]*)</span>', inner)
        title = re.search(r'<span class="r-title">([^<]*)</span>', inner)
        crn = re.search(r'CRN (\d+)', inner)
        score = re.search(r'<span class="r-score"[^>]*>([\d.]+)</span>', inner)
        rows.append({
            "class": cls.strip(),
            "code": " ".join(code.group(1).split()) if code else None,
            "title": html.unescape(title.group(1)).strip() if title else None,
            "crn": crn.group(1) if crn else None,
            "score": float(score.group(1)) if score else None,
            "badges": re.findall(r'<span class="badge[^"]*">([^<]*)</span>', inner),
            "flag": "uncertain-flag" in inner,
        })
    return rows


def lists(h):
    """ranked / uncertain / browse row lists, located positionally in the HTML."""
    out = {"ranked": None, "uncertain": None, "browse": None}
    browse_at = h.find('<details class="browse">')
    for m in OL.finditer(h):
        unranked, body = m.group(1), m.group(2)
        rows = rowsof(body)
        if not unranked:
            out["ranked"] = rows
        elif browse_at != -1 and m.start() > browse_at:
            out["browse"] = rows
        else:
            out["uncertain"] = rows
    return out


# ---- recompute expectations straight from the ranker -----------------------
conn = db.connect()
idx = rank.Index(db.offerings_for_term(conn, appmod.TERM))


def truth(sid, phrase):
    outstanding = db.outstanding_buckets(conn, sid)
    g = rank.group_results(rank.rank(idx, outstanding, phrase))
    unc = [r for r in g["requirement_only"] if r["flag"] == "topic_uncertain"]
    return g, unc


LIM = appmod.DISPLAY_LIMIT
tpl = open("templates/results.html", encoding="utf-8").read()

print("=" * 108)
print("C1  heading states the relevant count; no `results` variable survives")
jinja = " ".join(a + b for a, b in re.findall(r"\{\{(.*?)\}\}|\{%(.*?)%\}", tpl, re.S))
bad = re.findall(r"(?<![\w.'\"])results(?![\w\"])", jinja)
check("C1", "no bare `results` variable in any Jinja expression", not bad,
      "%d occurrence(s)" % len(bad))
for name, pat in [("count reads counts.relevant", r"counts\.relevant"),
                  ("guard reads groups.relevant", r"\{% if groups\.relevant %\}"),
                  ("loop reads groups.relevant", r"for r in groups\.relevant"),
                  ("ranked empty state exists", r"No course fits that phrase")]:
    check("C1", name, re.search(pat, tpl) is not None, pat)
h1 = get("/student/1?q=climate+policy")
g1, _ = truth(1, "climate policy")
mh = re.search(r"(\d+) courses? fit ", h1)
check("C1", "heading number equals counts.relevant (pre-cap)",
      mh and int(mh.group(1)) == g1["counts"]["relevant"],
      "heading=%s counts.relevant=%d" % (mh and mh.group(1), g1["counts"]["relevant"]))

print("=" * 108)
print('C2  student 1 / "climate policy"')
L1 = lists(h1)
lead = L1["ranked"][0] if L1["ranked"] else None
check("C2", "relevant list leads with PSC 664 Public Policy Analysis",
      bool(lead) and lead["code"] == "PSC 664" and "Public Policy Analysis" in (lead["title"] or ""),
      "%s / %s" % (lead and lead["code"], lead and lead["title"]))
codes1 = [r["code"] for r in L1["ranked"] or []]
for c in ("BSC 471", "MLC 362"):
    check("C2", "%s absent from the relevant list" % c, c not in codes1,
          "PRESENT" if c in codes1 else "absent")

print("=" * 108)
print("C3  dual fit badged in place, no separate section, never printed twice")
check("C3", "groups.both is never rendered",
      "groups.both" not in tpl and "groups['both']" not in tpl, "absent from template")
# Student 1 / "climate policy" has exactly one dual-fit row and it sits below
# DISPLAY_LIMIT, so badge rendering has to be checked on a case that shows one.
hd = get("/student/2?q=storytelling")
Ld = lists(hd)
gd, _ = truth(2, "storytelling")
exp_dual = len([r for r in gd["relevant"][:LIM] if r["bucket_score"] > 0])
dual = [r for r in Ld["ranked"] or [] if r["badges"]]
check("C3", "dual-fit rows carry a Closes badge inside the relevant list",
      len(dual) == exp_dual and exp_dual > 0,
      "s2/storytelling: %d badged, ranker says %d; e.g. %s -> %s"
      % (len(dual), exp_dual, dual[0]["code"] if dual else "-",
         dual[0]["badges"] if dual else "-"))
check("C3", "badged rows sit in the ranked list, not a section of their own",
      "group-head" not in (re.search(r'<ol class="results">.*?</ol>', hd, re.S) or
                           re.match("", "")).group(0) if Ld["ranked"] else True,
      "no sub-heading inside the ranked <ol>")
allrows = (L1["ranked"] or []) + (L1["uncertain"] or []) + (L1["browse"] or [])
crns = [r["crn"] for r in allrows]
dupes = sorted({c for c in crns if crns.count(c) > 1})
check("C3", "no CRN rendered twice anywhere on the page", not dupes, "dupes=%s" % (dupes or "none"))

print("=" * 108)
print('C4  student 1 / "storytelling" ordering and score field')
h4 = get("/student/1?q=storytelling")
L4 = lists(h4)
g4, _ = truth(1, "storytelling")
scores = [r["score"] for r in L4["ranked"] or []]
check("C4", "rows in non-increasing relevance_score order",
      all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)), "first 5 = %s" % scores[:5])
exp = ["%.2f" % r["relevance_score"] for r in g4["relevant"][:LIM]]
got = ["%.2f" % s for s in scores]
check("C4", "shown score is relevance_score, not score", exp == got,
      "%d/%d positions match" % (sum(1 for a, b in zip(exp, got) if a == b), len(exp)))
codes4 = [r["code"] for r in L4["ranked"] or []]
for c in ("AAST 300", "AAST 352", "AMS 345", "ANT 411", "ANT 412"):
    check("C4", "%s (relevance 0.00) absent from the relevant list" % c, c not in codes4,
          "PRESENT" if c in codes4 else "absent")

print("=" * 108)
print("C5  uncertain rows uncollapsed in their own block, closure + flag visible")
for sid in (1, 2, 3):
    hh = get("/student/%d?q=climate+policy" % sid)
    LL = lists(hh)
    _, u = truth(sid, "climate policy")
    shown = LL["uncertain"] or []
    check("C5", "student %d: rendered uncertain rows == ranker's" % sid, len(shown) == len(u),
          "rendered=%d truth=%d" % (len(shown), len(u)))
    if shown:
        d_at = hh.find('<details class="browse">')
        h3 = hh.find('<h3 class="group-head">')
        check("C5", "student %d: block is outside the collapsed <details>" % sid,
              h3 != -1 and (d_at == -1 or h3 < d_at), "h3@%d details@%d" % (h3, d_at))
        check("C5", "student %d: every row states its closure" % sid,
              all(r["badges"] for r in shown),
              "%d/%d badged" % (sum(1 for r in shown if r["badges"]), len(shown)))
        check("C5", "student %d: every row shows the uncertainty flag" % sid,
              all(r["flag"] for r in shown),
              "%d/%d flagged" % (sum(1 for r in shown if r["flag"]), len(shown)))

print("=" * 108)
print('C6  callout says "these" only about visible rows; absent at zero')
h2 = get("/student/2?q=climate+policy")
L2 = lists(h2)
co = "What these count for is known"
check("C6", "student 1 (0 uncertain): callout absent", co not in h1,
      "absent" if co not in h1 else "PRESENT")
check("C6", "student 2 (8 uncertain): callout present", co in h2,
      "present" if co in h2 else "ABSENT")
mg = re.search(r'<h3 class="group-head">\s*(\d+) course', h2)
check("C6", "block heading count == rows actually rendered",
      bool(mg) and int(mg.group(1)) == len(L2["uncertain"] or []),
      "heading=%s rendered=%d" % (mg and mg.group(1), len(L2["uncertain"] or [])))

print("=" * 108)
print("C7  browse list headed as requirement-closing, not as a phrase result")
# The browse <summary>, not the "Hours totals" one that appears earlier.
bsec = h2[h2.find('<details class="browse">'):]
summ = re.search(r"<summary>(.*?)</summary>", bsec, re.S)
stext = " ".join(re.sub(r"<[^>]+>", " ", summ.group(1)).split()) if summ else ""
check("C7", "headed as closing outstanding requirements",
      "close your outstanding requirements" in stext, stext[:66])
check("C7", "the summary itself does not quote the phrase", "climate policy" not in stext,
      "phrase absent" if "climate policy" not in stext else "PHRASE PRESENT")
check("C7", "states explicitly it is not ranked against what was typed",
      "Not ranked against" in h2, "found")

print("=" * 108)
print("C8  browse summary states shown against the pre-cap total")
g2, u2 = truth(2, "climate policy")
true_ro = g2["counts"]["requirement_only"]
true_browse = len([r for r in g2["requirement_only"] if r["flag"] != "topic_uncertain"])
mm = re.search(r"showing (\d+) of (\d+)", h2)
check("C8", "a 'showing N of M' pair renders", mm is not None, mm.group(0) if mm else "NOT FOUND")
if mm:
    n, M = int(mm.group(1)), int(mm.group(2))
    check("C8", "N == rows actually rendered in the browse list", n == len(L2["browse"] or []),
          "N=%d rendered=%d" % (n, len(L2["browse"] or [])))
    check("C8", "N and M are not presented as equal", n != M, "%d vs %d" % (n, M))
    # Criterion amended 2026-11-11: the browse list's own pre-cap total is
    # counts["browse"], because Q-2 moved the uncertain rows out of this list.
    check("C8", 'M == counts["browse"] (criterion as amended)', M == true_browse,
          "M=%d  counts.browse=%d  (counts.requirement_only=%d)" % (M, true_browse, true_ro))
    flat = " ".join(h2.split())  # the sentence wraps across a line in the template
    check("C8", "the rows held back from this list are stated separately",
          ("The %d with undetermined topics are listed above" % (true_ro - true_browse)) in flat,
          "all %d accounted for: %d + %d" % (true_ro, true_browse, true_ro - true_browse))

print("=" * 108)
print('C9  "rockets and propulsion" -- nothing clears RELEVANCE_FLOOR')
h9 = get("/student/2?q=rockets+and+propulsion")
L9 = lists(h9)
g9, _ = truth(2, "rockets and propulsion")
check("C9", "ranker agrees nothing clears the floor", g9["counts"]["relevant"] == 0,
      "counts.relevant=%d" % g9["counts"]["relevant"])
check("C9", "FR15 callout is shown", "Nothing offered this term fits" in h9, "present")
check("C9", "relevant list renders its own empty state", "No course fits that phrase" in h9, "present")
check("C9", "no ranked <ol> is emitted at all", L9["ranked"] is None,
      "absent" if L9["ranked"] is None else "PRESENT")
d9 = h9.find('<details class="browse">')
check("C9", "FR15 callout precedes the browse list",
      h9.find("Nothing offered this term fits") < (d9 if d9 != -1 else 10 ** 9), "ordered")

print("=" * 108)
print("C10 weak_no_closure stated, those rows not listed")
w = g1["counts"]["weak_no_closure"]
mw = re.search(r"(\d+) further courses? had a", h1)
check("C10", "weak_no_closure is non-zero for this case", w > 0, "weak_no_closure=%d" % w)
check("C10", "the number is stated on the page", bool(mw) and int(mw.group(1)) == w,
      "page=%s truth=%d" % (mw and mw.group(1), w))
exp_rows = (len(g1["relevant"][:LIM])
            + len([r for r in g1["requirement_only"] if r["flag"] == "topic_uncertain"][:LIM])
            + len([r for r in g1["requirement_only"] if r["flag"] != "topic_uncertain"][:LIM]))
check("C10", "no weak row leaks into any rendered list", len(allrows) == exp_rows,
      "rendered=%d expected=%d" % (len(allrows), exp_rows))

print("=" * 108)
print("C11 provenance line")
prov = re.search(r'<p class="provenance">(.*?)</p>', h1, re.S)
ptext = " ".join(re.sub(r"<[^>]+>", " ", prov.group(1)).split()) if prov else ""
check("C11", "states ordering is fit to the phrase only",
      "fit to your phrase by TF-IDF only" in ptext, ptext[:58])
check("C11", "states closure is shown on the row, never moving position",
      "never moves its position" in ptext and "shown on the course" in ptext, "found")
check("C11", "states the requirement list was not reordered at all",
      "not reordered at all" in ptext, "found")
check("C11", "FR18 dropped-CRN reporting intact (both branches)",
      "invented CRN" in tpl and "0 invented CRNs" in tpl, "present")

print("=" * 108)
print("C12 pre-search note drops D-19's single-list promise")
h0 = get("/student/1")
check("C12", "note renders before any search",
      "What a course would close for you is shown" in h0, "present un-searched")
# Checked against RENDERED output: the template keeps a Jinja comment at :202
# recording the old wording, which is documentation, not a promise on the page.
blend = re.compile(r"single (list|ranking)|blended|mixed into (one|a single)", re.I)
hits = [p for p, hh in (("un-searched", h0), ("s1/climate", h1), ("s2/climate", h2),
                        ("s2/rockets", h9)) if blend.search(hh)]
check("C12", "no blended/single-list promise in any rendered page", not hits,
      "pages with a promise: %s" % (hits or "none"))
check("C12", "the only such wording left is a Jinja comment",
      bool(re.search(r"\{#[^#]*single blended", tpl, re.S)), "template :202, not rendered")
check("C12", "says closure is shown on the result, not mixed into position",
      "rather than mixed into its position" in tpl, "found")

print("=" * 108)
print("C13 designed empty states (UX-DR34)")
check("C13", "ranked list has its own empty state", "No course fits that phrase" in tpl, "present")
check("C13", "browse list has its own gap state",
      "Nothing offered closes an outstanding requirement" in tpl, "present")
no_unc_empty = not re.search(
    r"\{% if uncertain_rows %\}.*?\{% else %\}.*?class=\"empty\"", tpl, re.S)
check("C13", "uncertain block has NO empty state -- story's stated deviation",
      no_unc_empty, "absent at zero rather than empty (documented)")

print("=" * 108)
print("X1  all 12 renders clean, plus the advisor-acting-as route")
PHRASES = ["climate policy", "storytelling", "medieval poetry", "rockets and propulsion"]
n_ok = 0
for sid in (1, 2, 3):
    for ph in PHRASES:
        r = client.get("/student/%d?q=%s" % (sid, ph.replace(" ", "+")))
        body = r.get_data(as_text=True)
        ok = (r.status_code == 200 and "Traceback" not in body
              and "jinja2" not in body.lower() and len(body) > 2000)
        n_ok += ok
        if not ok:
            check("X1", "s%d / %s" % (sid, ph), False, "status=%d len=%d" % (r.status_code, len(body)))
check("X1", "12 student renders return 200 with no traceback", n_ok == 12, "%d/12 clean" % n_ok)
ra = client.get("/advisor/1/student/1?q=climate+policy")
check("X1", "advisor acting-as route renders", ra.status_code == 200,
      "status=%d" % ra.status_code)

print("=" * 108)
print("X2  StrictUndefined -- the silent-Undefined trap that hid the last defect")
# Jinja's default Undefined renders '' and |length renders 0 without raising,
# which is how the page reported "0 ranked courses" above 55 matches for two
# commits. Re-rendering under StrictUndefined turns any such hole into an error.
import jinja2, logging
logging.disable(logging.CRITICAL)
appmod.app.config["PROPAGATE_EXCEPTIONS"] = True
appmod.app.jinja_env.undefined = jinja2.StrictUndefined
appmod.app.jinja_env.cache = {}
# meta.fallback_from is a deliberate optional: on the TF-IDF path meta has no
# such key and the template leans on Undefined being falsy. Idiomatic, correct
# under the default environment, and the only one -- allowed for, not ignored.
BENIGN = "has no attribute 'fallback_from'"
strict_ok, strict_err, benign = 0, [], 0
for sid in (1, 2, 3):
    for ph in PHRASES + [""]:
        path = "/student/%d%s" % (sid, ("?q=" + ph.replace(" ", "+")) if ph else "")
        try:
            r = client.get(path)
            strict_ok += r.status_code == 200
            if r.status_code != 200:
                strict_err.append("%s -> %d" % (path, r.status_code))
        except jinja2.UndefinedError as e:
            if BENIGN in str(e):
                benign += 1
            else:
                strict_err.append("%s -> %s" % (path, e))
        except Exception as e:
            strict_err.append("%s -> %s: %s" % (path, type(e).__name__, e))
check("X2", "no unintended Undefined feeds anything on the page", not strict_err,
      "%d clean, %d on the known-benign meta.fallback_from%s"
      % (strict_ok, benign, "; " + "; ".join(strict_err[:2]) if strict_err else ""))
# The 2-commit lie was a renamed variable silently rendering 0. Every field the
# row macro reads must therefore exist on every row the ranker emits.
conn2 = db.connect()
rows = rank.rank(idx, db.outstanding_buckets(conn2, 2), "climate policy")
need = ["offering", "flag", "relevance_score", "bucket_score", "buckets_closed",
        "other_sections", "reason"]
missing = {k: sum(1 for r in rows if k not in r) for k in need}
check("X2", "every field the row macro reads is on every ranker row",
      not any(missing.values()), "%d rows, missing=%s"
      % (len(rows), {k: v for k, v in missing.items() if v} or "none"))

print("=" * 108)
print("%d passed, %d failed" % (len(PASS), len(FAIL)))
for cid, desc, ev in FAIL:
    print("  FAIL %s  %s -- %s" % (cid, desc, ev))
print("ALL PASS" if not FAIL else "FAILURES ABOVE")
sys.exit(1 if FAIL else 0)
