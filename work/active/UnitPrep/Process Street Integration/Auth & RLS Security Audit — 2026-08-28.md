---
date: 2026-08-28
description: "Full auth/RLS backdoor audit of unitprep-api, triggered by building field-level PII encryption for the Process Street integration. Clean result: no backdoors, one historical fail-closed bug already self-fixed."
tags: [work-note, unitprep, process-street, security]
status: completed
quarter: Q3-2026
project: unitprep
---

# Auth & RLS Security Audit — 2026-08-28

Triggered by [[Client & Facility Schema (Process Street-Sourced)]]'s field-level encryption work — Boris asked directly: "let me know if any part of our infrastructure is lacking in these terms. I believe auth is solid, but I don't want any back doors." Run as an independent background investigation (read-only: grep across all migrations/`src/`, and read-only `SELECT` queries against the real dev database — no code or data changed by the audit itself).

## Scope checked

1. **Postgres role privileges** — does `app_service` (the role the running app connects as) have `BYPASSRLS` or `SUPERUSER`? Either would silently defeat every RLS policy in the codebase.
2. **Hardcoded/fallback secrets** — any encryption key loader that falls back to a default instead of erroring when the env var is missing.
3. **Auth bypass flags** — debug headers, env-gated skip-auth paths, anything resembling a backdoor.
4. **The "temporary admin+OM permission gate for testing credential-add"** — a deliberately temporary broadening mentioned in earlier session history — was it ever reverted?
5. **RLS policy soundness** — any policy trivially `USING (true)` outside genuinely public reference data; any table with RLS enabled but no policy for some command; any migration that disables RLS outside a `.down.sql`.
6. **Session/token security** — real CSPRNG, hash-not-plaintext storage, actual enforcement of expiry/revocation.
7. **`SECURITY DEFINER` functions** — each one checked for its own explicit permission check in the function body (a bug class: a caller-privileged `SECURITY DEFINER` function with a missing/wrong internal check is a real privilege-escalation vector).
8. **Column-level grants on `auth.users`** — confirming `role`/`status`/`deleted_at` stay walled off from direct `UPDATE` at the current, latest migration state (not just at the migration that first restricted it).

## Result: clean

- **#1 — clean, verified against the real dev DB, not just the SQL script**: `app_service` has `rolsuper=false, rolbypassrls=false`. (`neondb_owner`, the table owner, does have `rolbypassrls=true` — expected, it's never the role the running app connects as.)
- **#2 — clean**: both `auth::totp::load_key` and `clients::encryption`'s key loader return a `NotConfigured` error on a missing/malformed key; no fallback value anywhere. Same fail-closed pattern in `dropbox::config`.
- **#3 — clean**: no bypass/skip-auth/debug-header pattern found anywhere in `src/`.
- **#4 — resolved, not lingering**: current effective grants (confirmed by chronological grep of every `INSERT INTO auth.role_permissions`) show `client_credentials.add`/`.revoke` on `onboarding_manager` + `department_manager` only, `.approve` on `department_manager` only, `admin` holding none of the three — matches the intended final scoping.
- **#5 — clean, with two intentional exceptions**: two `WITH CHECK (true)` policies exist, both INSERT-only on append-only audit-log tables with SELECT separately role-gated — a deliberate, narrow pattern, not a broad hole. No RLS ever disabled outside a `.down.sql`.
- **#6 — clean**: tokens from the OS CSPRNG, only a SHA-256 hash persisted, cookies `HttpOnly`/`Secure`/`SameSite=Strict`, and `auth.resolve_session` enforces revocation/expiry/idle-timeout/account-status on every call.
- **#7 — one real bug found, already fixed weeks earlier in the same effort that introduced it**: `auth.set_user_role`/`auth.set_user_status` originally checked a singular GUC name (`app.current_user_role`) while the actual app code only ever sets the plural, comma-joined `app.current_user_roles` — meaning the check always evaluated false. This is a **fail-closed** bug (legitimate admin calls got wrongly rejected, not unauthorized calls wrongly allowed), and migration `20260806130000_migrate_users_role_to_user_roles` already corrected it. Confirmed no migration since reintroduces the singular form.
- **#8 — clean**: only one migration ever grants `UPDATE` on `auth.users`, explicitly column-scoped to `first_name`/`last_name`/`job_title`; no later migration widens it; moot as a `role`-column risk since `role` was later moved off `auth.users` entirely into the RLS-protected `auth.user_roles` join table.

## Verdict

Audit-passing-grade as of this date. Nothing resembling a backdoor, hardcoded secret, or auth bypass exists anywhere checked. The one real issue found was already caught and fixed by Boris's own earlier work, and it was never exploitable (fail-closed, not fail-open). One hygiene suggestion, not a fix: a small CI check that greps for `current_setting('app.current_user_role'` (singular) reappearing in any future migration, since the typo is easy to reintroduce and bit the codebase once already.

## Related

- [[Client & Facility Schema (Process Street-Sourced)]] — the encryption work that triggered this audit
- [[Process Street Integration — Kickoff & Findings]]
- [[Gotchas]] — general standing security/gotcha notes for this project
