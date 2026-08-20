---
date: 2026-08-07
description: "Grok reviewed UnitPrep's future tenant-PII/GDPR posture and proposed 13 implementation ideas ahead of the tenant/unit schema actually being designed. "
tags:
  - decision
source_repo: bmaksimov
---

# Response to Grok's tenant-PII/GDPR implementation suggestions

Grok reviewed UnitPrep's future tenant-PII/GDPR posture and proposed 13 implementation ideas ahead of the tenant/unit schema actually being designed. Evaluated each against what the vault already has decided (erasure/anonymize path, Groups deferral, audit-vs-ops-log split, SOC2/CCPA assessment) rather than in the abstract — 8 are genuinely new ground worth banking as defaults for whenever that schema work starts, 5 are rejected as premature, out of scope, or conflicting with a locked decision.


## Decisions

- Worth banking: a data_subject_requests table plus staff-mediated inventory -> export -> anonymize workflow. Nothing this concrete existed before — the vault only had 'controls will be needed eventually' in the abstract (Auth & Persistence Index, trigger-gated erasure section). Gives the eventual GDPR/CCPA work an actual shape to design against once real tenant PII lands.
- Worth banking: anonymize-in-place as its own DB operation distinct from soft-delete — scrub PII fields, keep the row/id so occupancy history and audit references stay intact. auth.users already has soft-delete; this is the same 'keep the FK, add an anonymize path' hybrid Boris already chose for users (Auth & Persistence Index), just noting it needs to exist for tenants specifically once that table is designed, not reinvented later.
- Worth banking: occupancy as a link table (tenant<->unit<->dates) rather than copying tenant PII onto every unit row. Pure default-to-bank since the tenant/unit schema doesn't exist yet — cheap to decide now, expensive to retrofit after unit rows already carry denormalized PII.
- Worth banking: redacted-summary vs full-detail views at the API layer — list screens never carry full PII, detail view costs an extra permission check and gets logged. Consistent with the existing 'log meaningful events, not every view' stance (Logging & Observability) — this is the list/detail split that makes that stance concrete for tenant data specifically.
- Worth banking: retention TTL as an enforced scheduled job, not a remembered policy. Flagged as becoming relevant the moment the lease tool starts producing exports — not urgent today, banked for that trigger.
- Worth revisiting timing on: Groups (client-scoped access — which OM sees which client). Architecture.md deferred Groups in v1 as hypothetical ('there's effectively one real user today'). Grok's point that it should exist before tenant PII spans many clients is fair — the deferral's own condition ('wait for a real need') may be close to firing once the client/tenant schema (an actual prerequisite, not this decision) lands. Not resolved now, flagged to reopen at that trigger rather than pre-emptively building it.
- Worth banking: a light PII column-classification convention — schema comments tagging pii/sensitive_pii, nothing more automated. Cheap habit, adopt when the tenant schema is first written rather than retrofitting labels later.
- Decided explicitly, in writing, as a real open question rather than deferring silently: does anonymizing a tenant also scrub audit rows that reference them, or is there a documented security-retention exception? Not answered yet — logged as a decision that needs making once, deliberately, rather than improvised ad hoc when the first real request arrives.
- Rejected: near-term field-level encryption. Data minimization beats encrypting data that shouldn't be held at all; revisit only if something genuinely sensitive (SSN, gov ID) is proposed, and the right answer there is 'don't store it', not 'encrypt it'. Consistent with Compliance & Process Readiness's existing data-profile assessment (no SSN/CC today).
- Rejected: a self-service tenant-facing portal. Out of scope entirely — tenants aren't UnitPrep's users (UnitPrep is Quikstor-internal, used by implementation managers per Platform Vision), and nothing in the platform vision suggests they ever will be.
- Rejected: a single unified audit.events table spanning auth and client-ops with a domain column. Conflicts with an already-locked access-boundary split (Admin structurally excluded from client-ops audit) — keep separate tables, not one table filtered by column.
- Rejected: storing document bytes in Postgres as a v1 stopgap for the lease tool. Skip the detour — when the lease tool actually needs file storage, go straight to real object storage rather than building throwaway blob-in-Postgres debt.
- Rejected: logging every PII detail-page view as a day-one requirement. Log the meaningful events (export, anonymize, bulk access) now per the existing Logging & Observability stance; full per-view logging is a control to add once there's an actual compliance trigger, not preemptively — mirrors the 'raise it at the right moment, not speculatively' pattern already used for Groups and least-privilege.




## Open

- No tenant/unit/occupancy schema exists yet — everything here is a default to apply *when* that schema gets designed, not a spec to build now.
- The audit-vs-erasure tension (does anonymize scrub audit rows referencing the tenant, or is there a security-retention exception) is logged as unresolved, matching how the vault already tracks the analogous users-table question.
- Groups/client-scoped access timing: watch for the client/tenant schema actually landing as the trigger to reopen the deferral, per Roles & Permissions — Design Discussion's pattern of raising least-privilege questions at the right moment rather than pre-emptively.


## Related

- [[Auth & Persistence Index]]
- [[Roles & Permissions — Design Discussion]]
- [[Compliance & Process Readiness]]
- [[Architecture]]
- [[Platform Vision (Onboarding Orchestrator)]]
- [[Logging & Observability]]


_Recorded 2026-08-07T17:56:07.657Z from `bmaksimov` via the om MCP server (routing: caller)._
