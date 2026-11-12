"""Course Navigator -- Flask prototype.

Two roles, student and advisor (D-20, D-25). There is no auth provider and no
password: v1 deliberately does not over-build, and the role split is what matters
for the demo, not the security model.

    python app.py      ->  http://127.0.0.1:5000
"""

import os

from flask import Flask, abort, redirect, render_template, request, url_for

import db
import rank
import rank_llm

TERM = os.environ.get("NAVIGATOR_TERM", "202710")
TERM_LABEL = "Spring 2027"

# auto -- use the LLM reranker when a credential is present, else TF-IDF.
# tfidf / llm force one. The fallback is deliberate: a graded demo must not
# depend on a network round trip.
RANKER = os.environ.get("NAVIGATOR_RANKER", "auto")

# How many rows per group the page shows. It lives here and not in rank.py on
# purpose: grouping has to be uncapped so the stage-2 pool is drawn before any
# display cut, so this cap is applied to what comes BACK from the reranker.
DISPLAY_LIMIT = 40

app = Flask(__name__)
_index = None


def get_index():
    """TF-IDF index over the term's offerings. Built once, reused."""
    global _index
    if _index is None:
        conn = db.connect()
        offerings = db.offerings_for_term(conn, TERM)
        conn.close()
        _index = rank.Index(offerings)
        app.logger.info("indexed %d offerings for %s", len(offerings), TERM)
    return _index


@app.route("/")
def home():
    conn = db.connect()
    users = conn.execute("""
        SELECT u.user_id, u.display_name, u.role, u.student_id, u.advisor_id,
               s.classification
        FROM app_user u
        LEFT JOIN student s ON s.student_id = u.student_id
        ORDER BY u.role DESC, u.display_name
    """).fetchall()
    conn.close()
    return render_template("home.html", users=users, term_label=TERM_LABEL)


@app.route("/student/<int:student_id>")
def student_view(student_id):
    return _results_page(student_id, viewer_role="student")


@app.route("/advisor/<int:advisor_id>")
def advisor_view(advisor_id):
    conn = db.connect()
    advisor = conn.execute("SELECT * FROM advisor WHERE advisor_id = ?",
                           (advisor_id,)).fetchone()
    if not advisor:
        abort(404)
    # Story 7.6: the name query lives in the query string (UX-DR22), so an
    # advisor can copy the URL and reopen the same result. Narrowing happens in
    # the SQL below, before the outstanding_buckets loop -- that loop costs ten
    # queries per advisee, and AC 6 is that non-matching advisees never pay it.
    query = (request.args.get("q") or "").strip()
    rows = db.advisees(conn, advisor_id, query)
    # One query for every advisee's recent phrases (FR28 via Story 7.7). Fetched
    # outside the loop deliberately: the per-advisee outstanding_buckets call
    # below is already the N+1 that Story 7.6's last criterion has to answer for.
    phrases = db.recent_phrases(conn, [s["student_id"] for s in rows])
    summary = []
    for s in rows:
        outstanding = db.outstanding_buckets(conn, s["student_id"])
        summary.append({
            "student": s,
            "open_count": sum(1 for r in outstanding if not r["satisfied"]),
            "open_names": [r["name"] for r in outstanding if not r["satisfied"]],
            # [] when the student has never searched -- recent_phrases omits
            # them rather than mapping them to empty, so AC 4 is a real absence.
            "recent_phrases": phrases.get(s["student_id"], []),
        })
    conn.close()
    return render_template("advisor.html", advisor=advisor, summary=summary,
                           query=query, term_label=TERM_LABEL)


@app.route("/advisor/<int:advisor_id>/student/<int:student_id>")
def advisor_student_view(advisor_id, student_id):
    return _results_page(student_id, viewer_role="advisor", advisor_id=advisor_id)


