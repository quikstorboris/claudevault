---
date: 2026-10-09
description: "Found after the refactor: five 60-second DELETE sweeps kept Neon compute awake 24/7. Replaced by a scheduled sweep; lists what still wakes the database and what to check on the cloud host."
tags: [work-note, unitprep, efficiency, neon, cost]
status: active
quarter: Q4-2026
project: unitprep
---

# Idle database wake-ups (Neon compute protection)

Follow-up to [[Efficiency Refactor - Master Plan and Progress]] and [[Efficiency Refactor - Concurrent Load Results]]. Question asked 2026-10-09: "are we protecting Neon compute?" The refactor protected the **request path** (no per-request session write, no ping per acquire, batching, bounded fan-out). It had never audited the **idle** path.

## Status (2026-10-09)

**Shipped in `unitprep-api` v1.9.119** (fix commit `a9c7636`, bump `ab50c57`, pushed and tagged). No migration. It went out together with the ClickUp session's v1.9.118 (`7482063`, `4534313`, `2776aac`; migration `20261009120000`), which sat unpushed beneath it in the same checkout; I reviewed those commits first (migration round-trips down and up, 107 `_db_` tests and the full preflight green at HEAD, UI and API route names match). Dev Neon already had `20261009120000`; **prod Neon is one migration behind (110 vs 111) until Boris runs `scripts/prod_db_sync.sh`** (interactive, he types `apply prod`). The new behavior needs nothing in the database.

## Finding

`DurableSessionStore::start_cleanup_task` (`core/src/durable_session_store.rs`) ran a `tokio::time::interval(60 s)` that issued a `DELETE ... WHERE kind = $1 AND last_accessed < ...` against `auth.durable_sessions`. There are five stores (Group Prep, dedup, tagger, registration ceremony, authentication ceremony), so **about five queries a minute, 24/7, as long as the server process is up.** Neon suspends compute after ~5 idle minutes (the default; whether prod has scale-to-zero enabled was NOT verified), so any timer under 5 minutes means compute-hours accrue for the whole month even with zero users.

Stale rows are never served (rehydration checks staleness and deletes the row), so the sweep is hygiene, not correctness.

## Fix

Replace the fixed timer with a **scheduled** sweep (`core/src/sweep_schedule.rs`, new):
- the first write after a quiet spell schedules one sweep for `now + timeout + 5 min grace` (rows expiring close together share one wake-up);
- each sweep deletes expired rows, then asks Postgres for the oldest row left (`min(last_accessed)`, covered by the existing `(kind, last_accessed)` index) and schedules the next sweep from that;
- nothing left means nothing scheduled and **no query at all**;
- one sweep 30 s after startup clears rows left by the previous process (the database is awake at startup anyway);
- a failed sweep retries after 60 s; a write landing in the gap between "sweep due" and "sweep started" gets a conservative follow-up.

Tests: 10 unit tests for the schedule plus 3 real-DB `_db_` tests (expired row removed then idle; leftovers cleared then idle; an idle store opens no connection, which the old design would have failed within milliseconds). The real-DB test caught a design flaw while I was writing it: a far-off startup sweep must be pulled forward by a row that expires sooner. No migration; no behavior change except when expired bytes are deleted.

## What still wakes the database when nobody is using the app

| Source | Cadence | Verdict |
|---|---|---|
| Vendor-format registry refresh (`client_ops/vendor_format.rs`) | every 4 h | fine; could be made lazy later |
| Vendor file-meta refresh (`client_ops/vendor_file_meta.rs`) | every 4 h | fine |
| Process Street background sync (`clients/sync`) | `sync_interval_hours` (1-168) | fine; keep the interval at hours |
| `GET /health/db` | whatever polls it | **do not point a host or uptime health check at it** (use `/health`, which does not touch the database) |
| The new scheduled sweep | a few times per active day | fine |

## On the cloud host (checklist, pairs with the cloud-move triggers)

1. Confirm in the Neon console that auto-suspend is enabled for the production compute and what the delay is.
2. After deploying, watch the compute's active periods over a quiet night: they should end ~5 min after the last request, apart from the 4-hourly refreshes.
3. Health checks and uptime monitors must hit `/health`, not `/health/db`.
4. More than one instance multiplies the per-process timers (4-hour refreshes, PS sync): see the ClickUp per-process note in `brain/Gotchas.md`.

## Lesson

A periodic background task that touches the database is a cost decision on a serverless database, not an implementation detail. Make background work event-driven (scheduled from the write that creates the work) rather than clock-driven, and when auditing "efficiency" include the idle path, not only the request path.
