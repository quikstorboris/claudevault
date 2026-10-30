---
date: 2026-10-29
description: "Hub for the unitprep-ui performance workstream: phased plan (Phase 0 measure, 1 load waterfall, 2 TanStack Query, 3 navigation, 4 heavy screens, 5 guardrails), working agreement and live progress."
tags: [work-note, unitprep, frontend, performance, plan]
status: active
quarter: Q4-2026
project: unitprep
---

# Frontend Performance Plan

Boris's call (2026-10-29): after the backend latency and Neon-compute work, the frontend "has been neglected for a while", so review it and speed it up, **not only in how it talks to the DB**. Code review first, then a phased plan, Boris reviews, then work.

- Findings: [[Frontend Code Review 2026-10-29]]
- Why this plan and what was rejected: [[Frontend Performance - Decisions and Discussion]]
- Backend context: [[Latency Investigation 2026-10-20 - Round Trips vs Neon]], [[Efficiency Refactor - Master Plan and Progress]], [[Session 2026-10-20 to 21 — OO Review Attempt, Latency and Neon Compute Audit, Release 1.9.134]]

## Status (as of 2026-10-29)

**Phase 0 in progress.** Nothing in `unitprep-ui` has been changed yet; the checkout was clean on `main` (`cf3fa86`, v1.6.106) when the review ran. The plan was approved in outline; Boris's only open choice (cache approach) is settled, see decisions.

## Working agreement

- **One phase at a time**, and within a phase **manageable chunks**. At the end of each response the assistant names the next chunk (e.g. "0.1 and 0.2") and sizes it.
- Success is measured the "desert way": fewer authenticated calls per navigation and faster perceived loads against the Phase 0 baseline, not micro-benchmarks.
- Out of scope, decided: micro-optimising Rust handlers, making ClickUp/Process Street feel local, more observability, deploy/Docker-prod work, keep-warm of Neon, a "bootstrap everything" API. See [[Frontend Performance - Decisions and Discussion]].
- Standing rules still apply: check file size and concern-mixing at the end of each task (`unitprep-ui/CLAUDE.md`), update [[UnitPrep Tech Stack]] the same session any dependency is added (TanStack Query, in Phase 2).

## Phases

### Phase 0: Measure first (no behaviour change)
- **0.1** Per-page request waterfall for six screens: clients list, client info, facility page, dedup results, Onboarding Work tab, admin users. Needs Brave via the Claude in Chrome extension, signed in as Boris (auth is passkey/TOTP and cannot be scripted).
- **0.2** Production `next build` plus per-route first-load JS and Sentry's share of the client bundle. Built in a **temporary hard-linked copy** (`~/tmp-ui-build` in WSL) so Boris's checkout and `.next` are never touched.
- **0.3** Profile the largest dedup and scan results with real fixtures (render time, long tasks).
- Exit: a short baseline table so every later phase has a before and after.

### Phase 1: Kill the load waterfall (expected biggest felt win)
- 1.1 Render the shell skeleton immediately; keep the `whoami` security gates (signed out, TOTP onboarding, step-up) intact. **Read the 2026-08-03 loading-guard gotcha first**: `checked && !user` guards exist because a real bug trapped users.
- 1.2 Stop `ClientLayout` waiting on the full company list just to show one client's name; take the name from company detail and fetch in parallel.
- 1.3 Start company-detail and facility reads at the same time.
- Exit: client page goes from a 4-step chain (whoami, full list, company detail, facility reads) to 2 parallel steps.
- Before starting: read the Efficiency Refactor frontend findings ([[Efficiency Refactor - Findings Reference]], [[Efficiency Refactor - Decisions and Investigations]], [[Efficiency Refactor - Code Review Brief]]) so nothing already tried or rejected is redone.

### Phase 2: TanStack Query for the shared reads
- Thin setup: `QueryClient`, a small query-keys module, `useQuery` on the hot reads only (`whoami`, client(id), company detail, facility and policies, filter options, directory), boring `staleTime` (tens of seconds to a couple of minutes), explicit invalidation after each write.
- Skip persistence, optimistic updates and infinite queries until something hurts. Leave the tool-session hooks (`useSessionAction`, `useFileUploadAction`, `useSessionPost`) alone: they are workflows, not cached reads.
- Retire the duplicate company list (`useClients` full list vs `useClientsDirectory`).
- Bonus: `useQuery` removes the `queueMicrotask` workaround that the `react-hooks/set-state-in-effect` lint rule forces on every fetch-on-mount hook.
- Add TanStack Query to [[UnitPrep Tech Stack]] the same session.

