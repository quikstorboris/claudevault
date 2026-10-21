---
date: 2026-10-19
description: "Append-only log of the twice-daily UnitPrep anomaly check (07:30 and 19:30 PT): one entry per run with status, what was found, and what was done. Newest entries at the bottom."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Routine check log

Append-only record written by the scheduled task `unitprep-anomaly-check` (and by hand). Rules, known-benign patterns and the fix policy are in [[Routine Monitoring and Troubleshooting Playbook]]; index in [[Server Logging and Grafana - Index]]. One entry per run, newest at the bottom, even when everything is clear. Format:

`### YYYY-MM-DD HH:MM PT | STATUS (ALL_CLEAR / ATTENTION / BLIND) | ANOMALIES=n` then one or two lines: what was seen, classification, request_ids, and any action (auto-fix branch and worktree path, commit, preflight result) or "no change".

### 2026-10-19 09:25 PT | ALL_CLEAR | ANOMALIES=0 | (created by hand when the routine was set up)

Baseline run of `anomaly_check.py --hours 14 --include-resolved`: Sentry has 0 unresolved issues in `orchestrator` and `orchestrator-ui` (five resolved Friday test issues listed as information); 16 log lines in the window, 0 requests (idle app), 0 ERROR, 0 HTTP 5xx; information only: 2 pool `before_acquire` warnings, 3 ClickUp limiter waits. Freshness: `unitprep-api` behind origin/main by 3 commits, `unitprep-ui` by 1; the running server (last start 2026-10-16 22:14:24Z) is older than the checkout's newest commit. A 200 h window run was used to confirm the script detects the six real Friday ERRORs and six HTTP 500s (it did, ANOMALIES=12). Sentry token expires 2026-11-15 13:31 PT. No change made.

### 2026-10-19 19:45 PT | ALL_CLEAR | ANOMALIES=0

`anomaly_check.py --hours 14`: Sentry auth OK (token good until 2026-11-15), 0 unresolved issues in both `orchestrator` and `orchestrator-ui`. 62 log lines / 46 requests in window, 0 ERROR, 0 HTTP 5xx; information only: 8 pool `before_acquire` warnings, 3 slow statements. Freshness: both repos at 0 commits behind origin (api is 1 commit ahead, unpushed, 0 uncommitted files); the running server (last start 2026-10-16 22:14:24Z, 76.5h old) is on code older than the checkout's newest commit (2026-10-19T12:19:18) — same known cargo-run-doesn't-reload situation as prior checks, not an anomaly. No change made.

### 2026-10-20 07:44 PT | ALL_CLEAR | ANOMALIES=0

`anomaly_check.py --hours 14`: Sentry auth OK (token good until 2026-11-15), 0 unresolved issues in both `orchestrator` and `orchestrator-ui`. 147 log lines / 0 requests in window (idle app, quiet log expected), 0 ERROR, 0 HTTP 5xx; information only: 2 pool `before_acquire` warnings, 65 ClickUp limiter waits. Freshness: both repos at 0 commits behind origin (api is 1 commit ahead, unpushed, 0 uncommitted files); the running server (last start 2026-10-16 22:14:24Z, 88.5h old) is on code older than the checkout's newest commit (2026-10-19T12:19:18) — same known cargo-run-doesn't-reload situation as prior checks, not an anomaly. No change made.

### 2026-10-20 19:45 PT | ALL_CLEAR | ANOMALIES=0

`anomaly_check.py --hours 14`: Sentry auth OK (token good until 2026-11-15), 0 unresolved issues in both `orchestrator` and `orchestrator-ui`. 158 log lines / 69 requests in window, 0 ERROR, 0 HTTP 5xx; information only: 28 pool `before_acquire` warnings, 4 slow statements. Freshness: both repos at 0 commits behind/ahead of origin, 0 uncommitted files; the running server (last start 2026-10-20 18:43:18Z, 8.0h old) is on code slightly older than the checkout's newest commit (2026-10-20T12:05:06) — same known cargo-run-doesn't-reload situation, not an anomaly. No change made.

### 2026-10-21 07:45 PT | ALL_CLEAR | ANOMALIES=0

`anomaly_check.py --hours 14`: Sentry auth OK (token good until 2026-11-15), 0 unresolved issues in both `orchestrator` and `orchestrator-ui`. 432 log lines / 0 requests in window (idle app, quiet log expected), 0 ERROR, 0 HTTP 5xx; information only: 0 pool `before_acquire` warnings, 206 ClickUp limiter waits. Freshness: both repos at 0 commits behind/ahead of origin, 0 uncommitted files; the running server (last start 2026-10-20 18:43:18Z, 20.0h old) is on code older than the checkout's newest commit (2026-10-20T12:05:06) — same known cargo-run-doesn't-reload situation, not an anomaly. No change made.

### 2026-10-21 12:36 PT | ATTENTION | ANOMALIES=12 | ad hoc check at Boris's request ("check now"), not the scheduled run

`anomaly_check.py --hours 14` found 4 unresolved Sentry issues (`ORCHESTRATOR-2..5`: company detail query, facility existence check, session resolution, ClickUp token load) + 4 ERROR + 4 HTTP 500, all in one incident window 2026-10-21 16:10:58–16:14:11 UTC (9:10–9:14 AM PT). Root cause, confirmed from logs and source: the idle-connection health check (`ping_through_to_backend` in `src/db.rs`) was sending its `SELECT 1` as an unnamed prepared statement (`query(..).persistent(false)`); Neon's transaction-mode PgBouncer can route that statement's Parse/Bind/Execute to different backends, and a burst of `WARN sqlx_core::pool::inner error from before_acquire: unnamed prepared statement does not exist` discarded a run of connections, starving real requests into the 10s pool-acquire timeout (4 consecutive HTTP 500s, ~10s latency each). **Classification: already fixed, not yet committed** — `src/db.rs` has an uncommitted change (`git status`: `M src/db.rs`) switching the ping to `sqlx::raw_sql("SELECT 1")` (simple query protocol, can't be split across backends), with a doc comment dated 2026-10-21 describing this exact incident; the currently running server (started 19:24:24 UTC / 12:24 PM PT, after the incident) is already running that fix. Per the main-checkout guardrail, made no edits to `src/db.rs` (visibly in-progress, uncommitted — appears to be Boris's own same-day fix). Reported to Boris; left the commit and any Sentry issue resolution to him. Freshness: `unitprep-api` 0 behind/ahead origin, 1 uncommitted file (`src/db.rs`, the fix above); `unitprep-ui` 0 behind/ahead, 0 uncommitted.
