---
date: 2026-10-16
description: "Living plan for UnitPrep/Orchestrator observability: what Sentry and Grafana each own, what is built, and every open task that must not be forgotten. Update the checkboxes as items land."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Observability plan and open tasks (Sentry + Grafana)

Decided 2026-10-16 with Boris. Built in [[Session 2026-10-16 (Part 2) — Sentry Setup, Log Correlation, Tools Dashboard]]; logging foundation in [[Session 2026-10-16 — Server Logging (JSON Files, Alloy, Grafana Cloud Loki)]].

## Who owns what

- **Sentry = errors and the emails about them.** Exceptions, panics, regressions, error spikes. Org `quikstor-wf`; projects `orchestrator` (Rust API) and `orchestrator-ui` (Next.js). Emails go to Boris.
- **Grafana = logs and log-derived health.** Searching logs, dashboards, 5xx rate, p95 latency. Not error emails (the old Grafana error and panic rules are retired).
- **Link between them:** `request_id` is on every log line and every Sentry event; `client_id`, `facility_id`, `user_id`, `roles` too. IDs only, never names, emails or phones. Recipes in `unitprep-api/docs/LOGS.md`.

## Built (api v1.9.130 + v1.9.131, ui v1.6.100)

- [x] Sentry SDK in both repos, off unless the DSN env var is set; PII scrubbed (`send_default_pii` off, bodies/cookies/query strings/credential headers stripped, invite tokens masked in the UI, only the user ID kept)
- [x] Sentry projects `orchestrator` and `orchestrator-ui`; Sentry email rules in both: new or regressed issue, and error spike (10+ events in 1 hour), created with the Sentry CLI (workflow rule ids 6182424-6182427)
- [x] Request/user/client/facility IDs on logs and Sentry events (v1.9.131)
- [x] Grafana `env` label (`LOG_ENV`, default `dev`) and an Environment picker on the dashboard
- [x] Dashboard "Tools and people" section
- [x] Grafana 5xx-rate and p95-latency alert definitions written into `docs/LOGS.md`

## Open tasks (nothing here is done yet)

> **Status check 2026-10-19 (Monday ~08:45 PT), added from [[Server Logging and Grafana - Index]]; live state read through the Grafana MCP server, git and the logs:**
> - **Push v1.9.131: done** (tag `v1.9.131` is on origin). Origin is further ahead: api 1.9.132 and ui 1.6.101 were pushed Friday 16:35-16:40 PT by the efficiency-refactor session.
> - **Re-import the dashboard: still pending.** The live dashboard has **17 panels** (the earlier version, without the Environment picker and "Tools and people" section).
> - **Retired Grafana rules: still pending.** Both "UnitPrep API errors" and "UnitPrep API panic" exist and evaluate (state normal, health ok); errors would still email twice once an error happens.
> - **Restart: still pending, and now two steps.** Boris's server last started 2026-10-16T22:14:24Z (15:14 PT), **before** the 1.9.131 commit (15:46:51 PT), and the local checkouts are behind origin (api by 3 commits, ui by 1): `git pull --ff-only` in both repos, then restart.
> - The "invalid token" answer from the Loki read token was **not reproducible**: `logcli` and the MCP server worked on 2026-10-16 16:19 PT and again on 2026-10-19.
> - Sentry check on 2026-10-19: no unresolved issues; five resolved issues, all Friday's test events; zero ERROR log lines since Sentry went live. Note `sentry issue list` shows unresolved only by default. See [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]].


### Needs Boris, soon
- [x] **Push v1.9.131** (committed and tagged locally as `3615590` / `v1.9.131`; pushed since, verified 2026-10-19)
- [ ] **Re-import the dashboard** in Grafana from `dev-tools/grafana/unitprep-api-logs.dashboard.json` (new Environment picker and Tools section). The new panel queries could not be checked against Loki: `GRAFANA_LOGS_READ_TOKEN` in `.env.local` answered "invalid token". Replace the token (Grafana portal > Access Policies, logs:Read) and eyeball every new panel once.
- [ ] **Pause or delete the two retired Grafana rules** ("UnitPrep API errors", "UnitPrep API panic") so errors do not email twice
- [ ] **Create the two Grafana health alerts by hand** ("UnitPrep API 5xx rate" above 5 per 5 min, "UnitPrep API p95 latency" above 2000 ms). Exact queries are in `docs/LOGS.md`, section "Health alerts to create in Grafana". They cannot be created from the repo (read-only tokens).
- [ ] **Restart the dev API and UI** servers to pick up v1.9.131
- [ ] **Grafana trial ends 2026-10-30**: check the permanent free-tier retention and volume limits (also in [[Production Readiness Checklist]])

