---
date: 2026-10-09
description: "Measured concurrent-operator load on the real router + real test-db after the efficiency refactor (A4-A6 validation), inline-vs-blocking A/B, 20 ms-RTT runs, per-run storage footprint, CI-allowlist gap, ClickUp playbook audit."
tags: [work-note, unitprep, efficiency, benchmark, load-test]
status: completed
quarter: Q4-2026
project: unitprep
---

# Efficiency refactor: concurrent load results (2026-10-09)

Follow-up to an external review (Grok) of [[Efficiency Refactor - Code Review Brief]]. Its useful point was the brief's own admitted gap: **A4-A6 (CPU work off the async workers) and the pool changes were never measured under concurrent load.** This note records that measurement plus three smaller checks. Plan context: [[Efficiency Refactor - Master Plan and Progress]].

## Method

New ignored test `src/api/concurrent_load_tests.rs` (`concurrent_load_report`), **not yet committed** (api working tree: `M src/api/mod.rs`, `?? src/api/concurrent_load_tests.rs`; fmt + `clippy -D warnings` clean). It drives the REAL router over real HTTP: real durable session stores, real vendor registry, real RLS, real session cookie, production pool policy (20 connections, idle-gated ping). The server runs on its own runtime with a fixed number of worker threads; the load generator is separate. Per level it runs K concurrent dedup operators (2,400-row upload = 272 KB CSV, no think time: worst case) plus 2 facility-detail readers and a **canary** (`GET /health/whoami`, session resolution + RLS, no CPU) every 20 ms. A stalled event loop shows up as canary latency.

```text
TEST_DATABASE_URL=postgres://app_service:app_service@127.0.0.1:5433/unitprep_test \
  cargo test --release --bin unitprep -- --ignored --nocapture concurrent_load_report
```
Knobs: `LOAD_WORKERS` (4), `LOAD_SECONDS` (12), `LOAD_ROWS` (2400), `LOAD_LEVELS` (1,4,8,16), `LOAD_MAX_RUNS` (400). Through `dev-tools/latency_proxy.py --delay-ms 10` (port 5434) it repeats with a 20 ms DB round trip. Machine: 22 cores, loopback Postgres 18 in Docker; absolute numbers are this box's, ratios are the point.

## Results: canary latency while heavy tools run (ms; direct DB, 4 server workers)

| dedup operators | canary p50 / p95 / p99 (max) | dedup check p50 / p95 / p99 | checks/s | peak pool in use |
|---|---|---|---|---|
| 0 (idle) | 1.3 / 1.7 / 2.1 | - | - | - |
| 1 | 2.3 / 3.5 / 5.4 (7.7) | 200 / 228 / 235 | 4.9 | 6 of 20 |
| 4 | 2.5 / 5.5 / 9.4 (16) | 234 / 267 / 271 | 17.2 | 5 |
| 8 | 3.1 / 7.3 / 14 (15) | 294 / 376 / 431 | 26.8 | 11 |
| 16 | 3.9 / 15 / 25 (60) | 375 / 750 / 918 | 38.7 | 18 |

Zero 5xx / transport errors at every level. Repeat runs vary at the tail (one 16-operator repeat had a 518 ms canary max); medians are stable. Facility detail (the multi-query page) tracks the canary: p50 2-6 ms.

**Only 2 server workers:** 8 operators canary 3.0 / 11 / 20 ms; 16 operators 5.3 / 49 / 88 (max 238) with the pool at 20 of 20. Still responsive.

## A/B: what moving CPU off the async workers is worth

Temporary, uncommitted patch making `spawn_blocking_in_span` run inline (reverted; tree verified clean of it). Same load, 4 workers:

| dedup operators | canary p50 / p99, BLOCKING pool (shipped) | canary p50 / p99, INLINE on async workers |
|---|---|---|
| 1 | 2.3 / 5.4 | 2.3 / 6.3 (max 130) |
| 4 | 2.5 / 9.4 | **38.7 / 157** |
| 8 | 3.1 / 14 | **386 / 602** |
| 16 | 3.9 / 25 | **857 / 1054** |

Inline, throughput also plateaus at ~19.5 checks/s vs 27-39 with the shipped design. **Conclusion: A4/A5/A6 are validated: without them four concurrent operators would make every other request wait ~40 ms, eight ~400 ms.**

