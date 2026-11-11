# Planning documents

The documents behind the application. Read them in this order.

| File | What it answers |
|---|---|
| [`PRD.md`](PRD.md) | What the product must do. 34 functional and 19 non-functional requirements, each carrying a finding, assumption or decision ID. §9 lists every point where SOW v2.0 went stale |
| [`Architecture.md`](Architecture.md) | How it is built. Stack, data model, the two-stage ranker, cross-cutting concerns. §7 is **"Not yet built"** — the honest list |
| [`data-model.md`](data-model.md) | The 14 tables as an ER diagram, generated from `schema.sql` and verified against the live database |
| [`UX Design.md`](UX%20Design.md) | 36 UX requirements and 15 named components, grounded in the screenshots in `../ux/` |
| [`epics.md`](epics.md) | **The backlog.** 8 epics, 38 stories, pre-sized, every story carrying an implementation status revalidated against the code. Starts with that status table and with the two decisions sprint 1 is waiting on |
| [`sprint-plan.md`](sprint-plan.md) | Sprint 1: the goal, what is in and out, the sequence, and the decision gate. Five of its six stories cannot start until the owner records a decision |
| [`sprint-status.yaml`](sprint-status.yaml) | The machine-readable status of every epic and story, generated from `epics.md` by `bmad-sprint-planning` |
| [`specs/`](specs/) | Implementation-level tech specs, written per change rather than maintained as a set |

## The backlog, and why it stopped being archived

`epics.md` came out of a BMAD epic-and-story run that **the team never voted on**, and until
November 11, 2026 it sat in `archive/` as evidence for the BMAD Decision Log deliverable rather
than as a backlog. The project owner promoted it that day. Two things changed with the
promotion, and nothing was deleted or reworded:

- Every one of the original 32 stories was revalidated against the code at commit `5fb1330` and
  carries a status — 13 implemented, 10 partial, 9 not started. A status names the file and the
  symbol it was read from, so it can be checked rather than trusted.
- Six stories were added for sprint 1: a credentialed sign-in page, and advisor
  search-by-student. One of the six, a degree-progress indicator, was dropped the same day —
  see below.

The sign-in feature contradicts something already decided, so it is held at a decision the owner
has to record: **proposed D-33** — a sign-in page reverses AR16 and the identity-not-security
reading of D-20. It is not decided in these documents, and is stated in full, with options and
consequences, in `epics.md`.

A second decision, proposed D-34, asked what a single degree-percent-complete figure may claim.
**It was dropped on November 11, 2026 rather than decided.** `db.numeric_progress` computes the
depth-study requirement as every credit the student holds against 33 hours, so it reads 482% for
the seeded senior — four of its four numeric requirements exceed 100% for that student and two of
them are not flagged approximate. There was no honest figure to choose between. The measurement
is kept in `epics.md` because the defect is live in today's UI, where the "Hours totals" panel
renders the same rows, and it is routed to the cleanup pass rather than to sprint 1.

The run that produced the original file is still legible as evidence: its pre-vote story text,
sizes and MoSCoW rankings are untouched, and the frontmatter records both the original BMAD steps
and the revalidation.

## What governs what

These documents are downstream of the elicitation record, not sources in their own right. Where
they disagree with the running log's decisions, the log wins — see
[the README](../README.md#source-of-truth).

Of the three decisions the README flags as proposed: D-29 and D-32 put rule provenance on screen,
and D-31 puts seminar themes in v1.

D-33 is a different kind of proposed. D-29 → D-32 are *in* the running log and not yet accepted
by the team; D-33 is **not in the log at all** — it is the number sprint 1 needs the owner to
write. Until it is written, no document here may be read as having settled it. D-34 was retired
unwritten when the feature it governed was dropped.

Two further numbers are pending from the same day, both in `specs/`: **D-35** (the ranker's
FR11/FR12 amendment) and **D-36** (chat-led query construction). Neither is in the log either.

## The requirement rules themselves

Not here — they live in [`../reference/`](../reference/), alongside the source documents they
derive from.

| File | What |
|---|---|
| [`new-college-requirements.md`](../reference/new-college-requirements.md) | **Start here for the rules.** Every degree requirement stated once, with its source and revision date. Conflicts flagged, not averaged |
| [`nc-website-audit.md`](../reference/nc-website-audit.md) | Why that file has to exist: the official sources contradict each other. Evidence behind D-29 → D-32 and Q-27 → Q-31 |
| `nc-seminar-themes-202710.csv` | CC/ESC/SPSC per NEW course — 15 seminars, 12 tagged, 3 unknown. Banner has no theme attribute |
| `*.pdf` | Both live Pre-Advising Checklists (Nov 2025 and the superseded Sept 2019), the Spring 2027 course booklet, the Third Year Review form |

## Where the data came from

| Source | What |
|---|---|
| `../data/spring2027.csv` | 9,621 sections, 3,324 courses, term 202710. **In this repo** |
| `../data/course-descriptions.csv` | 3,172 cached course descriptions. **In this repo** |
| `ua_classes.py` | Banner 9 JSON scraper, no login. A separate project, not in this repo — only needed to pull a *new* term |
| Banner `getCourseDescription` | Where the descriptions came from; ~5% of courses have no record |
| `../reference/nc-seminar-themes-202710.csv` | Seminar themes, extracted from the term booklet |
