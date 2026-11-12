# Story 1.5: Sign in with a credential

Status: review

<!-- Created 2026-11-11 by bmad-create-story. Third per-story file.
     BUILT AHEAD OF ITS DECISION RECORD: epics.md gates this story on the D-33
     running-log §6 entry, which this repository still calls outstanding. The
     owner directed that it be built regardless. D-33 itself was decided
     2026-11-11; only its log entry is in question. Recorded here, in the story
     status and in sprint-status.yaml so the gap is visible rather than implied. -->

## Story

As a student or an advisor,
I want to sign in with a credential instead of picking my name off a public list,
so that my record is reached by proving who I am rather than by knowing a URL.

## Acceptance Criteria

1. **Given** no session, **when** any route other than the sign-in page is requested, **then**
   the sign-in page is served and no student or advisor data appears in the response.
2. **Given** the sign-in page, **when** a credential matching an `app_user` row is submitted,
   **then** a session is established naming that user, and the view for that user's role opens.
3. **Given** the sign-in page, **when** a credential matching nothing is submitted, **then** the
   page states that sign-in failed without saying which half was wrong, and no view opens.
4. **Given** a signed-in user, **when** the header renders, **then** it names the signed-in user
   and their role, as the picker's header did.
5. **Given** the application is started with no session secret configured, **when** it boots,
   **then** it refuses to start rather than running on a default secret.
6. **Given** a submitted password, **when** it is checked against `app_user`, **then** it is
   verified against a stored `hashlib.pbkdf2_hmac` hash with a per-user salt, and no plaintext
   password is written to the database, the logs or the session.
7. **Given** the application, **when** its dependencies are inspected, **then**
   `requirements.txt` is unchanged — the hashing is standard library, so AR1 still holds.

## Tasks / Subtasks

- [x] Task 1: Credential columns and the hash (AC: 6, 7)
  - [x] `schema.sql`: `app_user` gains `password_hash`, `password_salt`, `password_iterations`
  - [x] New `auth.py`: `hash_password` / `verify_password` on `hashlib.pbkdf2_hmac`, stdlib only
  - [x] Compare with `hmac.compare_digest`, not `==`
  - [x] Store iterations per row so the cost can be raised later without invalidating rows
  - [x] `requirements.txt` must not change — AC 7 asserts this

- [x] Task 2: Config and the boot refusal (AC: 5)
  - [x] Extract `load_env` out of `rank_llm.py` into a new `config.py` — the session secret must
        not be loaded by the optional reranker module; AR14 names one loader, not one per feature
  - [x] `rank_llm.py` imports it from there so its own behaviour is unchanged
  - [x] Refuse to boot when `NAVIGATOR_SECRET_KEY` is missing **or** is a known placeholder
  - [x] The refusal must say how to fix it; a prototype that dies silently is worse than one
        that runs insecurely, because the next person reaches for the insecure path

- [x] Task 3: Sign-in, sign-out of the picker (AC: 1, 2, 3)
  - [x] New `templates/signin.html`
  - [x] `POST /signin` verifies and establishes `session["user_id"]`; **never** store the password
  - [x] A `before_request` guard serves the sign-in page for any unauthenticated route, with
        `static` and the sign-in route itself exempt — otherwise the page renders unstyled
  - [x] Serve the sign-in page directly rather than redirecting: AC 1 says *served*, and keeping
        the requested URL lets `next` return the user where they were going
  - [x] Failure copy must not distinguish unknown user from wrong password (AC 3)
  - [x] **Delete `templates/home.html`** and the picker. Keep a `/` route — `base.html` calls
        `url_for('home')` — which dispatches to the signed-in user's own view
  - [x] Remove `debug=True`: the Werkzeug debugger executes arbitrary code through the browser
        and cannot sit beside a credential

- [x] Task 4: Header and seeded logins (AC: 4, 2)
  - [x] `base.html` names the signed-in user and role, as the picker's header did (UX-DR5,
        which gains a signed-out state)
  - [x] `seed.py` seeds a password per `app_user`; README documents the demo logins

- [x] Task 5: Tests (AC: 1-7)
  - [x] New `test_auth.py` in the project's plain-script style
  - [x] AC 1 is the one to test hardest: assert no student or advisor **name** appears in any
        unauthenticated response, across every route, not merely that a 200 came back
  - [x] AC 6: assert no plaintext password anywhere in `app_user`, and that the session cookie
        does not carry it
  - [x] Existing suites import `app` and will now need the secret set — update them

