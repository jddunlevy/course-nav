---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation', 'revalidated-against-code-2026-11-11', 'sprint-1-stories-added-2026-11-11']
inputDocuments:
  - 'docs/PRD.md'
  - 'docs/Architecture.md'
  - 'docs/UX Design.md'
  - 'sprint/sprint system - run sheet and templates.md (class output format for deliverable #5)'
  - 'elicitation/findings - running log.md (source of truth, D-01 to D-32)'
  - 'app.py, db.py, rank.py, rank_llm.py, ingest.py, schema.sql, reference_data.sql, templates/*.html, static/style.css, test_rank_llm.py (read at commit 5fb1330 for the status revalidation)'
excludedDocuments:
  - "sow/SOW - New College Course Navigator (v2.0).md -- stale; marks interest ranking Won't-have and ranking out of scope, both reversed by D-22"
---

# New College Course Navigator - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for New College Course Navigator, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

**This is the live backlog.** It was produced by a BMAD run that the team did not vote on, and
it was kept as archived evidence until November 11, 2026, when the project owner promoted it.
Two things changed when it was promoted: every story carries an implementation status
revalidated against the code, and the sprint-1 stories for a formal sign-in page and advisor
search-by-student were added. Nothing in the original 32 stories was deleted or reworded — the
statuses and the supersession notes are additions, so the pre-vote text stays auditable.

## Implementation status, revalidated against the code

Read at commit `5fb1330`, against `app.py`, `db.py`, `rank.py`, `rank_llm.py`, `ingest.py`,
`schema.sql`, `reference_data.sql`, all four templates, `static/style.css` and
`test_rank_llm.py`. `navigator.db` was not opened — it was being rebuilt — so every claim below
comes from source, not from data.

| Status | Meaning |
|---|---|
| **Implemented** | Every acceptance criterion in the story is met by code that exists |
| **Partial** | The capability exists but at least one named acceptance criterion is not met |
| **Not started** | No code implements it |

13 implemented, 10 partial, 9 not started.

| Story | Status | Evidence |
|---|---|---|
| 1.1 Enter as a student or an advisor | **Implemented** | `home.html` lists `app_user`; `app.py` `student_view` / `advisor_view`; `base.html` names role and term; `results.html` acting-as banner; `abort(404)` on an unknown student or advisor. No credential, by AR16 — **superseded by 1.5–1.7** |
| 1.2 Outstanding requirements with hours remaining | **Partial** | `db.outstanding_buckets` with the `DISTINCT completed_id` guard (AR12) and `results.html` `.req-list` render it. AC 3 fails: `outstanding_buckets` returns satisfied requirements too and `results.html` renders them under the heading "Outstanding requirements", marked Complete. Still untested (AR17) |
| 1.3 Must-include constraints, not just hour totals | **Implemented** | `requirement_bucket.is_must_include` + `min_hours` in `reference_data.sql`; `must_unmet` in `db.outstanding_buckets`; `satisfied` is `and not any(must_unmet)`, so 9 of 9 Humanities hours with no Literature does not read satisfied; `results.html` renders "Must include:" as its own line naming the bucket |
| 1.4 Which rulebook and catalog year | **Not started** | No `rule_source` table and no provenance columns on `requirement`. `.source-note` exists in `static/style.css` and is used by no template. Matches Architecture §7 |
| 2.1 Which requirements a section would close | **Implemented** | `rank.rank` intersects a section's buckets with the student's open buckets; `results.html` `.r-badges` names each, `.badge.must` for must-include, and a flagged section keeps its badges. Reachable only through a phrase search, because 2.3 does not exist |
| 2.2 Why a section was tagged as it was | **Not started** | `offering_attribute.attribute` holds the Banner text and nothing surfaces it. `schedule_type` is printed as metadata, but no badge cites the attribute or the schedule type that produced it, and the lab rule is displayed only, never applied to closure |
| 2.3 Browse the whole offering list with tags | **Not started** | `app.py` `_results_page` leaves `results` empty when `phrase` is falsy, and `results.html` renders nothing in that case. No pagination over 9,621 sections |
| 3.1 Search by a free-text interest phrase | **Partial** | `rank.Index` is built once in the `_index` global; phrase is in the query string so results are linkable; every candidate comes from `db.offerings_for_term`. AC 4 fails: an empty phrase raises no error but shows no browse list either, which depends on 2.3. The under-2-second budget (NFR1) is unmeasured |
| 3.2 Rank requirement-closing matches above either alone | **Partial** | `rank.W_BOTH = 0.75` is added when both halves are non-zero, which is D-19 as a bonus and not as an ordering guarantee: `score = bucket_score + 2.0 × relevance (+0.75)`, so a section with `bucket_score` 4.0 and no phrase match outranks one at 1.0 + 2×0.5 + 0.75 = 2.75 that does both. AC 1 is therefore not guaranteed. The story's own sizing said this: "the weighting is hand-set and correctness is a judgment call, not a test" |
| 3.3 Surface sections closing two or more requirements | **Partial** | `rank.rank` keys `open_buckets` by `bucket_id` taking the higher weight, so a bucket shared by two requirements (World Language, in `CORE_HUM` and `UNIV_WLANG`) is credited once. But a section carrying two buckets of the **same** requirement — Humanities and Literature, both in `CORE_HUM` — adds both weights, so AC 2 fails and AR12's double count is live on the scoring side. AC 1's "both requirements are named" also fails: badges name buckets, not requirements |
| 3.4 Collapse duplicate sections to one course | **Implemented** | `rank.rank` keeps the best row per `(subject, course_number)` and counts the rest into `other_sections`; `results.html` prints "+N more section(s)" and omits it at zero |
| 3.5 Be told plainly when the phrase matched nothing | **Implemented** | `rank.phrase_matched`; `results.html` `.callout.gap` states that what follows is ranked on requirements only, not on the phrase, and suggests no replacement vocabulary (D-17) |
| 4.1 Guarantee every recommendation is a real offered section | **Implemented** | `rank_llm._validate` drops any CRN not in the input set, counts the drops, de-duplicates, and appends every candidate the model omitted; `results.html` `.provenance` prints the discarded count. A malformed body raises in `json.loads` and `app.py` falls back. Asserted by `test_rank_llm.py` cases 1–4 |
| 4.2 Reorder candidates by relevance and say why | **Partial** | `rank_llm.rerank` is complete and `reason_source = "llm"` is recorded in `_validate` — and then never read: `results.html` prints `r.reason` with no per-result "model-produced" label, so UX-DR36 and NFR16 are unmet at the result level, only at the page level. AR19 still holds, so the "ancient philosophy above Germanic Mythology" criterion is unverified |
| 4.3 Keep my personal data off the wire | **Implemented** | `rank_llm.build_prompt` sends the phrase, the open bucket names and public catalog text. `test_rank_llm.py` case 6 asserts no name, email, classification or depth-study label appears, and that no identifier field is labelled into the prompt — so a later addition fails the test, which is what the story asked for |
| 4.4 Degrade to deterministic ranking rather than failing | **Implemented** | `app.py` catches every exception from `rerank`, logs at warning with `type(e).__name__`, and sets `fallback_from`; `results.html` states which ordering was served. `rank_llm.available()` returns False with no import or credential, so the call is never attempted |
| 5.1 Show rotating-topic sections with the topic flagged | **Partial** | `ingest.mark_topic_uncertain` requires both a special-topics section and a generic or missing description, so Legends is correctly not flagged, and `results.html` renders "Cannot determine the topic — ask your advisor". AC 4 fails: `GENERIC_DESC_PATTERNS` expands to "varie"/"varies" and never matches "vary", and no pattern matches "subject matter varies" — AR18, 14 of 259 courses |
| 5.2 Keep requirement closure trustworthy when the topic is not | **Implemented** | `rank.rank` sets `relevance = 0.0` when `topic_uncertain` and leaves `bucket_score` untouched; the badges render with no hedging and the flag sits below them. The only residual risk is the 40-row display cut, not a blend |
| 6.1 Load the term's seminar themes from the course booklet | **Not started** | No loader, no `nc_seminar_theme` table. `reference/nc-seminar-themes-202710.csv` exists; `reference_data.sql` still carries the D-23 comment saying themes are deliberately absent |
| 6.2 See which theme each seminar closes | **Not started** | No `NC_SEMINAR` requirement; `requirement.rule_kind` is still `CHECK (rule_kind IN ('bucket', 'numeric'))`, so the theme-coverage kind cannot be represented (AR6) |
| 6.3 Flag seminars with no published theme | **Not started** | `recommendation.flag` allows only `ranked` and `topic_uncertain`; there is no unknown-theme variant of `UncertaintyFlag` |
| 7.1 See my advisees and how much each has outstanding | **Implemented** | `app.py` `advisor_view` computes `open_count` and `open_names` per advisee; `advisor.html` renders name, classification, count and the open requirement names, with an empty state. **Modified by 7.6–7.7** |
| 7.2 Search on a student's behalf and see what they see | **Implemented** | `advisor_student_view` and `student_view` both call `_results_page`, one template, one code path (UX-DR21); the acting-as banner names the student. Note the view is reachable by anyone who can type the URL — see 1.6 |
| 7.3 Check a proposed term against every outstanding requirement at once | **Not started** | No route, no proposed-term table (AR8). Architecture §7 agrees |
| 7.4 Confirm or reject proposed depth-study candidates | **Not started** | No proposal record, no advisor decision column (AR9) |
| 7.5 Warn when nothing offered can close a requirement | **Not started** | Nothing computes outstanding buckets against the term's offerings. `.callout.gap` exists in CSS and is used only for the no-phrase-match message; `RequirementCard` has no fourth state (UX-DR8) |
| 8.1 Put colour, type and spacing behind tokens | **Partial** | `static/style.css` defines the full colour palette, the spacing scale and the font stacks on `:root`, with a dark re-derivation. AC 1 fails: `#fff`, `#4A1620` and `#F7E9EB` remain as literals in `.masthead`, `.search button` and `.brand`. The type scale is not tokenised at all — 10/11/12/13/14/16/17/20/28px are written literally throughout, against UX-DR2 |
| 8.2 Meet WCAG 2.1 AA | **Partial** | `:focus-visible` is global at 2px; every status carries a glyph and a word; `.visually-hidden` labels the phrase input; `aria-label` on each requirement section and on the day boxes. Two criteria fail: the phrase input is **not** the first tab stop (the masthead link and the "Hours totals" `<summary>` precede it, UX-DR29), and no contrast audit is recorded for the dark palette, whose values are re-derived and unmeasured |
| 8.3 Stop truncating the fields the product exists to surface | **Partial** | No `text-overflow`, no `ellipsis` and no template truncation anywhere; `.r-title` is `flex: 1` with a `min-width`. AC 3 fails: a section with no listed instructor renders nothing — `{%- if o.instructors %}` — rather than an explicit placeholder |
| 8.4 Give every list a designed empty state | **Implemented** | Four `.empty` blocks: no users seeded, no advisees, no outstanding requirements, nothing matched. **Modified by 7.6** — the advisee search adds a fifth case |
| 8.5 Reflow rather than scroll sideways | **Partial** | The 640px query reflows `.req-list` to one column and restacks the result index. Two gaps: there is no 1024px breakpoint (UX-DR32 names both), and `.scroll-x` is defined but applied to nothing, so the five-column `.grid` tables on the home and advisor screens are unwrapped |
| 8.6 Make reranking visible rather than silent | **Implemented** | `.provenance` states the ordering method, the model, and either the discarded count or "0 invented CRNs"; the fallback is stated as a fallback. UX-DR35's "deterministic first, then refine" is not built — search is one blocking page load — but no acceptance criterion on this story asks for it |

