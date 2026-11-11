---
title: 'Separate pure relevance from requirement-weighted relevance in the ranker'
slug: 'relevance-requirement-separation'
created: '2026-11-11'
revised: '2026-11-11'
status: 'in-progress'
stepsCompleted: [1, 2, 3, 4, 5]
revision: 3
revision_note: >
  Revision 3, 2026-11-11. Tasks 1-9, 12, 13 and the Task 14 re-measurement have LANDED
  at commits 065d496 and 434c9cd; both test files report all assertions passing. Tasks
  10-11 (the template) did NOT land, so the result page currently renders "0 ranked
  courses" above a populated group set -- see the note under Tasks. Q-1 and Q-2 were
  ANSWERED by the owner on 2026-11-11 and Tasks 10-11 are unblocked; the answers are
  recorded in place below, and AC 2, AC 3 and AC 11 were rewritten to match them. The
  remaining template work is tracked as Story 3.6 in docs/epics.md, in sprint 1.
open_questions: ['D-35 (running-log entry and PRD amendment -- still outstanding)']
answered_questions:
  - 'Q-1 answered 2026-11-11: option (b), badges inside group 1; no group-2 section'
  - 'Q-2 answered 2026-11-11: option (b), the 8 uncertain-and-closing rows surface uncollapsed'
  - 'Group 3 relabelled a browse list (new finding: it is near phrase-invariant)'
  - 'D-36 (chat-led query construction) deferred past sprint 1'
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
code_patterns:
  - 'Module-level docstring citing the decision IDs the module implements'
  - 'Hand-tuned module constants in UPPER_CASE with a comment saying why'
  - 'Dict-of-primitives passed between layers; no ORM, no dataclasses'
  - 'Jinja2 comments naming the UX component and UX-DR id each block renders'
  - 'Uncertainty is surfaced, never filtered where closure exists (D-21, D-27)'
test_patterns:
  - 'Plain python scripts run directly: python test_rank.py'
  - 'check(name, got, want) helper prints PASS/FAIL and returns bool'
  - 'main() tallies and returns a nonzero exit code on failure'
  - 'No pytest, no API key required'
---

# Tech-Spec: Separate pure relevance from requirement-weighted relevance in the ranker

**Created:** 2026-11-11 · **Revised:** 2026-11-11 (revision 2)

> **Revision 3 note, 2026-11-11.** **Tasks 1–9, 12, 13 and the Task 14 re-measurement
> have landed** at commits `065d496` and `434c9cd`; `python test_rank.py` and
> `python test_rank_llm.py` both report all assertions passing. **Tasks 10–11 did not
> land**, and because Jinja2's default `Undefined` renders `{{ results|length }}` as `0`
> rather than raising, the result page currently shows "0 ranked courses" and "Nothing
> matched" above 55 relevant and 480 requirement-only rows. That is now **Story 3.6** in
> `docs/epics.md`, in sprint 1.
>
> **Q-1 and Q-2 are answered** — by the owner, 2026-11-11 — and Tasks 10–11 are
> unblocked. The answers are recorded in place in the section below, and AC 2, AC 3 and
> AC 11 were rewritten against them. One new finding came out of measuring Q-2 and is
> recorded there too: **group 3 is near phrase-invariant**, so it is relabelled as a
> browse list rather than presented as a result set. `D-36`
> (`design-chat-led-query-construction.md`) was **deferred** past sprint 1; Q-1's answer
> deliberately matches its decision 3, so that part of the template will not be rebuilt.
>
> **Revision 2 note, kept.** Revision 1 was reviewed adversarially and did not survive
> it. Three of its defects were Critical: a floor predicate that was a mathematical
> no-op, a persistence design that violated a `UNIQUE` constraint and would have 500'd on
> the happy path, and a task sequence that did not actually fix the truncation defect the
> spec exists to fix. Every finding was verified against the code and the live database
> before being accepted. Revision 2 addressed all of them.

## Overview

### Problem Statement

The single blended score in `rank.py` lets requirement closure overwhelm topical
relevance, so genuinely relevant courses are buried below courses that merely close a
requirement.

Measured against student 1 (Jordan Reyes) on the real Spring 2027 catalog — 3,324
courses, 9,621 sections, term 202710 — searching **"climate policy"**:

| Shown at | Course | Relevance | Closes a requirement |
| --- | --- | --- | --- |
| 1 | NCLT 370 Policy and Politics in Immigration | 0.31 | yes |
| 2 | **BSC 471 Plant Physiology** | 0.24 | yes |
| 3 | MLC 362 Applied Linguistics | 0.17 | yes |
| 4 | PSC 664 Public Policy Analysis | **1.00** | no |
| 12 | GY 302 Climatology | 0.59 | no |

Plant Physiology outranks Public Policy Analysis for "climate policy". Applied
Linguistics outranks Climatology.

**Root cause.** `rank.py:139-141` computes:

```python
score = bucket_score * 1.0 + relevance * W_RELEVANCE   # W_RELEVANCE = 2.0 (rank.py:87)
if bucket_score > 0 and relevance > 0:
    score += W_BOTH                                     # W_BOTH = 0.75 (rank.py:88)
```

Relevance is normalised against the term's own maximum (`rank.py:123`), so only the
single best match in the whole term reaches 1.0, capping a requirement-free course at
**2.00**. A course closing one bucket with 17% relevance scores `1.0 + 0.346 + 0.75` =
**2.096**. Verified: MLC 362's actual score is 2.0957; PSC 664's is 2.0000. Therefore:

> A requirement-closing course with 17% relevance outranks the single most relevant
> course in the entire term, and nothing without a requirement can ever beat it.

Three defects compound this:

1. **`W_BOTH` is paid on any nonzero relevance** (`rank.py:140`). It was meant to reward
   genuine dual fit (D-19) but fires on TF-IDF noise — one surviving shared token
   qualifies.
2. **The display cut precedes the reranker.** `app.py:103` calls
   `rank.rank(..., limit=40)`, whose cut lands at `rank.py:172` (`order[:limit]`), and
   only then does `app.py:108` hand the survivors to `rerank()`, whose own
   `MAX_CANDIDATES = 80` (`rank_llm.py:75`) can therefore never bind. A buried relevant
   course never reaches stage 2.
3. **The stage-2 prompt repeats the bias.** `rank_llm.py:90` reads "A section that does
   BOTH must rank above one that does only one of them", so the model reproduces the
   distortion on the candidates it does see.

A fourth, visible symptom: ties at `score == 1.00` break alphabetically by subject
(`rank.py:157-158`), so for "storytelling" ranks 8-12 are AAST 300, AAST 352, AMS 345,
ANT 411, ANT 412 — alphabetical filler above genuinely relevant JCM courses.

### Measured Result (Task 14)

