# Story 1.6: Scope every student view to the signed-in user

Status: review

<!-- Created 2026-11-11 by bmad-create-story. Fourth per-story file.
     Depends on Story 1.5, which landed the session this story checks against.
     This is the story that finally closes Story 7.6's AC 3. -->

## Story

As a student,
I want my record reachable only by me and my advisor,
so that my completed coursework is not readable by anyone who can increment a number in a URL.

## Acceptance Criteria

1. **Given** a signed-in student, **when** `/student/<id>` is requested for a different
   student's id, **then** the request is refused and carries none of that student's data.
2. **Given** a signed-in advisor, **when** `/advisor/<id>/student/<id>` is requested for one of
   their own advisees, **then** the view opens as it does today.
3. **Given** a signed-in advisor, **when** the student named in the URL is not their advisee,
   **then** the request is refused, because D-25 makes one-advisor-per-student the whole rule.
4. **Given** a signed-in student, **when** an advisor route is requested, **then** the advisor
   view does not render.
5. **Given** any of the refusals above, **when** it is served, **then** it does not reveal
   whether that id exists, so the route cannot be used to enumerate students.
6. **Given** a search is saved, **when** `search_request.actor_user_id` is written, **then** it
   is the signed-in user — `app.py` today selects the first `app_user` row matching the id in
   the path, which is identity by assertion.

## Tasks / Subtasks

- [x] Task 1: One authorisation rule, in `auth.py` (AC: 1, 2, 3, 4)
  - [x] `may_view_student(conn, user, student_id)` — true for that student, or for the advisor
        of record (D-25). Nobody else, including another advisor
  - [x] `may_view_advisor(user, advisor_id)` — true only for that advisor; a student is refused
  - [x] Put both in `auth.py`, not inline in the views: three routes need the same answer and
        three copies of a permission check is how one of them drifts

- [x] Task 2: Enforce on every route that takes an id (AC: 1, 2, 3, 4, 5)
  - [x] `student_view`, `advisor_view`, `advisor_student_view`
  - [x] `advisor_student_view` must check **both** halves: that the caller is that advisor, and
        that the student is their advisee. Checking only the first lets an advisor read any
        student by putting their own id in the first segment
  - [x] Refuse with the **same response** used for a nonexistent id — see Dev Notes on AC 5

- [x] Task 3: The actor on a saved search is the signed-in user (AC: 6)
  - [x] Replace the `SELECT user_id FROM app_user WHERE student_id/advisor_id = ?` lookup in
        `_results_page` with `g.user["user_id"]`
  - [x] That query is identity by assertion: it answers "who owns this id in the URL", not
        "who is making this request". With 1.5 the real answer is in the session

- [x] Task 4: Tests (AC: 1-6)
  - [x] New `test_scoping.py`, plain-script style
  - [x] AC 5 is the one to test hardest: assert the refusal for an id that exists is
        **byte-identical** to the refusal for an id that does not
  - [x] Cover every (role, route) pair, not just the ones named in the criteria
  - [x] AC 6: run a search and assert the persisted `actor_user_id` is the signed-in user, and
        that it differs from the student when an advisor searches on their behalf

- [x] Task 5: Close Story 7.6, and the records (AC: all)
  - [x] **Story 7.6's AC 3 enforcement half** — this is what the story was blocked on. Tick it
  - [x] `epics.md`: Story 1.6 status, Story 7.6's AC 3 note, Epic 1 and Epic 7 table rows
  - [x] `sprint-status.yaml`: 1.6 → review, 7.6 unchanged at done but its caveat removed
  - [x] `Architecture.md` §7 and §9 — both now say authorisation is missing "until Story 1.6"
  - [x] `README.md` — same caveat in the "Not built" paragraph

## Dev Notes

### AC 5 decides the shape of every refusal

If a forbidden-but-real id returns 403 and a nonexistent id returns 404, the pair of responses
is an enumeration oracle: a classmate learns exactly which student ids exist by reading status
codes. So **every refusal returns the same thing a missing record returns** — `abort(404)`.
The views already `abort(404)` for a missing student or advisor, so the correct implementation
is to make the authorisation failure indistinguishable from it, and the test must assert the
two responses match rather than merely that both are refusals.

This costs honesty in the error message — a student who mistypes their own id is told the page
does not exist. That is the right trade here: the alternative tells everyone else which ids are
real, and this is education-record data (NFR11).

### `advisor_student_view` needs both halves checked

`/advisor/<advisor_id>/student/<student_id>` carries two ids and both are attacker-controlled.
Checking only that the caller owns `advisor_id` leaves the student id unchecked, so any advisor
could read any student by putting their *own* advisor id in the first segment. Checking only
the advisee relationship leaves the first segment free to name someone else. Check both.

### The actor lookup is the quiet one

