"""Tests for the floor, the grouping and the orderings in rank.py (TD-1..TD-11).

The old blend let a course closing one bucket at 17% relevance outrank the most
relevant course in the term. The fix is set membership rather than a weight, so
what needs testing is the BOUNDARY (exactly 0.25 vs 0.2499), which set each row
lands in, and -- the part a reader will not trust on assertion alone -- that
group 1's order owes nothing to bucket_score.

No API key, no database, no pytest.

    python test_rank.py
"""

import rank
import rank_llm

BUCKETS = {1: ("LIT", "Literature"), 2: ("HI", "History"), 3: ("FA", "Fine Arts")}


def offering(oid, subject, number, title, buckets=(), uncertain=False,
             schedule_type="Lecture"):
    """One row of db.offerings_for_term()'s shape, trimmed to what rank() reads."""
    return {
        "offering_id": oid, "crn": str(10000 + oid), "subject": subject,
        "course_number": number, "title": title,
        "description": "A course about things.", "section_text": "",
        "schedule_type": schedule_type, "open_section": 1,
        "topic_uncertain": 1 if uncertain else 0,
        "buckets": [{"bucket_id": b, "code": BUCKETS[b][0], "name": BUCKETS[b][1]}
                    for b in buckets],
    }


def outstanding(must=()):
    """db.outstanding_buckets()'s shape: one open requirement over three buckets.

    Bucket ids listed in `must` carry the unmet must-include clause, so they are
    weighted W_MUST rather than W_BUCKET -- which is the only place must_unmet
    enters ranking, since it is not a field on the result dict.
    """
    return [{
        "requirement_id": 1, "code": "UA_HU", "name": "Humanities",
        "satisfied": False,
        "buckets": [{"bucket_id": b, "code": c, "name": n,
                     "must_include": b in must, "must_unmet": b in must}
                    for b, (c, n) in sorted(BUCKETS.items())],
    }]


class FixedIndex:
    """An Index stand-in with hand-chosen raw similarities.

    rank() touches only .offerings and .similarity(), and a stub is not laziness
    here: rank() normalises every similarity by the term's own maximum, so the
    relevance a course ends up with is a RATIO. Landing one exactly on 0.25
    through real catalog text is not reachable, and the boundary is the thing
    most worth testing. Every sims list below puts a 1.0 first so the normaliser
    is the identity and the numbers read as what they are.
    """

    def __init__(self, offerings, sims):
        self.offerings = offerings
        self._sims = list(sims)

    def similarity(self, phrase):
        return list(self._sims)


def ids(rows):
    return [r["offering_id"] for r in rows]


def grouped(offerings, sims, must=()):
    idx = FixedIndex(offerings, sims)
    return rank.group_results(rank.rank(idx, outstanding(must), "the phrase"))


def by_id(rows, oid):
    return next(r for r in rows if r["offering_id"] == oid)


# --- fixtures -------------------------------------------------------------

# A: the floor boundary. 0.25 is in, 0.2499 is out, and closure decides where
# an excluded row goes.
A = [
    offering(1, "AAA", "100", "Top Match"),
    offering(2, "FLR", "250", "Exactly On The Floor", buckets=(1,)),
    offering(3, "FLR", "249", "Just Under, Closes Something", buckets=(1,)),
    offering(4, "FLR", "248", "Just Under, Closes Nothing"),
]
A_SIMS = [1.0, 0.25, 0.2499, 0.2499]

# B: equal relevance, wildly unequal closure. Group 1's order must not notice.
B = [
    offering(1, "ZZZ", "100", "Equal Relevance, Closes Two", buckets=(1, 2)),
    offering(2, "AAA", "100", "Equal Relevance, Closes None"),
    offering(3, "MMM", "100", "Higher Relevance, Closes None"),
]
B_SIMS = [0.5, 0.5, 1.0]
B_NO_BUCKETS = [dict(o, buckets=[]) for o in B]

