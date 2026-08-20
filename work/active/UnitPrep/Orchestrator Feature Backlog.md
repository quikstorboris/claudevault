---
date: 2026-08-07
description: "Consolidated feature list: the roles/permissions work already in flight, Grok's accepted PII/GDPR suggestions, and the QMS-API-shaped features found 2026-08-07 (Go-Live Auditor, template editor). Living doc — update in place, don't restate elsewhere."
tags: [work-note, unitprep]
status: active
quarter: Q3-2026
project: unitprep
---

# Orchestrator Feature Backlog

Boris's ask, 2026-08-07: pull together the roles/permissions thread, Grok's
accepted suggestions, and today's QMS API findings into one list of features
to work on. This is that list — organized by readiness, not by source,
since "where an idea came from" matters less than "what it needs before it
can be built." Per [[Auth & Persistence Index]]'s single-source-status rule,
this note **owns** the consolidated view; the source notes below keep their
own detail and should be read for the reasoning behind each line, not
restated here.

## Correction 2026-08-08: two Tier 2 items already shipped, differently than described

Found while inspecting `unitprep-api`'s actual migrations directly (a
session outside this conversation did this work 2026-08-06/07, not yet
reflected here until now):

- **The `onboarding_manager` umbrella tool-access model is done.** Roles
  and permissions are now real data (`auth.roles`, `auth.permissions`,
  `auth.role_permissions`, `auth.user_roles`, multi-role per user), and
  `client_ops.perform` is exactly the umbrella permission recommended
  below — granted to `onboarding_manager` and `department_manager`, gating
  client-facing tools as one capability rather than per-tool grants.
- **A "Manager" approval role exists — but for QMS credential changes, not
  admin role changes.** `department_manager` (originally seeded as
  `district_manager`, renamed same-day — that term already means something
  else in self-storage) can do everything `onboarding_manager` can, plus
  approve pending `client_credentials.add`/`revoke` requests. The
  dual-approval idea below was scoped around admin-role-change approval,
  which is a different, still-unbuilt thing — don't conflate the two.
- **A fourth role, `sales`, now exists too** — read-only access to client
  records, capabilities still undefined. Not previously tracked anywhere in
  this backlog.
- **No `client_credentials` table exists yet** — the permission keys
  (`client_credentials.add/revoke/approve`) are defined and granted, but
  nothing stores an actual credential yet. Real work, not yet started.

Both corrected items removed from Tier 2 below. See
`unitprep-api/CHANGELOG.md` v1.6.0 for the full rollout this was drawn
from.

## Tier 1 — buildable now, no open design questions

