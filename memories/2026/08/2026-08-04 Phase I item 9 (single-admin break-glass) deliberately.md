---
date: 2026-08-04
description: "Boris explicitly decided 2026-08-04 to leave Phase I item 9 (\"confirm the single-admin break-glass path\") untouched for now, rather than have it…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-04T17:08:42.295Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# Phase I item 9 (single-admin break-glass) deliberately deferred, not abandoned -- bootstrap-admin CLI is accepted as sufficient while Boris is the only admin

Boris explicitly decided 2026-08-04 to leave Phase I item 9 ("confirm the single-admin break-glass path") untouched for now, rather than have it built/verified. His reasoning: while he is the only person on the platform, he has full code and database access himself, so the CLI (`bootstrap-admin --reissue-invite`, or direct DB/psql access) is a perfectly adequate break-glass path in practice -- there is no user-facing gap yet because there is no user who lacks his level of access.

This is a conscious risk acceptance, not an oversight -- the gap (an admin locked out with no CLI/DB access of their own, and no other admin to recover them) becomes real exactly when a second admin exists who does NOT have Boris's own infrastructure access. That is the condition under which this should be revisited, and it is a different trigger from Pending admin-recovers-fellow-admin test's trigger (which fires on ANY second admin existing, for a different, already-built feature -- multi-admin mutual recovery). Item 9 specifically needs a second admin WITHOUT infra access to become urgent.

With this deferred, Phase I's full 9-item list (see Auth hardening two-phase plan) is otherwise complete: audit-coverage verification, rate limiting, the audit-logging asymmetry fix, the HTTPS/SESSION_COOKIE_SECURE guardrail, the recovery flow, gating every product/tool route behind AuthenticatedUser, the full frontend build-out, and the admin Users tab are all shipped. Everything else in that plan's "Open" section (pentest, anomaly detection, KMS, hardware-bound passkey policy, ceremony-state scaling) was always Phase II or trigger-gated, never Phase I.

##### How this is known

Boris's direct instruction 2026-08-04, immediately after being told item 9 was still open and untested: "let's leave it alone for now. bootstrap is fine for now, while i'm the only one on the platform and i have full access to code and DB."

## How this is known

Direct instruction from Boris, quoted verbatim above.
