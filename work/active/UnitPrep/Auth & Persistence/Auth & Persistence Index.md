---
date: 2026-07-27
description: "Entry point for the OO self-hosted WebAuthn/TOTP auth + persistence workstream: note map and what is still open. Task status lives in Phase 2 Progress."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# UnitPrep Auth & Persistence — Index

Self-hosted WebAuthn/TOTP auth and Postgres persistence for the Onboarding
Orchestrator (OO). Architecture locked 2026-07-20, schema + RLS built and
verified on Neon dev 2026-07-21, Phase 2 Rust implementation in progress.

**Passkey registration and sign-in work end to end** — verified through a real
browser against a real Neon branch with three separate credentials (Windows
Hello twice, and Proton Pass), not only in tests. Shipped in `unitprep-api`
v1.2.0.

> [!note] Task status lives in [[Phase 2 Progress]], deliberately
> Which of the eleven Phase 2 tasks are done is volatile and belongs in exactly
> one place. This note previously restated it and drifted within a day. Go there
> for the current count; come back here for the map and the open questions.

## Notes

- [[Architecture]] — locked v1 decisions: self-hosted passkeys+TOTP, opaque
  session cookie (not JWT), Postgres/Neon, Admin>Security nav design, roles/RLS
  scope. Also records the reversal of the device-bound requirement.
- [[Build Plan & Infra Checklist]] — priority-ordered phases 1-4, trigger-gated
  deferred work (Cloudflare Access, KMS, ESP), Neon/infra setup status.
- [[Database Schema]] — the 7 core tables, conventions, columns. Includes the
  `auth` schema move that went undocumented for six days.
- [[RLS Implementation]] — `app_service` role, per-table policies, the
  `SECURITY DEFINER` functions, the column-level restrictions, and the pooler
  saga with its mid-session correction.
- [[Phase 2 Progress]] — **current status**, the 11-task order, and the
  constraints that bind tasks not yet written.
- [[Phase 2 Progress — Task Log]] / [[Phase 2 Progress — Task Log 2026-07-29]] —
  per-task detail, split by session era.
- [[Phase I Hardening — Session Log]], [[Phase I Route Gating & Frontend
  Kickoff — Session Log]], [[TOTP Redesign & Phase I Closeout — Session
  Log]], [[Phase II Hardening — Session Log]], [[Phase II Closeout & Auth
  Backlog — Session Log]] — first-hand build detail for Phase I's backend
  hardening (guardrail, audit coverage, rate limiting, recovery), route
  gating, and frontend build-out; the TOTP step-up redesign; and Phase II's
  session/anomaly hardening plus the post-close-out backlog. Recovered from
  inbox/loose-file drift and consolidated 2026-08-10, split across five
  notes by topic/size, 2026-07-31 through 08-04.
- [[Logging & Observability]] — assessment of the log/audit split, the one gap
  that is a bug, and an approved roadmap.
- [[Admin Panel & Audit Logs Polish — Session Log]] — first-hand build detail
  for the reactivate-user action, last-admin guard, dormant indicator, and
  audit-log steps 2-5 (cosmetics, lazy-load, CSV export, PDF export polish),
  2026-08-05/06.
- [[Session 2026-07-29 — Auth Tasks 4, 5, 8 and Infrastructure Fixes]] — the
  most recent handoff: what shipped, what was decided, what is open.
- [[Roles & Permissions — Design Discussion]] — **ongoing effort, started
  2026-08-04**, added to gradually rather than closed out in one pass. The
  "raise least privilege at the right moment" item below is what triggered
  it.
- [[Roles & Permissions — Design Finalization Log]], [[Roles & Permissions —
  Backend Build Log]], [[Roles & Permissions — Frontend Build & Ship Log]] —
  first-hand detail for step 1 (closing design rounds, schema, authorization
  core, frontend, commit/push), 2026-08-06/07, split across three notes.
- [[Compliance & Process Readiness]] — SOX/SOC2/CCPA/GLBA/PCI assessed
  against UnitPrep's actual data profile, plus CI/CD and availability/
  recovery — preemptive, explicitly not urgent.
- [[Orchestrator Feature Backlog]] — **consolidated planning view, 2026-08-07**
  — pulls this note's "Still open" section together with Grok's accepted
  suggestions and the QMS-API-shaped features found the same day, organized
  by what's buildable now vs. blocked vs. trigger-gated. Read that note for
  "what to build next"; this section stays the detailed source of record.

## Current status (2026-08-05) — read this before anything below

Both Phase I (ship it, enforce it) and Phase II (hardening) are **closed
out**, plus a full post-Phase-II backlog: disable-user, an admin audit-log
viewer (with `ip_address`/before-after diffing finally populated),
`rate_limit_rejected`/`session_expired_access_attempt`/`authorization_failure`
audit events, the `onboarding_manager` role, invite-time and after-the-fact
role assignment, a last-remaining-admin guard, and a dormant-account
indicator. Both repos pushed to `origin/main`. **Next: QMS API integration**
— that's the actual reason this whole auth effort exists. See
[[Roles & Permissions — Design Discussion]] for the now-ongoing permissions
work, and [[Compliance & Process Readiness]] for the deferred bureaucratic
bucket. Most of the "Still open" section below predates this and is
historical — check each item's own date before trusting it's still current.

## Still open

**Needs Boris, whenever convenient**

