---
date: 2026-07-30
description: "Two independent traps sit between \"the invite code is correct\" and \"I have seen the invite path work\"."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-30T21:14:00.236Z"
scope: general
projects: []
confidence: verified
---

# Testing a WebAuthn invite/registration flow: a stale session cookie silently hijacks the ceremony, and incognito hides password-manager passkeys

Two independent traps sit between "the invite code is correct" and "I have seen the invite path work". Both produce a **successful-looking** result, which is why they cost time.

**1. A session cookie beats the token, silently.**

Any sensibly-designed registration endpoint decides *who* a ceremony is for from the session when one exists, and ignores a client-supplied invite/enrolment token in that case — otherwise a signed-in user could redeem someone else's invite and plant a credential on that person's account. That is correct behaviour, and it means a browser tab that signed in five minutes ago will turn your invite test into "add another passkey to the account already signed in". The response is `200`, the log says registration complete, and the invite is left untouched — so nothing looks wrong until you query the database and find the invited account still has zero credentials.

Tells that it happened, all visible **before** the authenticator prompt:
- the `user.name` / `user.displayName` in the returned creation options is the signed-in account, not the invited one
- `excludeCredentials` is non-empty (an invite-eligible account has no credentials by definition)
- the finish response reports no new session was issued, since the caller already had one

**Make the harness print the target from the challenge it just received.** One line — `server says this ceremony is for: <user.name>` — converts a silent wrong-path into something impossible to miss. Do not have the client announce which path it *thinks* it is on; the client does not decide, the server does, and a client-side guess is exactly the misleading statement that hides this.

To actually get no cookie: **clear cookies for the origin in a normal window**, or use a different browser. Incognito works for the cookie but see below. Note there may be no sign-out endpoint yet in an auth build — logout is usually a later task than registration, so clearing cookies is the only lever available.

**2. Incognito disables extensions, which removes password-manager passkeys entirely.**

Browser extensions are off by default in incognito/private windows. A passkey held by Proton Pass, 1Password, Bitwarden and similar therefore becomes unreachable, and the browser offers only the platform authenticator and cross-device ("security key or other device"). This reads as a broken WebAuthn configuration or a rejected origin, and it is neither.

It bites **sign-in** much harder than registration, and the reason is worth knowing: with non-discoverable credentials (`residentKey: "discouraged"` / `requireResidentKey: false`) a `get()` can only be answered by an authenticator that actually holds one of the credential IDs in `allowCredentials`. If those live in the extension, the platform authenticator has nothing matching and is correctly not offered. A `create()` has no such constraint — nothing needs to be possessed yet — so registration still works in incognito via the platform authenticator, which makes the two cases behave differently and adds to the confusion.

Practical order of preference for a clean unauthenticated test: clear cookies in a normal window > a second browser you never signed in with > incognito.

**Worth checking once, and recording:** whether the credentials in play are synced or hardware-bound, since it determines whether they follow you to another machine at all. If the enrolment path stores a `device_bound`/backup-eligible flag, capture it **at enrolment** into the audit trail; read back from the credential row months later it cannot distinguish "enrolled as synced" from "row changed since".

## How this is known

Both hit directly on unitprep-api 2026-07-30 while verifying Phase 2 task 6. Trap 1: an invite-token registration returned 200 with session_issued:false and the challenge naming bmaksimov@quikstor.com with two excludeCredentials entries; the database then showed the invited account still at zero credentials with its invite unused, and the owner's account up from 2 to 3 credentials. Adding the target line to the harness and clearing cookies produced the correct run: challenge named invite-test@quikstor.com, empty excludeCredentials, session_issued:true, account flipped invited -> active, invite consumed, audit row {\"invite\": true}. Trap 2: the same test attempted in Chrome incognito offered only 'security key or other device' and threw NotAllowedError on sign-in; all three credentials involved were device_bound=false, i.e. synced in Proton Pass, and the extension was unavailable in incognito.

## Related

- [[Phase 2 Progress]]
- [[Gotchas]]
