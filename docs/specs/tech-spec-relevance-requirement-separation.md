---
title: 'Separate pure relevance from requirement-weighted relevance in the ranker'
slug: 'relevance-requirement-separation'
created: '2026-11-11'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python 3.14'
  - 'Flask (server-rendered Jinja2)'
  - 'SQLite (navigator.db, derived)'
  - 'Pure-Python TF-IDF (no sklearn, no numpy)'
  - 'anthropic>=1.0 (optional, stage-2 reranker)'
files_to_modify:
  - 'rank.py'
  - 'rank_llm.py'
  - 'app.py'
  - 'templates/results.html'
  - 'static/style.css'
  - 'db.py'
  - 'schema.sql'
  - 'test_rank.py (new)'
  - 'test_rank_llm.py'
code_patterns:
  - 'Module-level docstring citing the decision IDs the module implements'
  - 'Hand-tuned module constants in UPPER_CASE with a comment saying why'
  - 'Dict-of-primitives passed between layers; no ORM, no dataclasses'
  - 'Jinja2 comments naming the UX component and UX-DR id each block renders'
  - 'Uncertainty is surfaced, never filtered (D-21, D-27)'
test_patterns:
  - 'Plain python scripts run directly: python test_rank_llm.py'
  - 'check(name, got, want) helper prints PASS/FAIL and returns bool'
  - 'main() tallies and returns a nonzero exit code on failure'
  - 'No pytest, no API key required'
---

# Tech-Spec: Separate pure relevance from requirement-weighted relevance in the ranker

**Created:** 2026-11-11

## Overview

### Problem Statement

The single blended score in `rank.py` lets requirement closure overwhelm topical
relevance, so genuinely relevant courses are buried below courses that merely close a
requirement.

Measured against the seeded student on the real Spring 2027 catalog (3,324 courses,
9,621 sections), searching **"climate policy"**:

| Shown at | Course | Relevance | Closes a requirement |
| --- | --- | --- | --- |
| 1 | NCLT 370 Policy and Politics in Immigration | 0.31 | yes |
| 2 | **BSC 471 Plant Physiology** | 0.24 | yes |
| 3 | MLC 362 Applied Linguistics | 0.17 | yes |
| 4 | PSC 664 Public Policy Analysis | **1.00** | no |
| 12 | GY 302 Climatology | 0.59 | no |

Plant Physiology outranks Public Policy Analysis for "climate policy". Applied
Linguistics outranks Climatology.

**Root cause.** `rank.py:131-135` computes
`score = bucket_score + relevance * W_RELEVANCE` and then adds `W_BOTH` whenever
relevance is merely nonzero:

```python
score = bucket_score * 1.0 + relevance * W_RELEVANCE   # W_RELEVANCE = 2.0
if bucket_score > 0 and relevance > 0:
    score += W_BOTH                                     # W_BOTH = 0.75
```

Relevance is normalised so that only the single best match in the whole term reaches
1.0, capping a requirement-free course at **2.00**. A course closing one bucket with
17% relevance scores `1.0 + 0.34 + 0.75` = **2.09**. Therefore:

> A requirement-closing course with 17% relevance outranks the single most relevant
> course in the entire term, and nothing without a requirement can ever beat it.

Three defects compound this:

1. **`W_BOTH` is paid on any nonzero relevance.** It was meant to reward genuine dual
   fit (D-19) but fires on TF-IDF noise — a single surviving shared token qualifies.
2. **The `limit=40` cut happens before the LLM reranker sees anything**
   (`rank.py:153` feeding `app.py:98`). A buried relevant course never reaches stage 2,
   so the reranker cannot rescue it.
3. **The stage-2 prompt repeats the bias.** `rank_llm.py` SYSTEM says "A section that
   does BOTH must rank above one that does only one of them", so the model reproduces
   the same distortion on the candidates it does see.

A fourth, visible symptom: ties at `score == 1.00` are broken alphabetically by subject
(`rank.py:138`), so for "storytelling" ranks 8-12 are AAST 300, AAST 352, AMS 345,
ANT 411, ANT 412 — alphabetical filler above genuinely relevant JCM courses.

### Solution

Stop blending. Produce three explicitly labelled result groups from one retrieval pass,
and let membership — not a weight — encode requirement closure:

