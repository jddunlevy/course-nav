"""Tests for the reranker that do not need an API key.

The F-26 / D-16 guard is the whole safety argument for using an LLM here, so it
is tested directly rather than trusted.

    python test_rank_llm.py
"""

import db
import rank
import rank_llm


def fake(crn, subject, number, title, flag="ranked"):
    return {
        "offering_id": int(crn), "score": 1.0, "bucket_score": 1.0,
        "relevance_score": 0.5, "flag": flag, "reason": "tfidf reason",
        "other_sections": 0,
        "buckets_closed": [{"bucket_id": 1, "code": "LIT", "name": "Literature",
                            "must_unmet": False}],
        "offering": {"crn": crn, "subject": subject, "course_number": number,
                     "title": title, "description": "A course about things.",
                     "schedule_type": "Lecture", "open_section": 1},
    }


CANDIDATES = [
    fake("10001", "EN", "205", "English Literature I"),
    fake("10002", "PHL", "211", "Ancient Philosophy"),
    fake("10003", "AAST", "395", "Special Topics", flag="topic_uncertain"),
]


def check(name, got, want):
    ok = got == want
    print("{:4s} {:52s} got {!r}".format("PASS" if ok else "FAIL", name, got))
    return ok


def main():
    passed = True

    # 1. a hallucinated CRN is dropped
    ordered, dropped = rank_llm._validate([
        {"crn": "10002", "reason": "Fits ancient philosophy."},
        {"crn": "99999", "reason": "INVENTED COURSE."},
        {"crn": "10001", "reason": "Closes Literature."},
    ], CANDIDATES)
    passed &= check("invented CRN dropped", dropped, 1)
    passed &= check("invented CRN absent from output",
                    any(r["offering"]["crn"] == "99999" for r in ordered), False)

    # 2. the model's ordering is honoured
    passed &= check("model order applied",
                    [r["offering"]["crn"] for r in ordered],
                    ["10002", "10001", "10003"])

    # 3. a candidate the model forgot is kept, not lost
    ordered2, _ = rank_llm._validate(
        [{"crn": "10001", "reason": "Only one returned."}], CANDIDATES)
    passed &= check("omitted candidates retained", len(ordered2), 3)

    # 4. duplicate CRNs are not duplicated in output
    ordered3, dropped3 = rank_llm._validate([
        {"crn": "10001", "reason": "a"}, {"crn": "10001", "reason": "b"},
    ], CANDIDATES)
    passed &= check("duplicate CRN counted as dropped", dropped3, 1)
    passed &= check("duplicate CRN appears once", len(ordered3), 3)

    # 5. reasons are replaced and attributed
    passed &= check("llm reason used", ordered[0]["reason"], "Fits ancient philosophy.")
    passed &= check("reason attributed", ordered[0].get("reason_source"), "llm")
    passed &= check("untouched result keeps tfidf reason",
                    ordered[2]["reason"], "tfidf reason")

    # 6. the prompt carries no student identifiers
    conn = db.connect()
    outstanding = db.outstanding_buckets(conn, 1)
    student = db.get_student(conn, 1)
    prompt = rank_llm.build_prompt(CANDIDATES, "ancient philosophy", outstanding)
    # Only distinctive values can be tested by substring -- student_id is the
    # integer 1, which occurs inside CRNs and course numbers, so matching on it
    # proves nothing. Assert instead that no identifier FIELD is ever labelled
    # into the prompt, plus the distinctive values themselves.
    leaked = [v for v in (student["name"], student["email"],
                          student["classification"], student["depth_study_label"])
              if v and v in prompt]
    passed &= check("no student identifiers in prompt", leaked, [])
    labels = [w for w in ("student_id", "advisor", "grade", "catalog_year",
                          "@crimson", "depth_study")
              if w in prompt.lower()]
    passed &= check("no identifier fields labelled", labels, [])
    passed &= check("phrase present in prompt", "ancient philosophy" in prompt, True)
    passed &= check("rotating topic marked", "[TOPIC-ROTATES]" in prompt, True)
    conn.close()

    # 7. effort gating by model
    passed &= check("effort on opus 5", rank_llm._supports_effort("claude-opus-5"), True)
    passed &= check("no effort on haiku 4.5",
                    rank_llm._supports_effort("claude-haiku-4-5"), False)

    # 8. rerank_groups reorders group 1 and nothing else. rerank() is stubbed:
    # the assertion is about the plumbing, and the AC 10 fallback is only true
    # if the caller's grouping survives a stage-2 call that went wrong.
    groups = {"relevant": list(CANDIDATES), "both": [],
              "requirement_only": [fake("10004", "HY", "101", "World History")],
              "counts": {"relevant": 3, "requirement_only": 1,
                         "weak_no_closure": 0, "total": 4}}
    real_rerank = rank_llm.rerank
    rank_llm.rerank = lambda results, phrase, outstanding, model=None, **kw: (
        list(reversed(results)), {"ranker": "llm", "reranked": len(results)})
    try:
        out, meta = rank_llm.rerank_groups(groups, "ancient philosophy", outstanding)
    finally:
        rank_llm.rerank = real_rerank
    passed &= check("rerank_groups returns a new dict", out is groups, False)
    passed &= check("rerank_groups reordered group 1",
                    [r["offering"]["crn"] for r in out["relevant"]],
                    ["10003", "10002", "10001"])
    passed &= check("rerank_groups left the input's group 1 alone",
                    [r["offering"]["crn"] for r in groups["relevant"]],
                    ["10001", "10002", "10003"])
    passed &= check("rerank_groups left group 3 untouched",
                    out["requirement_only"] is groups["requirement_only"], True)
    passed &= check("rerank_groups reports the pool it drew from", meta["pool"], 3)

    print()
    print("ALL PASS" if passed else "FAILURES ABOVE")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
