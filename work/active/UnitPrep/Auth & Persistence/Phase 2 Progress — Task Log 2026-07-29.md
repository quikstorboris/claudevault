---
date: 2026-07-30
description: "Per-task write-ups for Auth & Persistence Phase 2 tasks 4, 5 and 8 — the 2026-07-29/30 session that shipped registration, login and first-admin bootstrap."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — Phase 2 Task Log, 2026-07-29/30

Tasks 4, 5 and 8, split from [[Phase 2 Progress — Task Log]] at the session
boundary — tasks 1-3 were built 2026-07-21 in a different session and read as a
separate era. **Content moved verbatim.**

Status and forward-looking constraints live in [[Phase 2 Progress]]. A
narrative account of this whole session, including the work outside Phase 2,
is in [[Session 2026-07-29 — Auth Tasks 4, 5, 8 and Infrastructure Fixes]].

## Task 4 complete, 2026-07-29 — WebAuthn registration HTTP endpoints

`POST /auth/register/begin` + `POST /auth/register/finish`, in a new `src/api/auth_register.rs`. Supporting pieces: `src/auth/registration_ceremony.rs` (ephemeral ceremony state), `src/auth/ceremony_cookie.rs` (short-lived ceremony cookie), a new `AppState.registration_ceremonies` store, `try_authenticated_user` and `begin_owner_rls_transaction` helpers, and one new migration.

### The sequencing problem this task had to solve first

The 11-task order puts registration (4) before invite acceptance (6), invite creation (7), and first-admin bootstrap (8) — but registration needs a *real user row* to attach a credential to, and before tasks 6-8 exist there is no way to reach one. Three options were weighed; the chosen answer was **build a deliberately-gated bootstrap path as part of task 4** rather than either reordering the whole plan or shipping an ungated `user_id`-parameterized endpoint (which would have been a real privilege-escalation hole — anyone could register a competing passkey against the existing admin before gating landed).

So `/begin` has two paths, decided once per request:
- **Authenticated** — a caller with a valid session adds another passkey *for themselves*. Target comes from the session; any `email` in the body is ignored outright (honouring it would let a signed-in user write a credential onto someone else's account).
- **Bootstrap** — the unauthenticated first-passkey path. Triple-gated: `AUTH_BOOTSTRAP_ENABLED=true` env var, **plus** active-user and zero-existing-credentials checks enforced *inside* the new SECURITY DEFINER function, not in Rust.

### Decisions worth keeping

- **Authorization checks live in the database, not the handler.** New migration `20260729200000_bootstrap_registration_lookup` adds `auth.resolve_bootstrap_registration(citext)` which only matches an `active`, non-deleted user with **zero** `webauthn_credentials` rows. Putting both conditions in the function means an anonymous caller cannot enumerate users and cannot re-register over an existing passkey *regardless of handler bugs*.
- **One indistinguishable rejection for every bootstrap failure** (no such email / not active / already has a passkey / bootstrap disabled). Carving out the two arguably-non-secret cases is exactly what would reveal the other two by elimination.
- **`begin_owner_rls_transaction` added as a strictly-less-privilege sibling to `begin_rls_transaction`** — sets only `app.current_user_id`, deliberately leaving `app.current_user_role` unset. `webauthn_credentials`' RLS policy consults only the user-id GUC, and the bootstrap path has no role to legitimately assert. Safe because every admin-bypass branch in this schema is a *text* comparison (`current_setting(...) = 'admin'`), which evaluates false when unset — no `NULLIF` guard needed, unlike the uuid casts (see [[RLS Implementation]]'s gotcha).
- **The ceremony is consumed BEFORE verification, not after.** A failed or replayed `/finish` must not get a second attempt against the same challenge; a legitimate retry needs a fresh `/begin`. This is the property the `a_failed_finish_still_consumes_the_ceremony` test exists to guard — a "delete on success" implementation looks correct in the happy path and is wrong exactly here.
- **`is_bootstrap` is decided at `begin` and carried in the ceremony**, not re-derived at `finish`. Whether a cookie happens to be present on the *second* request is a different question from which path authorized the ceremony. Only bootstrap ends with a newly issued session; an authenticated caller keeps the session they arrived with.
- **`try_authenticated_user` is called exactly once** in `/begin`. An earlier draft called it twice (once for the target, once for `is_bootstrap`) — caught in self-review: a wasted round trip and a window where the two answers could disagree.
- **Ceremony state uses `unitprep_core`'s generic `SessionStore`**, not a DB table — meaningless once complete/expired, and must not survive a restart. 5-minute TTL, matched deliberately in both the cookie and the store so neither silently decides the real timeout.
- **`sessions.ip_address` is left NULL.** Capturing a real client IP needs `into_make_service_with_connect_info` wiring plus a trusted-forwarded-header policy that doesn't exist yet; a spoofable value in an audit-relevant column is worse than none. `user_agent` *is* captured from headers.
- **Partial-failure honesty**: if the credential saves but `create_session` fails, the response says "passkey saved, but sign-in failed — try signing in" rather than a flat error. A flat failure would invite re-registration, which would now hit the zero-credentials guard and look permanently broken.

