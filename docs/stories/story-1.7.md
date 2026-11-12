# Story 1.7: Sign out and end the session

Status: review

<!-- Created 2026-11-11 by bmad-create-story. Fifth per-story file.
     Last story in sprint 1. Depends on Story 1.5, which is at review. -->

## Story

As a student or an advisor,
I want to sign out,
so that the next person at a shared advising-office machine does not land in my record.

## Acceptance Criteria

1. **Given** a signed-in user, **when** sign-out is chosen, **then** the session is cleared and
   the sign-in page is served.
2. **Given** a session that has been signed out, **when** a student view is requested again,
   **then** the sign-in page is served, and the signed-in response was not marked cacheable.
3. **Given** an advisor acting for a student, **when** sign-out is chosen, **then** the
   acting-as state ends with the session and does not carry into the next sign-in.

## Tasks / Subtasks

- [x] Task 1: The sign-out route (AC: 1, 3)
  - [x] `POST /signout` — **POST, not GET**: a GET sign-out fires from any `<img src>` or
        prefetch on a page the user visits, which logs people out at a distance
  - [x] `auth.logout()` already calls `session.clear()`; use it rather than popping one key,
        so nothing added to the session later survives a sign-out by omission
  - [x] Redirect to a bare `/signin` — **no `next`**: carrying it would send the next person
        who signs in straight back into the previous user's acting-as view (AC 3)
  - [x] Confirm on the sign-in page that sign-out happened, or it reads as a failure

- [x] Task 2: A control in the header (AC: 1, UX-DR5)
  - [x] A small POST form in `base.html` beside the signed-in name
  - [x] Present on every signed-in page, including the acting-as view, which is the state the
        story's "Why" says currently has no exit

- [x] Task 3: Signed-in responses must not be cacheable (AC: 2)
  - [x] `after_request`: `Cache-Control: no-store` on every non-static response
  - [x] This is the actual shared-machine defence. Clearing the session stops the *server*
        answering, but a cached page in the browser is served by the browser — the next person
        presses Back and reads the record without a request ever being made
  - [x] Leave `/static` cacheable: the stylesheet is not private and re-fetching it every
        request on a prototype is noise

- [x] Task 4: Tests (AC: 1-3)
  - [x] New `test_signout.py`, plain-script style
  - [x] AC 2 is two assertions, not one: the session no longer works **and** the earlier
        signed-in response carried `no-store`
  - [x] AC 3: sign in as an advisor, open the acting-as view, sign out, sign in **as a
        different user**, and assert the landing page is that user's own view
  - [x] Assert `GET /signout` does not sign anyone out

- [x] Task 5: Records (AC: all)
  - [x] `sprint-status.yaml`: 1.7 → review, roll-up; sprint 1 has no story left
  - [x] `docs/epics.md`: Story 1.7 status, Epic 1 table row
  - [x] `Architecture.md` §7 and `README.md` both list sign-out as not built — both are spent

## Dev Notes

### AC 2's second clause is the one with teeth

"The signed-in response was not marked cacheable" is not a note about the sign-out response —
it is a requirement on *every page served while signed in*. The threat in the story's own
"Why" is a shared advising-office machine: clearing the session only stops the **server** from
answering. If the student's result page is still in the browser's cache, the next person
presses Back and reads it without a request ever reaching Flask, and no amount of session
handling prevents that. `Cache-Control: no-store` on authenticated responses is the fix, and
the test has to assert the header on a signed-in page, not on the sign-out redirect.

### Why POST

A `GET /signout` link is triggered by anything that fetches a URL — a prefetching browser, an
`<img src="/signout">` on any page the user visits. The cost of POST here is one small form in
the header; the cost of GET is logging people out at a distance for free.

### AC 3 is about `next`, not about stored state