### Phase 3: Navigation and perceived speed
- 3.1 Cards and rows become real `<Link>`s (prefetch, open in new tab); today the clients grid uses `router.push` in an `onClick`.
- 3.2 `loading.tsx` and error boundaries per route group.
- 3.3 Pause the ClickUp copy-jobs poll in a hidden tab.

### Phase 4: Heavy-screen performance (scoped by Phase 0; drop if profiling shows no problem)
- 4.1 Virtualize or paginate large scan and dedup lists.
- 4.2 Move big file parsing and xlsx sniffing off the main thread if long tasks show up.
- 4.3 Lazy-load non-critical client code (Sentry extras) and trim any outsized first-load route.

### Phase 5: Guardrails
- 5.1 First-load JS budget check in `preflight.sh`.
- 5.2 Vitest tests for the query layer (invalidation, abort, stale data) plus one E2E for the client-page load.
- 5.3 Update this workstream's notes and the tech-stack note.

**Order:** 0, then 1, then 2, then 3. Phase 4 depends on Phase 0; Phase 5 runs alongside.

## Progress log

- **2026-10-29** Review done and plan agreed (see [[Frontend Code Review 2026-10-29]]). Phase 0 started: first attempt at the 0.2 build silently never ran (the process was launched in a way that died with its shell, and a watcher that grepped `pgrep -f "next build"` matched its own command line, so it would have waited forever). Restarted as a plain background command, which then failed too because the WSL login shell picked the Windows `npx`; restarted a third time with the Linux Node on `PATH`. Lessons in [[Frontend Performance - Decisions and Discussion]] and `brain/Gotchas.md`.
- **2026-10-29** `om` MCP re-registered for Windows-started sessions (`C:\Users\bmaksimov\.mcp.json` + `.om-project`); effective next session start.
- **2026-10-29 Phase 0.2 DONE: bundle baseline** (Next 16.4.3 Turbopack production build in the temp copy; sizes from `.next/diagnostics/route-bundle-stats.json`, gzip computed locally; Next 16 no longer prints sizes in the build log).
  - **Fixed baseline of about 625 KB raw / 194 KB gzipped JS on every route, including `/login`**, from 9 chunks shared by all 32 routes; the two biggest are 360 KB (contains React DOM/scheduler **and** Sentry) and 159 KB raw.
  - Heaviest routes only add 30-110 KB raw on top: facility page 734 KB raw / 227 KB gz, client info 733 / 225, unit-groups 705 / 219, dedup results 694 / 216. Typical admin pages 660-680 KB raw / 207-212 KB gz.
  - Reading: **the bundle is not the problem** (no outsized route, tab splitting already works); the shared floor is dominated by React plus Sentry. Splitting out Sentry's share would only trim part of the 194 KB floor. Phase 4.3 is therefore low priority unless 0.1/0.3 say otherwise. A build took about 7 s compile on this machine.
  - Not yet measured: Sentry's exact share (needs a source-map or `webpack-bundle-analyzer`-style breakdown; the 360 KB chunk was identified only by string match).