Measured after Tasks 1-9 and 12-13, `NAVIGATOR_RANKER=tfidf`, rebuilt database, same
term 202710. Group 1's top five is **identical across all three students**, which is the
point: it is the honest answer to "what fits my interest", and the student's outstanding
set no longer perturbs it.

**"climate policy"** — group 1's top five, all three students:

| # | Course | Relevance | Closes |
| --- | --- | --- | --- |
| 1 | PSC 664 Public Policy Analysis | 1.0000 | — |
| 2 | PSC 370 American Public Policy | 0.9447 | — |
| 3 | EC 496 Policy Evaluation Methods | 0.9135 | — |
| 4 | POPH 521 Health Policy & Planning | 0.7222 | — |
| 5 | CJ 686 Criminal Justice Policy | 0.6441 | — |

Compare the before table: PSC 664 moves from shown-at-4 to 1, and BSC 471 Plant
Physiology (0.2352) and MLC 362 Applied Linguistics (0.1729) are now below the floor and
absent from group 1 entirely. GY 302 Climatology (0.5912) rises from shown-at-12 to
group 1 position 9.

**"storytelling"** — group 1's top five, all three students:

| # | Course | Relevance | Closes |
| --- | --- | --- | --- |
| 1 | JCM 318 Documentary Storytelling | 1.0000 | yes |
| 2 | JCM 102 Media Foundations | 0.9152 | — |
| 3 | EN 408 Capstone Course: Advanced Creative Writing | 0.7319 | — |
| 4 | JCM 426 Advanced Design and Visualization | 0.6705 | — |
| 5 | JCM 466 Screenwriting II | 0.5642 | student 2, 3 |

The alphabetical filler is gone: AAST 300, AAST 352, AMS 345, ANT 411 and ANT 412 all
carry `relevance_score == 0.0000` and appear in no part of group 1. Group 1's lowest
relevance for this phrase is 0.3175.

**All four counts, pre-cap.** Group 2 is shown as the page actually renders it — derived
from the *capped* group 1 (Task 8, TD-3) — alongside the uncapped dual-fit count:

| Phrase | Student | Group 1 | Group 2 (displayed / uncapped) | Group 3 | Group 4 | Total |
| --- | --- | --- | --- | --- | --- | --- |
| climate policy | 1 Jordan Reyes | 55 | **0** / 1 | 64 | 41 | 160 |
| climate policy | 2 Rosa Delgado | 55 | **3** / 8 | 480 | 36 | 571 |
| climate policy | 3 Tobias Lindqvist | 55 | **2** / 5 | 279 | 39 | 373 |
| storytelling | 1 Jordan Reyes | 15 | **1** / 1 | 64 | 0 | 79 |
| storytelling | 2 Rosa Delgado | 15 | **8** / 8 | 480 | 0 | 495 |
| storytelling | 3 Tobias Lindqvist | 15 | **5** / 5 | 279 | 0 | 294 |

Group 1 + group 3 + group 4 = total in every row; the four sets partition the deduped
result set exactly.

**Two things this measurement corrects, both bearing on Q-1 and Q-2:**

1. **Q-1's group 2 column is an uncapped count, and the page cannot show it.** On
   "climate policy" student 1's single dual-fit course is NCLT 370 at group 1 position
   **42** — outside `DISPLAY_LIMIT = 40` — so group 2 renders **empty**, not with one
   row. Students 2 and 3 show 3 of 8 and 2 of 5 (their dual-fit courses sit at positions
   21, 37, 38, 42, 46, 49, 50, 52). This is correct under TD-3, which forbids group 2
   from holding a row group 1 does not show, but it sharpens Q-1: on the headline phrase
   the top-billed section is empty for the seeded student. Q-1's option (b) — badges
   inside group 1 — is the only option unaffected by the display cap.
2. **Group 4 is not "36-41 courses per search".** That range holds for "climate policy"
   only. For "storytelling" group 4 is **0** for all three students, because a
   single-token query gives every non-matching course a similarity of exactly 0 and those
   rows are dropped by `if score <= 0` before grouping. Whatever copy Task 10 writes for
   group 4 has to read correctly at zero.

"rockets and propulsion" is deliberately absent: its raw maximum similarity is 0.0000
across all 9,621 offerings, so group 1 is empty before and after. It is the AC 7 fixture
instead, and it behaves — `counts["relevant"] == 0`, 65 requirement-only rows, and not
one of their reasons mentions the phrase.

### Solution

Stop blending. Produce labelled result sets from one uncapped retrieval pass, and let
**membership** — not a weight — encode requirement closure:

1. **Fits your interest** — every course whose `relevance_score` reaches the floor,
   ordered on relevance alone.
2. **Also closes a requirement** — the subset of the *displayed* group 1 that closes an
   outstanding bucket, in group 1's order, badged.
3. **Closes a requirement, no topical match** — courses closing a bucket but below the
   floor, ordered by closure then by sub-floor relevance, collapsed behind a count.
4. **Weakly matched, closes nothing** — counted and stated, not listed. Named because it
   exists: 36-41 courses per search. Revision 1 called group 3 "the remainder", which
   was false and left the page total reconciling with nothing.

### Scope

**In Scope:**

- `rank.rank()` returns the grouped structure and **takes no `limit`** — grouping is
  uncapped so the reranker pool is drawn before any display cut.
- A relevance floor of 0.25 governs membership of groups 1 and 2, compared against the
  rounded `relevance_score` everywhere.
- `W_BOTH` is gated on the floor rather than on nonzero relevance.
- The display cap moves to the caller, applied after reranking.
- The stage-2 prompt no longer instructs the model to rank dual-fit sections first.
- `templates/results.html` renders the groups; group 3 is collapsed and states both the
  number shown and the true total.
- The FR15 "nothing matched" condition becomes "group 1 is empty", computed in grouping.
- `recommendation` gains `result_group`, and its `UNIQUE` constraint is widened to admit
  the deliberate overlap.
- A new `test_rank.py` covers the floor boundary, membership, ordering and counts.

**Out of Scope:**

- Replacing TF-IDF with embeddings. The module docstring names this as the escalation
  path; this interface does not change if it happens later.
- Retuning `W_MUST` / `W_BUCKET`. Group 3's primary key uses them unchanged.
- The advisor-side and sign-in work, and the chatbot direction — separate sprint items.
- Amending FR11/FR12 in `docs/PRD.md`. This spec *requires* that amendment but must not
  make it; see Open Questions.

## Answered Questions — decided 2026-11-11, Tasks 10–11 unblocked

These were product decisions, not implementation choices, and both were raised by the
adversarial review. **The owner answered both on 2026-11-11.** The original statements are
kept — a decision is only legible beside the alternatives it rejected — and each now carries
its answer and the evidence the answer turned on.

