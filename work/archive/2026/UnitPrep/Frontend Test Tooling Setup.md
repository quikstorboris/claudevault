---
date: 2026-07-28
description: "Set up Vitest + RTL + Playwright + coverage tooling for unitprep-ui, which had zero automated tests before this; all confirmed passing"
tags:
  - work-note
  - unitprep
status: completed
quarter: Q3-2026
project: unitprep
---

# Set up frontend test tooling (Vitest + Playwright) for unitprep-ui

unitprep-ui had zero automated tests before this. Added Vitest + React Testing Library for unit/component/hook tests (18 tests passing), `@vitest/coverage-v8` (baseline ~9%, honest starting point not a completed effort), and Playwright for E2E, including a regression test for the key={sessionId} state-scoping bug class that's been fixed four separate times across different routes. Boris installed the missing OS libraries (`libnspr4`, `libnss3`, `libasound2` -- note the plain name, not `libasound2t64`, since this image is Ubuntu 22.04 not 24.04) via `sudo apt-get install`, and the E2E test **passed twice in a row** once three further real bugs were found and fixed getting it to actually run (not just type-check):

1. The mocked `/validate` route only answered the POST, not the CORS preflight OPTIONS request a cross-origin `application/json` POST requires — an uncaught exception on the body-less preflight left the whole fetch hanging forever.
2. Next.js 16's dev server blocks cross-origin dev-resource requests by default; the E2E suite runs on `127.0.0.1:3100`, not `localhost:3000`. Fixed via `allowedDevOrigins: ["127.0.0.1"]` in `next.config.ts` (dev-only, no production effect).
3. Clients are frontend-only state in `sessionStorage` (see `lib/clients.tsx`) — the test now seeds one via `page.addInitScript()` before navigating, rather than hitting the app's own "this client isn't in the current browser session" guard.

## What changed

- vitest.config.ts, vitest.setup.ts: jsdom environment, @vitejs/plugin-react, @/* alias matching tsconfig, excludes e2e/.
- lib/useSessionPost.test.ts, lib/useSessionAction.test.ts: cover credentials: "include" (previously untested), 404/401-as-sessionExpired, real error surfacing, and downloadBlob's filename extraction.
- components/scan-results/ScanResultsStatTiles.test.tsx: the 5-tile stat grid's counts and Export Status text/color states.
- playwright.config.ts + e2e/session-remount.spec.ts: mocks /validate per session_id, uses browser back/forward (a genuine Next.js client-side transition) between two sessions' results pages, asserting neither session's data leaks into the other.


## Decisions

- Vitest over Jest: faster, native ESM support that plays better with Next.js's own setup with less config.
- E2E test mocks the backend via page.route() rather than running a real unitprep-api server -- this suite verifies frontend remount/state-scoping behavior specifically, which is a different concern from backend correctness (already covered by the Rust test suite).
- Used browser back/forward (page.goBack()/goForward()) rather than page.goto() between the two sessions -- goto() is always a hard navigation in Playwright/Chrome, which would mask the exact bug (state surviving a client-side/soft transition) this test exists to catch.


## Learned

- npm install failing with EISDIR/EPERM on node_modules/.bin symlinks inside WSL means npm resolved to the Windows-side binary (/mnt/c/Program Files/nodejs/npm) rather than a WSL-native one -- check `which npm`/`file $(which node)`; fix by prepending an existing native install (often already present under ~/.nvm/versions/node/<version>/bin even if not sourced in non-interactive shells) to PATH. Full lesson recorded separately as its own memory (scope: platform).
- Playwright's browser binary itself downloads fine without sudo (npx playwright install chromium), but chrome-headless-shell needs OS shared libraries (libnspr4, libnss3, libnssutil3, libasound2 on this Ubuntu image) that only `--with-deps`/`install-deps` (apt-get, needs sudo) can provide -- `ldd <binary> | grep 'not found'` shows exactly which ones before assuming a fix is needed.



## Open

- Only one E2E test exists (the key={sessionId} regression), now confirmed passing. A full golden-path test (real upload -> discover -> validate -> export against a live backend) was scoped out this session given time -- worth adding as the next E2E addition, now that the harness itself is proven working end to end.
- FE coverage baseline is low (~9%) since only 3 files have tests. Backend coverage tooling (cargo-llvm-cov as primary, cargo-tarpaulin as an occasional cross-check) is set up too, baseline ~81-84%.


## Related

- [[Post-Refactor Audit]]
- [[Full Review & 9-Milestone Refactor]]


_Recorded 2026-07-28T16:49:02.436Z from `bmaksimov` via the om MCP server (routing: fallback)._