1. **Fits your interest** — every course clearing the relevance floor, ranked on
   relevance alone. Requirement closure is ignored entirely in both membership and
   order.
2. **Also closes a requirement** — the subset of group 1 that closes an outstanding
   bucket, badged. Overlap with group 1 is intended.
3. **Closes a requirement, no topical match** — the remainder, collapsed behind a
   count, ranked on requirement closure where there is no relevance to compete with.

### Scope

**In Scope:**

- `rank.rank()` returns grouped results instead of one blended list.
- A relevance floor of 0.25 (normalised) governs membership of groups 1 and 2.
- `W_BOTH` is gated on the floor rather than on nonzero relevance.
- Candidate retrieval and truncation are reordered so the reranker sees the relevance
  pool before any cut.
- The stage-2 prompt ranks on topical fit only; requirement closure leaves the model.
- `templates/results.html` renders three groups; group 3 is collapsed.
- `phrase_matched()` becomes floor-aware, so the "nothing matched" callout fires when no
  course clears the floor.
- `recommendation.result_group` persists which group each row was shown in.
- A new `test_rank.py` covers grouping, the floor, and ordering.

**Out of Scope:**

- Replacing TF-IDF with embeddings. The module docstring names this as the escalation
  path; the interface in this spec does not change if it happens later.
- Retuning `W_MUST` / `W_BUCKET`. Group 3's internal order uses them unchanged.
- The advisor-side and sign-in work, and the chatbot direction — separate sprint items.
- Amending FR11/FR12 in `docs/PRD.md`. This spec requires that amendment but must not
  make it; see Notes.

## Context for Development

### Codebase Patterns

- **Decision IDs are load-bearing.** Every module docstring cites the `D-nn` / `F-nn`
  decisions it implements, and the elicitation running log governs over the PRD and the
  ERD. Code comments explain *why*, not *what* — match that register.
- **Constants are hand-tuned and say so.** `# weights -- tuned by hand against the test
  phrases, not learned`. New constants carry the same kind of comment.
- **Plain dicts between layers.** `rank.rank()` returns a list of dicts with
  `offering_id`, `offering`, `score`, `bucket_score`, `relevance_score`, `flag`,
  `buckets_closed`, `reason`, `other_sections`. No ORM, no dataclasses. Any new shape
  stays dict-of-primitives so `db.save_search` and Jinja2 keep working unchanged.
- **Uncertainty is shown, never filtered** (D-21, D-27). `topic_uncertain` zeroes
  relevance but must never remove a section or weaken its stated requirement closure.
- **Failure degrades, never 500s.** `app.py:100-104` catches every reranker exception
  and serves TF-IDF order, because a graded demo must not depend on a network call.
- **Templates name their components.** Each block in `results.html` carries a comment
  like `{# 8. CourseResultCard — UX-DR12 #}` tying it to `docs/UX Design.md`.
- **Dedup is by course, not section** (`rank.py:145-156`). One row per
  `(subject, course_number)` with `other_sections` counting the rest. This must stay
  true per group, and a course must not be deduped across groups 1 and 2 — the overlap
  is deliberate.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `rank.py` | Stage 1. `Index` (TF-IDF), `rank()`, `phrase_matched()`, `build_reason()`, the four weights. The primary change. |
| `rank_llm.py` | Stage 2. `SYSTEM` prompt carries the duplicated bias; `rerank()` takes the already-truncated list; `_validate()` is the F-26 guard and must not be weakened. |
| `app.py` | `_results_page()` lines 88-104 wire the two stages and apply `limit=40`; passes `results`, `matched`, `meta` to the template. |
| `templates/results.html` | Renders the single `<ol class="results">`. Becomes three groups. |
| `static/style.css` | Existing `.results`, `.badge`, `.callout`, `.empty`, `.r-*` classes to extend. |
| `db.py` | `save_search()` (line 208) writes `recommendation` rows; `outstanding_buckets()` supplies the bucket shape `rank()` consumes. |
| `schema.sql` | `recommendation` table gains `result_group`. |
| `test_rank_llm.py` | The test idiom to copy, and its `fake()` fixture builder. |
| `docs/PRD.md` | FR11, FR12, FR15 are the requirements this changes the meaning of. |
| `docs/UX Design.md` | UX-DR12 / UX-DR16 govern the result card and rank provenance. |
| `docs/archive/epics - bmad run (not voted).md` | Epic 3 stories 3.2 / 3.3 / 3.5 are the stories this supersedes. |