### Q-1 — Does group 2 warrant top billing when it holds 1 to 8 rows?

Revision 1 pinned all its evidence to student 1, who turns out to be the one of three
seeded students for whom every requirement-side mechanism is inert: one open bucket,
not must-unmet, so `bucket_score ∈ {0, 1.0}` and `W_MUST = 1.5` never fires. Measured
across all three students on "climate policy":

| Student | Open buckets | Group 1 | **Group 2** | Group 3 | Group 4 (no group) |
| --- | --- | --- | --- | --- | --- |
| 1 Jordan Reyes | 1 (none must) | 55 | **1** | 64 | 41 |
| 2 Rosa Delgado | 11 (LIT, HIST must) | 55 | **8** | 480 | 36 |
| 3 Tobias Lindqvist | 3 (LIT must) | 55 | **5** | 279 | 39 |

FR11/D-19 — the dual-fit idea the product leans on — surfaces between **1 and 8
courses**. This reframes the problem statement: the old blend was not over-weighting a
large set, it was letting a handful of courses dominate the entire first page. The
separation is still the right fix, but a top-billed section holding one row oversells
it.

**Options:** (a) group 2 stays a section, with its emptiness treated as a real and
useful answer; (b) group 2 becomes badges inside group 1 and no separate list exists;
(c) group 2 renders as a section only above a threshold count, badges below it.

### ✅ Q-1 ANSWERED 2026-11-11 — option (b): badges inside group 1, no section

There is no group-2 section. A dual-fit course is a **group-1 row carrying a badge** naming
what it closes.

**What decided it.** The table above: 1, 8 and 5 rows across the three seeded students. A
top-billed section holding one row oversells FR11 — the measurement reframed the problem, as
the question says, and the answer follows the reframing rather than the original design.

**Three consequences, all of them simplifications.**

1. `design-chat-led-query-construction.md` decision 3 lands in the same place — one ranked
   list, closure as badges — so **deferring D-36 costs no rework on this part** of Tasks
   10–11.
2. The `.results { counter-reset: r }` problem **disappears**. With one `<ol>` there is no
   way for a dual-fit course to print two different rank numbers on one page, so Task 10's
   note about deciding how the card presents that is void.
3. **Group 2's empty state is void too.** There is no group 2 to be empty, so Task 10's list
   of needed empty states drops from three to two: group 1 (the FR15 case) and the uncertain
   block from Q-2.

`groups["both"]` **stays in the data** — `app.py:129` derives it and `db.save_search` persists
`result_group = 'both'`, which is what makes the dual-fit set queryable later. It simply has no
section of its own on the page. AC 2 is rewritten accordingly.

**Blocks:** nothing. Tasks 10 and 11 are unblocked.

### Q-2 — Does collapsing group 3 weaken D-21 past what is acceptable?

Uncertain sections have relevance forced to 0 (`rank.py:137`), so they can **never**
clear the floor and can only ever land in group 3 — which this spec collapses behind a
`<details>`. "Shown, never hidden" (D-21) becomes "shown, if you expand it". The
top-of-page callout at `templates/results.html:135-137` would also read "N of these
rotate their topic" about rows not visible in "these".

Verified: 161 uncertain offerings exist in term 202710, but **zero** carry student 1's
single open bucket — so for the seeded student no uncertain row reaches results at all,
for any phrase. Students 2 and 3 do surface them.

**Options:** (a) group 3 stays collapsed and D-21 is amended to "shown on request";
(b) uncertain-but-requirement-closing sections are surfaced uncollapsed in their own
block; (c) group 3 renders uncollapsed with its own internal cap.

### ✅ Q-2 ANSWERED 2026-11-11 — option (b): the uncertain rows come out of the collapse

The **uncertain-and-closing rows surface uncollapsed in their own block**; the rest of group 3
collapses behind a `<details>` whose summary states both the shown and the true count.
**D-21 is not amended** — it keeps "shown, never hidden" exactly as written.

**What decided it: the set is 8 rows.** Measured 2026-11-11 against the rebuilt database, per
student, over five phrases:

| Student | Group 3 total | **Uncertain and closing** |
| --- | --- | --- |
| 1 Jordan Reyes | 64 | **0** |
| 2 Rosa Delgado | 480 | **8** |
| 3 Tobias Lindqvist | 279 | **8** |

And it is **phrase-independent** — necessarily so, since `rank.py` forces uncertain rows'
relevance to 0, which both keeps them out of group 1 and makes their membership a function of
closure alone. Option (b) was the expensive-looking answer and turned out to cost one small
block, which is why the measurement came before the decision rather than after it.

**This also fixes a defect that is live today.** `results.html:135-137` renders "8 of these
rotate their topic each term. They are shown, never hidden (D-21)" — and for student 2 it
renders that right now, about rows that are nowhere on the page, because `n_uncertain` is
computed from `groups["requirement_only"]` while the list below it is dead. Option (a) would
have left the callout's "these" pointing into a collapsed block; option (b) makes the sentence
true.

**Still required of Task 11:** the callout must be absent at zero (student 1, every phrase)
rather than rendering "0 of these".

### A finding from the measurement: group 3 is near phrase-invariant

Not part of either question, found while answering Q-2, and it changes how group 3 may be
labelled. Group 3's size for student 2, by phrase, against a ceiling of 488 offerings that
close one of her open buckets:

| Phrase | Group 1 | Group 3 |
| --- | --- | --- |
| climate policy | 55 | 480 |
| storytelling | 15 | 480 |
| medieval poetry | 20 | 478 |
| statistics | 31 | 488 |
| rockets and propulsion | 0 | **488** |

Group 3 is not a response to the phrase. It is the complete set of everything that closes an
outstanding bucket, minus the handful promoted into group 1 — which is why it grows as group 1
shrinks and reaches its ceiling exactly when group 1 is empty.

**So it is relabelled as a browse list**: headed "Courses that close your outstanding
requirements", with no reference to the phrase and an explicit statement that it is not ranked
against what was typed. This is consistent with what the code already does — Task 5 aligned
`build_reason()` so that sub-floor rows say nothing about the phrase — the label simply catches
up with the data. Without it, a search for "rockets and propulsion" shows the FR15 "nothing
matched" callout directly above 488 courses presented as part of the same result set.

Moving group 3 off the results page entirely is where D-36 sends it. That waits for D-36.

**Blocks:** nothing. Tasks 10 and 11 are unblocked.

### D-35 — the PRD amendment, for the elicitation log

> Renumbered from D-33 on 2026-11-11: sprint 1 claimed D-33 (sign-in reverses AR16) and
> D-34 (what a degree-percent figure may claim) in `docs/epics.md`. See
> `docs/specs/design-chat-led-query-construction.md`, which is D-36.

