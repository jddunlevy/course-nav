---
type: evidence
class: MIS 430
title: New College Web Sources — Consistency Audit
date: 2026-11-02
method: Documentary audit, not participant data (see Q-26)
scope: newcollege.ua.edu (33 pages, complete) + catalog.ua.edu + 3 linked PDFs + a DegreeWorks audit
revised: 2026-11-02 — §2 corrected after the DegreeWorks audit; §2a and §5a added
---
# New College Web Sources — Consistency Audit

## Why this exists

The running log records that students prefer unofficial web resources — department sites,
review sites, forums — over official ones (**F-18**, S-01). **Q-13** asks why, and is open.
No participant has said the official sources are hard to use, so this audit does not claim
they did.

What it does establish is a *mechanism* that would produce F-18 without a student ever being
able to articulate it: **the official sources disagree with each other**, and a student has no
way to tell which one is current. That is consistent with **F-28** (students simultaneously
believe they know what is available and that they are missing things) and with **A-10**
(students cannot reliably tell they have this problem).

This is documentary measurement, not participant behaviour. Per the Findings-register rule it
gets no F-number; it is cited as a source. It is the second body of evidence of this kind
after `spring2027.csv`, which strengthens the case in **Q-26** for a Data register.

## Method

The site is WordPress with an open REST API. All 33 published pages were enumerated via
`/wp-json/wp/v2/pages` rather than sampled by crawling, so the coverage is complete rather
than representative. Linked PDFs were downloaded and their text extracted. Catalog pages were
fetched from `catalog.ua.edu`. Every row below is reproducible from the archived copies in
this folder.

## Authority order — settled as D-30

1. **DegreeWorks, scoped to the student's catalog year** — the system that actually gates
   graduation, and the only source that knows which catalog year applies to a given student
2. **UA Undergraduate Catalog** — the formal published statement, versioned by catalog year
3. **Pre-Advising Checklist, rev. Nov 2025** — New College's operational form
4. **New College website and term course booklet** — advisory, and un-versioned

Earlier drafts of this audit put the UA Catalog first and treated anything disagreeing with it
as stale. The DegreeWorks audit in §2a and §5a changed that: DegreeWorks states a depth-study
range neither New College document mentions, and it is what blocks a graduation application.
Consistent with **D-13** — mirror DegreeWorks, do not replace it.

The ordering still needs an advisor's confirmation of their *own* practice (**Q-27**). It
matters because the audit's central finding is that sources lower in this order contradict
sources higher in it, and the ordering is what makes that a defect rather than a difference of
opinion.

---

## 1. Two Pre-Advising Checklists are live, one line apart

`/resources-for-students/` links both, under "Advising & Registration", with no dates shown:

| Link label | File | Actual revision date |
|---|---|---|
| PRE-Advising Checklist- new catalog | `…/2026/02/PRE-Advising-Checklist-new-catalog.pdf` | **Nov 2025** |
| PRE-Advising Checklist (PDF) | `…/2025/08/PRE-Advising-Checklist-Fillable.pdf` | **Sept 2019** |

Both return HTTP 200. The revision date is inside each PDF, not on the page. The second label
is the more generic of the two and reads as the default.

The two documents state **materially different graduation requirements**:

| Requirement | Nov 2025 (current) | Sept 2019 (still linked) |
|---|---|---|
| Intro seminar | NEW 200 (Idea Lab) | NEW 100 (Intro to Interdisciplinary Studies) |
| 200-level seminars | one | **two, from different themes** |
| Humanities | **9 hrs** Hum / Lit / Fine Arts / World Language, ≥1 Literature | **12 hrs** Hum / Fine Arts / Lit, ≥1 in *each* category |
| History & Social | **9 hrs**, ≥1 History | **12 hrs** Social & Behavioral, ≥1 HI *and* ≥1 SB |
| Course sequence | — | **HI or LIT two-course sequence required** |
| Writing | **3-hour** W class | **6-hour** writing requirement |
| US & Global Citizenship | 3-hour USGC class | **not mentioned** |
| Legends / Compass | listed | not listed |

A student who opens the second link plans for 24 hours of gen ed instead of 18, chases a
sequence requirement that no longer exists, and takes a course — NEW 100 — that is **no longer
offered** (confirmed in the Spring 2027 booklet, which says so explicitly).

This is the direct mechanism behind **F-12**: becoming aware of a relevant course too late, or
in this case, spending hours against requirements that are not the real ones.

## 2. The website's own degree page contradicts the catalog

