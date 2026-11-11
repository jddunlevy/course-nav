---
title: 'Chat-led query construction'
slug: 'chat-led-query-construction'
created: '2026-11-11'
status: 'design-approved'
kind: 'design'
sub_projects: ['A — chat-led conversation with sidebar filters', 'B — depth study as a typed, mutable record']
proposed_decision: 'D-36'
open_questions: ['Q-2 (from the ranker spec)', 'D-36 must be recorded in the elicitation log']
depends_on: 'docs/specs/tech-spec-relevance-requirement-separation.md'
dropped: 'Grad-school prerequisite awareness — no prerequisite data exists'
---

# Design: Chat-led query construction

**Created:** 2026-11-11 · **Status:** design approved, not yet specced for implementation

This covers sub-projects **A** (chat-led conversation, filters moved to a sidebar,
requirements no longer the organising frame) and **B** (depth study as a typed, mutable
record that influences ranking). They are designed together because they are one screen.

Sub-project **C** — a feedback loop where the student marks courses interesting or not
and suggestions refine — is deliberately deferred to its own cycle. It needs a new
entity and a defined rule for how feedback moves ranking, neither of which this design
settles.

## What was dropped, and why it must stay dropped

**Grad-school prerequisite awareness is out of scope permanently, not deferred.** The
original request included letting a student state grad-school intent so the system could
account for prerequisites. The data does not exist:

- `schema.sql:12` defers `prerequisite` as an entity, but the gap is larger than a
  deferred table. There is no source to populate one from.
- `data/spring2027.csv` — the Banner section feed the database is built from — has 30
  columns and none is a prerequisite or a restriction.
- `data/course-descriptions.csv` mentions a prerequisite in **20 of 3,172 courses
  (0.6%)**, as unstructured prose. Example, `BSC 403`: *"Prerequisites: BSC 114:115 or
  BSC 118, BSC 116:117 or BSC 120, and junior or senior standing, formal application,
  and a satisfactory interview."* Parsing that into a dependency graph from 0.6% coverage
  would produce a confident-looking structure over almost no data.

Delivering it would need a prerequisite entity, a new scrape to populate it, **and** a
model of what specific graduate programmes require — external data nobody on this
project has collected. That is data acquisition, not design. Recorded here so a later
sprint does not resurrect it as though it were a UI feature.

## Decisions

All eight were settled in session on 2026-11-11 and together constitute **proposed
D-36**. The elicitation running log governs and lives outside this repository, so nothing
here is settled until the owner records it.

### 1. The chat refines the query only. It never names a course.

The model's entire output is a structured query — a phrase plus filter state. Every
course the student sees comes from the existing validated renderer.

This is the load-bearing decision. **F-26** is that both AI users in the elicitation
reported an AI recommending courses that were not offered, and **D-16** makes grounding
in the real offered list the product's differentiator. `rank_llm.py`'s docstring calls
that guard "the whole safety argument" for using a model at all. A chat interface is a
text-generation surface by default, so the guarantee has to be re-established
deliberately or it is silently lost.

Keeping the generation surface and the recommendation surface physically separate costs
nothing and preserves F-26/D-16 exactly as it stands.

Two alternatives were considered and rejected:

- *The chat may discuss the validated list* — naming only courses already retrieved,
  with `_validate()`'s guard extended from a JSON array into free prose. Rejected
  because validating CRNs inside generated text is materially harder than validating an
  array, and a paraphrase naming a plausible course without its CRN defeats the check
  entirely.
- *The chat generates freely; only result cards are grounded* — rejected because it
  reintroduces the exact F-26 failure, relocated from the list into the prose.

There is a real cost: the chat reads as a smart search box rather than an advisor. It is
accepted, because the chat still earns its place — see decision 2's note on D-17.

### 2. The depth study is context for query construction, not a scoring term.

The depth study is given to the model as background when it builds the query. Asked for
"something quantitative", the chat produces `"environmental statistics, spatial data"`
rather than `"statistics"`, and states what it searched for.

**D-22 survives literally.** `schema.sql:35-36` says of `depth_study_label`: *"Ranking
never reads it; it reads the typed phrase."* That stays true — the ranker still never
reads the field. The chat does, and hands the ranker a better phrase. What needs
amending is the comment's *scope*, not its claim, and the amendment is one clarifying
line rather than a reversal. `templates/results.html:28` currently tells the student on
screen *"free text only — ranking never reads it, D-22"*; that copy needs updating to
match.

Two alternatives were considered and rejected:

- *A persistent scoring term*, always contributing to relevance. Rejected because it
  changes results through a channel the student cannot see, and it is a straight
  reversal of D-22 requiring ranker changes.
- *An explicit per-search toggle*. Rejected as a non-choice: defaulted off it is a
  feature nobody uses, defaulted on it is the rejected option with extra clicks.

