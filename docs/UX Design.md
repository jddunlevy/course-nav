---
stepsCompleted: []
inputDocuments:
  - 'docs/PRD.md'
  - 'docs/Architecture.md'
  - 'ux/Screenshot 2026-11-02 202346.png — Banner 9 Browse Classes, Spring 2027'
  - 'ux/Screenshot 2026-11-02 202415.png — DegreeWorks, Interdisciplinary Studies BS block'
  - 'ux/Screenshot 2026-11-02 202427.png — DegreeWorks, General Education block'
  - 'reference/nc-website-audit.md'
workflowType: 'ux-design'
authoredBy: 'hand-written as a BMAD input — see BMAD Decision Log #5'
---

# UX Design Specification - New College Course Navigator

**Author:** Jaxon
**Date:** November 2, 2026

> The extractable requirement list is **§10**. Sections 1–9 are the reasoning behind it.
> Colour and contrast values in §4 were sampled from the reference screenshots, not chosen.

---

## 1. What the reference images are

The three references are **current-state systems**, not target designs. They are what a New
College student uses today, and the design direction is to read as a sibling of them rather
than as a replacement for them (**D-13**: mirror DegreeWorks, do not replace it).

| Reference | System | What it does well | What it fails at |
|---|---|---|---|
| `…202346.png` | Banner 9, Browse Classes | Compact meeting-pattern widget; seat counts; honest "FULL" state | Every informative column truncated; 93 rows for one subject; **no requirement context at all** |
| `…202415.png` | DegreeWorks, major block | Requirement framing; status per line; "Still needed:" phrasing; catalog year shown | Enumerates courses by number with no titles; no themes; no indication of what is *offered* |
| `…202427.png` | DegreeWorks, gen-ed block | Clear completion states; "Satisfied by:" provenance rows | Block is "Commerce & Business Admin", not New College — see §2 |

### The gap the product fills, stated visually

DegreeWorks shows **requirements without offerings**. Banner shows **offerings without
requirements**. Neither shows the join, which is the product (**F-15**, **D-02**). The Navigator's
single novel screen element is a course result that carries its requirement meaning on its face.

## 2. Two findings from the references that constrain the design

**Catalog year is a first-class attribute, not metadata.** The DegreeWorks header reads
*"Catalog year: 2024-2025"*, and under it *"Still needed: 1 Class in NEW 100"* — a course the
Spring 2027 booklet says is no longer offered. Rules differ by catalog year and no New College
page says which year it describes. Per **D-29** and **D-32** the Navigator must show the catalog
year and the source document wherever it states a rule. This is a UI requirement, not a
footnote.

**A green check can be wrong.** The gen-ed block is headed *"General Education - Commerce &
Business Admin"* and shows the language requirement satisfied by **CS 104**, which the New
College checklist says explicitly does not count for New College. A completion indicator is
therefore scoped to a rule set, and showing one without naming its rule set is how a student
comes to believe a requirement is closed when it is not (**F-12**). Every status indicator in
this product carries its scope.

## 3. Design principles

1. **Inherit the vocabulary.** Students already read DegreeWorks' status circles, card blocks
   and "Still needed:" phrasing. Reusing them costs nothing and buys comprehension.
2. **Never encode meaning in colour alone.** DegreeWorks does — green, blue and red circles.
   Every state here carries a shape or a word as well (**§8**).
3. **Truncation is a defect, not a layout strategy.** Banner truncates the Attribute column,
   which is exactly the field this product exists to surface.
4. **Show the unknown; never hide it and never guess.** **D-21**, **D-27**, **D-31**.
5. **Inform the search, do not replace it.** Browsing stays available and pleasant (**D-04**,
   **F-01**, **F-02**).
6. **Never pitch on frustration.** The interface cannot assume the user believes they have the
   problem (**D-14**, **A-10**). No "stop wasting hours" copy.

## 4. Visual foundation

### Colour tokens

Sampled from the references with Pillow. Contrast ratios computed against WCAG 2.1.

| Token | Value | Source | On white |
|---|---|---|---|
| `--crimson` | `#872835` | DegreeWorks header, sampled | **8.80:1** |
| `--crimson-deep` | `#6B1F10` | derived, for hover/active | 11.48:1 |
| `--ink` | `#2A2F3F` | Banner day-box navy, sampled | 13.32:1 |
| `--surface` | `#FFFFFF` | both | — |
| `--page` | `#FAFAFA` | DegreeWorks page ground, sampled | — |
| `--rule` | `#E3E3E6` | derived, row separators | — |
| `--ok` | `#1E7A3C` | **chosen, not inherited** — see note | 5.14:1 |
| `--progress` | `#1B5E9E` | chosen | 5.72:1 |
| `--open` | `#9A2B2B` | chosen | 7.26:1 |
| `--unknown` | `#6B5E3A` | chosen, for the D-27 flag | 6.08:1 |

> **One thing deliberately not inherited.** Banner's "Search Again" button is `#638D4F` at
> **3.85:1** on white, which fails WCAG AA for normal text. `--ok` is a darker green chosen to
> pass. Inherit Banner's layout, not its contrast.