- [x] Task 6: The documentation this story falsifies (AC: all)
  - [x] `Architecture.md` §2 — the Auth row, and "survives being emailed" at §2's Store row,
        which stops being true once the file carries credentials
  - [x] `Architecture.md` §7 and §9 row 1 ("Auth provider, passwords, sessions")
  - [x] `Architecture.md` §10 — AR16 is reversed by D-33
  - [x] `README.md` "Not built" list, plus the demo logins
  - [x] `data-model.md` — `app_user` gains the credential columns
  - [x] PRD: a new FR carrying D-33; bump the count at `docs/README.md:7` from 34 to 35
  - [x] `epics.md`: Story 1.5 status, Story 1.1's superseded picker criteria, AR16
  - [x] `sprint-status.yaml`: 1.5 → review, roll-up, and the built-ahead-of-record note
  - [x] **Story 7.6's AC 3** — the enforcement half this story closes

## Dev Notes

### This story is why Story 7.6 is not finished

7.6's third criterion has an enforcement half that no amount of work inside 7.6 could close:
without a session, "this advisor" is a route parameter and `/advisor/2` is just a URL. AC 1
here is exactly that fix. When this lands, go back and close 7.6's record — it is listed in
Task 6 because it is easy to leave behind.

### The boot refusal must not strand the test suite

`test_advisor_row.py`, `test_advisor_search.py` and the Story 3.6 harness all `import app`. If
the secret check raises at import, every one of them fails until it sets `NAVIGATOR_SECRET_KEY`.
That is the correct failure — fail closed — but it means Task 5 updates those files in the same
commit, or the suite goes red for reasons unrelated to what is being tested.

### `load_env` is in the wrong module

It lives in `rank_llm.py:41` and runs at that module's import. `app.py` imports `rank_llm`, so
today the `.env` is loaded as a side effect of importing the **optional reranker**. Fine while
the only key was an API key; not fine once the session secret depends on it — if `rank_llm`
ever becomes conditionally imported, the secret silently stops loading. Move it to `config.py`
and have `rank_llm` import it from there. Its one behaviour to preserve: `utf-8-sig`, because
PowerShell writes a BOM that would otherwise become part of the first key name.

There is **no `.env` in the working tree** and `.gitignore` already covers it, so the story must
tell the user how to create one or the app will not start after this change.

### What "no data appears in the response" has to mean in the test

AC 1 is the criterion most easily faked. A guard that redirects returns no data and passes a
weak test, but so does a guard that renders the page with the student's name still in the
`<title>`. Assert on the absence of every seeded student and advisor name in the body of every
unauthenticated response, including `/`, `/student/1`, `/advisor/1`, the advisor-for-student
route and a search URL with a query string.

### Seeded passwords are demo credentials, not secrets

They go in `seed.py` and in the README, in the open, because this is a graded prototype whose
demo must be runnable. That is a deliberate, stated choice, not an oversight — the point of the
story is that the *mechanism* is real (per-user salt, pbkdf2, no plaintext at rest), not that
the demo accounts are secret. Say so in the README next to the logins.

### Project Structure Notes

- New: `auth.py`, `config.py`, `templates/signin.html`, `test_auth.py`
- Deleted: `templates/home.html`
- Modified: `app.py`, `schema.sql`, `seed.py`, `rank_llm.py`, `templates/base.html`, plus the
  existing test files and the documentation in Task 6
- `requirements.txt` must NOT change (AC 7)
- Schema change means the database is rebuilt: `python ingest.py --reset`, `python seed.py`,
  `python descriptions.py --from-csv`. Student ids 1-5 and advisor ids 1-2 must survive, because
  the doc set, the Story 3.6 harness and both advisor test files address them by number.

### References

