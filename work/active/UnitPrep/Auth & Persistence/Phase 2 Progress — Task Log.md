---
date: 2026-07-30
description: "Per-task completion write-ups for Auth & Persistence Phase 2 — tasks 1-5 and 8, verbatim from the core progress note when it crossed the 25KB split threshold."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — Phase 2 Progress — Task Log

Chronological bulk split out of [[Phase 2 Progress]] on 2026-07-30, when that
note crossed the vault's 25KB organization threshold. **Content moved verbatim
— nothing trimmed.** The core note keeps the task list, current status, and the
constraints that bear on future work; this holds the detailed account of how
each completed task actually went, including the mistakes and their corrections.

Read the core note first for *where things stand*; read this for *how they got
there*.

## Decisions made during task 1

**Dropped `axum-login` from the original plan.** The architecture doc's phrasing bundled "webauthn-rs + axum-login + TOTP fallback" together, decided before the DB-level session mechanism existed. Now that `create_session()`/`resolve_session()` (built in Phase 1) already *are* the session-store logic, axum-login's own abstraction (built around `tower-sessions` storing arbitrary session data) doesn't fit our specific token-hash → (user_id, role) shape. Session cookie handling (task 2) and verification middleware (task 3) were hand-rolled directly against our own functions instead. `totp-rs` stays, deferred to task 9 (added only when actually used).

**`AuthBackend` trait is synchronous, not async.** The existing `SessionStore` trait in `unitprep-core` is fully sync by deliberate design (session ops must stay short/sync, never hold a lock across `.await`). webauthn-rs's own ceremony verification is CPU-bound crypto, not I/O — nothing to `await` — so matching sync avoids async-trait-object complications (native async-fn-in-traits isn't yet object-safe on stable for `Arc<dyn Trait>` without `async-trait` or manual `Pin<Box<dyn Future>>`).

**Auth code lives in the binary (`src/auth/`), not `unitprep-core`.** `core` is used by `unit-group`/`dedup` tooling too, which has no reason to pull in webauthn-rs/OpenSSL. `db.rs` already set this precedent (binary-level infra, not core).

## webauthn-rs 0.5.5 — verified API specifics (checked via docs.rs, not assumed)

- Pulls in an OpenSSL system dependency via its `attestation` feature (default-on) — independent of sqlx's own `tls-rustls` choice, just two unrelated dependency trees. May need `libssl-dev` on deployment images later, not a concern for local dev.
- Added with `--features danger-allow-state-serialisation` — needed because ceremony state (`PasskeyRegistration`/`PasskeyAuthentication`) must be persisted across the begin/finish HTTP request pair; without this feature the state types aren't serializable at all.
- **Schema correction found here**: `Passkey` (the stored-credential type) is `Serialize`/`Deserialize`, meant to be persisted as one opaque blob — no public constructor to rebuild one from separately-stored parts, and `update_credential()` operates on the whole deserialized struct. The original `webauthn_credentials` schema (separate `public_key`/`sign_count` columns) would have left no way to reconstruct a working `Passkey`. Fixed via migration `fix_webauthn_credentials_storage` (single `passkey_data jsonb` column replaces both) **before** any ceremony code was written against the wrong shape.
- Confirmed method names/shapes (all compiled correctly on first attempt): `WebauthnBuilder::new(rp_id, &Url).build()`, `start_passkey_registration(user_id, username, display_name, exclude: Option<Vec<CredentialID>>)`, `finish_passkey_registration(&RegisterPublicKeyCredential, &PasskeyRegistration) -> Passkey`, `start_passkey_authentication(&[Passkey])`, `finish_passkey_authentication(&PublicKeyCredential, &PasskeyAuthentication) -> AuthenticationResult`, `Passkey::cred_id()`, `Passkey::update_credential(&AuthenticationResult)`, `CredentialID::from(Vec<u8>)`.

## Task 1 complete, 2026-07-21

`src/auth/mod.rs` (trait + data types + `AuthError`) and `src/auth/webauthn_backend.rs` (`WebauthnRsBackend` implementation) committed as `47cb01c`. `AppState` gained `auth_backend: Arc<dyn AuthBackend>`, configured from `WEBAUTHN_RP_ID`/`WEBAUTHN_RP_ORIGIN` env vars (localhost defaults). Verified: full workspace build + all 138 existing tests pass (added a `test_auth_backend()` fixture, same shape as `test_db_pool()`); ran the binary end-to-end, confirmed `/health` still works and startup doesn't panic with the default config. Nothing calls this backend yet — no HTTP endpoints exist for registration/login (tasks 4/5).

