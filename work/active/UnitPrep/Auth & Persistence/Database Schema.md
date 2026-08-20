---
date: 2026-07-27
description: "OO auth database schema (v1, Admin-only): 7 tables, columns, FKs, RLS approach per table, naming/indexing conventions. Built + migrated on Neon dev 2026-07-21."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — Database Schema

Table-by-table schema design finalized 2026-07-21, following [[Architecture]]. All seven tables below are migrated and verified on the Neon `dev` branch (via `sqlx migrate add -r` + `sqlx migrate run`, one table per migration). RLS policies, bootstrap functions, and full verification detail live in the companion note [[RLS Implementation]]. Rust wiring (`sqlx`/`dotenvy` into `unitprep-api`'s `main.rs`) is still pending — nothing in the running app touches these tables yet beyond the Phase 2 work tracked in [[Phase 2 Progress]].

> [!important] Every object below lives in a dedicated `auth` schema, not `public` — discovered undocumented 2026-07-29
> Migration `20260723150000_move_auth_objects_to_auth_schema` (dated 2026-07-23, **never recorded in this vault until now**) moved all 7 tables, all 4 enums, and all 6 functions into their own `auth` schema, leaving `public` for `_sqlx_migrations` and future non-auth domains. `db.rs` sets `search_path = auth,public` on every application connection, so unqualified names in application queries (`users`, `resolve_session`) still resolve normally.
>
> **Two consequences that have already bitten:**
> 1. The owner/migration connection's default `search_path` is `"$user", public` and does **not** include `auth` — verified live 2026-07-29 (`SELECT count(*) FROM users` → *relation does not exist*). Any new migration or manual `psql` work must schema-qualify explicitly (`auth.users`) or set the path first. The pre-move migrations in git history are unqualified and only worked because the tables were in `public` at the time.
> 2. Table-level grants survive a schema move, but schema-level `USAGE` does not — `scripts/setup_app_service_role.sql` was re-run 2026-07-23 to add `GRANT USAGE ON SCHEMA auth`. Repeat that on `prod` too, not just the `public` grants.
>
> The table/column designs described below are all still accurate; only their schema qualification changed.

> [!important] Stale as of 2026-08-08 — roles/permissions became real tables, and a second schema now exists
> A roles/permissions refactor shipped 2026-08-06/07 in a session that never recorded it here — caught 2026-08-08 while adding unrelated `client_ops` work and reading the real migrations directly. Two corrections:
>
> 1. **`users.role` (the `auth_role` enum) no longer exists.** Dropped once nothing referenced it. Role is now many-to-many: `auth.roles`, `auth.permissions`, `auth.role_permissions`, `auth.user_roles` — four real roles today (`admin`, `onboarding_manager`, `department_manager`, `sales`), a growing permission-key catalog, a user can hold more than one role. See [[Roles & Permissions — Design Discussion]] (also corrected 2026-08-08) rather than this note for current detail — not re-documented here to avoid a second copy going stale the same way.
> 2. **`client_ops` is a second schema, alongside `auth`.** First non-auth domain — see the vault's `QMS API` note set (`QMS Template Tags — Catalog & Editor Design` and siblings) for what's in it so far (`qms_tag`, `audit_log`).
>
> Everything else below (the seven original `auth` tables) is still accurate.

## Conventions locked in

- Postgres-native naming: snake_case, plural table names.
- UUID PKs almost everywhere, via native `uuidv7()` (Neon dev runs Postgres 18.4, which has it built in — no extension needed). Every UUID-PK column: `DEFAULT uuidv7()`.
  - Exception: `auth_audit_logs.id` is `bigint GENERATED ALWAYS AS IDENTITY`, not UUID — pure sequential-insert, never externally referenced, benefits from insert locality more than opacity.
- `TIMESTAMPTZ` everywhere, never bare `TIMESTAMP`.
- `email` as `citext` (needs `CREATE EXTENSION citext`) to avoid case-sensitivity bugs in the unique constraint.
- Enum vs. text rule of thumb: small/stable/rarely-added-to sets (`role`, `company`, `status`, `deletion_reason`) → Postgres enum. Frequently-expanding open sets (`event_type` in the audit log) → `text`, validated in Rust, to avoid `ALTER TYPE ADD VALUE` friction on a table that grows new categories often.
- `updated_at` auto-update trigger (`set_updated_at()`, written once, attached per table) only applies to `users` and `auth_configuration` — credential/session tables use event-driven `last_used_at`/`last_seen_at` set explicitly by app logic instead.
- sqlx/Rust mapping: `Uuid`, `chrono::DateTime<Utc>` (or `time::OffsetDateTime` — pick one, use everywhere), `Vec<u8>` for `bytea`, `Vec<String>` for `text[]`, `ipnetwork::IpNetwork` for `inet` (enable the `ipnetwork` sqlx feature rather than storing IPs as text), `sqlx::types::Json<T>` wrapping concrete Rust structs for `jsonb`. Postgres enums map to Rust enums via `#[derive(sqlx::Type)]`.

## `users`

- `id` UUID PK
- `email` citext UNIQUE NOT NULL
- `first_name`, `last_name` text NOT NULL — no combined `display_name` column; derive full name at render time to avoid a driftable duplicate field.
- `job_title` text NULL — named `job_title`, not `title`, to avoid visual collision with the `role` enum.
- `company` enum (`trojan`, `cobre`, `quikstor`) NOT NULL — extensible via `ALTER TYPE ... ADD VALUE`.
- ~~`role` `auth_role` enum NOT NULL DEFAULT 'admin'~~ — **dropped 2026-08-06/07**, see the correction callout above. Role is now `auth.user_roles`, many-to-many, not a column here at all.
- `status` enum (`invited`, `active`, `deactivated`) NOT NULL DEFAULT 'invited'
- `deleted_at` TIMESTAMPTZ NULL — soft delete, supports the future "restorable vault" idea from [[Architecture]].
- `deletion_reason` enum (`offboarding`, `emergency`) NULL — one timestamp + one categorical reason, not two parallel nullable timestamps. Forensic detail for an emergency deletion belongs in `auth_audit_logs`, not duplicated here. **Recommended invariant**: `CHECK ((deleted_at IS NULL) = (deletion_reason IS NULL))`.
- `created_at`, `updated_at` TIMESTAMPTZ NOT NULL DEFAULT now()

## `webauthn_credentials`

**Corrected 2026-07-21, during Phase 2 skeleton work**: originally designed with separate `public_key bytea` + `sign_count bigint`, decomposed by hand. Checking webauthn-rs's actual API showed this doesn't match how the library wants credentials persisted — its `Passkey` type is `Serialize`/`Deserialize` and meant to be stored as one opaque blob; there's no public constructor to rebuild it from separate parts, and `update_credential()` operates on the whole deserialized struct. Fixed via migration `fix_webauthn_credentials_storage` before any registration/login code was written against the wrong shape.

- `id` UUID PK
- `user_id` UUID, FK → `users(id)` ON DELETE CASCADE — needs an explicit index (Postgres doesn't auto-index FK columns).
- `credential_id` bytea UNIQUE NOT NULL — extracted via `Passkey::cred_id()`, its own column purely for fast lookup.
- `passkey_data` jsonb NOT NULL — replaces `public_key`/`sign_count`; the whole serialized `Passkey` struct, opaque to us. Sensitive — admin's "enrolled factor visibility" view must project this out, never expose raw.
- `transports` text[] — captured separately at registration time, not part of the Passkey blob.
- `device_bound` boolean NOT NULL DEFAULT true — **the default is a trap and is no longer relied on.** Until 2026-07-29 nothing ever wrote this column, so every row asserted `true` (cannot leave its hardware) regardless of the credential it described; the first real Windows Hello passkey was `backup_eligible` — i.e. synced — while its row said otherwise. Registration now writes it explicitly as `NOT backup_eligible`, read via webauthn-rs's `From<Passkey> for Credential` conversion. **Informational only** — nothing refuses a credential on it, see the reversed requirement in [[Architecture]].
- `nickname` text NULL
- `created_at`, `last_used_at` TIMESTAMPTZ

RLS: owner-scoped; admin reads through a view excluding `passkey_data`/`credential_id`.

## `totp_credentials`

- `id` UUID PK
- `user_id` UUID UNIQUE NOT NULL, FK → `users(id)` ON DELETE CASCADE
- `secret_encrypted` bytea NOT NULL — **encryption-at-rest mechanism deliberately not decided yet**; revisit when this table is actually built, per the KMS-deferred stance in [[Architecture]] (may need a minimal app-level-key stopgap before real KMS, since a TOTP secret is real from the moment it's created).
- `confirmed_at` TIMESTAMPTZ NULL — null until first successful verification
- `created_at`, `last_used_at` TIMESTAMPTZ

RLS: owner-only, never exposed to admin (only the derived boolean "is TOTP enrolled" is admin-visible).

## `sessions`

Login/auth sessions only — deliberately not a general "user activity session" concept. (Open question, unresolved: whether unit-group/dedup tools persist any per-user state server-side today, or if everything is ephemeral/client-side — worth confirming before assuming a table is or isn't needed there.)

- `id` UUID PK
- `token_hash` bytea UNIQUE NOT NULL — raw opaque token never stored, only its hash.
- `user_id` UUID, FK → `users(id)` ON DELETE CASCADE — needs an explicit index.
- `created_at`, `expires_at`, `last_seen_at` TIMESTAMPTZ
- `revoked_at` TIMESTAMPTZ NULL — distinguishes explicit "sign out everywhere" from natural expiry.
- `ip_address` inet NULL, `user_agent` text NULL
- Recommended: partial index on `expires_at WHERE revoked_at IS NULL`, for a future cleanup sweep job.

RLS approach here needs bootstrap functions since the middleware resolves `token_hash` → session before any per-user context exists — see [[RLS Implementation]] for `resolve_session()`/`create_session()`.

## `user_invites`

- `id` UUID PK
- `user_id` UUID, FK → `users(id)` ON DELETE CASCADE — needs an explicit index.
- `token_hash` bytea UNIQUE NOT NULL
- `created_by` UUID, FK → `users(id)` ON DELETE SET NULL, NULLABLE — nullable specifically for the bootstrap first-admin case.
- `expires_at` TIMESTAMPTZ NOT NULL, `used_at` TIMESTAMPTZ NULL
- `created_at` TIMESTAMPTZ
- Optional, not yet decided: partial unique index on `user_id WHERE used_at IS NULL` to prevent multiple simultaneously-outstanding invites per user.

RLS: admin-only; the setup-link endpoint is necessarily unauthenticated and verifies the raw token against `token_hash` directly.

## `auth_configuration`

Singleton table: `id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1)`.

- `mandatory_passkey_enrollment` boolean NOT NULL DEFAULT true — renamed from originally-proposed `mandatory_2fa` deliberately: passkey and TOTP aren't parallel/stackable requirements (passkey is primary and already inherently multi-factor; TOTP is a fallback, not a second mandatory layer).
- `allowed_factors` jsonb NOT NULL DEFAULT '["webauthn"]' — governs which fallback factors (currently just `totp`) are permitted.
- `step_up_actions` jsonb NOT NULL DEFAULT '[]'
- `updated_at` TIMESTAMPTZ, `updated_by` UUID FK → `users(id)` ON DELETE SET NULL

RLS: admin read/write only.

## `auth_audit_logs`

- `id` bigint GENERATED ALWAYS AS IDENTITY PK
- `event_type` text NOT NULL — not an enum, deliberately (see conventions above)
- `actor_user_id` UUID NULL, FK → `users(id)` ON DELETE SET NULL — needs an explicit index; nullable because a failed login with a bad email has no real user row.
- `target_user_id` UUID NULL, FK → `users(id)` ON DELETE SET NULL — needs an explicit index; for admin-acting-on-another-user events.
- `metadata` jsonb NOT NULL DEFAULT '{}' — general event context that isn't a value change.
- `before_state` jsonb NULL, `after_state` jsonb NULL — for change-type events (`role_changed`, `auth_configuration_updated`, `user_deactivated`), structured old/new values as separate columns rather than buried in `metadata` — queryable/diffable "what changed, from what, to what." Most event types leave both null.
- `ip_address` inet NULL, `user_agent` text NULL
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT now() — needs an index, the audit viewer's primary time-range access pattern.

RLS: admin read-only. Also revoke `UPDATE`/`DELETE` grants entirely (plus a trigger that raises on either) — an audit log editable after the fact isn't an audit log.

## GIN indexing on JSONB columns — explicitly deferred, with a trigger to revisit

No GIN index on any JSONB column for now (`auth_audit_logs.metadata`/`before_state`/`after_state`, `auth_configuration.allowed_factors`/`step_up_actions`). None currently have a query pattern that searches *into* the JSON across many rows.

**Revisit condition**: the first time a real feature needs to search/filter *inside* a JSONB column across many rows (e.g. a compliance export tool, or an admin search box querying `before_state`/`after_state`) — that's the trigger to add a GIN index on the specific column, not before.

## See also

- [[RLS Implementation]] — RLS policies, bootstrap functions (`create_session`, `resolve_session`, `resolve_invite`, `consume_invite`), functional verification, and the full pre-Rust-wiring audit.
- [[Architecture]] — the design decisions this schema implements.
- [[Phase 2 Progress]] — Rust code being wired up against these tables.
