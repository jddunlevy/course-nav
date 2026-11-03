# Course Navigator

Prototype for MIS 430. A web tool for New College students with self-designed
majors, and their advisors. Given a student's outstanding gen-ed requirements
and a free-text interest phrase, it ranks **this term's actually-offered
sections**. Sections that close a requirement *and* fit the phrase rank first.

Project docs, elicitation and diagrams live in the vault at
`C:\dev\jaxon-brain\MIS 430\final-project\`. The elicitation running log
(section 6, decisions D-01 to D-28) is the source of truth and overrides the
ERD, the process models and the SOW wherever they disagree.

## Stack

Python 3 + Flask + SQLite, server-rendered Jinja. No build step, no npm, no auth
provider, no deployment. Ranking is pure-Python TF-IDF, so Flask is the only
dependency.

## Setup

```
pip install -r requirements.txt

python ingest.py --reset              # build navigator.db, load spring 2027
python seed.py                        # demo advisor + 3 students (D-24)
python descriptions.py --term 202710  # cache course descriptions (~25 min)
python app.py                         # http://127.0.0.1:5000
```

`descriptions.py` is resumable and only fetches courses whose description is
still empty, so re-running it retries anything that failed.

## Data

| Source | What |
|---|---|
| `C:\dev\ua-classes\ua_classes.py` | Banner 9 JSON scraper, no login |
| `spring2027.csv` | 9,621 sections, 3,324 unique courses, term 202710 |
| `POST /searchResults/getCourseDescription` | Catalog descriptions, course level |

Descriptions are **course** level, not section level: every AAST 395 section
returns the same blurb. So they are fetched once per subject+number. About 5%
of courses return HTTP 500 from Banner, which appears to mean no description
record exists.

### A note on `&amp;`

Banner returns HTML-escaped text. `&amp;` ends in a semicolon, and the
attribute column is joined with `"; "`, so `PW: Digital Literacy & Pract` used
to split into two bogus attributes. Fixed at source in `ua_classes.py` with
`unesc()`, which also covers `title` (581 affected rows), `building`,
`sectionText` and `instructors`. `ingest.py` still unescapes defensively, since
older CSVs on disk carry the broken values.

## Schema

`schema.sql` plus `reference_data.sql`. Every table names the decision it
implements. Highlights, and how they depart from ERD v1:

**Cut** `topic`, `course_topic`, `career`, `career_topic`,
`search_request.career_id` — a hard-coded taxonomy, which D-22 forbids.
Replaced by `course.description` ranked against a typed phrase.

**Added** `gen_ed_bucket`, `requirement`, `requirement_bucket`,
`offering_attribute`, `completed_course`, `completed_course_bucket`, `advisor`,
`app_user`, `recommendation_bucket`.

**Requirements are a union of buckets, not a hierarchy (D-28).** Verified
against the data: Literature co-tags Humanities 95% of the time and World
Language 93%, but Fine Arts only 10% and History/Social-and-Behavioral 0%.
Modelling nesting would silently drop courses. `requirement_bucket` carries the
checklist's "including at least one Literature / at least one History" clauses
as `is_must_include`.

**Lab is not an attribute.** No Banner attribute anywhere contains "lab". The
2-hour lab rule inside the 8-hour Natural Science requirement is satisfied from
`course_offering.schedule_type` (`Laboratory`, 296 sections).

**`recommendation.offering_id` is NOT NULL.** The handoff asked us to pick
between the ERD ("every recommendation points at a real section") and the
process diagram ("relevant but not offered"). Resolved in favour of the ERD,
which is also what D-16 requires.

**Watch the double count when summing hours.** A course can carry two buckets
belonging to the *same* requirement — SPA 101 is both World Language and
Humanities — so a naive `SUM` over the join counts its credits twice and
overstates progress. `db.outstanding_buckets` sums over `DISTINCT completed_id`.
Getting this wrong marks a requirement satisfied and hides a course the student
still needs, which is the exact failure the tool exists to prevent (F-12).

## Ranking (D-19)

Two independent halves, deliberately not blended:

- `bucket_score` — hours closed against requirements still outstanding. From
  Banner attributes, always reliable. A must-include bucket is weighted higher.
- `relevance_score` — TF-IDF cosine between the phrase and
  title + description + section text.

`score = bucket_score + 2.0 x relevance + 0.75 when both are non-zero`. The
bonus is what makes D-19's "closes a requirement **and** fits the phrase" rank
above either alone. Weights are hand-set in `rank.py`, not learned.

### Stage 2: LLM reranking (optional)

TF-IDF alone ranks mediocrely — it is lexical, so "ancient greece" matches
"Ancient New World Civilization" on the word "ancient" and misses synonyms
entirely. `rank_llm.py` adds a second stage: TF-IDF retrieves the top 80, and
Claude reorders *those* and writes the `reason` line.

```
pip install "anthropic>=1.0"
export ANTHROPIC_API_KEY=...        # or: ant auth login
python app.py
```

| `NAVIGATOR_RANKER` | Behaviour |
|---|---|
| `auto` (default) | Rerank when a credential is present, else TF-IDF |
| `llm` | Force reranking; still falls back if the call fails |
| `tfidf` | Never call the API |

`NAVIGATOR_MODEL` (default `claude-opus-5`) and `NAVIGATOR_EFFORT` (default
`medium`) tune it. Effort is set for latency, not cost — this is an interactive
path. Note `_supports_effort`: Haiku 4.5 and older reject `effort` and adaptive
thinking with a 400, so those parameters are omitted for them.

**The model may only reorder, never invent.** F-26 is the finding that both AI
users were recommended courses that were not offered, and D-16 makes grounding
in the real offered list the differentiator. So Claude is handed real CRNs and
every CRN it returns is checked against that input set; anything else is dropped
(`_validate`), and the UI reports the count. A candidate the model omits is
appended rather than lost. `python test_rank_llm.py` exercises this without
needing a key.

**Only the phrase, the outstanding bucket names, and public catalog text leave
the machine.** No name, no ID, no completed coursework, no grades.

**The fallback is deliberate.** A graded demo must not depend on a network round
trip, so any failure logs and serves the TF-IDF order instead of erroring.

### Special topics (D-21, refined by D-27)

926 sections carry Banner's `Special Topics Course` attribute. The naive move —
flag all of them "cannot determine" — is wrong: all 136 `Legends` sections
carry it and are a known First-Year Compass requirement, and 166 of the 926
carry a real gen-ed bucket too.

So uncertainty attaches to **phrase relevance, not bucket closure**. A course is
`topic_uncertain` only when it has a special-topics section *and* its
description is missing or reads as the generic rotating blurb. Such a section
still ranks on everything it closes, is never hidden, and carries
"cannot determine the topic — ask your advisor" on the relevance half alone.

## Not built, on purpose

Auth provider, deployment, NEW seminar themes (D-23 — Banner has no attribute
and NC's list is still being compiled, F-36), `prerequisite` and `instructor`
as entities, and any approval workflow (D-26).

## Open

- **DegreeWorks import.** Seeded for the prototype. Audit-PDF parse is the
  stated v1 plan; it raises a FERPA question.
- **Depth-study hour rules** (`NC_DEPTH`, `NC_DEPTH_UPPER`) need a per-course
  depth-study flag that v1 does not collect. Shown as approximate.
