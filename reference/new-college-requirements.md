---
type: reference
class: MIS 430
title: New College Degree Requirements — Consolidated
date: 2026-11-02
catalog_year: 2026-2027
authority: DegreeWorks (catalog-year scoped) > UA Undergraduate Catalog > Pre-Advising Checklist (rev. Nov 2025) > NC website  # D-30
status: derived — every row cites its source; conflicts are flagged, not resolved silently
---
# New College Degree Requirements — Consolidated

One place where each rule is stated once, with the document it comes from and that document's
revision date. Built because the official sources disagree — see
[`nc-website-audit.md`](nc-website-audit.md) for what disagrees with what.

**This is derived material.** It is not authoritative and does not replace an advisor. Where
sources conflict, the conflict is shown rather than averaged. Rules marked ⚠ are unresolved.

Sources, in the authority order set by **D-30** (advisor confirmation still pending, **Q-27**):

| Key | Document | Revision | Authority |
|---|---|---|---|
| **DW** | DegreeWorks, scoped to the student's catalog year | live | **1 — gates graduation** |
| **CAT** | UA Undergraduate Catalog, Interdisciplinary Studies BA/BS | 2026-2027 | 2 |
| **PAC** | Pre-Advising Checklist | Nov 2025 | 3 |
| **BK** | NC Spring 2027 Course Booklet | 10-13-26 | 4 — advisory |
| **WEB** | newcollege.ua.edu `/degree-program/` | **undated** | 4 — advisory, un-versioned |
| ~~PAC19~~ | Pre-Advising Checklist — *still linked live, do not use* | Sept 2019 | superseded |

**Rules are catalog-year scoped (D-32).** A rule with no catalog year is not displayable. The
website states no catalog year anywhere, which is why it ranks last rather than merely stale —
see the audit §2.

---

## 1. University totals

| Rule | Value | Source |
|---|---|---|
| Total eligible credit | ≥ 120 hours | CAT, PAC |
| Coursework at 300 level or above | ≥ 36 hours | CAT, PAC |
| Upper-level residency — 300/400 earned on this campus | ≥ 12 hours | CAT only |
| GPA in the major | ≥ 2.0 | CAT only |

The last two appear in no New College document. A student reading only NC material would not
know about either.

## 2. New College totals

| Rule | Value | Source |
|---|---|---|
| Hours completed while enrolled in New College | ≥ 42 | CAT, WEB |
| Minor | not required for depth-study students | CAT |

## 3. Depth study

| Rule | Value | Source |
|---|---|---|
| Minimum hours | ≥ 33 | CAT, PAC, WEB |
| At 300/400 level | ≥ 15 hours | CAT, PAC, WEB |
| Independent study hours countable | ≤ 12 | CAT, PAC |
| Hours from NEW 490 | ≤ 20 | **PAC only** |
| ⚠ Maximum hours | **DW says 33–57** (catalog year 2024-25); WEB says 33–**39**; CAT says "at least 33", no ceiling | conflict — **Q-30**, partly answered: the ceiling is catalog-year dependent |
| ⚠ Hours from one department | WEB says ≤ 30; absent from CAT and PAC | unsourced — **Q-30** |

The depth study is not enumerated in any system. It exists as a title, a proposal paragraph,
and an advisor's judgment (SOW §3). This is why the product proposes and never asserts
(**F-04**, **D-22**).

## 4. New College seminars

**Five seminars total: NEW 200 plus four others.** (CAT, PAC — these two agree.)

| Rule | Value | Source |
|---|---|---|
| NEW 200 Idea Lab | required, counts as one of the five | CAT, PAC, BK |
| Additional seminars | 4 | CAT, PAC |
| At the 200 level | 1 | CAT, PAC |
| At the 300/400 level | 2 | CAT, PAC |
| At any level | 1 | CAT, PAC |
| Themes — CC, ESC, SPSC | ≥ 1 seminar in **each**, by graduation | CAT, PAC, BK, WEB |
| Minimum grade per seminar | **C-** | **CAT only** |
| Transfer credit | not accepted; all five taken through New College | CAT, WEB |

⚠ **WEB and BK both state the superseded rule** ("two lower-division seminars"). WEB also names
**NEW 100**, which is discontinued — the Spring 2027 booklet says so outright. Use CAT/PAC.

### Theme designations, Spring 2027

Banner carries **no** theme attribute; the term booklet is the only source. Extracted to
[`nc-seminar-themes-202710.csv`](nc-seminar-themes-202710.csv).

