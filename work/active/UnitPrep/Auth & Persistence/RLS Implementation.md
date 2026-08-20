---
date: 2026-07-27
description: "Row-level security build for the OO auth schema: app_service role, bootstrap SECURITY DEFINER functions, per-table policies, functional verification. RLS pass complete 2026-07-21."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — RLS Implementation

Companion to [[Database Schema]] — the row-level-security build-out across all seven tables, completed and functionally verified 2026-07-21.

> [!important] Stale as of 2026-08-08 — the GUC convention below is superseded
> This note describes the original **single-role** convention: one GUC,
> `app.current_user_role` (singular), a bare text comparison. The
> 2026-08-06/07 roles/permissions refactor (see [[Database Schema]]'s own
> correction callout and [[Roles & Permissions — Design Discussion]])
> replaced this with `app.current_user_roles` (**plural**, comma-joined,
> since a user can hold more than one role) and a real function,
> `auth.current_user_has_role(role_key)`, rather than a bare
> `current_setting(...) = 'admin'` comparison. Every specific
> `app.current_user_role` reference below is a historical snapshot of how
> it worked at the time, not current syntax to copy into new policies —
> check a real, recent migration (e.g.
> `add_roles_permissions_tables.up.sql`) for the actual current pattern.
> The verification methodology and RLS *reasoning* throughout this note
> are still sound; only the specific GUC name and check mechanism changed.

## `app_service` role

Non-owner Postgres role the running app connects as (migrations still run as `neondb_owner`, unaffected by its own policies). Created with `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`, deliberately **no password set** initially — a NULL password hash can't authenticate, so it's safe to create ahead of time. Boris sets the real password himself via `\password app_service` (never typed/seen by Claude), then builds a `NEON_DEV_DATABASE_URL_APP` entry in `.env.local` manually. Not blocking — only matters once the Rust app wires up a connection as this role.

Granted: `USAGE` on schema `public`, `SELECT/INSERT/UPDATE/DELETE` on all 7 tables, plus `ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner ...` so future tables auto-grant the same access. Explicitly revoked access to `_sqlx_migrations` (accidentally swept in by `ALL TABLES IN SCHEMA public`) — the app never needs it, only `sqlx-cli` does.

~~**Not yet done**: repeat this whole role setup on the `prod` branch before real go-live~~ — **done 2026-07-29**. Prod went from completely empty (no role, no `auth` schema, no tables, zero migrations) to all 17 migrations applied plus the full role/grant setup, then **audited byte-identical to dev across 43 structural facts** (role attributes, schema `USAGE`, per-table RLS flags and privileges, all 13 policies, all functions with their `SECURITY DEFINER`/execute state, enums, triggers, default ACLs). Prod holds zero user rows — no dev data crossed over — and its `auth_configuration` singleton is migration-seeded, same as dev.

**Discovered doing it**: Neon roles are **per-branch**, not project-wide, so creating `app_service` on dev never propagated to prod — and because the RLS migrations themselves contain `GRANT EXECUTE ... TO app_service`, the role must exist *before* `migrate run` while its grants can only be applied *after*. `setup_app_service_role.sql` could not satisfy both on a fresh branch and aborted prod partway through migration `20260721202617`; it's now guarded so the whole file is safe to run at any point (procedure: run it, migrate, run it again).

**Still outstanding on prod, and it's Boris's to do** (never handled by Claude): set the role's password with `psql "$NEON_PROD_DATABASE_URL_DIRECT" -c "\password app_service"`, then replace `REPLACE_WITH_PROD_APP_SERVICE_PASSWORD` in `.env.local`'s `NEON_PROD_DATABASE_URL_APP`. Nothing reads that value yet (no deployment), and `DATABASE_URL` must stay pointed at dev for local work.

**Manual dev-DB access**: no new role needed — `NEON_DEV_DATABASE_URL_DIRECT` (owner-privileged, already in `.env.local` for migrations) is also right for occasional manual edits, since owner already bypasses RLS. Hard rule: the running application itself must never connect through it.

**Per-developer roles — deferred, naming decided**: with one developer today, individual login roles for "who ran what raw SQL" have no one to distinguish yet. When a second developer joins: one role per person (`<name>_dev`, e.g. `boris_dev`), broad privileges for manual work (not RLS-restricted). Different concern from `auth_audit_logs`, which attributes *in-app* actions via `app.current_user_id`.