## 20 ms DB round trip (stand-in for remote Neon), 4 workers

Idle canary 127 ms (the round trips themselves). Under load the canary median stays 131-132 ms up to 8 operators (p99 ~200 ms); at 16 operators 186 / 293 / 390 ms. A single dedup check costs ~690 ms (vs ~200 direct) and the pool reaches 20 of 20 at 8 operators, so **with a remote database the pool, not the CPU, is the first thing to saturate.** Even so no request failed. Caveat: the Python proxy also throttles the ~1.9 MB payload, so part of the 690 ms is transfer through the proxy, not round trips.

## Finding: each stored dedup run is ~1.9 MB

`client_ops.tool_runs` stores 1,872 KB per run at 2,400 rows (encrypted source ~272 KB + encrypted records ~1.6 MB; encrypted data does not compress). Roughly **1,000 runs = 1.9 GB** of Neon storage. Not a problem today; decide a retention/compaction policy (or drop `records` for old runs) before volume grows. This also bears on Grok's "durable session blob size" point: it is real but belongs to tool-run history, not just the live session.

## Incident during the work (do not repeat)

The first full run filled the test-db: its data directory is a **RAM-backed tmpfs (7.7 GB)** and the unbounded test wrote ~7.4 GB (3,269 runs x 2 MB). Postgres PANICked on WAL write; the test-db container died. Recovered with `docker compose --profile test up -d test-db` + `./scripts/bootstrap_test_db.sh` (data is ephemeral by design; fixtures from earlier tests were lost, none needed). The intermittent 500s seen on that run ("Failed to verify session") coincided with the filling disk and did **not** reproduce in two further clean proxy passes. The test now caps runs per level (`LOAD_MAX_RUNS`), reports the stored bytes per run, deletes its rows and `VACUUM`s between levels, and removes its fixture. Host RAM was at ~8.5 GB used during the incident; check `docker exec unitprep-api-test-db-1 df -h /var/lib/postgresql` after any heavy DB test.

## CI coverage check (Grok #12)

`scripts/run_ci_db_tests.sh` is an explicit allowlist of 18 test names (deliberate, safe-by-default). The workspace has 144 `#[ignore]`d tests, of which **103 are the hermetic `_db_` family** (A1 session resolution, B2/B3 resync + sync, D4g registration, G1 audit rows, ClickUp links/copy/duplicate-check/connection, parent, waiver, people, summary, task roles, tool-run sealing). **They pass in 1.5 s against a fresh test-db and none reaches an external host** (the `app.clickup.com` strings are pasted-URL test data; the mock servers bind loopback). Almost all of them are NOT in the CI allowlist, so the refactor's own safety nets run only when someone runs them by hand. Options (a policy decision, not made): (1) add one extra step `cargo test --workspace -- --ignored _db_` (relies on the naming convention being hermetic; a new `_db_` test would be picked up automatically, which loosens the "new test does not join CI by omission" rule); (2) append the ~85 names to the allowlist (keeps the rule, costs a long list). Related: [[CI Backlog]].

## ClickUp playbook audit (Grok #2)

Grok assumed ClickUp skipped the integration standards. In the code: shared `integrations::http` client policy (timeouts, retry honouring `Retry-After`); every fan-out bounded by hand-rolled chunks of 4 (`WRITE_CONCURRENCY`, `LIST_READ_CONCURRENCY`, `CHUNK_SIZE`, task pages batched and capped by `MAX_TASK_PAGES`); a **per-user sliding-window rate limiter (~100 req/min, `clickup/rate_limit.rs`)** plus a call budget that moves large copies to background jobs; no database transaction opened in the copy/duplicate-check handlers (nothing held across ClickUp HTTP); the two `tokio::spawn` sites are one-per-request fire-and-forget (prefetch, Dropbox link store). Not verified: whether `task_cache::get_or_load` coalesces concurrent loads for the same user (minor). **No change needed.**

## Remaining of Grok's list, disposition

XLSX (#1): 154 ms at 5,000 rows on the blocking pool; do nothing unless operators report waiting. Tagger parse cache (#4), payload shape (#5), file splits (#7), bundle size (#8), hand-written TS (#9), migration squash (#10), Playwright in CI (#13): already in the brief's deliberate-deferrals or "touch when editing". `EXPLAIN ANALYZE` on production-shaped data (#14): do once real prod traffic exists.