# C: group 3's two keys. Within each bucket tier the alphabetically LATER
# subject has the better sub-floor relevance, so an alphabetical result is a
# visible failure rather than a coincidence.
C = [
    offering(1, "AAA", "100", "Top Match"),
    offering(2, "ZED", "400", "Must Tier, Better Sub-Floor", buckets=(1,)),
    offering(3, "ABE", "400", "Must Tier, Worse Sub-Floor", buckets=(1,)),
    offering(4, "ZED", "300", "Plain Tier, Better Sub-Floor", buckets=(2,)),
    offering(5, "ABE", "300", "Plain Tier, Worse Sub-Floor", buckets=(2,)),
]
C_SIMS = [1.0, 0.20, 0.05, 0.20, 0.05]

# D: D-21 / D-27. Relevance is zeroed for a rotating topic, so closure is the
# only thing left that can carry the row onto the page.
D = [
    offering(1, "AAA", "100", "Top Match"),
    offering(2, "UNC", "395", "Rotating Topic, Closes Something",
             buckets=(1,), uncertain=True),
    offering(3, "UNC", "396", "Rotating Topic, Closes Nothing", uncertain=True),
]
D_SIMS = [1.0, 1.0, 1.0]

# E: every set larger than any display cap, so counts can be shown to be
# pre-cap rather than pre-cap-by-accident.
E = [offering(0, "AAA", "100", "Top Match")]
E_SIMS = [1.0]
for _i in range(45):
    E.append(offering(100 + _i, "REL", "{:03d}".format(_i), "Clears The Floor"))
    E_SIMS.append(0.5)
for _i in range(50):
    E.append(offering(200 + _i, "REQ", "{:03d}".format(_i), "Closes Only",
                      buckets=(1,)))
    E_SIMS.append(0.1)
for _i in range(5):
    E.append(offering(300 + _i, "WEA", "{:03d}".format(_i), "Weak, Closes Nothing"))
    E_SIMS.append(0.1)


def check(name, got, want):
    ok = got == want
    print("{:4s} {:52s} got {!r}".format("PASS" if ok else "FAIL", name, got))
    return ok


