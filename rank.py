"""Ranking: gen-ed bucket closure x phrase relevance (D-19).

Two independent halves, deliberately kept separate -- and, since this revision,
never blended into the quantity that orders the page. `group_results()` turns
closure into SET MEMBERSHIP instead of a weight (TD-1), because any single-list
weighting leaves a constant that re-creates the distortion as soon as the
catalog or the student's outstanding set changes. The old blend let a course
closing one bucket at 17% relevance outrank the single most relevant course in
the whole term. The two halves:

  bucket_score     hours this section would close against requirements the
                   student still has outstanding. Comes from Banner attributes,
                   which are reliable. This is the double count (D-11, F-41).

  relevance_score  TF-IDF cosine similarity between the typed phrase (D-22) and
                   the course title + description + section text. Unreliable
                   when the description is a generic rotating-topic blurb, which
                   is what course.topic_uncertain marks (D-27).

TF-IDF is pure Python on purpose: 3,324 courses is small, and it keeps the
dependency list at Flask alone. If it ranks badly on the test phrases, the
escalation path is sentence embeddings -- the interface below would not change.

WHAT IS AND IS NOT FILTERED
---------------------------
D-21 and D-27 say uncertainty is surfaced, not hidden: `topic_uncertain` zeroes
relevance but never removes a section or weakens its stated closure. That is not
the same as "nothing is filtered". A section that closes nothing AND matches
nothing scores zero and is dropped (`if score <= 0`), and a section below
RELEVANCE_FLOOR that closes nothing is counted but never listed. Both have
always been true here; the grouping below just makes them visible.
"""

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z][a-z'-]+")

STOP = set("""
a about above after again all also am an and any are aren as at be because been
before being below between both but by can cannot could did do does doing down
during each few for from further had has have having he her here hers him his
how i if in into is it its itself just me more most my no nor not of off on once
only or other ought our ours out over own same she should so some such than that
the their theirs them then there these they this those through to too under
until up very was we were what when where which while who whom why will with
you your yours course courses student students hours hour credit credits
introduction study topics prerequisite prerequisites
""".split())


def tokenize(text):
    return [t for t in TOKEN_RE.findall((text or "").lower())
            if t not in STOP and len(t) > 2]


class Index:
    """TF-IDF over the offered courses for one term."""

    def __init__(self, offerings):
        self.offerings = offerings
        self.docs = []
        df = Counter()
        for o in offerings:
            text = " ".join(filter(None, [
                o.get("title"), o.get("title"),      # title counted twice: it is the
                o.get("description"), o.get("section_text"),  # strongest short signal
            ]))
            tf = Counter(tokenize(text))
            self.docs.append(tf)
            for term in tf:
                df[term] += 1

        n = max(len(self.docs), 1)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}

        self.vectors = []
        for tf in self.docs:
            vec = {t: (1 + math.log(c)) * self.idf.get(t, 0.0) for t, c in tf.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self.vectors.append({t: v / norm for t, v in vec.items()})

    def similarity(self, phrase):
        q_tf = Counter(tokenize(phrase))
        if not q_tf:
            return [0.0] * len(self.vectors)
        q = {t: (1 + math.log(c)) * self.idf.get(t, 0.0) for t, c in q_tf.items()}
        norm = math.sqrt(sum(v * v for v in q.values())) or 1.0
        q = {t: v / norm for t, v in q.items()}
        out = []
        for vec in self.vectors:
            # iterate the shorter side
            small, large = (q, vec) if len(q) < len(vec) else (vec, q)
            out.append(sum(w * large.get(t, 0.0) for t, w in small.items()))
        return out


# weights -- tuned by hand against the test phrases, not learned
W_BUCKET = 1.0
W_MUST = 1.5        # a must-include bucket (one Literature, one History) is worth more
W_RELEVANCE = 2.0
W_BOTH = 0.75       # D-19: genuine dual fit, now gated on RELEVANCE_FLOOR

# Also hand-set against the test phrases, not learned. 0.25 is the cut
# build_reason() already calls "strong match to your phrase", so the floor and
# the prose cannot disagree. On "climate policy" it admits GY 302 Climatology
# (0.5912) and excludes BSC 471 Plant Physiology (0.2352) and MLC 362 Applied
# Linguistics (0.1729). Fragile: BSC 471 clears exclusion by only 0.015 of a
# relative unit, and relevance is normalised against the term's own best match,
# so 0.25 of a weak maximum is still weak.
RELEVANCE_FLOOR = 0.25


# --- Prerequisite screen -------------------------------------------------
#
# There is no prerequisite ENTITY in this schema -- it was deferred as
# optional-for-v1 (schema.sql:12) -- so this is a TEXT screen over Banner's
# sectionText and the catalog description, and it is the weakest thing feeding
# the page. It can only find a prerequisite somebody wrote down in prose: 376
# of 9,621 offerings match any pattern below, so the other 9,245 come back
# clean whether or not they actually have one. MATH 125 and BSC 115 both carry
# real prerequisites and both come back clean. The UI must therefore say
# "none listed" and never "none" -- see results.html.
PREREQ_PATTERNS = [
    r"prereq",                                         # 131 offerings
    r"instructor permission required",                 # 121
    r"permission of",                                  # 118
    r"(?:junior|senior|graduate|sophomore) standing",  # 35
    r"placement (?:exam|and)",                         # 16
    r"formal application",                             # 9
    r"minimum grade of",                               # 4
    r"consent of",                                     # 1
]
PREREQ_RE = re.compile("|".join(PREREQ_PATTERNS), re.I)


def has_prerequisite(offering):
    """True when a prerequisite is WRITTEN DOWN for this section.

    False means "nothing said so", not "no prerequisite". The two are not the
    same thing here, and no caller may render them as though they were.
    """
    return bool(PREREQ_RE.search(" ".join(filter(None, [
        offering.get("section_text"), offering.get("description")]))))


def filter_no_prereq(results):
    """Drop the results whose course lists a prerequisite.

    Returns (kept, hidden_count). Kept separate from rank() so the page can
    state how many rows the toggle removed: a filter that silently shrinks a
    result set is indistinguishable from a ranker that got worse.
    """
    kept = [r for r in results if not r["has_prereq"]]
    return kept, len(results) - len(kept)


def filter_requirement(results, requirement_code):
    """Keep only the results that close one named requirement.

    Returns (kept, hidden_count), like filter_no_prereq, and for the same
    reason: the page states how many rows the narrowing removed rather than
    quietly serving a smaller set.

    A course can close several requirements at once, so this is membership in
    `buckets_closed`, not equality. Courses that close nothing carry an empty
    `buckets_closed` and are therefore always dropped -- which is the point of
    the link that leads here, but it does mean the phrase-only matches are gone
    from the page. The caller says so on screen.
    """
    kept = [r for r in results
            if any(b.get("requirement_code") == requirement_code
                   for b in r["buckets_closed"])]
    return kept, len(results) - len(kept)


def rank(index, outstanding, phrase, open_only=True):
    """Return ranked result dicts, one per course, uncapped.

    No `limit`: the display cut belongs to the caller, applied after stage-2
    reranking (TD-7). Capping here meant the reranker's own MAX_CANDIDATES
    could never bind, so a buried-but-relevant course never reached stage 2.
    """
    open_buckets = {}
    for req in outstanding:
        if req["satisfied"]:
            continue
        for b in req["buckets"]:
            prev = open_buckets.get(b["bucket_id"])
            weight = W_MUST if b["must_unmet"] else W_BUCKET
            if prev is None or weight > prev["weight"]:
                open_buckets[b["bucket_id"]] = {
                    "bucket_id": b["bucket_id"], "code": b["code"],
                    "name": b["name"], "weight": weight,
                    "requirement": req["name"],
                    # The requirement's own code, not the bucket's: a bucket
                    # belongs to several requirements' unions (D-28), so the
                    # bucket code cannot name which requirement was asked for.
                    "requirement_code": req["code"],
                    "must_unmet": b["must_unmet"],
                }

    sims = index.similarity(phrase)
    # Normalise to the best match in this result set. Raw cosine against short
    # catalog text lands around 0.1-0.3, which loses to bucket_score every time
    # and buries genuinely on-topic courses. Normalising makes "best phrase
    # match" worth W_RELEVANCE regardless of the absolute cosine scale.
    top = max(sims) if sims else 0.0
    if top > 0:
        sims = [s / top for s in sims]

    results = []
    for o, sim in zip(index.offerings, sims):
        if open_only and o.get("open_section") == 0:
            continue

        closed = [open_buckets[b["bucket_id"]] for b in o["buckets"]
                  if b["bucket_id"] in open_buckets]
        bucket_score = sum(b["weight"] for b in closed)

        uncertain = bool(o.get("topic_uncertain"))
        # D-27: the generic blurb carries no topical signal, so do not pretend
        # it does. Bucket closure is untouched -- the section still ranks on it.
        relevance = 0.0 if uncertain else sim

        # ONE canonical quantity gates W_BOTH, decides group membership and
        # feeds build_reason(). Gating on the unrounded local instead would let
        # a course at 0.249963 join group 1 while being denied W_BOTH.
        relevance_score = round(relevance, 4)

        score = bucket_score * 1.0 + relevance * W_RELEVANCE
        # Gated on the floor, not on nonzero relevance: W_BOTH was meant to
        # reward genuine dual fit (D-19), and one surviving shared TF-IDF token
        # is not that.
        if bucket_score > 0 and relevance_score >= RELEVANCE_FLOOR:
            score += W_BOTH

        if score <= 0:
            continue

        results.append({
            "offering_id": o["offering_id"],
            "offering": o,
            "score": round(score, 4),
            "bucket_score": round(bucket_score, 4),
            "relevance_score": relevance_score,
            "flag": "topic_uncertain" if uncertain else "ranked",
            "has_prereq": has_prerequisite(o),
            "buckets_closed": closed,
            "reason": build_reason(o, closed, relevance_score, uncertain),
        })

    # The dedup below keeps the FIRST row per course, so this sort chooses which
    # section represents a course -- and therefore which relevance_score that
    # course carries into grouping. Keying on -score let the blended number make
    # that choice silently, which is the same defect one step removed (TD-10).
    # Invariant: a course enters grouping with its best-matching open section's
    # relevance, since offering_attribute is per-offering and the schema does not
    # guarantee the max-relevance section is encountered first.
    results.sort(key=lambda r: (-r["relevance_score"], r["offering"]["subject"],
                                r["offering"]["course_number"]))

    # One row per COURSE, not per section. A course with five CRNs is one
    # decision for the student; the extra sections are a scheduling detail, and
    # left in they crowd everything else off the first page.
    best, order = {}, []
    for r in results:
        key = (r["offering"]["subject"], r["offering"]["course_number"])
        if key in best:
            best[key]["other_sections"] += 1
            # A prerequisite is a property of the COURSE, but sectionText is
            # per-section and the sort above picks the representative on
            # relevance alone. Without this OR, whether MATH 112 looks
            # prerequisite-free depends on which of its CRNs happened to sort
            # first -- the filter would be nondeterministic across terms.
            best[key]["has_prereq"] = (best[key]["has_prereq"]
                                       or r["has_prereq"])
        else:
            r["other_sections"] = 0
            best[key] = r
            order.append(key)
    return [best[k] for k in order]


def group_results(results, order_by_relevance=False):
    """Partition `rank()`'s output into the four labelled sets (TD-1).

    Returns plain lists and plain counts -- no Flask, no Jinja2 -- because the
    same shape is the natural input to a conversational refinement loop later.

      relevant          group 1, "fits your interest": relevance at or above the
                        floor, ordered on RELEVANCE ALONE (TD-4). No bucket
                        tiebreaker: a bucket key here would re-admit the
                        distortion this whole change exists to remove, and it is
                        near-inert anyway (3 of 55 rows tie on "climate policy").
      both              group 2, left EMPTY here. It is a badged view of the
                        DISPLAYED group 1, so only the caller can build it, after
                        reranking and after the display cap (TD-3).
      requirement_only  group 3: closes something but is below the floor. Ordered
                        by -bucket_score, then -relevance_score, then
                        subject/number. must_unmet is NOT a key -- it is already
                        inside bucket_score via W_MUST, and it is not a field on
                        this dict. Sub-floor relevance is the second key because
                        bucket_score is frequently constant across the entire
                        group (student 1's group 3 is {1.0: 64}); without it the
                        alphabetical filler this spec calls out as the symptom
                        would simply relocate to the top of group 3.

    `order_by_relevance` drops the closure key and orders group 3 on relevance
    alone. It is for the caller that has already narrowed the set to ONE
    requirement: every row there closes the same thing, so closure says almost
    nothing and sorting on it first buries exactly what the narrowing was asked
    to surface. This is not the blend D-19 and D-35 forbid -- no two quantities
    are combined, and group membership is untouched.
      counts            pre-cap sizes, including `weak_no_closure` -- the fourth
                        set, 36-41 courses per search, which is counted and
                        stated but never listed. Named because it exists: the
                        page total has to reconcile with something.

    The four sets partition `results` exactly: relevant + requirement_only +
    weak_no_closure == total.
    """
    relevant = [r for r in results if r["relevance_score"] >= RELEVANCE_FLOOR]

    if order_by_relevance:
        def group3_key(r):
            return (-r["relevance_score"], r["offering"]["subject"],
                    r["offering"]["course_number"])
    else:
        def group3_key(r):
            return (-r["bucket_score"], -r["relevance_score"],
                    r["offering"]["subject"], r["offering"]["course_number"])

    requirement_only = sorted(
        (r for r in results if r["bucket_score"] > 0
         and r["relevance_score"] < RELEVANCE_FLOOR), key=group3_key)

    weak_no_closure = sum(1 for r in results if r["bucket_score"] == 0
                          and 0 < r["relevance_score"] < RELEVANCE_FLOOR)

    return {
        "relevant": relevant,
        "both": [],
        "requirement_only": requirement_only,
        "counts": {
            "relevant": len(relevant),
            "requirement_only": len(requirement_only),
            "weak_no_closure": weak_no_closure,
            "total": len(results),
        },
    }


def build_reason(offering, closed, relevance_score, uncertain):
    """One line, shown per result. The ERD's `reason` field.

    Takes the SAME rounded relevance_score that gates W_BOTH and decides
    membership, so the prose and the grouping cannot disagree.
    """
    parts = []
    if closed:
        names = ", ".join(b["name"] for b in closed)
        must = [b for b in closed if b["must_unmet"]]
        if must:
            parts.append("Closes {} -- and you still need at least one {}"
                         .format(names, must[0]["name"]))
        else:
            parts.append("Counts toward {}".format(names))
    if uncertain:
        parts.append("topic rotates each term and the catalog description is "
                     "generic -- cannot determine fit, ask your advisor")
    elif relevance_score >= RELEVANCE_FLOOR:
        parts.append("strong match to your phrase")
    # Below the floor the reason says NOTHING about the phrase. Such a row can
    # only reach the page inside group 3, whose heading promises closure and not
    # topical fit -- which is exactly what lets group 3 sort on sub-floor
    # relevance without that sort asserting a fit the prose would then deny.
    if offering.get("schedule_type") == "Laboratory":
        parts.append("lab section")
    return "; ".join(parts) if parts else "Offered this term"