**Accepted loss.** A persistent scoring term is the only one of the three that can
surface a course the student would never have thought to ask about. Sub-project C's
feedback loop is the better place to recover that.

**Why the chat is worth building at all.** **D-17** records that students cannot describe
what fits them, which is why there is no autocomplete on the phrase box
(`templates/results.html:93-95`). A single text field therefore puts the whole burden of
articulation on the student. A conversation that interrogates vague interest into a
usable query is a genuine improvement on a text field, and it needs none of the risk
rejected in decision 1.

### 3. Requirements become sidebar filter state and per-card badges. One ranked list.

Requirements stop **ordering** the page. They do not stop being **visible**: every card
still carries its `RequirementBadge` set, and the sidebar holds a "closes a requirement"
toggle plus per-bucket checkboxes.

The distinction matters because **F-15 / D-02** — "which of my outstanding requirements
would this course close?" — is the inverse question no existing system answers, and
Epic 2 exists entirely to serve it. Banner cannot answer it and DegreeWorks cannot
answer it. Making requirements "not the focus" could quietly discard the product's second
differentiator. It does not here: the badges still answer the inverse question on every
card. What is dropped is requirement-*driven ranking*, which is the defect the ranker
spec exists to fix.

**This closes Q-1 in `tech-spec-relevance-requirement-separation.md`** as "badges inside
group 1, no separate group-2 section". Two independent lines of evidence agree:

- This design makes requirements filter state, so a separate dual-fit section has no
  place in it.
- The ranker's own Task 14 measurement found that a separate section is undercut by the
  display cap. Student 1's only dual-fit course for "climate policy" is at group 1
  position **42**, outside `DISPLAY_LIMIT = 40`, and because group 2 derives from the
  capped group 1 (TD-3, Task 8) the top-billed section renders **empty** on the headline
  phrase and the seeded student. Displayed group 2 across the six measured cases: 0, 3,
  2, 1, 8, 5.

A top-billed section that can render empty while a dual-fit course exists is worse than
a badge. The grouped return from `group_results()` stays as it is — this is a
presentation decision, not a ranker change.

### 4. Filters are settable from the conversation and the sidebar both.

### 5. The sidebar query state is the single source of truth. The chat writes to it.

Each turn the chat proposes filter changes; they land in the sidebar as visible state;
that state is what gets searched. The student can override anything by clicking. The chat
reads current sidebar state at the start of every turn, so it cannot contradict what is
on screen.

Decisions 4 and 5 are inseparable: as soon as two things can write one query they can
disagree. One state object with the chat as a writer to it makes divergence structurally
impossible, costs no model round-trip per click, and keeps the chat's effect on the query
visible — the same principle that makes decision 2 acceptable.

Two alternatives were considered and rejected:

- *The chat owns the query; sidebar clicks inject a message* — coherent as a single
  narrative, rejected because every click costs a model round-trip in an interactive
  path.
- *Two independent states merged at search time* — easiest to build, rejected because the
  chat could never adjust a filter, which contradicts decision 4.

### 6. The conversation resets between sessions. The depth study persists.

- **Conversation** — session only. No transcript is stored.
- **Depth study** — persists. It is a record on the student, and the point of
  sub-project B is that it can be updated.
- **Filter state** — resets with the conversation. Filters are query state the
  conversation built; carrying them across sessions would leave a student wondering why
  half the catalog is missing.

This has a large simplifying consequence: **no new tables.** See Data model.

### 7. An advisor opens their own fresh conversation on the student's behalf.

Same code path, same ranker, same depth study and standing. The transcript is the
advisor's. Nothing of the student's conversation is ever visible, because by decision 6
nothing is kept.

**FR29** requires that an advisor sees exactly what the student sees, and archived
Story 7.2 is explicit that "one template and one code path; divergence between the two
views is a defect". A conversational interface complicates that by introducing a
transcript to be on one side or the other of. Decision 6 dissolves the problem: FR29
holds as written — the advisor sees what the student *would* see for the same query — and
the privacy question answers itself because there is no persisted transcript to expose.
The acting-as banner (`templates/results.html:14-20`, UX-DR5) is unchanged.

Two alternatives were considered and rejected:

- *Conversation scoped to the student and shared within a session* — useful in a live
  appointment, rejected because it needs a real-time story the prototype does not have
  and makes "session" mean something spanning two people.
- *Advisor keeps the current phrase box, students get the chat* — rejected because it
  breaks the one-code-path rule outright and leaves the advisor with the worse tool.

### 8. Grad-school prerequisite awareness is dropped.

See *What was dropped*.

## Architecture

The defining property: **this is a layer above the ranker. Nothing inside the ranker
changes.**

```
conversation turns ──┐
current query state ─┼──→ converse.py ──→ query delta ──→ validate ──→ session query
depth study ─────────┘                                                      │
                                                                            ▼
                     rank() ──→ group_results() ──→ rerank_groups() ──→ render
                                    (entirely unchanged)
```

