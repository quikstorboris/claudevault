---
date: 2026-10-16
description: "Index and status of the server logging / Grafana workstream for unitprep-api (started 2026-10-16): what exists, where every detail is recorded, how to resume, open items and everything still unverified."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
  - index
---

# Server logging and Grafana: index

**What this is:** `unitprep-api` now writes structured JSON logs to rotated files, an Alloy container ships them to Grafana Cloud Loki, and there is a dashboard, alert rules, a CLI and an MCP server to read them. Built on 2026-10-16 in one long session ("Part 1"); Sentry and log correlation were added the same afternoon by another session ("Part 2"). This folder is the exhaustive record of Part 1.

## The notes

| Note | What is in it |
|---|---|
| [[Session 2026-10-16 — Server Logging (JSON Files, Alloy, Grafana Cloud Loki)]] | The short summary note written during the session (kept as the quick read). |
| [[Server Logging Design and Decisions]] | How it works, the JSON shape, every decision with its reason, alternatives rejected, forward-looking cloud constraints. |
| [[Grafana Cloud Setup and Objects]] | Account/stack/datasource ids, token inventory (no values), the dashboard and its 17 panels, alert rules, contact point, Grafana UI facts. |
| [[Reading Logs - Tools and Recipes]] | Every way to read logs; what was installed (logcli 3.7.8, mcp-grafana 2.0.2) and how it was verified; LogQL recipes. |
| [[Findings - DB Connection Drops, Cold Starts and Latency]] | Evidence: 500s after idle, the `SELECT 1` fix, the 2.3 s cold start, the ~50 ms round-trip arithmetic, per-route latency table. |
| [[Release 1.9.129 and 1.6.99 - Company Page Editing Review Record]] | The push of outstanding API commits, the dependent uncommitted front-end work, the backend review, commits/tags/pushes. |
| [[Build Timeline 2026-10-16 (Part 1)]] | Chronology of every step, approvals, blocks and slips. |
| [[Questions and Answers 2026-10-16 (Part 1)]] | Every question Boris asked and the substance of each answer. |
| [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]] | Monday check: the logs were in Grafana (stale view), why the weekend looked silent, the `before_acquire` warning explained, Sentry holds only test issues, origin has moved ahead of the local checkouts. |
| [[Sentry and Grafana Access for Claude]] | What Claude can reach and by which route (Sentry CLI works, no connectors in this session), Sentry token types from Sentry's docs, what was and was not tested. |
| [[Observability Stack as a Demonstration of Skill]] | The honest portfolio view: the scale check (overkill for one user), why it was still worth it, skills demonstrated with evidence, quotable numbers, what not to overclaim. |

