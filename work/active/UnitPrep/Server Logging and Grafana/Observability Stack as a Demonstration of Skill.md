---
date: 2026-10-19
description: "An honest portfolio-style account of the observability stack built around UnitPrep/Orchestrator (structured logs, Loki/Grafana, Sentry): what it is, why it is overkill for an app with one user, what is still worth it, which engineering judgments it demonstrates (with evidence links), numbers that can be quoted, and what must not be overclaimed."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# The observability stack as a demonstration of skill (with an honest scale check)

Boris's framing, 2026-10-19: this is a good thing to have **even as a demo of knowledge**, because **both Grafana and Sentry are overkill for something like OO**. This note keeps both halves true: what it shows, and how big it really is. Everything it cites is recorded in [[Server Logging and Grafana - Index]]; nothing here is stronger than that evidence.

## The scale check, first (so nothing below is inflated)

| Fact | Reality on 2026-10-19 |
|---|---|
| Users | **One** (Boris: developer, tester and user; few people know the app exists) |
| Deployment | **None.** Dev only on a laptop. Neon "prod" exists but is unused until a real deployment ([[UnitPrep Fly.io and Deployment Notes]]) |
| Log volume | 146 lines on the busiest day (the build day), then **66, 15, 16** (Sat, Sun, Mon), almost all the nightly sync. The weekend produced no request lines at all |
| Real errors since Sentry went live | **Zero.** Sentry holds five issues, all Friday's own test events ([[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]]) |
| Panic alert | Never fired (there have been no panics) |
| Cost | About nothing: Grafana Cloud free trial (ends 2026-10-30, permanent limits unverified), Sentry off unless a DSN is set, files on disk. No infrastructure to run |

So by volume, a Loki pipeline, two dashboards (about 28 panels once the other session's "Tools and people" section is counted), alert rules, a CLI and an MCP server **is overkill** for this app. A proportionate setup would be: the rotated JSON files plus `grep`/`logcli`, and Sentry's free tier for errors. Everything else (the dashboards, the alert rules, the Grafana MCP server, the request/user/client ID correlation) is the part that outruns the app's size. The Grafana email alerts were already retired in favour of Sentry the same afternoon, which is itself a sensible scale-down.

## Why it was still worth doing (honest reasons)

1. **It was cheap.** Free tiers, off-by-default Sentry, no servers; the incremental work was configuration and judgement, not operating anything.
2. **It found real problems on day one**, which is the best argument that the instrument earns its keep even at this size:
   - dead pooled database connections returning HTTP 500s in about 1 ms after an idle spell, diagnosed from the log timestamps, with the fix confirmed twice live ([[Findings - DB Connection Drops, Cold Starts and Latency]]);
   - the **latency is round-trip bound**: about five database round trips at ~50 ms to Neon in Oregon, so the hosting region matters more than any query work;
   - the ClickUp integration **logged nothing** (found by surveying the code, fixed the same day);
   - the first alert email said only `A=2 C=1` and was rebuilt to name the error, route and module;
   - Boris's running server was **older than the fix** (binary built 12:29, fix committed 13:24), which the logs plus git made provable;
   - the UI's finished-looking work depended on **uncommitted backend code** and would have shipped as a UI that 404s.
3. **It is groundwork for the cloud move.** The format (JSON, request IDs), the "stdout in the cloud, files in dev" split, the labelling (`env`), and the read tooling were built once and tested before they matter ([[Server Logging Design and Decisions]]).
4. **It is a learning vehicle with real data**, which is exactly the "demo of knowledge" use.

## What it demonstrates, with the evidence

| Skill | Evidence (where to look) |
|---|---|
| **Designing structured logging that is cloud-portable** | Two output layers under one filter, a bounded rotating file, `LOG_FORMAT`/`LOG_DIR`/`LOG_ENV`, stdout for the cloud ([[Server Logging Design and Decisions]]) |
| **Cardinality and privacy discipline** | Only `level`, `job`, `env` become Loki labels; request IDs, paths, messages stay in the line; correlation uses **IDs only, never names, emails or phones**; Sentry scrubber strips bodies, cookies, query strings, credential headers ([[Server Logging Design and Decisions]], Part 2 note) |
| **Diagnosing from evidence, not guesses** | "1 ms means an already-dead connection was handed out"; the 36 h = 9 x 4 h arithmetic that ties a warning to a background timer; binary build time vs commit time; TCP connect time x round trips = observed latency ([[Findings - DB Connection Drops, Cold Starts and Latency]], [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]]) |
| **Honest uncertainty** | Every note lists what is unverified (the pooler hypothesis, free-tier limits, Fly.io specifics, an alert email nobody has seen); a hypothesis is called a hypothesis |
| **Secrets hygiene** | Read-only tokens, one key extracted at a time from `.env.local` (never `source`d), compose passes single variables by interpolation, a token pasted into chat flagged immediately, token inventory records names and scopes only ([[Grafana Cloud Setup and Objects]]) |
| **Least-privilege tooling for an AI assistant** | `logcli` and the Grafana MCP server run read-only (`--disable-write`, a short tool list, telemetry off), checksums verified before install ([[Reading Logs - Tools and Recipes]]) |
| **Release engineering** | Pre-push preflight (format, lint, tests, audit, secret scans, type-drift and schema checks), changelog entries, version bumps, tags, shipping the dependent halves together; a docs-only change deliberately not tagged ([[Release 1.9.129 and 1.6.99 - Company Page Editing Review Record]]) |
| **Reviewing unfinished work like a stranger's PR** | Backend review of the company-edit code: double permission checks, RLS, a row lock, no injection surface, no migration needed, tests run on the local DB, three gaps listed rather than hidden |
| **Forward-looking architecture without premature building** | Region next to the database, ephemeral-disk-safe logging, a Fly.io hub note with the unverified items marked ([[UnitPrep Fly.io and Deployment Notes]]) |
| **Operating several parallel AI sessions safely** | Two follow-up sessions proposed, started by Boris, verified from the git log; another session's uncommitted notes read but never edited; WSL git vs Windows git confusion caught before a blind commit ([[Build Timeline 2026-10-16 (Part 1)]]) |