The elicitation running log governs over the PRD and lives outside this repository, so
this spec records what needs deciding and changes nothing:

- **FR11 (D-19, F-41)** "Sections that close an outstanding requirement **and** match
  the phrase rank above sections doing either alone." Under this design they are grouped
  separately, not ranked above. D-19's intent survives; its single-list mechanism does
  not.
- **FR12 (D-11, F-14, A-05)** "Sections closing two or more outstanding requirements are
  surfaced above sections closing one." Under TD-4 this now holds **only in group 3**.
  Revision 1 claimed it survived as a tiebreaker in groups 1 and 2; that claim created a
  direct contradiction with the Solution section and has been withdrawn. FR12 is
  narrowed, not preserved. **Revision 3 narrows it further, close to retirement:** group 3
  is relabelled a browse list, so FR12 now survives only inside a list that is not a
  search result. Say that plainly in the log rather than letting the FR stand on a
  technicality.
- **FR15 (D-17)** is strengthened: the callout fires when nothing clears the floor
  rather than when nothing scored above zero.
- **D-21 is preserved, not amended.** Q-2 was answered (b): the uncertain-and-closing rows
  — 8 of them, phrase-independent — surface uncollapsed, so "shown, never hidden" stays
  literally true and needs no amendment. This is the one thing the log does **not** owe an
  edit for.
- `docs/UX Design.md`: **UX-DR12** (`:202`) and **UX-DR16** (`:206`) need amending, and
  **UX-DR18** (`:208`) specifies `EmptyState` with exactly three variants — this design
  takes it to **five**: group 1 empty (the FR15 case) and the uncertain block empty.
  *(Revision 2 said "group 2 empty, group 3 empty". Q-1 (b) removed group 2's section, so
  its empty state is void; Q-2 (b) added the uncertain block's. Still two new variants,
  different two.)* **UX-DR34** (`:239`) requires every list to have one. *(Revision 1 cited
  UX-DR25 (`:221`) here, which is about removing text truncation from requirement-bearing
  fields, not list length. Wrong citation.)*
- **A new UX-DR, or an amendment, for the browse-list framing.** The phrase-invariance
  finding means group 3 must be labelled as not-ranked-against-the-phrase. No existing
  UX-DR covers a list that sits on a search page without answering the search.
- `docs/archive/epics - bmad run (not voted).md` Epic 3 stories 3.2 and 3.3 are
  superseded by this spec and should be reconciled when that backlog is promoted.

## Context for Development

### Codebase Patterns

- **Decision IDs are load-bearing.** Every module docstring cites the `D-nn` / `F-nn`
  decisions it implements. Code comments explain *why*, not *what* — match that
  register.
- **Constants are hand-tuned and say so.** `# weights -- tuned by hand against the test
  phrases, not learned` (`rank.py:84`). New constants carry the same kind of comment.
- **Plain dicts between layers.** `rank()` emits exactly `offering_id`, `offering`,
  `score`, `bucket_score`, `relevance_score`, `flag`, `buckets_closed`, `reason`
  (`rank.py:146-155`) plus `other_sections` (`rank.py:168`). **`must_unmet` is not a
  field on this dict** — it exists only per-bucket inside `buckets_closed`. Any new
  shape stays dict-of-primitives.
- **Uncertainty is shown, never filtered where closure exists** (D-21, D-27).
  `rank.py:137` zeroes relevance for `topic_uncertain` but must never remove a section
  or weaken its stated closure. Note the true current behaviour: a section with
  `bucket_score == 0` and zero relevance is dropped by `if score <= 0: continue`
  (`rank.py:143`) — so "nothing is filtered" has never been literally true, and the new
  docstring must not claim it.
- **Failure degrades, never 500s.** `app.py:109-113` catches every reranker exception and
  serves TF-IDF order, because a graded demo must not depend on a network call.
- **Templates name their components**, e.g. `{# 8. CourseResultCard — UX-DR12 #}`.
- **Dedup is by course, not section** (`rank.py:163-172`). One row per
  `(subject, course_number)`, `other_sections` counting the rest.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `rank.py` | Stage 1. Weights at `:85-88`, `phrase_matched()` at `:91`, `rank()` at `:100`, normalisation at `:123`, scoring at `:139-141`, sort at `:157`, dedup at `:163-172`, `build_reason()` at `:175` with its 0.25 cut at `:189`. The primary change. |
| `rank_llm.py` | Stage 2. `MAX_CANDIDATES` at `:75`, the biased `SYSTEM` sentence at `:90`, `build_prompt()` at `:121`, `_validate()` at `:177` (the F-26 guard — do not weaken), `rerank()` at `:205` with its own cut at `:214`. |
| `app.py` | `RANKER` default `auto` at `:24`. `_results_page()` wires both stages at `:102-113`, saves at `:119`, computes `n_uncertain` at `:132`. |
| `templates/results.html` | `:101` the pre-search copy asserting D-19; `:111` the result count; `:123-127` `RankProvenance`; `:135-137` the uncertainty callout; `:142` the `{% if results %}` guard; `:143` the single `<ol class="results">`; `:151` the visible `.r-score`; `:195` the else-branch empty state. |
| `static/style.css` | `.results` counter at `:271-291`; `.badge`, `.callout`, `.empty`, `.r-*` to extend. |
| `db.py` | `outstanding_buckets()` at `:50` supplies the bucket shape; `save_search()` at `:208`. |
| `schema.sql` | `recommendation` at `:233-245`; `flag`'s `CHECK` at `:241-242`; `UNIQUE (request_id, offering_id)` at `:244`. |
| `test_rank_llm.py` | The test idiom to copy and its `fake()` fixture builder. Note it imports `rank` but never calls `rank()`. |

### Technical Decisions

**TD-1 — Labelled sets, not a re-weighting.** Membership encodes requirement closure, so
no weight has to be balanced against another. Re-weighting was considered and rejected:
any single-list weighting leaves a tunable constant that re-creates the distortion as
soon as the catalog or the student's outstanding set changes.

**TD-2 — Relevance floor 0.25.** Reuses the cut `build_reason()` already treats as
"strong match to your phrase" (`rank.py:189`), so the floor and the prose agree. On
"climate policy" it admits GY 302 Climatology (0.5912) and excludes BSC 471 Plant
Physiology (0.2352) and MLC 362 Applied Linguistics (0.1729). Named `RELEVANCE_FLOOR`,
with a comment saying it is hand-set against the test phrases. **Fragility to state in
that comment:** BSC 471 clears exclusion by only 0.015 of a relative unit.

**TD-3 — Overlap between groups 1 and 2 is intended.** A course does not stop fitting
the phrase because it also closes a requirement. Group 1 is the honest answer to "what
fits my interest"; group 2 is a filtered, badged **view of the displayed group 1** — so
it can never contain a row group 1 does not show.

