---
stepsCompleted: ['parse-epics', 'generate-sprint-status', 'validate-coverage']
inputDocuments:
  - 'docs/epics.md (the live backlog; 8 epics, 38 stories after the sprint-1 additions)'
  - 'docs/sprint-status.yaml (generated from it; 8 epics, 38 stories, 8 retrospectives)'
  - 'docs/PRD.md, docs/Architecture.md, docs/UX Design.md'
  - 'app.py, db.py, rank.py, rank_llm.py, ingest.py, schema.sql, templates/*.html, static/style.css (read at commit 5fb1330)'
  - 'elicitation/findings - running log.md (source of truth, D-01 to D-32 -- not in this repository)'
workflowType: 'sprint-planning'
authoredBy: 'bmad-sprint-planning, November 11 2026'
---

# Sprint 1 plan - New College Course Navigator

**Owner:** Jaxon
**Date:** November 11, 2026
**Tracking file:** [`sprint-status.yaml`](sprint-status.yaml) — the machine-readable half of this
plan. Every epic and story in [`epics.md`](epics.md) appears there exactly once.
**Sprint length:** not set here. The class cadence lives in the run sheet under `sprint/`, which
is not in this repository.

## The sprint goal

Two features the project owner asked for:

1. A formal sign-in page, replacing the role picker.
2. On the advisor side, search by student — with each result showing that student's depth study
   or interest.

A degree-progress indicator was asked for as part of feature 2 and **dropped on November 11,
2026**, the day it was specced: `db.numeric_progress` reads 482% for the seeded senior, so there
was no honest figure to render. The defect it exposed is live in today's UI and is routed to the
cleanup pass. Full record in [`epics.md`](epics.md).

## The gate: one decision, not yet made

The sign-in feature contradicts something already decided, and this project routes an open
decision to the owner rather than guessing it. The full statement, with options and
consequences, is in [`epics.md`](epics.md). In short:

| Proposed ID | What it decides | What it reverses | Blocks |
|---|---|---|---|
| **D-33** | Identity provider, where credentials live, whether the seeded picker survives for grading, and what happens to the `/student/<id>` URL pattern | **AR16** outright; `Architecture.md` §2 and §9 row 1; the identity-not-security reading of **D-20** recorded inline in `schema.sql`. **Not** FR33, which already reads "signs in" | Stories 1.5, 1.6, 1.7 — and therefore 7.6 |

**This is not a developer's call and it is not decided here.** Jaxon records the entry in the
running log §6; until then the stories carry the gap. Four of the five sprint stories are gated
on it.

Two smaller consequences worth taking with the decisions:

- **The PRD owes one FR.** No FR covers a credential; FR33 covers the role split. By the PRD's
  own evidence rule, a requirement with no ID is an opinion — so the feature needs an FR carrying
  its new decision ID once it is recorded.
- **`UX Design.md` §6 already calls the role picker "Temporary"**, and `Architecture.md` §7 lists
  "Real role-based sign-in" under *Not yet built* while `epics.md` Story 1.1 treats the picker as
  satisfying FR33. The two documents disagree today; D-33 is what settles them.

## Scope

**In.** Five stories, two epics touched.

| Story | Size | Lane | Status |
|---|---|---|---|
| 1.5 Sign in with a credential | L | A | Blocked on D-33 |
| 1.6 Scope every student view to the signed-in user | M | A | Blocked via 1.5 |
| 1.7 Sign out and end the session | S | A | Blocked via 1.5 |
| 7.6 Find an advisee by name | M | B | Startable with a caveat — see below |
| 7.7 See what each advisee is working on | S | B | **Ready for dev.** No dependency on sign-in |

Roll-up: 1 L, 2 M, 2 S. One of five is ready for development today.

**Out, and deliberately.** Everything in Epics 2–6 keeps the status recorded in
`sprint-status.yaml`. In particular the four highest-value unbuilt items — 1.4 rule provenance,
7.3 the proposed-term review, 7.5 the gap warning and Epic 6's seminar themes — are *not* in this
sprint, even though 7.3 and 7.5 are closer to the product's stated purpose than a login page is.
That is the owner's prioritisation, recorded rather than argued with.