## The pipeline, in one picture

```
 request / background job
        |
   tracing (JSON; request_id, user_id, client_id)         Sentry (errors + panics, scrubbed)
        |                                                        ^
   rotated file  ./logs/unitprep-api.DATE.log  (7 days)          | request_id links the two
        |
   Grafana Alloy (docker, "logs" profile)  -- labels: job, env, level
        |
   Grafana Cloud Loki  -->  Explore / Drilldown / dashboard / alerts
        |
   read by: logcli, Grafana MCP (read-only), Chrome, or just grep the files
```

## Numbers that can be quoted (and where they came from)

- About **50 ms** TCP round trip from the laptop to Neon in us-west-2; a signed-in request makes roughly **five** sequential database round trips (read from the code, not traced), matching warm medians of **276-400 ms**. Cold start after idle: **about 2.3 s** (one observation).
- Log volume: **146, 66, 15, 16** lines per day, 2026-10-16 to 10-19.
- On the build day: **14 API commits, 3 UI commits and 8 vault commits**, releases **api 1.9.129-1.9.131 and ui 1.6.99-1.6.100** (another session then shipped 1.9.132 and 1.6.101), across several sessions; the API range touched 28 files (about +3,540 / -50 lines).
- Tools: logcli 3.7.8, mcp-grafana 2.0.2 (checksum-verified), Alloy 1.10.0.

## Talking points (each is true and has evidence)

1. **"The logs told me my server was stale."** A 1 ms 500 meant a dead pooled connection; the file timestamps showed the binary predated the fix; a restart and a second live observation closed it. (Diagnosis from first principles with real data.)
2. **"I built logging so it moves to the cloud unchanged."** File in dev because the dev server is started through `docker compose exec` which Docker cannot capture; stdout in the cloud; labels low-cardinality; region next to the database. (Design for the migration without building it.)
3. **"I scaled it down on purpose."** Error emails moved to Sentry, Grafana email rules retired, no "no-logs" alert until there is a prod host that should always be logging. (Knowing when to stop.)
4. **"I shipped two dependent repos together after reviewing the code nobody had committed."** (Release judgement, review habit.)

## What must not be overclaimed

- **No production, no users beyond Boris, no real incidents.** The stack has been tested by deliberate and accidental dev events only.
- **The idle-500 root cause is a hypothesis** (a pooler answering a bare `Sync` ping); the fix is observed working, not proven against the original failure.
- **Built with an AI coding assistant.** The decisions were Boris's (no database for logs, JSON, local files, accept Neon's cold start, ship both halves, Sentry owns errors, no "no-logs" alert until live, scale-down of the Grafana emails); the assistant did the implementation, investigation and write-up. Say that plainly.
- Free-tier limits, the Fly.io details and the alert email rendering are **unverified**.
- Sentry's value is untested on a real error; the panic alert has never fired.

## If this were a real production system, what is missing

Retention and cost policy, log sampling, an on-call rotation and paging, runbooks per alert, SLOs and tuned thresholds (the 5xx and p95 thresholds are first guesses), a PII review of every field, backup of the dashboards beyond one JSON file, multi-environment separation tested for real, and a source-map pipeline for readable front-end stack traces. Listed so the demo shows awareness of the gap between a good start and an operated system.

## Related

[[Server Logging and Grafana - Index]] · [[Server Logging Design and Decisions]] · [[Findings - DB Connection Drops, Cold Starts and Latency]] · [[Grafana Cloud Setup and Objects]] · `perf/Brag Doc.md` (an entry for this can be added if Boris wants it; the quarterly structure there is still empty)