def main():
    passed = True

    # 1. the floor boundary, and W_BOTH gated on it
    g = grouped(A, A_SIMS)
    passed &= check("0.2500 is in relevant", ids(g["relevant"]), [1, 2])
    passed &= check("0.2500 relevance_score as expected",
                    by_id(g["relevant"], 2)["relevance_score"], 0.25)
    # 1.0 bucket + 0.25*2.0 relevance + 0.75 W_BOTH
    passed &= check("0.2500 is paid W_BOTH",
                    by_id(g["relevant"], 2)["score"], 2.25)
    passed &= check("0.2499 is not in relevant",
                    2 in ids(g["relevant"]) and 3 not in ids(g["relevant"]), True)
    passed &= check("0.2499 with closure lands in requirement_only",
                    ids(g["requirement_only"]), [3])
    # 1.0 bucket + 0.2499*2.0, and no W_BOTH
    passed &= check("W_BOTH not paid below the floor",
                    by_id(g["requirement_only"], 3)["score"], 1.4998)
    passed &= check("0.2499 with no closure is in neither set",
                    4 in ids(g["relevant"]) or 4 in ids(g["requirement_only"]),
                    False)
    passed &= check("0.2499 with no closure is still counted",
                    g["counts"]["weak_no_closure"], 1)
    passed &= check("below-floor reason claims no topical fit",
                    "phrase" in by_id(g["requirement_only"], 3)["reason"], False)
    passed &= check("at-floor reason claims the match",
                    "strong match to your phrase"
                    in by_id(g["relevant"], 2)["reason"], True)

    # 2. group 1 orders on relevance alone (TD-4)
    g = grouped(B, B_SIMS)
    passed &= check("relevant order is -relevance then subject",
                    ids(g["relevant"]), [3, 2, 1])
    passed &= check("closing two buckets does not lift a row in relevant",
                    by_id(g["relevant"], 1)["bucket_score"], 2.0)
    passed &= check("removing bucket data changes no position in relevant",
                    ids(grouped(B_NO_BUCKETS, B_SIMS)["relevant"]), [3, 2, 1])

    # 3. group 3 orders by bucket tier, then sub-floor relevance (TD-5)
    g = grouped(C, C_SIMS, must=(1,))
    passed &= check("requirement_only is bucket tier then sub-floor relevance",
                    ids(g["requirement_only"]), [2, 3, 4, 5])
    passed &= check("requirement_only is not alphabetical within a tier",
                    g["requirement_only"][0]["offering"]["subject"], "ZED")
    passed &= check("must-unmet tier outranks plain tier via W_MUST",
                    [r["bucket_score"] for r in g["requirement_only"]],
                    [1.5, 1.5, 1.0, 1.0])
    passed &= check("only the top match clears the floor here",
                    ids(g["relevant"]), [1])

    # 4. uncertainty is routed, not filtered (D-21, D-27)
    g = grouped(D, D_SIMS)
    row = by_id(g["requirement_only"], 2)
    passed &= check("uncertain with closure lands in requirement_only",
                    ids(g["requirement_only"]), [2])
    passed &= check("uncertain row keeps its flag", row["flag"], "topic_uncertain")
    passed &= check("uncertain row keeps its closure intact",
                    [b["name"] for b in row["buckets_closed"]], ["Literature"])
    passed &= check("uncertain row has relevance zeroed",
                    row["relevance_score"], 0.0)
    passed &= check("uncertain row never reaches relevant",
                    2 in ids(g["relevant"]), False)
    passed &= check("uncertain without closure appears nowhere",
                    3 in ids(g["relevant"]) or 3 in ids(g["requirement_only"]),
                    False)

    # 5. counts are pre-cap, and the four sets partition the result set
    g = grouped(E, E_SIMS)
    passed &= check("counts are pre-cap", g["counts"],
                    {"relevant": 46, "requirement_only": 50,
                     "weak_no_closure": 5, "total": 101})
    c = g["counts"]
    passed &= check("the four sets partition the results",
                    c["relevant"] + c["requirement_only"] + c["weak_no_closure"],
                    c["total"])
    passed &= check("relevant is returned uncapped", len(g["relevant"]), 46)
    passed &= check("requirement_only is returned uncapped",
                    len(g["requirement_only"]), 50)
    passed &= check("both is left for the caller to derive", g["both"], [])

    # 6. the empty case -- FR15's condition is counts["relevant"] == 0
    g = rank.group_results([])
    passed &= check("empty input gives empty groups",
                    [g["relevant"], g["both"], g["requirement_only"]], [[], [], []])
    passed &= check("empty input gives zero counts", g["counts"],
                    {"relevant": 0, "requirement_only": 0,
                     "weak_no_closure": 0, "total": 0})

    # 7. rerank_groups returns a new dict and leaves its argument alone (TD-11).
    # rerank() is stubbed because the point is the plumbing around it, and the
    # AC 10 fallback depends on the input surviving a stage-2 call either way.
    g = grouped(C, C_SIMS, must=(1,))
    g["relevant"] = grouped(B, B_SIMS)["relevant"]      # three rows to reorder
    before_relevant = ids(g["relevant"])
    before_req = ids(g["requirement_only"])
    real_rerank = rank_llm.rerank
    rank_llm.rerank = lambda results, phrase, outstanding, model=None, **kw: (
        list(reversed(results)), {"ranker": "llm", "reranked": len(results)})
    try:
        out, meta = rank_llm.rerank_groups(g, "the phrase", outstanding())
    finally:
        rank_llm.rerank = real_rerank
    passed &= check("rerank_groups returns a new dict", out is g, False)
    passed &= check("rerank_groups reorders relevant",
                    ids(out["relevant"]), list(reversed(before_relevant)))
    passed &= check("rerank_groups leaves the argument's relevant alone",
                    ids(g["relevant"]), before_relevant)
    passed &= check("rerank_groups leaves requirement_only untouched",
                    ids(out["requirement_only"]), before_req)
    passed &= check("rerank_groups carries counts through",
                    out["counts"], g["counts"])
    passed &= check("rerank_groups reports the pre-cap pool size",
                    meta["pool"], len(before_relevant))

    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