### Technical Decisions

**TD-1 — Three groups, not a re-weighting.** Membership encodes requirement closure, so
no weight has to be balanced against another. Re-weighting was considered and rejected:
any single-list weighting leaves a tunable constant that re-creates the distortion the
moment the catalog or the student's outstanding set changes.

**TD-2 — Relevance floor 0.25, normalised.** Reuses the cut `build_reason()` already
treats as "strong match to your phrase" (`rank.py:170`), so the floor and the prose
agree. On "climate policy" it admits Climatology (0.59) and excludes Applied Linguistics
(0.17) and Plant Physiology (0.24). Named `RELEVANCE_FLOOR`, with a comment saying it is
hand-set against the test phrases.

**TD-3 — Overlap between groups 1 and 2 is intended.** A course does not stop fitting
the phrase because it also closes a requirement. Group 1 is the honest answer to "what
fits my interest"; group 2 is a filtered, badged view of it. Neither list misrepresents
what it claims to rank.

**TD-4 — Group 2 orders by relevance, with `bucket_score` as tiebreaker.** Membership
already guarantees requirement closure, so ordering on it again would reintroduce the
distortion inside the group. FR12 (D-11, "two or more requirements surfaced above one")
is honoured as the tiebreaker among comparably relevant courses rather than as the
primary key.

**TD-5 — Group 3 orders by `bucket_score`, then `must_unmet`, then subject/number.**
This is where FR12 genuinely belongs: there is no relevance to compete with. It also
replaces today's purely alphabetical tiebreak, which is what put Anthropology of Europe
above relevant courses.

**TD-6 — The reranker ranks topical fit only.** Requirement closure is deterministic
data the code already has exactly; semantic relevance is the thing the model is actually
good at. Removing closure from `SYSTEM` deletes the duplicated bias and sharpens the
division of labour. `_validate()` and the privacy boundary in `build_prompt()` are
untouched — outstanding bucket names stay in the prompt only so the generated `reason`
can mention what a course closes.

**TD-7 — Group, then cap, then rerank, then re-group.** Grouping runs unlimited over the
deduped result set; the reranker receives the union of groups 1 and 2 (deduped by CRN,
capped at `MAX_CANDIDATES`); its returned order replaces group 1's order, and group 2 is
re-derived from it so both groups agree. Group 3 is never sent to the model — it has no
topical signal to rank on, and sending it would pay tokens for nothing.

**TD-8 — `score` is kept but demoted.** Nothing sorts on it any more, but it is a
`recommendation` column and the result card's title tooltip. It stays computed, with
`W_BOTH` gated on `RELEVANCE_FLOOR` so the number stops overstating noise.

**TD-9 — `phrase_matched()` becomes floor-aware.** Today it returns True when any cosine
anywhere exceeds zero, which can be true while the page shows zero topical matches.
Redefining it as "at least one course clears the floor" makes the FR15 callout fire when
the student would otherwise see a requirement-only page labelled as a ranking for their
phrase.

## Implementation Plan

### Tasks

- [ ] Task 1: Add the relevance floor and gate `W_BOTH` on it
  - File: `rank.py`
  - Action: Add `RELEVANCE_FLOOR = 0.25` beside the existing weights with a comment
    noting it is hand-set and matches `build_reason()`'s "strong match" cut. Change the
    bonus condition from `relevance > 0` to `relevance >= RELEVANCE_FLOOR`.
  - Notes: Leave `W_BUCKET`, `W_MUST`, `W_RELEVANCE` at their current values.

