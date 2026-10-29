---
date: 2026-10-29
description: "Full discussion trail behind the frontend performance workstream: the Grok POC proposal and pushback, Boris's scope decisions, request-count vs Neon-compute nuance, TanStack Query vs in-house cache (and the reversal), and process lessons."
tags: [work-note, unitprep, frontend, performance, decisions]
status: active
quarter: Q4-2026
project: unitprep
---

# Frontend Performance: Decisions and Discussion

Companion to [[Frontend Performance Plan]] and [[Frontend Code Review 2026-10-29]]. Records what was proposed, what was rejected and why, so it is not re-litigated.

## 1. Grok's "desert rule" POC (first proposal)

**Proposal (pasted by Boris from Grok):** prove the "desert rule" on one more API path the way `GET /clients/filter-options` was done (three sequential SELECTs merged into one statement). Steps: pick a target (`GET /clients` first), inventory every DB round trip, merge only independent reads that always ship together, keep the same JSON and RLS model, measure 5-10 warm samples before and after on a release build, then decide (clear win: repeat once; already dense: stop).

**Assistant's read:** methodology sound, the step-2 gate ("if N is already 1-2, stop") is the valuable part, but:
- The gain is small: a statement costs about 36 ms against Neon ([[Latency Investigation 2026-10-20 - Round Trips vs Neon]]), so 4 trips to 2 saves roughly 70 ms, barely perceptible on a list page.
- Hard to measure: local latency is 5-12 ms and Neon round-trip jitter is bigger than the effect.
- Result may not transfer: with "no cloud move", the Neon round trip is what is measured; if the API ever sits next to Neon the per-trip cost shrinks.
- Generic: it ignores fixed per-request overhead (`begin_for`: BEGIN, RLS `set_config`, COMMIT), which would be paid on every route and is a better lever than per-route merges (unverified; code not read).
- Recommended: inventory only, no merge unless there is a clear fixed cost or an obvious mergeable pair.

## 2. Boris's scope decisions (2026-10-29)

- **No warming of anything** ("this is production time talk"). Current speeds are reasonable and expected to transfer to production.
- **Integration latency is acceptable:** time spent talking to ClickUp or Process Street when working locally is fine. Services and DB being the bottleneck is accepted.
- **Conserve Neon compute**, but be ready for possible future deployment and "opening the faucet a little more"; improve anything that clearly can be improved.
- **Drop micro-improvements and opportunistic ideas.** Focus on real wins. Rust is not on the critical path.
- **Review the frontend**, which "we've been neglecting for a while", for speed in general, not only DB interaction.

## 3. Grok's second opinion (frontend chattiness) and the nuance added

Grok: backend is good enough; the main remaining lever is how chatty the UI is: duplicate fetches (Strict Mode, remounts), waterfalls on facility pages, eager tab loads, stale-while-revalidate, polling in background tabs.

**Assistant agreed with the conclusion, with two caveats:**
- **Request count is not the same as Neon compute.** Neon bills compute time while the endpoint is awake, so what matters most is whether anything keeps it awake or wakes it; ten small queries in one burst cost very little more than three. The big compute levers were already pulled (background timers, idle pings, cold starts). So frontend chattiness is mainly a **latency and "feels busy" lever**, a weaker compute lever than implied.
- Parts of Grok's claims were assumptions (e.g. "six to ten parallel GETs", "`whoami` per mount"); the code review found the real shape instead. `useClickUpAccess` was suspected and turned out not to fetch.

## 4. Cache approach for Phase 2: TanStack Query (decided)

**Assistant's first answer (in-house):** ~100-150 lines on the existing `ApiResult` / hooks pattern, no new dependency, easier to reason about, reversible.

**Grok's counter (TanStack Query):** the diagnosed failure mode (serial chain plus no shared cache) is exactly what a query cache solves: in-flight dedupe, shared cache by key, stale-while-revalidate, cancellation, invalidation after writes. In-house usually fails on the hard parts: Strict Mode double-mount, navigation races, who invalidates what after a mutation, the next endpoint that joins the chain. Keep the setup thin (a few keys, boring stale times). It does **not** fix serial awaits by itself: Phase 1 must still break those by hand.

**Reversal and verdict: TanStack Query.** Boris asked "what's better?"; the assistant first recommended in-house, then after Grok's counter conceded and switched:
- "~100-150 lines" only covered the happy path; dedupe, Strict Mode safety, cancellation and invalidation are where it grows into a half-built React Query.
- The reads in play are not a small set (whoami, client(id), company detail, facility, policies, filter options, a directory keyed by search and filters).
- "In-house is reversible" was weak: an in-house cache is also hard to back out of once every hook uses it.
- Bonus missed at first: `useQuery` removes the `queueMicrotask` workaround forced by `react-hooks/set-state-in-effect`.
- **Guardrails kept:** thin setup, hot shared reads only, leave workflow hooks (`useSessionAction`, `useFileUploadAction`, `useSessionPost`) alone, no persistence/optimistic/infinite queries yet, it is one more package for `npm audit` and the preflight, so add it to [[UnitPrep Tech Stack]] when adopted.
- When in-house would have been right: only if Phase 2 were 2-3 read-mostly keys with no cross-page reuse and a hard no-new-dependency rule. That does not match the app.

## 5. Process lessons from the first session

- **`om` MCP missing in a Windows-started session.** The vault's `om` MCP server is wired through each repo's `.mcp.json`; the UI repo's points at the WSL path `/mnt/c/Users/bmaksimov/my-vault/...`, which works only in sessions started inside WSL. The home folder `C:\Users\bmaksimov` had no `.mcp.json` (despite an older memory note saying it was wired). Fixed 2026-10-29 by adding `C:\Users\bmaksimov\.mcp.json` (Windows path to `om-mcp.mjs`) and a `.om-project` file (`windows-home`) so memories scope to that name rather than the folder name. Takes effect next session start. The vault is plain files, so it stayed readable throughout via Read/Grep.
- **Background build wasted a cycle.** A `nohup ... &` inside `wsl.exe -- bash -lc '(...)'` died with its shell, leaving an empty log; a wait-loop using `pgrep -f "next build"` matched its own command line and would never finish. Run long WSL jobs as a plain foreground command of a background task, and never `pgrep -f` for a string that appears in your own command.
- **Unquoted `$VAR`/`$HOME` inside `wsl.exe -- bash -lc '...'` from Git Bash came through empty**; use absolute paths.
- **Build in a copy.** The real checkout's `.next` is Boris's dev server's; a dev container (`/app`) serves it. Production builds for measurement go in a hard-linked copy (`rsync` excluding `node_modules`/`.next`, `cp -al node_modules`).

## Related

[[Frontend Performance Plan]], [[Frontend Code Review 2026-10-29]], [[Latency Investigation 2026-10-20 - Round Trips vs Neon]], [[Efficiency Refactor - Decisions and Investigations]]
