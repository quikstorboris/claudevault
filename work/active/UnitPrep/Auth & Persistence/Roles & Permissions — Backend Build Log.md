---
date: 2026-08-06
description: "Event-log satellite for the roles/permissions backend build: task 1.1 (schema live on Neon dev) and tasks 1.2-1.4 (data-driven authorization core, grant/revoke role endpoints, THREAT_MODEL update), verbatim, chronological."
tags: [work-note, unitprep, event-log]
status: active
quarter: Q3-2026
project: unitprep
---

# Roles & Permissions — Backend Build Log

Event-log satellite for [[Roles & Permissions — Design Discussion]]. Continues from [[Roles & Permissions — Design Finalization Log]] once the 9-task breakdown was agreed. Covers the backend implementation of step 1: task 1.1 (roles/permissions schema, migrated live to Neon dev and functionally verified) and tasks 1.2-1.4 (data-driven authorization core, grant/revoke role endpoints, `THREAT_MODEL.md` update), both on 2026-08-06/07. Continued in [[Roles & Permissions — Frontend Build & Ship Log]]. Recovered from the vault's `inbox/` auto-filed notes 2026-08-10; moved here verbatim, nothing trimmed, in chronological order by each note's own `_Recorded ...Z_` timestamp.

## 2026-08-06 19:48 — Task 1.1 shipped: roles/permissions schema live on Neon dev, functionally verified

