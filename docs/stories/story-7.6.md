# Story 7.6: Find an advisee by name

Status: done

<!-- Created 2026-11-11 by bmad-create-story. Second per-story file; follows
     docs/stories/story-7.7.md, which built the row this story searches. -->

## Story

As an advisor,
I want to type part of a student's name and get my matching advisees,
so that I can open the right student during an appointment instead of reading the whole list.

## Acceptance Criteria

1. **Given** a signed-in advisor with advisees, **when** no query has been entered, **then**
   the full advisee list renders as it does today, with its open-requirement counts.
2. **Given** a query, **when** it matches part of an advisee's name, **then** only matching
   advisees are listed, each linking to the existing advisor-for-student view.
3. **Given** a query naming a real student who is not this advisor's advisee, **when** results
   render, **then** that student does not appear, and nothing in the response reveals that they
   exist. — **SPLIT, see Dev Notes.** The scoping half is reachable now; the enforcement half
   is not, and must be recorded unmet rather than ticked.
4. **Given** a query matching none of this advisor's advisees, **when** results render, **then**
   the empty state names the query and says the search covers this advisor's advisees only.
5. **Given** a search result list, **when** I copy the page URL and open it again, **then** the
   same query and the same results are reproduced.
6. **Given** an advisor with the full student body as advisees, **when** a query is run, **then**
   the page does not compute a requirement roll-up for every non-matching advisee —
   `advisor_view` calls `db.outstanding_buckets` once per advisee, which is ten queries each.

## Tasks / Subtasks

- [x] Task 1: Seed a second advisor with their own advisee (AC: 3)
  - [x] Add a second entry to `ADVISORS` in `seed.py:14`
  - [x] Give them one student, so a real non-advisee exists to query for
  - [x] Keep Dana Whitfield first and her four advisees in their current order — advisor and
        student ids are assigned by insertion order; see the id-stability note in Dev Notes
  - [x] Confirm `test_advisor_row.py` still passes: it reads `ADVISOR_ID = 1` and asserts
        against `db.advisees(conn, 1)`, which must be unchanged

- [x] Task 2: Scope the filter in SQL, not after the fact (AC: 2, 3, 6)
  - [x] Extend `db.advisees(conn, advisor_id)` with an optional name query rather than adding
        a second function — one query, so `advisor_id` and the name filter are ANDed and a
        non-advisee cannot be returned by construction
  - [x] Match on part of the name, case-insensitively
  - [x] Filter **before** the `outstanding_buckets` loop in `advisor_view` (`app.py:79`), not
        after — that loop is the ten-queries-per-advisee cost AC 6 names

- [x] Task 3: Add the search form and the no-query state (AC: 1, 5)
  - [x] GET form with `name="q"` on `/advisor/<id>`, mirroring the phrase search at
        `templates/results.html:159` so the two searches behave alike
  - [x] The query lives in the query string (UX-DR22), so the URL is copyable and reproducible
  - [x] With no query, render exactly today's full list — this is Story 7.1's state, now the
        no-query branch of a search

- [x] Task 4: Add the no-match empty state (AC: 4)
  - [x] Name the query back to the advisor and state that the search covers their advisees only
  - [x] Do **not** say whether a non-matching name belongs to a real student anywhere (AC 3)
  - [x] This is UX-DR18's **fifth** variant — Story 3.6 took it to four; do not write "fourth"

- [x] Task 5: Verify against rendered HTML (AC: 1-6)
  - [x] Extend `test_advisor_row.py`, or add a sibling, following its established pattern
  - [x] AC 6 is measurable, not a judgment call: count SELECTs with
        `sqlite3.Connection.set_trace_callback` and assert the count scales with *matches*,
        not with the advisee count
  - [x] AC 5: fetch the same URL twice and compare the rendered rows
  - [x] AC 3: query the other advisor's student by name against `/advisor/1` and assert both
        that they are absent and that the response never names them
  - [x] Re-run under `jinja2.StrictUndefined`, and re-run the Story 3.6 harness

- [x] Task 6: Update the records (AC: all)
  - [x] `sprint-status.yaml`: 7.6 → review, refresh the roll-up tally
  - [x] `docs/epics.md`: Story 7.6 status, Epic 7 table row, **and Story 7.1**, which this
        story modifies into the no-query state
  - [x] Record AC 3 as **partially met** with the reason, rather than ticking or failing it
  - [x] `UX Design.md` and `epics.md`: UX-DR18 gains its fifth variant (both copies)

## Dev Notes

### AC 3 splits in two, and only half is reachable

