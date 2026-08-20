---
date: 2026-08-06
description: "Event-log satellite for the final three design-discussion sessions (nav/capability matrix/multi-role settled, Approvals nav finalized, 9-task build breakdown) that closed the roles/permissions design arc before implementation began, verbatim."
tags: [work-note, unitprep, event-log]
status: active
quarter: Q3-2026
project: unitprep
---

# Roles & Permissions — Design Finalization Log

Event-log satellite for [[Roles & Permissions — Design Discussion]]. Covers the final three design-discussion sessions from 2026-08-06 that closed out the multi-day design arc before implementation began: the nav/capability-matrix/multi-role settling pass, the Approvals-nav/`approval_requests`-retention closeout, and the 9-task build breakdown with the full remaining roadmap. Continued in [[Roles & Permissions — Backend Build Log]] (schema + authorization core) and [[Roles & Permissions — Frontend Build & Ship Log]] (frontend + commit/push) — this three-way split keeps each note under the vault's ~25KB organization threshold. Recovered from the vault's `inbox/` auto-filed notes 2026-08-10; moved here verbatim, nothing trimmed, in chronological order by each note's own `_Recorded ...Z_` timestamp.

## 2026-08-06 19:05 — Roles migration sketch (#1) — nav, capability matrix, and multi-role mechanics settled in detail

Deep design pass on step 1 of the agreed build order (roles migration). Corrected an overstated claim (the Admin/Security nav was only ever planned, never built in unitprep-ui). Settled the Administration nav shape, the role capability matrix's remaining ambiguities, DM oversight mechanics, the approval-workflow shape, audit-log domain split, and reversed an earlier recommendation on enforcement after Boris pushed back with good reasoning. Still no code written.

**Decisions**

