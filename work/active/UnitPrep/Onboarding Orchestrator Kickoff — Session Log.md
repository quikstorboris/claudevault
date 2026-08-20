---
date: 2026-08-06
description: "Event-log satellite for the Onboarding Orchestrator persistence kickoff: the QMS OpenAPI-grounded brainstorm, company/facility/multi-role decisions, the agreed build order, a PII/compliance backlog review, and the step-1-complete resume point, verbatim, chronological."
tags: [work-note, unitprep, event-log]
status: active
quarter: Q3-2026
project: unitprep
---

# Onboarding Orchestrator Kickoff — Session Log

Event-log satellite for [[Platform Vision (Onboarding Orchestrator)]] and [[Orchestrator Feature Backlog]]. Covers five first-hand sessions from 2026-08-06 and 2026-08-07: the QMS-OpenAPI-grounded brainstorm that moved the Orchestrator vision from concept to concrete persistence design questions, the follow-up that resolved company/facility sourcing and endorsed multi-role users, the agreed build order (roles → client/facility → QMS credentials → first QMS pull → results persistence), an external (Grok) PII/compliance architecture review turned into a trigger-gated backlog, and the step-1-complete resume-point snapshot. Recovered from the vault's `inbox/` auto-filed notes 2026-08-10; moved here verbatim, nothing trimmed, in chronological order by each note's own `_Recorded ...Z_` timestamp.

## 2026-08-06 16:53 — QMS API persistence & Onboarding Orchestrator kickoff — brainstorm, no build yet