The sprint plan says this criterion "ships unmet until Lane A" because *"my advisees" is not a
defined set without a signed-in advisor*. That is right about enforcement and wrong about
scoping, and the two should not be recorded as one thing:

- **Scoping — reachable now.** The advisor is identified by the route (`/advisor/<advisor_id>`),
  so the set is defined. If the name filter is ANDed with `advisor_id` in a single SQL query, a
  non-advisee cannot be returned by construction, and the response can be checked to never name
  them. Task 1 seeds a second advisor so there is a real non-advisee to query for — without
  that fixture this half is not merely unverified but untestable, the same gap Story 7.7 hit.
- **Enforcement — not reachable.** Nothing stops anyone opening `/advisor/2` and seeing that
  advisor's students. There is no session and no ownership check; that is Story 1.5 and 1.6.

So: implement and verify the scoping half, and record AC 3 as **partially met — scoping
verified, enforcement blocked on 1.5/1.6**. Do not tick it. The sprint plan's instruction not
to tick it stands; this only makes the record more precise than "unmet".

### AC 6 is a real measurement, and the number is confirmed

`db.outstanding_buckets` issues exactly **10 SELECTs per student** — measured with
`set_trace_callback`, matching the criterion's claim (one requirement query plus one bucket
query for each of the nine bucket requirements). With four advisees the unsearched page costs
40. The fix is ordering, not caching: filter the advisee set in SQL, then loop. Filtering the
list *after* the loop would satisfy the visible behaviour of AC 2 while failing AC 6 silently,
which is the trap this criterion exists to catch.

### Seeding a second advisor: what is safe and what is not

Advisor and student ids are assigned in insertion order (`INTEGER PRIMARY KEY`, no
`AUTOINCREMENT`, no `sqlite_sequence` — verified for Story 7.7). **Keep Dana Whitfield first
and her four students in their current order**, and append the new advisor and their student
last. Students 1-4 and advisor 1 then keep their ids, which matters because:

- `test_advisor_row.py` hardcodes `ADVISOR_ID = 1` and asserts against `db.advisees(conn, 1)`
- Story 3.6's review harness addresses students 1, 2 and 3 by number
- The ranker spec's fixtures and most of the doc set name students by id

The new student will also appear on the home-page picker (`templates/home.html`), which lists
every `app_user`. That is correct — they are a real user — but it does mean the picker grows,
and `home.html` is the screen Story 1.5 deletes.

### One row component, two states

The story's own "Why" says the search must share one row component with the unsearched list or
the two will diverge. Story 7.7 just rebuilt that row (name, working depth study, recent
phrases, open count, open requirements). Render both the no-query list and the result list
through the same loop over `summary` — do not fork the markup.

### Copy constraints

- **AC 4** names the query back to the advisor. Escape it; it is user input rendered into HTML.
  Jinja autoescapes by default here, but the empty-state copy must not be marked `|safe`.
- **AC 3** forbids revealing that a non-matching name belongs to a real student. The empty
  state therefore says what the search *covers*, never what it *excluded*. "No advisee of yours
  matches X" is fine; "X is not your advisee" is not — it confirms X exists.
- The framing note Story 7.7 added above the table stays; it explains the two new fields.

### Testing standards

Plain scripts, no pytest: `python test_advisor_row.py`, exit 0, `PASS`/`FAIL` lines, a
`check(name, got, want)` helper. Expectations are recomputed from `db`, not copied from this
file. `NAVIGATOR_RANKER=tfidf` so nothing touches the network. The StrictUndefined sweep at the
end of `test_advisor_row.py` should grow to cover the new query URLs.

### Project Structure Notes

- Touches `templates/advisor.html`, `app.py` (`advisor_view`), `db.py` (`advisees`),
  `seed.py` (the second-advisor fixture), `test_advisor_row.py`.
- `db.advisees` has exactly one caller (`app.py:73`), so extending its signature is safe.
- Shares `app.py` and `advisor.html` with Story 7.7 — which is why 7.7 was built first and why
  these two must not run concurrently. 7.7 is at review; its changes are in the tree.
- Lane A (1.5/1.6) will later add the session this story's AC 3 needs. It also rewrites
  `/advisor/<id>` routing, so expect this story's scoping query to be revisited there.

### References