### Verification (independently run, not assumed)

`cargo build --workspace` clean. `cargo test --workspace`: **344 passing**, 0 failed (up from 336 at v1.1.5 — exactly the 8 new tests: 3 ceremony-cookie, 5 handler), 2 pre-existing ignored real-PII fixtures unchanged. `cargo clippy --workspace --all-targets`: **7 warnings, down from the 17-warning baseline** — task 4 consumed a lot of previously-dead auth code; all 7 remaining are pre-existing login/logout items awaiting tasks 5/10, zero introduced by this work. `cargo fmt --all -- --check` clean. Migration applied to Neon dev and the function verified present via `\df`.

**Not yet exercised end-to-end against a real browser/authenticator** — no frontend calls these endpoints yet, and Windows Hello has not been driven through a real ceremony. The handler logic, gating, and ceremony lifecycle are unit-tested; the actual passkey round trip is unverified. That is the first thing to do alongside task 5.

**Uncommitted**, per this project's standing pattern — pending Boris's go-ahead.

### Also created this session

Boris's real user row in `auth.users` (`019faf50-b873-7df5-83f3-945710e6a4bf`, `bmaksimov@quikstor.com`, Implementation Manager, `company=quikstor`, `role=admin`, `status=active`) — the bootstrap path's target. A 5-role expansion was raised and declined, see [[Key Decisions]]; `role=admin` remains the only valid enum value.

## Task 5 complete, 2026-07-29 — WebAuthn login HTTP endpoints

`POST /auth/login/begin` + `POST /auth/login/finish` in a new `src/api/auth_login.rs`, plus `src/auth/authentication_ceremony.rs`, a second ceremony cookie name, a shared `src/auth/audit_log.rs`, and migration `20260729240000_login_candidate_lookup`.

### Decisions worth keeping

- **The two legs need different database access, and that shaped the design.** `/begin` starts from a client-supplied email with no session, so no `app.current_user_id` GUC — and `webauthn_credentials` is owner-only RLS, so a direct read returns zero rows for everyone. Hence `auth.resolve_login_candidate`, a `SECURITY DEFINER` lookup. `/finish` needs no such bypass: the ceremony carries a server-side `user_id` that was never client-supplied, so it reads *and* writes through ordinary owner-scoped RLS.
- **The ceremony stores only `user_id`, never a copy of the credential set.** Re-reading at `finish` avoids a stale copy (a passkey revoked in another tab mid-ceremony) — verifying against a stale set is the kind of check that keeps passing after it has stopped meaning anything.
- **Login must persist what it verified.** webauthn-rs advances the credential's signature counter (the anti-cloning mechanism); not writing the updated blob back leaves the check comparing against a frozen value, which passes forever and detects nothing. `last_used_at` is stamped in the same statement.
- **Ceremony consumed before verification**, same as registration — but it matters more here: replaying an assertion against a live challenge is a real attack, not just an untidy retry.
- **Separate ceremony cookie names for registration and login**, not one shared name. The stores are separate and both can be in flight at once; a shared name would let one `begin` silently strand the other's ceremony. A test asserts independence in both directions.
- **Audit events wired now, not deferred to task 11**, per the build plan's from-day-one requirement. `login_succeeded` / `login_failed` / `passkey_registered`. `audit_log::record` is deliberately infallible to callers — propagating a logging failure would let anyone who could break audit writes deny logins, and the trail is not more important than the operation it describes. A failed attempt against an unknown address records no actor, with the address in `metadata` rather than a column since it may match no account.
- **User-enumeration resistance holds**: unknown email, inactive user, soft-deleted user, and active-but-no-passkey all return one byte-identical 401. One residual leak is accepted and documented — the identified WebAuthn flow must name credential ids in `allowCredentials`, so whether a *usable* challenge returns still signals existence. Adopting discoverable credentials later closes it for free.

