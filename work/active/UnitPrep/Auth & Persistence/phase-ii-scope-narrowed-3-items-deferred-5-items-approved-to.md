---
date: 2026-08-04
description: "Boris reviewed the 8-item Phase II backlog (auth-hardening-two-phase-plan) and made a scope call: defer hardware-bound passkey policy, KMS for the TOT"
tags:
  - decision
source_repo: bmaksimov
---

# Phase II scope narrowed — 3 items deferred, 5 items approved to proceed one at a time

Boris reviewed the 8-item Phase II backlog (auth-hardening-two-phase-plan) and made a scope call: defer hardware-bound passkey policy, KMS for the TOTP key, and the formal external pentest indefinitely. The remaining five items (session/TOTP hardening, anomaly/risk signals, threat model/control matrix, audit retention & review docs, ceremony-state scaling fix) are approved to build now, one task at a time, starting with session/TOTP hardening.


## Decisions

- Hardware-bound passkey policy: deferred, not rejected. Whether to require security-key-only credentials (all users, admins only, or optional) is a team decision that hasn't happened yet — no point building enforcement (authenticatorAttachment hint + backup_eligible check, see [[WebAuthn credential-binding policy (hardware-key-only) is]]) ahead of that call.
- KMS for TOTP_ENCRYPTION_KEY: deferred. Boris is not ready to sign up for a cloud provider (AWS/GCP/Azure) at this point, and self-hosted Vault wasn't preferred either. The key stays in a plain environment variable for now. Revisit if/when there's already a reason to be provisioning cloud infra.
- Formal external pentest: deferred, very low priority right now, and Boris is not sure it will ever be needed for this project. Still worth knowing it's the single highest-leverage move for external-audit credibility (adversarial/empirical vs code review) if a demanding audit ever comes up.
- Approved to build now, sequentially: (2) session/TOTP hardening — idle+absolute session expiry, SameSite=Strict cookies, TOTP replay window; (4) anomaly/risk-based auth signals; (6) formal threat model/control matrix; (7) audit retention & review process documentation; (8) ceremony-state horizontal-scaling fix (low urgency — only matters if unitprep-api ever runs multi-instance).
- Starting order: session/TOTP hardening first, since it's the most concrete and highest-value of the remaining five.




## Open

- Team hasn't yet decided whether hardware-bound passkeys are needed at all.
- KMS service-vs-library choice remains unmade and now has no near-term trigger.
- Pentest scope/vendor/timing unset and deprioritized — may never happen for this project.
- Anomaly/risk-based auth design not started.
- Ceremony-state scaling fix stays deferred until unitprep-api actually needs multiple instances.


## Related

- Auth hardening — two-phase plan (Phase I: ship & enforce, Phase II: iron-clad hardening) _(no note yet)_
- Auth security assessment (backend-only, 2026-07-30) _(no note yet)_


_Recorded 2026-08-04T17:21:10.811Z from `bmaksimov` via the om MCP server (routing: caller)._
