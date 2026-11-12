# Story 7.7: See what each advisee is working on in the search result

Status: done

<!-- Created 2026-11-11 by bmad-create-story. First per-story file in this project:
     until now a story's full context was its section in docs/epics.md
     (sprint-status.yaml:16-17). epics.md remains the backlog of record — this file
     is dev context for one story and does not replace it. -->

## Story

As an advisor,
I want each search result to show that student's depth study and the words they last searched,
so that I recognise the right student and know what they are pursuing before opening them.

## Acceptance Criteria

1. **Given** an advisee with a depth-study label, **when** the row renders, **then** the label
   is shown as that student's own working label, not as a confirmed programme of study.
2. **Given** an advisee with no label recorded, **when** the row renders, **then** it says the
   label is not recorded rather than leaving the field blank.
3. **Given** an advisee who has run searches, **when** the row renders, **then** it shows their
   most recent interest phrases, attributed as what the student typed.
4. **Given** an advisee who has never searched, **when** the row renders, **then** it says so,
   and no interest is inferred from their coursework.
5. **Given** any row, **when** it renders, **then** nothing on it asserts whether a course or a
   phrase fits the depth study — that judgment stays the advisor's.

## Tasks / Subtasks

- [x] Task 1: Seed a fixture that exercises AC 2 and AC 4 (AC: 2, 4)
  - [x] Append a fourth entry to `STUDENTS` in `seed.py:19` with `depth_study_label=None`
  - [x] Give it no `COMPLETED` entry — `COMPLETED.get(i, [])` at `seed.py:144` already
        returns `[]` for a missing index, so no code change is needed for that
  - [x] Do not give it any `search_request` rows — AC 4 needs a never-searched advisee
  - [x] Append it **last**; see the id-stability note in Dev Notes before reordering
  - [x] Re-run `python seed.py` and confirm four advisees on `/advisor/1`

- [x] Task 2: Supply the two fields to `advisor_view` (AC: 1, 2, 3, 4)
  - [x] `depth_study_label` needs no query work: `db.advisees` is `SELECT * FROM student`
        (`db.py:202-205`), so it already reaches the template as `row.student.depth_study_label`
  - [x] Add a `db.py` helper returning recent phrases per student, and call it **once** for
        the whole advisee set, not once per advisee — see the N+1 note in Dev Notes
  - [x] Add the result to each entry of the `summary` list built at `app.py:74-81`

- [x] Task 3: Render the two fields on the existing advisee row (AC: 1, 2, 3, 4, 5)
  - [x] Extend the `AdviseeRow` table at `templates/advisor.html:13-33` — it is a `<table
        class="grid">`, so add header cells and body cells together or the columns shift
  - [x] Label the depth study as the student's own working label (D-22), reusing the wording
        already shipped at `results.html:94-95` so the two screens cannot diverge
  - [x] Render "not recorded" for a null label (AC 2) and a never-searched message (AC 4)
        as field-level copy — **not** as a UX-DR18 EmptyState variant; see Dev Notes
  - [x] Attribute the phrases as what the student typed (AC 3)
  - [x] Assert nothing about fit between phrase, course and depth study (AC 5)

- [x] Task 4: Verify against rendered HTML (AC: 1-5)
  - [x] Render `/advisor/1` and assert each of the five criteria against the HTML, including
        the two fixture cases, following the harness pattern from Story 3.6's review
  - [x] Re-render under `jinja2.StrictUndefined` — a misspelled field renders empty rather
        than raising, which is how the result page lied for two commits
  - [x] Confirm `/advisor/1/student/<id>` and `/student/<id>` still render (shared `base.html`)

- [x] Task 5: Update the records this story changes
  - [x] `sprint-status.yaml`: 7.7 → review (the dev-story DoD ends at review, not
        done), and refresh the roll-up tally
  - [x] `docs/epics.md`: Story 7.7 status, and the Epic 7 status table row
  - [x] `UX Design.md:125` describes component 15 `AdviseeRow` as "One student in the advisor
        list, with open-requirement count" — now understates it; amend or note it

## Dev Notes

### Both fields already exist — this is a rendering story

`student.depth_study_label` is at `schema.sql:37` and `search_request.phrase` at
`schema.sql:206`. Neither reaches the advisor screen. Confirmed against the live database:

```
Jordan Reyes      Cognitive science                93 searches
Rosa Delgado      Public health and storytelling   85 searches
Tobias Lindqvist  Environmental policy             63 searches
```

### Why Task 1 comes first

All three seeded advisees have a label and have searched, so **AC 2 and AC 4 have no
exercisable fixture**. Without Task 1 those two branches ship unverified. That is the exact
shape of the Story 3.6 defect, where an unexercised branch rendered a falsehood for two
commits before anyone opened the page.

### Re-seeding is safe: student ids are stable