**Session-variable convention**: two GUCs set together right after a session resolves — `app.current_user_id` and `app.current_user_role` — avoiding a self-referential subquery back into `users` to check "is this caller admin."

## Critical bug caught by functional testing — apply this pattern everywhere

Naively writing `id = current_setting('app.current_user_id', true)::uuid` throws a hard Postgres error ("invalid input syntax for type uuid: ''") whenever the setting is unset/empty — which happens on any request the middleware forgot to stamp with identity, or any pre-auth context. `missing_ok=true` only suppresses the "no such setting" error, not a bad cast on an empty string.

**Correct, safe form, required for every table**: `NULLIF(current_setting('app.current_user_id', true), '')::uuid` — `NULLIF` collapses the empty string to real `NULL` first, so the cast is skipped and the comparison safely evaluates to `NULL` (false) instead of throwing. Text comparisons like `current_setting('app.current_user_role', true) = 'admin'` don't need this guard.

## Per-table policies

- **`users`** — built, reverted once to fix the bug above, functionally verified: owner-or-admin `SELECT`/`UPDATE`, admin-only `INSERT`, `DELETE` hard-blocked for everyone (`USING (false)`) — hard delete should never happen through the app, only the `deleted_at` soft-delete column. Verified via `SET ROLE app_service` + manually set GUCs inside `BEGIN...ROLLBACK` blocks.
  - ~~**Known, deliberately-not-fixed gap**: the `UPDATE` policy is row-scoped, not column-scoped~~ — **closed 2026-07-29, at the DB layer rather than the app layer** (migration `20260729210000_restrict_users_update_columns`). The original note proposed an app-layer fix (never accept a `role` field on a self-service endpoint); Boris asked for it closed properly rather than deferred, and column-level privileges turned out to be the better answer since they're enforced *in addition to* RLS and don't depend on application discipline surviving future refactors. `app_service` now holds `UPDATE` on only `first_name`, `last_name`, `job_title`; `role`/`status`/`company`/`email`/`deleted_at`/`deletion_reason` are withheld and require a `SECURITY DEFINER` admin-checked function (none built yet — no endpoint needs one). Verified as the real `app_service` role on both branches: escalation refused, mixed `first_name + role` statement refused whole rather than partially applied, profile update succeeds with the `updated_at` trigger still firing. **Gotcha found while doing it**: `setup_app_service_role.sql`'s blanket `GRANT ... ON ALL TABLES IN SCHEMA auth` silently re-granted table-level `UPDATE` and re-opened the hole with no error — the script now re-asserts the narrow grant, and the column list must be kept in sync between the migration and the script.
- **`webauthn_credentials` / `totp_credentials`** — single `FOR ALL` owner-only policy on each, no admin bypass at the RLS layer at all. Verified with two test users: each saw only their own row even with `app.current_user_role = 'admin'` set (confirming no accidental bypass).
- **`sessions`** — needed a **write-side** bootstrap function too, not just read-side: session *creation* happens at login, before any `current_user_id` context exists either. Final shape:
  - `sessions_select_own_or_admin`, `sessions_update_own_or_admin` — standard owner-or-admin. **Hardened 2026-07-29** (migration `20260729220000_revoke_sessions_update`): the `UPDATE` policy is row-scoped, so with `app_service` also holding table-level `UPDATE` a caller could have set `revoked_at = NULL` on their own rows (undoing sign-out-everywhere) or pushed `expires_at` out indefinitely — both defeating the exact guarantee the opaque-token-over-JWT decision was made to get. `app_service`'s `UPDATE` grant on `sessions` is now revoked outright with **no** column-level replacement, since no legitimate app-level update exists: `create_session`/`resolve_session` are `SECURITY DEFINER` and unaffected. The policy itself is left in place to keep row scoping for any future non-owner role. **Task 10 (logout) must use a `SECURITY DEFINER` function that only ever sets `revoked_at = now()`** — granting `UPDATE (revoked_at)` would hand back the un-revoke capability, because a column grant permits writing `NULL` just as readily as a timestamp.
  - `sessions_insert_blocked` — `WITH CHECK (false)`, always; the only sanctioned creation path is `create_session()`.
  - No `DELETE` policy yet — deferred until a cleanup-sweep job exists (which would need its own bootstrap-shaped answer, since a scheduled job has no `current_user_id` context either).