- **2026-10-29 Phase 0.1 (2 of 6 screens) DONE: request waterfalls**, measured in Brave with the in-page Resource Timing API (`performance.getEntriesByType('resource')`) on the **production build** served from the temp copy on `localhost:3000` (the API's default CORS allows only `localhost:3000`/`5173`; the Docker UI on `3001` would be blocked), against the local API on 8080 and the real Neon dev DB, already signed in. Warm, direct page loads, times in ms from navigation start. The temp server was stopped afterwards (it held port 3000).
  - **`/clients` (Clients list):** `whoami` 54-413, then **three in parallel from ~417**: `clickup/connection` (to 731), `filter-options` (to 963), `GET /clients` directory (to 696). Last response at about 963 ms. So the page's own data waits a full `whoami` round trip (about 360 ms) before it even starts: F1 confirmed.
  - **`/clients/<id>/info` (client page), two samples, same shape:**
    - sample 1: `whoami` 191-415, `GET /clients` (full list) 419-609 and `clickup/connection` 420-645 in parallel, **`GET /clients/<id>` company detail only starts at 613** (after the full list returns) and ends 1187, then `POST clickup/prefetch` 1193-1462.
    - sample 2: `whoami` 43-410, list 414-678, detail 681-918, prefetch 921-1158.
    - **Critical path is 4 serial hops: whoami, full company list, company detail, ClickUp prefetch (about 1.2-1.5 s to the last byte).** F1 and F2 confirmed with numbers: the company detail request is gated behind the **full company list**, which exists only to look up the client's name.
  - **Estimated Phase 1 gain on the client page (hypothesis):** company detail can start as soon as the route is known (even alongside `whoami`), and the ClickUp prefetch is a fire-and-forget POST off the render path. Taking the full list off the critical path alone removes about 190-260 ms; letting detail run beside `whoami` could cut the page from about 1.2-1.5 s to roughly whoami-or-detail (about 0.6-0.8 s).
  - **New findings:** (F10) the nav's `ClickUpStatusDot` fires `GET /integrations/clickup/connection` on every full page load (module-cached per page load, so not per navigation); (F11) the client page fires `POST /integrations/clickup/prefetch` on every view (`ClickUpCompanySection`, only when the user has ClickUp access), a ClickUp-backed warm-up call that is off the render path but is real API/ClickUp work on each visit. Neither is a big cost; note for Phase 1/3.
  - Per-request latencies here (190-570 ms, even for `whoami`) are higher than the 36 ms/statement estimate in [[Latency Investigation 2026-10-20 - Round Trips vs Neon]]; consistent with Neon connection/compute behaviour and the DEV API doing several statements per authenticated request (BEGIN, RLS setup, query). Not investigated here.
  - **Not yet measured:** client-side navigation (clicking from the list, which may skip `whoami`), the facility page, dedup results, Onboarding Work, admin users. Single warm sample each; no repeat variance beyond the two client-page samples.
- **2026-10-29 Follow-ups to 0.1 (Boris asked)**
  - **ClickUp prefetch POST was a real waste; fixed in `unitprep-ui` (uncommitted, tests/tsc/eslint green).** `ClickUpCompanySection` fired `POST /integrations/clickup/prefetch` on **every** view of a company page for any ClickUp-permitted user, even when the Link ClickUp dialog is never opened. Server side that is `require_permission` + `load_user_token` + `onboarding_space_name` (3 DB statements, logged 228-258 ms) plus, when the 5-minute hierarchy cache is stale, ClickUp reads against the shared in-process rate limiter. Now it warms up **once per mount, on pointer-enter or focus of the Link ClickUp button**; not on load. Two new tests in `components/clickup/ClickUpSections.test.tsx` (no prefetch on load; exactly one on repeated hover). Trade-off: a very fast click gets the dialog's own loading state instead of a pre-warmed list.
  - **ClickUp connection call is correct by design, left alone.** `GET /integrations/clickup/connection` is a single-row DB read of the stored status (no ClickUp call), gated on the `integrations.clickup` permission, shared module-level per page load (not per navigation), so the nav dot never refetches on client-side navigation. It costs about 220-310 ms server time off the render path. Candidate for Phase 1/2: fold into `whoami` or serve from the query cache.
  - **The "surprise" (whoami 190-400 ms) is explained, not a regression: it is statement count times Neon RTT.** Server-side `request completed` latencies match the browser's numbers (whoami 217-555 ms), so the time is in the API, not the frontend. `whoami` runs **6 sequential statements**: `auth.resolve_session` (in `AuthenticatedUser`), BEGIN, `set_config` RLS (`begin_owner_rls_transaction`), `totp_credentials` query, `auth.users` name query, COMMIT. That is roughly 36-57 ms each, consistent with the ~36 ms/statement figure in [[Latency Investigation 2026-10-20 - Round Trips vs Neon]]. Four of the six are fixed per-request overhead (resolve, BEGIN, set_config, COMMIT), paid by every authenticated route.
  - **Candidate backend task, on the critical path of every page load: slim `whoami`.** The frontend gates the whole shell on it (F1). Returning `first_name`, `last_name` and `totp_enrolled` from `auth.resolve_session` (or one SECURITY DEFINER read) would take `whoami` from 6 statements to about 1-2, roughly 200-300 ms to 50-100 ms on every full page load. Needs a migration plus `resolve_session` change (high-sensitivity function, see [[Efficiency Refactor - Decisions and Investigations]] Decision 1 for the surrounding rules); **not started, needs Boris's go-ahead.** This is the evidenced exception to "hold the line on API densification".
  - **CORS and port 3001:** the API's default allowed origins are only `http://localhost:3000` and `:5173`; the Docker `ui-dev` container publishes on host `3001`, so it cannot call the API unless `CORS_ALLOWED_ORIGINS` is set (it is not set in `.env.local`/`.env`). Recommendation: do not change the code default; set `CORS_ALLOWED_ORIGINS` in `.env.local` only if the 3001 container is actually used.
- **2026-10-29 whoami fix BUILT, verified on dev (not committed, not on prod).** Boris paused Phase 0 to fix this first, with security preserved.
  - **Design chosen:** new additive migration `20261029160000_add_session_profile` adds `auth.session_profile(p_token_hash, p_idle_minutes)` returning first name, last name and confirmed-TOTP boolean. `whoami` now = extractor's `resolve_session` plus this one call = **2 statements instead of 6**.
  - **Security shape (all pinned by 4 real-DB tests in `src/api/session_profile_db_tests.rs`):** keyed by the session token with **no user-id parameter** (can only describe the owner of a live session the caller holds); validity is **delegated to `resolve_session`**, not re-implemented, so revoked, expired, idle and deactivated sessions return nothing (whoami then 401s); names plus a boolean only (no email, no secret); `SECURITY DEFINER` with pinned `search_path`; `EXECUTE` revoked from `PUBLIC`, granted to `app_service` only. Documented in `THREAT_MODEL.md` (new row), `AUTHENTICATION.md` and `CHANGELOG.md` (Unreleased). `SCHEMA.sql` regenerated. clippy `-D warnings`, rustfmt and the full workspace test suite green.
  - **Trade-off, recorded:** `whoami`'s read no longer runs under RLS; it relies on the token scoping above (same trust model as `resolve_session` and `check_session_expired`).
  - **Alternatives rejected:** (a) adding names/TOTP to `resolve_session` itself, which would put PII and an extra table lookup on **every** authenticated request and alter the most sensitive function; (b) a `user_id`-keyed definer function, which would bypass RLS for arbitrary ids; (c) one CTE statement with `set_config` plus RLS reads, which depends on planner evaluation order for a security GUC (fails closed but subtle).
  - **Applied to** the local test-db and the **Neon dev** branch (only that migration was pending; additive). **Prod not touched** (Boris runs the prod scripts by hand; deploy order is safe either way because the migration is additive). The dev API in the `api-dev` container was restarted on the new code (detached `cargo run`, log at `/tmp/api-run.log` in the container); Boris's old foreground `cargo run` terminal exited.
  - **Result (server-side `latency_ms` from the API log, dev API to Neon dev):** before 217-555 ms (eight samples, median about 331); after 225 ms for the first call after restart (cold pool), then **116, 114, 116, 81, 81, 74, 74, 74 ms**; browser-side in-page fetches 78-122 ms. Roughly 2-4x faster per `whoami`. Client page load to last response: about 1.16-1.46 s before, about 1.13-1.66 s in the two post-fix loads, but those still include the old prefetch call and a cold first request; the page chain itself (whoami, full list, company detail) is unchanged and remains the Phase 1 target.
  - **UI prefetch fix verified in a real browser** against a rebuilt production copy: no `POST /integrations/clickup/prefetch` on page load; exactly one after hovering the Link ClickUp button twice.
  - **Env:** `CORS_ALLOWED_ORIGINS` added to `unitprep-api/.env.local` (gitignored): `localhost` and `127.0.0.1` on ports 3000, 3001, 3100, 5173. Takes effect on API start (the restart above loaded it); so the Docker UI on 3001 and the E2E port can now call the API.
  - **Still to do on Boris's say:** commit and release both repos per their conventions (api needs a version bump and the CHANGELOG's Unreleased section moved; `unitprep-ui` change is two files), apply the migration to **prod** by hand before deploying the API code, and note the vault. The `whoami` response shape is unchanged, so no UI change is required for it.
- Results for the remaining 0.1 screens and 0.3 are appended here as each chunk finishes (Phase 0 still paused).

## Related

[[Production Readiness Checklist]], [[UnitPrep Tech Stack]]