- [Source: docs/epics.md#Story 7.6] — the six acceptance criteria, size M, "startable before
  Lane A at a stated cost", "Modifies Story 7.1", "Adds a variant to Story 8.4"
- [Source: docs/epics.md#Story 7.1] — the list this story turns into the no-query state
- [Source: docs/epics.md#Story 7.7] / [docs/stories/story-7.7.md] — the row component reused
- [Source: docs/sprint-plan.md:86] — 7.6 startable, third criterion unmet until Lane A
- [Source: docs/UX Design.md:215] — UX-DR22, the query lives in the query string
- [Source: docs/UX Design.md:208] — UX-DR18, which gains a fifth variant here
- [Source: db.py:50-120] — `outstanding_buckets`, the 10-query-per-student cost
- [Source: db.py:202-205] — `advisees`, to be extended with the name filter
- [Source: app.py:66-91] — `advisor_view`, including the 7.7 `recent_phrases` call
- [Source: templates/results.html:159] — the GET search form to mirror

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code)

### Debug Log References

- `python test_advisor_search.py` -> exit 0, 31 assertions, ALL PASS
- `python test_advisor_row.py` -> exit 0, 30 · `test_rank.py` 36 · `test_rank_llm.py` 20
- Story 3.6's review harness re-run as a regression check -> 63/63, exit 0

### Completion Notes List

**AC 3 is split, as the Dev Notes planned, and is NOT ticked.** Scoping is met and verified;
enforcement is not reachable without a session and stays open against Stories 1.5/1.6. Seeding
a second advisor (Marcus Bell, with Priya Raman) is what made the scoping half testable at
all -- every student in the database belonged to the only advisor, so "a student who is not
this advisor's advisee" named nobody. The test asserts the stronger property: the empty state
for a real non-advisee is identical to the empty state for a name nobody has. A page saying
"not your advisee" would have passed a naive absence check while confirming the student exists.

**AC 6 was measured rather than argued.** Two of its assertions failed on the first run, both
by exactly one statement, and the code was right both times: a page with no matching advisees
also skips `db.recent_phrases`, which returns early on an empty id list instead of issuing an
`IN ()` query. So a no-match search saves 41 statements, not 40. The expectations were corrected
and the extra saving is now asserted in its own right.

**Scope lives in the SQL.** `db.advisees` ANDs the name filter into the same statement as
`advisor_id`. Filtering the returned rows in Python would look identical on screen, satisfy
AC 2, and fail AC 6 silently -- which is the trap that criterion exists to catch. LIKE
wildcards are escaped with `/` as the escape character, so a query of `%` looks for a literal
percent sign rather than returning the roster.

**Both list states share one row.** The no-query list and the search results run through the
same loop over `summary`, so the component Story 7.7 built cannot diverge between them -- the
risk this story's "Why" named.

**One deviation: the search input reuses `id="q"`,** the same id the phrase search uses on the
results page. They never render on the same page, so it is not a duplicate-id defect, and
keeping it matches the existing `label for="q"` idiom. Noted because a future combined screen
would have to rename one.

### File List

- `db.py` — modified: `advisees` gained an optional, SQL-level name filter
- `app.py` — modified: `advisor_view` reads `?q=` and narrows before the roll-up loop
- `templates/advisor.html` — modified: GET search form, "showing matches" note, fifth EmptyState
- `seed.py` — modified: second advisor and their advisee; `STUDENT_ADVISOR` mapping
- `test_advisor_search.py` — **new**: 31 assertions, incl. statement counting for AC 6
- `docs/stories/story-7.6.md` — **new**: this file
- `docs/epics.md` — modified: Story 7.6 status, Epic 7 row, Story 7.1, UX-DR18
- `docs/sprint-status.yaml` — modified: 7.6 → review, roll-up tally, Story 8.4 note
- `docs/UX Design.md` — modified: UX-DR18 now names five variants

## Change Log

| Date | Change | Why |
|---|---|---|
| 2026-11-11 | Story file created (`bmad-create-story`) | Second per-story file; follows 7.7 |
| 2026-11-11 | Seeded a second advisor and advisee | AC 3 had no non-advisee to query for; every student belonged to the only advisor |
| 2026-11-11 | Name filter ANDed into `db.advisees`' SQL | Makes scope structural (AC 3) and keeps non-matching advisees out of the ten-query roll-up (AC 6) |
| 2026-11-11 | Escaped LIKE wildcards with `/` | A query of `%` would otherwise return every advisee |
| 2026-11-11 | Added UX-DR18's fifth empty state | AC 4; states what the search covers, never what it excluded (AC 3) |
| 2026-11-11 | Added `test_advisor_search.py` | AC 3 and AC 6 are both fakeable by a test that only reads the page |
| 2026-11-11 | AC 3 recorded as split, not ticked | Scoping verified; enforcement blocked on 1.5/1.6 |