### `converse.py` — a new module, kept separate from `rank_llm.py`

Separate rather than folded in, deliberately. The two modules do different jobs with
different failure modes and different guards: `rank_llm.py` reorders a validated list of
real CRNs, `converse.py` emits a query and must never see a CRN at all. Keeping them
apart means neither one's guard can be weakened by a change to the other, and it keeps
each file small enough to reason about — which the existing code already treats as a
value.

It mirrors `rank_llm.py`'s established shape: a JSON-schema structured output, a
validator, and an explicit degradation path.

**The guarantee is structural, not instructional.** The output schema has fields for
`phrase` and the known filters and **no field in which a course could be named**. A
model physically cannot return a course recommendation through it. This is the same
reasoning that makes `_validate()` trustworthy — the guard lives in the shape of the
data, not in a request the model may ignore.

**Validation follows `_validate()`'s pattern.** Every filter field and value is checked
against an allowlist; anything unrecognised is dropped and counted; the count is
surfaced. A model that invents a filter must not be able to silently narrow a student's
catalog. The dropped count appears in the UI for the same reason FR18's discarded-CRN
count does: a user who cannot see that validation ran has no reason to believe it did.

**Failure degrades, never 500s**, matching `app.py:109-113`. With no credential, or on
any exception, the chat panel falls back to the current phrase box and the ranker still
serves results. A graded demo must not depend on a network round trip.

### Flow in `app.py`

The conversation turn applies its validated delta to the session query, and the existing
pipeline runs untouched: `rank()` → `group_results()` → `rerank_groups()` → render.

## Data model

Almost nothing changes, which is a direct consequence of decision 6.

| What | Change |
| --- | --- |
| `student.depth_study_label` | **Already exists** (`schema.sql:37`). Needs a setter in `db.py` and a route — the field is currently write-once at seed time (`seed.py:135`), with no setter anywhere. |
| `schema.sql:35-36` comment | Gains a clarifying line: the ranker still never reads the field; the chat may, to construct a phrase. The existing claim is not withdrawn. |
| Conversation state | Session only. No table. |
| Filter state | Session only. No table. |
| `search_request` / `recommendation` | Unchanged. Search history and the "Recent:" affordance keep working. |

**No migration.**

## Components

**New:**

| Component | Purpose |
| --- | --- |
| `ChatPanel` | Transcript and input. |
| `QuerySidebar` | Phrase chip, filter controls, requirement toggle and per-bucket checkboxes. The single source of truth from decision 5. |
| `DepthStudyBox` | Editable, persists. Sub-project B's whole surface. |
| `QueryProvenance` | States what was actually searched — *"searched for 'environmental statistics, spatial data', excluding labs"* — plus any dropped filter count. Decisions 2 and 5 both depend on the chat's effect being visible rather than hidden, so this is load-bearing, not decoration. |

**Reused unchanged:** `CourseResultCard` (UX-DR12), `RequirementBadge`, `UncertaintyFlag`
(UX-DR15), `RankProvenance` (UX-DR16), `EmptyState` (UX-DR18, UX-DR34).

`docs/UX Design.md` will need the four new components added and `UX-DR18`'s variant list
revisited — the ranker spec already changes that component's contract, and this design
adds further states.

## Open questions and follow-ups

- **D-36 must be recorded in the elicitation log** before any of this is built. The log
  governs over the PRD and the ERD and is not in this repository.
- **D-22's scope amendment** (decision 2) rides along with D-36.
- **Q-2 from the ranker spec is still open** and this design does not resolve it: whether
  collapsing requirement-only results behind a `<details>` weakens D-21's "shown, never
  hidden" past what is acceptable. Note that decision 3 changes its shape — with
  requirements as filter state there may be no collapsed group to argue about — so Q-2
  should be re-read against this design before being answered.
- **Decision-ID collision, resolved here.** Sprint 1 claimed D-33 (sign-in reverses
  AR16) and D-34 (what a degree-percent figure may claim). The ranker spec had also used
  D-33 for its FR11/FR12 amendment; it is renumbered **D-35**. This design is **D-36**.
  The owner may renumber when writing the log; the point is that no two pending decisions
  share an id in the repository.
- **New FRs needed** for chat-led query construction, depth-study editing, and the filter
  sidebar. `bmad-edit-prd` is the right next tool.
- **Sub-project C** (feedback loop) gets its own design cycle. It needs a new
  per-student-per-course entity and a defined rule for how feedback moves ranking —
  neither settled here.

## Dependencies

- **`docs/specs/tech-spec-relevance-requirement-separation.md` must land first.** This
  design renders the grouped result structure that spec produces, and decision 3 resolves
  that spec's Q-1. Tasks 10-11 of that spec are the template work this design then builds
  on.
- No new packages beyond the optional `anthropic>=1.0` already present.
- No database migration.
