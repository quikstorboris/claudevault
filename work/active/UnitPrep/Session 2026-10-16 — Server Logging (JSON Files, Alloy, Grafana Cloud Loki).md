---
date: 2026-10-16
description: "Added stored server logs to unitprep-api: JSON files rotated daily (7 kept), shipped by Grafana Alloy to Grafana Cloud Loki, verified end to end. Records what was decided, rejected, and what must change for a cloud host."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Session 2026-10-16: Server Logging (JSON Files, Alloy, Grafana Cloud Loki)

## Context

Boris asked whether the Rust server's logs are stored, and if not whether a rolling week could be. **Before this session: not stored anywhere.** `src/startup/logging.rs` installed a plain `tracing_subscriber::fmt()` writing to stdout/stderr, default filter `unitprep=info,sqlx=warn`; output vanished when the terminal closed or the container was recreated. The durable records that did exist were business events (`auth.auth_audit_logs`, the activity log, tool-run history), not server diagnostics.

This became the first piece of the observability design; the cloud-move implications are collected in [[UnitPrep Fly.io and Deployment Notes]].

## What was built (`unitprep-api`, commit `c840470`, local, **not pushed**, no version bump, still 1.9.128)

- `src/startup/logging.rs`: two independent outputs under one `RUST_LOG`-style filter.
  - stdout: human-readable text by default; `LOG_FORMAT=json` switches it to JSON (for a platform that collects stdout).
  - `LOG_DIR` set: a second **JSON** layer writing `unitprep-api.YYYY-MM-DD.log`, **daily rotation, last 7 files kept** by the appender itself (`tracing-appender` `max_log_files`), no cron. The writer guard is parked in a `OnceLock` so `init()`'s signature did not change.
- `Cargo.toml`: `tracing-subscriber` gained the `json` feature; new dependency `tracing-appender = "0.2"` (lockfile also pulled `crossbeam-channel`, `symlink`, `tracing-serde`, and bumped one existing `getrandom` from 0.3.4 to 0.4.3 as a resolver side effect).
- `docker-compose.yml`: `api-dev` sets `LOG_DIR=/app/logs` (the bind-mounted checkout, so files appear in `./logs`, now gitignored); a new **`alloy`** service in its own **`logs`** profile (image `grafana/alloy:v1.10.0`).
- `dev-tools/alloy/config.alloy`: tails `/logs/unitprep-api.*.log`, promotes only `level` to a Loki label (everything else, including `request_id`, stays in the JSON line and is queried with `| json`), pushes to Grafana Cloud Loki.
- Run it: `docker compose --env-file .env.local --profile dev --profile logs up -d`. **`--env-file`, interpolation, never `env_file:`**, so only `GRAFANA_API_KEY` reaches the Alloy container and not every secret in `.env.local` (the Neon URLs must never be near this file).

**Request IDs already existed** (`TraceLayer` span in `src/api/router/mod.rs` carries `request_id`, `method`, `path`); no work was needed there.

## Decisions

- **Not in the database.** Boris agreed. Reasons given: high volume and low value per line would bloat Neon and its backups, and logging would depend on the DB being up, which is exactly when the DB is what is broken. The business-level record already lives in the audit tables.
- **JSON format.** Boris's call.
- **Local files are fine on a schedule; Docker-level size/retention limits are also fine** (Boris). In practice the files carry the retention in dev.
- **Why files and not Docker's own log capture:** the dev server is started with `docker compose exec api-dev cargo run`, an exec'd process whose output **Docker's log capture never sees**. The container's main process is the `cargo watch` test loop. That is why logs go to a bind-mounted file for Alloy to read. See [[Gotchas]].
- **Grafana Cloud Loki** (hosted) chosen as the place to search them. Boris is not worried about personal information in the logs; if it ever matters, redact by recognizing names (best effort, name recognition misses things).
- **Near real-time:** Alloy follows the file like `tail -f`. Observed in the test: file timestamp 12:06:58.757, shown in Grafana 12:06:58.850, so under a second here.

## Considered and not built (recorded so they are not re-derived)

- **An admin log viewer inside the app.** Reasonable later. Boris pointed out that if it is a page where you pick a JSON file from disk and the browser parses it, the server never touches the file and **no server-side permission is needed**. Permissions only matter if the API reads its own log directory and serves it over HTTP. Deferred; Grafana Explore covers the need for now.
- **AI-assisted log analysis ("recommend a solution") inside the app.** Not built. Logs show symptoms, not causes; advice is weak without the code and schema. Better first step used here: point Claude Code at the log directory when something breaks. If ever built: pre-aggregate rather than send raw lines, and handle the PII-to-a-third-party question deliberately.
- **Docker log-driver limits as the retention mechanism.** Size-based, not time-based, and does not see exec'd processes. Not used.