### A concurrent change that will move six of these statuses

As of this revalidation the working tree carries uncommitted work against
`docs/specs/tech-spec-relevance-requirement-separation.md`, by another hand, which rewrites
`rank.py`, `app.py`, `db.py`, `rank_llm.py` and `schema.sql`. It replaces the blended score with
four labelled result groups, removes `rank.phrase_matched`, removes the `limit` argument from
`rank.rank`, adds `recommendation.result_group`, and tells the reranker **not** to rank on
closure. The statuses above describe commit `5fb1330`; when that work lands, **3.2, 3.3, 3.5,
4.2, 4.4 and 8.6 must be re-read before they are trusted**, and `templates/results.html` has not
yet been updated to the new `groups` shape. It also touches `app.py` and `results.html`, which
is where sprint 1 lands — see the sequencing note in `sprint-plan.md`.

### Claims in the other planning documents that the code does not support

Found while revalidating. None is a story; each is a line in another document that should be
corrected there, and two of them affect how a story is read.

1. **`Architecture.md` §6: "TF-IDF retrieves the top 80; the model reorders *those*."** At commit
   `5fb1330` `app.py` calls `rank.rank(..., limit=40)` while `rank_llm.MAX_CANDIDATES` is 80, so
   the reranker could never be handed more than 40 and the 80 could not bind. The in-flight spec
   fixes this deliberately and documents it as TD-7.
2. **`Architecture.md` §7 and Story 1.1 disagree about FR33.** §7 lists "Real role-based sign-in"
   under *Not yet built*; Story 1.1 lists FR33 and FR34 as covered and is sized as having "no
   credential handling (AR16)". Both cannot be right. Proposed D-33 is what settles it.
3. **"Approximate" understates `NC_DEPTH`.** The PRD's open items and `Architecture.md` both call
   the depth-study hour rules approximate. `db.numeric_progress` computes `NC_DEPTH` as the sum
   of *all* the student's completed credits against 33, and `NC_DEPTH_UPPER` as all credits at
   300 or above against 15. That is not an approximation of the rule; it is a number that
   saturates past 100% for any senior — measured at 482% for the seeded senior. The feature
   that would have surfaced it was dropped; the defect itself was not fixed and is a cleanup
   item. Full detail under "Dropped — the degree-percent-complete indicator".
4. **`UX Design.md` §5 specifies `SeatCounter` as "17 of 20".** `results.html` renders "17 seats"
   or "FULL", and the specified form is not currently renderable at all:
   `db.offerings_for_term` selects `seats_available` but not `enrollment` or `max_enrollment`,
   though the schema has both.
5. **Two specified components are styled and never rendered.** `static/style.css` defines
   `.chip-status` (`StatusChip`, UX-DR7) and `.source-note` (`SourceNote`, UX-DR10) and no
   template uses either. Reading the stylesheet makes those two look done; they are not on screen.
6. **`data-model.md` says the 14 tables were "verified against the live database".** That
   verification could not be repeated here — `navigator.db` was being rebuilt and was not opened
   — and the in-flight change adds a column to `recommendation`, so the diagram will need
   re-verifying rather than trusting.
7. **The setup pipeline is printed in two different orders.** AR2 in this document says
   `ingest.py --reset`, `seed.py`, `descriptions.py`; `README.md` and `Architecture.md` §4 both
   say ingest, descriptions, seed. Each step is idempotent so nothing breaks, but the documents
   disagree in print.

## What sprint 1 adds, supersedes and modifies

Six stories were added on November 11, 2026 for the two features the project owner asked for.
No original story was deleted or reworded; the effects on them are recorded here and inline.

| New story | Size | Effect on the existing backlog |
|---|---|---|
| 1.5 Sign in with a credential | L | **Supersedes** Story 1.1's first two acceptance criteria ("Given the role picker is open") and voids its sizing note, "no credential handling (AR16)". 1.1's header, acting-as and not-found criteria survive unchanged |
| 1.6 Scope every student view to the signed-in user | M | **Modifies** Story 7.2 — the advisor-for-student view needs an ownership check it does not have — and closes the hole that `/student/<id>` is readable by anyone who can type a number |
| 1.7 Sign out and end the session | S | New. Nothing existing covers ending a session, because nothing existing starts one |
| 7.6 Find an advisee by name | M | **Modifies** Story 7.1: the advisee list becomes the no-query state of a search rather than a screen of its own. **Modifies** Story 8.4 — a fourth empty-state variant, "no advisee matched", against UX-DR18's stated three |
| 7.7 See what each advisee is working on | S | New. Reads `student.depth_study_label` and `search_request.phrase`, both of which exist and neither of which reaches the advisor screen |
| ~~7.8 Show a degree-progress indicator~~ | — | **Dropped November 11 2026**, the day it was added. `db.numeric_progress` reads 482% for the seeded senior, so there was no honest figure to render. Nothing else depended on it |

Also touched, and not re-sized here: Stories 8.1 and 8.2 gain a surface. A sign-in form is new
UI that needs the token set, a visible focus indicator and a labelled input, and it becomes the
first screen every user sees — which makes the 8.2 criteria about tab order and focus visible on
the one page that cannot be skipped.

## Open decisions this sprint depends on

Both sprint-1 features contradict something already decided, and this project's convention is
that an open decision is surfaced and routed to the owner rather than guessed. The elicitation
running log is the source of truth and holds **D-01 → D-32**; it is not in this repository. A
feature that contradicts one of those needs a **new decision ID recorded by Jaxon in the running
log §6**. The IDs below are proposed numbers for that record, not decisions — nothing here is
decided, and neither story ships until the matching entry exists.

### Proposed D-33 — a formal sign-in page, replacing the role picker

