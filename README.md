# Course Navigator

Prototype for MIS 430. A web tool for New College students with self-designed majors, and
their advisors. Given a student's outstanding requirements and a free-text interest phrase, it
ranks **this term's actually-offered sections** — sections that close a requirement *and* fit
the phrase rank first.

## Setup

Clone to running in about a minute. No external data source, no network, no API key.

```
pip install -r requirements.txt

python ingest.py --reset          # build navigator.db from data/spring2027.csv
python descriptions.py --from-csv # load the description cache from data/
python seed.py                    # 2 demo advisors + 5 students (D-24)

# The app refuses to boot on a default session secret (D-33). .env is gitignored.
python -c "import secrets; print('NAVIGATOR_SECRET_KEY=' + secrets.token_hex(32))" >> .env

python app.py                     # http://127.0.0.1:5000, then sign in
```

`navigator.db` is **not** in the repository — it is derived, 4 MB, and rebuilt by the first
three commands. The inputs it is built from *are* in the repository, under `data/`.

Every seeded user shares the password `navigator` — advisors `dwhitfield` and `mbell`,
students `jreyes`, `rdelgado`, `tlindqvist`, `nhaddad` and `praman`. These are published on
purpose: this is a course prototype whose demo has to run from a clean clone. The mechanism is
real; the accounts are not secret.

## Tests

Plain scripts, no pytest, no API key, no network. Each exits 0 and prints one line per
assertion. They need the seeded database.

```
python test_rank.py           #  36  the relevance floor, grouping, orderings
python test_rank_llm.py       #  20  rerank_groups, prompt and validation
python test_result_page.py    #  64  the result page, against Story 3.6's criteria
python test_prereq.py         #  38  the prerequisite screen and its toggle
python test_req_link.py       #  42  the open-requirement link and the ?req= filter
python test_advisor_row.py    #  17  the working depth study on the advisee row
python test_advisor_search.py #  30  advisee name search, scoping and query cost
python test_auth.py           #  61  sign-in, the boot refusal, password storage
python test_scoping.py        #  40  who may see which record
python test_signout.py        #  26  sign-out, and that signed-in pages are no-store
```

374 assertions. The two advisor counts are data-dependent -- both loop over
advisor 1's advisees, so reseeding moves them. Two files guard defect *classes*
rather than features. `test_result_page.py`
re-renders every page under `jinja2.StrictUndefined`, because Jinja's default Undefined
renders `{{ x|length }}` as `0` without raising — which is how the result page reported
"0 ranked courses" above 55 matches for two commits. `test_scoping.py` asserts that a
forbidden record and a nonexistent one return *byte-identical* responses, so the routes cannot
be used to find out which student ids are real.

## Options

Neither is needed to run or demo what is here.

**LLM reranking** needs a credential:

```
pip install "anthropic>=1.0"
Set-Content -Encoding utf8 .env 'ANTHROPIC_API_KEY=sk-ant-...'
```

`NAVIGATOR_RANKER` = `auto` (default) · `llm` · `tfidf`. Any failure falls back to
deterministic ranking, so a graded demo cannot break. Full detail in
[`docs/Architecture.md`](docs/Architecture.md) §6.

**Refreshing the catalog** from Banner instead of the shipped copy needs the scraper, a
separate project (`ua_classes.py`): `python ingest.py --csv <new>.csv --term <term> --reset`,
then `python descriptions.py --term <term>` to crawl descriptions (~25 min, resumable).

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
this repository**; it lives in the project vault on Jaxon's machine, so there is exactly one
copy of it. Every `D-nn`, `F-nn`, `A-nn` and `Q-nn` cited in these documents resolves there —
ask him for a copy. Only read-only source material is duplicated here, so the build does not
depend on a website that changes underneath it.

**D-29 → D-32 are proposed, not yet accepted by the team.** The planning documents are written
as though they hold. If D-31 is rejected, Epic 6 and three stories go with it.

## Status

Sign-in is built (D-33, Story 1.5): a username and password, hashed with the standard
library's PBKDF2-HMAC and a per-user salt, with every route but the sign-in page requiring a
session. Story 1.6 scoped every record route to the signed-in user — a student reaches only
their own record, an advisor only their own advisees, and a refusal is indistinguishable from a
record that does not exist. Story 1.7 added sign-out, and with it `Cache-Control: no-store` on
every signed-in page: on a shared advising-office machine it is the browser cache, not the
session, that hands the next person the previous one's record.

Not built: SSO, password reset, lockout, rate limiting, an auth *provider*, deployment,
`prerequisite` and `instructor` as entities, and any approval workflow (D-26). Seminar themes
are **specified but not implemented** — D-31 partly reversed D-23 once the term booklet turned
out to carry the theme data Banner lacks.

Open questions, known defects and the full "not yet built" list are in
[`docs/Architecture.md`](docs/Architecture.md) §7 and §9.