## Verified

- `cargo check` and `cargo clippy --all-targets -D warnings` clean.
- Ran a test copy of the server on **port 8081** (port 8080 was held by Boris's own running server, deliberately left alone; it is an older build without this change): JSON file created, four lines written including `/health` 200 and `/nope` 404 with `request_id`.
- Alloy started, followed the file with no push errors; the four lines appeared in Grafana Explore (`{job="unitprep-api"} | json`) with full fields. This also proved the token in `.env.local` is a **write**-capable token.

## Things that went sideways or are worth knowing

- **A read-scoped token was pasted into chat first** (an autogenerated `stack-1878563-hl-read` policy: logs/metrics/traces **read**, useless for shipping). Replaced by a write-scoped policy with its token saved to `.env.local` as `GRAFANA_API_KEY`. Whether the old read policy/token was deleted was **not confirmed**. Boris's stated stance at the time: "I don't care about token security at this point." Worth deleting it anyway. Lesson reinforced: the secret should go from the Grafana screen straight into `.env.local`, never through chat.
- **`.env.local` already had a line `GRAFANA_API_KEY`** (line 111) before the new token was added; the variable name I had suggested (`GRAFANA_LOKI_TOKEN`) was not what Boris used. Config uses `GRAFANA_API_KEY`.
- **Grafana shows the level label as `level_extracted`**, because Loki already has a `level` of its own. Cosmetic: `{job="unitprep-api"} | json | level="ERROR"` works.
- **WSL transiently failed once** (`Wsl/Service/0x8007274c`, a connection timeout); an immediate retry worked. Not a repo problem.
- The repo already had **uncommitted edits from other work** (`src/api/*`, `client_ops/audit_log.rs`); only the logging files were committed.
- **Alloy was left running** after the test; its container and volume persist until `docker compose --profile logs down`.

## Not done

- **Not pushed, not version-bumped/tagged.**
- **Grafana trial ends 2026-10-30**; permanent free-tier limits unverified. Check the Plan details page.
- **The prod/cloud path is not built or tested** (and no prod exists). See [[UnitPrep Fly.io and Deployment Notes]] for the checklist.
- Boris's running dev server on 8080 needs a restart to pick up the change (api-dev sets `LOG_DIR` automatically on container recreate).

## Later the same day: dashboard, panic alert, and a real DB-connection finding

**Built in Grafana (account `quikstorboris`, stack `joyfulpelican1551`):**
- Dashboard **"UnitPrep API Logs"** (uid `unitprep-api-logs`): errors and panics (stat), log lines by level, requests by status code, max request latency, and an errors/warnings log panel. Source of truth is `unitprep-api/dev-tools/grafana/unitprep-api-logs.dashboard.json` (uncommitted at the time of writing) so it can be re-imported for prod.
- Contact point **`email-boris`** (email, bmaksimov@quikstor.com, "for today" per Boris) and alert rule **"UnitPrep API panic"** (`sum(count_over_time({job="unitprep-api"} |= "panicked" [5m]))` above 0, every 1 minute, pending 0s, no-data = OK, folder GrafanaCloud, group `unitprep-api`). The Grafana default notification policy still routes to an empty contact point; this rule routes directly to `email-boris`.
- **Only panics alert.** A handled `ERROR` (like the DB errors below) does not. An ERROR-level alert is recommended but not created. Boris wants the recipient to become an admin setting, see [[Orchestrator Feature Backlog]]; reminder scheduled for 2026-10-16 16:00 PT.

**Real finding (a handled error, not a panic):** after the dev server sat idle about 10 minutes, the first four DB-touching requests all failed with `error communicating with database: expected to read 5 bytes, got 0 bytes at EOF` (login `POST /auth/login/begin` twice, `GET /health/whoami` twice), each returning 500 in about 1 ms. 1 ms means a pooled connection that was already dead was handed out. Four minutes later `/health/db` probes succeeded and the logs show `error from before_acquire` warnings: the idle-gated ping (`PING_IDLE_THRESHOLD`, 30 s, `src/db.rs`) **does** catch and replace dead connections, one per request. So the pool self-heals, but the first requests after a long idle can hit dead connections the ping did not catch. **Unverified hypothesis:** Neon (compute auto-suspend, see [[Efficiency Refactor - Idle Database Wake-ups (Neon Compute)]]) and its pooler drop idle connections, and the comment-only ping sqlx sends does not always reveal that through the pooler. Candidate fixes, none applied: ping with a real `SELECT 1`, an `idle_timeout` below Neon's suspend window, or one automatic retry on a connection-closed error. Needs a reproduction (idle more than 6 minutes, then probe). The log file and Grafana made this diagnosable in minutes, which is the logging work paying off.

**Added afterward (same day):**
- Second alert rule **"UnitPrep API errors"**: any `level="ERROR"` line in the last 5 minutes (`sum(count_over_time({job="unitprep-api", level="ERROR"}[5m]))` above 0), same group, no-data = OK, routed to `email-boris`. Created at Boris's request after the DB-connection errors showed a handled `ERROR` does not trip the panic alert. Expect noise at first; tune after a week.
- Dashboard extended to 15 panels (`dev-tools/grafana/unitprep-api-logs.dashboard.json`, version 2): **per-route latency** (slowest routes by average ms; p95 by route; 5xx by route; ids in paths are collapsed with a `label_format` regex so `/clients/<uuid>` is one route), **database connection errors**, **Process Street** calls by status and 429-waits/failures, **Dropbox** successes/errors, **errors and warnings by module** (the `target` field), and **slow SQL** (sqlx WARN). The Process Street and Dropbox panels were empty at import because neither had run since logging began; their queries match the messages in `src/process_street/client.rs` and `src/dropbox/client/*`.
- **Gap found: ClickUp logs nothing.** `src/clickup/*` has no `tracing` calls at all, so ClickUp rate-limit hits, failures and copy-job progress are invisible in Grafana (see [[Gotchas]] for the multi-instance rate-limit issue). Worth adding log lines on 429s, failures and copy-job start/finish. Not done.
- Auth only logs `ERROR`s (failed ceremonies, session lookup failures); failed-login *attempts* are audit-table rows in the DB, not log lines, so they are not in Grafana.

**Tooling to read logs without the browser (installed same day, after Boris asked whether Grafana has a CLI/SDK):**
- `logcli` 3.7.8 and `mcp-grafana` 2.0.2 installed to `~/.local/bin` in WSL (GitHub release assets, SHA256 verified). Wrapper scripts `scripts/logcli.sh` and `scripts/grafana-mcp.sh` extract just one key from `.env.local` (never `source` it), docs in `unitprep-api/docs/LOGS.md`. The MCP server is registered as `grafana` in the repo-local `.mcp.json`, runs `--disable-write`, with only the search/datasource/loki/alerting/dashboard/folder/navigation tool groups, usage statistics off. Verified: the MCP server accepts `GRAFANA_URL` + `GRAFANA_SERVICE_ACCOUNT_TOKEN` (a fake token got a 401 from the stack, correct).
- **Verified working (2026-10-16, after Boris added both tokens):** `scripts/logcli.sh` returned the real 13:27 ERROR/WARN lines from Loki; the MCP server (driven over stdio) listed 20 read-only tools, no write tools, `list_datasources` returned the stack's datasources and `query_loki_logs` returned real ERROR lines. The MCP server is only available to Claude Code sessions started in `unitprep-api` (project-scoped `.mcp.json`), after approving it. Tokens used: `GRAFANA_LOGS_READ_TOKEN` (access policy, `logs:read` only) for `logcli`, and `GRAFANA_SERVICE_ACCOUNT_TOKEN` (stack service account, Viewer) for the MCP server. (Original note: `GRAFANA_LOGS_READ_TOKEN` (access policy, `logs:read` only) for `logcli`, and `GRAFANA_SERVICE_ACCOUNT_TOKEN` (stack service account, Viewer) for the MCP server. Steps are in `docs/LOGS.md`.) Claude Code also asks for approval the first time a session starts with the new project MCP server.
- Slip worth knowing: editing `grafana-mcp.sh` through the `\wsl.localhost` path stripped its executable bit again (see [[Gotchas]]); a first edit also dropped a line-continuation backslash that `bash -n` did not catch.

## Related

[[UnitPrep Fly.io and Deployment Notes]] · [[Production Readiness Checklist]] · [[UnitPrep Docker Standards]] · [[UnitPrep Tech Stack]] · [[Key Decisions]] · [[Gotchas]]