| Theme | Courses |
|---|---|
| **CC** Creativity and Culture | NEW 212, NEW 213, NEW 415¹ |
| **ESC** Environment, Sustainability, Conservation | NEW 215, NEW 226, NEW 243, NEW 335 |
| **SPSC** Social Problems and Social Change | NEW 237, NEW 238, NEW 390², NEW 415¹, NEW 436, NEW 490² |
| ⚠ **No designation printed** | NEW 419 Arts Entrepreneurship · NEW 421 Youth Culture · NEW 472 Social Change |

¹ NEW 415 is dual-designated `SPSC/CC`. ² Special-topics sections whose actual topic the booklet
names (SLANT; Political Ecology) but Banner does not — see §8.

The three undesignated courses are listed under "New College Seminars" in the booklet, so they
count as seminars, but which theme they close is unstated. Per **D-27** they are shown with the
theme marked unknown and the student referred to their advisor — never hidden, and never
guessed.

## 5. Gen ed and core

Per **PAC** (Nov 2025), which matches what DegreeWorks tracks against. The 2019 checklist states
all of these differently and is wrong — see the audit §1.

| Requirement | Value |
|---|---|
| First-year Legends + College Compass | e.g. NEW 101 |
| First-year Composition | EN 101 / 102 / 103 |
| Mathematics | MATH 110 minimum · **MATH 125 required for BS** |
| Natural Science | 8 hours, **including ≥ 2 hours of lab** |
| Humanities / Literature / Fine Arts / World Language | 9 hours, **including ≥ 1 Literature** |
| History / Social & Behavioral Sciences | 9 hours, **including ≥ 1 History** |
| Writing | one 3-hour **W** course |
| US & Global Citizenship | one 3-hour **USGC** course |
| World Language | see §6 |

**Requirements are a union of buckets, not a hierarchy (D-28).** Measured on `spring2027.csv`
(figures canonical in §11): Literature co-tags Humanities 95% of the time and World Language
93%, but Fine Arts only 10% and History / Social-and-Behavioral 0%. Modelling nesting silently
drops courses. The
"including at least one Literature / one History" clauses are must-include constraints on the
union, carried in `requirement_bucket.is_must_include`.

**Lab is not an attribute.** No Banner attribute anywhere contains "lab". The 2-hour lab rule
is satisfied from `course_offering.schedule_type = 'Laboratory'` (296 sections).

## 6. World language

| Rule | Source |
|---|---|
| 101–102 sequence, or a 103 course, in a qualifying language | CAT, WEB |
| American Sign Language qualifies | WEB; PAC19 adds that CS courses do **not** |
| Or demonstrated proficiency from immersion or equivalent during college | WEB |
| Counts toward the 9-hour Humanities / World Language pool | PAC |

## 7. Third Year Review and senior project

| Rule | Source |
|---|---|
| Required of every student, in the year before graduating | CAT, WEB, BK |
| **Gates enrolment in NEW 495** — no review, no capstone | CAT, WEB, BK |
| Committee: the NC advisor + ≥ 1 outside expert in the depth-study area | WEB, TYR form |
| Documentation circulated to the committee ≥ 5 days prior | TYR form |
| Deadline in practice | ≥ 1 semester before the final semester; **3 semesters** earlier if applying to graduate or professional programs | WEB |
| Completed form goes to **Mrs. Jenna Lewis, 201 Lloyd** | WEB |
| NEW 495 is 2 hours, by permission, and does **not** count as a seminar | BK |

The review is the only point of formal approval for the depth study. Everything before it is
advisor guidance, which is why the product models no approval entity (**D-26**).

## 8. Special topics

Banner tags 926 sections `Special Topics Course`, but the attribute alone does not mean the
topic is unknown: all 136 **Legends** sections carry it and are a known First-Year Compass
requirement, and 166 of the 926 also carry a real gen-ed bucket (**D-27**).

Uncertainty attaches to **phrase relevance, never to requirement closure**. A section's gen-ed
buckets are always trustworthy; only its topic may be unknown.

For New College courses the term booklet resolves it where Banner cannot — Banner's description
for NEW 390 and NEW 490 is the generic rotating blurb, while the booklet names the actual topic:

| Course | Banner title | Banner description | Booklet |
|---|---|---|---|
| NEW 390 | Sp Topics: SLANT Lab | *"Subject matter varies…"* | Special Topics: **SLANT** (SPSC) |
| NEW 490 | Political Ecology | *"Subject matter varies…"* | Special Topics: **Political Ecology** (SPSC) |

