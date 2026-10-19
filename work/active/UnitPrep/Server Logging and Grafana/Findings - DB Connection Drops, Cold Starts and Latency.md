---
date: 2026-10-16
description: "The evidence trail for the dev server's idle database problems found through the new logs on 2026-10-16: the 500s after idle, the dead-connection fix, the cold-start slowness, and why warm requests cost 250-400 ms (about five round trips at 50 ms to Neon in Oregon). Every timestamp, measurement and decision."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Findings: DB connection drops, cold starts and latency

Part of [[Server Logging and Grafana - Index]]. Durable lessons are also in [[Gotchas]] (the database-fix session wrote "First requests after a long idle can hit a dead pooled connection"). Background on why Neon suspends: [[Efficiency Refactor - Idle Database Wake-ups (Neon Compute)]]. Cloud-move implications: [[UnitPrep Fly.io and Deployment Notes]].

All times below are UTC (Z) with Pacific time (PT = UTC-7) where useful. The logs themselves were read through the new Grafana/Loki tooling, which is why this was diagnosable in minutes.

## 1. The 500s after a long idle (first seen 12:39 PT)

- Server started 19:29:03Z (12:29 PT) from a binary built 19:29:01Z.
- **19:39:10Z - 19:39:22Z**: after ~10 idle minutes the first four database-touching requests failed: `POST /auth/login/begin` (19:39:10, 19:39:22) and `GET /health/whoami` (19:39:15, twice). Each logged `ERROR ... error communicating with database: expected to read 5 bytes, got 0 bytes at EOF` and returned **HTTP 500 in 1-4 ms**, followed by a `WARN error occurred while testing the connection on-release`. **1 ms means an already-dead pooled connection was handed out**, not a slow query or a new connection (a new TLS+auth connection to Neon takes far longer).
- **19:43:51Z - 19:43:59Z** (Claude probing `GET /health/db` six times a second apart): all returned 200; the first took ~1.0 s, the rest 0.31-0.34 s; each probe logged one `WARN error from 'before_acquire'` (the idle-gated ping discarded one dead connection per request, 6 in total). So the pool self-heals one connection per request, but the first requests after a long idle can still reach dead connections.
- The pool settings (`src/db.rs`): `max_connections(20)`, `acquire_timeout(10s)`, `test_before_acquire(false)` plus a custom `before_acquire` that pings only connections idle >= 30 s (`PING_IDLE_THRESHOLD`). Connection string is Neon's `-pooler` (PgBouncer) endpoint.
- **Hypothesis (unproven)**: sqlx 0.8's `ping()` is a bare protocol `Sync`; PgBouncer can answer that without a backend, so a connection whose backend died (Neon compute suspended) can pass the check and fail on the first real statement.
- **Fix (commit `6556023`, shipped in api 1.9.129)**: the idle ping now runs a real `SELECT 1` (`ping_through_to_backend`), still only when idle >= 30 s; test `the_idle_ping_discards_connections_whose_backend_was_killed` (`--ignored`, local test-db). The database-fix session (`local_b58b2e85-...`) **could not reproduce the 500 on demand**; on a dev server idle 7-12 min every dead connection was caught by `before_acquire` (one WARN per request, ~0.65 s each, no 500). It also noted: the laptop was in **Modern Standby 12:31-12:37 PDT** (just before the first failures at 12:39), WSL's monotonic clock does not stall in standby (uptime matched wall clock, so `idle_for` is not underestimated), and probing several servers in parallel keeps the shared Neon compute awake and hides the problem. Residual risk accepted: a dead connection that is trusted (idle < 30 s) can still fail one request. "Do not reintroduce `conn.ping()`."
- **The fix was not live in Boris's server at first.** On 2026-10-16 at 20:27:29Z the same error returned for two requests (`GET /client-ops/qms-tags`, 18 ms and 4 ms, no `before_acquire` WARN beforehand, so the old ping had passed the dead connections). Cause: his server (pid 11075) had started at 20:07:19Z from a binary built 19:29:01Z, while the fix was committed at **20:24:22Z (13:24:22 PT)**. `cargo run` does not reload, so a restart was needed. Boris restarted several times afterwards (20:31:30/20:32:13, 20:46:57/20:47:01, 20:49:50/20:49:52).
- The 20:27:29 errors tripped the Grafana error alert (Normal -> Alerting 13:28:00 PT), the first real end-to-end alert; Boris pasted that email.

## 2. The first request after idle is slow, but no longer fails (14:00 PT)

After the fix was running (server started 20:49:52Z, idle ~11 minutes):
- **21:00:44Z - 21:00:48Z**: `GET /clients` took **2275 ms**, `GET /clients/filter-options` **2465 ms** and a follow-up `filter-options` **957 ms**, all HTTP **200**; five `WARN error from 'before_acquire'` lines (dead connections discarded, each replaced by opening a new one) and two `slow statement` WARNs (`SELECT user_id, role_keys, permission_keys ... FROM auth.resolve_session($1,$2)` at 356 ms, over the 200 ms threshold). **No ERROR lines in the last 20 minutes.**
- Reading: Neon scale-to-zero cold start (about 1.5-2.5 s for the first connection through the pooler) plus dead pooled connections being discarded and reopened one at a time. The UI fires `/clients` and `/clients/filter-options` concurrently, so several requests each pay.
- This was the first live evidence that the real `SELECT 1` ping turns the 500s into a slow-but-successful request. **One observation, not proof.**
- **Decision (Boris, ~14:05 PT): "accept neon".** Options laid out: (1) accept it (dev, once per idle gap, the cost of scale-to-zero); (2) set the pool `idle_timeout` below Neon's ~5-minute suspend window to drop connections before Neon kills them (removes the discard pile-up, not the cold start); (3) turn off Neon auto-suspend (higher bill, undoes part of the efficiency work; a go-live decision). Revisit at go-live. Nothing was changed.