- **`user_invites`** — admin-only `FOR ALL` on the table. `created_by` now `DEFAULT NULLIF(current_setting('app.current_user_id', true), '')::uuid` — app no longer passes it explicitly.
- **`auth_configuration`** — plain admin-only `FOR ALL`, no bootstrap complexity (always queried by an already-authenticated admin).
- **`auth_audit_logs`** — `SELECT` admin-only; `INSERT` unconditional (`WITH CHECK (true)`) since the app must log events (e.g. a failed login) with no identity context at all. No `UPDATE`/`DELETE` policy for either table — combines with the append-only trigger for real belt-and-suspenders: for `app_service`, RLS filters to zero visible rows before the trigger even runs; for `neondb_owner` (bypasses RLS by ownership), the trigger is the only defense and does throw.

## Bootstrap `SECURITY DEFINER` functions

**Now five, not four** — a fifth was added 2026-07-29 for [[Phase 2 Progress]]'s task 4:

- **`resolve_bootstrap_registration(email citext) RETURNS TABLE (user_id, first_name, last_name)`** — matches only an `active`, non-deleted user with **zero** existing `webauthn_credentials` rows. Both conditions live in the function rather than in the calling handler deliberately: it is reached by an *unauthenticated* caller, so putting them here means an anonymous request cannot enumerate users and cannot register a passkey over an existing one regardless of application-layer bugs. Migration `20260729200000_bootstrap_registration_lookup`. Note its `SET search_path = auth, public` and fully-qualified `auth.users`/`auth.webauthn_credentials` references — see the schema-move callout in [[Database Schema]] for why unqualified names would fail at `CREATE FUNCTION` time now.

The original four, all owned by `neondb_owner`, `EXECUTE` revoked from `PUBLIC` and granted only to `app_service`. Their `SET search_path` was originally `public` (hardening against search-path hijacking) and was re-pointed to `auth, public` by the schema-move migration:

- **`create_session(user_id, token_hash, expires_at, ip, user_agent) RETURNS uuid`** — refuses to create a session for a user that isn't `status = 'active' AND deleted_at IS NULL`.
- **`resolve_session(token_hash) RETURNS TABLE (user_id, role)`** — does the token lookup and bumps `last_seen_at` in one round trip (`UPDATE ... RETURNING`); only matches a session that is unrevoked, unexpired, **and** whose owning user is still active/non-deleted — this is what makes deactivating a user immediately kill their existing sessions rather than waiting for natural expiry.
- **`resolve_invite(token_hash) RETURNS TABLE (invite_id, user_id)`** — read-only validation (unused, unexpired), safe to call repeatedly mid-registration.
- **`consume_invite(token_hash) RETURNS uuid`** — atomically marks the invite used **and** flips the user from `invited` to `active` in the same statement.

Mechanically this works because `neondb_owner` owns both the tables (exempt from RLS, no `FORCE ROW LEVEL SECURITY` set) and these functions — a `SECURITY DEFINER` function executes with its owner's privileges.

**Functional verification, not just structural**: direct `INSERT` as `app_service` rejected; `resolve_session` with the right hash returned correct `(user_id, role)` and bumped `last_seen_at`; wrong hash returned zero rows; after revoking, the same valid hash returned zero rows; after deactivating the owning user, resolution of their still-otherwise-valid session returned zero rows; owner/admin `SELECT` scoping showed 1 row for non-admin vs. all sessions for admin. One real bug caught mid-test: test data defaulted to `status = 'invited'`, correctly tripping `create_session`'s active-user guard — a bug in the test setup, not the function; worth remembering as a gotcha for future manual testing. `resolve_invite`/`consume_invite` similarly verified against wrong/already-consumed/expired tokens.

## Status: RLS pass complete across all seven tables, 2026-07-21

Every table has RLS enabled with policies matching the plan above, each functionally exercised via `SET ROLE app_service` + manually-set GUCs inside throwaway `BEGIN...ROLLBACK` blocks, test data cleaned up after each run.

## Password-policy question raised and resolved, 2026-07-21

Boris asked for a "password requirements" config (length, special characters, case, expiration, reuse history) scoped per group/role. Flagged rather than built: **OO's locked v1 architecture has no passwords at all** — passkeys are the primary factor, TOTP the fallback, specifically to avoid this whole category of problem. None of those fields have a real equivalent for a machine-generated passkey or unchosen TOTP secret. **Deferred entirely** — not building session-lifetime or lockout-threshold substitutes either, since nothing concrete needs them yet. Separately, the "per group/role" framing implied reversing the Groups/multi-role deferral — confirmed as a misstatement; the 2026-07-20 decision stands (single Admin role, no Groups table, until a real second role/department need shows up).