**TD-4 — Group 1 and group 2 order on relevance alone.** `-relevance_score`, then
`subject`/`course_number` for determinism. **No bucket tiebreaker.** Revision 1 put
`-bucket_score` second, which contradicted its own Solution section and was in any case
near-inert — only 3 of 55 rows tie on relevance for "climate policy", and 0 for
"storytelling". Group 2 preserves group 1's order exactly, because it is a view of it.
The cost is that **FR12 no longer holds in groups 1 and 2**; that is a real narrowing,
recorded in D-35 rather than papered over.

**TD-5 — Group 3 orders by `-bucket_score`, then `-relevance_score`, then
subject/number.** `must_unmet` is *not* a sort key: it is already encoded in
`bucket_score` via `W_MUST = 1.5` vs `W_BUCKET = 1.0`, and it is not a field on the
result dict. Sub-floor relevance is the second key because `bucket_score` alone is
frequently constant across the whole group — verified: student 1's group 3 is
`{1.0: 64}`, and 373 of student 2's 480 rows tie at 1.0. Revision 1 claimed this
ordering "replaces today's purely alphabetical tiebreak"; with `bucket_score` as the
only real key it would have **relocated** the alphabetical filler to the top of group 3,
reproducing the exact AAST 300 / AAST 352 / AMS 345 sequence the spec holds up as the
symptom. Sub-floor relevance is weak signal, but it is signal, and it is not a claim of
topical fit — group 3's heading and reasons say nothing about the phrase.

**TD-6 — The reranker is not told to prefer dual fit.** Delete `rank_llm.py:90`. What
stays, deliberately: the outstanding bucket names and the per-candidate `closes:` clause
in `build_prompt()` (`:132`, `:146`), and the hard rules at `:94` and `:97`. Closure
data therefore **does not leave the prompt** — it is needed so the generated `reason`
can say what a course closes, which is FR20. Revision 1's Scope claimed "requirement
closure leaves the model", which was false; only the ranking instruction does.
`_validate()` and the privacy boundary are untouched.

**TD-7 — Group uncapped, rerank, then cap for display.** This is the fix for defect 2,
and revision 1 got it wrong. `rank()` takes no `limit` and groups the whole deduped
result set. `rerank_groups()` draws its pool from the **uncapped** group 1, capped at
`MAX_CANDIDATES` (`rank_llm.py:75`), which now actually binds — 55 courses clear the
floor for "climate policy", 15 of which revision 1 would still have cut before stage 2.
The display cap is applied by the caller afterwards. Group 3 is never sent to the model:
it has no topical signal to rank on.

**TD-8 — The blended `score` stops being displayed.** Nothing sorts on it, so showing it
as the card's headline number would re-present the ranking being rejected. Verified
under the new ordering for "climate policy": PSC 664 at position 1 displays 2.00, while
NCLT 370 at position 42 displays **2.38 — the largest number on the page**. Groups 1 and
2 show `relevance_score`; group 3 shows its badges and no number. `score` stays computed
for the `recommendation` column, with `W_BOTH` gated on the floor. *(Revision 1 claimed
`score` was the card's tooltip. It is the reverse: `score` is the visible `.r-score`
text at `templates/results.html:151` and `bucket_score`/`relevance_score` are the
`title=` attribute.)*

**TD-9 — FR15 is decided by group 1 being empty, not by `phrase_matched()`.**
`phrase_matched()` cannot answer this question. Normalisation divides every similarity
by the term's maximum, so the normalised maximum is always exactly 1.0 whenever any raw
cosine exceeds 0 — a floor-aware version of it is a no-op. Verified: "climate policy"
raw max 0.4288 → normalised 1.0; "storytelling" 0.3172 → 1.0; "rockets and propulsion"
0.0 → 0.0, which is identical to today's answers. Worse, it normalises over *all*
offerings including `open_section == 0` sections and `topic_uncertain` courses whose
relevance is later forced to zero, so the term's argmax may never enter the result set.
`phrase_matched()` is therefore **deleted**, and the caller tests
`counts["relevant"] == 0`.

**TD-10 — The dedup representative is chosen by relevance explicitly.** Today the dedup
at `rank.py:163-172` consumes a list already sorted by `-score` (`:157`), so the blended
score silently decides which section represents a course and therefore which
`relevance_score` that course carries into grouping — the problem one step removed.
Verified as currently small but real: 11 of 3,324 courses show per-section relevance
variation under "climate policy", and the schema does not guarantee the max-relevance
section wins, since `offering_attribute` is per-offering. Sort by `-relevance_score`
before dedup and state the invariant.

**TD-11 — `rerank_groups()` must not mutate its argument.** It returns a new dict. The
fallback guarantee in AC 10 depends on the deterministic grouping surviving a stage-2
exception, and today that holds only accidentally, because `rerank()` builds a new list
and `app.py:108` rebinds on success.

**TD-12 — Reason provenance is mixed and must be stated.** Groups 1 and 2 get
LLM-authored reasons (`reason_source = "llm"`, set in `_validate()`); group 3 keeps its
TF-IDF reason because it is never sent. One `RankProvenance` line covering all groups
would attribute uniformly what is mixed.

## Implementation Plan

**Status, 2026-11-11.** Tasks 1–9, 12, 13 and 14 **landed** at commits `065d496` and `434c9cd`
and are ticked below. Tasks 10–11 did **not** land; Q-1 and Q-2 are now answered, so they are
**unblocked and ready for dev**, tracked as **Story 3.6** in `docs/epics.md`.

> **The result page is wrong until Tasks 10–11 land.** `app.py:153` passes `groups`;
> `templates/results.html` still reads `results` at `:111`, `:142`, `:143`, `:144` and `:195`.
> Jinja2's default `Undefined` renders `{{ results|length }}` as `0` and sends
> `{% if results %}` down the else branch, so nothing raises — the page renders "0 ranked
> courses for ‘climate policy’" and "Nothing matched" above 55 relevant and 480
> requirement-only rows. Task 10's own note predicted exactly this; it is now live.

### Tasks

- [x] Task 1: Add the relevance floor and gate `W_BOTH` on it · **LANDED**
  - File: `rank.py`
  - Action: Add `RELEVANCE_FLOOR = 0.25` beside the weights at `:85-88`, commented as
    hand-set, matching `build_reason()`'s cut, and noting BSC 471 clears exclusion by
    0.015. At `:140` change `relevance > 0` to compare the **rounded** `relevance_score`
    against the floor.
  - Notes: One canonical quantity — `round(relevance, 4)` — gates `W_BOTH`, decides
    membership, and feeds `build_reason()`. Revision 1 gated on the unrounded local and
    grouped on the rounded value, so a course at 0.249963 would have joined group 1 while
    being denied `W_BOTH`. Leave `W_BUCKET`, `W_MUST`, `W_RELEVANCE` unchanged.