### Verification — including against the live database, unlike task 4

`cargo build/test/clippy/fmt --workspace`: **350 tests passing** (up from 344), clippy **down to 2 warnings** from the 7-warning baseline (task 5 consumed all the previously-dead authentication code; the 2 left are `clear_session_cookie`/`SESSION_COOKIE_NAME` awaiting task 10), fmt clean.

**Then run against real Neon dev with the real binary** — which is what caught the pooler bug below. Confirmed live: `/health/db` reports `app_service`; `register/begin` returns a genuine WebAuthn challenge and sets its ceremony cookie; `login/begin` returns byte-identical 401s for a credential-less real account and a nonexistent one; two `login_failed` rows landed in `auth_audit_logs` with no actor — which also exercised the no-`RETURNING` audit insert in exactly the no-identity-context case that `RETURNING` breaks on.

### Real browser ceremony — DONE 2026-07-29, tasks 4 and 5 now fully verified

Driven end to end through Windows Hello in Chrome on Windows, against the real Neon dev branch, using a throwaway harness (`dev-tools/auth-test.html` + `run-auth-harness.sh`, deliberately uncommitted). This was the last unverified piece of both tasks.

**What worked**: bootstrap registration → credential stored → session cookie issued → login → `GET /health/whoami` returning the correct `user_id`/`role` → a *second* login. Database state confirms all of it: 1 credential row with `last_used_at` advanced, 3 sessions (one from registration, one per login), and a complete 5-row audit trail (`passkey_registered` with `bootstrap: true`, two `login_succeeded` with session ids, plus two earlier actor-less `login_failed` rows from curl probes).

**The DB-level bootstrap guard closed the door by itself**: `resolve_bootstrap_registration` now returns zero rows for Boris, because he has a credential. So even with `AUTH_BOOTSTRAP_ENABLED=true` still set, the bootstrap path cannot be reused against his account — exactly as designed, and confirmed rather than assumed.

**Three env vars are the difference between working and an opaque browser error** (all set by the harness script): `WEBAUTHN_RP_ORIGIN` must equal the page origin exactly, `CORS_ALLOWED_ORIGINS` must include it (the API only defaults to `:3000`/`:5173`), and `SESSION_COOKIE_SECURE=false` — otherwise the browser silently drops the cookie over plain http and the ceremony loses it between its two requests. A first `NotAllowedError` on a dismissed prompt is benign; retry.

### Two findings from the real ceremony that unit tests could never have surfaced

**1. `webauthn_credentials.device_bound` was wrong data, not just unpopulated — both halves now resolved 2026-07-29.** The column is `NOT NULL DEFAULT true` and **nothing anywhere wrote it** (`grep` found it only in the creating migration). The credential Windows Hello produced reports `backup_eligible: true` — a **synced** passkey — so the row claimed `device_bound = true` while describing a credential that was the opposite. A fabricated value, which is worse than a null one because nothing about it looks wrong.

- **Data fixed**: registration now writes it explicitly as `NOT backup_eligible`, read through webauthn-rs's `From<Passkey> for Credential` conversion. That conversion is gated behind the `danger-credential-internals` feature, now enabled — the crate's warning on it is specifically about *changing* internal `Credential` values and it names reading internals for storage as an intended use, so reading one boolean is within scope. The alternative was parsing the serialized blob, whose shape is explicitly not guaranteed and which would fail *silently* rather than at compile time.
- **The one pre-existing wrong row was backfilled** and consistency verified (`device_bound = NOT backup_eligible` for every row, zero mismatches).
- **Requirement dropped, not deferred** — see the reversal recorded in [[Architecture]]. Boris's call: device-bound is a bad fit because he works remotely on occasion, and Windows Hello produces a synced credential by default, so enforcing it would block the ordinary path to protect secrets that do not exist yet. The column survives as **information only**; nothing refuses a credential on it.
- A `device_bound_from_backup_eligible` helper exists purely so the relation is asserted in one place. Both sides are plain booleans, so a dropped `!` would compile and silently invert the meaning for every credential forever. **The first version of that test was tautological** — it re-stated the inversion locally, so dropping the `!` in production would have left it green; rewritten to call the production function.

**Still unverified**: a *fresh* registration writing the correct value has not been observed — the backfill fixed existing data and the derivation is unit-tested, but the insert path's new binding has only been exercised in tests. The next real harness run (adding a second passkey via the authenticated path) is the natural check.