Also committed this session, before task 1: the `fix_webauthn_credentials_storage` migration (schema correction above), as its own commit.

Not yet pushed to origin as of this writing — pending Boris's go-ahead, same as every commit this session.

## Task 2 complete, 2026-07-21

`src/auth/session_token.rs` (random 256-bit token + SHA-256 hash, `getrandom` not `rand` directly — `rand` 0.10's API had churned enough that `getrandom::fill()` was the more robust choice for this one narrow need) and `src/auth/session_cookie.rs` (plain, unsigned `axum-extra` `CookieJar` wrapper — deliberately not `cookie-private`/`cookie-signed`, since the token is opaque and only ever trusted via a `resolve_session()` round-trip, not decoded as a claim). Both have real unit tests (round-trip, no-collision, issue/read/clear). Committed as `6748839`.

`SESSION_COOKIE_SECURE` env var (default true) added as an escape hatch — genuinely unverified yet whether `Secure=true` will cause problems testing the full login flow over plain `http://localhost` later; flagged to check empirically in tasks 4/5, not resolved here.

Full workspace test suite: 143 tests, all passing.

## Task 3 complete, 2026-07-21

`src/auth/authenticated_user.rs`: `AuthenticatedUser` (axum `FromRequestParts<AppState>` extractor) resolves the session cookie via `resolve_session()` — no GUC context needed for that one call since it's `SECURITY DEFINER` and bypasses RLS on its own. Returns 401 for missing/unresolvable cookies. Split cleanly from a separate `begin_rls_transaction(pool, user_id, role)` helper — begins a transaction and sets both GUCs via `set_config(..., true)` (the `is_local` argument, equivalent to `SET LOCAL`), so a pooled connection can never leak one request's identity into a later, unrelated request reusing the same connection. Handlers that need RLS-scoped queries call this explicitly rather than assuming any GUC is pre-set on the shared pool.

`Role` is an enum with one variant (`Admin`) today, mirroring the schema's own extensible-single-value design.

Added `GET /health/whoami` to exercise `AuthenticatedUser` end to end, since no real protected endpoint exists yet. **Verified against the live dev database, not just unit tests**: generated a real token/hash pair (Python, matching the exact base64url+SHA-256 scheme), inserted a real test user+session row, ran the app with a temporary owner-credential `DATABASE_URL` override (`app_service`'s real password still isn't set in `.env.local` — this was a one-off local override, never committed), confirmed via curl: no cookie → 401, garbage cookie → 401, valid cookie → 200 with correct `user_id`/`role`. Test data cleaned up after. Committed as `e43ec10`.

**Mistakes made and caught while building this, worth remembering for future WSL/heredoc work**:
1. Rust lifetime syntax (`'_`, `'static`) and SQL bind-parameter placeholders (`$1`) both use characters that collide with shell-escaping techniques — apostrophes need `'"'"'`-escape treatment, `$1` inside a heredoc needs `\$1`.
2. A multi-line `sed -i 'Nd' file` (delete) followed by inserting new content at the same now-shifted line number is fragile — safer to `cat replacement.txt remainder_of_file > combined && mv` when replacing a block at the top of a file.
3. When splicing a new function into a file via `sed -i 'Nr snippet.txt'`, double-check N is *after* the target function's closing brace — an off-by-one doesn't error at write time, only at compile time (or worse, silently produces valid-but-wrong Rust if brace count still balances).

Full workspace test suite: 145 tests, all passing.

## Later tasks

Tasks 4, 5 and 8 (the 2026-07-29/30 session) are in
[[Phase 2 Progress — Task Log 2026-07-29]] — split at the session boundary when
this note crossed the 25KB threshold.

Tasks 6, 7, 9 and 10 are in
[[Phase 2 Progress — Task Log (Tasks 6, 7, 9, 10)]] — their first-hand write-ups
existed all along but had drifted into `inbox/` and the bare
`work/active/UnitPrep/` root under auto-generated filenames, never linked from
here. That note also folds in a logging-roadmap closure, a backend security
assessment, and a passkey-only readiness review from the same period, found in
the same drifted state.