`student.student_id` is `INTEGER PRIMARY KEY` with no `AUTOINCREMENT` anywhere in
`schema.sql`, and the database has no `sqlite_sequence` table. On an emptied table SQLite
restarts rowids at 1, so `python seed.py` keeps Jordan/Rosa/Tobias as ids 1/2/3 in insertion
order and appends the fixture as id 4. This matters because the doc set, the ranker spec's
fixtures and Story 3.6's review harness all address students by number. **Append the fixture
last; do not insert it mid-list.**

`seed.py`'s `__main__` deletes `search_request` before reseeding (`seed.py:165`), so the reseed
also clears the 185 `search_request` rows Story 3.6's review added on 2026-11-11. That is
intended, not collateral: those rows are review noise and make every student's most recent
phrase "rockets and propulsion", which would otherwise obscure AC 3.

### Do not make the N+1 worse

`advisor_view` already calls `db.outstanding_buckets` once per advisee (`app.py:76`). Story
7.6's sixth acceptance criterion calls this out as a defect to avoid compounding ("ten queries
each"). Fetch recent phrases for the whole advisee set in one grouped query rather than adding
a second per-advisee round trip. `_results_page` has an inline per-student version at
`app.py:165-166` (`ORDER BY request_id DESC LIMIT 5`) — reuse its ordering, but put the new
query in `db.py` so 7.6 can reuse it instead of copying a third variant.

### The copy is the hard part, not the Jinja

- **D-22** — the depth study is a free-text working label and ranking never reads it. The
  results page already says this at `results.html:94-95`: "Working depth study: … (free text
  only — ranking never reads it, D-22)". Match it rather than inventing new phrasing.
- **D-26** — nothing is approved before the third-year review, so the label must not read as a
  confirmed programme of study (AC 1). `advisor.html:7-8` already states the no-approval rule.
- **F-04** — the advisor screen must never assert; it informs. AC 5 is this evidence item
  applied to the row.
- **AC 4** forbids inferring interest from coursework. Say the student has not searched; do
  not substitute their completed courses as a proxy.

### AC 2 and AC 4 are not UX-DR18 variants

UX-DR18's `EmptyState` is a whole-list component (`advisor.html:36` carries its "no advisees"
variant). AC 2 and AC 4 are **field-level** copy inside a populated row. Keep them distinct:
UX-DR18's variant count has already been miscounted twice in this project, and Story 7.6 — not
this story — is what adds the next variant. Do not increment UX-DR18 here.

### Testing standards

There is no committed template test; `test_rank.py` and `test_rank_llm.py` cover the ranker
only, and run as plain scripts (`python test_rank.py`, exit 0, no pytest). Story 3.6's review
harness established the pattern for page assertions: render through `app.test_client()` and
assert against the returned HTML with expectations recomputed from `db`/`rank` rather than
copied from the story. Follow it, and keep `NAVIGATOR_RANKER=tfidf` so nothing depends on a
network call.

### Project Structure Notes

- Touches `templates/advisor.html`, `app.py` (`advisor_view`), `db.py` (one new helper),
  `seed.py` (the fixture). No schema migration: both columns exist.
- Shares no file with Lane A (1.5: `app.py` routes, `schema.sql`, a new sign-in template) —
  but both edit `app.py`, so if 1.5 runs concurrently, land this story first. It is Lane B and
  startable today; 1.5 is gated on the D-33 running-log entry.
- **Story 7.6 reuses the row this story builds** (`epics.md:1674`) and must follow it, not run
  beside it: both edit `templates/advisor.html`.
- Variance from UX-DR19 as written: the DR names three fields (student, classification, open
  count) and this story adds two more. The DR text needs amending, which is why Task 5 carries
  `UX Design.md:125`.

### References