Banner's own brick `#7A170E` is *not* adopted. Two different institutional reds on one campus
is Banner's problem; the Navigator follows DegreeWorks, which is the system it complements.

### Type and space

A system sans stack (`-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif`), matching
both references. Scale: 12 / 14 / 16 / 20 / 28 px, with 16px as body. Spacing on a 4px grid:
4 / 8 / 12 / 16 / 24 / 32. Cards: 8px radius, 1px `--rule` border, no drop shadow — DegreeWorks'
shadow adds nothing at this density.

## 5. Component inventory — 15 components

Each is named, and each is specified tightly enough to write acceptance criteria against.

| # | Component | Purpose | States |
|---|---|---|---|
| 1 | `AppHeader` | Crimson bar: product name, current role, student name, term | student / advisor / advisor-acting-for-student |
| 2 | `StatusCircle` | Requirement completion, mirroring DegreeWorks | complete / in-progress / not-started |
| 3 | `StatusChip` | Block-level status beside a heading | COMPLETE / IN-PROGRESS / INCOMPLETE |
| 4 | `RequirementCard` | One outstanding requirement: name, hours applied/required, must-include constraints | satisfied / partial / open / **no offering closes it** |
| 5 | `RequirementBadge` | One bucket a course would close, shown on a result | ordinary / must-include (emphasised) |
| 6 | `SourceNote` | "Pre-Advising Checklist, rev. Nov 2025 · catalog year 2024–25" | — |
| 7 | `PhraseInput` | Free-text interest phrase + recent phrases | empty / filled / no-match |
| 8 | `CourseResultCard` | A ranked offering with its requirement meaning | ranked / topic-uncertain / full |
| 9 | `MeetingPattern` | SMTWTFS day boxes + time, borrowed from Banner | scheduled / TBA / online |
| 10 | `SeatCounter` | "17 of 20" or "FULL" | open / full |
| 11 | `UncertaintyFlag` | "Cannot determine the topic — ask your advisor" | topic unknown / theme unknown |
| 12 | `RankProvenance` | How results were ordered, and how many were discarded | deterministic / reranked / fell back |
| 13 | `GapWarning` | Nothing offered closes this requirement | — |
| 14 | `EmptyState` | Phrase matched nothing; no advisees; no outstanding requirements | three variants |
| 15 | `AdviseeRow` | One student in the advisor list, with open-requirement count | — |

### The two that carry the product

**`CourseResultCard`** is the only element with no equivalent in either reference system. It
must show, without truncation: subject and number, full title, credits, every
`RequirementBadge` it closes, the one-line reason it matched the phrase, `MeetingPattern`,
`SeatCounter`, and "+N more sections" when deduplicated (**FR13**). A card that closes a
must-include bucket says which: "closes your **Literature** requirement", not "Humanities".

**`RankProvenance`** is how the grounding guarantee becomes visible. It states whether the
order is deterministic or reranked, and the count of candidates discarded by validation
(**FR18**). A user who cannot see that the system checked has no reason to trust that it did.

## 6. Screens

| Screen | Route | Composition |
|---|---|---|
| Role picker | `/` | List of `app_user` rows. Temporary — there is no auth (**Architecture §9**). |
| Student | `/student/<id>` | `AppHeader` · `RequirementCard` list with `SourceNote` · `PhraseInput` · `CourseResultCard` list with `RankProvenance` |
| Advisor | `/advisor/<id>` | `AppHeader` · `AdviseeRow` list |
| Advisor-for-student | `/advisor/<id>/student/<id>` | Identical to Student plus an acting-as banner |
| **Term review** *(new)* | `/advisor/<id>/student/<id>/review` | Proposed term checked against every outstanding requirement in one pass (**FR30**) |

The student and advisor result views render from one template and one code path. They must not
diverge — an advisor is meant to see what the student sees (**FR29**).

## 7. Interaction and states

Every list has a designed empty state. Every requirement panel has a "nothing offered closes
this" state (**FR32**) — the condition behind **F-12** and **F-13**, and the one most likely to be
left undrawn.

Search is a full page load with the phrase in the query string, so a result is linkable and a
student can send one to their advisor. No autocomplete: **D-17** says students cannot describe
what fits, so suggesting vocabulary would put words in their mouth.

Reranking takes seconds. The page does not block on it silently — if the deterministic order is
shown first and refined, the refinement must be visible, and if it falls back, `RankProvenance`
says so rather than failing quietly (**FR21**).

## 8. Accessibility

Both references fail in ways worth not repeating: DegreeWorks encodes completion in circle
colour alone, and Banner truncates mid-word with no title attribute and fails AA on its primary
button.

Target: **WCAG 2.1 AA**. Body text ≥ 4.5:1, large text ≥ 3:1, non-text indicators ≥ 3:1.

## 9. Responsive

