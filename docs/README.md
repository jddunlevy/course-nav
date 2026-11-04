# Planning documents

The documents behind the application. Read them in this order.

| File | What it answers |
|---|---|
| [`PRD.md`](PRD.md) | What the product must do. 34 functional and 19 non-functional requirements, each carrying a finding, assumption or decision ID. §9 lists every point where SOW v2.0 went stale |
| [`Architecture.md`](Architecture.md) | How it is built. Stack, data model, the two-stage ranker, cross-cutting concerns. §7 is **"Not yet built"** — the honest list |
| [`data-model.md`](data-model.md) | The 14 tables as an ER diagram, generated from `schema.sql` and verified against the live database |
| [`UX Design.md`](UX%20Design.md) | 36 UX requirements and 15 named components, grounded in the screenshots in `../ux/` |
| [`archive/`](archive/) | BMAD's epic and story run — 8 epics, 32 stories, pre-sized. **Not voted by the team.** Kept as evidence for the BMAD Decision Log deliverable, not used as the backlog |

## What governs what

These documents are downstream of the elicitation record, not sources in their own right. Where
they disagree with the running log's decisions, the log wins — see
[the README](../README.md#source-of-truth).

Of the three decisions the README flags as proposed: D-29 and D-32 put rule provenance on screen,
and D-31 puts seminar themes in v1.

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
