---
date: 2026-10-23
description: "Next.js flagged 16.4.0 as critical in the browser; upgraded to 16.4.3 with the vite/vitest dev advisories, which also retired the unpatched braces allowance. ui 1.6.104."
tags: [work-note, unitprep, security, dependencies]
status: completed
quarter: Q4-2026
project: unitprep
---

# Next.js 16.4.3 security upgrade (ui 1.6.104, 2026-10-23)

## Trigger

The browser's Next.js dev overlay showed "Security Insight: Next.js 16.4.0 is affected by a known security vulnerability" (suggested: `next upgrade --agent=security`). Boris asked whether it was the unpatched advisory we track with a monthly check. **It was not**: that one is `braces` (GHSA-vfj7-8cjw-p6xm), a dev-only lint-chain DoS with no patch, allowed in `unitprep-ui/scripts/preflight.sh` with a review date of 2026-11-06. The Next.js one is a different, patched, critical set.

## The Next.js advisories (range 16.0.0 - 16.4.0, fixed in 16.4.x)

- GHSA-2464-fhr4-w9xw: unauthenticated RCE in the Image Optimization API when SVG files are used.
- GHSA-673q-mjm6-r5xr: unauthenticated RCE in `use cache` functions returning typed arrays.
- GHSA-p3m5-59mp-jv5r: denial of service in the App Router using Server Actions.
This app does not use `use cache` or Server Actions (it is a client UI in front of a separate Rust API), so real exposure was low, but the fix is a patch release.

## What was done

- Worktree off `origin/main` (other work was in flight), `npm ci`, `npm audit fix`: `next` 16.4.0 -> **16.4.3** (current `latest`), `vite` 8.1.x -> 8.3.5 (high: custom-middleware cross-origin script execution, `server.fs.allow` bypass, `launch-editor` command injection chain).
- `npm audit fix` alone left the vitest moderate (GHSA-qxg6-89mg-rqv8, GHSA-xp26-3454-mjgp, `@vitest/mocker` 5.0.0-beta.1 - 5.0.2), so `vitest` and `@vitest/coverage-v8` were bumped to `^5.0.5` explicitly; `eslint-config-next` 16.2.9 -> 16.4.3 to match Next. `npm audit`: **0 vulnerabilities**.
- The newer eslint config warns on `window.location.assign("/clients")` in `app/login/page.tsx`; that hard navigation is deliberate (stale Turbopack HMR after a long idle tab), so it got an `eslint-disable-next-line` with the reason.
- **The braces allowance was deleted**: after the upgrade `npm audit` no longer reports GHSA-vfj7-8cjw-p6xm (patched chain pulled in). The preflight block's own instructions said to delete it when it stopped being reported; step 4 is a plain `npm audit` again. The scheduled task `braces-advisory-monthly-check` was **paused** (safe to delete).
- Verification: tsc, eslint, vitest 1,067 passed, all 14 Playwright specs passed, full preflight green (including the ts-rs drift check). Shipped `v1.6.104` (`cbda58f`).

## Notes

- The dev overlay's "Security Insight" is a real signal; `npm audit` on the UI was already failing locally, but only a preflight run would have shown it. The daily anomaly check does not cover dependency advisories; the monthly CI review task (`unitprep-ci-tier2-review`) is the nearest routine. Consider a weekly `npm audit` + `cargo audit` look (the zip exception in the api has a review date of 2026-11-16).
- Install scripts: npm now blocks `unrs-resolver` postinstall unless approved (`npm install-scripts approve`); nothing broke, the package works without it.

## Related

[[Efficiency Refactor - Second Pass Execution Record]], [[Gotchas]]
