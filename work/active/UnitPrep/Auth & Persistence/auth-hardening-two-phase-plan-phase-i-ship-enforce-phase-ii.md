---
date: 2026-07-31
description: "Consolidated everything identified across the passkey-only enforcement discussion (recovery design, synced-credential tradeoff, GitHub LLM feedback, h"
tags:
  - decision
source_repo: bmaksimov
---

# Auth hardening — two-phase plan (Phase I: ship & enforce, Phase II: iron-clad hardening)

Consolidated everything identified across the passkey-only enforcement discussion (recovery design, synced-credential tradeoff, GitHub LLM feedback, hardware-key policy, KMS, pentest) into an ordered two-phase plan, plus a third bucket for trigger-gated items with no committed timeline. Boris proposed the two-phase split; this note captures the adjustments made (folding rate-limiting and route-gating into Phase I) and the full backlog.


## Decisions

- Phase I = task 11 (audit-coverage verification) + rate limiting on auth endpoints + the audit-logging asymmetry bug fix + an HTTPS-mandatory/SESSION_COOKIE_SECURE startup guardrail + the recovery flow (extend invite/reissue to allow revoke-and-reissue for an already-credentialed account, gated on manual out-of-band admin approval, no ESP required) + gating product/tool routes behind AuthenticatedUser + the full frontend build-out (WebAuthn client, API relay routes, login/invite/TOTP UI including QR rendering, session context, middleware gating, sign-out) + the Admin>Security>Users tab + confirming the single-admin break-glass path. Rate limiting and route-gating were added beyond the original 11-task list because 'enforce logins' isn't meaningfully true without them.
- Recovery flow deliberately does NOT use email/ESP: the locked-out user contacts the admin out-of-band (Teams/phone), which serves as the identity-reconfirmation step the original break-glass design called for; the admin then revokes the old credential and issues a new invite through the existing manual-link mechanism. This avoids introducing email-account-compromise as a new single point of failure and avoids taking on the still-undecided ESP dependency for a rare, small-volume event.
- Phase II = hardware-bound passkey policy (authenticatorAttachment hint + backup_eligible rejection check) + session/TOTP hardening (idle+absolute expiry, SameSite=Strict, TOTP replay window) + KMS for TOTP_ENCRYPTION_KEY (service-vs-library decision deferred to when built) + anomaly/risk-based auth signals + a formal external pentest + a formal threat model/control matrix + audit retention & review process documentation + the ceremony-state horizontal-scaling fix (only if multi-instance deployment is ever needed).
- ESP integration, Cloudflare Access/ZTNA, and the right-to-erasure/anonymize path are explicitly kept OUT of both phases as a separate 'trigger-gated, not scheduled' bucket, consistent with how they were already tracked in Build Plan & Infra Checklist - the two-phase plan should not be read as implicitly scheduling them.




## Open

- Formal external pentest scope and vendor/timing not yet decided - flagged by Boris as something to pursue, framed as the single highest-leverage action for external-audit credibility since it's adversarial/empirical rather than code review.
- Anomaly/risk-based auth detection design not started - Boris explicitly flagged this to revisit later (Phase II item).
- Ceremony state remains in-memory/single-instance - flagged by Boris for future discussion; only actually blocking if/when horizontal scaling of unitprep-api is ever needed.
- KMS service-vs-library choice (AWS/GCP/Azure KMS vs self-hosted HashiCorp Vault) undecided - apply the same framework already used for auth/DB/ESP when this is built.
- Hardware-bound passkey policy scope undecided - whether to require it for all users, admins only, or leave fully voluntary.


## Related

- Passkey-only enforcement readiness assessment: recovery-path gap, QR codes, frontend scope _(no note yet)_
- [[Architecture]]
- [[Build Plan & Infra Checklist]]
- [[Phase 2 Progress]]
- Auth security assessment (backend-only, 2026-07-30) _(no note yet)_
- [[Phase I Hardening — Session Log]], [[Phase I Route Gating & Frontend Kickoff — Session Log]], [[TOTP Redesign & Phase I Closeout — Session Log]], [[Phase II Hardening — Session Log]], [[Phase II Closeout & Auth Backlog — Session Log]] — first-hand execution detail for this plan, both phases


_Recorded 2026-07-31T16:18:38.279Z from `bmaksimov` via the om MCP server (routing: caller)._