`/degree-program/` is the page a student lands on for degree requirements. Checked against
`catalog.ua.edu/undergraduate/arts-sciences/new-college/interdisciplinary-studies-ba/`:

| Claim on `/degree-program/` | UA Catalog (2026–27) says | Verdict |
|---|---|---|
| "NEW 100 (Introduction to Interdisciplinary and Integrative Studies)" | NEW **200** Idea Lab | **Un-versioned, not wrong** — see the correction below |
| "two lower-division seminars (200-level), two upper-division, and one more from either level" | "one lower-level seminar, two upper-level seminars, and a fourth seminar from any level", in addition to NEW 200 | Matches the pre-2025 rule; no catalog year stated |
| "a depth study (33-39 hours)" | "at least 33 hours" — no ceiling stated | **Third of four figures** — see §2a |
| "No more than 30 hours can come from one department" | not stated in the catalog or either checklist | **Unsourced** |
| — | "A minimum grade of **C-** is required for each integrative seminar" | **Missing** from the website and both checklists |
| — | "No more than 20 hours from NEW 490 classes" (checklist) | **Missing** from the website and the catalog |

> **Correction, 2026-11-02.** An earlier draft of this audit called the NEW 100 reference an
> error. A DegreeWorks audit for a student on the **2024–2025** catalog lists
> *"Intro to Integrative Studies — Still needed: 1 Class in NEW 100"*. The website's claim is
> therefore **correct for students on a pre-2025-26 catalog** and wrong only for current ones.
> The Spring 2027 booklet says the same thing from the other side: NEW 100 "is not required for
> students enrolled in the 2026-2027 academic catalog."
>
> The defect is real but different, and worse in one respect: **no New College page states which
> catalog year it describes.** A reader cannot tell whether a rule applies to them. Every other
> row in this table is the same defect — the website is not stale so much as un-versioned, and an
> un-versioned rule is unusable by a population spanning four catalog years.
>
> One consequence is sharp. The booklet also says NEW 100 "is no longer being offered." A
> 2024–25 student is therefore required by DegreeWorks to take a course that does not exist, and
> nothing tells them to substitute NEW 200 except a note buried in a term PDF. That is **F-12**
> — becoming aware too late — produced by the documentation itself, and it is precisely the case
> **FR32**'s gap warning exists to catch.

### 2a. Four different depth-study hour figures

| Source | Depth-study hours |
|---|---|
| UA Catalog, 2026–27 | "at least 33" — no ceiling |
| Pre-Advising Checklist, Nov 2025 | "a minimum of 33" |
| NC website `/degree-program/` | **33–39** |
| **DegreeWorks**, catalog year 2024–25 | **"33-57 credits are required"** |

DegreeWorks is the one that gates graduation, and it states a range neither NC document
mentions. **Q-30** is partly answered: a ceiling does exist, it is catalog-year dependent, and
no New College source states it correctly.

DegreeWorks also enforces **"a minimum of 12 Upper-Level credits in residence… in the major"**,
which appears in the UA Catalog and in no New College document at all.

The Nov 2025 checklist and the UA Catalog agree with each other on every point where both
speak. The website matches the older rule set without saying so.

## 3. The current term's own booklet carries the old seminar rule

`NC Spring 2027 Course Booklet (rev. 10-13-26)` — the newest document of the set, for the term
in `navigator.db` — states:

> "Students are required to complete at least **two lower-division seminars** (from different
> thematic designations) and two upper-division seminars"

That is the 2019 rule, contradicting both the catalog and the Nov 2025 checklist. It is then
partly patched by a note two lines later: *"New College students enrolled in the 2026-2027
academic catalog are required to take NEW 200: Idea Lab as one of their five seminars."*

So the seminar requirement is stated **five different ways across five official sources**:

| Source | Rule |
|---|---|
| UA Catalog | NEW 200 + four: one lower, two upper, one any; all three themes |
| Pre-Advising Checklist, Nov 2025 | NEW 200 + four: one 200-level, two 300/400, one any; all three themes |
| NC website `/degree-program/` | five total: two lower, two upper, one either; NEW **100** |
| Spring 2027 Course Booklet | ≥five: two lower from *different themes*, two upper; + NEW 200 note |
| Pre-Advising Checklist, Sept 2019 | two 200-level from different themes, two 300/400, fifth any; NEW **100** |

Two agree. Three do not. All five are reachable in two clicks from the New College homepage.

## 4. "Courses Offered Now" is a PDF, and the seminar page loops back to it