**2. The signature counter is 0 and will stay 0 on this authenticator** — so a claim made earlier in this note's task-5 section needs qualifying. Persisting `updated_passkey_data` is still correct and necessary in general (a counter-implementing authenticator would advance it, and a frozen stored value would make the anti-cloning check pass forever). But for *this* platform authenticator the counter is always 0, so the two successful logins prove the **write path executes** (`last_used_at` moved) — they do **not** exercise counter advancement, and this credential gets no anti-cloning protection from the mechanism at all. Platform authenticators commonly omit counters; this is WebAuthn reality, not a defect.

### Two mistakes made and corrected this session

1. **Edited two already-applied migrations** (comment-only), which changed their sqlx checksums and made every later `sqlx migrate run` refuse to start. Fixed by restoring both files byte-exactly and verifying against the recorded checksums. **Standing rule earned: never edit a migration applied anywhere, not even a comment** — put the correction in code that reads the schema, or in a new migration.
2. **Left a 30-second stall in the test suite.** The login tests took 30.00s where the rest of the crate runs in microseconds: the shared test pool is lazy, so a handler reaching the database doesn't error, it waits out sqlx's 30s default `acquire_timeout` and *then* errors — test still passes, only the suite gets mysteriously slower. Tightened to 50ms so an unintended query fails fast instead of hiding. Now 0.05s.

### The pooler bug this task uncovered

Task 5's live test was the first time any handler touched real Postgres, and it immediately failed everything with `unsupported startup parameter in options: search_path`. Full account in [[RLS Implementation]], including the correction to an earlier wrong "pooler confirmed working" conclusion. Short version: `db.rs` sent `search_path` as a connection option, which Neon's pooler rejects; fixed by dropping it and schema-qualifying all application SQL.

## Task 8 complete, 2026-07-29 — first-admin bootstrap

`unitprep bootstrap-admin` — a **subcommand of the main binary**, in `src/bootstrap.rs`. Creates the first administrator and prints a one-time setup link.

### Reordered: 8 before 6 and 7, deliberately

The task list has 6 (invite acceptance) → 7 (invite creation) → 8 (bootstrap), but 8 is the actual dependency of the other two. An invite is created *by an admin*, and until one exists nobody can create one — so bootstrap is the way in, and it **mints the first invite token itself**, which is exactly what makes acceptance testable without hand-inserting rows. (An earlier suggestion in this session to do 7 before 6 was wrong for the same reason and is superseded: bootstrap supplies the token, so 8 → 6 → 7 is right.) `user_invites.created_by` being nullable "specifically for the bootstrap first-admin case" confirms this was the original intent.

### Decisions

- **A subcommand, not an endpoint.** An HTTP endpoint that can mint an administrator is a hole whose only defence is an env var being correct everywhere, forever — precisely the shape of `AUTH_BOOTSTRAP_ENABLED`, which this exists to retire. A subcommand has no remote surface: the guard is structural rather than configured.
- **A subcommand rather than a `src/bin/` target** because this crate has no library target, so a separate binary could not `use` the token generation/hashing in `auth::session_token` and would have to reimplement it. Duplicating a security primitive to keep files tidy is the wrong trade.
- **Connects as the owner** via a dedicated `BOOTSTRAP_DATABASE_URL`, never `DATABASE_URL`. The owner bypasses RLS, which is what allows inserting a user with no established identity. Teaching `app_service` to create users would hand the running application a permanent capability to serve a one-time need. **Bonus confirmed behaviour**: if an operator wrongly points it at the app role, RLS refuses the insert rather than half-working.
- **The "no existing users" guard prevents operator error, not attack** — anyone holding the owner credential can already do everything this tool does. Documented as such so nobody mistakes it for a boundary.
- **The account is created `invited`, not `active`**, so the first admin walks the *same* enrolment path as everyone after them (accept invite → `consume_invite` flips to `active` → enrol passkey). One path exercised from the first account, rather than a special case that runs once and is therefore never really tested.

### `--reissue-invite`, and why it is not optional

A lost setup token would otherwise leave an **unrecoverable database**. Discovered while testing: `DELETE FROM auth.users` is impossible — `auth_audit_logs.actor_user_id`/`target_user_id` are `ON DELETE SET NULL`, and the append-only trigger forbids that UPDATE, *including for the owner role*. One failed sign-in attempt is enough to make an account permanently undeletable. So "delete the user and start over" — which the tool's first draft actually printed as advice — is conditionally true immediately after bootstrap and silently impossible thereafter. Worse than plainly wrong.