- CORRECTION: the "Admin > Security" nav (Authentication Policy/Users/Groups/Audit Logs tabs) documented in Architecture.md was only ever a plan from 2026-07-20, never built in unitprep-ui. Confirmed directly by Boris ("can't see it anywhere"). Backend endpoints for users/audit-logs do exist (Phase 2 work); the frontend admin pages do not. Future scoping must treat this as building from scratch, not extending an existing page.
- Administration nav: Users, Roles (read-only capability-matrix view for now, editor deferred), Audit Logs, Security Policies (renamed/expanded Authentication Policy tab, backed by existing `auth_configuration` table + new columns for session length/passkey limits/expiration). Groups explicitly stays deferred/on-ice, not part of this work.
- Admin is barred from approving client-ops actions (confirmed final, not just my recommendation) — that's exclusively a DM task.
- DM oversight, two distinct mechanisms: (1) a DM can never approve their own request — buildable now regardless of DM headcount, closes the obvious self-approval bypass. (2) once 2+ DMs exist, the approvals history is visible to any DM (not scoped to "only my own decisions"), giving peer/detective oversight without a formal second-approval workflow. With exactly one DM today, this is a known, accepted single-point-of-trust gap, same treatment as the single-admin gap — deferred, not solved now.
- Sales role: capabilities deferred, but confirmed general shape is read-only client-record access, no operations, no credential access.
- "OM configure own credentials" clarified: means personal auth recovery (passkey rotation, TOTP reconfigure after losing a device), NOT roles/admin functions. Reclassified as a baseline capability every authenticated user gets regardless of role (Admin and DM need to recover lost devices too) — removed from the per-role capability matrix, not an OM-specific grant.
- OM can revoke a client's QMS API credential unilaterally, no approval needed. Re-adding one after revocation requires DM approval again — UI must warn about this at revoke time (product/UX detail, not designed further now).
- Approvals nav: in-app notification at login + a dedicated "Approvals" menu, DM-role-gated. Must NOT live under Administration (Admin-only) since DM is excluded from admin entirely — Approvals should be its own top-level nav item, peer to Administration.
- Custom role deletion is explicitly ALLOWED and intended. The `is_system` flag protects only the 4 built-in roles (admin, onboarding_manager, district_manager, sales) from delete/rename, since the permission model's own integrity depends on those existing — not a general anti-deletion stance. What happens to users holding a deleted custom role (strip vs block-until-unassigned) is left for whenever the custom-role editor is actually built.
- Audit log architecture: hard split by access domain, not just UX categories. (1) System/Security audit (Administration > Audit Logs, admin-visible): auth events, permission/role changes, user admin actions — organized as TABS on the existing Audit Logs page (Authentication / Permissions & Roles / Users & Access), reusing the already-established tabbed-page convention rather than adding a new nav parent. (2) Client-ops audit (DM/OM-visible, Admin excluded, lives wherever DM/OM's own nav is): API-key add/revoke/approve, tool-run activity. Role grant/revoke events land in the admin-visible "Permissions & Roles" tab since role administration is a system/admin concern, not client-ops.
- REVERSED earlier recommendation: enforcement will be data-driven from day one, not hardcoded-then-migrated-later. A `permissions` catalog table + `role_permissions` join table gets built and seeded now with today's full capability matrix; every check becomes `has_permission(user, key)` via that data, no hardcoded role-name checks scattered through the backend. What stays deferred is only the admin-facing editing UI (custom-role creation/permission-checkbox screen) — the data model itself was never the expensive part once the matrix was already fully enumerated in conversation, so there was no real cost saved by hardcoding first. Boris's pushback (prefers avoiding hardcoding generally, "elegance" principle) was correct and changed this recommendation.
- `approval_requests` table: scoped as a lean OPERATIONAL QUEUE only (pending items, maybe a short grace window on just-decided ones for UI feedback) — explicitly NOT the permanent historical record. The permanent record is an immutable audit-log event written at decision time with full before/after context, mirroring the existing rule that an audit log must never be editable after the fact. Reasoning: a queue table and an audit table solve different problems (operational vs. permanent-record), and overloading one with the other's job (e.g. needing to lock down UPDATE/DELETE on `approval_requests` to make it audit-grade) creates exactly the kind of gap already known from the "ops telemetry vs audit trail are different jobs" lesson.
- Self-role-edit invariant confirmed absolute, no exception for single- or multi-role self-assignment, even for the person setting the system up. Boris's own dual role (admin + onboarding_manager) will be granted manually outside the guarded path when this is actually built, same pattern as the existing first-admin bootstrap CLI.

**Verification**

None — pure design discussion, no code or schema built.

**Open**

- Still no code written — this is design-only. Next step is presumably actually building step 1 (roles/permissions schema + Administration nav) whenever Boris says to start.
- Cascade behavior for deleting a custom role that users still hold (strip vs. block) — left for when the custom-role editor is built.
- Exact permission-key catalog / naming scheme for the permissions table — not enumerated yet, just the mechanism (data-driven, not hardcoded) is decided.

**Related (as recorded)**

- Onboarding Orchestrator kickoff, continued _(no note yet)_
- Build order agreed for Onboarding Orchestrator persistence work _(no note yet)_
- [[Architecture]]
- [[Roles & Permissions — Design Discussion]]
- [[Compliance & Process Readiness]]

## 2026-08-06 19:18 — Roles migration sketch closed out — Approvals nav finalized, approval_requests confirmed permanent

Final round of confirmations closing out the design-discussion arc for step 1 (roles migration). All prior proposals from the previous session confirmed as-is; one new design point resolved (OM's own request-history view) and one earlier open question settled (`approval_requests` retention). Still entirely design-only, no code written across this whole multi-session arc.

**Decisions**

- Confirmed as final, no changes: DM can never approve their own request; personal-account recovery (passkey rotation/TOTP reconfigure) is a baseline capability for all users, not an OM-specific grant; `is_system` only protects the 4 built-in roles from delete/rename, custom roles remain fully deletable; the admin-visible audit log's tabbed-categories split (Authentication/Permissions & Roles/Users & Access) is agreed.
- Approvals nav finalized: ONE top-level nav item (not under Administration), visible to both DM and OM, but role-scoped by row rather than split into separate pages — DM sees the full queue (pending + all history, for the peer-oversight reason already discussed), OM sees only rows where they are the requester ("My requests" — their own pending/approved/rejected history). Reuses the same `approval_requests` table and page instead of building a second surface, and mirrors the already-established oversight-view-vs-personal-activity-view distinction from the Profile page idea.
- `approval_requests` retention settled: kept PERMANENTLY (not pruned), same as originally proposed then walked back to "maybe prune later if needed." Boris's call: keep both `approval_requests` and the audit log forever for now; only reconsider cleanup of `approval_requests` specifically if/when its size actually becomes a real problem — the audit log's permanence is non-negotiable regardless. Side effect: OM's "my requests" history view can query `approval_requests` directly (`requested_by = self`) rather than needing the audit log at all for that display — the audit log stays the authoritative compliance record, `approval_requests` becomes the convenient queryable day-to-day view for both DM's queue and OM's personal history.

**Verification**

None — pure design discussion.

**Open**

- Still zero code written across this entire design arc (spanning company/facility source, roles, capability matrix, audit architecture, approvals). Next real step is presumably Boris signaling readiness to actually start building step 1 of the agreed order.

**Related (as recorded)**

- Roles migration sketch (#1) — nav, capability matrix, and multi-role mechanics settled in detail _(no note yet)_

## 2026-08-06 19:30 — Roles work (#1) broken into 9 build tasks; full remaining roadmap recorded before implementation starts

Design discussion phase closes here. Boris confirmed the temporary admin+OM gate for credential-add (deferred to step 3, not buildable yet since no credential endpoint exists), confirmed seeding both his roles directly, confirmed adding Sales, and clarified the permission catalog is a permanent mechanism with growing content, not a throwaway. Step 1 (roles/permissions) was then broken into 9 concrete, ordered build tasks spanning unitprep-api and unitprep-ui. Boris expects this whole session to stay on step 1 until context runs out, so the full remaining roadmap (steps 2-5 plus the deferred bucket) is recorded here for continuity in case a future session picks this up without this conversation's context.

**Decisions**

- Temporary admin+OM gate for testing credential-add before the real DM-approval workflow exists: implement as ONE extra, explicitly-temporary check at the call site of the future credential-add endpoint (requires caller to also hold admin, on top of the real `client_credentials.add` permission) — NOT as AND-composition baked into the general `role_permissions` engine, which stays a simple OR-across-roles model everywhere else. This cannot literally be coded yet — the credential-add endpoint itself doesn't exist until step 3 — so it's recorded here as a requirement to apply WHEN step 3 is built, not a task under step 1.
- Confirmed: migration seeds Boris's user with both admin and onboarding_manager directly. Confirmed: Sales role gets seeded now alongside the other 3 system roles, minimal/empty permission set for now. Confirmed: the permissions catalog is the permanent mechanism (data-driven, never needs a redo) with content that simply grows over time as new gated actions get built — not something to be treated as temporary or thrown away.
- Step 1 (roles/permissions) broken into 9 ordered build tasks, tracked live in this session's task list: (1) schema migration (roles/permissions/role_permissions/user_roles tables, seed data, migrate+assign Boris's roles, drop old `users.role` column, single clean cutover), (2) backend authorization core (`has_permission()` check, retrofit existing gated endpoints, enforce self-role-edit-absolute on `user_roles`), (3) role-management endpoints + `role_granted`/`role_revoked` audit events with full before/after set, (4) `THREAT_MODEL.md` doc hygiene (close the onboarding_manager-permissions gap, mark last-admin-guard as deferred-by-choice), (5) frontend Administration nav shell (none of this exists yet in unitprep-ui), (6) frontend Users page with multi-role UI, (7) frontend Roles page (read-only matrix, no editor yet), (8) frontend Audit Logs page (tabbed by domain: Authentication/Permissions & Roles/Users & Access), (9) frontend Security Policies page (`auth_configuration`-backed).

**Verification**

None yet — planning/task-breakdown only, no code written.

**Open**

- REMAINING ROADMAP, for continuity if a future session resumes this without today's conversation context. After step 1 (roles, in progress, 9 sub-tasks above): step 2 = Client/Facility/Contacts schema (manual-entry-first, company/facility 1-to-many from day one, contacts as owner/site_manager type, RLS by role — no field list enumerated yet). step 3 = QMS credential storage + `client_credentials`/refresh token mechanics (encrypted `clientId`/`clientSecret` per client, same open encryption-at-rest question as `TOTP_ENCRYPTION_KEY`) — THIS is where the temporary admin+OM gate above gets applied, and where the real `client_credentials.add`/`revoke` permissions get exercised for the first time. step 4 = first real read-only QMS pull (company+facility list) to prove step 3 end-to-end. step 5 = shared tool-run results persistence (dedup/unit-group results stored so exports can be regenerated without re-running analysis), attributed to real client/facility ids from the start.
- DEFERRED BUCKET, no trigger yet for any of these: `approval_requests` table + Approvals nav (DM action queue + OM "my requests" view) — deferred specifically until step 3 gives it a real action to gate, not built now since testing an approval abstraction with zero real consumers was judged premature. Document/file storage (S3-equivalent) for lease templates and any future tool-output files. Dropbox integration. Zoho/HubSpot/ClickUp/Process.st config-template integrations. Custom-role creation/editing UI (the roles/permissions DATA MODEL is being built data-driven now specifically so this slots in later with zero backend rework — only the admin-facing editor is deferred). Groups (department-level client-visibility scoping, orthogonal to roles) — explicitly "on ice" per Boris. Sales role's actual capability list beyond "read-only baseline." DM peer-oversight mechanics and self-approval-refusal — conceptually agreed, not built (no approval workflow exists yet to build it into).
- Nothing implemented yet as of this note — migrations, code, and frontend pages for step 1 all still pending. This is the last pure-planning checkpoint before implementation work begins.

**Related (as recorded)**

- Roles migration sketch closed out — Approvals nav finalized, approval_requests confirmed permanent _(no note yet)_
- Build order agreed for Onboarding Orchestrator persistence work _(no note yet)_

## Related

- [[Roles & Permissions — Backend Build Log]] — continues with the actual implementation (schema, authorization core)
- [[Roles & Permissions — Frontend Build & Ship Log]] — the frontend build and the commit/push that closed step 1
- [[Roles & Permissions — Design Discussion]] — the core note this satellite provides first-hand detail for
- [[Auth & Persistence Index]]
