---
date: 2026-08-04
description: "When a backend route that used to be open gets a session/auth requirement added, every EXISTING frontend caller of that route needs a check too --…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-04T16:19:43.202Z"
scope: general
projects: []
confidence: verified
---

# Gating backend routes behind auth doesn't retrofit frontend callers that predate auth -- audit every existing fetch() call site, not just the new ones

When a backend route that used to be open gets a session/auth requirement added, every EXISTING frontend caller of that route needs a check too -- not just newly-written code. A `fetch()` to a different-origin API (different port counts) silently omits cookies unless `credentials: "include"` is set explicitly, regardless of browser default behavior; the request doesn't error at the fetch layer, it just looks anonymous to the server. If the server now requires a session, that reads as "signed out" no matter how recently the user actually signed in -- and it looks identical to a real sign-out bug, not a wiring gap, from the user's side.

This is easy to fully miss because gating work is naturally reasoned about from the backend outward ("add AuthenticatedUser to every route"), and grep for "every route that needs updating" finds backend handlers, not frontend call sites that already existed before auth was a concept in the codebase at all. A thorough sweep needs a second, explicit pass: grep the frontend for every direct `fetch()` (not just ones going through a shared, already-audited helper/hook) and check each one for `credentials: "include"`.

**A sign this gap is coming**: if a codebase has some fetch call sites written with `credentials: "include"` *and a comment explaining it's for auth that doesn't exist yet* ("inert today... but the seam needs to exist now so wiring auth in later doesn't mean grep-and-patch every call site"), that comment is telling you exactly what still needs to happen elsewhere in the same codebase -- other call sites that predate that seam almost certainly don't have it, and the sweep the comment anticipated may never have actually been done.

**How to verify the fix, not just apply it**: don't just add the header and assume it's right -- reproduce the exact failure and its resolution against the real running server. The clearest proof is the *contrast*: fire the identical request with and without `credentials: "include"` and confirm the with-credentials version gets past the auth gate (a different, later error, or success) while the without-credentials version reproduces the original symptom exactly (down to the same error message the user reported). A component-level unit test with a mocked fetch will not catch this class of bug at all, since the mock has no concept of cross-origin cookie policy -- only a real network round trip does.

##### How this is known

Hit directly on unitprep-ui 2026-08-04. A user reported dedup refusing to run with "Sign in required" immediately after a successful, confirmed passkey login. Investigation found four fetch() call sites (a file-upload page, a discovery-flow hook with two calls, a group-file-upload component, and a fire-and-forget session-cancel helper) missing credentials: "include", all predating the backend's auth requirement -- while two other call sites in the same codebase (useSessionPost, useSessionAction) already had it, with a comment explicitly anticipating this exact gap ("wiring auth in later doesn't mean grep-and-patch every fetch call site in the app"). Confirmed via the browser's own JS context against the real dev server: the identical multipart request returned 401 {"error":"unauthorized","message":"Sign in required"} without credentials: "include" and a real downstream validation error (proving it passed the auth gate) with it.

## How this is known

Reproduced the exact user-reported symptom and its fix via a real network round trip from the browser's own JS context against the live dev server -- same request, only credentials差 differed, producing 401 Sign in required in one case and a real validation response in the other.