**Also out: the ten partial stories.** The revalidation found ten stories where the capability
exists but a named criterion does not hold. None is in this sprint. Two of them are correctness
defects rather than polish and should be read before the next sprint is planned:

- **3.3** — `rank.py` credits a section twice when it carries two buckets of the same requirement
  (Humanities and Literature, both in `CORE_HUM`). This is **AR12** / **NFR8** on the scoring
  side rather than the hours side.
- **5.1** — `ingest.GENERIC_DESC_PATTERNS` cannot match "vary", so 14 of 259 special-topics
  courses are ranked on phrase relevance they do not have (**AR18**, a known open defect).

## Sequence

```
Lane A   D-33 recorded -> 1.5 Sign in -> 1.6 Ownership check -> 1.7 Sign out
Lane B   7.7 Depth study + recent phrases on the advisee row -> 7.6 Search the advisee set
```

Lane B is the only lane that can start. Two notes on it:

1. **7.7 first, not 7.6.** The depth-study label and the recent phrases exist today in
   `student.depth_study_label` and `search_request.phrase`, and neither reaches the advisor
   screen. Putting them on the existing advisee row delivers half of feature 2 with no dependency
   on any decision, and it builds the row component that 7.6 then reuses.
2. **7.6 can be built before Lane A, at a stated cost.** Scoped to the advisor id in the route —
   which is what the application does today — the search works, but its third and fourth
   acceptance criteria (a non-advisee must not appear, and nothing may reveal that they exist)
   cannot be met without a session. Starting 7.6 early means leaving those two criteria
   explicitly open, not ticked. Lane A then closes them.

## Risks

| Risk | Why it is real here | Handling |
|---|---|---|
| **The sprint cannot start.** Four of five stories are decision-gated | This is the plan's main finding, not a hedge | The first deliverable of the sprint is the two decision records, from the owner. Lane B proceeds meanwhile |
| **A concurrent rewrite owns the same files** | Uncommitted work against `docs/specs/tech-spec-relevance-requirement-separation.md` is rewriting `rank.py`, `app.py`, `db.py`, `rank_llm.py` and `schema.sql`, and `templates/results.html` has not yet been updated to its new `groups` shape. Sprint 1 touches `app.py` routes and the templates | Land that work and re-read Stories 3.2, 3.3, 3.5, 4.2, 4.4 and 8.6 before starting Lane A. Do not branch sprint-1 route work off the current working tree |
| **Sign-in makes the database a secret-bearing file** | `Architecture.md` §2 sells SQLite as "survives being emailed", and a local credential store ends that. Also **AR1**: Flask is the only hard dependency | One of the questions inside D-33. If SSO is chosen it does not arise |
| **FERPA is still unresolved** | **NFR11**. Today `/student/<id>` exposes any student's completed coursework to anyone who can type a number — the sprint improves this, it does not close the open item | Story 1.6 is the mitigation. The import-path question stays open |
| **AR15 limits what sign-in can even be** | No deployment; localhost:5000. A university SSO redirect cannot complete against it without a registered client | Sizing of 1.5 is L, M or S depending on the answer, so the sprint's total size is not known until D-33 is recorded |
| **`numeric_progress` overstates progress, on screen, today** | The dropped indicator was the new surface, not the defect. `NC_DEPTH` sums every credit a student holds against 33 hours, so the "Hours totals" panel in `results.html` already renders `159/33` for the seeded senior. Four of four numeric requirements read over 100% for that student and two are not flagged approximate | Not in this sprint. Routed to the cleanup pass with the rest of the revalidation findings |

## Definition of done for this sprint

- Proposed D-33 is recorded in the running log §6, with the option chosen and the reversal
  stated — or the matching stories are formally carried to the next sprint, unstarted.
- Every story that ships meets every acceptance criterion in its `epics.md` section, or the
  unmet ones are written into the status table as unmet. A criterion is not quietly dropped.
- `sprint-status.yaml` matches the code. The November 11 revalidation is the precedent: a status
  is a claim about source, and it carries the file and symbol it was read from.
- `Architecture.md` §2, §7 and §9 and `README.md`'s "Not built" list are updated the moment
  sign-in lands. All three currently assert that the product authenticates nobody.
- If a new FR is added to the PRD for either feature, it carries its decision ID.