## Full live audit against this plan, 2026-07-21 (pre-Rust-wiring gate)

Before starting Rust wiring, a complete audit of the *actual* Neon dev branch state (not just the design doc) was performed — every table's columns, every enum's values, RLS-enabled flag per table, every policy, every index, every trigger, every function's `SECURITY DEFINER` flag and grants, `app_service`'s role attributes and table grants, the default-privileges rule, the seeded `auth_configuration` row. **Everything matched the documented plan exactly, with zero discrepancies** — all 13 policies present with correct commands, all FK-column indexes present, all 4 triggers on the right tables, all 4 bootstrap functions correctly scoped. `_sqlx_migrations` shows all 14 migrations applied in order, matching the two git commits exactly — no drift between committed and live state.

**One positive discovery**: `app_service`'s password is no longer NULL — already set via `\password app_service`. ~~Still outstanding~~ — **resolved 2026-07-29**: `.env.local`'s `DATABASE_URL` now holds the real password and the connection is live end-to-end (`psql "$DATABASE_URL" -c "select current_user;"` → `app_service`; running app's `GET /health/db` → `{"status":"ok","connected_as":"app_service"}`).

**Pooler saga, actually resolved 2026-07-29 — with a mid-session correction**

> [!warning] An earlier version of this note claimed the pooler was "confirmed clean at both levels". **That was wrong.** The `psql` half was genuine; the `GET /health/db` half was not — that "ok" came from an `unitprep-api` process still running the *DIRECT* URL (the restart either predated the `.env.local` save or didn't pick it up). Recorded here rather than quietly overwritten, because it is exactly the failure mode the [[Gotchas]] entry on stale-process verification describes: a passing check against the wrong process reads identically to a passing check against the right one.

The real story, in order:

1. The original pooled-connection failure was **not** the duplicate-`DATABASE_URL`-line bug. That line was a real, separate problem, and fixing it made `psql` work through the pooler — which is what created the false confidence.
2. The actual blocker was in `db.rs`: it set `options=[("search_path", "auth,public")]`, and **`search_path` travels in the Postgres startup packet, which Neon's pooler rejects** — `unsupported startup parameter in options: search_path`. Every query failed, `/health/db` included. Found only when the task-5 login endpoints were first exercised against the live database with the real binary.
3. Why it hid so well: the unit tests use an unreachable lazy pool and never execute SQL, and a *direct* connection accepts the parameter happily. So identical code worked or failed purely on which endpoint `DATABASE_URL` named, with no test able to tell.
4. **Fix**: drop the connection-level `search_path` entirely and schema-qualify every reference in application SQL (`auth.users`, `auth.resolve_session(...)`, and so on). Moving it to an `after_connect` `SET` would *not* work — the pooler is transaction-mode PgBouncer, so a session-level `SET` isn't reliably bound to the issuing client; it would appear fine under light load and start leaking or vanishing under concurrency, which is worse than failing.

**Now genuinely verified against the pooled endpoint**, by running the real binary and watching the real database: `/health/db` reports `app_service`; `register/begin` returns a real WebAuthn challenge and sets its ceremony cookie; `login/begin` returns byte-identical 401s for a credential-less real account and a nonexistent one; two `login_failed` rows landed in `auth_audit_logs`. The pooled host is the live `DATABASE_URL`, matching the original architectural intent.

**Three different `search_path` regimes are now in play, all deliberate** — worth knowing before touching any of them: *none* for the application (queries are qualified), `auth, public` pinned inside each `SECURITY DEFINER` function, and the owner role's own default (`"$user", public`) for migrations, which is why migrations must qualify too.

## Remaining open items, not yet resolved

- Whether unit-group/dedup tools need their own persisted working-session state at all (separate from this auth `sessions` table) — unconfirmed, ask before assuming either way.
- `totp_credentials.secret_encrypted` encryption-at-rest mechanism — deferred to when that table is actually populated.
- Whether `user_invites` gets the partial-unique "one outstanding invite per user" constraint — optional, not decided.
- Repeating the `app_service` role setup on the `prod` branch before go-live.

## See also

- [[Database Schema]] — the tables these policies protect.
- [[Phase 2 Progress]] — Rust-side consumption of `resolve_session`/`create_session` (tasks 2-3).