- [Source: docs/epics.md#Story 1.5] — the seven criteria, "Ready for dev once the D-33 log entry
  exists", "Resized L → M by D-33", "removes the picker"
- [Source: docs/epics.md:198] — AR16, "No auth provider is in scope", reversed by D-33
- [Source: docs/epics.md:246] — AR14, the `.env` loader; the Werkzeug debugger note
- [Source: docs/epics.md#Story 1.1] — the picker criteria this story supersedes
- [Source: docs/Architecture.md:55] — §2 Store row, "survives being emailed"
- [Source: docs/Architecture.md:300-304] — §9 row 1, "Auth provider, passwords, sessions"
- [Source: README.md:64-68] — the "Not built" list
- [Source: rank_llm.py:36-66] — `load_env`, to be moved to `config.py`
- [Source: schema.sql:43-53] — `app_user`, including the role/person CHECK constraint
- [Source: docs/stories/story-7.6.md] — the AC 3 enforcement half this story closes

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code)

### Debug Log References

- `python test_auth.py` -> exit 0, 60 assertions, ALL PASS
- `test_advisor_row.py` 30 · `test_advisor_search.py` 31 · `test_rank.py` 36 · `test_rank_llm.py` 20
- Story 3.6 harness re-run as a regression check -> 63/63, exit 0

### Completion Notes List

**Built ahead of its decision record, at the owner's direction.** The sprint plan gates this
story on the D-33 running-log §6 entry, which this repository still calls outstanding. Stated
in the story status and in `sprint-status.yaml` rather than left implied.

**It does NOT fully close Story 7.6's AC 3, which is why the story was built.** 1.5 closes the
anonymous half: no route but the sign-in page serves data, verified across six routes against
every seeded person's name. It does not close authorisation between signed-in users — advisor 1
can still open `/advisor/2` and `/student/5`, confirmed by running it. Story 1.6 is the last
step. This was mis-stated when the work was scoped and is corrected here and in 7.6's record.

**`load_env` moved out of `rank_llm.py` into `config.py`.** The `.env` was being read as a side
effect of importing the *optional reranker*. Harmless while the only key was an API key;
unacceptable once the session secret depends on it, because a conditionally imported module
would silently stop loading the secret.

**The boot refusal needed an escape hatch to be testable.** AC 5 cannot be exercised in-process
— by the time the test imports `app` the check has already run — and it cannot be exercised in
a subprocess either while the developer's own `.env` sits next to the module, because that file
*is* a configured secret. `config.ENV_FILE` is now overridable via `NAVIGATOR_ENV_FILE`. Two
AC 5 assertions failed first time for exactly this reason, and the code was right both times.

**`authenticate()` hashes even when the username is unknown.** Returning early would make an
unknown user measurably faster to reject than a wrong password, turning the form into a
user-enumeration oracle — which would undo AC 3's single error message.

**Three existing suites needed updating, not because they broke but because the app changed.**
They import `app` (now requiring a secret) and request routes (now requiring a session). One
real assertion changed meaning: `/` returns 302 to the signed-in user's view instead of
rendering a picker.

### File List

- `auth.py` — **new**: PBKDF2-HMAC hashing, authenticate, session helpers
- `config.py` — **new**: the `.env` loader (moved) and the session-secret boot refusal
- `templates/signin.html` — **new**
- `test_auth.py` — **new**: 60 assertions
- `templates/home.html` — **DELETED**: the role picker
- `app.py` — modified: secret at import, `before_request` guard, `/signin`, `/` dispatches, `debug=False`
- `rank_llm.py` — modified: imports `load_env` from `config`
- `schema.sql` / `seed.py` — modified: credential columns, seeded demo passwords
- `templates/base.html` / `static/style.css` — modified: signed-in header, sign-in form
- `test_advisor_row.py` / `test_advisor_search.py` — modified: set a secret, sign in
- `docs/`: `Architecture.md` (§2 ×2, §7, §9, AR16), `data-model.md`, `PRD.md` (FR35),
  `README.md` (count), `epics.md`, `sprint-status.yaml`, `../README.md` (not-built, logins)

## Change Log

| Date | Change | Why |
|---|---|---|
| 2026-11-11 | Credential columns + `auth.py` | D-33; stdlib only, so `requirements.txt` is unchanged (AC 7) |
| 2026-11-11 | `config.py`, `load_env` moved | A security control must not load via the optional reranker |
| 2026-11-11 | Boot refusal on missing/placeholder/short secret | AC 5; a default secret is a forgeable session |
| 2026-11-11 | `NAVIGATOR_ENV_FILE` override | AC 5 was untestable while a real `.env` sat beside the module |
| 2026-11-11 | Role picker deleted, `/` dispatches | The picker was a public index of who exists, each a link into their record |
| 2026-11-11 | `debug=False` | The Werkzeug debugger runs arbitrary code through the browser |
| 2026-11-11 | Docs across 7 files | The story falsifies Arch §2's "survives being emailed", §9 row 1 and AR16 |
