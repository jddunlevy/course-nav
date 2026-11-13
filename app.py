"""Course Navigator -- Flask prototype.

Two roles, student and advisor (D-20, D-25). Signing in takes a credential
(D-33, Story 1.5): the role picker that stood in for authentication is gone, and
every route but the sign-in page requires a session. AR16 is reversed.

    python app.py      ->  http://127.0.0.1:5000
"""

import os

from flask import (Flask, abort, g, redirect, render_template, request,
                   session, url_for)

import auth
import config
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
# Read at import, not lazily: a missing or default secret must stop the process
# rather than surface later as a forgeable session (Story 1.5, AC 5). config
# raises MissingSecret, a SystemExit, with instructions for generating one.
app.secret_key = config.secret_key()

# Everything else requires a session. `static` is exempt or the sign-in page
# renders unstyled; `signin` is exempt or there is no way in.
PUBLIC_ENDPOINTS = {"static", "signin"}

_index = None


@app.before_request
def require_sign_in():
    """Serve the sign-in page for any unauthenticated request (AC 1).

    Served, not redirected: the criterion says the sign-in page is served, and
    keeping the requested URL lets `next` return the user where they were going
    after they sign in. The response carries no student or advisor data at all.
    """
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    conn = db.connect()
    try:
        user = auth.current_user(conn)
    finally:
        conn.close()
    if user is None:
        return render_template(
            "signin.html", term_label=TERM_LABEL, signed_out=None,
            next_url=request.full_path if request.query_string else request.path), 401
    g.user = user
    return None


@app.context_processor
def inject_signed_in_user():
    """The header names the signed-in user on every page (AC 4, UX-DR5)."""
    return {"signed_in_user": getattr(g, "user", None)}


@app.after_request
def never_cache_private_pages(response):
    """No signed-in page may sit in the browser cache (Story 1.7, AC 2).

    Clearing the session only stops the SERVER answering. The threat this story
    names is a shared advising-office machine, and a cached page is served by
    the browser itself -- the next person presses Back and reads the record
    without a request ever reaching Flask. `/static` is left cacheable: the
    stylesheet is not private.
    """
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
    return response


@app.route("/signout", methods=["POST"])
def signout():
    """End the session (Story 1.7).

    POST only. A GET sign-out fires from anything that fetches a URL -- a
    prefetching browser, an `<img src="/signout">` on any page the user
    visits -- which logs people out at a distance.

    Redirects to a BARE /signin with no `next`. Carrying `next` would send the
    next person who signs in straight back into the previous user's acting-as
    view, which is exactly what AC 3 forbids.
    """
    auth.logout()
    return redirect(url_for("signin", signed_out=1))


@app.route("/signin", methods=["GET", "POST"])
def signin():
    error = None
    next_url = request.values.get("next") or ""
    if request.method == "POST":
        conn = db.connect()
        try:
            user = auth.authenticate(conn, request.form.get("username"),
                                     request.form.get("password"))
        finally:
            conn.close()
        if user is not None:
            auth.login(user)
            # Only same-site relative paths, so `next` cannot be turned into an
            # open redirect to another host.
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            endpoint, kwargs = auth.home_endpoint_for(user)
            return redirect(url_for(endpoint, **kwargs))
        # AC 3: one message for both halves. Saying which was wrong turns the
        # form into a way to find out which usernames exist.
        error = "Sign-in failed. Check your username and password."
    return render_template("signin.html", error=error, next_url=next_url,
                           signed_out=request.args.get("signed_out"),
                           term_label=TERM_LABEL)


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
    """Open the signed-in user's own view (AC 2).

    This used to list every `app_user` for the caller to pick from. D-33 removed
    the picker outright rather than keeping it as a bypass: a public list of who
    exists, each name a working link into their record, was the thing the
    credential is for. `base.html` still links here, so the endpoint stays.
    """
    endpoint, kwargs = auth.home_endpoint_for(g.user)
    return redirect(url_for(endpoint, **kwargs))


@app.route("/student/<int:student_id>")
def student_view(student_id):
    # Story 1.6: the student, or their advisor of record (D-25). The refusal is
    # abort(404) and not 403 on purpose -- see the note on _results_page.
    if not auth.current_may_view_student(student_id):
        abort(404)
    return _results_page(student_id, viewer_role="student")