**What is being reversed, plainly.** **AR16** states "No auth provider is in scope. The role
picker stands in for authentication; the role split is what matters for the demonstration."
A sign-in page reverses that outright, and with it `Architecture.md` §2 ("Auth: **None** —
deliberate") and §9's first row, whose last line reads "The first row is the one to be honest
about in the final presentation: the product models two roles and authenticates neither."

**D-20** is reversed in its *approach*, not in its content. D-20 and F-40 say both roles need a
login and that the role split is what the system models; v1 read that as identity rather than
security, and `schema.sql` records the reading inline on `app_user`: "No auth provider in v1
(D-26 scope) -- this is identity, not security." A sign-in page makes it security. **FR33 is not
reversed** — it already reads "A user signs in as either a student or an advisor, and sees the
view for that role." What changes is what "signs in" means.

**The design questions this raises. They are not answered here.**

1. **Which identity provider?** UA single sign-on is the only one a real deployment could use,
   and **AR15** says there is no deployment — the application runs on localhost:5000, where an
   SSO redirect cannot complete without a client registered with the university. The
   alternatives are a local credential table or one shared demo passphrase. The three are
   different stories: roughly L, M and S.
2. **Where do credentials live?** `app_user` has `username` and no password column. Adding one
   makes `navigator.db` a secret-bearing file, and `Architecture.md` §2 currently sells SQLite
   as "survives being emailed". It also adds a hashing dependency to a stack whose only hard
   dependency is Flask (**AR1**). Choose SSO and the question disappears.
3. **Does the seeded-user picker survive for grading and demo?** `seed.py` creates one advisor
   and three students (**D-24**) and the graded demonstration needs all four reachable. A demo
   bypass left in the shipped code is a second, unauthenticated door, which weakens the thing
   the story exists for. Removing it, keeping it, or gating it on an environment variable are
   three different claims to make in the final presentation.
4. **What happens to `/student/<id>`?** Today anyone can read any student's completed coursework
   by typing a number, and **NFR11** says that is education-record data to which FERPA applies.
   Either the pattern stays and gains an ownership check (Story 1.6), or it is replaced by a
   `/me` route plus `/advisor/student/<id>`, which rewrites every link and changes **UX-DR22**:
   a shareable result URL only works if the recipient is permitted to open it — an advisor is,
   a classmate is not, and a signed-out link becomes a redirect to sign-in.
5. **Session mechanism and secret.** A Flask session needs a `SECRET_KEY`, which is a new `.env`
   key under **AR14**, and `app.py` currently runs `app.run(debug=True)` — the debugger would be
   served alongside a login form.
6. **The PRD's own evidence rule.** No FR covers a credential; FR33 covers the role split. By
   the PRD's rule — "a requirement with no ID is an opinion and does not belong here" — this
   feature owes a new FR carrying the new decision ID once it is recorded.

**If it is not decided:** Stories 1.5, 1.6 and 1.7 cannot be sized or started, and Story 7.6's
"my advisees" has no definition to be scoped against.

### Dropped — the degree-percent-complete indicator

**Dropped by the project owner on November 11, 2026, before any decision was recorded.** This
was proposed D-34. It is kept here rather than deleted, because the measurement behind it is the
only record of a live defect, and because a later sprint should not resurrect the feature as
though it were a UI question.

**Why it was dropped: the computation underneath it is wrong, not approximate.**
`db.numeric_progress()` computes `NC_DEPTH` (33 hours) as `SUM(credits)` over *all* of the
student's completed coursework, and `NC_DEPTH_UPPER` (15 hours at 300/400) as the sum of all
credits at 300 or above. Every course a student has ever taken counts toward their depth study.
Measured against the rebuilt database on November 11, 2026 — student 1 Jordan Reyes, a senior
with 159 credits:

| Requirement | Computed | `approximate` |
|---|---|---|
| `NC_DEPTH` | 159/33 = **482%** | True |
| `NC_DEPTH_UPPER` | 55/15 = **367%** | True |
| `UNIV_TOTAL` | 159/120 = **132%** | **False** |
| `UNIV_UPPER` | 55/36 = **153%** | **False** |

`approximate: True` understates it. 482% is not an approximation of a rule, and two of the four
over-100% figures are not flagged approximate at all. This is the same shape of defect as
**AR12** and **NFR8**: a sum over the wrong set, overstating progress in the direction that
flatters. Student 2 reads plausibly only because she has 12 credits recorded; the defect is
invisible on a freshman and unmissable on a senior.

**Two further structural facts about the denominator**, both still true and both unaddressed.
Three of the nine bucket requirements — `CORE_MATH`, `CORE_COMPASS`, `UNIV_WLANG` — have
`hours_needed` NULL and are satisfied by `min_courses`, so they have no hours denominator at
all; `outstanding_buckets` substitutes `(min_courses or 1) * 3` for display, which is a 3-hour
guess and not a rule from the checklist. And `approximate` is keyed on the string prefix `NC_`,
so the `NC_SEMINAR` requirement Epic 6 adds (**AR6**) would be marked approximate by a string
match with nobody deciding it.

**What the drop does and does not close.** It removes the new surface: Story 7.8 is dropped and
no percentage ships. It does **not** fix the defect, which is already on screen — the "Hours
totals" panel in `templates/results.html` renders these same rows, so Jordan Reyes displays
`159/33` today. The defect is routed to the cleanup pass, not to this sprint.

**If the feature is ever revived**, it needs the per-course depth-study flag the PRD carries as a
Growth Feature: a schema change plus a per-student data-entry pass, larger than both sprint-1
features together. Reviving it without that flag means choosing which compromise to print, which
is what **D-17**, **D-27** and **D-31** exist to refuse.

## Requirements Inventory

### Functional Requirements

- FR1: A student can see, for every section offered in the term, which of their outstanding requirements it would close. (**F-15**, **F-21**, **D-02**)
- FR2: A student can see why a section was tagged as it was — which Banner attribute or schedule type produced which requirement bucket. (SOW §6 row 8, **F-21**)
- FR3: The system displays the source document and revision date for the requirement rules in force. (**D-29**; `nc-website-audit.md`)
- FR4: A student can see which requirements a section closes even when the section's topic cannot be determined. (**D-27**)
- FR5: A student can see each outstanding requirement with hours remaining and hours completed. (**F-19**, **F-16**)
- FR6: The system shows must-include constraints distinctly from hour totals — "9 hours, including at least one Literature". (**D-28**, Pre-Advising Checklist)
- FR7: The system computes a requirement as a union of gen-ed buckets, not a hierarchy, and never counts one completed course twice against the same requirement. (**D-28**)
- FR8: A student's completed coursework is loaded into the system and drives what counts as outstanding. (**D-24**, **F-19**)
- FR9: A student or advisor can enter a free-text interest phrase; no fixed taxonomy of topics or careers exists. (**D-22**, resolves **Q-24**)
- FR10: The system ranks only sections actually offered in the modelled term. (**D-16**, **F-26**)
- FR11: Sections that close an outstanding requirement **and** match the phrase rank above sections doing either alone. (**D-19**, **F-41**)
- FR12: Sections closing two or more outstanding requirements are surfaced above sections closing one. (**D-11**, **F-14**, **A-05**)
- FR13: Results are deduplicated by course, with the number of additional sections stated. (prototype measurement: up to 30 rows per course)
- FR14: A student can browse the full offering list with requirement tags shown and no phrase entered. (**D-04**, **F-01**, **F-02**)
- FR15: A student is told when their phrase matched nothing, rather than being shown an arbitrary ranking. (**D-17**)
- FR16: A second-stage reranker reorders the retrieved candidate set by relevance to the phrase. (**D-22**, **A-04**)
- FR17: The reranker may only reorder sections it was given. It cannot introduce a section. (**D-16**, **F-26**)
- FR18: Every section identifier the reranker returns is validated against the input set; anything not in it is discarded and the discarded count is reported. (**D-16**)
- FR19: A candidate the reranker omits from its ordering is appended rather than dropped. (**D-16**)
- FR20: The reranker produces a one-line reason for each result, derived from the course text it was given. (SOW §6 row 8)
- FR21: Any reranker failure falls back to the deterministic ranking and serves results rather than erroring. (NFR5)
- FR22: Only the interest phrase, the names of outstanding requirement buckets, and public catalog text are sent off the machine. No name, student ID, completed coursework, or grades. (NFR12)
- FR23: A section whose topic cannot be determined from catalog text is shown, never hidden, and labelled "cannot determine the topic — ask your advisor". (**D-21** as refined by **D-27**)
- FR24: Topical uncertainty never attaches to requirement closure. A section's gen-ed buckets remain stated plainly even when its topic is unknown. (**D-27**)
- FR25: A section is flagged uncertain only when it has a special-topics section **and** its description carries no topical signal — not on the special-topics attribute alone. (**D-27**; 136 Legends sections carry the attribute and are a known requirement)
- FR26: A NEW course is shown with its seminar theme — CC, ESC or SPSC — for the modelled term. (**D-31**, partly reversing **D-23**)
- FR27: A course listed as a seminar for which no theme is published is shown as a seminar with the theme marked unknown, under the FR23 flag. (**D-31**, **D-27**; 3 of 15 this term)
- FR28: An advisor can see their advisees with a count of each one's outstanding requirements. (**D-01**, **D-25**)
- FR29: An advisor can run the same search on a student's behalf and see what the student sees. (**D-01**, **F-04**)
- FR30: An advisor can check a student's proposed term against every outstanding requirement in one pass. (SOW §6 row 5, **F-04**)
- FR31: Depth-study candidates are proposed to an advisor for confirmation and are never asserted as fact. (**F-04**, **D-17**, SOW §6 row 6)
- FR32: The system warns when no offered section closes an outstanding requirement. (SOW §6 row 7, **F-12**, **F-13**)
- FR33: A user signs in as either a student or an advisor, and sees the view for that role. (**D-20**, **F-40**)
- FR34: A student has exactly one advisor. The student records person has no role in the system. (**D-25**, **F-39**)

### NonFunctional Requirements

- NFR1: A phrase search returns ranked results in under 2 seconds without the reranker, over ~9,600 sections.
- NFR2: With reranking enabled, results return in under 10 seconds, or the fallback in NFR5 fires.
- NFR3: The retrieval index is built once per process, not per request.
- NFR4: The product functions with no network access and no API credential. Ranking degrades, it does not fail.
- NFR5: Any reranker failure — credential, network, malformed response, schema change — is logged and serves deterministic results. A graded demonstration must not depend on a round trip.
- NFR6: Concurrent reads during a long-running description fetch must not fail. (WAL plus busy timeout; measured defect, now fixed.)
- NFR7: Requirement tagging is rule-based and reproducible. The same inputs produce the same tags, and the rule that produced a tag can be shown.
- NFR8: No requirement may be marked satisfied by double-counting one completed course against the same requirement twice. (Measured defect: SPA 101 is both World Language and Humanities, producing 19 hours against a 9-hour pool.)
- NFR9: The rule set states which catalog year and which source document it encodes. (**D-29**)
- NFR10: Model-produced text is labelled as such and is never the sole basis for a requirement claim.
- NFR11: Completed coursework is student education-record data. FERPA applies, and the DegreeWorks import path must be resolved against it before it ships. (Open — see §9.)
- NFR12: No personally identifying data leaves the machine. The off-machine payload is limited to the phrase, outstanding bucket names, and public catalog text. Asserted by test, not by comment.
- NFR13: The system stores no grades.
- NFR14: The product informs the manual search rather than replacing it. Browsing the full list with tags remains available. (**D-04**, **F-02**)
- NFR15: Output is never pitched on user frustration, and the interface does not assume the user believes they have the problem. (**D-14**, **A-10**)
- NFR16: Every AI-produced suggestion is visibly labelled as proposed, with the text it was derived from. (**R1**, **F-04**)
- NFR17: Course and section data come from Banner, via a scraper requiring no login. HTML-escaped text must be unescaped before attribute splitting. (Measured defect: `&amp;` ends in a semicolon and the attribute column joins on `"; "`, splitting one attribute into two; affected 220 attribute rows and 581 titles.)
- NFR18: Course descriptions are course-level, not section-level, and are cached once per subject and number. About 5% of courses have no description record in Banner.
- NFR19: Seminar theme data has no Banner source and is loaded from the term course booklet. The refresh is manual and must be documented per term. (**D-31**)

### Additional Requirements

**STARTER TEMPLATE: NONE.** `Architecture.md` section 2 states explicitly that this is not a
greenfield scaffold -- it is an existing, running Python application with dependencies declared
and a working database. **Epic 1 Story 1 must NOT be a project-initialisation story.** A
scaffolding story here would be invented work in a graded backlog.

- AR1: Stack is fixed -- Python 3, Flask, SQLite, server-rendered Jinja. No build step, no npm, no client framework. Flask is the only hard dependency; `anthropic` is optional and imported defensively.
- AR2: Setup is a four-step idempotent pipeline (`ingest.py --reset`, `seed.py`, `descriptions.py`, `app.py`). Any new data source must fit it and be re-runnable.
- AR3: Banner 9 section data is integrated via the `ua-classes` JSON scraper, which needs no login. 9,621 sections / 3,324 courses for term 202710.
- AR4: Course descriptions come from Banner's `getCourseDescription` endpoint, are **course-level not section-level**, are cached once per subject and number, and are absent for about 5% of courses (HTTP 500).
- AR5: Seminar theme data has **no Banner source**. It loads from `reference/nc-seminar-themes-202710.csv`, extracted from the term course booklet. The refresh is manual and per-term, and must be documented as such.
- AR6: A new `nc_seminar_theme` table plus an `NC_SEMINAR` requirement are required for FR26 and FR27. This adds a requirement *kind* the schema does not have -- theme coverage across three themes plus a level distribution, rather than hours against a bucket pool. It is the largest unbuilt item.
- AR7: A rule-provenance store is required for FR3, NFR9, D-29 and D-32 -- source document, revision date, catalog year, URL -- either as a `rule_source` table or as columns on `requirement`.
- AR8: A proposed-term representation and route are required for FR30; neither exists.
- AR9: A depth-study proposal record carrying an advisor decision is required for FR31. It must never assert, only propose (F-04).
- AR10: WAL and `busy_timeout` must be set at database creation. Journal mode cannot be switched from an ordinary connection; getting this wrong reintroduces `database is locked` during description fetches.
- AR11: HTML entities must be unescaped **before** attribute splitting. The escape for an ampersand ends in a semicolon and the attribute column joins on `"; "`. Regression here silently corrupts 220 attribute rows and 581 titles.
- AR12: Hour sums must be taken over `DISTINCT completed_id`. A course carrying two buckets of the same requirement (SPA 101 is World Language and Humanities) otherwise double-counts and marks a requirement satisfied that is not.
- AR13: Logging is the standard Flask logger. Index construction and **every** reranker fallback log at warning with the exception type.
- AR14: Configuration is environment variables with a `.env` loader read as `utf-8-sig`, because PowerShell writes a BOM that corrupts the first key.
- AR15: No deployment, hosting, or CI is in scope. The application runs on localhost port 5000.
- AR16: No auth provider is in scope. The role picker stands in for authentication; the role split is what matters for the demonstration.
- AR17: `db.outstanding_buckets` has no test coverage and is the highest-risk untested code given AR12. Tests for it belong in the backlog.
- AR18: An open defect exists in `ingest.GENERIC_DESC_PATTERNS`: it cannot match "vary" or "subject matter varies", leaving 14 of 259 special-topics courses unflagged. The fix must be title-aware and is a pending team decision, not a patch.
- AR19: The live LLM path has never run against a real credential. The response schema is unvalidated; the first real call may surface a schema error, which the fallback will catch.

> **AR16 is under reversal.** Sprint 1 replaces the role picker with a credentialed sign-in
> page, which contradicts AR16 directly and reads on the architecture's "Auth: None —
> deliberate". It does not ship until the owner records the reversal — see "Open decisions this
> sprint depends on", proposed D-33. AR15 (no deployment, localhost only) is **not** reversed,
> and that constrains which identity providers are even reachable.

### UX Design Requirements

- UX-DR1: Implement the colour token set in §4 as CSS custom properties on `:root`, replacing hard-coded colours in `static/style.css`.
- UX-DR2: Implement the type scale (12/14/16/20/28px, 16px body) and the 4px spacing grid as tokens.
- UX-DR3: Define card styling once — 8px radius, 1px `--rule` border, no shadow — and apply it to `RequirementCard` and `CourseResultCard` rather than styling each.
- UX-DR4: Replace Banner's `#638D4F` with the `--ok` token at 5.14:1 wherever a success or completion colour is used; no inherited colour may ship below 4.5:1.
- UX-DR5: Build `AppHeader` with three states — student, advisor, and advisor-acting-for-student — the third carrying a visible acting-as banner naming the student.
- UX-DR6: Build `StatusCircle` with three states (complete, in-progress, not-started), each carrying a distinct shape or glyph in addition to colour.
- UX-DR7: Build `StatusChip` with COMPLETE / IN-PROGRESS / INCOMPLETE variants, styled after DegreeWorks' outlined chip.
- UX-DR8: Build `RequirementCard` showing requirement name, hours applied against hours required, must-include constraints, and a `StatusCircle`; with a distinct fourth state for "no offered section closes this".
- UX-DR9: Build `RequirementBadge` with an emphasised variant for must-include buckets, naming the specific bucket (Literature, History) rather than the parent pool.
- UX-DR10: Build `SourceNote` rendering the source document, its revision date, and the catalog year; attach it to every surface that states a requirement rule.
- UX-DR11: Build `PhraseInput` with recent phrases and a no-match state; no autocomplete or suggested vocabulary.
- UX-DR12: Build `CourseResultCard` showing subject, number, untruncated title, credits, all requirement badges, the match reason, meeting pattern, seats, and a "+N more sections" affordance.
- UX-DR13: Build `MeetingPattern` as SMTWTFS day boxes plus time, with TBA and online variants, following Banner's widget.
- UX-DR14: Build `SeatCounter` with open and full variants, the full variant distinguished by text as well as colour.
- UX-DR15: Build `UncertaintyFlag` with two variants — unknown topic, and unknown seminar theme — each stating what is unknown and directing the user to their advisor.
- UX-DR16: Build `RankProvenance` stating whether the order is deterministic or reranked and how many candidates validation discarded.
- UX-DR17: Build `GapWarning` for a requirement no offered section can close.
- UX-DR18: Build `EmptyState` with three variants: no phrase match, no advisees, no outstanding requirements.
- UX-DR19: Build `AdviseeRow` showing the student, their classification, and a count of open requirements.
- UX-DR20: Build the advisor term-review screen at `/advisor/<id>/student/<id>/review`, checking a proposed term against every outstanding requirement in one pass.
- UX-DR21: Render the student and advisor-for-student result views from a single template and code path so they cannot diverge.
- UX-DR22: Make search results linkable — the phrase lives in the query string and a result URL can be shared with an advisor.
- UX-DR23: Audit `static/style.css` and replace every literal colour with a token from UX-DR1.
- UX-DR24: Introduce semantic classes for the states named in §5 rather than styling by element or position.
- UX-DR25: Remove all text truncation from requirement-bearing fields — title, attribute, instructor. These are the fields the product exists to surface.
- UX-DR26: Meet WCAG 2.1 AA — body text ≥ 4.5:1, large text ≥ 3:1, non-text indicators ≥ 3:1. Run a contrast audit over the finished palette and record the result.
- UX-DR27: Ensure no state is conveyed by colour alone; every status carries a glyph, shape, or word.
- UX-DR28: Provide a visible keyboard focus indicator on every interactive element, at ≥ 3:1 against its background.
- UX-DR29: Make the result list keyboard-navigable in DOM order, with the phrase input as the first tab stop on the student view.
- UX-DR30: Give `StatusCircle` and `SeatCounter` accessible text so a screen reader announces state, not just a styled element.
- UX-DR31: Mark each requirement group as a landmark region with a heading, so a screen reader user can move between requirements without traversing every result.
- UX-DR32: Support breakpoints at 640px and 1024px; `RequirementCard` and `CourseResultCard` reflow from two columns to one below 640px.
- UX-DR33: Ensure no element causes horizontal scrolling of the page body at any supported width; wide content scrolls within its own container.
- UX-DR34: Give every list a designed empty state; no list may render as a blank region.
- UX-DR35: Make reranking visible — show the deterministic order first, indicate refinement in progress, and state plainly via `RankProvenance` when it falls back.
- UX-DR36: Label every model-produced line as proposed, alongside the source text it derives from.

### FR Coverage Map

Every FR maps to exactly one epic. 34 of 34 covered; no FR appears in two epics.

| FR | Epic | Capability |
|---|---|---|
| FR1 | 2 | Which outstanding requirements a section would close |
| FR2 | 2 | Why a section was tagged as it was |
| FR3 | 1 | Source document and revision date for the rules in force |
| FR4 | 2 | Closure shown even when topic is undeterminable |
| FR5 | 1 | Outstanding requirements with hours remaining |
| FR6 | 1 | Must-include constraints shown distinctly from hour totals |
| FR7 | 1 | Requirement as a union of buckets; no same-requirement double count |
| FR8 | 1 | Completed coursework drives what is outstanding |
| FR9 | 3 | Free-text interest phrase, no fixed taxonomy |
| FR10 | 3 | Only sections actually offered in the term |
| FR11 | 3 | Closes-a-requirement AND matches-phrase ranks first |
| FR12 | 3 | Sections closing two or more requirements surface |
| FR13 | 3 | Deduplicated by course with section count |
| FR14 | 2 | Browse the full offering list with tags, no phrase |
| FR15 | 3 | No-match stated rather than arbitrary ranking |
| FR16 | 4 | Second-stage rerank of the retrieved set |
| FR17 | 4 | Reorder only; cannot introduce a section |
| FR18 | 4 | Every returned identifier validated; discards counted |
| FR19 | 4 | Omitted candidates appended, not lost |
| FR20 | 4 | One-line reason per result |
| FR21 | 4 | Any failure falls back and still serves results |
| FR22 | 4 | Only phrase, bucket names and public text leave the machine |
| FR23 | 5 | Undeterminable topic shown, flagged, never hidden |
| FR24 | 5 | Uncertainty never attaches to requirement closure |
| FR25 | 5 | Flagged on generic description, not the attribute alone |
| FR26 | 6 | Seminar theme per NEW course for the term |
| FR27 | 6 | Seminars with no published theme flagged unknown |
| FR28 | 7 | Advisee list with open-requirement counts |
| FR29 | 7 | Advisor searches on a student's behalf |
| FR30 | 7 | Proposed term checked against all requirements in one pass |
| FR31 | 7 | Depth-study candidates proposed, never asserted |
| FR32 | 7 | Warn when nothing offered closes a requirement |
| FR33 | 1 | Role-based entry as student or advisor |
| FR34 | 1 | One advisor per student; records person has no role |

**Sprint 1 adds no FRs, and that is the point.** Five new stories cover one capability the PRD
does not state: a credentialed sign-in, since FR33 covers the role split, not a credential. By
the PRD's own evidence rule — "a requirement with no ID is an opinion and does not belong
here" — it owes an FR carrying its new decision ID once proposed D-33 is recorded. Until then
these stories carry the decision gap, not a requirement. A sixth story, 7.8, would have owed a
second FR for a degree-progress indicator; it was dropped.

### Dependency order

Each epic uses earlier ones; none requires a later one to function.

```
Epic 1  (standalone)
  |
  +-- Epic 2  (uses 1's outstanding requirements)
  |     |
  |     +-- Epic 3  (uses 1 + 2)
  |           |
  |           +-- Epic 4  (reranks 3; 3 works without it -- NFR5 fallback)
  |           +-- Epic 5  (flags 3's output; 3 works without it)
  |           +-- Epic 7  (uses 1 + 2 + 3)
  |
  +-- Epic 6  (uses 1's requirement framing; new requirement kind)
```

## Epic List

### Epic 1: Sign in and see where I stand

A student or advisor enters the system as themselves and sees that student's outstanding
requirements -- hours applied against hours required, must-include constraints stated
separately from hour totals, and the source document, revision date and catalog year behind
every rule. Standalone: complete without any search, ranking or AI.
**FRs covered:** FR3, FR5, FR6, FR7, FR8, FR33, FR34

### Epic 2: See what every offered course would close

A student browses the term's offered sections with the requirements each would close shown on
the card, and can see why each tag was applied. Closure is shown even for sections whose topic
is unknown. This is the inverse question no existing system answers (F-15, D-02).
**FRs covered:** FR1, FR2, FR4, FR14

### Epic 3: Find courses that fit my interests

A student or advisor types a free-text interest phrase and gets offered sections ranked so
that closing an outstanding requirement *and* fitting the phrase beats either alone (D-19).
Double-counting sections surface, duplicate sections collapse to one course, and a phrase that
matched nothing is stated rather than silently producing an arbitrary order.
**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR15

### Epic 4: Trust the AI's ordering  *(core AI feature)*

Results are reordered by a second-stage model that writes a reason for each one, and every
recommendation is provably a real section offered this term -- the model may only reorder what
it was handed, every identifier it returns is validated against that set, and anything else is
discarded and counted. Nothing personal leaves the machine. Any failure serves the
deterministic order instead of erroring. Standalone: Epic 3 is fully functional without this.
**FRs covered:** FR16, FR17, FR18, FR19, FR20, FR21, FR22

### Epic 5: See what the system cannot determine

Sections whose topic cannot be read from catalog text appear in results with the unknown part
named and the student directed to their advisor -- never hidden, never guessed. Uncertainty
attaches to topical fit only; what a section counts for stays trustworthy even when its topic
is not. Lives in the deterministic ranker, not the AI path.
**FRs covered:** FR23, FR24, FR25

### Epic 6: Track New College seminar themes

A student sees which of the three themes -- Creativity and Culture, Environment Sustainability
and Conservation, Social Problems and Social Change -- each New College seminar closes, and
which seminars have no published theme. Adds a requirement *kind* the schema does not have:
coverage across three themes plus a level distribution, rather than hours against a bucket
pool.
**FRs covered:** FR26, FR27

### Epic 7: Advise a student in one pass

An advisor sees their advisees with open-requirement counts, searches on a student's behalf and
sees exactly what the student sees, and checks a proposed term against every outstanding
requirement at once instead of course by course. Depth-study candidates are proposed for the
advisor to confirm or reject, never asserted. The system warns when nothing offered can close a
requirement.
**FRs covered:** FR28, FR29, FR30, FR31, FR32

### Epic 8: Design system and accessibility

Cross-cutting interface work: the colour, type and spacing tokens, semantic styling,
WCAG 2.1 AA compliance, responsive reflow and designed empty states. Added during Step 3
rather than Step 2, because Step 3 makes UX-DR coverage a failure condition and 36 UX-DRs do
not fit into seven feature epics without bloating them. The 15 component-level UX-DRs stayed
with the feature epics that use them; this epic carries the rest.
**FRs covered:** none — this epic covers UX-DRs only
**UX-DRs covered:** UX-DR1–UX-DR4, UX-DR7, UX-DR18, UX-DR23–UX-DR35

## Epic 1: Sign in and see where I stand

A student or advisor enters the system as themselves and sees that student's outstanding
requirements, with the source and catalog year of every rule. Standalone: complete without any
search, ranking or AI.

**FRs:** FR3, FR5, FR6, FR7, FR8, FR33, FR34 · **NFRs:** NFR8, NFR9 · **UX-DRs:** UX-DR5, UX-DR6, UX-DR8, UX-DR10, UX-DR19

**Sprint 1 adds Stories 1.5, 1.6 and 1.7** — a credentialed sign-in page in place of the role
picker, an ownership check on the student routes, and sign-out. They reverse AR16 and are
blocked on proposed D-33. The epic's title was already "Sign in and see where I stand"; until
sprint 1 the first half of it was a list of names.

### Story 1.1: Enter as a student or an advisor

As a student or advisor,
I want to enter the system as myself,
So that what I see is my own position rather than a generic catalog.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — two roles and a one-advisor-per-student rule, but no credential handling (AR16).
**Covers:** FR33, FR34 · **UX:** UX-DR5, UX-DR19
**Status:** Implemented — evidence in the status table above. **Superseded in part by Stories 1.5, 1.6 and 1.7:** the role-picker criteria and the "no credential handling (AR16)" sizing no longer hold.

**Acceptance Criteria:**

**Given** the role picker is open
**When** I choose a student
**Then** the student view opens for that student
**And** the header names the student and the term.

**Given** the role picker is open
**When** I choose an advisor
**Then** the advisor view opens listing only that advisor's advisees.

**Given** an advisor is viewing a student
**When** the page renders
**Then** a visible acting-as banner names the student being viewed.

**Given** a student id that does not exist
**When** the view is requested
**Then** the system returns not-found rather than an empty page.

### Story 1.2: See my outstanding requirements with hours remaining

As a student,
I want to see each requirement I have not finished with hours applied against hours required,
So that I know what still needs closing before I look at any course.

**MoSCoW:** Must · **Size:** M · **Why:** Complex — thirteen requirements over a twelve-bucket union, and the hour maths has a known double-count trap.
**Covers:** FR5, FR7, FR8 · **NFRs:** NFR8 · **Architecture:** AR12 · **UX:** UX-DR6, UX-DR8
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** a student with completed coursework
**When** the student view loads
**Then** every unmet requirement is listed with hours applied, hours required, and a status indicator.

**Given** a completed course carrying two buckets of the same requirement, such as SPA 101 in both World Language and Humanities
**When** progress is computed
**Then** its credits count once toward that requirement, not twice.

**Given** a student who has satisfied a requirement
**When** the view loads
**Then** that requirement shows as complete and does not appear as outstanding.

**Given** a student with no completed coursework recorded
**When** the view loads
**Then** every requirement shows zero applied hours rather than an empty or broken panel.

### Story 1.3: See must-include constraints, not just hour totals

As a student,
I want "including at least one Literature" shown separately from "9 hours",
So that I do not close the hours and still fail the requirement.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — the constraint is already modelled as `is_must_include`; this surfaces it.
**Covers:** FR6 · **UX:** UX-DR8, UX-DR9
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** a requirement carrying a must-include bucket
**When** the requirement card renders
**Then** the constraint is stated as its own line, naming the specific bucket.

**Given** a student with 9 of 9 Humanities hours but no Literature course
**When** the card renders
**Then** the requirement is **not** shown as satisfied, and the unmet constraint is named.

**Given** a requirement with no must-include bucket
**When** the card renders
**Then** no constraint line appears.

### Story 1.4: See which rulebook and catalog year I am measured against

As a student,
I want every requirement to name its source document, revision date and catalog year,
So that I can tell whether the rule actually applies to me.

**MoSCoW:** Should · **Size:** M · **Why:** Uncertain — needs a provenance store that does not exist, and the authority order rests on one DegreeWorks audit (Q-27).
**Covers:** FR3 · **NFRs:** NFR9 · **Architecture:** AR7 · **UX:** UX-DR10 · **Decisions:** D-29, D-30, D-32
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** a requirement card
**When** it renders
**Then** it shows the source document, its revision date, and the catalog year the rule belongs to.

**Given** a rule with no recorded catalog year
**When** the page renders
**Then** the rule is not displayed as authoritative, and the gap is stated.

**Given** a student on a catalog year other than the loaded rule set
**When** the view loads
**Then** a notice states which catalog year is being applied and that it may not be theirs.

### Story 1.5: Sign in with a credential

As a student or an advisor,
I want to sign in with a credential instead of picking my name off a public list,
So that my record is reached by proving who I am rather than by knowing a URL.

**MoSCoW:** Must · **Size:** L · **Why:** Uncertain — the provider, the credential store and the fate of the demo picker are one unmade decision, and the size is L, M or S depending on which way it goes.
**Covers:** FR33 (re-covered — the picker satisfied it without a credential) · **NFRs:** NFR11 · **Architecture:** reverses AR16; adds a config key under AR14 · **UX:** UX-DR5, which gains a signed-out state · **Decisions:** needs **proposed D-33**, not yet recorded
**Status:** Not started · **Blocked on proposed D-33.** Supersedes the role-picker criteria of Story 1.1.
**Added:** sprint 1, November 11 2026.

**Acceptance Criteria:**

Only the criteria that hold under *every* option in proposed D-33 are written here. Criteria
naming a provider or a credential store would decide the decision rather than wait for it.

**Given** no session
**When** any route other than the sign-in page is requested
**Then** the sign-in page is served and no student or advisor data appears in the response.

**Given** the sign-in page
**When** a credential matching an `app_user` row is submitted
**Then** a session is established naming that user, and the view for that user's role opens.

**Given** the sign-in page
**When** a credential matching nothing is submitted
**Then** the page states that sign-in failed without saying which half was wrong, and no view opens.

**Given** a signed-in user
**When** the header renders
**Then** it names the signed-in user and their role, as the picker's header did.

**Given** the application is started with no session secret configured
**When** it boots
**Then** it refuses to start rather than running on a default secret.

### Story 1.6: Scope every student view to the signed-in user

As a student,
I want my record reachable only by me and my advisor,
So that my completed coursework is not readable by anyone who can increment a number in a URL.

**MoSCoW:** Must · **Size:** M · **Why:** Complex — `/student/<id>` and `/advisor/<id>` key on raw record ids, and `_results_page` checks only that the student exists. One route pattern has to serve a student, that student's advisor, and nobody else.
**Covers:** FR33, FR34 · **NFRs:** NFR11 — completed coursework is education-record data · **Decisions:** D-25 makes "my advisee" the entire authorisation rule
**Depends on:** Story 1.5 — there is no identity to check against until sign-in exists.
**Status:** Not started · **Blocked on proposed D-33** through Story 1.5.
**Added:** sprint 1, November 11 2026.

**Acceptance Criteria:**

**Given** a signed-in student
**When** `/student/<id>` is requested for a different student's id
**Then** the request is refused and carries none of that student's data.

**Given** a signed-in advisor
**When** `/advisor/<id>/student/<id>` is requested for one of their own advisees
**Then** the view opens as it does today.

**Given** a signed-in advisor
**When** the student named in the URL is not their advisee
**Then** the request is refused, because D-25 makes one-advisor-per-student the whole rule.

**Given** a signed-in student
**When** an advisor route is requested
**Then** the advisor view does not render.

**Given** any of the refusals above
**When** it is served
**Then** it does not reveal whether that id exists, so the route cannot be used to enumerate students.

**Given** a search is saved
**When** `search_request.actor_user_id` is written
**Then** it is the signed-in user — `app.py` today selects the first `app_user` row matching the id in the path, which is identity by assertion.

### Story 1.7: Sign out and end the session

As a student or an advisor,
I want to sign out,
So that the next person at a shared advising-office machine does not land in my record.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — small, but without it sign-in is a one-way door and the acting-as state has no exit.
**Covers:** FR33 · **UX:** UX-DR5
**Depends on:** Story 1.5.
**Status:** Not started · **Blocked on proposed D-33** through Story 1.5.
**Added:** sprint 1, November 11 2026.

**Acceptance Criteria:**

**Given** a signed-in user
**When** sign-out is chosen
**Then** the session is cleared and the sign-in page is served.

**Given** a session that has been signed out
**When** a student view is requested again
**Then** the sign-in page is served, and the signed-in response was not marked cacheable.

**Given** an advisor acting for a student
**When** sign-out is chosen
**Then** the acting-as state ends with the session and does not carry into the next sign-in.

---

## Epic 2: See what every offered course would close

A student browses the term's offered sections with the requirements each would close shown on
the card. This is the inverse question no existing system answers.

**FRs:** FR1, FR2, FR4, FR14 · **UX-DRs:** UX-DR9, UX-DR12, UX-DR13, UX-DR14, UX-DR25

### Story 2.1: See which of my outstanding requirements a section would close

As a student,
I want each offered section labelled with the requirements it would close for me,
So that I can tell what is worth taking without asking anyone.

**MoSCoW:** Must · **Size:** M · **Why:** Complex — the join between a student's outstanding buckets and each section's attributes is the product's core, and it must stay correct for sections whose topic is unknown.
**Covers:** FR1, FR4 · **UX:** UX-DR9, UX-DR12, UX-DR14
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** a section carrying a gen-ed attribute matching an outstanding requirement
**When** it appears in a list
**Then** it shows a badge naming each requirement it would close.

**Given** a section closing a must-include bucket
**When** the badge renders
**Then** it names the specific bucket — "Literature", not "Humanities".

**Given** a section whose topic cannot be determined
**When** it renders
**Then** the requirements it closes are still stated plainly and are not suppressed.

**Given** a section closing none of this student's outstanding requirements
**When** it renders
**Then** it shows no requirement badges rather than a misleading empty badge.

### Story 2.2: See why a section was tagged as it was

As a student,
I want to see which attribute produced which requirement tag,
So that I can check the tool rather than trust it.

**MoSCoW:** Should · **Size:** S · **Why:** Complex — the data is already in `offering_attribute`; this exposes it.
**Covers:** FR2 · **NFRs:** NFR7 · **UX:** UX-DR12
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** a tagged section
**When** I inspect a requirement badge
**Then** it states the Banner attribute or schedule type the tag came from.

**Given** a lab section satisfying the Natural Science lab rule
**When** I inspect it
**Then** the explanation cites `schedule_type = Laboratory`, not an attribute, because no Banner attribute contains "lab".

### Story 2.3: Browse the whole offering list with tags shown

As a student,
I want to browse every offered section with its tags and no search phrase,
So that the tool informs my own search rather than replacing it.

**MoSCoW:** Could · **Size:** M · **Why:** Dependent — needs Story 2.1's tagging; pagination over 9,621 sections is the open part.
**Covers:** FR14 · **NFRs:** NFR14 · **UX:** UX-DR25 · **Decisions:** D-04
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** no phrase has been entered
**When** the student view loads
**Then** offered sections are listed with requirement badges shown.

**Given** a long title or attribute
**When** it renders
**Then** it is shown in full and is never truncated mid-word.

---

## Epic 3: Find courses that fit my interests

A free-text phrase ranks offered sections so that closing a requirement *and* fitting the
phrase beats either alone.

**FRs:** FR9, FR10, FR11, FR12, FR13, FR15 · **NFRs:** NFR1, NFR3 · **UX-DRs:** UX-DR11, UX-DR12, UX-DR18, UX-DR22

### Story 3.1: Search by a free-text interest phrase

As a student,
I want to type what I am interested in, in my own words,
So that I do not have to pick from a taxonomy that does not describe my depth study.

**MoSCoW:** Must · **Size:** M · **Why:** Complex — index construction over 9,621 sections must stay under the 2-second budget and build once per process.
**Covers:** FR9, FR10 · **NFRs:** NFR1, NFR3 · **UX:** UX-DR11, UX-DR22 · **Decisions:** D-22
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** the student view
**When** I enter a phrase and submit
**Then** ranked results appear in under two seconds without the reranker.

**Given** results have been returned
**When** I read them
**Then** every result is a section offered in the modelled term.

**Given** a result list
**When** I copy the page URL and open it again
**Then** the same phrase and results are reproduced.

**Given** the input is empty
**When** I submit
**Then** the browse list is shown rather than an error.

### Story 3.2: Rank requirement-closing matches above either signal alone

As a student,
I want courses that both close a requirement and match my interest to come first,
So that the top of the list is the set of courses genuinely worth my time.

**MoSCoW:** Must · **Size:** L · **Why:** Uncertain — the weighting is hand-set and correctness is a judgment call, not a test.
**Covers:** FR11 · **Decisions:** D-19
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** a section closing an outstanding requirement and matching the phrase
**When** results are ordered
**Then** it ranks above any section doing only one of those.

**Given** two sections closing the same requirement
**When** one matches the phrase and one does not
**Then** the matching one ranks higher.

**Given** a section matching the phrase but closing nothing outstanding
**When** results are ordered
**Then** it still appears, below the sections that close something.

### Story 3.3: Surface sections that close two or more requirements

As a student,
I want courses that close more than one outstanding requirement raised,
So that I can graduate without taking more hours than I need.

**MoSCoW:** Must · **Size:** M · **Why:** Complex — must not re-introduce the same-requirement double count from AR12.
**Covers:** FR12 · **NFRs:** NFR8 · **Decisions:** D-11, D-19
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** a section closing two distinct outstanding requirements
**When** results are ordered
**Then** it ranks above comparable sections closing one, and both requirements are named.

**Given** a section carrying two buckets of the *same* requirement
**When** it is scored
**Then** it is credited once, not twice.

### Story 3.4: Collapse duplicate sections to one course

As a student,
I want thirty sections of one course shown once,
So that one course cannot fill the whole results page.

**MoSCoW:** Should · **Size:** S · **Why:** Complex — measured at up to 30 rows per course.
**Covers:** FR13 · **UX:** UX-DR12
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** a course with multiple offered sections matching
**When** results render
**Then** one card is shown with a stated count of additional sections.

**Given** a course with exactly one section
**When** it renders
**Then** no additional-sections note appears.

### Story 3.5: Be told plainly when my phrase matched nothing

As a student,
I want to know when nothing matched,
So that I do not read an arbitrary ordering as a recommendation.

**MoSCoW:** Should · **Size:** S · **Why:** Complex — must distinguish "no lexical match" from "no results at all".
**Covers:** FR15 · **UX:** UX-DR11, UX-DR18 · **Decisions:** D-17
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** a phrase matching no course text
**When** results render
**Then** the view states that the phrase matched nothing and does not present a ranked list as if it had.

**Given** a phrase matching nothing
**When** the message renders
**Then** it suggests no replacement vocabulary, because students report being unable to describe what fits.

---

## Epic 4: Trust the AI's ordering  *(core AI feature)*

A second-stage model reorders retrieved candidates and writes a reason per result. Grounding
is enforced in code, not requested in a prompt. Epic 3 remains fully functional without this.

**FRs:** FR16–FR22 · **NFRs:** NFR2, NFR4, NFR5, NFR10, NFR12, NFR16 · **UX-DRs:** UX-DR16, UX-DR35, UX-DR36 · **Architecture:** AR19

> **Story order is deliberate.** The validation boundary (4.1) is built before the reranking it
> guards (4.2). Reversed, a developer completing only the first story would ship an AI that can
> recommend a course that is not offered — the exact failure F-26 records and D-16 exists to
> prevent. Caught in Step 4 dependency validation.

### Story 4.1: Guarantee every recommendation is a real offered section

As a student,
I want to be certain nothing recommended is a course that is not actually offered,
So that I do not hit the failure both AI users in our research hit.

**MoSCoW:** Must · **Size:** L · **Why:** Complex — the validation boundary is the product's differentiator and must hold against malformed output.
**Covers:** FR17, FR18, FR19 · **UX:** UX-DR16 · **Decisions:** D-16 · **Evidence:** F-26
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** the model returns an identifier not in the candidate set
**When** results are assembled
**Then** it is discarded, never shown, and the discarded count is reported on the page.

**Given** the model omits a candidate it was given
**When** results are assembled
**Then** that candidate is appended rather than lost.

**Given** the model returns only identifiers from the candidate set
**When** results are assembled
**Then** the discarded count is zero and all candidates are present.

**Given** the model returns malformed or unparseable output
**When** results are assembled
**Then** nothing from that response is shown and the deterministic order is served.

**CANNOT ANSWER** — the response cannot be parsed
**Then** no recommendation is shown from it; the deterministic order stands.

**SHOULD NOT ANSWER** — the model proposes a course outside the offered set
**Then** the proposal is dropped silently from results and counted visibly.

**SHOWS ITS WORK** — every search
**Then** the page states how many candidates were validated and how many discarded.

### Story 4.2: Reorder candidates by relevance and say why

As a student,
I want the ordering improved beyond keyword matching, with a reason on each result,
So that a course about my interest is not ranked below one that merely shares a word.

**MoSCoW:** Must · **Size:** L · **Why:** Uncertain — the live path has never run against a real credential, so the response schema is unvalidated (AR19).
**Depends on:** Story 4.1 — reranking must not ship before the validation boundary exists (D-16).
**Covers:** FR16, FR20 · **NFRs:** NFR2, NFR10, NFR16 · **UX:** UX-DR16, UX-DR36
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** a credential is present and candidates were retrieved
**When** results render
**Then** they are in model-reordered order and each carries a one-line reason drawn from that course's text.

**Given** reranking is active
**When** a reason renders
**Then** it is visibly labelled as model-produced, not presented as catalog fact.

**Given** the phrase "ancient philosophy"
**When** results render
**Then** Ancient Philosophy ranks above Germanic Mythology, which the lexical ranker gets wrong.

**CANNOT ANSWER** — the candidate text is too thin to judge relevance
**Then** the candidate keeps its deterministic position and no reason line is invented for it.

**SHOULD NOT ANSWER** — asked to decide whether a course counts toward the depth study
**Then** relevance ordering only; the requirement judgment is not made here and is routed to the advisor.

**SHOWS ITS WORK** — any reordering
**Then** the reason names the course text it came from, and the ordering method is stated on the page.

### Story 4.3: Keep my personal data off the wire

As a student,
I want nothing about me sent to a third party,
So that using the tool does not expose my record.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — asserted by test rather than by comment; the payload must be pinned.
**Covers:** FR22 · **NFRs:** NFR12, NFR13
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** a rerank request is built
**When** its payload is inspected
**Then** it contains only the phrase, outstanding bucket names, and public catalog text.

**Given** a rerank request is built
**When** its payload is inspected
**Then** it contains no name, no student id, no completed coursework and no grades.

**Given** the test suite runs
**When** the payload assertion executes
**Then** it fails if any personal field is added later.

### Story 4.4: Degrade to deterministic ranking rather than failing

As a student,
I want results even when the model call fails,
So that a demonstration or an advising appointment is never blocked by a network problem.

**MoSCoW:** Must · **Size:** M · **Why:** Complex — must cover credential, network, timeout and schema failures identically.
**Covers:** FR21 · **NFRs:** NFR4, NFR5 · **UX:** UX-DR16, UX-DR35
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** no credential is configured
**When** a search runs
**Then** deterministic results are served and the page states the ordering method.

**Given** the model call raises any exception
**When** a search runs
**Then** the failure is logged at warning with its exception type and deterministic results are served.

**Given** a fallback has occurred
**When** results render
**Then** the page says so rather than presenting the fallback as a rerank.

---

## Epic 5: See what the system cannot determine

Rotating-topic sections appear with the unknown part named. Uncertainty attaches to topical
fit only, never to what a section counts for.

**FRs:** FR23, FR24, FR25 · **UX-DRs:** UX-DR15 · **Architecture:** AR18 · **Decisions:** D-21, D-27

### Story 5.1: Show rotating-topic sections with the topic flagged unknown

As a student,
I want a special-topics course shown with a clear note that its topic cannot be determined,
So that I ask my advisor instead of guessing or missing it entirely.

**MoSCoW:** Must · **Size:** M · **Why:** Uncertain — the current detector under-matches on 14 of 259 courses and the fix must be title-aware (AR18).
**Covers:** FR23, FR25 · **UX:** UX-DR15
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** a course with a special-topics section and a generic rotating description
**When** it appears in results
**Then** it is shown, not hidden, and labelled "cannot determine the topic — ask your advisor".

**Given** a course with the special-topics attribute but a specific description
**When** it appears in results
**Then** it is **not** flagged, because the attribute alone is not evidence.

**Given** a Legends section, all of which carry the special-topics attribute
**When** it appears
**Then** it is not flagged, and it still closes its First-Year Compass requirement.

**Given** a description reading "Subject matter varies" or "topics vary"
**When** flagging runs
**Then** the course is flagged, closing the gap where the pattern matched "varies" but never "vary".

### Story 5.2: Keep requirement closure trustworthy when the topic is not

As a student,
I want a flagged course to still tell me what it counts for,
So that uncertainty about the subject does not hide a requirement I could close.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — the two halves of the score must stay separate and must not be blended.
**Covers:** FR24 · **Decisions:** D-27
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** a flagged course that closes an outstanding requirement
**When** it renders
**Then** the requirement badge is shown with full confidence and no hedging.

**Given** a flagged course
**When** it is scored
**Then** the uncertainty reduces only its relevance contribution, never its requirement contribution.

**Given** a flagged course that closes a requirement nothing else closes
**When** results render
**Then** it is not ranked out of view.

---

## Epic 6: Track New College seminar themes

A student sees which of the three themes each New College seminar closes, and which seminars
have no published theme.

**FRs:** FR26, FR27 · **NFRs:** NFR19 · **UX-DRs:** UX-DR15 · **Architecture:** AR5, AR6 · **Decisions:** D-23, D-31

### Story 6.1: Load the term's seminar themes from the course booklet

As an advisor,
I want the term's published seminar themes loaded into the system,
So that theme coverage can be tracked at all, given Banner carries no theme attribute.

**MoSCoW:** Should · **Size:** M · **Why:** Dependent — the only source is a per-term PDF with no feed, so the refresh is manual and must be documented.
**Covers:** FR26 · **NFRs:** NFR19 · **Architecture:** AR5
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** the term theme file
**When** the loader runs
**Then** each New College course is stored with its theme, and dual designations such as SPSC/CC are preserved.

**Given** the loader runs twice
**When** it completes
**Then** the result is identical and no duplicate rows are created.

**Given** a course in the file that is not in the term's offerings
**When** the loader runs
**Then** it is skipped and reported rather than creating an orphan.

### Story 6.2: See which theme each seminar closes

As a student,
I want each New College seminar to show its theme,
So that I can tell which of the three I still need.

**MoSCoW:** Should · **Size:** L · **Why:** Complex — adds a requirement kind the schema lacks: coverage across three themes plus a level distribution, not hours against a pool.
**Covers:** FR26 · **Architecture:** AR6
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** a seminar with a published theme
**When** it renders
**Then** the theme is shown alongside its other requirement badges.

**Given** a student missing one theme
**When** the requirement panel renders
**Then** the missing theme is named and seminars closing it are identifiable.

**Given** a student with all three themes covered but too few upper-level seminars
**When** the panel renders
**Then** the level shortfall is reported separately from theme coverage.

### Story 6.3: Flag seminars with no published theme

As a student,
I want a seminar with no published theme shown as such,
So that I ask rather than assume it counts for the theme I need.

**MoSCoW:** Should · **Size:** S · **Why:** Complex — reuses the existing uncertainty guardrail; three of fifteen seminars this term are affected.
**Covers:** FR27 · **UX:** UX-DR15 · **Decisions:** D-27, D-31
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** a seminar the booklet lists with no theme designation
**When** it renders
**Then** it is shown as a seminar with the theme marked unknown and the student directed to their advisor.

**Given** such a seminar
**When** theme coverage is computed
**Then** it is not counted toward any theme, and it is not hidden from results.

---

## Epic 7: Advise a student in one pass

An advisor reviews a whole proposed term against every outstanding requirement at once, and
confirms or rejects depth-study proposals.

**FRs:** FR28–FR32 · **UX-DRs:** UX-DR17, UX-DR19, UX-DR20, UX-DR21, UX-DR36 · **Architecture:** AR8, AR9

**Sprint 1 adds Stories 7.6 and 7.7** — search the advisee set by name, and show each result's
depth study and recent phrases. FR28 is an advisee *list*; a search is more than that, and no FR
covers it. A third story, 7.8, carried a degree-progress indicator and was dropped the day it
was added — see above.

### Story 7.1: See my advisees and how much each has outstanding

As an advisor,
I want my advisees listed with a count of open requirements,
So that I can see who needs attention before the appointment.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — reuses the Epic 1 computation per advisee.
**Covers:** FR28 · **UX:** UX-DR19
**Status:** Implemented — evidence in the status table above. **Modified by Stories 7.6 and 7.7:** the list becomes the no-query state of a search.

**Acceptance Criteria:**

**Given** an advisor with advisees
**When** the advisor view loads
**Then** each advisee is listed with their classification and a count of open requirements.

**Given** an advisor with no advisees
**When** the view loads
**Then** a designed empty state is shown rather than a blank region.

### Story 7.2: Search on a student's behalf and see what they see

As an advisor,
I want to run the student's own search and see the student's own result,
So that we are looking at the same thing during the appointment.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — one template and one code path; divergence between the two views is a defect.
**Covers:** FR29 · **UX:** UX-DR21
**Status:** Implemented — evidence in the status table above. **Modified by Story 1.6:** the route needs an ownership check once sign-in exists.

**Acceptance Criteria:**

**Given** an advisor viewing a student
**When** a phrase is submitted
**Then** the results are identical to what the student sees for the same phrase.

**Given** an advisor viewing a student
**When** the page renders
**Then** an acting-as banner names the student.

### Story 7.3: Check a proposed term against every outstanding requirement at once

As an advisor,
I want to enter a student's proposed courses and see the whole term checked in one pass,
So that I confirm a plan in one review instead of course by course from memory.

**MoSCoW:** Must · **Size:** L · **Why:** Complex — needs a proposed-term representation and route that do not exist, plus per-requirement roll-up across the set.
**Covers:** FR30 · **Architecture:** AR8 · **UX:** UX-DR20 · **Evidence:** F-04
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** a set of proposed sections
**When** the review runs
**Then** every outstanding requirement shows what the proposed term would close and what would remain.

**Given** a proposed term leaving a requirement untouched
**When** the review renders
**Then** that requirement is called out as unaddressed.

**Given** two proposed courses closing the same single-course requirement
**When** the review runs
**Then** the redundancy is reported rather than counted twice.

**Given** an empty proposed term
**When** the review runs
**Then** every requirement shows as unaddressed rather than erroring.

### Story 7.4: Confirm or reject proposed depth-study candidates

As an advisor,
I want depth-study candidates proposed for my decision rather than asserted,
So that the judgment that is mine stays mine.

**MoSCoW:** Should · **Size:** L · **Why:** Uncertain — depth study has no machine-readable record to check against, so the proposal can only ever be a suggestion.
**Covers:** FR31 · **Architecture:** AR9 · **UX:** UX-DR36 · **Evidence:** F-04 · **Decisions:** D-17, D-26
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** a proposed depth-study candidate
**When** it renders
**Then** it is labelled "proposed" and shows the text it was derived from.

**Given** a proposed candidate
**When** I confirm or reject it
**Then** the decision is recorded against my identity and the proposal never becomes fact without it.

**CANNOT ANSWER** — the depth-study description is too thin to propose from
**Then** nothing is proposed, what is missing is stated, and no guess is offered.

**SHOULD NOT ANSWER** — asked whether a course definitively counts toward the depth study
**Then** the system proposes only and routes the decision to the advisor.

**SHOWS ITS WORK** — every proposal
**Then** the source text is shown beside it.

### Story 7.5: Warn when nothing offered can close a requirement

As a student,
I want to be told when no offered course closes a requirement,
So that I can plan around it instead of discovering it too late.

**MoSCoW:** Should · **Size:** M · **Why:** Complex — computable from outstanding buckets against offerings, but must not fire on requirements already satisfied.
**Covers:** FR32 · **UX:** UX-DR17 · **Evidence:** F-12, F-13
**Status:** Not started — evidence in the status table above.

**Acceptance Criteria:**

**Given** an outstanding requirement with no offered section closing it
**When** the requirement panel renders
**Then** a warning states that nothing this term closes it.

**Given** an outstanding requirement with at least one offered section
**When** the panel renders
**Then** no warning appears.

**Given** a requirement the student has already satisfied
**When** the panel renders
**Then** no warning appears regardless of what is offered.

### Story 7.6: Find an advisee by name

As an advisor,
I want to type part of a student's name and get my matching advisees,
So that I can open the right student during an appointment instead of reading the whole list.

**MoSCoW:** Must · **Size:** M · **Why:** Complex — the advisee list is one flat table today; the search has to stay scoped to the signed-in advisor's own advisees and share one row component with the unsearched list, or the two will diverge.
**Covers:** FR28 — extends it from a list to a search · **UX:** UX-DR19, UX-DR18 (a fourth variant), UX-DR22 — the query lives in the query string, as the phrase search's does
**Depends on:** Stories 1.5 and 1.6 — "my advisees" is not a defined set without a signed-in advisor.
**Status:** Not started · Modifies Story 7.1, which becomes the no-query state. Adds a variant to Story 8.4.
**Added:** sprint 1, November 11 2026.

**Acceptance Criteria:**

**Given** a signed-in advisor with advisees
**When** no query has been entered
**Then** the full advisee list renders as it does today, with its open-requirement counts.

**Given** a query
**When** it matches part of an advisee's name
**Then** only matching advisees are listed, each linking to the existing advisor-for-student view.

**Given** a query naming a real student who is not this advisor's advisee
**When** results render
**Then** that student does not appear, and nothing in the response reveals that they exist.

**Given** a query matching none of this advisor's advisees
**When** results render
**Then** the empty state names the query and says the search covers this advisor's advisees only.

**Given** a search result list
**When** I copy the page URL and open it again
**Then** the same query and the same results are reproduced.

**Given** an advisor with the full student body as advisees
**When** a query is run
**Then** the page does not compute a requirement roll-up for every non-matching advisee —
`advisor_view` calls `db.outstanding_buckets` once per advisee, which is ten queries each
(one requirement query plus one bucket query for each of the nine bucket requirements).

### Story 7.7: See what each advisee is working on in the search result

As an advisor,
I want each search result to show that student's depth study and the words they last searched,
So that I recognise the right student and know what they are pursuing before opening them.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — both fields already exist (`student.depth_study_label`, `search_request.phrase`) and neither is on the advisor screen. The care is in labelling them as the student's own words rather than as a system judgment (D-22).
**Covers:** FR28 · **UX:** UX-DR19 · **Decisions:** D-22 — the depth study is a free-text working label and ranking never reads it; D-26 — nothing is approved before the third-year review · **Evidence:** F-04
**Depends on:** Story 7.6.
**Status:** Not started.
**Added:** sprint 1, November 11 2026.

**Acceptance Criteria:**

**Given** an advisee with a depth-study label
**When** the row renders
**Then** the label is shown as that student's own working label, not as a confirmed programme of study.

**Given** an advisee with no label recorded
**When** the row renders
**Then** it says the label is not recorded rather than leaving the field blank.

**Given** an advisee who has run searches
**When** the row renders
**Then** it shows their most recent interest phrases, attributed as what the student typed.

**Given** an advisee who has never searched
**When** the row renders
**Then** it says so, and no interest is inferred from their coursework.

**Given** any row
**When** it renders
**Then** nothing on it asserts whether a course or a phrase fits the depth study — that judgment stays the advisor's.

### Story 7.8: Show a degree-progress indicator in the search result — DROPPED

**Dropped by the project owner on November 11, 2026**, the same day it was added and before
proposed D-34 was recorded. The acceptance criteria written for it are not reproduced, because
none of them can be satisfied while the computation behind the figure is wrong.

**Why.** `db.numeric_progress` reads **482%** for the seeded senior — see "Dropped — the
degree-percent-complete indicator" above for the measurement. There was no honest figure to
render, so there was no compromise worth choosing and no decision worth recording.

**Status:** Dropped. Not blocked and not deferred: the underlying computation has to be fixed
before any roll-up figure is worth specifying, and that fix is a cleanup item rather than a
feature.
**Added:** sprint 1, November 11 2026. **Dropped:** November 11 2026.

Stories 7.6 and 7.7 never depended on it and are unaffected. The `AdviseeRow` component it would
have extended is still built by 7.7.

---

## Epic 8: Design system and accessibility

Cross-cutting interface work: the token set, semantic styling, accessibility, responsive
behaviour and empty states. Added at Step 3 to carry the UX-DRs that are not specific to one
feature epic.

**UX-DRs:** UX-DR1–UX-DR4, UX-DR7, UX-DR18, UX-DR23, UX-DR24, UX-DR25, UX-DR26–UX-DR35

### Story 8.1: Put colour, type and spacing behind tokens

As a developer,
I want one token set the whole interface draws from,
So that a colour or spacing change happens in one place and stays consistent.

**MoSCoW:** Should · **Size:** M · **Why:** Complex — requires auditing every literal colour in the stylesheet and replacing it.
**Covers:** UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR23, UX-DR24
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** the stylesheet
**When** it is audited
**Then** no literal colour value remains outside the token definitions.

**Given** the token set
**When** contrast is measured
**Then** no token used for text falls below 4.5:1 on its background.

**Given** a status that was styled by element or position
**When** the refactor is complete
**Then** it is styled by a semantic class instead.

### Story 8.2: Meet WCAG 2.1 AA

As a student using assistive technology,
I want the interface to meet AA,
So that I can use it at all.

**MoSCoW:** Should · **Size:** L · **Why:** Complex — spans contrast, focus, keyboard order, screen-reader text and landmarks, and both reference systems fail parts of it.
**Covers:** UX-DR7, UX-DR26, UX-DR27, UX-DR28, UX-DR29, UX-DR30, UX-DR31
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** the finished palette
**When** a contrast audit runs
**Then** body text is at least 4.5:1, large text at least 3:1, non-text indicators at least 3:1, and the result is recorded.

**Given** any status indicator
**When** colour is removed
**Then** the state is still distinguishable by glyph, shape or text.

**Given** keyboard navigation
**When** I tab through the student view
**Then** the phrase input is the first stop, focus is visible at 3:1 or better, and order follows the DOM.

**Given** a screen reader
**When** a requirement status is reached
**Then** its state is announced as text, not as an unlabelled element.

**Given** a screen reader
**When** moving by landmark
**Then** each requirement group is reachable without traversing every result.

### Story 8.3: Stop truncating the fields the product exists to surface

As a student,
I want titles and attributes shown in full,
So that the tool does not repeat the failure it was built to fix.

**MoSCoW:** Must · **Size:** S · **Why:** Complex — truncation is the specific defect observed in the reference system.
**Covers:** UX-DR25
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** a long course title or attribute
**When** it renders at any supported width
**Then** it is shown in full with no mid-word truncation.

**Given** any requirement-bearing field — title, attribute, instructor
**When** the page renders
**Then** no ellipsis abbreviation is applied to it by CSS or by template logic.

**Given** a field that is genuinely empty, such as a section with no listed instructor
**When** it renders
**Then** an explicit placeholder is shown rather than a blank cell that reads as truncation.

### Story 8.4: Give every list a designed empty state

As a student,
I want to be told why a list is empty,
So that I can tell the difference between no results and a broken page.

**MoSCoW:** Should · **Size:** M · **Why:** Complex — three distinct variants with different copy.
**Covers:** UX-DR18, UX-DR34
**Status:** Implemented — evidence in the status table above. **Modified by Story 7.6:** a fourth empty-state variant, no advisee matched.

**Acceptance Criteria:**

**Given** no phrase match, no advisees, or no outstanding requirements
**When** the view renders
**Then** the matching empty state is shown with copy specific to that case.

**Given** any list in the product
**When** it is empty
**Then** it never renders as a blank region.

### Story 8.5: Reflow rather than scroll sideways

As a student on a laptop or phone,
I want the layout to reflow,
So that I am not scrolling a wide grid to read an attribute.

**MoSCoW:** Could · **Size:** M · **Why:** Dependent — needs the card components from Epics 1–3 to exist first.
**Covers:** UX-DR32, UX-DR33
**Status:** Partial — evidence in the status table above.

**Acceptance Criteria:**

**Given** a viewport below 640px
**When** the view renders
**Then** requirement and result cards reflow from two columns to one.

**Given** any supported width
**When** the page renders
**Then** the page body never scrolls horizontally; wide content scrolls inside its own container.

### Story 8.6: Make reranking visible rather than silent

As a student,
I want to see how my results were ordered,
So that I know whether the AI ran and whether it fell back.

**MoSCoW:** Should · **Size:** S · **Why:** Dependent — needs Epic 4's provenance data.
**Covers:** UX-DR35
**Status:** Implemented — evidence in the status table above.

**Acceptance Criteria:**

**Given** results were reranked
**When** they render
**Then** the ordering method and the validated/discarded counts are stated.

**Given** reranking fell back
**When** results render
**Then** the fallback is stated plainly rather than presented as a rerank.
