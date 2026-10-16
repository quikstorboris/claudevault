---
date: 2026-10-16
description: "Hub for everything known or decided about hosting UnitPrep/Orchestrator in the cloud (Fly.io or otherwise): current state (no prod), standing design rules, what each deferred trigger is, and the logging/observability design. Add to this whenever Fly.io or deployment comes up."
tags: [reference, unitprep, deployment, fly-io]
status: active
---

# UnitPrep: Fly.io and Deployment Notes

**Purpose:** one place to land every fact, decision and open question about the eventual cloud deployment, so nothing lives only in scrollback. This is a hub: it links to the detailed entries rather than copying them. **Add to it any time Fly.io or deployment comes up.** The standing "deferred until the cloud move" list also lives in [[Production Readiness Checklist]].

## Where things stand (as of 2026-10-16)

- **There is no production deployment.** Nothing runs on Fly.io or any other cloud host. The API and UI run on Boris's laptop (WSL + Docker dev containers).
- **One user.** Boris is the solo developer, tester and user. Very few people know the tool exists yet.
- **It is connected to three other live systems** (per Boris), which is why auth was designed carefully (see [[Key Decisions#UnitPrep auth architecture (2026-07-20, final)|the auth decision]]) even though there is effectively one user.
- **Neon runs two environments.** Only **dev** is used day to day. The **prod** branch is brought level with dev occasionally by hand ([[UnitPrep Prod DB Sync Procedure]]) and is **not used by anything** until a real deployment exists.
- **Hosting is not committed.** Boris, 2026-10-16: "possibly but not necessarily fly.io." The earlier decision (below) named Fly.io the likely target; treat that as the working assumption, not a contract.

## Standing design rule (Boris, 2026-10-16, restating 2026-09-29)

**Architecture should be forward-looking and account for the eventual migration, without building for it yet.** Concretely:

1. Design for **multiple instances** from the start ([[Key Decisions#UnitPrep: Fly.io is the target backend host; design assumes multi-instance from now on (2026-09-29)|decision 2026-09-29]]).
2. Prefer **host-agnostic** choices (stdout logs, environment-variable config, no dependence on a local disk surviving) over Fly-specific ones. Where a Fly-specific option is clearly better, it is allowed, but note it here.
3. The dev setup may differ from prod where that is the pragmatic choice, but **the app code should not need to change** to move; only the surrounding config should.

## Already decided or recorded elsewhere

| Topic | Where |
|---|---|
| Fly.io named target; assume multiple machines; Redis becomes a planned (undated) dependency | [[Key Decisions]] (2026-09-29), [[Session 2026-09-29 — Docker Phases 2-3, cargo-chef Amendment & Fly.io Multi-Instance Decision]] |
| Production-shaped multi-stage image ("Docker phase 4"), execution trigger-gated | [[UnitPrep CI-CD Framework]], [[UnitPrep Docker Standards]] |
| ClickUp rate limiter, task cache and background-copy runner are per-process; needs a shared limiter (Redis) before more than one instance | [[Gotchas]] (top entries), [[ClickUp Copy — Design and Phase 1]] |
| Dedup tool-run history is ~1.9 MB per run with no retention policy; decide before metered storage | [[Gotchas]] (HIGH IMPORTANCE entry) |
| Re-run the load test (`concurrent_load_report`) on the chosen host; the 20-connection pool saturated at about 8 concurrent dedup operators with a 20 ms DB round trip | [[Efficiency Refactor - Concurrent Load Results]] |
| Neon compute must be able to auto-suspend; point health checks at `/health`, not `/health/db` | [[Efficiency Refactor - Idle Database Wake-ups (Neon Compute)]] |
| Durable sessions already use a `SessionStore` trait, so a Redis-backed store is additive | [[Key Decisions]] (2026-09-29) |
| Activity-log and other retention decisions deferred to go-live | [[Production Readiness Checklist]] |

## Logging and observability (added 2026-10-16)

Built in [[Session 2026-10-16 — Server Logging (JSON Files, Alloy, Grafana Cloud Loki)]]; the decision entry is in [[Key Decisions]].

**What exists today (dev):** the API writes human-readable text to the terminal and, when `LOG_DIR` is set, a second **JSON** copy in daily files (last 7 kept). A Grafana Alloy container tails those files and pushes them to **Grafana Cloud Loki**; they are searched in Grafana Explore. Every request already carries a `request_id`.

**What carries over to any cloud host unchanged**
- The JSON field layout, the `request_id`, and the `level` field.
- `LOG_FORMAT=json` makes stdout JSON, which is what a cloud platform collects.

**What is dev-only and must be redone for a cloud host**
- The `alloy` service and `dev-tools/alloy/config.alloy` live in `docker-compose.yml`; a cloud platform does not run that file.
- The `LOG_DIR` files. Fly.io machines (and most container hosts) have **ephemeral disks**, so the 7-day files would vanish on a deploy or restart. In the cloud: leave `LOG_DIR` unset and ship **stdout** instead.
- The Alloy config hardcodes `env = "dev"`, the Loki URL and the Loki user. Prod logs must be labeled `env=prod` so the two never mix.

**What the move needs (checklist)**
- [ ] Set `LOG_FORMAT=json`, leave `LOG_DIR` unset on the cloud host.
- [ ] Choose how stdout reaches Loki (see "Unverified" below).
- [ ] Grafana credentials as host secrets, never in a compose or config file.
- [ ] `env=prod` label; separate token or stack for prod if dev noise or cost matters.
- [ ] Decide log retention on the Grafana side (see the trial note below) instead of relying on files.
- [ ] Re-check log volume at `info` before committing to a tier.

> [!warning] Unverified: Fly.io specifics recalled from memory on 2026-10-16, not checked against current docs
> - Fly's usual route for forwarding logs elsewhere is a **separate small app, `fly-log-shipper`**, which has a Loki output. Confirm it still exists and how it is configured.
> - `fly logs` shows only a short recent buffer, so Grafana (or another sink) would be the real history.
> - Running Alloy as a second process in the same VM is an alternative to the shipper app.
> Verify all three when the move is actually being prepared.

**Grafana Cloud account facts (non-secret):** stack `joyfulpelican1551` (https://joyfulpelican1551.grafana.net), Loki push endpoint `https://logs-prod-021.grafana.net/loki/api/v1/push`, Loki user ID `1836339`. **The account is on a free trial that ends 2026-10-30.** What the permanent free tier keeps (retention, volume) was **not verified**; check the Plan details page before then. The write token lives only in `unitprep-api/.env.local` as `GRAFANA_API_KEY`.

## Open questions to settle when the move is real

- Is the host really Fly.io? (Boris 2026-10-16: maybe not.) If not, which notes above change: the `fly-log-shipper` route, any Fly-specific machine/volume assumptions.
- One Grafana stack for dev and prod, or two?
- Does anything in the UI or API need to know it is behind a proxy (cookie `Secure`, `X-Forwarded-*`, WebAuthn origin)? Not examined yet.
- Secrets: how `.env.local` values map to host secrets, and which of them must differ between dev and prod.

## Latency is round-trip bound: put the API next to the database (measured 2026-10-16)

From Boris's laptop (WSL) to the Neon dev endpoint (`...-pooler.us-west-2.aws.neon.tech`, Oregon), a TCP connect takes about **50 ms**. A warm authenticated request makes roughly five sequential database round trips (session lookup, `BEGIN`, set the RLS claims, the data query, `COMMIT`), which matches the measured warm times: `/clients` median 288 ms, `/clients/filter-options` 400 ms, `/health/whoami` 276 ms, a trivial `/health/db` 318 ms (Loki, last 3 h). So the latency is mostly distance, not slow queries. **When the API is hosted in or near us-west-2, the same five round trips should cost a few milliseconds each**, an order of magnitude less. Consequences: do not spend effort shaving round trips now; **choose the host region next to the Neon region** (verify which Fly.io region is closest to us-west-2 at that time; not checked). Cold start after Neon auto-suspend adds about 1.5 to 2.5 s to the first request after idle and discards dead pooled connections one at a time; Boris decided on 2026-10-16 to **accept that** in dev (scale-to-zero is deliberate, see [[Efficiency Refactor - Idle Database Wake-ups (Neon Compute)]]). Revisit keep-awake (or a shorter pool `idle_timeout`) when going live. Evidence in [[Session 2026-10-16 — Server Logging (JSON Files, Alloy, Grafana Cloud Loki)]].

## Related

[[Production Readiness Checklist]] · [[UnitPrep CI-CD Framework]] · [[UnitPrep Docker Standards]] · [[UnitPrep Tech Stack]] · [[UnitPrep Prod DB Sync Procedure]]
