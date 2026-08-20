---
date: 2026-07-30
description: "Two records exist in most systems that have any audit requirement, and they do different jobs: - **ops telemetry** (`tracing`, structured logs) —…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-30T16:54:09.735Z"
scope: general
projects: []
confidence: verified
---

# Raise logging improvements while already touching that code — and judge the audit trail separately from the ops log, because a gap hides between them

Two records exist in most systems that have any audit requirement, and they do different jobs:

- **ops telemetry** (`tracing`, structured logs) — *what is happening now*, ephemeral, read during an incident
- **the audit trail** (a table, append-only) — *what happened*, permanent, read for forensics and compliance

The failure mode is judging them together. A path can be adequately logged and still be a hole in the audit trail, or vice versa. Check each separately, and specifically look for **asymmetry between comparable paths**: if a failed sign-in writes an audit row but a rejected registration writes nothing, that difference is almost never intentional, and it means one class of probing is invisible while an identical class is recorded.

Worth knowing: recording a rejection server-side leaks nothing even when the HTTP response is deliberately indistinguishable to the caller. Indistinguishable-to-the-attacker and invisible-to-the-operator are different properties, and conflating them loses the second for free.

**What good looks like, as review criteria rather than volume:**

- Structured fields, not values interpolated into prose — `user_id=…`, not `"user 123 did x"`. Queryable later at no extra cost now.
- Identifiers, not personal data. A UUID in a log is fine; an email address accumulates PII in a place with weak access control. (The audit *table* may legitimately store an attempted address, since an unmatched address is data about the attempt rather than an identity — and that table is access-controlled.)
- Severity that means something. A cancelled browser prompt is `warn`; a database failure is `error`. If everything is `info`, severity carries no information.
- A **correlation id** for anything spanning more than one request. Two-request ceremonies (WebAuthn, OAuth) are the obvious case: without one, concurrent attempts by the same user are indistinguishable in the log, and the id usually already exists in the code.
- Log both the start and the completion of a multi-step flow, so one that starts and never finishes is visible.
- Never log secrets: tokens, challenges, credential blobs.
- Audit writes must not be able to fail the operation they describe — otherwise breaking audit writes becomes a denial of service on the thing being audited.

**On timing**: raise these while already editing the handler, adding the endpoint, or touching that surface. Logging work saved up into a separate initiative competes with features and loses; folded into work already in flight it costs almost nothing. A user who cares about observability would rather be asked "want a correlation id while I'm in here?" than handed a backlog.

## How this is known

Assessment done on unitprep-api 2026-07-30 against real server output from a full passkey session; Boris approved the resulting roadmap including the deferred items and asked that opportunities be flagged proactively ("I love me a good log"). The asymmetry described was confirmed empirically, not inferred: a 403 rejected registration produced no tracing line and zero matching rows in auth_audit_logs, while a failed login on the same deployment wrote a login_failed row. The correlation-id gap was likewise concrete — begin and finish log lines carried only user_id, and the ceremony id already existed in the handler.

## Related

- [[Logging & Observability]]
- [[Database Schema]]
- [[RLS Implementation]]