There is no acting-as flag in the session — the acting-as view is `/advisor/<id>/student/<id>`,
so the state lives entirely in the URL. That means the only way it can "carry into the next
sign-in" is through the `next` parameter Story 1.5 added: sign out from the acting-as page
while `next` still points at it, and the following sign-in lands the next person inside the
previous student's record. So sign-out must redirect to a bare `/signin`. `session.clear()`
covers anything session-shaped that gets added later.

### Project Structure Notes

- Modified: `app.py` (the route and the `after_request`), `templates/base.html`,
  `templates/signin.html` (the confirmation), `static/style.css`. New: `test_signout.py`
- `auth.logout()` already exists from Story 1.5 and is currently unused — this story is its
  only caller
- No schema change, no new dependency

### References

- [Source: docs/epics.md#Story 1.7] — the three criteria; "without it sign-in is a one-way
  door and the acting-as state has no exit"
- [Source: auth.py] — `logout()`, written in Story 1.5 and unused until now
- [Source: app.py] — `signin`, the `before_request` guard, and `PUBLIC_ENDPOINTS`
- [Source: templates/base.html] — the masthead and its signed-in state (UX-DR5)
- [Source: docs/epics.md#Story 1.5] — `next`, and the open-redirect guard on it

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code)

### Debug Log References

- `python test_signout.py` -> exit 0, 26 assertions, ALL PASS
- Full suite: 244 assertions across 7 files, all exit 0
- Story 3.6 harness re-run as a regression check -> 63/63, exit 0

### Completion Notes List

**AC 2's second clause was the work.** "The signed-in response was not marked cacheable" reads
like a footnote on the sign-out response and is in fact a requirement on every authenticated
page. Clearing the session stops the server answering; it does nothing about a page the
browser already holds, which is precisely the shared-machine case the story's "Why" describes.
`Cache-Control: no-store, no-cache, must-revalidate, private` now goes on every non-static
response, and the test asserts it on a signed-in page rather than on the sign-out redirect.

**AC 3 is about `next`, not stored state.** There is no acting-as flag in the session — the
acting-as view is a URL — so the only path by which it could survive is the `next` parameter
Story 1.5 added. The test signs out from the acting-as page and then signs in as a *different*
user, asserting they land on their own view and cannot reach the previous acting-as URL. The
second half of that now fails closed twice over, because Story 1.6 would refuse it anyway.

**Sign-out is POST**, and `GET /signout` is asserted to return 405 and to leave the session
intact. A GET sign-out is triggered by any prefetch or `<img src>` on a page the user visits.

**`auth.logout()` existed and was unused.** Written in Story 1.5 against this story; this is
its only caller. It calls `session.clear()` rather than popping `user_id`, so anything added
to the session later cannot survive a sign-out by omission.

**No story left in sprint 1.** 3.6, 7.6 and 7.7 are done and approved; 1.5, 1.6 and 1.7 are at
review.

### File List

- `app.py` — modified: `POST /signout`, `after_request` no-store, `signed_out` into the template
- `templates/base.html` — modified: the sign-out form in the masthead
- `templates/signin.html` — modified: the signed-out confirmation
- `static/style.css` — modified: `.signout`
- `test_signout.py` — **new**: 26 assertions
- `docs/stories/story-1.7.md` — **new**: this file
- `docs/epics.md`, `docs/sprint-status.yaml` — modified: 1.7 status, Epic 1 row, roll-up
- `docs/Architecture.md`, `README.md` — modified: the "sign-out not built" caveats are spent

## Change Log

| Date | Change | Why |
|---|---|---|
| 2026-11-11 | `POST /signout`, `session.clear()` | AC 1; POST so sign-out cannot be triggered at a distance |
| 2026-11-11 | `Cache-Control: no-store` on signed-in responses | AC 2; the browser cache is the shared-machine exposure, not the session |
| 2026-11-11 | Redirect to a bare `/signin`, no `next` | AC 3; otherwise the next person signs in into the previous student's record |
| 2026-11-11 | Sign-out control in the masthead | UX-DR5; the acting-as view had no exit |