- [Source: docs/epics.md#Story 7.7] — story statement, all five acceptance criteria, size S,
  Lane B, "Depends on: nothing", dependency direction corrected 2026-11-11
- [Source: docs/epics.md#Epic 7] — "Advise a student in one pass", FR28-FR32
- [Source: docs/PRD.md:236] — FR28: an advisor can see their advisees with a count of each
  one's outstanding requirements (D-01, D-25)
- [Source: docs/epics.md:483] — UX-DR19: build `AdviseeRow` showing the student, their
  classification, and a count of open requirements
- [Source: docs/UX Design.md:125] — component 15 `AdviseeRow`; [:145] advisor screen inventory
- [Source: docs/sprint-plan.md:86] — 7.7 ready for dev, no dependency on sign-in
- [Source: schema.sql:37] — `student.depth_study_label`; [:206] D-22, the phrase is the whole
  input: no stored topic, no career
- [Source: db.py:202-205] — `db.advisees` is `SELECT *`, so the label already reaches the view
- [Source: app.py:66-84] — `advisor_view` and the `summary` list this story extends
- [Source: templates/advisor.html:13-33] — the `AdviseeRow` table to extend (row loop :15-32)
- [Source: templates/results.html:94-95] — existing D-22 depth-study wording to match
- [Source: docs/epics.md#Story 7.6] — sixth criterion, the `advisor_view` N+1 warning

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code)

### Debug Log References

- `python test_advisor_row.py` -> exit 0, 30 assertions, ALL PASS
- `python test_rank.py` -> exit 0, 36 assertions · `python test_rank_llm.py` -> exit 0, 20
- Story 3.6's review harness re-run as a regression check -> 63/63, exit 0

### Completion Notes List

**Three of the five criteria had no exercisable fixture, and fixing that was most of the
work.** AC 2 (no label) and AC 4 (never searched) were unverifiable because all three seeded
advisees had a depth-study label and had searched. A fourth advisee is now seeded -- Noor
Haddad, `depth_study_label` NULL, no searches, no completed coursework. Appending her was safe
because `student_id` is `INTEGER PRIMARY KEY` with no `AUTOINCREMENT` and the database has no
`sqlite_sequence`, so rowids restart at 1 on an emptied table and students 1-3 keep their ids.

**Then AC 3 lost its own fixture to that fix.** `seed.py` deletes `search_request` on every
run, so after reseeding *nobody* had searched and "most recent phrases" had nothing to render.
`seed.py` now carries a deterministic `SEARCHES` map graded 3 / 2 / 1 / 0 phrases across the
four advisees. This was not in the plan and is the more useful finding: before this story, AC 3
passed only because of search rows left behind by whoever last used the app -- 185 of which had
been written by Story 3.6's review earlier the same day, making every student's most recent
phrase "rockets and propulsion". Reseeding cleared those.

**Rendered as two stacked fields in the Student cell, not two new columns.** The `.grid` is
already five wide, UX-DR25 forbids truncating either field, and Story 8.5 records this table as
unwrapped by `.scroll-x` -- so two more columns would scroll the page body and breach UX-DR33.
Column count is unchanged.

**`db.recent_phrases` takes the whole advisee set in one query** rather than one call per
advisee, because `advisor_view` already runs `outstanding_buckets` per advisee and Story 7.6's
last criterion exists to answer for that; a second per-advisee round trip would deepen it. It
returns distinct phrases (a student who searched the same words four times told the advisor one
thing) and omits never-searched students entirely, so AC 4 is a real absence rather than a
silent empty list.

**AC 5 is checked against the row cells, not the page.** The note above the table uses the word
"fits" to *deny* that any judgment is being made, so a page-wide word search failed on the one
sentence that satisfies the criterion. The assertion is scoped to the rendered cells.

**One deviation: no `project-context.md` exists**, so the DoD's "dependencies within scope"
item was checked against `requirements.txt` and the existing imports instead. Nothing new was
added -- stdlib `re`/`os`, plus `jinja2`, already a Flask dependency.

### File List

- `templates/advisor.html` — modified: two stacked fields in the Student cell; framing note
- `app.py` — modified: `advisor_view` fetches recent phrases once and passes them per advisee
- `db.py` — modified: added `recent_phrases(conn, student_ids, limit=3)`
- `seed.py` — modified: fourth advisee fixture, `TERM`, and the `SEARCHES` map
- `static/style.css` — modified: `.advisee-meta`, `.meta-label`, `.own-words`, `.not-recorded`
- `test_advisor_row.py` — **new**: 30 assertions over rendered HTML, incl. StrictUndefined
- `docs/stories/story-7.7.md` — **new**: this file
- `docs/epics.md` — modified: Story 7.7 status, Epic 7 table row, UX-DR19 amendment
- `docs/sprint-status.yaml` — modified: 7.7 → review, roll-up tally
- `docs/UX Design.md` — modified: component 15 `AdviseeRow`, UX-DR19 amendment

## Change Log

| Date | Change | Why |
|---|---|---|
| 2026-11-11 | Story file created (`bmad-create-story`) | First per-story file in the project; `sprint-status.yaml:16` recorded that none existed |
| 2026-11-11 | Seeded a fourth advisee with no label and no searches | AC 2 and AC 4 were unverifiable against the existing three advisees |
| 2026-11-11 | Added a deterministic `SEARCHES` fixture to `seed.py` | Reseeding wiped `search_request`, which took AC 3's fixture with it; an AC must not depend on ad-hoc browsing |
| 2026-11-11 | Added `db.recent_phrases`, one query per advisee set | Avoids compounding the `advisor_view` N+1 that Story 7.6's last criterion must answer for |
| 2026-11-11 | Stacked both fields in the Student cell | Five-column `.grid` is unwrapped by `.scroll-x` (Story 8.5); more columns would breach UX-DR33 |
| 2026-11-11 | Added `test_advisor_row.py` | First committed page-level test; the StrictUndefined guard is the defect class that hid the Story 3.6 bug |
| 2026-11-11 | Amended UX-DR19 and component 15 in both copies | The DR named three fields; the row now carries five |