> **Open defect, found while building this file.** `ingest.GENERIC_DESC_PATTERNS` does not match
> this blurb. The pattern `\bvaries? (by|with|each) …` expands to "varie" or "varies" and so can
> never match "**vary**", and nothing matches "subject matter varies". 14 of 259 special-topics
> courses are affected: they carry the generic blurb and are **not** flagged `topic_uncertain`,
> so they are ranked on phrase relevance they do not have. Current flag count is 72; it should
> be ~86. Not fixed here — a naive fix would over-flag courses like `NEW 490`, whose *title*
> names the topic even though the description does not. The fix should be title-aware, which is
> a refinement of D-27 and a team decision.

## 9. What no single official source states

Each of these is true and appears in only one place. The point of this file is that a student
cannot assemble the list by reading any one document:

- Upper-level residency, 12 hours on campus — **CAT only**
- 2.0 GPA in the major — **CAT only**
- C- minimum in every seminar — **CAT only**
- ≤ 20 hours from NEW 490 — **PAC only**
- USGC and the 3-hour W course — **PAC only** (absent from CAT's NC pages and from PAC19)
- Seminar theme per course — **BK only**, published per term inside a PDF and never joined to Banner
- NEW 100 is discontinued — **BK only**, while WEB still requires it

## 10. How the product uses this

`schema.sql` + `reference_data.sql` encode §1–§5 as `requirement`, `gen_ed_bucket` and
`requirement_bucket`. The schema follows **CAT** and **PAC**, which the audit confirms are the
correct sources.

Two consequences of this file for the build, both proposed rather than decided:

- **D-29** (proposed) — show the source document and revision date for every rule on screen.
  The tool is exactly as current as the document behind it, and the documents disagree.
- **D-31** (proposed) — ship seminar themes for the current term from the booklet, partly
  reversing **D-23**. Untagged seminars get the D-27 flag.

**Q-25 is now answerable.** Running log §4 omits Legends/Compass, first-year Composition and
MATH 110. All three are in PAC, all three are in §5 above, and the schema already follows the
checklist. §4 of the running log is the document that needs correcting, not the schema.

---

## 11. Catalog measurements — canonical

**This table is the single source for every catalog measurement cited anywhere in the
repository.** Other documents restate individual figures where they are load-bearing; when one
changes, change it here first, then grep for it. All figures measured on `spring2027.csv`
(Banner, term 202710) and `navigator.db` on 2026-11-02.

| Measurement | Value | Used to justify |
|---|---|---|
| Sections / courses in term 202710 | 9,621 / 3,324 | Scale; why browsing the catalog costs hours (F-23, F-24) |
| Distinct Banner section attributes | 26 | Why only 12 are allowlisted (**D-28**) |
| Literature co-tags Humanities | **95%** | Requirements are a union, not a hierarchy (**D-28**) |
| Literature co-tags World Language | 93% | ditto |
| Literature co-tags Fine Arts | **10%** | ditto — nesting would drop 90% |
| Literature co-tags History / Social-Behavioral | **0%** | ditto — nesting would drop all of them |
| Sections with `schedule_type = Laboratory` | 296 | Lab is not an attribute; the 2-hour rule comes from schedule type |
| Sections carrying `Special Topics Course` | 926 | Why the attribute alone cannot mean "topic unknown" (**D-27**) |
| Courses carrying it | 259 | ditto |
| …of those 926, carrying a real gen-ed bucket | 166 | ditto |
| `Legends` sections carrying it | **136** (0 flagged) | A known First-Year Compass requirement; flagging all 926 would be wrong |
| Courses currently flagged `topic_uncertain` | 72 | Should be ~86 — see the open defect below |
| Special-topics courses under-flagged by the regex gap | **14 of 259** | `varies?` cannot match "vary"; fix must be title-aware |
| Course descriptions cached | 3,172 | ~5% of courses return HTTP 500, meaning no record exists |
| Rows corrupted by the HTML-entity bug, attributes | 220 | Unescape before splitting on `"; "` |
| Rows corrupted, titles | **581** | ditto — the larger and less obvious half |
| NEW courses counting as seminars, Spring 2027 | 15 | **D-31** |
| …with a published theme | 12 | ditto |
| …with no published theme | 3 | NEW 419, NEW 421, NEW 472 — shown with the D-27 flag |

Per the Findings-register rule these are **not** participant behaviour and carry no F-numbers.
They are cited as a source, which is the second body of evidence of this kind after the web
audit and the reason **Q-26** proposes a Data register.
