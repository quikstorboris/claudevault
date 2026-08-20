---
date: 2026-07-28
description: "When a Playwright test intercepts a fetch route via page.route() for an endpoint the app calls with a JSON body across origins (e.g."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-28T17:26:43.380Z"
scope: general
projects: []
confidence: verified
---

# Mocking a cross-origin JSON POST route in Playwright must also answer the CORS preflight OPTIONS request

When a Playwright test intercepts a fetch route via page.route() for an endpoint the app calls with a JSON body across origins (e.g. app on port 3100, API on port 8080 — different ports count as different origins), the browser sends a CORS preflight OPTIONS request first (any POST with Content-Type: application/json is a "non-simple" request per the CORS spec, so it always preflights). An OPTIONS request has no body, so calling request.postDataJSON() unconditionally inside the route handler throws for that request. An uncaught exception in a page.route() handler means route.fulfill() is never called, which leaves that request — and so the entire fetch, preflight included — hanging until the test's default timeout, indistinguishable from a genuinely stuck loading state in the app under test.

Fix: branch on request.method() inside the handler. For OPTIONS, immediately fulfill with a 204/200 and the CORS headers the browser needs (Access-Control-Allow-Origin matching the app's own origin, Access-Control-Allow-Credentials if the app sends credentials, Access-Control-Allow-Methods, Access-Control-Allow-Headers) — only then parse the body for the real POST/GET request.

Why this generalizes: any Playwright suite mocking a cross-origin JSON API (a separate backend dev server, a different port, a different subdomain) hits this the first time the mocked endpoint is actually exercised — same-origin mocks never trigger it, which is why it can go unnoticed until a repo's frontend and backend are proxied through genuinely different origins in tests.

## How this is known

Reproduced directly: a Playwright E2E test against unitprep-ui hung on "Loading…" with no error until the route handler was split on request.method(), after which the same test passed twice in a row.
