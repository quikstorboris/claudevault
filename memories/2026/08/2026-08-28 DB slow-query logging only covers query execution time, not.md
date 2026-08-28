---
date: 2026-08-28
description: "unitprep-api's DB latency visibility (added 2026-08-28: sqlx's built-in `sqlx::query` tracing events, widened into the default log filter, with the…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T16:44:13.991Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# DB slow-query logging only covers query execution time, not pool-acquisition wait -- diagnostic implication for future latency complaints

unitprep-api's DB latency visibility (added 2026-08-28: sqlx's built-in `sqlx::query` tracing events, widened into the default log filter, with the slow-statement threshold tightened in db.rs) only times time spent actually EXECUTING a query against Postgres. It does NOT time how long a request waited to acquire a free connection out of the pool (`PgPoolOptions::new().max_connections(5)` in `src/db.rs`) before that query could even start.

**Why this matters for future diagnosis**: if Boris (or anyone) reports "requests feel slow" once more people are actually using Orchestrator concurrently, and the sqlx slow-query logs come back clean (no WARN-level `sqlx::query` lines, or only occasional ones well under whatever threshold was set), do NOT conclude the database isn't the bottleneck. A clean query-latency log is consistent with EITHER "the DB genuinely isn't the problem" OR "requests are queueing waiting for one of only 5 pooled connections to free up, and that wait time is currently invisible." The two need to be told apart before reasoning further about root cause -- don't jump to "must be something else entirely" (network, frontend, unrelated code) just because query execution itself looks fast.

**What actually distinguishes them, if it comes up**: pool-acquisition-wait-time has no instrumentation yet. The diagnostic move at that point is to add it (e.g. wrapping `pool.acquire()` calls or checking sqlx's `PoolOptions` hooks for a way to time acquisition, at the point this is actually needed) rather than guessing from query-execution numbers alone. Also worth just checking `max_connections(5)` against actual concurrent request volume at the time -- 5 was set when this app had essentially one user testing it locally, not a demo audience.

This was recorded specifically as a forward-looking trigger, per Boris's own request, for when a real latency complaint arises later in this project.

## How this is known

Read directly from unitprep-api's src/db.rs (max_connections(5), connect_lazy_with) and from sqlx-core-0.8.6's actual installed source (src/logger.rs) confirming QueryLogger only times from query start to query finish, with no pool-acquisition timing anywhere in that crate.
