---
date: 2026-07-31
description: "A user can already voluntarily choose a hardware security key over a synced/platform authenticator at the browser's credential picker — that requires…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-31T16:18:24.552Z"
scope: general
projects: []
confidence: inferred
---

# WebAuthn credential-binding policy (hardware-key-only) is enforceable with a small targeted check, not a new capability

A user can already voluntarily choose a hardware security key over a synced/platform authenticator at the browser's credential picker — that requires zero backend change, since the browser offers whatever authenticators are present regardless of server-side code. But *mandating* hardware-bound credentials (rejecting synced ones) is not purely a policy/communication decision — it needs two small, well-scoped code changes, both reusing data a WebAuthn registration ceremony already produces:

1. Set `authenticatorAttachment: "cross-platform"` in the `PublicKeyCredentialCreationOptions` sent to the browser at registration-begin, so the browser's picker only *offers* external authenticators (security keys) in the first place — better UX than accepting then rejecting.
2. At registration-finish, check the credential's `backup_eligible` flag (part of WebAuthn Level 3 authenticator data) — already commonly captured as a `device_bound` column in any reasonably-designed schema — and reject the registration if policy requires a hardware-bound factor.

Neither change touches the verification library's core logic; both are additive checks around data the ceremony already surfaces. Worth knowing before quoting "hardware-key enforcement" as either free (it's not, quite) or as a big lift (it's also not) — it lands in an unusually cheap middle ground because the enforcement signal already exists in the protocol, it just isn't read for gating purposes by default.

## How this is known

Reasoned from the WebAuthn Level 3 spec's authenticator data flags and from webauthn-rs's typical registration option builder API; not verified against a live enforcement implementation in this codebase, since this policy hasn't been built yet.

## Related

- [[Architecture]]