### Verify when convenient
- [ ] `user_id` / `roles` on a real authenticated request's log line and Sentry event were built but **not checked live** (only `client_id`/`facility_id` on logs were). After restarting, make one signed-in request and look for `span_user_id` in Grafana and a `user.id` plus `roles` tag on a Sentry event.
- [ ] `request_id` tag on a real Sentry event from the API: not yet seen live.
- [ ] The UI browser SDK is verified (envelopes returned 200); a server-side UI error is not.

### When a prod host exists
- [ ] Restrict both Sentry email rules to `environment:production` (they fire for dev now): `sentry alert issues edit quikstor-wf/<project>/<rule-id> --environment production`
- [ ] Set `SENTRY_ENVIRONMENT=production` (API) and `NEXT_PUBLIC_SENTRY_ENVIRONMENT=production` (UI); set `LOG_ENV=prod` on the log shipper
- [ ] Add the **"no logs at all" Grafana alert** (Boris said: not until live). An idle dev server would fire it constantly.
- [ ] Source-map upload for the UI: set `SENTRY_AUTH_TOKEN` at build time (internal integration with Release:Admin, Project:Read), so UI stack traces are readable
- [ ] Connect the GitHub integration in Sentry for suspect commits and "resolved in next release"
- [ ] Performance tracing: set `SENTRY_TRACES_SAMPLE_RATE` / `NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE` around 0.1 (default is off)
- [ ] Re-tune the 5xx and p95 thresholds against real traffic (first guesses; dev is a debug build, so slower)
- [ ] The Sentry CLI login expires **2026-11-15** (auto-refresh is on; check it worked)

### Ideas not yet decided
- [ ] Report failed UI fetches to Sentry with method, URL and status (the generic "could not reach the server" message hid the CORS DELETE bug)
- [ ] Sentry cron monitors for the background refresh tasks (`startup::tasks`)
- [ ] Uptime check on `/health`; Prometheus-style metrics for request rate and latency (relevant at the cloud move)
- [ ] Fingerprint outbound-integration errors per integration (ClickUp, Process Street, Dropbox, Elavon) and record ClickUp 429s as breadcrumbs, not errors
- [ ] A `tool` tag/label (dedup, tagger, unit groups) on Sentry events; the dashboard already groups by first URL segment
- [ ] Sentry server-side data scrubbing (Security & Privacy settings) as a second layer behind the SDK scrubber

## Gotchas learned (also worth `brain/Gotchas.md`)

- `@sentry/nextjs` v11 does not export `withSentryConfig` from the package root: import it from `@sentry/nextjs/config`.
- The Rust `sentry` 0.49 `ClientOptions` is `#[non_exhaustive]`: build it with the builder methods (`.dsn()`, `.release()`, `.before_send()`), not a struct literal.
- Sentry's issue-alert REST path (`projects/<org>/<project>/rules/`) returns 404 now; alerts are "workflows". Use `sentry alert issues create` (conditions like `first_seen_event`, `regression_event`, `event_frequency_count`). `sentry alert issues view` and `list` show 0 conditions for them (a CLI display quirk); `sentry api organizations/<org>/workflows/` shows the truth.
- `sentry api ... --silent` swallows the 404 body: do not use it when checking a call worked.
- Reaching the repos through `wsl.exe -d Ubuntu -- bash -c '...'` from Git Bash mangles `$VAR` and `$(...)`; pipe a heredoc into `wsl.exe -d Ubuntu -- bash -s` instead.
- A fresh Sentry issues feed can look empty: the project, environment, time range and search filters hide new issues. The issue was in Sentry the whole time.
