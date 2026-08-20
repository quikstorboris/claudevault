---
date: 2026-08-07
description: "Event-log satellite for the roles/permissions frontend build (tasks 5-9, plus fixing frontend breakage the backend rewrite caused) and the commit/push that closed step 1 as unitprep-api v1.6.0 / unitprep-ui v1.4.0, verbatim, chronological."
tags: [work-note, unitprep, event-log]
status: active
quarter: Q3-2026
project: unitprep
---

# Roles & Permissions — Frontend Build & Ship Log

Event-log satellite for [[Roles & Permissions — Design Discussion]]. Continues from [[Roles & Permissions — Backend Build Log]]. Covers the frontend implementation (tasks 5-9, plus fixing frontend breakage the backend rewrite caused) and the final commit/push that closed out step 1 as unitprep-api v1.6.0 / unitprep-ui v1.4.0, both on 2026-08-07. Recovered from the vault's `inbox/` auto-filed notes 2026-08-10; moved here verbatim, nothing trimmed, in chronological order by each note's own `_Recorded ...Z_` timestamp.

## 2026-08-07 16:51 — Roles frontend (tasks 5-9) shipped; also fixed frontend breakage from the backend authorization rewrite

Completed the frontend half of the roles/permissions work, closing out step 1 of the build order entirely (backend + frontend). Discovered along the way that unitprep-ui already had admin Users and Audit Logs pages from an earlier session neither Boris nor this session's earlier turns knew were live, and that today's backend rewrite had broken them (`WhoAmI.role`/`UserSummary.role` became `roles` arrays, `changeUserRole` endpoint no longer exists). Fixed that breakage as part of the same pass, then added the two new pages (Roles, Security Policies) and two small backend endpoints that didn't exist yet. Verified via full TypeScript type-check and lint; full interactive browser verification was blocked by a known, already-documented environment issue (Turbopack/Watchpack over the WSL-UNC bridge), not by anything in the code changes themselves.

**What changed**

- unitprep-api: migration `add_security_policies_permission` (new permission key, granted to admin) + `AUTH_CONFIGURATION_UPDATED` audit event. New `src/api/auth_roles.rs` (`GET /auth/roles`, any authenticated caller, one query with `array_agg` per role — no permission gate, matching the RLS catalog-tables-are-readable-by-anyone intent). New `src/api/auth_configuration.rs` (`GET`/`PUT /auth/configuration`, gated by the new `security_policies.manage` permission) — deliberately scoped to `step_up_actions` only: discovered while building this that `auth.auth_configuration.allowed_factors` exists in the schema but is read by zero code paths anywhere, so a UI control for it would edit a value with no effect on real behavior — left out and flagged rather than built as decoration. Session-length/passkey-count-limit policies have no backing columns at all and aren't part of this work either. whoami's response gained `permissions: Vec<String>` alongside the existing `roles`.
- unitprep-ui: found and fixed real breakage the backend rewrite caused in already-existing admin pages (`admin/users`, `admin/audit-logs`) that this session didn't know existed until reading the actual repo — `WhoAmI.role`/`UserSummary.role` (singular) became `roles: string[]`, the `changeUserRole` endpoint it called no longer exists. `lib/auth.ts`: `Role` type widened from a closed union to `string` (roles are data now), added `permissions` to `WhoAmI` + a `hasPermission()` helper, added `listRoles()`/`getAuthConfiguration()`/`updateAuthConfiguration()`, replaced `changeUserRole` with `grantRole`/`revokeRole` hitting the new endpoints. `components/auth/RequireAdmin.tsx` replaced with `RequirePermission.tsx` (checks a permission prop via `hasPermission`, not a hardcoded role-name comparison) across all 5 admin pages. `LeftNav.tsx` restructured: Users/Roles/Audit Logs/Security Policies grouped under an "Administration" heading, each individually gated by its own permission rather than one blanket `adminOnly` flag; footer now shows every held role, joined. `admin/users/page.tsx`: single role `<select>` replaced with per-user role chips (each removable via its own × unless it's the caller's own row, which hides remove controls entirely rather than showing them disabled) plus a per-row "add role" picker sourced from the live `GET /auth/roles` catalog instead of a hardcoded `VALID_ROLES` constant. `admin/audit-logs/page.tsx`: added category-preset tab buttons (All/Authentication/Permissions & Roles/Users & Access) layered on top of the existing `EventTypeMultiSelect` rather than replacing it — clicking a tab just presets the selection, fine-tuning still available. New pages: `admin/roles/page.tsx` (read-only capability matrix from `GET /auth/roles`, gated on `users.manage_roles` since it has no write actions of its own), `admin/security-policies/page.tsx` (step-up-actions checkboxes wired to the new configuration endpoints, gated on `security_policies.manage`).