- [x] Task 2: Sort by relevance before the course-level dedup · **LANDED**
  - File: `rank.py`
  - Action: Change the sort at `:157-158` to key on `-relevance_score`, then
    `subject`/`course_number`. Comment that the dedup below picks the representative
    section, so this sort decides which section's relevance the course carries.
  - Notes: TD-10. `-score` must stop being the dedup's ordering input.

- [x] Task 3: Remove `limit` from `rank()` and extract grouping · **LANDED**
  - File: `rank.py`
  - Action: Drop `limit` from the `rank()` signature at `:100` and the `order[:limit]`
    cut at `:172`. Add `group_results(results)` returning
    `{"relevant": [...], "both": [...], "requirement_only": [...], "counts": {...}}`,
    uncapped. `relevant` = `relevance_score >= RELEVANCE_FLOOR`, in the Task 2 order.
    `requirement_only` = `bucket_score > 0 and relevance_score < RELEVANCE_FLOOR`, sorted
    by `-bucket_score`, then `-relevance_score`, then subject/number. `counts` carries
    `relevant`, `requirement_only`, `weak_no_closure`, and `total`.
  - Notes: `both` is **not** built here — it derives from the displayed group 1 after
    reranking (TD-3, Task 7). `weak_no_closure` is the fourth set: `bucket_score == 0`
    and `0 < relevance_score < FLOOR`. Verified sizes on "climate policy": 41 / 36 / 39
    for students 1 / 2 / 3. It is counted and stated, never listed. Keep
    `group_results()` free of Flask and Jinja2 imports.

- [x] Task 4: Delete `phrase_matched()` · **LANDED**
  - File: `rank.py`
  - Action: Remove `phrase_matched()` (`:91-97`) entirely and its caller at `app.py:102`.
  - Notes: TD-9 — it cannot express the floor condition. Its docstring's reasoning
    ("without this the UI silently degrades...") is still correct and should move to the
    `counts["relevant"]` check in `app.py`.

- [x] Task 5: Align `build_reason()` with the floor · **LANDED**
  - File: `rank.py`
  - Action: Replace the literal `0.25` at `:189` with `RELEVANCE_FLOOR`, comparing the
    same rounded quantity. At or above the floor reads as a match; below it the reason
    must not claim topical fit at all, only what the course closes.
  - Notes: Group 3 reasons therefore say nothing about the phrase, which is what lets
    TD-5 use sub-floor relevance as a sort key without asserting fit.

- [x] Task 6: Remove the dual-fit instruction from the stage-2 prompt · **LANDED**
  - File: `rank_llm.py`
  - Action: Delete line `:90`. Change the ranking framing to fit against the interest
    phrase. Keep every hard rule at `:92-101` and all of `build_prompt()`.
  - Notes: TD-6. Do not touch `_validate()` (`:177`) — it is the F-26 / D-16 guard and
    the whole safety argument for using a model here.

- [x] Task 7: Add `rerank_groups()` · **LANDED**
  - File: `rank_llm.py`
  - Action: Add `rerank_groups(groups, phrase, outstanding, model=None)`. Pool =
    `groups["relevant"]` uncapped, passed to the existing `rerank()` (which applies
    `MAX_CANDIDATES`). Return a **new** dict: `relevant` in the reranked order,
    `requirement_only` unchanged, `counts` unchanged. Add `pool` to `meta`.
  - Notes: TD-11 — must not mutate `groups`. `both` is still not built here. `rerank()`
    keeps its current signature.

- [x] Task 8: Rewire `_results_page()` and apply the display cap · **LANDED**
  - File: `app.py`
  - Action: Replace `:102-103` with a single `rank.rank(idx, outstanding, phrase)` call.
    Call `rerank_groups()` inside the existing try/except at `:107-113`. Then apply
    `DISPLAY_LIMIT` (new module constant, 40) to `relevant` and `requirement_only`, and
    derive `both` from the **capped** `relevant` by filtering `bucket_score > 0`. Pass
    `groups` and `counts`. Replace `matched` with `counts["relevant"] > 0`. Compute
    `n_uncertain` over the **displayed** group 3 only.
  - Notes: Capping after reranking is the fix for defect 2. `n_uncertain` cannot include
    group 1 — uncertain rows have relevance 0 and can never clear the floor, so revision
    1's "across groups 1 and 3" was half dead code. The except branch must leave the
    deterministic grouping intact (AC 10).

- [x] Task 9: Persist the group, and widen the uniqueness constraint · **LANDED**
  - File: `schema.sql`, `db.py`
  - Action: Add `result_group TEXT NOT NULL CHECK (result_group IN ('relevance', 'both',
    'requirement_only'))` to `recommendation` (`:233-245`), following the `flag` column's
    `CHECK` convention at `:241-242`. **Change `UNIQUE (request_id, offering_id)` at
    `:244` to `UNIQUE (request_id, offering_id, result_group)`.** Change
    `save_search(conn, student_id, actor_user_id, term, phrase, groups)` at `db.py:208`
    to walk the three displayed groups, `rank` numbered from 1 within each.
  - Notes: **This is the Critical finding.** Without the widened constraint, the first
    search containing any dual-fit course raises
    `IntegrityError: UNIQUE constraint failed: recommendation.request_id,
    recommendation.offering_id` — verified by executing the two inserts against the real
    schema. `db.save_search` is unguarded at `app.py:119`, so it is a 500 on the happy
    path. `navigator.db` is derived and gitignored, so no migration is needed:
    `python ingest.py --reset`, `python descriptions.py --from-csv`, `python seed.py`
    (the order in `README.md:15-17`; `app.py:146-150` lists a different one, a
    pre-existing inconsistency this spec does not fix).

