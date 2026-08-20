---
date: 2026-08-04
description: "Boris asked to log two ideas raised while discussing the anomaly-signal work (2026-08-04) so they resurface when their triggers actually fire, rather "
tags:
  - decision
source_repo: bmaksimov
---

# Two Phase II follow-on features logged, trigger-gated for later

Boris asked to log two ideas raised while discussing the anomaly-signal work (2026-08-04) so they resurface when their triggers actually fire, rather than getting lost. Neither is being built now -- both are explicitly "revisit later," and Boris confirmed he wants both revisited when the right time comes.


## Decisions

- Cloudflare-driven geolocation upgrade -- trigger: Cloudflare (Access/ZTNA/CDN, any of it) gets put in front of unitprep-api, which is already tracked as a trigger-gated initiative in [[Build Plan & Infra Checklist]] for other reasons. When that happens, do two things together, not separately: (1) decide a trusted-header policy -- only trust Cloudflare's own headers (CF-Connecting-IP, CF-IPCountry) when the request's real TCP origin is one of Cloudflare's published edge IP ranges, or the anomaly signal becomes spoofable by anyone who can set that header directly; (2) once trusted, upgrade the Phase II anomaly signal (see [[Phase II item 4 shipped: anomaly/risk-based login signals (new IP/device, gated TOTP step-up)]]) from 'new IP address' to 'new country/region' using CF-IPCountry -- no MaxMind/GeoIP database needed, Cloudflare's edge already resolves it and hands it over free in the header. Both of these were already the open item this session's ip_address/ConnectInfo work left behind (direct-exposure topology, no proxy trusted yet).
- HMAC-signed 'remember this device, skip step-up' cookie -- trigger: step-up friction becomes a real annoyance (e.g. an admin repeatedly hitting the anomaly gate on their own regular but IP-shifting device, like a laptop that roams between home/office/mobile-hotspot), or an explicit ask to reduce step-up frequency for trusted devices. Not needed for anything shipped so far -- the current design (audit + gate) only ever compares a login against the server's own session-history database, so there is no client-supplied claim to protect with a keyed MAC. It becomes the right tool the moment there's a genuinely new primitive: a client-held credential asserting 'this specific browser already proved a step-up once' that the server must not blindly trust. Design sketch for when it's built: HMAC over (user_id, device_id, expiry) keyed by a server-side secret (mirrors the existing TOTP_ENCRYPTION_KEY pattern -- an app-level secret, KMS-deferred same as that one), verified statelessly or with a DB round-trip for revocation, distinct from the session cookie and from the existing elevated_until step-up-for-sensitive-actions mechanism. Would be the first client-trusted signed claim in an architecture that has otherwise deliberately avoided them (opaque session tokens verified by DB lookup, not JWTs) -- worth re-confirming that tradeoff explicitly when actually designing it, not assuming the answer is yes just because the primitive is cheap.




## Open

- Neither feature has a scheduled date -- both are pure trigger-gated backlog, consistent with how Cloudflare Access/KMS/ESP are already tracked in [[Build Plan & Infra Checklist]].


## Related

- Phase II item 4 shipped: anomaly/risk-based login signals (new IP/device, gated TOTP step-up) _(no note yet)_
- [[Build Plan & Infra Checklist]]


_Recorded 2026-08-04T19:00:28.165Z from `bmaksimov` via the om MCP server (routing: caller)._