- **QMS Template Tagging Assistant** — resolved and re-scoped 2026-08-07,
  grounded against three real client document pairs plus QMS's own Standard
  Templates library 2026-08-08 (see [[QMS Template Tags — Evidence from
  Real Documents]]). Not a document generator (QMS always generates the
  real document); the tool finds spots in a client's raw legal document
  that should become QMS tags and proposes the substitution for OM review
  — never applies anything silently, per the hard "propose, don't modify"
  rule in [[QMS Template Tags — Catalog & Editor Design]]. Phased:
  - **Phase 1 (catalog + API): shipped 2026-08-08.** `client_ops` schema
    (first schema outside `auth`), `client_ops.qms_tag` seeded with the 13
    most-common tags, exposed via `GET/POST /client-ops/qms-tags`,
    `PUT .../{tag_key}`, `PATCH .../deactivate`/`.../reactivate`. All three
    client-ops-adjacent roles (admin, onboarding_manager,
    department_manager) can maintain it via a new `client_ops.manage_tags`
    permission — Boris's call, since this is a stand-in for QMS one day
    exposing tags via its own API, not a client operation in its own
    right. Every mutation writes to a new `client_ops.audit_log` — a
    distinct, non-security operations trail, separate from
    `auth.auth_audit_logs` on purpose (same access-boundary reasoning
    already locked for Admin vs. client-ops data). 305 tests passing.
  - **Phase 2 (rule-based candidate detection for easy fields)** — next up,
    paused for discussion before starting.
  - **Phase 3 (harder judgement calls: `d.now` vs. `m.indate`, "no tag
    exists")** — a real future candidate for the dormant
    `src/ai/interface.rs` stub in `unitprep-api`, confirmed genuinely
    unbuilt (declared, zero call sites), not started.
- **OM output storage: write back to the client's Dropbox folder, not a DB
  or S3.** Resolved 2026-08-07 for all OM-produced output (formatted
  templates, dedup/unit-group CSVs) — reuses the same "user already granted
  folder access" mechanism [[Platform Vision (Onboarding Orchestrator)]]
  established for *reading* client folders, just applied to writing a
  finished file back. No new infrastructure needed; defers real
  object-storage work indefinitely, consistent with Grok's already-rejected
  Postgres-blob-as-stopgap call.
- **Go-Live Readiness Auditor.** The single most concrete new item from
  today. Full checklist mapping in [[QMS API - Tool Opportunities]] — roughly
  a third of the manual pre-go-live/go-live-day checklist is a clean
  one-click API check (Coverage, Specials, unit counts, the Elavon/credit-
  card probe, payment scheme, reservation days, and the whole Security
  Deposit/Recurring Fees/Admin Fee/Transfer Fee cluster via one
  `move-in-charges` call). Blocked only on the QMS base URL (see Blocked
  section) and auth wiring, not on any unresolved design question.
- **Per-user session management for admins** (list a specific user's active
  sessions, remote sign-out). Named in the original admin-panel scope, never
  built — see [[Auth & Persistence Index]] "Next in the build."
- **Admin correction of email on an unenrolled account.** Approved
  2026-07-30, not built. Needs a `SECURITY DEFINER` function checking caller
  is admin, since `email` is outside `app_service`'s UPDATE grant — see
  [[Auth & Persistence Index]] "Approved, not built."
- **Logging gap fix**: a rejected registration attempt currently writes no
  audit row, while a failed login does. Small, already-scoped fix — see
  [[Logging & Observability]].
- **PII column-classification convention** (from Grok, accepted). Schema
  comments tagging `pii`/`sensitive_pii`, nothing automated. Cheap habit,
  adopt the moment the tenant/unit schema is first written — see
  [[response-to-groks-tenant-piigdpr-implementation-suggestions|the Grok
  response]].

## Tier 2 — needs one design decision first, then buildable

- **Occupancy as a link table** (tenant↔unit↔dates), from Grok, accepted.
  Not urgent by itself — becomes load-bearing the moment the tenant/unit
  schema actually gets designed, which per [[Platform Vision (Onboarding
  Orchestrator)]] hasn't started yet. Bank the decision, don't build the
  schema early.
- **Redacted-summary vs. full-detail views**, from Grok, accepted. Same
  timing as the item above — a convention to apply *when* tenant data starts
  flowing through Orchestrator's own UI, not before.
- **Data Subject Request workflow** (`data_subject_requests` table,
  staff-mediated inventory → export → anonymize), from Grok, accepted.
  Gives the long-standing "erasure/anonymize path" item (see [[Auth &
  Persistence Index]] "Trigger-gated") an actual shape — still trigger-gated
  on the first EU user / enterprise security review / customer DPA, per that
  note, but no longer purely abstract.
- **Anonymize-in-place as its own operation**, distinct from soft-delete,
  from Grok, accepted. Same trigger as the DSR workflow above — design once,
  together, rather than as two separate efforts later.
- **The audit-vs-erasure decision**: does anonymizing a tenant also scrub
  audit rows referencing them, or is there a documented security-retention
  exception? From Grok, logged as a real open decision, not resolved. Worth
  deciding in writing whenever the DSR workflow above gets designed, not
  improvised per-request later.
- **Dual-approval specifically for admin role changes** (distinct from the
  now-shipped `department_manager` credential-approval flow — see the
  correction above, don't conflate the two). Recommended *not* to build
  yet — needs a genuine second active admin to mean anything, otherwise
  it's the same person approving their own request through an extra click.
  Interim compensating control already identified: make
  `role_changed`/`user_deactivated` prominent on the admin Users page. See
  [[Roles & Permissions — Design Discussion]].

## Tier 3 — trigger-gated, watch for the trigger rather than schedule

- **Groups (client-scoped access)** — deferred in v1 as hypothetical
  ("there's effectively one real user today"). Grok's point that it should
  exist before tenant PII spans many clients is fair; the deferral's own
  "wait for a real need" condition may be close to firing once the
  client/tenant schema lands. Watch for that schema landing as the trigger —
  see [[Roles & Permissions — Design Discussion]].
- **Retention TTL as an enforced scheduled job**, from Grok, accepted.
  Trigger: the lease tool starts producing exports.
- **Should `admin` see financial data** — deferred, no trigger yet (no
  financial data flows through the system today). See [[Roles & Permissions
  — Design Discussion]].
- **Step-up re-auth** (Phase 4) — not started, no trigger. If device-bound
  credentials are ever revisited, this is where they'd belong.
- **`totp_credentials.secret_encrypted` encryption at rest** — deferred to
  task 9, no new trigger since.
- **Cloudflare Access/ZTNA, KMS/secrets-at-rest, real ESP integration** —
  long-standing trigger-gated infra items, unchanged. See [[Build Plan &
  Infra Checklist]].
- **Profile page** (personal info, activity-log tab) — idea captured, not
  scheduled. See [[Roles & Permissions — Design Discussion]] "Ideas
  captured, not yet built."

## Blocked (not a design question — waiting on external input)

- **QMS base URL.** The spec's `servers` field is empty; Boris is checking
  with a colleague. Blocks the Go-Live Auditor and any other live QMS-API
  work, full stop — see [[QMS API Index]].
- **Whether Basic auth calls protected QMS endpoints directly, or only
  bootstraps `/login`** — same conversation as the base URL, per [[QMS API
  Index]]'s Auth section.

## Explicitly not doing (from Grok's review, rejected, still valid)

Field-level encryption (data minimization instead), a self-service
tenant-facing portal (out of scope — tenants aren't Orchestrator's users), a
single unified `audit.events` table (conflicts with the locked Admin/
client-ops access-boundary split), document bytes in Postgres as a v1
stopgap (go straight to object storage when actually needed), and day-one
per-view PII logging (log meaningful events only). Full reasoning in
[[response-to-groks-tenant-piigdpr-implementation-suggestions|the Grok
response]].

## Related

- [[Onboarding Orchestrator Kickoff — Session Log]] — first-hand session
  detail behind the roles/permissions thread, the build order, and the
  PII/compliance backlog this note consolidates, 2026-08-06/07
- [[QMS API - Tool Opportunities]] — full detail behind the Go-Live Auditor
- [[QMS Template Tags — Catalog & Editor Design]] — full detail behind the
  template editor
- [[Roles & Permissions — Design Discussion]] — full detail behind every
  roles/permissions item above
- [[response-to-groks-tenant-piigdpr-implementation-suggestions|Response to
  Grok's tenant-PII/GDPR implementation suggestions]] — full reasoning
  behind every Grok-sourced item, accepted and rejected
- [[Auth & Persistence Index]] — the "Still open" section this backlog
  consolidates and supersedes for planning purposes (that note keeps the
  detailed status; read this one for what to build next)