`_results_page` currently resolves the actor with a `SELECT ... FROM app_user WHERE
student_id = ?` (or `advisor_id`) against the id **in the path**. Before 1.5 there was nothing
better. Now it is both wrong and misleading: it records who the URL is about rather than who
made the request, so every persisted search attributes itself to the record's owner. With the
scoping checks above the two usually coincide, which is exactly why this would survive
unnoticed — the one case where they differ is an advisor searching on a student's behalf
(FR29), which is the case the audit trail most needs to get right.

### What this does NOT cover

Sign-out is Story 1.7 — a session, once established, ends only when the cookie is discarded.
No rate limiting, no lockout, no audit log of refusals. All out of scope and already recorded.

### Project Structure Notes

- Modified: `auth.py`, `app.py`, plus the docs in Task 5. New: `test_scoping.py`
- No schema change, no new dependency, no template change: the refusal reuses Flask's 404
- `test_advisor_search.py` signs in as Dana and requests `/advisor/2` while counting SELECTs
  (`count_selects(client, "/advisor/2")`). That will start returning 404 under this story and
  the count comparison will break — it must be updated to sign in as the right advisor

### References

- [Source: docs/epics.md#Story 1.6] — the six criteria; D-33 keeps the `/student/<id>` pattern,
  so this is an added check rather than a re-routing; "Size M stands"
- [Source: docs/epics.md#Story 7.6] — the AC 3 enforcement half this story closes
- [Source: docs/epics.md:416] — NFR11, completed coursework is education-record data
- [Source: app.py] — `student_view`, `advisor_view`, `advisor_student_view`, and the actor
  lookup inside `_results_page`
- [Source: auth.py] — `current_user`, `home_endpoint_for`; the new checks belong beside them
- [Source: db.py:202] — `advisees`, which already answers "is this student mine"

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code)

### Debug Log References

- `python test_scoping.py` -> exit 0, 40 assertions, ALL PASS
- Full suite: `test_auth.py` 61 · `test_advisor_search.py` 31 · `test_advisor_row.py` 30 ·
  `test_rank.py` 36 · `test_rank_llm.py` 20 -> 218 assertions, all exit 0
- Story 3.6 harness re-run as a regression check -> 63/63, exit 0
- Authorisation matrix probed by hand across three signed-in users and every route

### Completion Notes List

**This closes Story 7.6's AC 3**, which is what the story was built for. 7.6's caveat has been
withdrawn in `epics.md` and `sprint-status.yaml` rather than left standing.

**Every refusal is `abort(404)`**, identical to a missing record. The test compares the
forbidden and nonexistent responses byte for byte rather than checking that both are refusals,
and separately asserts a permitted request is still distinguishable — without that second
check the first would pass on a route that refused everything.

**Both ids on the two-id route are checked.** Verifying only the advisor segment would let any
advisor read any student by putting their own id in it; verifying only the advisee
relationship would leave the segment free to name someone else. Both are attacker-controlled.

**AC 6 was the quiet one.** `_results_page` resolved the actor with a `SELECT ... FROM app_user
WHERE student_id = ?` against the id *in the path* — "who is this page about", not "who asked".
Every advisor search on a student's behalf was being attributed to the student. Now `g.user`,
with a test asserting the recorded actor is the advisor and specifically **not** the student.

**Three existing assertions changed meaning and were updated, not suppressed.**
`test_advisor_search.py` measured `/advisor/2` while signed in as Dana, which is now a 404, so
it signs in as Marcus for that route — the story file predicted this one. `test_auth.py`'s AC 7
check listed `auth.py`'s imports and expected exactly three; `auth.py` now imports the
project's own `db`, so the assertion was rewritten to express what AC 7 actually means — no
third-party dependency — instead of a brittle literal list.

### File List

- `auth.py` — modified: `may_view_student`, `current_may_view_student`, `may_view_advisor`
- `app.py` — modified: checks on all three id-bearing routes; actor is `g.user`
- `test_scoping.py` — **new**: 40 assertions
- `test_advisor_search.py` / `test_auth.py` — modified: see above
- `docs/stories/story-1.6.md` — **new**: this file
- `docs/epics.md` — modified: Story 1.6 status, **Story 7.6's AC 3 closed**, Epic 7 row
- `docs/sprint-status.yaml` — modified: 1.6 → review, 7.6's caveat withdrawn, roll-up
- `docs/Architecture.md` / `README.md` — modified: the "until Story 1.6" caveats are spent

## Change Log

| Date | Change | Why |
|---|---|---|
| 2026-11-11 | `may_view_student` / `may_view_advisor` in `auth.py` | Three routes need one answer; three copies is how one drifts |
| 2026-11-11 | Checks on all three id-bearing routes | AC 1-4; both ids checked on the two-id route |
| 2026-11-11 | Refusals are `abort(404)`, not 403 | AC 5: a 403/404 split is an id-enumeration oracle (NFR11) |
| 2026-11-11 | Actor on a saved search is `g.user` | AC 6: the old lookup recorded the record's owner, not the requester |
| 2026-11-11 | Story 7.6's AC 3 caveat withdrawn | The enforcement half it was waiting on is now met |