- `app_service` has **no password on the prod branch**. Not needed until a
  deployment exists. Connect with `NEON_PROD_DATABASE_URL_DIRECT`, run
  `\password app_service`, then replace the placeholder in `.env.local`'s
  `NEON_PROD_DATABASE_URL_APP`. Nothing reads it yet. **Still true as of
  2026-08-05** — no deployment exists yet.
- **Break-glass access documentation** (who besides Boris can reach
  `TOTP_ENCRYPTION_KEY`, DB credentials, hosting/Neon account access) — only
  Boris knows the actual facts here; a template exists, needs him to fill it
  in. Named in `AUTHENTICATION.md`'s Phase I item 9 since 2026-07-30, still
  the one open half of that item.
- A quick check of Neon's actual backup/PITR settings (~10 minutes) — see
  [[Compliance & Process Readiness]].

**Next in the build**

- ~~The admin panel~~ — **built and since expanded well past its original
  scope** (Users, invites, recovery, disable, role assignment, audit-log
  viewer). See [[Compliance & Process Readiness]] and `AUTHENTICATION.md`'s
  Phase III section for exactly what shipped.
- ~~Remaining Phase 2 work (tasks 9-11)~~ — **done**, along with everything
  in Phase II and the post-Phase-II backlog above.
- **Per-user session management for admins** (list a specific user's active
  sessions, remote sign-out) — named in the original admin-panel scope,
  never built. Standalone deactivation covers "remove all access" but not
  "see and selectively revoke."

**Approved, not built**

- **Admin correction of the email on an account that has not enrolled**, then
  reissue. Agreed 2026-07-30. This is the answer to "an admin mistyped the
  invite address", which self-service profile editing cannot solve — the typo
  happens before anyone can authenticate, so there is no user to log in and fix
  it. Needs a `SECURITY DEFINER` function checking the caller is an admin, since
  `email` is deliberately outside `app_service`'s UPDATE column grant. Natural
  fit for the admin-panel work, and it makes the un-deletable-row problem mostly
  moot: you correct a mistyped invite rather than needing to remove it.

- Logging improvements — see [[Logging & Observability]]. One is a small bug: a
  rejected registration attempt is recorded nowhere.
- Notify-on-enrolment once an ESP exists ("X just enrolled", revoke as the
  response) — adopted instead of a blocking admin-approval step.
- ~~Least privilege as the role model grows — Boris asked for this to be raised
  at the right moment rather than pre-emptively.~~ **Raised 2026-08-04** —
  `onboarding_manager` shipped, making it a real question. Now its own ongoing
  effort, see [[Roles & Permissions — Design Discussion]].

**Undecided**

- `totp_credentials.secret_encrypted` encryption at rest — deferred to task 9.
- ~~`user_invites` partial-unique "one outstanding invite per user" constraint.~~
  **Settled 2026-07-30 without a constraint.** Both issuing paths — the
  `bootstrap-admin` CLI and `POST /auth/invites` — retire outstanding invites
  before minting, so at most one is ever live per account. The invariant is
  maintained by every writer rather than enforced against writers that would
  break it. Revisit only if a third issuing path appears, since the argument
  rests on there being no path that skips the retirement.
- Step-up re-auth (Phase 4) — not started. If device-bound credentials are ever
  revisited, this is where they belong: per-action, not per-account.

**Trigger-gated, no trigger yet**

- Cloudflare Access/ZTNA, KMS/secrets-at-rest, real ESP integration.
- **An erasure / anonymize path for personal data.** Today there is none: soft
  delete keeps `email`, `first_name` and `last_name` intact indefinitely, and a
  user with audit history cannot be hard-deleted by anyone. That is fine for
  10-100 internal employee accounts at one US company, and it is *not* the thing
  a reviewer would call overkill — append-only audit trails are expected in
  SOC 2 / PCI / HIPAA / SOX contexts. What a reviewer would raise is **right-to-
  erasure** (GDPR Art. 17, CCPA/CPRA analogues), which normally expects PII to be
  anonymizable while the audit trail survives.

  **Boris's chosen remedy for when it matters: the hybrid — keep the foreign
  keys, add an anonymize path** (tombstone name/email, or encrypt PII under a
  per-user key and destroy the key). Deliberately deferred: it is *additive*
  later rather than a rewrite, so nothing is being locked in by waiting.
  Explicitly rejected in passing: dropping the FKs in favour of denormalized
  identity snapshots in the audit rows — that trades a referential guarantee for
  PII sitting in the log.

  **Triggers to raise it**: the first EU-based user, the first enterprise
  security review, or the first customer DPA. Being able to say "we identified
  this and scoped the fix" is a much stronger review position than having it
  found for you.

## Standing facts worth not rediscovering

- **Restore requires re-enrolment.** Deactivating or soft-deleting a user removes
  their passkeys by trigger. History survives; the credential does not.
- **A user with audit history cannot be hard-deleted by anyone**, including the
  owner role. Soft delete is the only delete. This is intended.
- **Prod is provisioned but parked.** **Dev is one migration ahead as of
  2026-07-30** — dev 24, prod 23, the gap being
  `20260730120000_invite_registration_lookup`. Policy is dev-only by default,
  with a sync recommended when pending migrations accumulate; one is not yet
  worth a sync, but this is the counter to watch.
- **No sign-out exists yet**, so sessions accumulate and cannot be revoked.