Outside this folder: [[Session 2026-10-16 (Part 2) — Sentry Setup, Log Correlation, Tools Dashboard]] and [[Observability Plan and Open Tasks (Sentry + Grafana)]] (the other session's record and the living open-task list, **that list is the one to update**); the cloud hub [[UnitPrep Fly.io and Deployment Notes]]; [[Production Readiness Checklist]]; [[Orchestrator Feature Backlog]] (alert email as an admin setting); [[Gotchas]] and [[Key Decisions]] (entries dated 2026-10-16); [[UnitPrep Tech Stack]] (rows for tracing-appender, Alloy, Grafana Cloud, logcli, mcp-grafana).

## State at ~16:30 PT, 2026-10-16

- `unitprep-api`: logging shipped in **1.9.129** (`v1.9.129`), Sentry in 1.9.130, log-correlation/env label/tools dashboard in 1.9.131; docs commit `3db7be1`. `unitprep-ui`: `v1.6.99` (company page editing), `v1.6.100` (Sentry). All pushed. All of Part 1's vault notes and Part 2's two notes are committed and pushed as of 2026-10-19 (see the vault log).
- Grafana: dashboard "UnitPrep API Logs" (uid `unitprep-api-logs`), alert rules "UnitPrep API errors" (`bg1fr6erxfthca`) and "UnitPrep API panic" (`fg1frrc3623gga`) **still exist and evaluate** (normal, ok at 16:19 PT) although Part 2 declared them retired in favour of Sentry; contact point `email-boris`.
- Read paths verified working at 16:19 PT: `scripts/logcli.sh` and the `grafana` MCP server.
- **Update 2026-10-19 08:17 PT**: pipeline still healthy (Loki holds 146/66/15/16 lines for Oct 16-19, newest 10:14:24Z); Sentry has five resolved Friday test issues and no unresolved ones; the local `unitprep-api`/`unitprep-ui` checkouts are **behind origin** (api by 3 commits, ui by 1: 1.9.132 and 1.6.101 were pushed Friday 16:35-16:40 PT by another session) and Boris's server runs the older code. See [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]].
- Boris's dev server needed a restart to pick up the pool fix, ClickUp logging and the 1.9.131 changes; whether he did after 1.9.131 is not recorded here.

## How to resume

- Look at logs: files first (`unitprep-api/logs/*.log`), then `scripts/logcli.sh`, then the MCP server in a session started in `unitprep-api`, then Chrome ([[Reading Logs - Tools and Recipes]]).
- Re-run the shipper: `docker compose --env-file .env.local --profile dev --profile logs up -d`.
- Change the dashboard: edit `dev-tools/grafana/unitprep-api-logs.dashboard.json` and re-import (Import (Overwrite)), see [[Grafana Cloud Setup and Objects]] for the working method.
- Never paste a token into chat or the vault; names and scopes only.

## Open items (Part 1's view; the living list is in the Observability Plan note)

- [ ] **Re-import the dashboard** (Part 2's 1.9.131 version with the Environment picker and "Tools and people"): the live dashboard still has 17 panels as of 2026-10-19.
- [ ] **Pause or delete the two Grafana email rules** (Sentry now owns error emails), or decide to keep them; otherwise errors email twice.
- [ ] **Alert email as an admin setting** ([[Orchestrator Feature Backlog]], a 16:00 PT reminder fired 2026-10-16). Design question: the app cannot edit Grafana's contact point without a write token, so either the app does its own alerting or syncs through Grafana's API; a branded email needs the app to send mail itself.
- [ ] **Grafana trial ends 2026-10-30**; verify the permanent free-tier limits ([[Production Readiness Checklist]]).
- [ ] Watch the dashboard's "Database connection errors" panel after long idles to confirm the `SELECT 1` ping removed the 500s ([[Findings - DB Connection Drops, Cold Starts and Latency]]).
- [ ] The panic alert has **never been seen firing** (there have been no panics).
- [ ] Delete the read-scoped token that was pasted into chat (policy `stack-1878563-hl-read`), unless already done: never confirmed.
- [ ] The Part 2 note reported one "invalid token" answer from the Loki read token; re-tests passed; unexplained.
- [ ] Gaps in the shipped company-edit code (no real-staff DB test, PII in audit before/after, no field length limits): [[Release 1.9.129 and 1.6.99 - Company Page Editing Review Record]].
- [ ] At the cloud move: stdout JSON, `LOG_DIR` unset, `env=prod`, host region next to Neon us-west-2, decide keep-awake vs cold start ([[UnitPrep Fly.io and Deployment Notes]]).
- [ ] GitHub Actions results for the `v1.9.129` and `v1.6.99` tag runs were never looked at by Part 1.
- [ ] **Fast-forward `git pull` in `~/Development/unitprep-api` and `unitprep-ui`, then restart the server**, to bring it level with origin (1.9.132 / 1.6.101); not done because it changes files under a running server and was not asked.
- [ ] Confirm which background job fires every 4 hours from server start (it explains the `:14:24` `before_acquire` warnings); inferred from timestamps only.
- [ ] Prove Sentry delivery from the running API with a real or deliberate error (none since the last restart).
- [ ] Decide whether to add this stack to `perf/Brag Doc.md` ([[Observability Stack as a Demonstration of Skill]]).

## Things recorded here that are unverified (do not treat as fact)

Fly.io specifics (`fly-log-shipper`, ephemeral disks, `fly logs` buffer, which region is nearest Neon us-west-2); Grafana free-tier limits and retention; whether `alerting_manage_routing` is read-only under `--disable-write`; the exact five-round-trip count per request (read from code, not traced); the cause of the idle 500s (hypothesis: a pooler answers a bare `Sync` ping); whether the alert test email rendered as intended (Grafana confirmed it was sent, nobody looked at it); `grafanactl`/Terraform/Foundation SDK details.

## Related

`work/Index.md` (the work index) · [[Key Decisions]] · [[Gotchas]]