- [ ] Task 2: Split `rank()` into scoring and grouping
  - File: `rank.py`
  - Action: Keep the per-offering scoring loop and the course-level dedup as they are,
    both unlimited. Extract the grouping into `group_results(results, limit)` returning
    `{"relevant": [...], "both": [...], "requirement_only": [...], "counts": {...}}`.
    `relevant` = `relevance_score >= RELEVANCE_FLOOR` sorted by `-relevance_score`, then
    `-bucket_score`, then subject/number. `both` = the members of `relevant` with
    `bucket_score > 0`, same order. `requirement_only` = `bucket_score > 0` and
    `relevance_score < RELEVANCE_FLOOR`, sorted by `-bucket_score`, then `-must_unmet`,
    then subject/number.
  - Notes: `limit` caps `relevant` and `requirement_only` independently; `both` is a
    subset and needs no cap. `counts` carries the pre-cap totals so the template can say
    "61 more" truthfully. Dedup by `(subject, course_number)` stays within a group, so a
    course may appear in both `relevant` and `both` — TD-3.

- [ ] Task 3: Make `rank()` return the grouped structure
  - File: `rank.py`
  - Action: Have `rank()` return `group_results(...)`. Update the docstring to state the
    three groups, the floor, and that nothing is filtered for uncertainty.
  - Notes: This is a breaking interface change with exactly three callers — `app.py`,
    `test_rank_llm.py`, `test_rank.py`. Do not keep a compatibility shim.

- [ ] Task 4: Make `phrase_matched()` floor-aware
  - File: `rank.py`
  - Action: Return True when at least one similarity, after normalisation, reaches
    `RELEVANCE_FLOOR`. Update the docstring to say the callout now fires when no course
    clears the floor, not merely when nothing scored above zero.
  - Notes: Normalisation divides by the term's own maximum, so guard the case where
    every similarity is zero.

- [ ] Task 5: Reorder `build_reason()` for the new grouping
  - File: `rank.py`
  - Action: The "strong match" / "some overlap" phrasing must agree with the floor: at or
    above the floor reads as a match, below it must not claim topical fit at all.
  - Notes: Group 3 rows get a reason about what they close and nothing about the phrase.

- [ ] Task 6: Remove the requirement bias from the stage-2 prompt
  - File: `rank_llm.py`
  - Action: Rewrite `SYSTEM` to rank on fit to the interest phrase alone. Delete "A
    section that does BOTH must rank above one that does only one of them". Keep every
    hard rule: CRNs only from the list, never invent, never drop for poor fit, flag
    TOPIC-ROTATES, one short reason under 20 words.
  - Notes: `build_prompt()` keeps the outstanding bucket names so a reason can say what a
    course closes. Do not touch `_validate()` — it is the F-26 / D-16 guard and the whole
    safety argument.

- [ ] Task 7: Rerank the relevance pool, then re-derive the groups
  - File: `rank_llm.py`
  - Action: Add `rerank_groups(groups, phrase, outstanding, model=None)`. Build the
    candidate pool as `relevant` plus any `both` members not already in it, deduped by
    CRN, capped at `MAX_CANDIDATES`. Call the existing `rerank()` on that pool. Apply the
    returned order to `relevant`, then re-derive `both` by filtering `relevant` on
    `bucket_score > 0`. Return `requirement_only` untouched.
  - Notes: `meta` gains `pool` (candidates sent) so UX-DR16 provenance can state it.
    `rerank()` keeps its current signature — `rerank_groups` wraps it.

- [ ] Task 8: Rewire `_results_page()`
  - File: `app.py`
  - Action: Call `rank.rank(idx, outstanding, phrase)` for grouped results, then
    `rank_llm.rerank_groups(...)` inside the existing try/except. Pass `groups` to the
    template instead of `results`. Keep `n_uncertain` but compute it across groups 1
    and 3.
  - Notes: The except branch must leave `groups` as the deterministic grouping — the
    fallback contract in the docstring is unchanged.

- [ ] Task 9: Persist which group a recommendation was shown in
  - File: `schema.sql`, `db.py`
  - Action: Add `result_group TEXT NOT NULL` to `recommendation`. Change
    `save_search(conn, student_id, actor_user_id, term, phrase, groups)` to walk the
    three groups, writing `result_group` of `'relevance'`, `'both'`, or
    `'requirement_only'` and `rank` numbered from 1 within each group.
  - Notes: `navigator.db` is derived and gitignored, so this needs no migration —
    `python ingest.py --reset && python descriptions.py --from-csv && python seed.py`.
    Say so in the task output; `README.md` already documents that sequence.