`/degree-program/courses/` is the only page for what is actually offered. For Spring 2027 it
offers one link — a **9-page PDF booklet** — then 25 archived booklets going back to Fall 2015,
then "For descriptions of all available classes, please visit the UA Undergraduate Catalog."

`/degree-program/seminars/` promises "View a list of upcoming and recent seminar courses, with
descriptions" and links **back to the same courses page**. There is no searchable list of
offered New College courses anywhere on the site.

This is consistent with **F-24** (students search the full university catalog, or have no
consistent approach to scope) and **F-32** (the registration dashboard is the single most-relied-on
source). If the program's own site cannot answer "what is offered that counts for X", Banner is
the only remaining option, and Banner does not carry the New College attributes at all — see §5.

## 5. The booklet holds data Banner does not — this partly reverses D-23

**D-23** deferred CC/ESC/SPSC seminar tagging from v1 because Banner has no attribute for it and
NC's list was still being compiled (**F-36**). The first half is confirmed; the second is not.

Queried against `navigator.db` for term 202710: **no NEW course carries any theme attribute.**
Banner has `Special Topics Course`, `Writing`, `PW: Global Engagement`, `Experiential Learning`
and so on — nothing thematic. D-23's premise holds for Banner.

But the booklet prints the theme next to the course title, in the form
`NEW 212: Creativity (FA/HU) (CC)`. Extracted to
[`nc-seminar-themes-202710.csv`](nc-seminar-themes-202710.csv):

- **15** courses count as New College seminars this term
- **12** carry a theme designation — CC, ESC, SPSC, and one dual (`NEW 415` is `SPSC/CC`)
- **3** do not: **NEW 419** Arts Entrepreneurship, **NEW 421** Youth Culture, **NEW 472** Social Change

The list is not "still being compiled" in the sense F-36 implied — it is published every term,
inside a PDF, and thrown away at the end of it. Nothing joins it to Banner.

The three untagged seminars are the seminar-theme analogue of the special-topics problem
(**F-37**, **D-21**, **D-27**): a student can see that NEW 419 is a seminar and cannot tell which
of the three themes it closes. The guardrail D-27 already defines — show it, never hide it,
flag the part that is unknown — applies unchanged.

## 5a. DegreeWorks answers a different question than New College asks

Two observations from a real DegreeWorks audit (catalog year 2024–25) that bear directly on
**D-13** — complement DegreeWorks, do not replace it.

**It tracks seminar levels but not themes.** The Integrative Seminars block enumerates eligible
courses by level — *"1 Class in NEW 211 or 212 or 215 or 216 or 226 or 230 or 237 or 238 or 243
or 273"* for lower-division, a longer list for upper. Nowhere does it mention CC, ESC or SPSC.
So the level distribution is tracked by a real system and the **theme coverage is not tracked
anywhere** — it lives only in the term booklet (§5) and in the advisor's head. That is the
precise gap **D-31** fills, and it is a narrower and better-evidenced claim than "DegreeWorks
doesn't handle New College."

**The gen-ed block is not the New College one.** The audit's general-education section is
headed *"General Education - Commerce & Business Admin"*, and under "Foreign Language or
Computer Requirements" it is satisfied by **CS 104**. The Sept 2019 New College checklist states
the opposite in as many words: ASL counts for New College, *"but CS courses **will not**."*

A student can therefore see a green check against a language requirement that New College will
not accept. This is **F-12** again — a requirement believed closed that is not — and it is the
strongest single argument for the product: DegreeWorks reports progress against *a* rule set,
and which rule set depends on a block header the student is unlikely to read.

*Caveat:* one audit, one student. Whether every New College student's gen-ed block is run
against a non-NC rule set is unknown and worth asking (**Q-31**).

## 6. Two pages are published that should not be

- `/resource-cards/` — placeholder content, live: *"heading / option for plain text or list /
  one / two / three"*, twice.
- `/degree-program/why-new-college-2/` — titled **"Why New College? DRAFT"**, published
  alongside the real `/degree-program/why-new-college/`.

Neither is in the navigation, but both return HTTP 200 and are indexable. Minor next to §1–§3,
and the same root cause: nothing retires old material.

## 7. What this does and does not support

**Supports**
- **F-18** gains a mechanism. Unofficial sources are not obviously worse than official ones
  when the official ones contradict each other and carry no dates.
- **Q-13** gains a candidate answer, to be tested with S-01 rather than assumed.
- **SOW §9 R4** ("requirement rules change between catalog years") is not a future risk. It has
  already happened, it is unmanaged, and both rule sets are live. Likelihood should rise.