Banner requires horizontal scrolling on a laptop at 93 rows for one subject. The Navigator does
not use a horizontal data grid. Breakpoints at 640 and 1024; `RequirementCard` and
`CourseResultCard` reflow from two columns to one; the `MeetingPattern` day boxes stay fixed
because they are already compact. No table in this product may scroll the page body
horizontally.

---

## 10. UX Design Requirements

### Design tokens

- UX-DR1: Implement the colour token set in §4 as CSS custom properties on `:root`, replacing hard-coded colours in `static/style.css`.
- UX-DR2: Implement the type scale (12/14/16/20/28px, 16px body) and the 4px spacing grid as tokens.
- UX-DR3: Define card styling once — 8px radius, 1px `--rule` border, no shadow — and apply it to `RequirementCard` and `CourseResultCard` rather than styling each.
- UX-DR4: Replace Banner's `#638D4F` with the `--ok` token at 5.14:1 wherever a success or completion colour is used; no inherited colour may ship below 4.5:1.

### Components

- UX-DR5: Build `AppHeader` with three states — student, advisor, and advisor-acting-for-student — the third carrying a visible acting-as banner naming the student.
- UX-DR6: Build `StatusCircle` with three states (complete, in-progress, not-started), each carrying a distinct shape or glyph in addition to colour.
- UX-DR7: Build `StatusChip` with COMPLETE / IN-PROGRESS / INCOMPLETE variants, styled after DegreeWorks' outlined chip.
- UX-DR8: Build `RequirementCard` showing requirement name, hours applied against hours required, must-include constraints, and a `StatusCircle`; with a distinct fourth state for "no offered section closes this".
- UX-DR9: Build `RequirementBadge` with an emphasised variant for must-include buckets, naming the specific bucket (Literature, History) rather than the parent pool.
- UX-DR10: Build `SourceNote` rendering the source document, its revision date, and the catalog year; attach it to every surface that states a requirement rule.
- UX-DR11: Build `PhraseInput` with recent phrases and a no-match state; no autocomplete or suggested vocabulary.
- UX-DR12: Build `CourseResultCard` showing subject, number, untruncated title, credits, all requirement badges, the match reason, meeting pattern, seats, and a "+N more sections" affordance.
- UX-DR13: Build `MeetingPattern` as SMTWTFS day boxes plus time, with TBA and online variants, following Banner's widget.
- UX-DR14: Build `SeatCounter` with open and full variants, the full variant distinguished by text as well as colour.
- UX-DR15: Build `UncertaintyFlag` with two variants — unknown topic, and unknown seminar theme — each stating what is unknown and directing the user to their advisor.
- UX-DR16: Build `RankProvenance` stating whether the order is deterministic or reranked and how many candidates validation discarded.
- UX-DR17: Build `GapWarning` for a requirement no offered section can close.
- UX-DR18: Build `EmptyState` with three variants: no phrase match, no advisees, no outstanding requirements.
- UX-DR19: Build `AdviseeRow` showing the student, their classification, and a count of open requirements.

### Screens

- UX-DR20: Build the advisor term-review screen at `/advisor/<id>/student/<id>/review`, checking a proposed term against every outstanding requirement in one pass.
- UX-DR21: Render the student and advisor-for-student result views from a single template and code path so they cannot diverge.
- UX-DR22: Make search results linkable — the phrase lives in the query string and a result URL can be shared with an advisor.

### Visual standardisation

- UX-DR23: Audit `static/style.css` and replace every literal colour with a token from UX-DR1.
- UX-DR24: Introduce semantic classes for the states named in §5 rather than styling by element or position.
- UX-DR25: Remove all text truncation from requirement-bearing fields — title, attribute, instructor. These are the fields the product exists to surface.

### Accessibility

- UX-DR26: Meet WCAG 2.1 AA — body text ≥ 4.5:1, large text ≥ 3:1, non-text indicators ≥ 3:1. Run a contrast audit over the finished palette and record the result.
- UX-DR27: Ensure no state is conveyed by colour alone; every status carries a glyph, shape, or word.
- UX-DR28: Provide a visible keyboard focus indicator on every interactive element, at ≥ 3:1 against its background.
- UX-DR29: Make the result list keyboard-navigable in DOM order, with the phrase input as the first tab stop on the student view.
- UX-DR30: Give `StatusCircle` and `SeatCounter` accessible text so a screen reader announces state, not just a styled element.
- UX-DR31: Mark each requirement group as a landmark region with a heading, so a screen reader user can move between requirements without traversing every result.

### Responsive

- UX-DR32: Support breakpoints at 640px and 1024px; `RequirementCard` and `CourseResultCard` reflow from two columns to one below 640px.
- UX-DR33: Ensure no element causes horizontal scrolling of the page body at any supported width; wide content scrolls within its own container.

### Interaction

- UX-DR34: Give every list a designed empty state; no list may render as a blank region.
- UX-DR35: Make reranking visible — show the deterministic order first, indicate refinement in progress, and state plainly via `RankProvenance` when it falls back.
- UX-DR36: Label every model-produced line as proposed, alongside the source text it derives from.
