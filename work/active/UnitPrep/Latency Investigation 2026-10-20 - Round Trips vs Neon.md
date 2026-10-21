---
date: 2026-10-20
description: Why OO API requests take 300 ms to 2 s on the dev setup - per-request SQL round trips and new connections to Neon, not Rust. Measurements, model, fixes, method gotchas.
tags:
  - work-note
  - unitprep
  - performance
status: active
quarter: Q4-2026
---

# Latency investigation, 2026-10-20: the API is slow because of database round trips, not Rust

Related: [[UnitPrep Fly.io and Deployment Notes]] (cloud-move hub, same-region fix), [[Gotchas]], [[Efficiency Refactor Master Plan]] (earlier round-trip work), [[UnitPrep Docker Standards]].

**Question:** backend logs show p50 ~318 ms, p90 ~970 ms, p99 ~2.3 s (162 requests, 2026-10-16..20), where early on everything was double-digit ms. Is "stupid fast" worth chasing?

**Answer: yes, and the cause is network, not code.**

## Evidence

Local run (second API instance from the dev container's debug build, local `test-db` Postgres 18, empty tables, bench admin session):

| Endpoint | Local wall time | SQL statements (+1 `BEGIN` not logged by sqlx) |
|---|---|---|
| `/health` | 2-3 ms | 0 |
| `/health/db` | 3-4 ms | 1 |
| `/health/whoami` | 8 ms | 5 (session, set_config, 2 reads, COMMIT) |
| `/clients` | 6-9 ms | 4 |
| `/clients/filter-options` | 8-9 ms | 6 (3 sequential SELECTs) |
| `/clients/staff` | 7 ms | 4 |
| `/client-ops/qms-tags` | 8 ms | 4 |

Real round trip to the Neon dev DB (laptop to `us-west-2` pooler endpoint, measured with psql and raw TCP):

- TCP connect ~45 ms.
- **Per-statement round trip on a warm connection ~36 ms.**
- **New connection (TLS + SCRAM + pooler) ~300 ms**; first one after idle 849 ms.

## The model fits the logs

`latency ~ 36 ms x (round trips) + ~300 ms x (new connections needed) + real query time`

- `/health/whoami`: 6 round trips x 36 = 216 ms predicted, 220 ms observed median.
- `/health/db` observed median 318 ms = one cold connection (it is polled rarely, so the pool is idle).
- Tails of 1-2.5 s = cold/new connections and Neon wake-up. `/clients/filter-options` opens several connections via `tokio::join!`, each potentially a new 300 ms handshake.
- List endpoints run 100-250 ms above the model: real query execution on real data. Not yet measured (needs per-statement elapsed against Neon).

## Where the round trips come from (code)

- `src/auth/authenticated_user.rs`: session lookup = 1 round trip on every gated request.
- `begin_rls_transaction`: `BEGIN` + `set_config` + `COMMIT` = 3 more, on ~195 handlers.
- Handler queries, some sequential (`filter-options` runs 3 SELECTs in series).
- Already done in earlier refactors: ping skipped unless idle >= 30 s (`src/db.rs`), GUCs set in one statement, `tokio::join!` in client detail.

## Candidate fixes (not yet done)

1. Fold session lookup + RLS setup into one round trip (or cache the resolved session for a few seconds).
2. Combine `BEGIN`/`set_config` into the first statement, or avoid a transaction for pure reads where RLS context can be set differently.
3. Merge sequential reads into one query (`filter-options`).
4. Keep a few connections warm (`min_connections`, idle/max lifetime settings, keepalive) so requests never pay the 300 ms handshake.
5. Biggest lever: put the API and database in the same region (the planned cloud move). A same-region round trip is ~1-2 ms.

## Method gotchas (do not repeat)

- **A second API instance started inside the dev container loads `/app/.env.local` through the bind mount (`dotenvy`) and picked up real Process Street credentials.** `/clients/search` then made 6 run listings + 84 form-field reads (all GET, read-only) against Process Street. Fix: start the bench instance with `cd` into an empty directory, fake `DROPBOX_*`, `PROCESS_STREET_API_KEY`, `CLICKUP_API_BASE_URL=http://127.0.0.1:9`, `INTEGRATION_SECRETS_ENCRYPTION_KEY`, blank `SENTRY_DSN`, and `LOG_DIR` in `/tmp` (so Alloy never ships bench logs to Grafana).
- `pkill` does not exist in the dev container; use `kill <pid>` found via `/proc/*/cmdline`. SIGTERM waits for in-flight requests.
- `docker exec` containers have no curl/python; bash `/dev/tcp` works for timing.
- sqlx's `sqlx::query=debug` log gives per-statement `elapsed`; `BEGIN` is not logged but is a wire round trip.
- Local empty-table timings hide real query cost; query counts are valid, times are not.
- `dev-tools/latency_proxy.py` (adds artificial latency in front of `test-db`) exists for this and was not needed here.

## Left behind

Local `test-db` (tmpfs, throwaway) is now migrated (117) with a bench admin user and session; it vanishes when the container is recreated.

## Follow-up 2026-10-21: compute audit (Neon dev) and the `filter-options` fix

**Scope decision (Boris):** keep scale-to-zero; no keep-warm connections, no region move. Round-trip tax is accepted. Anything that reduces compute is a win, "no need to get crazy".

**Query cost is not the problem.** `EXPLAIN ANALYZE` (read-only, admin GUC, rolled back) on the Neon dev DB: 23 companies, 35 facilities, 120 QMS tags, 46 tool runs. Execution times: qms-tags 0.12 ms, both `DISTINCT` filter queries 0.07 ms, client list 0.33 ms; only `auth.staff_directory()` took 7 ms (cold, 14 buffer reads). Each statement still costs ~34 ms of round trip. `pg_stat_statements` is NOT installed on the dev DB. The latency above the round-trip model comes from connection setup after idle (pool idle ping + reconnect through the pooler), which is the scale-to-zero price.

**What wakes the compute on its own (API, no user activity):**
- `client_ops::vendor_format::start_refresh_task` x2 (units, tenants) and `vendor_file_meta::start_refresh_task`: every 4 h, all three tick together = ~6 wakes/day, each keeping compute up for the autosuspend window (default 5 min, so roughly 30 compute-minutes/day on an idle server). Nothing writes `client_ops.vendor_format` / `vendor_file_meta` at runtime today (migrations only, which restart the server); the 4 h poll exists for a future self-service UI and for a pool that was not up at boot. Candidate: drop the periodic poll, refresh at startup (retry lazily if that failed) and from the future UI's write handler. NOT done yet, awaiting Boris's decision.
- Process Street sync: one scheduled sync per `sync_interval_hours` (default 24) plus a settings read before each sleep. Fine.
- Durable session sweeps (`core/src/durable_session_store.rs`): already redesigned to be scheduled-not-periodic. Fine.
- UI polling (`useCopyJobs`, 3 s) only runs while a copy job is `running`. Fine.

**Shipped (uncommitted in the working tree, 2026-10-21):** `src/api/clients_filter_options.rs` now runs ONE statement instead of three (saves 2 round trips, ~70 ms on Neon, and calls `auth.staff_directory()` once). New ignored real-DB test `get_filter_options_db_returns_canonical_states_sorted_pms_and_assigned_staff` passes on `test-db`; fmt and clippy clean. `src/db.rs` has a separate uncommitted change from another session (idle ping moved to the simple query protocol after `unnamed prepared statement does not exist` errors on 2026-10-21); untouched.

**Done 2026-10-21 (committed `d0480cb`, after `b1adf77` for filter-options):** the three registry refresh timers are removed. Each cache loads once at startup; `start_retry_if_unloaded` retries (30 s doubling, cap 15 min) only if that load failed, then stops; `refresh()` is the hook for a future vendor-editing UI. Verified on a started instance: 3 startup loads (previously 6, because each timer's immediate first tick duplicated `initial_cache`), 0 failures, 0 SQL statements in the 20 s after startup. Workspace tests, `clippy -D warnings` and fmt all clean. The dev server has to be restarted to pick this up. This also explains the `:14:24` `before_acquire` warnings in [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]] (three timers ticking every 4 h from server start). Superseded entries updated in [[Gotchas]].

Session record (decisions, slips, commits, open items): [[Session 2026-10-20 to 21 — OO Review Attempt, Latency and Neon Compute Audit, Release 1.9.134]]. Decision entry: [[Key Decisions]] ("Neon compute outranks latency"). Released as `unitprep-api` 1.9.134 (local, not pushed).
