---
date: 2026-08-14
description: "M4 of the fix plan closed in one pass: npm audit fix resolved all 6 High-severity advisories (next itself resolved to a genuinely new 16.3.1 patch rel"
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 4 done — npm audit fix closed all 6 advisories, Next.js reachability reassessment moot

M4 of the fix plan closed in one pass: npm audit fix resolved all 6 High-severity advisories (next itself resolved to a genuinely new 16.3.1 patch release, past the previously-stuck vulnerable range, taking postcss/sharp with it). Backend needed nothing -- already clean. Shipped as unitprep-ui v1.5.3. Also pushed an unpushed local commit from Boris (Template Tagger UI tests, v1.5.2) that surfaced during a cross-review with Grok.

## What changed

- unitprep-ui: v1.5.2 -- pushed Boris's own already-committed-but-unpushed Template Tagger UI test coverage commit (TagPicker/useTaggerReport/useTaggerApply), found while cross-checking Grok's second-opinion review against the actual repo state
- unitprep-ui: v1.5.3 -- npm audit fix, 0 vulnerabilities remaining (was 6 High); real dev-server smoke check confirmed Next.js 16.3.1 boots cleanly and proxy.ts executes correctly on a live request
- Plan file (C:\Users\bmaksimov\.claude\plans\polished-crunching-hopcroft.md) updated: M5's assign_tiers entry strengthened per Grok's cross-review (hard cap, not just a warn threshold, plus a tagger-specific upload size cap -- confirmed via grep that only the generic 100MB router-wide DefaultBodyLimit currently applies); M7's tagger-test entry marked done


## Decisions

- Did not attempt a deeper Next.js CVE reachability re-analysis beyond confirming 0 current vulnerabilities -- the exercise this milestone item called for (re-checking proxy.ts/next/image as exposure factors) only matters against a live advisory, and upgrading next past the vulnerable range removed the live advisory outright. Documented the exposure-surface facts (proxy.ts exists, next/image used in 2 components) for whenever a future advisory does appear, rather than doing a full reachability writeup against nothing.
- Verified the Next.js version bump with a real dev-server boot + a live request through proxy.ts, not just the test suite -- a minor Next.js version bump is exactly the kind of dependency change this project's own gotchas (proxy.ts export-name requirement, allowedDevOrigins) warn is worth checking empirically.


## Learned

- The Windows-hosted Browser pane genuinely cannot reach a WSL-hosted dev server's localhost:3000 in this environment (confirmed via curl exit code 7, connection refused, from the Windows side) -- a real cross-boundary networking limit, not a bug. Also: a background process started with `nohup ... &` inside one `wsl.exe -e bash -lc '...'` invocation does not reliably survive to be reachable from a SEPARATE later `wsl.exe -e bash -lc` invocation (confirmed: the exact same server that successfully served a request in its startup log became unreachable moments later from a fresh wsl.exe call). Practical implication: verify a WSL dev server's behavior from its own startup log within the SAME command that started it, not by navigating to it from the Windows-side browser tooling or a later separate WSL invocation.


## Verification

unitprep-ui: vitest run 330 passed (46 files); tsc --noEmit clean; eslint clean; npm audit 0 vulnerabilities (was 6 High). Real dev server (Next.js 16.3.1, Turbopack) started cleanly, GET /login returned 200 with proxy.ts executing in 6ms, confirmed via the server's own startup log. unitprep-api: cargo fmt --all -- --check 0 diffs, cargo audit clean -- no changes needed. Both commits pushed to origin/main.



## Related

- [[2026-08-13-third-audit-fix-plan-full-session-handoff-m1-m2-done-m3-in-p]]
- [[2026-08-14-milestone-3-fully-closed-admin-guard-concurrency-test-added]]


_Recorded 2026-08-14T16:14:31.035Z from `bmaksimov` via the om MCP server (routing: caller)._
