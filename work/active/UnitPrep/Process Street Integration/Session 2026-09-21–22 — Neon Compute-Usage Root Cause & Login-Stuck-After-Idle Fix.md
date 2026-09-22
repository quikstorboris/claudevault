---
date: 2026-09-22
description: "Root-caused a Neon free-tier compute-usage alert to a 5-min backend poll colliding with the default suspend timeout (Process Street was not the cause); fixed, plus a separate unitprep-ui login-stuck-after-idle bug fixed with a hard navigation."
tags: [work-note, unitprep, process-street, infra]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-21–22 — Neon Compute-Usage Root Cause & Login-Stuck-After-Idle Fix

Two unrelated investigations in one sitting: a Neon free-tier compute-usage alert (Boris's own suspicion going in was [[Process Street Integration — Kickoff & Findings|the Process Street integration]]), and a separate `unitprep-ui` login bug reported mid-session. **Neither fix is committed/pushed as of this note** — both are verified locally (build/tests green) and waiting on Boris.

## Neon compute-usage investigation

### Trigger and tooling

Neon flagged 80% of the free-tier monthly compute allowance used (climbed to 91.4% during the investigation itself). Installed `neonctl` v5.0.0 in WSL via the native `nvm`-managed Node (Windows Node on PATH would have silently run the wrong toolchain, per [[Gotchas#WSL: `bash -lc` doesn't reliably source `nvm`, so `npx` silently runs the Windows toolchain instead|the existing WSL/nvm gotcha]]), authenticated against the `org-wild-sky-15500238` org, and pulled real usage data for project `hidden-fire-83981383` ("Onboarding Orchestrator").

### Process Street ruled out

The `production` branch/endpoint (`br-mute-dew-a6julq3j` / `ep-snowy-recipe-a67ufw7h`) has **zero** compute time for the entire period — nothing is deployed there, so it can't be the source. The person-index sync is wall-clock-scheduled (once daily), runs strictly sequentially, and is paced against PS's own ~2,500-req/hour API limit — not a query-volume problem. Boris's suspicion was reasonable to check but wasn't the cause.

### Wrong turn: misread `suspend_timeout_seconds`

Both endpoints showed `suspend_timeout_seconds: 0` via the API. Read that as "autosuspend disabled" (Neon's actual "never suspend" value) and spent real effort trying to PATCH it back to 300 — blocked by both the API (`ERROR: modifying the suspend interval is not permitted on this account`) and the Console UI (greyed out, "Upgrade your plan to configure this setting"). Drafted and posted a support request to Neon's Discord (Free plan has no ticket/email support tier, Discord is the actual channel) with the full evidence trail — project/endpoint/operation IDs, the before/after operations-log timeline, the exact API rejection.

**Neon staff (`daniel_h`) corrected this same day**: `0` means *"use the plan default"* (300s on Free), not "never suspend" — that's a separate value, `-1`. Free plan can't edit this field at all (by design, not a bug), and the account has never held a paid plan, so there was never a stuck/leftover paid-tier setting to begin with. See the new [[Gotchas#Neon_ `suspend_timeout_seconds: 0` means "use the plan default," not "never suspend" -- that's `-1`|Gotchas entry]] for the corrected semantics, captured so this mistake doesn't repeat.

### Real root cause: a background poll colliding with the default idle timeout

With the account-level theory dead, the original (correct) diagnosis from the first pass of this investigation stands: `unitprep-api`'s `client_ops::vendor_format::start_refresh_task` runs **two** background loops (Units, Tenants — [main.rs:222-237](\\wsl.localhost\Ubuntu\home\bmaksimov\Development\unitprep-api\src\main.rs)) that each query Postgres every **300 seconds, forever, for as long as the server process runs**. Neon's Free-plan default idle timeout is also 300s. Every tick landed close enough to the timeout boundary to reset it before it could fire — so any time the dev server was left running, the compute simply never got a real idle window to suspend in.

The Neon operations log (`GET /projects/{id}/operations`) confirms this pattern **predates** any config confusion: two earlier multi-day continuous-active stretches (2026-08-21→26, ~5 days; 2026-09-11→15, ~4 days) show up as long unbroken `active` windows in an account whose suspend behavior was always the untouchable Free-plan default the whole time. A currently-running `target/release/unitprep` process (started that morning) was independently confirmed live via `ps aux`, holding the compute active during the investigation itself.

### Fix shipped (not yet committed)

Bumped the refresh interval from 300s to **4 hours** in `client_ops::vendor_format::start_refresh_task` ([vendor_format.rs:82](\\wsl.localhost\Ubuntu\home\bmaksimov\Development\unitprep-api\src\client_ops\vendor_format.rs)), with the doc comment updated to explain why. `cargo build --release` clean, `cargo test vendor_format --release` passing. Boris's call on scope: keep the dev server running continuously going forward (RAM is no longer a constraint on `QSLP14`, superseding the older memory-driven "don't leave it running" guidance — see [[Gotchas#This laptop has ~2GB of RAM headroom -- local model inference and the vault's own test suite will freeze it|the QSLP15 RAM gotcha]], now explicitly not applicable here for this reason), so the interval fix — not a "stop leaving it running" behavior change — is what actually closes the loop. The running process still needs a restart to load the new binary.

### Read replicas: considered and correctly rejected

Boris asked whether Neon's read-replica feature was worth exploring as part of the same cost investigation. It isn't, for this workload: a replica is a **separate, independently-billed compute** that would inherit the same "polling collision" exposure (doubling the burn, not fixing it), and nothing about this app's real query volume (single-operator internal tool, ~40-90ms per-query latency observed) needs read-scaling in the first place.

## `unitprep-ui`: login stuck after a long idle period

### Symptom

After leaving a tab idle a long time, signing back in via passkey looks like it works (prompted, submitted, no errors) but the UI stays on `/login`. `Ctrl+Shift+R` fixes it. No server-side errors — backend logs show both `/auth/login/begin` and `/auth/login/finish` succeeding, plus a `200` from `/health/whoami` carrying a real, authenticated user, immediately followed (a few seconds later) by a second full login cycle, presumably Boris retrying by hand after nothing appeared to happen.

### What was ruled out

Read through the actual auth flow: [app/login/page.tsx](\\wsl.localhost\Ubuntu\home\bmaksimov\Development\unitprep-ui\app\login\page.tsx), the `useCurrentUser` module-level store ([lib/currentUser.tsx](\\wsl.localhost\Ubuntu\home\bmaksimov\Development\unitprep-ui\lib\currentUser.tsx), a `useSyncExternalStore`-based singleton), and the protected-shell guard in `app/(app)/layout.tsx`. All correct — the server log confirms `whoAmI()` really did come back with a genuine authenticated user (not the "nobody's signed in" `200` this endpoint also returns) *before* the app attempted to navigate. This is not a session/auth-state bug.

### Assessed root cause (not confirmed via live repro)

`unitprep-ui` runs Next.js 16 with Turbopack (the current default dev bundler, confirmed via the running process list). The login page navigates on success with a client-side soft navigation (`router.replace("/clients")`), which depends on Turbopack's dev-mode HMR/router connection. After a tab sits idle long enough, that connection can go stale, and the next soft navigation can silently fail to complete — no thrown error, URL/content just don't update. A hard reload always recovers because it bypasses the stale in-memory router state entirely, which matches the observed symptom exactly. This is a **dev-mode-only** class of issue (a `next build && next start` production run has no Turbopack HMR machinery to go stale), but the app currently only runs via `next dev`.

### Fix shipped (not yet committed)

[app/login/page.tsx](\\wsl.localhost\Ubuntu\home\bmaksimov\Development\unitprep-ui\app\login\page.tsx): the post-login redirect now uses `window.location.assign("/clients")` (a hard navigation) instead of `router.replace("/clients")` — structurally immune to any stale client-router state, at the cost of one full page load on a rare, non-hot-path event. The *other* redirect in the same file (bouncing an already-signed-in visitor away from `/login`) was deliberately left as `router.replace`, since it doesn't follow a long-idle event. `tsc --noEmit` clean, `eslint` clean on the file, full `vitest` suite 439/439 passing (no dedicated login-page test existed to update).

## Related

- [[Process Street Integration — Kickoff & Findings]]
- [[Gotchas]]
- [[WSL Execution Technique]]
- [[New Laptop Migration — QSLP14]]
