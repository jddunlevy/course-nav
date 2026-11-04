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

Three decisions these documents assume are **proposed and not yet accepted by the team**: D-29
and D-32 (rule provenance on screen) and D-31 (seminar themes in v1). If D-31 is rejected, Epic 6
and three stories go with it.

## For the requirement rules themselves

Not here — [`../reference/new-college-requirements.md`](../reference/new-college-requirements.md).
Every degree requirement stated once with its source and revision date, conflicts flagged rather
than averaged. [`../reference/nc-website-audit.md`](../reference/nc-website-audit.md) is why that
file has to exist: the official sources contradict each other.