**Decisions**

- `allowed_factors` gets no UI control — confirmed by grep that nothing in unitprep-api reads that column, so exposing a toggle for it would mislead an admin into thinking it does something. Named as an open item (schema exists, unenforced) rather than silently building decorative UI or silently ignoring the gap.
- Session-length and passkey-count-limit settings are NOT part of Security Policies as shipped — no backing columns exist for either, and adding them was judged separate, larger scope (migrating env-var-based settings to DB-backed config) from "wire a UI to what `auth_configuration` already has." Flagged as a real follow-up, not silently dropped from the original task 9 description.
- `GET /auth/roles` has no permission gate (any authenticated caller) — matches the RLS policy's own intent (`roles_select_authenticated`) that the role/permission catalog isn't sensitive. The admin Roles PAGE is still gated client-side (and by extension, the only real caller in practice), but the endpoint itself doesn't need to be admin-only.
- Reissuing an invite for a still-invited user now resubmits only `user.roles[0]` (the backend's reissue path replaces the whole role set with one submitted role) — flagged in a code comment as a real edge-case: an invited user granted extra roles before ever enrolling would lose them on reissue. Not fixed further; a UI role-picker for reissue was judged out of scope for this pass.

**Learned**

- unitprep-ui already had built `admin/users` and `admin/audit-logs` pages from a session this vault's context didn't surface — confirms the earlier claim ("none of the Administration frontend exists yet") was wrong in a different way than the district_manager/Authentication-Policy-tab correction two sessions ago. The lesson repeats: read the actual current repo before asserting what does or doesn't exist, even (especially) right after a previous claim about it was already corrected once.
- This machine's known Turbopack/Watchpack-over-WSL-UNC-bridge issue (flagged in the vault's UnitPrep UI Dev Environment note as unresolved, "a `package.json --webpack` default proposed but not applied") is worse than previously documented: it doesn't just cause a restart loop (fixable with `WATCHPACK_POLLING=true`, confirmed working — the loop stopped), it also makes Turbopack's own first-page compile hang indefinitely (2+ minutes, no error, no completion) when the entire module graph has to be read over the WSL-to-Windows UNC bridge. This is almost certainly the root cause the note's own "confirmed to affect Boris's own real terminal" observation was pointing at, now isolated further. A real fix (running `next dev` from inside native WSL rather than crossing the bridge, or the proposed webpack fallback) is still not applied — worth a dedicated session.
- Confirmed (again, independently) that this machine has no native Linux node/npm/npx on WSL at all — only Windows-side binaries reachable via `/mnt/c`. Pure-JS tools (`tsc`, eslint's real entrypoint `.js` files) run fine when invoked directly via `node <script>.js` from PowerShell against the `\\wsl.localhost` UNC path. Tools with native platform bindings (vitest, via its rolldown dependency) cannot: they resolve to the Linux-built native module inside `node_modules` (since `node_modules` was npm-installed from WSL) but execute under Windows node, producing "Cannot find module @rolldown/binding-win32-x64-msvc" — a hard platform mismatch, not fixable by finding a different entrypoint script the way eslint/tsc's issue was.

**Verification**

Backend: `cargo check`/`test`/`clippy` all clean after adding the 2 new endpoints (296 tests passing, same as before). Frontend: full-project `tsc --noEmit` clean (zero type errors across every changed and unchanged file), `eslint .` clean except one pre-existing warning in a generated `coverage/` file plus one warning in this session's own `LeftNav.tsx` that was fixed immediately (unused import). Comprehensive repo-wide grep sweeps after each file confirmed no remaining references to the old `Role` type, `changeUserRole`, `VALID_ROLES`, or `RequireAdmin`. Live interactive browser/vitest verification NOT completed — see open items.

**Open**

- Full interactive browser verification of the new/changed pages (Users role chips, new Roles page, new Security Policies page, Audit Logs category tabs) was NOT completed — blocked by the dev-server hang described above, not by any known code defect. Verified instead via a full TypeScript type-check (clean, zero errors) and eslint (clean except one pre-existing warning in a generated `coverage/` file, unrelated) across the whole frontend. This is a real gap relative to the standing "start the dev server and use the feature in a browser" verification habit — worth closing out once the dev-environment issue itself is fixed.
- The Turbopack-hangs-over-UNC-bridge issue itself is unresolved and now more precisely characterized — a good candidate for its own dedicated session (likely fix: run `next dev` from a genuine WSL-native shell rather than crossing from Windows, or actually apply the previously-proposed webpack fallback).
- Vitest could not be run at all due to the win32/linux native-binding mismatch — existing frontend test suite (`LeftNav.test.tsx`, which this work modified, plus everything else) is unverified by an actual test run this session. Same root cause as the browser-verification gap.
- `allowed_factors`, session-length, and passkey-count-limit policies remain flagged, unbuilt follow-ups on the Security Policies page.

**Related (as recorded)**

- Tasks 1.2-1.4 shipped: data-driven authorization core, grant/revoke role endpoints, THREAT_MODEL updated _(no note yet)_
- [[UnitPrep UI Dev Environment]]

## 2026-08-07 17:46 — Step 1 work committed and pushed — unitprep-api v1.6.0, unitprep-ui v1.4.0

Closes out the "uncommitted state" open item from the resume-point note recorded earlier today. Everything from the roles/permissions work (backend + frontend + both live bugfixes) is now committed, versioned, and pushed to `origin/main` on both repos. A new session can start step 2 from a genuinely clean baseline — no pending local changes related to this work remain in either repo (only the same pre-existing unrelated uncommitted files noted before: `session_cookie.rs`/`step_up_policy.rs`/`totp.rs`/`README.sample.md`/assets on the backend, `app/layout.tsx`/`.claude/`/public assets on the frontend).

**Decisions**

- unitprep-api bumped 1.5.0 → 1.6.0 (3 commits: "Add role catalog and security-policy endpoints", "Fix resolve_session missing permission_keys", "Bump version to 1.6.0"), pushed as `362107f..1164fe3`. unitprep-ui bumped 1.3.1 → 1.4.0 (2 commits: "Add roles/permissions admin UI; fix breakage from the backend rewrite", "Bump version to 1.4.0"), pushed as `7047ed4..04f855f`. Both CHANGELOGs updated in the project's existing Keep-a-Changelog style before bumping — unitprep-api's `Unreleased` section already had unrelated Phase-II-hardening content sitting in it from before this session; today's entries were appended alongside it, all under the same `[1.6.0]` section, rather than treated as a separate release.

**Verification**

unitprep-api: `cargo check`/`test`/`clippy` all clean at v1.6.0 before committing (296 tests passing). unitprep-ui: `tsc --noEmit` and eslint both clean before committing. `git push` confirmed for both (`362107f..1164fe3` on unitprep-api, `7047ed4..04f855f` on unitprep-ui).

**Open**

- Step 2 (Client/Facility/Contacts schema) starts from a genuinely clean, fully-pushed baseline on both repos as of this note.

**Related (as recorded)**

- UnitPrep Onboarding Orchestrator — resume point as of 2026-08-07, step 1 complete, ready for step 2 _(no note yet)_

## Related

- [[Roles & Permissions — Backend Build Log]] — the backend work this frontend build depended on
- [[Roles & Permissions — Design Finalization Log]] — the design discussion that started this build arc
- [[Roles & Permissions — Design Discussion]] — the core note this satellite provides first-hand build detail for; its "Current state, as of 2026-08-08" correction already covers the shipped end-state (department_manager rename, `client_ops.perform`, etc.) that postdates everything in this log
- [[Admin Panel & Audit Logs Polish — Session Log]] — the audit-log/admin-panel polish batch that vaulted the design-discussion note this build implements
- [[Onboarding Orchestrator Kickoff — Session Log]] — the same-arc persistence planning that agreed step 1 (this migration) should come first
- [[Auth & Persistence Index]]
