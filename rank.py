"""Ranking: gen-ed bucket closure x phrase relevance (D-19).

Two independent halves, deliberately kept separate:

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
W_BOTH = 0.75       # D-19: closing a requirement AND fitting the phrase ranks first


def phrase_matched(index, phrase):
    """True if the phrase hit anything at all.

    Without this the UI silently degrades to "courses that close a requirement"
    when nothing matches, which looks like an answer but is not one.
    """
    return max(index.similarity(phrase), default=0.0) > 0


def rank(index, outstanding, phrase, limit=40, open_only=True):
    """Return ranked result dicts. Nothing is ever filtered out for uncertainty."""
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
                    "requirement": req["name"], "must_unmet": b["must_unmet"],
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

        score = bucket_score * 1.0 + relevance * W_RELEVANCE
        if bucket_score > 0 and relevance > 0:
            score += W_BOTH

        if score <= 0:
            continue

        results.append({
            "offering_id": o["offering_id"],
            "offering": o,
            "score": round(score, 4),
            "bucket_score": round(bucket_score, 4),
            "relevance_score": round(relevance, 4),
            "flag": "topic_uncertain" if uncertain else "ranked",
            "buckets_closed": closed,
            "reason": build_reason(o, closed, relevance, uncertain),
        })

    results.sort(key=lambda r: (-r["score"], r["offering"]["subject"],
                                r["offering"]["course_number"]))

    # One row per COURSE, not per section. A course with five CRNs is one
    # decision for the student; the extra sections are a scheduling detail, and
    # left in they crowd everything else off the first page.
    best, order = {}, []
    for r in results:
        key = (r["offering"]["subject"], r["offering"]["course_number"])
        if key in best:
            best[key]["other_sections"] += 1
        else:
            r["other_sections"] = 0
            best[key] = r
            order.append(key)
    return [best[k] for k in order[:limit]]


def build_reason(offering, closed, relevance, uncertain):
    """One line, shown per result. The ERD's `reason` field."""
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
    elif relevance >= 0.25:
        parts.append("strong match to your phrase")
    elif relevance > 0:
        parts.append("some overlap with your phrase")
    if offering.get("schedule_type") == "Laboratory":
        parts.append("lab section")
    return "; ".join(parts) if parts else "Offered this term"