## 3. Why a *warm* request costs 250-400 ms

Boris pasted four warm requests at 21:04:11Z: `GET /clients` 387 ms, `GET /clients/filter-options` 519 ms and 383 ms, and a first one of 843 ms (path cut off; that size fits a request that opened a fresh connection, a few extra round trips on top).

Per-route latency from Loki (last 3 h, ~14:05 PT, `request completed` lines, ids collapsed to `:id`; samples are small and include the cold ones):

| Route | n | min | median | p90 | max |
|---|---|---|---|---|---|
| POST /auth/login/finish | 1 | 937 | 937 | 937 | 937 |
| GET /client-ops/qms-tags | 6 | 4 | 437 | 893 | 893 |
| GET /clients/filter-options | 10 | 253 | 400 | 2465 | 2465 |
| GET /integrations/clickup/connection | 3 | 219 | 320 | 571 | 571 |
| PUT /clients/:id/implementation-completed | 1 | 320 | 320 | 320 | 320 |
| GET /health/db | 6 | 310 | 318 | 998 | 998 |
| GET /clients | 6 | 182 | 288 | 2275 | 2275 |
| GET /health/whoami | 9 | 1 | 276 | 1697 | 1697 |
| GET /clients/:id | 2 | 253 | 267 | 282 | 282 |
| POST /integrations/clickup/prefetch | 4 | 221 | 247 | 259 | 259 |
| POST /auth/logout | 1 | 157 | 157 | 157 | 157 |
| POST /auth/login/begin | 3 | 1 | 1 | 81 | 81 |
| OPTIONS (various) / GET /health / GET /nope | - | 0 | 0 | 0 | 0 |

- **Network distance**: the dev database host is Neon in **us-west-2 (Oregon)** (`ep-winter-hill-a6qmwens-pooler.us-west-2.aws.neon.tech`). A raw TCP connect from the WSL laptop took **53, 48, 55, 60 and 49 ms**.
- **Round trips**: a signed-in request does a session lookup (`auth.resolve_session`), then `begin_for` -> `begin_rls_transaction` (pool begin + a statement that sets the RLS claims), the data query, and commit: roughly **five sequential round trips**. 5 x ~50 ms = ~250 ms, matching the warm medians (288 / 400 / 276 / 318 ms). Routes with no database work (`/health`) take 0 ms. This is read from the code (`src/api/rls.rs`, `src/auth/authenticated_user.rs`) and **not traced statement by statement**.
- Therefore **latency is mostly distance, not slow queries**. Hosted in or near us-west-2, the same five round trips should cost a few milliseconds each, roughly an order of magnitude less. Do not spend effort shaving round trips now; **pick the cloud host's region next to the Neon region** (which Fly.io region is closest to us-west-2 was not checked). Recorded in [[UnitPrep Fly.io and Deployment Notes]].

## 5. The weekend (2026-10-17 to 10-19): a second live observation, and the 4-hourly timer

Read on 2026-10-19 ([[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]]): with no traffic since Friday evening, the server logged only the 03:00 PT sync and a few warnings. At **2026-10-19T10:14:24Z** two `WARN error from 'before_acquire' ... expected to read 5 bytes, got 0 bytes at EOF` appeared together with **no ERROR and no failed request**: two dead pooled connections were discarded and replaced by the real `SELECT 1` ping, which is the fix doing its job (the first live observation was the 2.3 s cold start on 10-16 that returned 200 instead of 500). The timestamp is exactly **36 h = 9 x 4 h** after the server's last start (2026-10-16T22:14:24Z), and a `slow statement` on 10-18 at 18:14:26Z is exactly 44 h = 11 x 4 h after it, so a **background job every 4 hours from startup** is what touches the pool. (Which job: inferred from the timestamps and the efficiency refactor's note about "two 4-hour registry refreshes"; the code was not read.) Each such wake brings Neon's compute up for a few minutes. Still one more observation, not proof of the original idle-500 cause.

## 4. Still to verify

- A long idle with the fix running **and** the real 500 window: watch the dashboard's "Database connection errors" panel for a week; zero 500s after idle would support the hypothesis.
- If this error returns with **no** `before_acquire` warning beforehand, look at the pooler path, not the pool settings.
- Whether a shorter pool `idle_timeout` is worth it (option 2 above) once cold-start behaviour is judged on real use.

## Related

[[Server Logging and Grafana - Index]] · [[Grafana Cloud Setup and Objects]] · [[Reading Logs - Tools and Recipes]] · [[Production Readiness Checklist]]
