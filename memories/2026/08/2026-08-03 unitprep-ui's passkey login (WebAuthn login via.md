---
date: 2026-08-03
description: "The frontend login page (app/login/page.tsx) built on the native PublicKeyCredential.parseRequestOptionsFromJSON/credential.toJSON() approach (rather…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-03T21:08:46.004Z"
scope: project
projects: ["unitprep-ui"]
confidence: verified
---

# unitprep-ui's passkey login (WebAuthn login via navigator.credentials.get()) verified working end-to-end against a real Windows Hello authenticator

The frontend login page (app/login/page.tsx) built on the native PublicKeyCredential.parseRequestOptionsFromJSON/credential.toJSON() approach (rather than hand-rolled base64url<->ArrayBuffer conversion) has now been confirmed working by an actual human completing a real passkey ceremony through it - not just unit/lint/type checks, and not just a curl-level check of the backend's own JSON shape. Boris signed in from /login using a real passkey and it worked.

This closes the "honest gap" flagged when the login page was first built: at that point only the page's rendering, redirect-when-already-signed-in logic, and the absence of console errors had been verified - completing an actual WebAuthn ceremony through the browser's native credential UI had not.

Practical implication for the rest of the auth frontend build (invite redemption reuses the exact same ceremony shape via navigator.credentials.create() instead of .get()): the browser-native parse/toJSON approach is validated as correct against this project's real webauthn-rs backend, not just theoretically compatible per the WebAuthn Level 3 spec. No further wire-format verification should be needed for the registration ceremony specifically because of this - the same conversion functions are used for both.

## How this is known

Boris directly reported "signed in from /login successfully using passkey" after testing the running dev server himself.