- [ ] Task 10: Render the groups · **UNBLOCKED — Q-1 (b), Q-2 (b)** · Story 3.6
  - File: `templates/results.html`, `static/style.css`
  - Action: **One `<ol>`, not three.** Replace the `{% if results %}` guard at `:142` and
    the `<ol class="results">` at `:143` with a single group-1 list, each row carrying a
    closure badge when `bucket_score > 0` (Q-1 (b) — there is **no** group-2 section).
    Below it, the **uncertain-and-closing block, uncollapsed**: the rows of
    `groups["requirement_only"]` whose `flag == "topic_uncertain"`, with closure stated
    and the flag visible (Q-2 (b)). Below that, the rest of `requirement_only` in a
    `<details>`, headed as a **browse list** — "Courses that close your outstanding
    requirements" — with no reference to the phrase and an explicit line saying it is not
    ranked against what was typed. **Update every other `results` reference:** the count
    at `:111` and the else-branch empty state at `:195`. Show `relevance_score`, not
    `score`, at `:151`. Update the pre-search copy at `:101`, which still asserts D-19's
    single-list promise. The `<details>` summary states both the number shown and
    `counts["requirement_only"]`. State `counts["weak_no_closure"]`. Add the Jinja2
    component comments; add heading styles using the existing tokens.
  - Notes: The silent-`Undefined` warning this note used to carry is **no longer
    hypothetical — it is the live behaviour**; see the status block above. Group 3 is
    capped, so the summary must not claim it is complete: for student 2 / "climate policy"
    the true count is 480 against 40 shown. `.results { counter-reset: r }`
    (`style.css:271-291`) restarts per `<ol>` — with Q-1 (b) there is only one `<ol>`, so
    the dual-rank-number problem is **void**. Empty states needed: group 1 (the FR15
    case) and the uncertain block. **Group 2's empty state is void** along with its
    section. `groups["both"]` stays in the data and keeps being persisted; it just has no
    section.

- [ ] Task 11: Update the provenance and uncertainty copy · **UNBLOCKED — Q-1 (b), Q-2 (b)** · Story 3.6
  - File: `templates/results.html`
  - Action: Rewrite `RankProvenance` (`:123-127`) to say that ordering within the relevant
    list is **topical only**, that closure is applied as **grouping and badging** rather
    than as score, and that the requirement-only set was **not reranked** (TD-12). Keep
    the dropped-CRN count (FR18) exactly as it reads. Rewrite the uncertainty callout at
    `:135-137` to point at the uncollapsed block Q-2 (b) creates — "these" is now true —
    and make it **absent at zero** rather than rendering "0 of these".
  - Notes: Under Q-2 (b) the callout's "shown, never hidden (D-21)" becomes literally
    accurate, so D-21 needs no amendment and the sentence can stand as written. This also
    closes a live defect: for student 2 the page renders "8 of these rotate their topic"
    today, about rows that are nowhere on it. `8.6` in `docs/epics.md` is marked Partial
    on exactly this task — the provenance line currently describes an ordering the code
    stopped performing at `065d496`.

- [x] Task 12: Write `test_rank.py` · **LANDED**
  - File: `test_rank.py` (new)
  - Action: Follow `test_rank_llm.py` exactly — module docstring, `fake()`-style fixture
    builders, `check(name, got, want)`, `main()` returning nonzero on failure, runnable
    with no API key and **no database**. Cover: a course at exactly 0.25 is in
    `relevant`; at 0.2499 it is not, and lands in `requirement_only` if it closes
    anything and in neither if it does not; `relevant` order is independent of
    `bucket_score`; `requirement_only` orders by `bucket_score` then sub-floor relevance,
    and is not alphabetical when relevance differs within a tier; `W_BOTH` is not paid
    below the floor; `topic_uncertain` with closure lands in `requirement_only` with
    closure intact; `topic_uncertain` without closure appears nowhere; all four `counts`
    are pre-cap; `group_results` on an empty input returns empty groups and zero counts;
    `rerank_groups` does not mutate its argument.
  - Notes: Build the index from a small hand-written offering list.

- [x] Task 13: Check `test_rank_llm.py` still passes · **LANDED**
  - File: `test_rank_llm.py`
  - Action: Run it. Add one case asserting `rerank_groups` returns a new dict with
    `relevant` reordered and `requirement_only` untouched.
  - Notes: Revision 1 said this file needed fixtures updated "for the grouped return".
    It does not — it imports `rank` but never calls `rank()`, and all 15 of its
    assertions are independent of `rank()`'s return shape. `rank.rank()` has exactly
    **one** caller, `app.py:103`, not the three revision 1 claimed.

- [x] Task 14: Re-measure and record the result · **LANDED**
  - File: this spec
  - Action: Re-run "climate policy" and "storytelling" for all **three** students and
    append group 1's top five and all four counts beside the before table.
  - Notes: Do **not** include "rockets and propulsion" in the after table — verified raw
    max similarity 0.0000 across all 9,621 offerings, because both tokens are outside
    the index vocabulary, so group 1 is empty for that phrase before and after. Use it
    instead as the AC 7 fixture.

### Acceptance Criteria

AC 1-7 and AC 11-13 are evaluated with `NAVIGATOR_RANKER=tfidf`, so they test this code
rather than a model's output. AC 8-10 state their own ranker preconditions.

**Verification status, 2026-11-11.** Ticked below: **AC 5, 6 and 13**, asserted by
`test_rank.py`'s 37 passing cases, and **AC 12**, verified directly against the rebuilt
`navigator.db` by saving a search for student 2 / "climate policy" that contained 3 dual-fit
rows in its displayed set — three `result_group` values persisted (`relevance` 40,
`requirement_only` 40, `both` 3), each ranked from 1 within its group, no `IntegrityError`
(the write was rolled back afterwards). **The spec's Critical finding is closed.**

Not yet verifiable: **AC 1–4, 7 and 11** all assert what the page renders, and the page does
not render the groups until Tasks 10–11 land. They are Story 3.6's acceptance criteria. **AC 8–9**
need a live credential and are still blocked by **AR19**. **AC 10**'s no-mutation half is
asserted by both test files; its provenance-line half is Task 11.

**AC 2, AC 3 and AC 11 were rewritten** against the Q-1 and Q-2 answers; the superseded wording
is noted inline.

- [ ] AC 1: Given student 1 and "climate policy" with `NAVIGATOR_RANKER=tfidf`, when the
  page renders, then group 1 leads with PSC 664 Public Policy Analysis, and neither
  BSC 471 (0.2352) nor MLC 362 (0.1729) appears in it.
