---
stepsCompleted: ['parse-epics', 'generate-sprint-status', 'validate-coverage', 'record-decisions', 'rescope']
revision: 2
revision_note: >
  Revision 2, November 11 2026. The owner answered the decisions this plan was gated on --
  D-33 (sign-in) and D-35 (the ranker's Q-1 and Q-2) -- and deferred D-36. The gate section
  below records what was decided instead of what was pending. Story 1.5 resized L to M. Story
  3.6 added, closing the ranker spec's unlanded Tasks 10-11. Lane B resequenced so 7.7 precedes
  7.6, correcting an inverted dependency in epics.md. The sprint now has six stories and two
  startable today rather than one.
inputDocuments:
  - 'docs/epics.md (the live backlog; 8 epics, 39 stories after Story 3.6)'
  - 'docs/sprint-status.yaml (generated from it; 8 epics, 39 stories, 8 retrospectives)'
  - 'docs/PRD.md, docs/Architecture.md, docs/UX Design.md'
  - 'docs/specs/tech-spec-relevance-requirement-separation.md (revision 3; Tasks 1-9, 12-14 landed)'
  - 'docs/specs/design-chat-led-query-construction.md (D-36, deferred)'
  - 'app.py, db.py, rank.py, rank_llm.py, ingest.py, schema.sql, templates/*.html, static/style.css, test_rank.py, test_rank_llm.py (re-read at commit 56f20b9)'
  - 'navigator.db, rebuilt -- measured for the Q-2 answer and to verify the ranker spec AC 12'
  - 'elicitation/findings - running log.md (source of truth, D-01 to D-32 -- not in this repository)'
workflowType: 'sprint-planning'
authoredBy: 'revision 1 by bmad-sprint-planning, November 11 2026. Revision 2 hand-written the same day after the owner answered D-33 and D-35 -- the workflow was NOT re-run'
---

# Sprint 1 plan - New College Course Navigator

**Owner:** Jaxon
**Date:** November 11, 2026 · **Revision 2**, same day, after the decisions were recorded
**Tracking file:** [`sprint-status.yaml`](sprint-status.yaml) — the machine-readable half of this
plan. Every epic and story in [`epics.md`](epics.md) appears there exactly once.
**Sprint length:** not set here. The class cadence lives in the run sheet under `sprint/`, which
is not in this repository.

## The sprint goal

Two features the project owner asked for, and one repair the sprint cannot honestly ship without:

1. A formal sign-in page, replacing the role picker.
2. On the advisor side, search by student — with each result showing that student's depth study
   or interest.
3. **Make the result page show its results again.** Not a feature request — the ranker
   separation landed its logic and not its template, so a search renders "0 ranked courses"
   above fifty-five that matched. Story 3.6.

A degree-progress indicator was asked for as part of feature 2 and **dropped on November 11,
2026**, the day it was specced: `db.numeric_progress` reads 482% for the seeded senior, so there
was no honest figure to render. The defect it exposed is live in today's UI and is routed to the
cleanup pass. Full record in [`epics.md`](epics.md).

## The gate: opened

Revision 1 of this plan found that four of its five stories were gated on a decision nobody had
made, and said so rather than guessing. **The owner made the decisions on November 11, 2026.**
Full statements in [`epics.md`](epics.md); the operative content:

| ID | Decided | Effect on this sprint |
|---|---|---|
| **D-33** | A **local credential table** — a password hash on `app_user`, verified with stdlib `hashlib.pbkdf2_hmac`. **The picker is removed**, and `seed.py` gives the four seeded users known passwords so the demo signs in like a real user. **`/student/<id>` stays** and gains an ownership check | Unblocks 1.5, 1.6, 1.7 and 7.6's third criterion. **Resizes 1.5 from L to M** |
| **D-35** | The ranker's Q-1 → **badges inside the relevant list, no dual-fit section**. Q-2 → **the 8 uncertain-and-closing rows surface uncollapsed**, D-21 preserved. The requirement-only set is **relabelled a browse list** | Unblocks the ranker spec's Tasks 10–11, which become **Story 3.6** |
| **D-36** | **Deferred** past this sprint. Its own design cycle | Keeps the sprint at two features plus the repair |

**What is still outstanding, and it is not a developer's to close:** the **running-log §6
entries** for D-33 and D-35. The log governs over the PRD and is not in this repository. The
decisions are made and this plan is sized against them, but until the entries exist the IDs are
provisional and the PRD edits below cannot be written.

Three consequences that ride along with the decisions:

- **The PRD owes one FR** for the credential, carrying D-33 — no FR covers a credential, FR33
  covers the role split — and **three amendments** for D-35: FR11's mechanism withdrawn, FR12
  narrowed close to retirement, FR15 strengthened. `bmad-edit-prd` is the tool. Not written yet,
  because the log entries do not exist.
- **`Architecture.md` §2 stops being true when 1.5 lands.** It sells SQLite as "survives being
  emailed"; a credential store ends that. §7, §9 row 1 and `README.md`'s "Not built" list go at
  the same moment — all four are accurate *today*, which is why they are not edited yet.
- **`UX Design.md` §6 already calls the role picker "Temporary"**, and `Architecture.md` §7 lists
  "Real role-based sign-in" under *Not yet built* while `epics.md` Story 1.1 treats the picker as
  satisfying FR33. D-33 settles that disagreement in §7's favour: the picker was never
  authentication.

## Scope

**In.** Six stories, three epics touched.

| Story | Size | Lane | Status |
|---|---|---|---|
| 3.6 Render the result groups | M | **C** | **Ready for dev.** No dependency on anything |
| 7.7 See what each advisee is working on | S | B | **Ready for dev.** No dependency on sign-in |
| 7.6 Find an advisee by name | M | B | Startable; third criterion stays unmet until Lane A — see below |
| 1.5 Sign in with a credential | ~~L~~ **M** | A | Ready for dev once the D-33 log entry exists |
| 1.6 Scope every student view to the signed-in user | M | A | After 1.5 |
| 1.7 Sign out and end the session | S | A | After 1.5 |

Roll-up: **4 M, 2 S — no L.** Two of six are startable today with nothing outstanding, where
revision 1 had one of five. The L disappeared when D-33 chose the local credential table: the
uncertainty that sized 1.5 at L was the unmade decision, not the work, and stdlib hashing means
there is no dependency question either.

**Story 3.6 is new, and it is why the sprint's shape changed.** The ranker separation landed
Tasks 1–9, 12–14 at `065d496` and `434c9cd` — tests passing, database rebuilt, the Critical
`UNIQUE`-constraint defect verified closed — and did **not** land Tasks 10–11. Because Jinja2's
default `Undefined` renders `{{ results|length }}` as `0` instead of raising, the page fails
silently: a search for "climate policy" shows "0 ranked courses" and "Nothing matched" above 55
relevant and 480 requirement-only rows. Tracking it as a story rather than as untracked repair
is what the sprint's own definition of done requires — a status is a claim about source, and the
largest gap between the docs and the code cannot be the one thing left unstated.

**Out, and deliberately.** Everything in Epics 2–6 keeps the status recorded in
`sprint-status.yaml`. In particular the four highest-value unbuilt items — 1.4 rule provenance,
7.3 the proposed-term review, 7.5 the gap warning and Epic 6's seminar themes — are *not* in this
sprint, even though 7.3 and 7.5 are closer to the product's stated purpose than a login page is.
That is the owner's prioritisation, recorded rather than argued with.

**Also out: the partial stories**, now twelve rather than ten after the November 11 re-read.
None but 3.6's targets are in this sprint. Three are correctness defects rather than polish and
should be read before the next sprint is planned:

- **3.3** — `rank.py` credits a section twice when it carries two buckets of the same requirement
  (Humanities and Literature, both in `CORE_HUM`). **Unchanged by the landed work** — the ranker
  spec's tasks never touched it. This is **AR12** / **NFR8** on the scoring side rather than the
  hours side.
- **5.1** — `ingest.GENERIC_DESC_PATTERNS` cannot match "vary", so 14 of 259 special-topics
  courses are ranked on phrase relevance they do not have (**AR18**, a known open defect).
- **`numeric_progress` overstates progress on screen, today.** `NC_DEPTH` sums every credit a
  student holds against 33 hours, so the "Hours totals" panel renders `159/33` for the seeded
  senior. Four of four numeric requirements read over 100% for that student and two are not
  flagged approximate. The dropped indicator was the new surface; this is the defect, and it is
  still live.

Two statuses moved in ways worth naming, because neither is a developer's oversight:

- **3.2 is superseded, not defective.** Its premise — that dual fit should rank above either
  signal alone — was withdrawn by D-35. Its acceptance criteria are unreachable and are not
  carried forward.
- **8.6 regressed by standing still.** The provenance line still renders, and now describes an
  ordering the code stopped performing at `065d496`. Visible provenance that misdescribes the
  mechanism is worse than none; Task 11, inside Story 3.6, is the fix.

## Sequence

```
Lane C   3.6 Render the result groups                            <- start today, nothing outstanding
Lane B   7.7 Depth study + last phrase on the advisee row  ->  7.6 Search the advisee set
Lane A   D-33 log entry -> 1.5 Sign in -> 1.6 Ownership check -> 1.7 Sign out
```

**Lanes B and C start today.** Lane A starts the moment the D-33 running-log entry exists; it is
no longer waiting on a decision, only on its record. Four notes:

1. **3.6 is its own lane because it shares no file with the other two.** It is
   `templates/results.html` and `static/style.css`; Lane A is `app.py` routes plus `base.html`
   and a new sign-in template; Lane B is `advisor.html`. 3.6 and Lane A both touch the result
   page's surroundings, so if they run concurrently, land 3.6 first — it is startable now and
   Lane A is not.
2. **7.7 first, not 7.6.** The depth-study label and the last-searched phrase exist today in
   `student.depth_study_label` and `search_request.phrase`, and neither reaches the advisor
   screen. Putting them on the existing advisee row delivers half of feature 2 with no dependency
   on any decision, and it builds the row component that 7.6 then searches. **`epics.md` had
   this inverted** — Story 7.7 read "Depends on: Story 7.6" — and that line was corrected on
   November 11 2026.
3. **7.6 can be built before Lane A, at a stated cost.** Scoped to the advisor id in the route —
   which is what the application does today — the search works, but its **third** acceptance
   criterion (a non-advisee must not appear, and nothing may reveal that they exist) cannot be
   met without a session. Starting 7.6 early means writing that criterion into the status table
   as **unmet**, not ticking it. Lane A then closes it. *(Revision 1 said "third and fourth"; the
   fourth criterion — the empty state naming the query — needs no session. The third is the only
   one gated.)*
4. **Lane A's internal order is forced.** 1.6 has no identity to check and 1.7 has no session to
   end until 1.5 exists.

## Risks

Revision 1's first risk — "the sprint cannot start" — is **closed**: the decisions were made,
and two lanes are startable today. What replaced it is smaller but real.

| Risk | Why it is real here | Handling |
|---|---|---|
| **The running-log entries never get written** | The decisions are made but the log is the source of truth and is outside this repository. Code built against an unrecorded decision is code built on a conversation | Lane A does not start until the D-33 entry exists. Lanes B and C do not depend on it. This is the sprint's first deliverable and it is the owner's, not a developer's |
| **The result page ships half-fixed** | Story 3.6 carries thirteen acceptance criteria and most of them are copy, not logic: which count is pre-cap, what the browse list may claim, whether the uncertainty callout can say "these". Copy is the easiest thing to wave through in review | Each criterion names the number or the file it is checked against. The ranker spec's AC 1–4, 7 and 11 are the same checks from the other direction |
| ~~A concurrent rewrite owns the same files~~ **Closed.** That work landed at `065d496` and `434c9cd`; the working tree is clean, and Stories 3.1, 3.2, 3.3, 3.5, 4.2, 4.4 and 8.6 were re-read on November 11 against the landed code | What remains of it is the template, now Story 3.6, in this sprint and owned by it | No handling needed. Branch sprint-1 work off `main` |
| **Sign-in makes the database a secret-bearing file** | **Realised, by choice.** D-33 chose the local credential table, so `navigator.db` will hold password hashes and `Architecture.md` §2's "survives being emailed" becomes false | Accepted deliberately: it is the only option demonstrable under AR15. §2 is corrected the moment 1.5 lands. **AR1 is not at risk** — `hashlib.pbkdf2_hmac` is standard library, so `requirements.txt` does not change, and Story 1.5 carries an acceptance criterion asserting that |
| **FERPA is still unresolved** | **NFR11**. Today `/student/<id>` exposes any student's completed coursework to anyone who can type a number — the sprint improves this, it does not close the open item | Story 1.6 is the mitigation. The import-path question stays open |
| ~~AR15 limits what sign-in can even be~~ **Resolved into the decision.** No deployment; localhost:5000, so a university SSO redirect could not complete without a registered client | This is precisely why D-33 chose a local credential table over SSO. 1.5 is sized **M** and the sprint's total size is now known |
| **The debugger would be served beside a login form** | `app.py` runs `app.run(debug=True)`. The Werkzeug debugger executes arbitrary code through the browser | Not a trade-off to weigh — it goes off, and `SECRET_KEY` becomes a new `.env` key under AR14. Both are acceptance criteria on Story 1.5. This was never put to the owner as a choice |
| **`numeric_progress` overstates progress, on screen, today** | The dropped indicator was the new surface, not the defect. `NC_DEPTH` sums every credit a student holds against 33 hours, so the "Hours totals" panel in `results.html` already renders `159/33` for the seeded senior. Four of four numeric requirements read over 100% for that student and two are not flagged approximate | Not in this sprint. Routed to the cleanup pass with the rest of the revalidation findings. **Note for Story 3.6:** it rewrites the result page and will have this panel open in front of it. Resist fixing it there — it is a `db.py` rule defect, not a template one, and folding it in would put an unreviewed hours change inside a rendering story |

## Definition of done for this sprint

- **D-33 and D-35 are recorded in the running log §6**, with the options chosen and the
  reversals stated — or the matching stories are formally carried to the next sprint, unstarted.
  The decisions exist; the records do not. Lane A does not start without D-33's.
- **The result page renders its results.** No reference to `results` survives in
  `templates/results.html`, and the ranker spec's AC 1–4, 7 and 11 pass. This is the one item on
  this list that is true or false by looking at the screen.
- Every story that ships meets every acceptance criterion in its `epics.md` section, or the
  unmet ones are written into the status table as unmet. A criterion is not quietly dropped —
  Story 7.6's third criterion is the known case, and it is expected to ship unmet until Lane A
  closes it.
- `sprint-status.yaml` matches the code. The November 11 revalidation and re-read are the
  precedent: a status is a claim about source, and it carries the file and symbol it was read
  from. **8.6 is the cautionary case** — it was "done" while describing an ordering the code had
  stopped performing.
- `Architecture.md` §2, §7 and §9 and `README.md`'s "Not built" list are updated **the moment
  sign-in lands**, not before. All four currently assert that the product authenticates nobody,
  which is true today. §2's "survives being emailed" is the one that becomes a false security
  claim rather than merely stale.
- `README.md` documents the four seeded logins, since D-33 removed the picker and the graded
  demonstration now signs in.
- The PRD carries a new FR for the credential bearing D-33, and the FR11, FR12 and FR15
  amendments bearing D-35 — once the log entries exist. A requirement with no ID is an opinion.
- `data-model.md` is re-verified **once**, after Story 1.5, rather than twice: `recommendation`
  already gained `result_group` and `app_user` is about to gain a credential column.
