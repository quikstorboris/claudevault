---
date: 2026-10-19
description: "First Monday check on the new observability stack: why logs seen in the terminal looked missing in Grafana (they were there, the view was stale), why the server looked silent over the weekend (idle, not broken), what the before_acquire warning at 03:14 PT means, what the weekend's few log lines were, and that Sentry holds only Friday's test issues. All evidence and commands."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Check-in 2026-10-19: weekend quiet, the pool warning, an empty Sentry

Part of [[Server Logging and Grafana - Index]]. Follows [[Build Timeline 2026-10-16 (Part 1)]]. How the tools used here were set up: [[Reading Logs - Tools and Recipes]] and [[Sentry and Grafana Access for Claude]].

## What Boris asked (Monday 2026-10-19, about 08:15 PT)

He pasted three lines from the bash window where the server has been running since Friday:
```
2026-10-19T10:00:13.55Z INFO ...schedule: Process Street sync scheduled (daily_time) next_sync_at=2026-10-20 10:00:00 UTC timezone=America/Los_Angeles
2026-10-19T10:14:24.85Z WARN sqlx_core::pool::inner: error from `before_acquire` error=error communicating with database: expected to read 5 bytes, got 0 bytes at EOF   (twice)
```
and asked: why is this not in Grafana, what is the warning about, why did logging seem to stop last week although the server has been up all along, and is there anything real in Sentry (he saw mostly fake errors).

## Finding 1: nothing stopped; the lines are in Grafana

Evidence (all read at 08:17 PT, 15:17Z):
- **Local files** in `unitprep-api/logs/`: `unitprep-api.2026-10-16.log` (61,290 B, last write 16:34 PT Friday), `-17` (24,951 B, 03:01), `-18` (6,234 B, 11:14), `-19` (6,106 B, 03:14). The three newer files are owned by `root` (the container writes them). The 10-19 file's last two lines are the two `before_acquire` warnings.
- **Containers**: `alloy-1`, `api-dev-1`, `test-db-1` all "Up 2 days". Alloy's log shows it started tailing `/logs/unitprep-api.2026-10-19.log` at 10:00:06Z, i.e. it noticed the new daily file within seconds; no push errors.
- **Loki** (`scripts/logcli.sh`, 8 days back): lines per day **146** (10-16), **66** (10-17), **15** (10-18), **16** (10-19). **Newest line in Loki: `2026-10-19T10:14:24.859981Z`**, exactly the last line Boris pasted. So the terminal and Grafana agree.
- Why it looked missing: that line was 5 hours old (03:14 PT, viewed at 08:17 PT). Explore and Drilldown default to **the last hour** and the dashboard to **six hours**, so a default view shows nothing; and these pages are snapshots until refreshed (see [[Grafana Cloud Setup and Objects]]). Use Last 24 hours or 7 days and refresh.

## Finding 2: "logging stopped last week" was the server being idle

The server writes a line per request and for a few background jobs; it logs nothing while nobody uses it. No request has hit the server since Friday evening, so the weekend's files are small. What was in them (counted from the files):

| Day | Lines | What they are |
|---|---|---|
| 10-17 (Sat) | 66 | 25 `ClickUp rate limiter full, call is waiting` WARNs + 39 `Process Street call` INFOs + `Process Street person-index sync completed` + `sync scheduled` |
| 10-18 (Sun) | 15 | 3 limiter waits + 9 Process Street calls + the two sync lines + 1 `slow statement` WARN at 18:14:26Z |
| 10-19 (Mon) | 16 | 3 limiter waits + 9 Process Street calls + the two sync lines + 2 `before_acquire` WARNs at 10:14:24Z |

- The daily burst is the **03:00 PT (10:00Z) Process Street person-index sync** (`daily_time` schedule), which also makes ClickUp calls and so trips the in-process ClickUp rate limiter (80 calls per 60 s per user) a few times. It is the limiter doing its job (calls wait, none fail), not an error. Saturday's run was larger (25 waits, 39 calls) than Sunday's and Monday's (3 waits, 9 calls); not investigated. These are the first real looks at ClickUp traffic made possible by the ClickUp logging added on 2026-10-16.
- There were **no request lines**, no ERRORs and no panics on 10-17, 10-18 or 10-19.

## Finding 3: the `before_acquire` warning, explained

`WARN sqlx_core::pool::inner: error from 'before_acquire' ... expected to read 5 bytes, got 0 bytes at EOF`:
- The API keeps a pool of database connections. Neon suspends its compute when idle, which kills the idle connections. Before reusing a connection that has sat idle 30 s or more, the pool tests it with a real `SELECT 1` (the fix in api `6556023`, see [[Findings - DB Connection Drops, Cold Starts and Latency]]). The test failed on a dead connection, the pool **discarded it and opened a fresh one**, which also wakes Neon. The warning is that mechanism reporting its work. **No request failed**: there is no ERROR line and nobody was waiting.
- Two lines at the same instant = two dead connections discarded together.
- **Why at 10:14:24?** Boris's server last started at **2026-10-16T22:14:24Z**. 10:14:24Z on 10-19 is exactly **36 h = 9 x 4 h** later, and the `slow statement` on 10-18 at 18:14:26Z is exactly 44 h = 11 x 4 h. So a **background job that runs every 4 hours from startup** uses the pool; most runs find live connections and log nothing, some find the idle ones dead. The efficiency refactor's notes name the remaining wakers as "two 4-hour registry refreshes and the PS sync interval" ([[Efficiency Refactor - Idle Database Wake-ups (Neon Compute)]]). **This session did not read that task's code**, so which job fires at :14:24 is an inference from the timestamps.
- Cost: each such wake brings Neon's compute up for a few minutes (the known price of those refreshes). Not a new problem.
- This is a **second live observation that the `SELECT 1` ping works** (the first was the 2.3 s cold start on 10-16 at 21:00Z that returned 200 instead of 500). Still an observation, not proof of the original cause.

