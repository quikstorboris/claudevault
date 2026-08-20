---
date: 2026-08-03
description: "Had Grok and Copilot independently review AUTHENTICATION.md and the broader codebase. Both converged on the same shape as the existing Phase I/II plan"
tags:
  - decision
source_repo: bmaksimov
---

# Auth roadmap revised after external review (Grok + Copilot, 2026-07-31)

Had Grok and Copilot independently review AUTHENTICATION.md and the broader codebase. Both converged on the same shape as the existing Phase I/II plan (rate limiting and route gating as the top gaps, correctly sequenced) — useful external confirmation. Two concrete gaps surfaced that weren't previously written down anywhere and got folded into Phase I; one item the reviews flagged as pending was actually already shipped.


## Decisions

- Added Phase I item: decide the tool-session (unit_group/dedup) ownership rule BEFORE gating product routes, not after. owner_id already exists on the tool-session model and is always None today - once every request carries an AuthenticatedUser this stops being neutral, and Grok correctly flagged that leaving it implicit invites a messy retrofit once real user data exists in those sessions. Sequenced immediately before route gating in the plan since gating is what forces the question.
- Added Phase I item: decide the role model (Role enum is structured for more than Admin, but nothing beyond Admin is used yet) before building the admin Users panel, since that panel will force the question (who can view users / create invites / revoke sessions) one way or another regardless.
- Added guidance to the frontend-build Phase I item: keep auth request/response shapes (WebAuthn ceremony payloads, TOTP bodies, session/user shape) in one place both FE and BE can check against, even just a hand-maintained shared types file - cheapest moment to start this discipline is now, while both sides are being written fresh, not after they exist and disagree. This addresses Grok's OpenAPI/contract-drift concern scoped to just the auth surface rather than the whole API.
- Widened the existing single-admin break-glass Phase I item: 'the bootstrap CLI still works' and 'someone besides the current admin could actually reach what break-glass needs (TOTP_ENCRYPTION_KEY, DB credentials, hosting/Neon access)' are different claims - only the first was previously covered. Motivated by Copilot's bus-factor-1 observation, but scoped to the credential-custody angle rather than the broader organizational risk, which stays explicitly out of this document.
- Corrected the roadmap doc: SESSION_COOKIE_SECURE fail-fast guardrail (shipped earlier the same day) was still listed as pending in Grok's review - marked as already shipped in AUTHENTICATION.md rather than left in the TODO list.
- Explicitly declined to fold in: dual UnitGroup/Group Prep naming, sessionStorage-only tool-session client data, and API-wide OpenAPI generation - all real per the reviews, but platform-general rather than auth-specific, recorded in a new 'Noted, deliberately outside this document's scope' section instead of silently dropped or scope-creeping the auth roadmap.



## Verification

Recalled the vault first for any prior decision on tool-session ownership or role-model expansion (query: 'tool session owner_id ownership role model admin operator viewer') - no matching prior note found across Database Schema, RLS Implementation, Phase 2 Progress, or Build Plan, confirming these are genuinely new rather than restating an existing decision.



## Related

- Auth hardening — two-phase plan (Phase I: ship & enforce, Phase II: iron-clad hardening) _(no note yet)_
- Shipped: fatal startup guardrail against SESSION_COOKIE_SECURE=false on a real deployment _(no note yet)_


_Recorded 2026-08-03T15:19:41.871Z from `bmaksimov` via the om MCP server (routing: caller)._
