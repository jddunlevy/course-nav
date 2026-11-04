# Course Navigator

Prototype for MIS 430. A web tool for New College students with self-designed majors, and
their advisors. Given a student's outstanding requirements and a free-text interest phrase, it
ranks **this term's actually-offered sections**. Sections that close a requirement *and* fit
the phrase rank first.

## Setup

Clone to running in about a minute. No external data source, no network, no API key.

```
pip install -r requirements.txt

python ingest.py --reset          # build navigator.db from data/spring2027.csv
python descriptions.py --from-csv # load the description cache from data/
python seed.py                    # demo advisor + 3 students (D-24)
python app.py                     # http://127.0.0.1:5000
python test_rank_llm.py           # 15 assertions, no API key needed
```

`navigator.db` is **not** in the repository — it is derived, 4 MB, and rebuilt by the first three
commands. The inputs it is built from *are* in the repository, under `data/`.

To refresh the catalog from Banner instead of the shipped copy you need the scraper, which is a
separate project (`ua_classes.py`): `python ingest.py --csv <new>.csv --term <term> --reset`, then
`python descriptions.py --term <term>` to crawl descriptions (~25 min, resumable). Neither is
needed to run or demo what is here.

Optional LLM reranking needs a credential:

```
pip install "anthropic>=1.0"
Set-Content -Encoding utf8 .env 'ANTHROPIC_API_KEY=sk-ant-...'
```

`NAVIGATOR_RANKER` = `auto` (default) · `llm` · `tfidf`. Any failure falls back to
deterministic ranking, so a graded demo cannot break. Full detail in
[`docs/Architecture.md`](docs/Architecture.md) §6.

## Where everything lives

| Path | What |
|---|---|
| `*.py`, `schema.sql`, `templates/` | The application |
| `data/` | The inputs the database is built from — the Banner section CSV and the description cache |
| [`docs/`](docs/) | Planning artifacts — PRD, Architecture, data model, UX Design |
| [`reference/`](reference/) | Source documents the requirement rules derive from, archived |
| `course-docs/` | MIS 430 assignment PDFs |
| `ux/` | Reference screenshots — Banner and DegreeWorks, the current-state systems |

### Planning artifacts

| File | What |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | 34 functional and 19 non-functional requirements, each carrying a finding or decision ID. §9 lists every point where SOW v2.0 is stale |
| [`docs/Architecture.md`](docs/Architecture.md) | Stack, data model, the two-stage ranker, and §7 "Not yet built" |
| [`docs/data-model.md`](docs/data-model.md) | The 14 tables as an ER diagram, generated from `schema.sql` and verified against the live database |
| [`docs/UX Design.md`](docs/UX%20Design.md) | 36 UX requirements and 15 named components, grounded in the `ux/` screenshots |
| [`docs/archive/`](docs/archive/) | BMAD's epic/story run — 8 epics, 32 stories, pre-sized. **Not voted by the team.** Kept as evidence for deliverable #9 (BMAD Decision Log), not used as the backlog |

### Reference

| File | What |
|---|---|
| [`reference/new-college-requirements.md`](reference/new-college-requirements.md) | **Start here for the rules.** Every degree requirement stated once, with its source and revision date. Conflicts flagged, not averaged |
| [`reference/nc-website-audit.md`](reference/nc-website-audit.md) | Why that file is needed: the official sources disagree with each other. Evidence behind D-29 → D-32 and Q-27 → Q-31 |
| `reference/nc-seminar-themes-202710.csv` | CC/ESC/SPSC per NEW course — 15 seminars, 12 tagged, 3 unknown. Banner has no theme attribute |
| `reference/*.pdf` | Both live Pre-Advising Checklists (Nov 2025 and the superseded Sept 2019), the Spring 2027 course booklet, the Third Year Review form |

## Source of truth

The elicitation running log governs. Section 6 holds decisions **D-01 → D-32**, and they override
the ERD, the process models and the SOW wherever those disagree.

> The log is **not in this repository.** It lives in the project vault on Jaxon's machine, at
> `MIS 430\final-project\elicitation\findings - running log.md`, along with the SOW versions and
> the weekly status reports. Ask him for a copy — the decision IDs cited throughout these
> documents (D-nn, F-nn, A-nn, Q-nn) all resolve there.

Living project documents — the running log, the SOW, weekly status reports — stay in the vault
so there is exactly one copy of each. Only read-only source material is duplicated into this
repository, so the build does not depend on a website that changes underneath it.

**D-29 → D-32 are proposed, not yet accepted by the team.** They are written into the planning
documents as though they hold. If D-31 is rejected, Epic 6 and three stories go with it.

## Data sources

| Source | What |
|---|---|
| `data/spring2027.csv` | 9,621 sections, 3,324 courses, term 202710. **In this repo** |
| `data/course-descriptions.csv` | 3,172 cached course descriptions. **In this repo** |
| `ua_classes.py` | Banner 9 JSON scraper, no login. A separate project, not in this repo — only needed to pull a *new* term |
| Banner `getCourseDescription` | Where the descriptions came from; ~5% of courses have no record |
| `reference/nc-seminar-themes-202710.csv` | Seminar themes, extracted from the term booklet |

## Not built

Auth provider, deployment, `prerequisite` and `instructor` as entities, and any approval
workflow (D-26). Seminar themes are **specified but not implemented** — D-31 partly reversed
D-23 once the term booklet turned out to carry the theme data Banner lacks.

Open questions, known defects and the full "not yet built" list are in
[`docs/Architecture.md`](docs/Architecture.md) §7 and §9.
