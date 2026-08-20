---
date: 2026-08-04
description: "Investigated Phase II item 8 (ceremony-state horizontal-scaling fix) before building it: the real scope turned out to be all four of AppState's InMemo"
tags:
  - decision
source_repo: bmaksimov
---

# Phase II closed out — item 8 scoped and deferred; disable-user and FE audit-log gaps found and queued

Investigated Phase II item 8 (ceremony-state horizontal-scaling fix) before building it: the real scope turned out to be all four of AppState's InMemorySessionStore instances, not just the two WebAuthn ceremony stores the item names, since unit-group and dedup tool sessions have the identical single-process limitation. With no multi-instance deployment planned, Boris deferred it -- same treatment as the three already-deferred items. That closes out Phase II: items 2, 4, 6, 7 shipped 2026-08-04, items 1, 3, 5, 8 are all deferred/trigger-gated, none scheduled. Two unrelated gaps surfaced from a real user bug report and questions this session and got explicitly ordered into the backlog: a missing disable-user admin action, and unreadiness for a frontend audit-log viewer.

## What changed

- AUTHENTICATION.md - Phase II section summary updated to reflect closeout; item 8 struck through and marked deferred with the real reason (scope spans all 4 in-memory stores, not just ceremonies)
- THREAT_MODEL.md - the multi-instance matrix row rewritten to name all four InMemorySessionStore instances rather than just WebAuthn ceremonies; 'Known gaps' section gained two new entries: no standalone deactivate-user endpoint/button, and auth_audit_logs' ip_address/before_state/after_state columns existing since the original schema but never populated by audit_log::record()
- CHANGELOG.md - Unreleased summary line updated to note item 8's deferral and Phase II's closeout


## Decisions

- Phase II item 8 deferred, not built -- reasoning: (1) no multi-instance deployment is planned or needed today (direct exposure, single process); (2) a real fix isn't ceremony-specific -- AppState holds 4 separate InMemorySessionStore instances (RegistrationCeremony, AuthenticationCeremony, unit-group sessions, dedup sessions), all with the identical process-local limitation, so doing this properly means replacing the store backend everywhere at once (Redis or Postgres-backed), a genuine infrastructure undertaking, not a small targeted change; (3) the in-memory design is arguably better for single-instance security today (WebAuthn challenge state never leaves the process) -- a shared external store would be a downgrade in the meantime for zero current benefit. This mirrors exactly why hardware-passkeys/KMS/pentest were deferred: don't build speculative infrastructure ahead of an actual trigger.
- Disable-user (a small new admin-gated endpoint reusing the already-built auth.set_user_status primitive, plus a frontend button) is explicitly queued as the NEXT task, right after this Phase II closeout -- found via a real user bug report ('disable user feature is not available in the FE') rather than being in the original Phase II scope.
- Frontend audit-log-viewer-per-user work is explicitly NOT ready to start -- confirmed gaps: no GET /auth/audit-logs listing endpoint exists at all; auth.auth_audit_logs.ip_address/before_state/after_state have existed in the schema since the very first migration but audit_log::record() has never written any of the three; Boris wants a before/after diff view (red for removed, green for added) plus IP/user info, which needs a real decision about which event types even have a natural before/after (a status change does, a login attempt doesn't) before the diff UI means anything. ISO 8601 (confirmed as the likely referenced standard, though from a pre-vault conversation with no other record) is the easy part -- created_at is already TIMESTAMPTZ and serializes to ISO 8601 by default; the before/after capture design is the real remaining work. Ordered after disable-user in the backlog.




## Open

- Disable-user: needs a new endpoint (something like POST /auth/users/:id/deactivate, admin-gated, wrapping auth.set_user_status) plus a frontend button in the admin Users table. Not yet started.
- FE audit-log viewer: needs (a) the listing endpoint, (b) audit_log::record() extended to capture ip_address (ConnectInfo is already available at every call site that matters) and, for event types where it makes sense, before_state/after_state, (c) a decision on which event types get before/after treatment at all, (d) the actual frontend diff-view component (red/green highlighting). Not yet started, not yet fully scoped.


## Related

- Phase II item 4 shipped: anomaly/risk-based login signals (new IP/device, gated TOTP step-up) _(no note yet)_
- Phase II items 6 and 7 shipped: formal threat model and audit retention docs _(no note yet)_
- Phase II scope narrowed — 3 items deferred, 5 items approved to proceed one at a time _(no note yet)_


_Recorded 2026-08-04T20:38:46.873Z from `bmaksimov` via the om MCP server (routing: caller)._