- [ ] Task 10: Render the three groups
  - File: `templates/results.html`, `static/style.css`
  - Action: Replace the single `<ol class="results">` with three sections: "Fits your
    interest" (relevance only, stating that requirements are ignored here), "Also closes
    a requirement" (badged), and a `<details>` holding "N more close a requirement but
    do not match <phrase>". Keep the existing result-card markup for all three. Add the
    Jinja2 component comments naming the new blocks, matching the file's convention. Add
    the group heading styles to `style.css` using the existing tokens.
  - Notes: UX-DR25 — nothing truncated. Every group needs a designed empty state per
    UX-DR (Story 8.4): group 1 empty is the FR15 case; group 2 empty is the honest and
    useful "nothing that fits also closes a requirement".

- [ ] Task 11: Update the rank provenance line
  - File: `templates/results.html`
  - Action: State that ordering within "Fits your interest" is topical only and that
    requirement closure is applied as grouping, not as score. Keep the dropped-CRN count
    (FR18) exactly as it reads today.

- [ ] Task 12: Write `test_rank.py`
  - File: `test_rank.py` (new)
  - Action: Follow `test_rank_llm.py` exactly — module docstring, `fake()`-style fixture
    builders, `check(name, got, want)`, `main()` returning nonzero on failure, runnable
    as `python test_rank.py` with no API key. Cover: a course below the floor is excluded
    from groups 1 and 2 and present in group 3; a course at exactly 0.25 is included;
    `relevant` order is independent of `bucket_score`; `both` is a subset of `relevant`
    in the same relative order; `W_BOTH` is not paid below the floor; `topic_uncertain`
    lands in group 3 with its closure intact; `counts` reports pre-cap totals;
    `phrase_matched()` is False when every course is below the floor.
  - Notes: Build the index from a small hand-written offering list, not from
    `navigator.db`, so the test needs no database.

- [ ] Task 13: Fix `test_rank_llm.py` for the new shapes
  - File: `test_rank_llm.py`
  - Action: Update the fixtures and assertions for the grouped return and the rewritten
    `SYSTEM`. Add a case asserting `rerank_groups` re-derives `both` from the reranked
    `relevant` order. Keep every existing `_validate()` assertion — the invented-CRN
    guard is not in scope to change.

