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

Optional LLM reranking needs a credential:

```
pip install "anthropic>=1.0"
Set-Content -Encoding utf8 .env 'ANTHROPIC_API_KEY=sk-ant-...'
```

`NAVIGATOR_RANKER` = `auto` (default) · `llm` · `tfidf`. Any failure falls back to
deterministic ranking, so a graded demo cannot break. Full detail in
[`docs/Architecture.md`](docs/Architecture.md) §6.

To refresh the catalog from Banner instead of the shipped copy you need the scraper, which is a
separate project (`ua_classes.py`): `python ingest.py --csv <new>.csv --term <term> --reset`, then
`python descriptions.py --term <term>` to crawl descriptions (~25 min, resumable). Neither is
needed to run or demo what is here.

## Where everything lives

| Path | What |
|---|---|
| `*.py`, `schema.sql`, `templates/` | The application |
| `data/` | The inputs the database is built from — the Banner section CSV and the description cache |
| [`docs/`](docs/) | Planning artifacts — PRD, Architecture, data model, UX Design. Start at [`docs/README.md`](docs/README.md) |
| [`reference/`](reference/) | Source documents the requirement rules derive from, archived. **Start here for the rules:** [`new-college-requirements.md`](reference/new-college-requirements.md) |
| `course-docs/` | MIS 430 assignment PDFs |
| `ux/` | Reference screenshots — Banner and DegreeWorks, the current-state systems |

## Source of truth

The elicitation running log governs — Section 6 holds decisions **D-01 → D-32**, and they
override the ERD, the process models and the SOW wherever those disagree. The log is **not in
this repository**; it lives in the project vault on Jaxon's machine, so there is exactly one copy
of it. Every `D-nn`, `F-nn`, `A-nn` and `Q-nn` cited in these documents resolves there — ask him
for a copy. Only read-only source material is duplicated into this repository, so the build does
not depend on a website that changes underneath it.

**D-29 → D-32 are proposed, not yet accepted by the team.** The planning documents are written as
though they hold. If D-31 is rejected, Epic 6 and three stories go with it.

## Not built

Auth provider, deployment, `prerequisite` and `instructor` as entities, and any approval
workflow (D-26). Seminar themes are **specified but not implemented** — D-31 partly reversed
D-23 once the term booklet turned out to carry the theme data Banner lacks.

Open questions, known defects and the full "not yet built" list are in
[`docs/Architecture.md`](docs/Architecture.md) §7 and §9.
