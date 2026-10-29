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
- Results for 0.1 and 0.3 are appended here as each chunk finishes.

## Related

[[Production Readiness Checklist]], [[UnitPrep Tech Stack]]