Built and ran the roles/permissions migration for UnitPrep's Onboarding Orchestrator auth work: two new migrations (`20260806120000_add_roles_permissions_tables`, `20260806130000_migrate_users_role_to_user_roles`) creating `auth.roles`/`permissions`/`role_permissions`/`user_roles`, seeding the 4 system roles + 8-permission catalog + `role_permissions` matrix from the session's capability-matrix discussion, migrating every existing user's single role into the join table, granting Boris's account both admin and onboarding_manager directly, and dropping `auth.users.role` + the `auth_role` enum. Applied to the real Neon dev branch and functionally verified with 10 test cases via psql as `app_service`. Scope grew beyond the original one-line task description once the real blast radius became clear while reading the actual codebase (not just the vault's stale description) — recorded here so that growth is visible, not buried.

**What changed**

- `migrations/20260806120000_add_roles_permissions_tables.{up,down}.sql` — new: `auth.roles`/`permissions`/`role_permissions`/`user_roles` tables, RLS on all four (catalog tables readable by any authenticated caller, mutation admin-only; `user_roles` owner-or-admin read, admin-only write with a `WITH CHECK` that structurally blocks self-grant/self-revoke even for admin), `auth.current_user_has_role(text)` helper (GUC-string check against a new `app.current_user_roles` session variable, not a live table query — continues the existing single-role design's own reasoning for avoiding self-referential subqueries in admin checks), and the seed data for 4 system roles + 8 permissions + the `role_permissions` matrix.
- `migrations/20260806130000_migrate_users_role_to_user_roles.{up,down}.sql` — the cutover: rewires all 8 existing admin-check RLS policies (`auth.users` x3, `auth.sessions` x2, `auth.user_invites`, `auth.auth_configuration`, `auth.auth_audit_logs`) and 3 SECURITY DEFINER functions (`resolve_session`, `list_users_for_admin`, `set_user_status`) from the old single-role GUC to the new helper; widens `resolve_session` and `list_users_for_admin` to return `role_keys TEXT[]` instead of a single role column; drops the now-superseded `set_user_role` function; migrates every existing user's `auth.users.role` value into `auth.user_roles`; grants Boris's account (bmaksimov@quikstor.com) `onboarding_manager` directly in the same migration (the sanctioned bootstrap route around the self-role-edit-absolute rule, since the migration runs as table owner and bypasses RLS); drops `auth.users.role` and the `auth.auth_role` enum. Down-migration reverses all of it, documented as lossy for any user who ends up holding more than one role (collapses back to a single value, preferring admin).
- Discovered while reading the real Rust source (not assumed from the vault): `resolve_session` already takes 2 params and returns 4 columns (idle-timeout + step-up fields added since the vault's RLS Implementation note was written), and 3 more functions/8 more policies reference the single-role GUC than the vault's stale description suggested. Scoped the migration against the actual current schema, not the documented one.

**Decisions**

- `app.current_user_roles` (plural) replaces `app.current_user_role` as a comma-joined list of role keys, set once per request by the middleware (Rust side still pending, task 1.2). Chose a GUC-string check over a live query against `user_roles`/`roles` specifically to preserve the original design's stated reason for avoiding self-referential subqueries in admin checks — generalizing the existing pattern rather than replacing it with a different one.
- Permission catalog content is my best-effort translation of the session's capability matrix into concrete keys — flagged two assumptions inline in the migration's own comments rather than silently deciding: `district_manager` gets `client_credentials.add` directly (not just approve), inferred from "OM not allowed: elevated privileges of DM's" rather than something Boris stated explicitly; sales gets zero permissions for now. Both are a data UPDATE away from correct if wrong, not a migration.
- Split into two migrations rather than one: the first (new tables + seed data) is purely additive and safe to run standalone; the second (rewiring existing policies/functions, dropping the old column) is the actual behavior-changing cutover. Made the blast radius of the change visible in the migration history itself rather than one large diff.

**Learned**

- Verified functionally against the real Neon dev branch as `app_service` (10 test cases, run inside `BEGIN...ROLLBACK` so nothing persisted): `current_user_has_role` resolves correctly for a multi-role caller (admin=true, onboarding_manager=true, district_manager=false for Boris); catalog tables (roles/permissions) are readable by any authenticated caller; `list_users_for_admin` returns `role_keys` arrays for admin and is refused for non-admin (raised the exact expected error text); a non-admin sees exactly their own 1 `user_roles` row, not others'; admin CAN grant a role to someone else (INSERT succeeded, 1 row) but CANNOT grant/revoke a role on their own account — the self-grant attempt was refused by Postgres itself ("new row violates row-level security policy for table user_roles"), not just by an app-layer check; `is_system` correctly blocks role deletion even for an admin caller (DELETE 0 rows on both a non-admin trying to delete 'admin' and an admin trying to delete 'sales').
- The known applies-doubly-here gotcha (`SET ROLE` from `neondb_owner` fails on Neon since the owner isn't a member of `app_service`) held again — used the real `app_service` connection string (`NEON_DEV_DATABASE_URL_APP`) directly for functional testing instead, per the RLS Implementation note's own prior discovery of this.
- The `.env.local` values are double-quote-wrapped (`NEON_DEV_DATABASE_URL_DIRECT="postgresql://..."`), which the WSL Execution Technique note's documented grep|cut extraction pattern doesn't strip — caused "relative URL without a base" from sqlx until a trailing `sed 's/^"//; s/"$//'` was added. Worth amending that reference note's extraction snippet.

**Verification**

Ran both migrations against the real Neon dev branch via `sqlx migrate run` (`sqlx migrate info` confirmed clean apply, both show `/installed` afterward). Structural check via psql as the owner role confirmed: 4 roles, 8 permissions, correct `role_permissions` mapping, all 4 existing users (including Boris) correctly migrated into `user_roles` with Boris holding both admin and onboarding_manager, `auth.users.role` column gone, `auth.auth_role` type gone. Functional check via psql as the real `app_service` role (10 cases inside `BEGIN...ROLLBACK`, detailed above) confirmed the helper function, RLS visibility scoping, admin-gated functions, and the self-role-edit-absolute backstop all behave exactly as designed under real RLS enforcement, not just in the abstract.

**Open**

- The running unitprep-api binary cannot authenticate anyone right now — `resolve_session`'s shape changed (`role_keys` array, not a single role column) and the GUC name changed (`app.current_user_roles`, not `app.current_user_role`), but the Rust middleware hasn't been updated to match yet. Expected and accepted (single dev-only user, no zero-downtime need), but real until task 1.2 (backend authorization core) lands — that's the immediate next piece, not a separate concern to schedule later.
- Task 1.3's role-management endpoints need to replace the dropped `auth.set_user_role` with real grant/revoke functions against `auth.user_roles` (mirroring the same admin-check-plus-self-edit-guard shape already proven here at the RLS layer).
- Permission catalog content (district_manager's exact grant, sales's empty set) should be treated as provisional until Boris explicitly confirms — flagged inline in the migration, not yet separately confirmed in conversation.

**Related (as recorded)**

- Roles work (#1) broken into 9 build tasks; full remaining roadmap recorded before implementation starts _(no note yet)_
- [[Database Schema]]
- [[RLS Implementation]]
- [[WSL Execution Technique]]

## 2026-08-07 15:48 — Tasks 1.2-1.4 shipped: data-driven authorization core, grant/revoke role endpoints, THREAT_MODEL updated

Completed the backend half of the roles/permissions work in one continuous pass: retrofitted every existing admin-gated endpoint from hardcoded Role-enum matching to data-driven permission checks, replaced the single-role `change_user_role` endpoint with real grant/revoke endpoints operating on the new `user_roles` table, and updated `THREAT_MODEL.md` to reflect what closed and what changed shape. Scope grew further than 1.2's own description once dependencies became concrete: fixing `resolve_session` required a 4th same-day migration, and every user-creation path (bootstrap CLI, invite issuance) needed its own INSERT split into two statements since `users.role` no longer exists. Verified with a full build, full test suite, clippy in strict mode, and a live server run against the real Neon dev database — not just unit tests.

**What changed**

- `migrations/20260806150000`-equivalent (actual filename: `resolve_session` extended in place via a new migration) — `resolve_session` gained a 6th/5th shape change: now also returns `permission_keys TEXT[]` alongside `role_keys`, computed via a second `array_agg` subquery joining `user_roles`→`role_permissions` in the same query. This is what makes `AuthenticatedUser.has_permission()` a `HashSet` lookup with zero extra DB round trips per request, rather than a live query per permission check.
- `src/auth/authenticated_user.rs` — full rewrite: removed the `Role` enum entirely (roles are data now, hardcoding them in Rust contradicted the whole point); `AuthenticatedUser` gained `role_keys: Vec<String>` and `permission_keys: HashSet<String>`, both resolved once per request from `resolve_session`; added `has_permission()`/`require_permission()` (the latter checks a permission, records an `AUTHORIZATION_FAILURE` audit row on failure, and returns the shared 403 — replaces an identical match-block that was duplicated 11 times across 5 files); `begin_rls_transaction` now takes `role_keys: &[String]` and sets a new `app.current_user_roles` GUC (comma-joined) instead of the old singular `app.current_user_role`.
- `src/auth/roles.rs` — new module: `resolve_role_id` (validates a client-supplied role key against real data) and `role_keys_for_user` (full current role set for a user, used for audit before/after state and duplicate-grant/revoke checks).
- `src/api/auth_user_role.rs` — full rewrite: the old single-value `change_user_role` (backed by the now-deleted `auth.set_user_role` SECURITY DEFINER function) replaced by `grant_role`/`revoke_role`, operating as plain INSERT/DELETE on `auth.user_roles` inside `begin_rls_transaction` — no SECURITY DEFINER function needed at all, since `user_roles`' own RLS policies (admin-only, self-grant/self-revoke structurally blocked) are the real enforcement. `revoke_role` re-implements the last-remaining-admin guard against a role_id count instead of the old role column. New routes: `POST /auth/users/{id}/roles` (grant), `DELETE /auth/users/{id}/roles/{role_key}` (revoke), replacing `POST /auth/users/{id}/role`.
- `src/api/auth_users.rs`, `auth_user_status.rs`, `auth_invites.rs`, `auth_audit_logs.rs` — every admin-gated handler's `match admin.role` block replaced with `admin.require_permission(...)` calls against the real permission catalog (`users.manage`, `users.manage_roles`, `audit_logs.read`). `auth_user_status.rs`'s deactivate-user last-admin check and `auth_invites.rs`'s user-creation/reissue paths rewritten against `user_roles` instead of the dropped `users.role` column — new-user creation is now two statements (INSERT users, then INSERT user_roles) instead of one; a reissue "replaces" role by deleting then re-inserting rather than UPDATE-ing a column.
- `src/bootstrap.rs` — the first-admin CLI's INSERT split the same way: creates the user row, then grants admin via a second INSERT into `user_roles` with `granted_by` left NULL (no administrator exists yet to attribute it to, same reasoning `user_invites.created_by` already used).
- `src/api/mod.rs` — router updated for the new grant/revoke routes; whoami's response changed from a single `role: &'static str` to `roles: Vec<String>`.
- `src/api/test_support.rs` — added shared `admin_user()`/`onboarding_manager_user()` fixtures (carrying real `permission_keys` matching the seeded matrix), replacing 6 near-identical local `admin()`/`onboarding_manager()` helpers scattered across test modules.
- `THREAT_MODEL.md` — closed the "onboarding_manager has no permissions" gap (struck through, dated). Corrected a now-inaccurate claim in the "no automated check" gap: the exhaustive-match compiler backstop it described no longer exists at all now that roles are data, not a closed enum — documented honestly as a slightly different (not automatically worse, but not compiler-caught either) shape of the same gap, rather than left stale.

**Decisions**

- No SECURITY DEFINER function needed for grant/revoke, unlike the old `set_user_role` — `auth.user_roles` has normal table grants (via the existing `ALTER DEFAULT PRIVILEGES` rule) and its own correct RLS policies, so a plain RLS-scoped INSERT/DELETE is sufficient and was already proven correct in task 1.1's functional verification. Simpler than the pattern it replaces.
- Role-key validity moved from a pre-transaction Rust-enum check to a database lookup inside the transaction (`resolve_role_id`) — roles are open-ended data now, so there is no closed set to validate against in Rust. This cost the "a typo never touches the database" property for role validation specifically (documented and the affected test updated to expect a DB round trip); every other input field keeps that property unchanged.
- Test fixtures needing a specific `AuthenticatedUser` (admin/onboarding_manager) now live once in `test_support.rs` with real `permission_keys` mirroring the seeded catalog, rather than duplicated per file — removed 6 identical local helper functions across `auth_user_role.rs`, `auth_users.rs`, `auth_user_status.rs`, `auth_invites.rs`, `auth_audit_logs.rs`, `auth_totp.rs`'s inline literals.

**Learned**

- The blast radius was larger than the task list assumed going in: `resolve_session`, `list_users_for_admin`, and 8 RLS policies across 5 tables all referenced the single-role GUC/column and needed rewiring (found by reading the actual current migrations, not trusting the vault's already-stale description of `resolve_session`'s shape). `auth_invites.rs`'s user-creation path, `bootstrap.rs`'s first-admin creation, and `auth_user_status.rs`'s last-admin-guard raw SQL all directly referenced the now-dropped `users.role` column and needed real logic changes, not just import fixes — these weren't visible from the task's one-line description and only surfaced by grepping for every reference to the dropped column/type before writing anything.
- sqlx's lifetime elision breaks silently once a function gains a second reference parameter alongside the one whose lifetime should flow into the return type — `begin_rls_transaction` needed an explicit named lifetime (`<'a>` tying `pool` and the return type together) the moment `role_keys: &[String]` was added alongside `pool: &PgPool`, which is a real, easy-to-hit Rust rule, not a project-specific gotcha, but worth remembering here since it was the only genuine compile error out of the whole rewrite.

**Verification**

`cargo check --workspace --all-targets`: clean, zero warnings. `cargo test --workspace`: 296 passed / 0 failed / 1 ignored in the main binary, plus 46+57+71 passing across the three library crates — zero failures anywhere. `cargo clippy --workspace --all-targets -- -D warnings`: clean. Live run against the real Neon dev database: started the actual server, confirmed `/health` and `/health/db` (`connected_as: app_service`), confirmed `/health/whoami`, `/auth/users`, and the brand-new `POST /auth/users/{id}/roles` all correctly return 401 with no session cookie — proving the new 5-column `resolve_session` call and the new route wiring both work end-to-end against live infrastructure, not just against a lazy test pool.

**Open**

- Permission catalog content (department_manager's exact grants, sales's empty set) is still the same provisional best-effort guess flagged back in task 1.1 — unchanged by this work, still worth Boris's explicit confirmation whenever convenient.
- Task 1.3's originally-scoped "role-management endpoints" is now fully done (grant/revoke + audit), but the frontend that will call them (tasks 1.6/1.7) doesn't exist yet.
- No integration test enumerates every route against its expected required permission — flagged honestly in `THREAT_MODEL.md` as an open gap, not built.

**Related (as recorded)**

- Task 1.1 shipped: roles/permissions schema live on Neon dev, functionally verified _(no note yet)_
- Roles work (#1) broken into 9 build tasks; full remaining roadmap recorded before implementation starts _(no note yet)_

## Related

- [[Roles & Permissions — Design Finalization Log]] — the design discussion this backend build implements
- [[Roles & Permissions — Frontend Build & Ship Log]] — continues with the frontend build and the commit/push that closed step 1
- [[Roles & Permissions — Design Discussion]] — the core note this satellite provides first-hand build detail for
- [[Auth & Persistence Index]]
- [[Database Schema]]
- [[RLS Implementation]]