- [ ] AC 2: **Rewritten under Q-1 (b).** Given the same search, when a course that both
  clears `RELEVANCE_FLOOR` and closes an outstanding bucket renders, then it appears
  **once**, as a group-1 row carrying a badge naming what it closes — and no separate
  dual-fit section exists on the page. `groups["both"]` is still derived and still
  persisted with `result_group = 'both'`, so the set stays queryable without being a
  section. *(Superseded wording: "when group 2 renders, then every row in it closes at
  least one outstanding bucket and also appears in the displayed group 1.")*
- [ ] AC 3: **Extended under Q-2 (b) and the phrase-invariance finding.** Given the same
  search, when the collapsed group renders, then (a) its summary states both the number
  shown and the true total (64 for student 1, 480 for student 2) and does not present them
  as equal when they differ; (b) it is headed as a **browse list** — courses that close
  outstanding requirements — carrying no reference to the phrase and stating that it is not
  ranked against what was typed; and (c) the uncertain-and-closing rows are **not** inside
  it, having been surfaced uncollapsed above (AC 11).
- [ ] AC 4: Given student 1 and "storytelling" with `NAVIGATOR_RANKER=tfidf`, when group
  1 renders, then its rows are in non-increasing `relevance_score` order and AAST 300,
  AAST 352, AMS 345, ANT 411 and ANT 412 — all `relevance_score == 0.00` — appear in
  none of it.
- [x] AC 5: **PASSING.** Given a fixture course whose `relevance_score` rounds to exactly
  0.25, when results are grouped, then it is in `relevant` and is paid `W_BOTH` if it
  closes a bucket; given 0.2499, it is in neither `relevant` nor paid `W_BOTH`. Asserted by
  `test_rank.py`: "0.2500 is in relevant", "0.2500 is paid W_BOTH", "0.2499 is not in
  relevant", "W_BOTH not paid below the floor".
- [x] AC 6: **PASSING.** Given two fixture courses with equal `relevance_score` where one
  closes two buckets and the other closes none, when group 1 is ordered, then their order
  is decided by subject/course_number and **not** by `bucket_score`, and removing the
  bucket data changes no row's position in group 1. Asserted by `test_rank.py`: "closing
  two buckets does not lift a row in relevant", "removing bucket data changes no position
  in relevant".
- [ ] AC 7: Given "rockets and propulsion", for which no course clears the floor, when
  the page renders, then the FR15 callout is shown, group 1 renders its empty state, and
  no requirement-only row is presented as a result for the phrase.
- [ ] AC 8: Given `NAVIGATOR_RANKER=llm` and student 1 / "climate policy", when a search
  runs, then the pool sent to stage 2 is group 1 drawn before any display cap — 55
  courses, of which 15 fall outside the old `limit=40` — and a course from beyond
  position 40 can appear in the reranked top ten.
- [ ] AC 9: Given the reranker returns a CRN that was not in its input, when results are
  validated, then it is dropped and the dropped count is displayed. Unchanged from today.
- [ ] AC 10: Given the reranker raises any exception, when the page renders, then the
  deterministic grouping is served with every group intact, the `groups` dict passed in
  is unmodified, and the provenance line says the reranker was unavailable.
- [ ] AC 11: **Rewritten under Q-2 (b).** Given student 2 and a section flagged
  `topic_uncertain` that closes an outstanding bucket, when the page renders, then it
  appears **uncollapsed**, in the uncertain block above the browse list, with its closure
  stated and its uncertainty flag shown — not behind a `<details>`. The set is 8 rows for
  students 2 and 3, phrase-independent. And given student 1, for whom the set is empty,
  the uncertain callout and the block are **absent** rather than rendering "0 of these".
  *(The grouping half — that such a row lands in `requirement_only` with closure intact —
  is already asserted by `test_rank.py`: "uncertain with closure lands in
  requirement_only", "uncertain row keeps its closure intact", "uncertain row keeps its
  flag". What remains is the rendering.)*
- [x] AC 12: **PASSING — verified against the rebuilt database, 2026-11-11.** Given a
  completed search containing at least one dual-fit course, when it is saved, then no
  `IntegrityError` is raised and each `recommendation` row carries a `result_group` of
  `relevance`, `both` or `requirement_only` with `rank` numbered from 1 within its group.
  Verified by saving student 2 / "climate policy", whose displayed set held 3 dual-fit
  rows: `relevance` 40 rows ranked 1–40, `requirement_only` 40 ranked 1–40, `both` 3
  ranked 1–3, no exception. The write was rolled back. **This was the spec's Critical
  finding** — on the old `UNIQUE (request_id, offering_id)` this exact search would have
  500'd on the happy path, since `db.save_search` is unguarded at its call site.
- [x] AC 13: **PASSING.** Given `python test_rank.py` and `python test_rank_llm.py` run
  with no `ANTHROPIC_API_KEY` set, then both report all assertions passing and exit 0. Run
  2026-11-11: `test_rank.py` 37 cases, `test_rank_llm.py` all cases, both "ALL PASS",
  both exit 0, neither opens the database.

## Additional Context

### Dependencies

- No new packages. TF-IDF stays pure Python; the dependency list stays Flask alone plus
  the optional `anthropic>=1.0`.
- `navigator.db` must be rebuilt after Task 9. Offline, about a minute, inputs in `data/`.
- Tasks 10-11 are blocked on **Q-1** and **Q-2**. Tasks 1-9 and 12-13 are not.
- Blocks nothing downstream. The sign-in and advisor-side sprint items are independent;
  the chatbot direction consumes this grouping and should be planned after it lands.

### Testing Strategy

**Unit** — `test_rank.py`, new, no database and no API key. The floor boundary at exactly
0.25 and at 0.2499, membership of all four sets, ordering independence from
`bucket_score` in group 1, group 3's two-key ordering, `W_BOTH` gating, uncertain
routing both with and without closure, pre-cap counts, the empty-input case, and
`rerank_groups` non-mutation.

**Integration** — `test_rank_llm.py`, extended with the `rerank_groups` case; every
existing `_validate()` assertion must still hold.

**Persistence** — AC 12 run against a rebuilt database, on a search with a dual-fit
course. This is the one that would have caught the Critical constraint failure.

**Manual** — all three students, not just the seeded one, which is where revision 1's
evidence went wrong. Run "climate policy" and "storytelling" with
`NAVIGATOR_RANKER=tfidf` and confirm AC 1-4; "rockets and propulsion" for AC 7; then
`NAVIGATOR_RANKER=llm` with a deliberately bad key for AC 10.

**Regression guard** — the before table in the Problem Statement, verified reproducible,
is the baseline. Task 14 records the after.

### Notes

**Known limitations.**

- The floor is a hand-set constant against three test phrases, exactly as the existing
  weights are. Honest, not learned. BSC 471 clears exclusion by 0.015 of a relative
  unit, so the boundary is more fragile than a single clean example suggests.
- Normalising relevance against the term's best match makes the floor relative: on a
  phrase the whole catalog matches weakly, 0.25 of a weak maximum is still weak. TD-9's
  empty-group-1 callout is the mitigation, not a fix. Note also that normalisation runs
  over all offerings, including closed sections and uncertain courses whose relevance is
  then zeroed, so the denominator can come from a section that never reaches the page.
- TF-IDF cannot tell that "climate" and "warming" are related — "rockets and propulsion"
  scores 0.0000 across the entire catalog because both tokens are out of vocabulary. That
  is the embeddings escalation path, out of scope here.
- FR12 is narrowed, not preserved (TD-4, D-35).

**Future considerations.** The grouped return is the natural input to the chatbot
direction — "these fit, these also close something, these only close something, these
barely matched" is already the shape a conversational refinement loop needs. Keeping
`group_results()` free of Flask and Jinja2 concerns makes that reuse free.
