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
| [[Routine Monitoring and Troubleshooting Playbook]] | **Read this to troubleshoot UnitPrep.** Claude can and should check Sentry and the logs itself: the order of lookup, known-benign patterns, what a real anomaly looks like, the twice-daily routine and its fix guardrails. |
| [[Routine Check Log]] | Append-only log written by the twice-daily routine (07:30 and 19:30 PT): status and findings per run. |

Outside this folder: [[Session 2026-10-16 (Part 2) — Sentry Setup, Log Correlation, Tools Dashboard]] and [[Observability Plan and Open Tasks (Sentry + Grafana)]] (the other session's record and the living open-task list, **that list is the one to update**); the cloud hub [[UnitPrep Fly.io and Deployment Notes]]; [[Production Readiness Checklist]]; [[Orchestrator Feature Backlog]] (alert email as an admin setting); [[Gotchas]] and [[Key Decisions]] (entries dated 2026-10-16); [[UnitPrep Tech Stack]] (rows for tracing-appender, Alloy, Grafana Cloud, logcli, mcp-grafana).

## State at ~16:30 PT, 2026-10-16

- `unitprep-api`: logging shipped in **1.9.129** (`v1.9.129`), Sentry in 1.9.130, log-correlation/env label/tools dashboard in 1.9.131; docs commit `3db7be1`. `unitprep-ui`: `v1.6.99` (company page editing), `v1.6.100` (Sentry). All pushed. All of Part 1's vault notes and Part 2's two notes are committed and pushed as of 2026-10-19 (see the vault log).
- Grafana: dashboard "UnitPrep API Logs" (uid `unitprep-api-logs`), alert rules "UnitPrep API errors" (`bg1fr6erxfthca`) and "UnitPrep API panic" (`fg1frrc3623gga`) **still exist and evaluate** (normal, ok at 16:19 PT) although Part 2 declared them retired in favour of Sentry; contact point `email-boris`.
- Read paths verified working at 16:19 PT: `scripts/logcli.sh` and the `grafana` MCP server.
- **Update 2026-10-19 08:17 PT**: pipeline still healthy (Loki holds 146/66/15/16 lines for Oct 16-19, newest 10:14:24Z); Sentry has five resolved Friday test issues and no unresolved ones; the local `unitprep-api`/`unitprep-ui` checkouts are **behind origin** (api by 3 commits, ui by 1: 1.9.132 and 1.6.101 were pushed Friday 16:35-16:40 PT by another session) and Boris's server runs the older code. See [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]].
- Boris's dev server needed a restart to pick up the pool fix, ClickUp logging and the 1.9.131 changes; whether he did after 1.9.131 is not recorded here.

## Standing practice since 2026-10-19 (Boris: a very significant improvement in how Claude and he troubleshoot)

- **Claude checks Sentry and the logs itself, before asking Boris for pasted output**, and routinely: `python3 scripts/anomaly_check.py` (in `unitprep-api`), the `./logs` files, `scripts/logcli.sh`, the Sentry CLI. Written into both repos' `CLAUDE.md` and the playbook.
- **Scheduled routine `unitprep-anomaly-check`**: every day at 07:30 and 19:30 PT, runs the check, logs to [[Routine Check Log]], investigates anything found and may prepare a fix on a separate worktree branch (local commit only, never pushed or merged). Only runs while the desktop app is open and the laptop awake.
- **The stack is frozen** (Boris: "no new starts ... until something comes up"): nothing new is added to observability unless a real problem calls for it.

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
- [x] Which background job fired every 4 hours from server start (the `:14:24` `before_acquire` warnings): confirmed 2026-10-21 from the code as the three vendor-registry refresh tasks (`vendor_format` x2, `vendor_file_meta`), which ticked together; removed the same day, see [[Latency Investigation 2026-10-20 - Round Trips vs Neon]]. These warnings should stop after the server restarts on the new build.
- [ ] Prove Sentry delivery from the running API with a real or deliberate error (none since the last restart).
- [ ] **Stale ClickUp panel query** in the repo's dashboard JSON (and the live dashboard): it still matches the old "ClickUp rate limiter full" text; since api 1.9.135 the message is `Rate limiter full` with a `limiter` field ([[Grafana Cloud Setup and Objects]]). Not fixed (frozen).
- [ ] **First routine runs** (first at 19:30 PT on 2026-10-19): check [[Routine Check Log]] for entries; confirm the task actually runs unattended and writes its log; review any `auto-fix/*` worktree under `~/Development/autofix/` before merging.
- [ ] Commit and push the repo-side pieces (`unitprep-api/scripts/anomaly_check.py` and the new `CLAUDE.md` sections in both repos) once Boris wants them on GitHub; the routine uses the script from the main checkout.
- [x] **Log-file retention is now a setting**, `LOG_RETENTION_DAYS` (default 7, 1-365), done 2026-10-22 at Boris's request after he asked why it was a constant; api commit `5a7b6eb`, local, **not pushed** ([[Server Logging Design and Decisions]]). The running server needs a restart to read it; set it under `api-dev` in `docker-compose.yml` for the container.
- [ ] Decide whether to add this stack to `perf/Brag Doc.md` ([[Observability Stack as a Demonstration of Skill]]).

## Things recorded here that are unverified (do not treat as fact)

Fly.io specifics (`fly-log-shipper`, ephemeral disks, `fly logs` buffer, which region is nearest Neon us-west-2); Grafana free-tier limits (retention 14 days and 50 GB/month were verified on 2026-10-22 from the pricing page; other limits were not); whether `alerting_manage_routing` is read-only under `--disable-write`; the exact five-round-trip count per request (read from code, not traced); the cause of the idle 500s (hypothesis: a pooler answers a bare `Sync` ping); whether the alert test email rendered as intended (Grafana confirmed it was sent, nobody looked at it); `grafanactl`/Terraform/Foundation SDK details.

## Related

`work/Index.md` (the work index) · [[Key Decisions]] · [[Gotchas]]