- [ ] Task 14: Re-measure and record the before/after
  - File: `docs/specs/tech-spec-relevance-requirement-separation.md`
  - Action: Re-run the three test phrases ("climate policy", "storytelling", "rockets and
    propulsion") and append the resulting group-1 top five to this spec beside the
    before table.
  - Notes: This is the evidence the fix worked, and the write-up material for the
    deliverable.

### Acceptance Criteria

- [ ] AC 1: Given the seeded student and the phrase "climate policy", when the page
  renders, then "Fits your interest" leads with PSC 664 Public Policy Analysis, and
  neither BSC 471 Plant Physiology (0.24) nor MLC 362 Applied Linguistics (0.17) appears
  in it.
- [ ] AC 2: Given the same search, when "Also closes a requirement" renders, then every
  row in it closes at least one outstanding bucket and also appears in "Fits your
  interest".
- [ ] AC 3: Given the same search, when the collapsed group renders, then it states the
  true count of courses that close a requirement without clearing the relevance floor,
  and expanding it lists them ordered by requirement closure.
- [ ] AC 4: Given the phrase "storytelling", when "Fits your interest" renders, then no
  row in the first ten has `relevance_score` of 0.00 — the alphabetical filler is gone.
- [ ] AC 5: Given a course whose relevance is exactly 0.25, when results are grouped,
  then it is included in "Fits your interest".
- [ ] AC 6: Given two courses with equal relevance above the floor where one closes two
  buckets and the other closes none, when group 1 is ordered, then their relative order
  is decided by the bucket tiebreaker, and removing the bucket data does not change the
  order of any other pair.
- [ ] AC 7: Given a phrase where no course clears the floor, when the page renders, then
  the FR15 "nothing matched" callout is shown and "Fits your interest" renders its empty
  state rather than requirement-only rows.
- [ ] AC 8: Given the reranker is available, when a search runs, then the candidate pool
  sent to it is the union of groups 1 and 2 drawn before any display cap, and a course
  that would have fallen outside the old `limit=40` can appear in the reranked top ten.
- [ ] AC 9: Given the reranker returns a CRN that was not in its input, when results are
  validated, then it is dropped and the dropped count is displayed — unchanged from
  today.
- [ ] AC 10: Given the reranker raises any exception, when the page renders, then the
  deterministic grouping is served with all three groups intact and the provenance line
  says the reranker was unavailable.
- [ ] AC 11: Given a section flagged `topic_uncertain`, when results are grouped, then it
  appears in group 3 with its requirement closure stated plainly and its uncertainty
  flag shown, and it is never silently dropped (D-27).
- [ ] AC 12: Given a completed search, when `recommendation` rows are read back, then
  each carries a `result_group` of `relevance`, `both`, or `requirement_only`, with
  `rank` numbered from 1 within its group.
- [ ] AC 13: Given `python test_rank.py` and `python test_rank_llm.py` are run with no
  `ANTHROPIC_API_KEY` set, then both report all assertions passing and exit 0.

## Additional Context

### Dependencies

- No new packages. TF-IDF stays pure Python and the dependency list stays Flask alone
  plus the optional `anthropic>=1.0`.
- `navigator.db` must be rebuilt after Task 9 (`ingest.py --reset`, then
  `descriptions.py --from-csv`, then `seed.py`). The inputs are in `data/`, so this is
  offline and takes about a minute.
- Blocks nothing. The advisor-side and sign-in sprint items are independent; the chatbot
  direction consumes this grouping and should be planned after it lands.

### Testing Strategy

**Unit** — `test_rank.py`, new, no database and no API key: the floor boundary at
exactly 0.25, group membership and the subset relation, ordering independence from
`bucket_score`, `W_BOTH` not paid below the floor, `topic_uncertain` routing, pre-cap
counts, `phrase_matched()` at the floor.

**Integration** — `test_rank_llm.py`, extended: `rerank_groups` re-derives `both` from
the reranked `relevant`, candidates are pooled before the cap, and every existing
`_validate()` invented-CRN assertion still holds.

**Manual** — run the three phrases through the real catalog and confirm AC 1 through
AC 4 and AC 7 on screen; force `NAVIGATOR_RANKER=tfidf` and then `llm` with a bad key to
confirm AC 10's fallback renders all three groups.

**Regression guard** — the before table in the Problem Statement is the baseline. Task 14
records the after.

### Notes

**Required documentation follow-up, deliberately not done here.** This spec changes what
two accepted requirements mean, and the elicitation running log — not this repository —
governs. It needs a new decision recorded by Jaxon before `docs/PRD.md` is edited:

- **FR11 (D-19, F-41)** currently reads "Sections that close an outstanding requirement
  **and** match the phrase rank above sections doing either alone." Under this design
  they are no longer ranked above — they are grouped separately. D-19's intent survives;
  its single-list mechanism does not.
- **FR12 (D-11, F-14, A-05)** "Sections closing two or more outstanding requirements are
  surfaced above sections closing one" becomes a tiebreaker in groups 1 and 2 and the
  primary key in group 3 — see TD-4, TD-5.
- **FR15 (D-17)** is strengthened rather than changed: the callout now fires on the floor
  instead of on nonzero cosine.
- `docs/UX Design.md` gains the three group headings and their empty states;
  UX-DR12 and UX-DR16 need amending.
- `docs/archive/epics - bmad run (not voted).md` Epic 3 stories 3.2 and 3.3 are
  superseded by this spec and should be reconciled when that backlog is promoted.

**Known limitations.**

- The floor is a hand-set constant against three test phrases, exactly as the existing
  weights are. It is honest but not learned, and a different catalog could want a
  different number. The comment must say so.
- Normalising relevance against the term's best match means the floor is relative: on a
  phrase where the whole catalog matches weakly, 0.25 of a weak maximum is still weak.
  TD-9's floor-aware callout is the mitigation, not a fix.
- TF-IDF cannot tell that "climate" and "warming" are related. That is the embeddings
  escalation path the module docstring already names, out of scope here.

**Future considerations.** The grouped return is the natural input to the chatbot
direction — "these fit, these also close something, these only close something" is
already the shape a conversational refinement loop needs. Keep `group_results()` free of
Flask and Jinja2 concerns so that reuse costs nothing.