`--reissue-invite` closes it: retires any outstanding invite (so a mislaid token does not stay live until natural expiry) and mints a replacement. Narrow on purpose — refuses if the account has any passkey enrolled, or is not `invited`.

### Latent schema contradiction found, flagged not fixed

`auth_audit_logs`' two user FKs declare `ON DELETE SET NULL`, but the append-only trigger means that action **can never fire**. Harmless in practice — the design is soft-delete-only anyway (`users_delete_blocked` is `USING (false)`, and [[Architecture]] describes a restorable-archive pattern) — but the schema *declares* a behaviour it cannot perform, which misleads a reader. Changing those FKs to `NO ACTION`/`RESTRICT` would make the schema state the truth, at zero functional benefit today. Not acted on unilaterally.

### Verification

`cargo build/test/clippy/fmt --workspace`: **366 tests passing** (up from 351), clippy still at the 2-warning baseline, fmt clean. The serve path was re-checked after adding subcommand dispatch (`/health` still reports `1.2.0`).

Verified against the live dev branch with the real binary: a malformed invocation exits 2 without connecting; a missing `BOOTSTRAP_DATABASE_URL` refuses with a pointed message; **the guard refuses because a user exists**; pointing at the app role fails on RLS; reissue refuses for an enrolled account and for a nonexistent one. The full invite lifecycle — create `invited` admin, `created_by` NULL, `resolve_invite` finds it, reissue kills the old token and mints a live one, `consume_invite` flips to `active` — was verified in a rolled-back transaction. Dev data unchanged throughout.

**Not verified**: the create-mode happy path through the tool itself, because it requires a genuinely empty database and the only one available is the prod branch. The SQL is verified; the Rust path around it is not.

### Follow-on work, same session (2026-07-30)

**Create mode is now verified for real.** The gap noted above closed by bootstrapping the **prod** branch, which was the only genuinely empty database available — the tool refuses to run anywhere a user exists, so nowhere else could exercise it. Prod now holds Boris's admin account (`invited`) plus one live 24-hour invite. Both modes confirmed against a live database: create produced the account and invite as intended and refused a second run; reissue retired the first invite and minted a live replacement, leaving **exactly one usable link**.

> [!warning] Caught only by checking the database, not the tool's output
> The first prod run used a **stale binary** — compiled before the 24-hour change — and cheerfully printed "valid for 7 day(s)". The database confirmed it (`lifetime_hours = 168`). Had I trusted the tool's own output I would have reported a 24-hour invite that was actually a week long. Rebuilt, then reissued, which incidentally gave reissue mode its real end-to-end test. **Lesson: after changing a value a CLI prints, verify the stored result, not the printout.**

**Prod drift closed**: dev and prod both at 23 migrations, checksums clean on both, and **48 structural facts diffed identical**. Note the parity probe first reported "IDENTICAL across 0 structural facts" — a false pass, because the query errored on both sides (`confdeltype` is `"char"`, so `||` was ambiguous) and diffed two empty files. Fixed and re-run; the "0 facts" was the tell.

**Two migrations added** (both applied to dev and prod):

- `20260730100000_honest_audit_log_fk_actions` — the `ON DELETE SET NULL` → `RESTRICT` fix for the contradiction found earlier. Nothing changes about what is possible; the error now names the foreign key instead of misdirecting at the append-only trigger.
- `20260730110000_expire_factors_on_deactivation` — the factor-expiry trigger from decision 3 in [[Key Decisions]].

**Also**: `README.md` now documents the bootstrap command and how the first admin is created — the discoverability answer to "how would a developer know this in five years". Its security-posture section was stale (claimed no authentication existed anywhere) and now says accurately that registration and sign-in exist while **no tool endpoint requires them yet**.

**Next**: task 6, invite acceptance — which finally lets `AUTH_BOOTSTRAP_ENABLED` be retired, and has a live prod invite waiting to test against. Still unobserved: a fresh registration writing `device_bound` correctly.

> [!note] Superseded 2026-07-30 — task 6 landed.
> `AUTH_BOOTSTRAP_ENABLED` and `auth.resolve_bootstrap_registration` are both
> **deleted**, so the bootstrap mechanics described above no longer exist in the
> code. The reasoning is kept because it is what the replacement was designed
> against; the mechanics are history. Current status lives in
> [[Phase 2 Progress]]. `device_bound` at enrolment is still unobserved on a
> fresh registration — it is now captured into the `passkey_registered` audit
> metadata, but that has not been seen on a real ceremony.

