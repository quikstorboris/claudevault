---
date: 2026-10-16
description: "Set up Sentry for UnitPrep (both repos, both projects, email alerts), then tied Sentry events to Grafana logs with request/user/client IDs, added an env label and a Tools dashboard. What shipped, what was verified, what was not."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Session 2026-10-16 (Part 2): Sentry setup, log correlation, tools dashboard

Open work lives in [[Observability Plan and Open Tasks (Sentry + Grafana)]]. Foundation: [[Session 2026-10-16 — Server Logging (JSON Files, Alloy, Grafana Cloud Loki)]]. New stack rows are in [[UnitPrep Tech Stack]].

## Part A: Sentry set up (api v1.9.130, ui v1.6.100, both pushed)

- The Sentry agent plugin installer found "no AI coding tools" (it does not detect the Claude desktop app) in WSL and on Windows, so projects were made by hand in the UI ("Set up manually") and then with the **Sentry CLI** (`~/.local/bin/sentry`, OAuth login).
- Projects: `orchestrator` (Rust, made in the UI) and `orchestrator-ui` (Next.js, made with the CLI). The UI project is named to match the existing one, not `unitprep-ui`.
- API: `sentry` crate (rustls; features `panic`, `tracing`, `tower`, `tower-http`), `src/startup/sentry.rs`, a tracing layer in `logging.rs`, tower layers in `api/router`. Off unless `SENTRY_DSN` is set. The panic integration gives stack traces, so the two `tracing` panic lines are dropped in `before_send` to avoid duplicates.
- UI: `@sentry/nextjs` 11, `instrumentation-client.ts`, `instrumentation.ts`, server and edge configs, both error boundaries call `captureException`, `lib/sentryOptions.ts` scrubber (masks `/invites/<token>`). Replay is off.
- Verified: an API test event arrived tagged `unitprep-api@1.9.129` / `development`; browser errors reach `orchestrator-ui` (envelopes returned 200, issue `ORCHESTRATOR-UI-3`). Boris's browser test looked "missing" only because of Sentry's feed filters.
- The 5 `npm audit` findings in the UI are the old `braces` chain, identical with and without Sentry (allowance review 2026-11-06).

## Part B: decisions (Boris)

- **Sentry owns errors and error emails; Grafana owns logs.** The old Grafana error and panic email rules are retired.
- Link the tools through `request_id`; add user and client info to logs as **IDs only, no names or PII**.
- Grafana alerts for 5xx rate and p95 latency: yes. "No logs" alert: **not until live**. Env label on logs: yes. A tools dashboard: yes.

## Part C: built (api v1.9.131, committed and tagged locally, **not pushed** at time of writing)

> Update 2026-10-19: v1.9.131 **is pushed** (tag on origin). Still pending as of that day: the Grafana dashboard re-import (the live dashboard still has 17 panels), pausing/deleting the two retired Grafana email rules, and a server restart (the server predates this release). See the status block in [[Observability Plan and Open Tasks (Sentry + Grafana)]].

- `src/api/router/request_context.rs`: `request_id`, `client_id`, `facility_id` from the URL path (strict UUID check, so route words like `search` never become IDs), plus a Sentry scope-tagging middleware inside the hub layer.
- `record_request_identity` in `src/auth/authenticated_user.rs`: `user_id` and `roles` onto the log span and Sentry scope when a session resolves. The Sentry scrubber keeps only `user.id`.
- Alloy `env` label from `LOG_ENV` (default `dev`; compose passes it); dashboard Environment picker (every query filtered by `env=~"$env"`) and a "Tools and people" section (11 panels).
- Sentry email rules (new or regressed; spike 10+ per hour) in both projects, created with `sentry alert issues create` (workflows 6182424-6182427).
- `docs/LOGS.md` updated: correlation recipes, env label, Grafana health-alert definitions, Sentry alert notes.
- API preflight green (all 10 steps, gitleaks included).

## Not verified (be honest)

- `user_id` / `roles` on a real signed-in request (logs and Sentry): the code is simple but there was no live check.
- The new dashboard queries against real data: the Loki read token returned "invalid token", so they are syntax-reviewed only. (Update 2026-10-19: that token worked in two later checks, so the answer was not reproducible; the queries are still unchecked against the live dashboard because it has not been re-imported.)
- The `request_id` tag on a live Sentry event.
- The Alloy config parses (`alloy fmt`) but the `LOG_ENV` path was not run end to end.

## Rejected / not done

- Creating the Grafana alert rules from the repo: the tokens are read-only, so they are written as recipes instead.
- A Sentry `request_id` tag from the browser: browser events have no API request id.