@app.route("/advisor/<int:advisor_id>")
def advisor_view(advisor_id):
    # Story 1.6, AC 4: a student requesting an advisor route gets the same
    # response as a request for an advisor who does not exist.
    if not auth.may_view_advisor(g.user, advisor_id):
        abort(404)
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
    summary = []
    for s in rows:
        outstanding = db.outstanding_buckets(conn, s["student_id"])
        summary.append({
            "student": s,
            "open_count": sum(1 for r in outstanding if not r["satisfied"]),
            # name AND code: the name is displayed, the code is what the link
            # to that requirement's own search carries.
            "open_reqs": [{"name": r["name"], "code": r["code"]}
                          for r in outstanding if not r["satisfied"]],
        })
    conn.close()
    return render_template("advisor.html", advisor=advisor, summary=summary,
                           query=query, term_label=TERM_LABEL)


@app.route("/advisor/<int:advisor_id>/student/<int:student_id>")
def advisor_student_view(advisor_id, student_id):
    # BOTH ids are attacker-controlled and both are checked. Checking only the
    # advisor half would let any advisor read any student by putting their own
    # id in the first segment; checking only the advisee half would let them
    # name someone else in it.
    if not (auth.may_view_advisor(g.user, advisor_id)
            and auth.current_may_view_student(student_id)):
        abort(404)
    return _results_page(student_id, viewer_role="advisor", advisor_id=advisor_id)


def _results_page(student_id, viewer_role, advisor_id=None):
    conn = db.connect()
    student = db.get_student(conn, student_id)
    if not student:
        abort(404)

    outstanding = db.outstanding_buckets(conn, student_id)
    numeric = db.numeric_progress(conn, student_id)
    phrase = (request.args.get("q") or "").strip()
    # Story 1.6 scoped records, not search controls: the screen is a property of
    # the query, so both roles get it from the one handler they share.
    no_prereq = request.args.get("no_prereq") == "1"
    # ?req=<requirement code> narrows every list to the courses that close that
    # one requirement. Validated against THIS student's outstanding set rather
    # than trusted: an unknown or already-satisfied code filters nothing, and
    # `req` is None in the template so the page does not claim it did.
    req_code = (request.args.get("req") or "").strip()
    req = next((r for r in outstanding
                if r["code"] == req_code and not r["satisfied"]), None)

    groups = rank.group_results([])
    matched = True
    n_prereq_hidden = 0
    n_req_hidden = 0
    meta = {"ranker": "tfidf"}
    if phrase:
        idx = get_index()
        results = rank.rank(idx, outstanding, phrase)
        # Both screens run before grouping and before the cap. Screening after
        # the cap would hide rows the page had already counted, so the stated
        # totals would describe a different set than the one on screen -- the
        # D-21 failure mode.
        if req:
            results, n_req_hidden = rank.filter_requirement(results, req["code"])
        if no_prereq:
            results, n_prereq_hidden = rank.filter_no_prereq(results)
        # Inside one requirement every row closes the same thing, so the
        # closure sort key is dead weight and relevance is the only ordering
        # left that means anything. That is what the link promises.
        groups = rank.group_results(results, order_by_relevance=bool(req))

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

        # Story 1.6, AC 6: the actor is whoever is signed in. This used to be a
        # SELECT for the app_user owning the id in the PATH, which answers "who
        # is this page about" rather than "who asked for it" -- identity by
        # assertion. The two coincide except in the one case the audit trail
        # most needs right: an advisor searching on a student's behalf (FR29).
        db.save_search(conn, student_id, g.user["user_id"], TERM, phrase, groups)

    # One row per phrase: the requirement links all search the same
    # depth-study words, so without the grouping this is five copies of one
    # phrase. MAX(request_id) keeps the ordering on recency rather than on
    # created_at, whose one-second resolution ties within a page load.
    recent = conn.execute("""
        SELECT phrase, MAX(created_at) AS created_at
        FROM search_request WHERE student_id = ?
        GROUP BY phrase ORDER BY MAX(request_id) DESC LIMIT 5
    """, (student_id,)).fetchall()
    conn.close()

    return render_template(
        "results.html", student=student, outstanding=outstanding,
        numeric=numeric, phrase=phrase, groups=groups, counts=groups["counts"],
        recent=recent,
        matched=matched, meta=meta, viewer_role=viewer_role, advisor_id=advisor_id,
        term_label=TERM_LABEL, no_prereq=no_prereq, n_prereq_hidden=n_prereq_hidden,
        req=req, n_req_hidden=n_req_hidden,
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
    # debug=False since Story 1.5: the Werkzeug debugger executes arbitrary
    # code through the browser on any traceback, which cannot sit beside a
    # credential store. It was already running with use_reloader=False, because
    # on Python 3.14 the watchdog reloader picks up changes inside the standard
    # library and restarts in a loop, so nothing is lost but the error pages.
    app.run(debug=False, port=5000, use_reloader=False)