Boris shared the real QMS OpenAPI spec (`api-1.json`, 92 paths) and a 7-point brainstorm for starting client/facility persistence, document/template handling, multi-role users, and future integrations. This is exactly the "Onboarding Orchestrator" vision captured 2026-07-16/17/27 — now moving from vision to first concrete design questions. Read the actual spec (not the doc's stale summary) to ground the discussion in real API capabilities. Explicitly no coding yet — pure design discussion, decisions still open.

**What changed**

No code changed — design/research session only.

**Decisions**

None committed yet. Surfaced one real conflict for Boris to resolve deliberately rather than silently: Database Schema's `users.role` is a single enum column, explicitly designed that way ("stays a column, not a join table, since role is one-per-user in this design") — but Boris now wants multi-role per user (his own admin+OM example). This requires moving to a `user_roles` join table; flagged as a conscious schema-direction decision, not yet made.

**Learned**

- Read the real QMS OpenAPI spec end-to-end via python (588KB, too big for a normal Read): 92 paths, 56 GET / 25 POST / 12 PATCH / 11 PUT / 1 DELETE — write surface is real, not negligible, though GET dominates by tag (EndUsers, Units, Reports, Reservations, Leads heaviest).
- Auth is NOT a static API key passed on every call: `POST /api/v2/login` takes `grantType=client_credentials` (`clientId`+`clientSecret`) or `refresh_token`, returns a short-lived Bearer JWT + refresh token. Whatever secret Boris pasted in chat today is almost certainly a ClientSecret half of a `client_credentials` pair, not a bearer token itself — a credential store needs to hold `clientId`+`clientSecret` (encrypted at rest, same open question as `TOTP_ENCRYPTION_KEY`) and manage token refresh, not just forward one static header.
- Company (`GET /companies/{code}`) and Facility (`GET .../facilities`, `.../facilities/{code}`) schemas confirmed by reading the actual response schemas: Company has `name`, `email`, `phoneNumbers[]`, `addresses[]`, `isActive`, `facilityCount`, `location(lat/lng/tz)`. Facility has `name`, `isActive`, `location`, `phoneNumbers[]`, `addresses[]`, `tenantPortalUrl`. Neither has a `website` field, an occupied/vacant flag, or any owner/site-manager/contact modeling — confirmed by grepping all schemas for Owner/Manager/Contact/Staff, which only turned up QMS's own internal "CompanyUser" (note/lead authors) and tenant-side `AlternateContact`, nothing facility-organizational. This means Boris's requested corporate/facility/owner/site-manager persistence is entirely new UnitPrep-side modeling — QMS gives none of it, confirming the API can't be a source of truth for that data.
- Multi-facility-per-company is already native to the API shape (`GET /companies/{code}/facilities` returns a list) — no scaffolding gap there, UnitPrep's own client/facility tables just need to mirror that one-to-many from day one as Boris asked.
- No document-download endpoint exists anywhere in the spec (grepped for doc/urn/file). Lease records expose `signedDocumentUrns` (opaque URN array) with no resolving endpoint documented — so the already-executed signed lease PDF is not fetchable via this API. Sample lease templates for the future tag-extraction/template-processor tool (item 3, and the "lease document processor" already named as a future tool in Platform Vision) will have to keep coming from the client directly, not from QMS.
- Neon (the project's existing Postgres host) has no object/file storage feature analogous to Supabase Storage — confirmed against general Neon knowledge since Boris asked directly. Any raw-file persistence (tool output files, uploaded lease templates) needs a real S3-compatible store (S3/R2/B2/Spaces) as a separate service; Postgres-only stays viable only if the "store computed results, regenerate exports on demand" approach (Boris's own idea in point 4) actually eliminates the need to persist generated files at all.

**Verification**

Read the actual `api-1.json` spec via python (`json.load` + schema/path introspection) rather than trusting any stale doc summary — confirmed path counts, method counts, tag breakdown, exact response schema properties for Company/Facility/EndUser/Lease, security schemes, and grepped for document/owner/manager/contact concepts to confirm their absence.

**Open**

- Roles: move `users.role` from enum column to a `user_roles` join table (many-to-many) to support Boris's own admin+OM dual-hat need — not yet decided, needs deliberate sign-off since it reverses a documented v1 design choice.
- New persistence schema for client/facility/contacts (likely a dedicated schema, e.g. `clients` or `crm`, following the auth-schema precedent) — no tables designed yet, just discussed conceptually.
- File/object storage for lease template uploads and any future tool-output files that can't be satisfied by "store results, regenerate exports" — explicitly tabled by Boris for now, same as before.
- Tenant-PII report persistence (dedup/unit-group results) — access-control/compliance shape not designed, flagged against existing Compliance & Process Readiness assessment (CCPA-processor framing, no SSN/CC so lower breach-notification stakes, but still needs role-scoped access).
- Future integrations named today: Process.st, ClickUp, Zoho, Dropbox, HubSpot (HubSpot is new — not in the original Platform Vision list, which had Dropbox/ClickUp/Zoho/Process.st only). Nothing to build now, config-template extensibility already anticipated this.
- The QMS dev credential Boris pasted directly into chat plaintext today — not used for any live call this session (explicitly no-coding-yet), but it's now sitting in a chat transcript; worth Boris's own judgment on whether to rotate it once real credential storage exists.

**Related (as recorded)**

- [[Platform Vision (Onboarding Orchestrator)]]
- [[Roles & Permissions — Design Discussion]]
- [[Database Schema]]
- [[Compliance & Process Readiness]]
- [[future-feature-per-client-notes-attributed-to-the-entering-u]]
- [[UnitPrep File Locations]]

## 2026-08-06 17:13 — Onboarding Orchestrator kickoff, continued — company/facility source, documents, multi-role decided in principle

Follow-up to the same-day QMS API persistence brainstorm. Boris resolved three of the open questions from that session: company/facility/owner/manager data will be manually entered (Zoho/HubSpot as possible future sources, not now), document download from QMS is confirmed unnecessary (OMs provide leases via direct upload or future Dropbox selection), and multi-role per user is endorsed as the right model, not just an acceptable compromise. Still no code written — design discussion only.

**Decisions**

- Company/facility/contact data for Client records will be entered manually for now; Zoho and/or HubSpot are candidate future sources for that data, not QMS. No field list designed yet — deferred to when Client data schema is actually built.
- No document-download integration with QMS is needed, now or as a near-term plan. Lease documents reach UnitPrep via direct upload by OMs, or later via a Dropbox folder/file selection once that integration exists — QMS was never going to be the source for these anyway (no such endpoint exists in the spec).
- Multi-role per user (e.g. admin + onboarding_manager on one account) is endorsed, not merely tolerated. Reasoning given: it's standard RBAC (`user_roles` join table, union-of-capabilities), it's exactly what the existing "role = job function, not trust level" principle already anticipates, and it doesn't deepen the already-accepted single-admin segregation-of-duties gap since it's an orthogonal capability grant that doesn't touch audit/oversight power. The one honest caveat named: with a single admin, that account can self-grant any role unchecked — same fact as the existing single-admin exception, just newly visible from this angle, and should be documented alongside it rather than treated as new risk.

**Verification**

None — pure design discussion, no code or schema changes made.

**Open**

- Migrate `users.role` from enum column to a `user_roles` join table — decided in principle this session, not yet scheduled or built (still no-coding-yet).
- Client/facility/contact schema and its field list — still not designed; now explicitly scoped as manual-entry-first with Zoho/HubSpot as later possible sources.
- Document/file storage (S3-equivalent) — still tabled; now lower urgency than previously discussed since QMS was ruled out as a document source and Dropbox-based selection is the more likely near-term path once built, not raw QMS document sync.

**Related (as recorded)**

- QMS API persistence & Onboarding Orchestrator kickoff — brainstorm, no build yet _(no note yet)_

## 2026-08-06 18:16 — Build order agreed for Onboarding Orchestrator persistence work; single-admin caveat shelved; roles-table shape decided

Closing out the same-day design-discussion arc. Boris asked for a recommended implementation order across everything discussed this session (multi-role, client/facility/contacts, QMS credentials, results persistence, documents, integrations). Also made two smaller calls: the single-admin segregation-of-duties caveat is explicitly irrelevant until real rollout (not a standing concern to keep raising), and admin-configurable custom roles is confirmed future-only ("bells and whistles"), which informed a mechanical recommendation for the roles migration itself.

**Decisions**

- Single-admin / no-real-users-yet risk (self-granting roles, no second admin to check anything) is explicitly deprioritized: Boris's own framing is that until the app is actually rolled out, stolen source code grants no DB or user-creation access, so this class of gap is not worth tracking as an open item right now. Distinct from the compliance note's SOX framing, which still applies once there ARE real users — this is a "not yet, not never" call, not a reversal of that assessment.
- Custom/admin-configurable roles confirmed future-only, not near-term scope. Informed a mechanical choice for the upcoming roles migration: back `user_roles` with a small normalized `roles` lookup table (id, key, label) rather than a hardcoded enum, specifically because it costs about the same to build now but avoids a second migration when custom roles eventually get real. Not building any admin UI or permission-matrix now — just choosing the storage shape that doesn't need re-doing later.
- Agreed build order for everything discussed this session: (1) roles → `user_roles` join table (small, unblocks Boris's own dual-hat need, prerequisite for RLS on everything after), (2) Client/Facility/Contacts schema (manual-entry-first, 1-to-many facility from day one, RLS by role), (3) QMS credential storage + `client_credentials`/refresh token mechanics (needs a client record to attach to), (4) first real read-only QMS pull (company+facility list) to prove #3 end-to-end, (5) shared tool-run results persistence, attributed to real client/facility ids from the start rather than retrofitted. Everything else (document/file storage, Dropbox, Zoho/HubSpot/ClickUp/Process.st, role-config UI) stays parked until its own concrete trigger arrives, consistent with the existing "validate each layer before generalizing" principle.

**Verification**

None — pure planning/sequencing discussion.

**Open**

- Nothing built yet — next session presumably starts on step 1 (roles migration) if Boris proceeds in the agreed order. Still no code written as of this note.

**Related (as recorded)**

- QMS API persistence & Onboarding Orchestrator kickoff — brainstorm, no build yet _(no note yet)_
- Onboarding Orchestrator kickoff, continued — company/facility source, documents, multi-role decided in principle _(no note yet)_
- UnitPrep multi-role (admin+OM) is endorsed, not just tolerated _(no note yet)_

## 2026-08-07 15:17 — PII/compliance architecture backlog — 9 trigger-gated items, deliberately not built now

Reviewed an external (Grok) architecture proposal for client/facility/tenant PII persistence against this project's actual state and existing compliance assessment. Most of the proposal overlapped with decisions already made this session (schema-per-domain, RLS pattern, audit domain split, staging-not-system-of-record framing). Extracted 8 genuinely new considerations plus a 9th (SSN/EIN/TIN for a future Elavon payment-processor prefill tool) that Boris raised independently. Explicitly rejected: any near-term field-level encryption, a self-service tenant portal, a unified cross-domain `audit.events` table, and Postgres-as-document-store even as a stopgap. Boris's explicit standing instruction: track these as a trigger-gated backlog and surface each at the right moment, not build preemptively — security thoroughness must be balanced against feature velocity, not maximized at its expense.

**Decisions**

- REJECTED, with reasons, not just deferred: (1) near-term field-level encryption — data minimization beats encrypting things that shouldn't be stored in the first place, EXCEPT see the new Elavon exception below. (2) a self-service tenant-facing portal — tenants are the client's customers, not UnitPrep's users; Boris's own words: "maaaaybe waaaay later" as a Process Street replacement, not soon, not as DSR tooling. (3) a single unified `audit.events` table spanning auth + client-ops with a domain column — conflicts with the already-locked access boundary (Admin structurally excluded from client-ops audit); Boris's own words: "stupid." (4) storing document bytes in Postgres even as a v1 stopgap — skip straight to real object storage whenever the lease tool actually needs file storage.
- NEW: a concrete, real exception to the "don't store sensitive government IDs" default. Clients apply to the payment processor Elavon, which requires EIN/TIN (and likely SSN for sole-proprietor owners) on the application. A future tool may prefill Elavon's Word application from UnitPrep-held owner/client data, OR that data may end up sourced from Process Street instead — undecided, tool not yet scoped. Either way this is the first genuinely sensitive-government-ID use case identified for this platform, and it is the trigger that would justify real field-level encryption (not the general tenant PII case, which stays name/address/phone/email per the existing Compliance & Process Readiness assessment). Worth a fresh compliance look (GLBA/PCI-adjacency framing) when that tool is actually scoped — not concluded now, just flagged as the first real trigger for a class of control previously reasoned away as unnecessary.
- Boris's explicit standing instruction for this project (feedback, not a one-off): security/compliance controls should be tracked as a trigger-gated backlog and proactively called out at the right moment as the app evolves — but NOT front-loaded or built preemptively. Explicit framing: "this is all in the name of security, but i don't want to get bogged down locking down the fort at the cost of slow feature development. need a good balance here." Apply this by defaulting new security/compliance ideas to "noted, trigger-gated" rather than "build now," the same discipline already used elsewhere in this project (KMS, ZTNA, Groups, last-admin-guard, per-developer DB roles) — this instruction generalizes that existing pattern explicitly rather than introducing a new one.

**Verification**

None — architecture/compliance discussion only, no code or schema changes from this exchange.

**Open**

1. Data Subject Request workflow (`data_subject_requests` table + staff-mediated inventory/export/anonymize flow). Trigger: the first real tenant PII table ships with real data — needed at that point, not before.
2. Anonymize-in-place as its own DB operation, distinct from soft-delete (scrub PII fields, keep the row/id for referential + audit integrity). Trigger: bundled with #1 — should ship alongside the first tenant PII table, not deferred past it, since it's the actual erasure mechanism DSRs need.
3. Occupancy as a tenant↔unit↔date-range link table rather than copying tenant PII onto every unit row. Trigger: apply automatically when the tenant/unit schema is actually designed — a shape decision to make at that time, not a separate backlog item with its own trigger.
4. Redacted summary vs. full-detail DTOs at the API layer (list views never carry full PII; detail view costs an extra permission check + gets logged). Trigger: the first API/UI screens that list tenants or facilities — cheap to do right from the start, adopt then.
5. Retention TTL enforced by a scheduled job, not a remembered policy. Trigger: the lease tool starts generating Word exports or accepting raw document uploads.
6. Explicit decision on the audit-vs-erasure tension: does anonymizing a tenant scrub audit rows that reference them, or is there a documented security-retention exception? Trigger: bundled with #1/#2 — decide once, in writing, before the anonymize function ships, not improvised later.
7. Reconsider the timing of "Groups" (client-scoped access — which OM/DM sees which client), currently deferred as hypothetical. Trigger: the Client/Facility schema (build-order step 2) actually ships and tenant PII starts spanning multiple clients — re-evaluate then, not now.
8. Lightweight PII column-classification convention (schema comments tagging `pii`/`sensitive_pii`, no tooling). Trigger: the first PII-bearing table (tenant schema) — near-free, adopt as a habit at that point rather than deferring.
9. SSN/EIN/TIN handling for a possible future Elavon-application-prefill tool, including whether that data is UnitPrep-sourced or Process-Street-sourced, and whether real field-level encryption becomes justified. Trigger: that tool is actually scoped — not yet, tool doesn't exist.

**Related (as recorded)**

- [[Compliance & Process Readiness]]
- [[Platform Vision (Onboarding Orchestrator)]]
- [[Roles & Permissions — Design Discussion]]

## 2026-08-07 17:34 — UnitPrep Onboarding Orchestrator — resume point as of 2026-08-07, step 1 complete, ready for step 2

Full status/roadmap snapshot for continuing in a new session. Step 1 (roles/permissions — backend + frontend) is functionally complete on both dev and prod, including two live bugs found after Boris actually used the app (both fixed and verified against his real session). A meaningful amount of that work is still uncommitted locally in both repos as of this note — check `git status` before assuming anything described here is pushed. Step 2 (Client/Facility/Contacts schema) has not been started; nothing below it in the roadmap has moved.

**Decisions**

- STEP 1 STATUS: COMPLETE, both dev and prod. Roles/permissions data model (`auth.roles`/`permissions`/`role_permissions`/`user_roles`), data-driven `has_permission()`/`require_permission()` throughout the backend, grant/revoke role endpoints, `GET /auth/roles`, `GET`+`PUT /auth/configuration` (`security_policies.manage`), whoami returns roles+permissions, and the full frontend (Administration nav grouping, Users page role chips, read-only Roles page, tabbed Audit Logs, Security Policies page) are all built and were live-verified end to end against Boris's real browser session — not just tests.
- TWO LIVE BUGS found post-"complete" and fixed on both dev and prod, both worth knowing about because of HOW they were found: (1) `resolve_session` was missing the `permission_keys` column entirely — designed and coded against in Rust, never actually migrated into the DB function. Slipped through because every test (unit tests, the live smoke test) only ever exercised the unauthenticated 401 path, never a real `resolve_session` call with a valid session — Boris's actual login was the first thing to hit it. Fixed by migration `20260807130000_resolve_session_returns_permission_keys`. (2) `LeftNav` rendered an `<li>` wrapping a `NavItem` (which itself renders an `<li>`) around the Account link, an HTML-invalid li-in-li that Next.js correctly flagged as a hydration error in Boris's real browser — something no type-check or lint catches. Fixed by giving `NavItem` an optional `className` prop instead of a wrapping `<li>`. Generalizable lesson recorded separately: automated verification (tsc/eslint/unit tests) proved necessary but not sufficient twice in one day — both bugs needed a REAL authenticated user in a REAL browser to surface, and neither did until Boris manually used the app after being told it was verified.
- UNCOMMITTED STATE as of this note (verify with `git status` before trusting this, it will go stale): unitprep-api has 2 new migration pairs (`20260807120000` security_policies permission, `20260807130000` resolve_session fix) plus 2 new files (`auth_roles.rs`, `auth_configuration.rs`) plus modifications to `api/mod.rs` and `auth/audit_log.rs`, all uncommitted. unitprep-ui has the ENTIRE frontend roles work uncommitted: `lib/auth.ts`, `LeftNav.tsx`+test, `RequirePermission.tsx` (new, replacing deleted `RequireAdmin.tsx`), `admin/users`+`audit-logs`+`audit-logs/export`+`account` page edits, and two new pages (`admin/roles`, `admin/security-policies`). Both repos also have the SAME pre-existing unrelated uncommitted files noted in earlier sessions (backend: `session_cookie.rs`, `step_up_policy.rs`, `totp.rs`, `README.sample.md`, `assets/readme/`; frontend: `app/layout.tsx`, `.claude/`, `public/favicon.svg`, `public/orchestrator-logo-dark.svg`) — none of these are from this work, exclude them from any commit the same way prior sessions did.
- PERMISSION CATALOG STILL PROVISIONAL: department_manager's exact grants and sales's empty permission set are still Claude's best-effort guess from the original capability-matrix conversation, never explicitly confirmed by Boris. Cheap to fix (a data UPDATE, not a migration) whenever he reviews it — flagged repeatedly, still open.

**Learned**

- Confirmed dev-environment facts worth not re-discovering next session: this machine has NO native Linux node/npm/npx anywhere in WSL — only Windows-side binaries reachable via `/mnt/c`. Pure-JS Node tools (`tsc`, eslint's real `.js` entrypoint) run fine invoked as `node <real-entrypoint>.js` directly from PowerShell against the `\\wsl.localhost` UNC path — npx/npm's `.cmd` wrapper scripts do NOT work this way (they shell out to cmd.exe, which refuses a UNC current directory outright). Tools with native platform bindings (vitest, via rolldown) CANNOT be run this way at all — `node_modules` was installed under WSL (Linux bindings), Windows-side node needs win32 bindings that don't exist there; this is a hard platform mismatch, not a missing-entrypoint problem, and has no known workaround short of running from genuine WSL node (which doesn't exist on this machine) or reinstalling `node_modules` from Windows (untested, likely disruptive).
- The Turbopack/Watchpack-over-WSL-UNC-bridge dev-server issue (previously flagged in UnitPrep UI Dev Environment as an unresolved restart loop) is worse than documented: setting `WATCHPACK_POLLING=true` does stop the restart loop, but Turbopack's first-page compile can then hang indefinitely (2+ minutes, no error, no completion) reading the full module graph over the bridge. Real fix still not applied (run `next dev` from genuine WSL node, or the previously-proposed webpack fallback) — worth a dedicated session, since it's now blocked BOTH interactive verification and the test suite in the same session.
- Reinforced from two fresh incidents: "it compiles, type-checks, and passes unit tests" is not the same claim as "it works" for anything touching (a) a live database function whose contract isn't compile-time-checked (sqlx runtime queries), or (b) real DOM/hydration behavior a browser enforces that no static tool catches. Both gaps here were only found because Boris personally exercised the real app after being told it was done — worth treating "have you actually clicked through it yourself" as a standing question before calling frontend/backend integration work complete, independent of how clean the automated checks look.

**Verification**

Everything under STEP 1 was verified as described in the two prior work notes this one links from (build/test/clippy clean on backend, tsc+eslint clean on frontend, both live bugs confirmed fixed against Boris's real session/browser after the fact). This note itself is a status snapshot, not new verification.

**Open**

- STEP 2 (next, not started): Client/Facility/Contacts schema. Known going in from earlier sessions: manual-entry-first (QMS API doesn't model corporate/facility/owner/site-manager data at all — confirmed by reading the real QMS OpenAPI spec), 1-to-many facility-per-company from day one (matches how the QMS API itself shapes it), contacts modeled with an owner/site_manager type distinction, RLS scoped by role same as auth tables, and — per the standing Postgres-schemas-per-domain rule — this needs its OWN schema (likely `clients`), not bolted onto `auth` or dumped into `public`. No field list enumerated yet, no table names decided, nothing built.
- STEP 3: QMS credential storage (`client_credentials` + refresh token mechanics, encrypted at rest — same open question as `TOTP_ENCRYPTION_KEY`). This is also where the previously-agreed temporary admin+OM permission gate for testing credential-add gets applied (see the roles-work session notes), and where the real `client_credentials.add`/`revoke`/`approve` permissions — already seeded in the roles migration, unused until now — get their first real consumer.
- STEP 4: first real read-only QMS pull (company+facility list) to prove step 3 end-to-end.
- STEP 5: shared tool-run results persistence (dedup/unit-group results stored so exports can be regenerated without re-running analysis), attributed to real client/facility ids from the start.
- DEFERRED BUCKET, unchanged, no new triggers fired: `approval_requests` table + Approvals nav (deferred until step 3 gives it a real action), document/file storage (S3-equivalent, no urgent need), Dropbox/Zoho/HubSpot/ClickUp/Process.st integrations, custom-role creation/editing UI, Groups (client-scoped visibility), the 9-item PII/compliance backlog from the Grok-review session (DSR workflow, anonymize-in-place, occupancy-as-link-table, redacted DTOs, retention TTL, audit-vs-erasure decision, Groups-timing reconsideration, PII column-classification convention, and the Elavon SSN/EIN exception to the no-field-encryption default).
- Whether to commit+push the currently-uncommitted step-1 work before starting step 2 — asked, not yet answered as of this note. (Resolved same day — see [[Roles & Permissions — Frontend Build & Ship Log]]'s 17:46 entry: both repos committed and pushed as unitprep-api v1.6.0 / unitprep-ui v1.4.0.)

**Related (as recorded)**

- Task 1.1 shipped: roles/permissions schema live on Neon dev, functionally verified _(no note yet)_
- Tasks 1.2-1.4 shipped: data-driven authorization core, grant/revoke role endpoints, THREAT_MODEL updated _(no note yet)_
- Roles frontend (tasks 5-9) shipped; also fixed frontend breakage from the backend authorization rewrite _(no note yet)_
- Build order agreed for Onboarding Orchestrator persistence work _(no note yet)_
- PII/compliance architecture backlog — 9 trigger-gated items, deliberately not built now _(no note yet)_

## Related

- [[Platform Vision (Onboarding Orchestrator)]] — the long-term vision this kickoff started turning into concrete design questions
- [[Orchestrator Feature Backlog]] — the consolidated planning view this session's decisions feed into
- [[Roles & Permissions — Design Discussion]] and its build satellites ([[Roles & Permissions — Design Finalization Log]], [[Roles & Permissions — Backend Build Log]], [[Roles & Permissions — Frontend Build & Ship Log]]) — step 1 of the build order agreed here
- [[Compliance & Process Readiness]] — the general SOX/SOC2/CCPA framework the PII backlog review cross-references
- [[Auth & Persistence Index]]