## Finding 4: Sentry holds only Friday's test events

Method (details in [[Sentry and Grafana Access for Claude]]): Sentry CLI 0.47.0 in WSL, logged in as Boris.
- `sentry issue list quikstor-wf/<project>` says "No issues found" for **both** `orchestrator` and `orchestrator-ui`. That list **defaults to unresolved issues only**; `--period` makes no difference (it defaults to 90 days). With `--query "is:resolved"` it shows five issues; `is:ignored` and `is:archived` are empty. (A first attempt with `--period 14d` and "No issues found" briefly looked like Sentry being empty; the lesson is in [[Gotchas]].)
- The five resolved issues, all from Friday 2026-10-16 between 21:35Z and 22:25Z (14:35-15:25 PT), all test events:
  - `ORCHESTRATOR-1` "unitprep-api Sentry setup check (safe to resolve)", 2 events (first 21:35:31Z, last 22:13:09Z)
  - `ORCHESTRATOR-UI-1` and `-2` "TypeError: Sentry.captureMessage is not a function" (an early test attempt), 1 event each
  - `ORCHESTRATOR-UI-3` "Error: sentry ui test" (/login), 2 events; `ORCHESTRATOR-UI-4` "Error: sentry ui test from claude browser" (/login), 1 event
- **Nothing real**: no unresolved issue, and the local logs contain **zero ERROR lines after 21:51Z on 10-16** (Sentry shipped in api 1.9.130 at 14:51 PT = 21:51Z). All 6 ERROR lines that exist (19:39-20:27Z on 10-16, the DB errors) predate Sentry. Warnings never become Sentry issues.
- Is the running server configured to report? Names only checked (values never printed): `SENTRY_DSN` and `SENTRY_ENVIRONMENT` lines exist in `unitprep-api/.env.local`, `NEXT_PUBLIC_SENTRY_DSN` in `unitprep-ui/.env.local`. The container's environment does not carry `SENTRY_DSN`, but the app reads `.env.local` itself at startup. The server's last start (22:14:24Z, 15:14 PT Friday) is after 1.9.130, so Sentry is active in it.
- **Not proven**: that the *running* server sends events, because no real error has happened since. The last API event Sentry has is the test at 22:13:09Z, one minute before that restart.

## Finding 5: origin has moved on; the local checkouts are behind

While preparing this record, `git fetch` showed:
- `unitprep-api`: local `HEAD 3615590` (1.9.131), `origin/main b59af80`, **behind by 3**, ahead by 0. `unitprep-ui`: local `7eb5b64` (1.6.100), `origin/main 23033ff`, **behind by 1**.
- They were pushed Friday 16:35-16:40 PT by **another session** (the efficiency refactor's second pass), after the work in Part 1 and Part 2:
  - api `7a8a4f5` **1.9.132**: `DB_POOL_MAX_CONNECTIONS` (default 20, accepted 1-200, else 20) makes the pool size configurable for a remote database; ts-rs bindings for `UserSummary`, `CreateInviteRequest`, `SyncStatusResponse` (replacing hand-written UI types); `scripts/tool_runs_storage.sql`; a docx timing test; RUNBOOK sections "Database pool and load" and "Stored tool runs (retention)".
  - api `7ab0506`: the large ClickUp modules split into focused files (code moved verbatim; `clickup_connection/`, `clickup_run_update/`, `clickup_copy/bulk/`, the 1,400-line DB test file split).
  - api `b59af80`: `cargo audit` accepts three `zip` extraction advisories (RUSTSEC-2026-0367, -0368, -0369) in `.cargo/audit.toml`, review date **2026-11-16**.
  - ui `23033ff` **1.6.101**: generated types replace hand-written ones. Tags `v1.9.132` and `v1.6.101` exist on GitHub only.
- Boris's server and `cargo watch` container run the local 1.9.131 / 1.6.100 code. A fast-forward `git pull` in each repo plus a restart would bring them level. **Not done** (not asked; pulling changes files under a running server). The dashboard's ClickUp panels filter on message text, not module paths, so the ClickUp module split should not break them (**not verified**). The pool change sits next to the `SELECT 1` ping logic; the diff touches only the max-connections setting.

## What was not looked at

The 4-hourly job's code; why Saturday's sync made more calls; whether the `v1.9.129`/`v1.6.99` (and later) GitHub Actions runs passed; the running server's Sentry delivery.

## Related

[[Server Logging and Grafana - Index]] · [[Findings - DB Connection Drops, Cold Starts and Latency]] · [[Observability Plan and Open Tasks (Sentry + Grafana)]] · [[Gotchas]]