- **Deliverable #6.** A tool that reads the wrong source silently causes a student to miss a
  graduation requirement. That is the most severe harm in the product and it is now evidenced,
  not hypothetical. The guardrail is to name the source and its revision date on screen.
- **D-19 / D-28.** The requirement stack the schema encodes matches the catalog and the Nov 2025
  checklist. The schema is built on the right sources.

**Does not support**
- Any claim that a participant found the website hard to use. None did. F-18 says where they
  go, not why.
- Any claim about how often students hit the stale checklist. Unmeasured, and unmeasurable from
  outside.
- Treating the catalog as authoritative without an advisor confirming it (**Q-27**).

## 8. Proposed register entries

Not yet written to `findings - running log.md` — these are for the team to accept or reject.
Numbering continues from F-41, D-28, Q-26.

**Findings** — none. No participant behaviour was observed. This is a source, per the rule.

**Decisions**

| ID | Proposed decision | Driver |
|---|---|---|
| D-29 | Every requirement rule in the product names its source document and revision date on screen. The tool is only as current as the document behind it, and the documents disagree. | This audit; SOW R4 |
| D-30 | **DegreeWorks is the authority for degree rules, scoped to the student's catalog year.** It is the system that actually gates graduation and the only source that knows which catalog year applies. The UA Catalog and the Pre-Advising Checklist are reference; the New College website is advisory and un-versioned. Consistent with **D-13** (mirror DegreeWorks, do not replace it) and **D-24**. Still pending Q-27 for the advisor's own view. | This audit; DegreeWorks audit, catalog year 2024–25 |
| D-32 | **Every rule the product states is scoped to a catalog year, and the catalog year is shown.** A rule with no catalog year is not displayable. Follows from D-29 and D-30. | This audit |
| D-31 | **Partly reverses D-23.** Seminar themes ship in v1 for the current term, sourced from the term course booklet, not Banner. Courses the booklet leaves untagged are shown with the D-27 "cannot determine — ask your advisor" flag rather than hidden. | This audit; F-36, D-27 |

**Open questions**

| ID | Question | Ask |
|---|---|---|
| Q-27 | Which source do advisors treat as authoritative when the catalog, the checklist and the website disagree? | I-03 follow-up / Jenna Lewis |
| Q-28 | Who owns the New College website, and what is the process for retiring a superseded form? | NC administration |
| Q-29 | Is the 2019 checklist still linked deliberately — do students on an older catalog year need it? If so, it needs a date and a catalog-year label, not removal. | I-03 follow-up |
| Q-30 | Partly answered — DegreeWorks states **33-57** for catalog year 2024-25, so a ceiling exists and is catalog-year dependent. Where does the website's **39** come from, and the "30 hours from one department" cap? | Advisor / catalog editor |
| Q-31 | Is every New College student's general-education block run against a non-NC rule set? One audit shows a C&BA block accepting CS 104 for language, which the NC checklist says does not count. | Jenna Lewis / advisor |

## 9. Sources

| Source | Retrieved | Archived as |
|---|---|---|
| `newcollege.ua.edu`, all 33 pages via WP REST API | 2026-11-02 | — |
| UA Undergraduate Catalog, Interdisciplinary Studies BA | 2026-11-02 | — |
| Pre-Advising Checklist, rev. Nov 2025 | 2026-11-02 | `PRE-Advising-Checklist-new-catalog.pdf` |
| Pre-Advising Checklist, rev. Sept 2019 | 2026-11-02 | `PRE-Advising-Checklist-Fillable (2025-08, older link).pdf` |
| NC Spring 2027 Course Booklet, rev. 10-13-26 | 2026-11-02 | `NC Spring 2027 Course Booklet (10-13-26).pdf` |
| Third Year Review form, rev. 7/2023 | (already held) | `Third-Year-Review-7.25.2023.pdf` |
| `navigator.db`, term 202710 | 2026-11-02 | attribute query, §5 |
| DegreeWorks audit, catalog year 2024-25 | 2026-11-02 | `ux/Screenshot 2026-11-02 2024{15,27}.png` |
| Banner 9 Browse Classes, Spring 2027 | 2026-11-02 | `ux/Screenshot 2026-11-02 202346.png` |

A note on the referral: the Third Year Review page names **Mrs. Jenna Lewis, 201 Lloyd** as
the person who receives the completed form. That is the referral from I-03, still uncontacted,
and it corroborates **F-39** — the student records person — from a second,
documentary source.