def _results_page(student_id, viewer_role, advisor_id=None):
    conn = db.connect()
    student = db.get_student(conn, student_id)
    if not student:
        abort(404)

    outstanding = db.outstanding_buckets(conn, student_id)
    numeric = db.numeric_progress(conn, student_id)
    phrase = (request.args.get("q") or "").strip()

    groups = rank.group_results([])
    matched = True
    meta = {"ranker": "tfidf"}
    if phrase:
        idx = get_index()
        groups = rank.group_results(rank.rank(idx, outstanding, phrase))

        use_llm = RANKER == "llm" or (RANKER == "auto" and rank_llm.available())
        if use_llm and groups["relevant"]:
            try:
                groups, meta = rank_llm.rerank_groups(groups, phrase, outstanding)
            except Exception as e:
                # Never let the ranker take the page down. TF-IDF order stands,
                # and because rerank_groups() does not mutate its argument the
                # grouping here is still the full deterministic one.
                app.logger.warning("LLM rerank failed, using TF-IDF: %s", e)
                meta = {"ranker": "tfidf", "fallback_from": "llm",
                        "error": type(e).__name__}

        # Cap for DISPLAY only, and only now -- after stage 2 has chosen from
        # the whole pool. counts stay pre-cap so the page can say how many
        # exist, not just how many it is showing.
        #
        # Q-2 (D-35): the uncertain-and-closing rows are selected BEFORE the cap
        # and placed at the head of the displayed set. They have to be, because
        # rank.py forces their relevance to 0, which sorts them last inside every
        # bucket tier -- for student 2 / "climate policy" they sit at positions
        # 161, 162, 317-319, 406, 414 and 423 of 480, so a straight [:40] deleted
        # all eight. That is D-21 ("shown, never hidden") failing silently, and it
        # cannot be fixed in the template: by the time Jinja sees the list the rows
        # are already gone.
        uncertain = [r for r in groups["requirement_only"]
                     if r["flag"] == "topic_uncertain"]
        browse = [r for r in groups["requirement_only"]
                  if r["flag"] != "topic_uncertain"]
        # Both halves are counted pre-cap. `requirement_only` is the true total of
        # the whole requirement-closing set; `browse` is that minus the uncertain
        # rows, which is what the collapsed list's "N of M" has to measure against
        # now that the uncertain rows are shown outside it.
        counts = dict(groups["counts"], uncertain=len(uncertain), browse=len(browse))
        groups = dict(groups, counts=counts,
                      relevant=groups["relevant"][:DISPLAY_LIMIT],
                      requirement_only=(uncertain[:DISPLAY_LIMIT]
                                        + browse[:DISPLAY_LIMIT]))
        # Group 2 is a badged view of the DISPLAYED group 1, so it is derived
        # from the capped list and can never hold a row group 1 does not show.
        groups["both"] = [r for r in groups["relevant"] if r["bucket_score"] > 0]

        # FR15 (D-17). Without this the UI silently degrades to "courses that
        # close a requirement" when nothing matches, which looks like an answer
        # but is not one. The old phrase_matched() could not express it:
        # normalisation divides by the term's own maximum, so the normalised max
        # is always exactly 1.0 whenever any raw cosine is nonzero.
        matched = groups["counts"]["relevant"] > 0

        actor = conn.execute(
            "SELECT user_id FROM app_user WHERE {} = ?".format(
                "advisor_id" if viewer_role == "advisor" else "student_id"),
            (advisor_id if viewer_role == "advisor" else student_id,)).fetchone()
        if actor:
            db.save_search(conn, student_id, actor["user_id"], TERM, phrase, groups)

    recent = conn.execute("""
        SELECT phrase, created_at FROM search_request
        WHERE student_id = ? ORDER BY request_id DESC LIMIT 5
    """, (student_id,)).fetchall()
    conn.close()

    return render_template(
        "results.html", student=student, outstanding=outstanding,
        numeric=numeric, phrase=phrase, groups=groups, counts=groups["counts"],
        recent=recent,
        matched=matched, meta=meta, viewer_role=viewer_role, advisor_id=advisor_id,
        term_label=TERM_LABEL,
        # The uncertain rows only, and only the displayed ones. Counted off the
        # pre-cap selection above rather than off the capped list, which read 0
        # for every student -- the callout could not fire at all.
        n_uncertain=sum(1 for r in groups["requirement_only"]
                        if r["flag"] == "topic_uncertain"))


@app.template_filter("meeting")
def meeting(o):
    days = o.get("days") or ""
    if not days and not o.get("begin_time"):
        return "time TBA"
    return "{} {}-{}".format(days or "--", o.get("begin_time") or "?",
                             o.get("end_time") or "?")


if __name__ == "__main__":
    if not os.path.exists(db.DB_PATH):
        raise SystemExit(
            "navigator.db not found. Run:\n"
            "  python ingest.py --reset\n"
            "  python seed.py\n"
            "  python descriptions.py --from-csv")
    # use_reloader=False: on Python 3.14 the watchdog reloader picks up changes
    # inside the standard library and restarts in a loop, so the server never
    # settles. Debug error pages are kept; only the file watcher is off.
    app.run(debug=True, port=5000, use_reloader=False)
