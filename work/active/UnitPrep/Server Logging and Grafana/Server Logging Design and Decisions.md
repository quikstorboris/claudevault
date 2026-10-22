---
date: 2026-10-16
description: "How unitprep-api's stored server logging works (JSON files, daily rotation, Alloy shipper to Grafana Cloud Loki), every design decision with its reason, and every alternative considered and rejected."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Server logging: design and decisions

Part of [[Server Logging and Grafana - Index]]. Build order and commits are in [[Build Timeline 2026-10-16 (Part 1)]]; the Grafana side is in [[Grafana Cloud Setup and Objects]].

## Starting point (before 2026-10-16)

- `src/startup/logging.rs` installed a plain `tracing_subscriber::fmt()` writing human-readable text to stdout/stderr, filter `unitprep=info,sqlx=warn` unless `RUST_LOG` is set.
- A wrapping panic hook also logs `tracing::error!(panic = %panic_info, "panicked")`, so panics reach the same stream.
- **Nothing was stored.** Output went to the terminal that launched the server (or `docker compose logs` for a container's main process) and vanished on close or recreate.
- The durable records that did exist were business events, not diagnostics: `auth.auth_audit_logs`, the Activity Logs (`client_ops.audit_log`) and the tool-run history.
- **Request IDs already existed**: a `TraceLayer` span in `src/api/router/mod.rs` (`make_span_with`) carries `method`, `path` and `request_id` (assigned by `SetRequestIdLayer`, echoed by `PropagateRequestIdLayer` as `x-request-id`). Nothing was added for this.

## What was built (api commit `c840470`, released in 1.9.129)

### The application side (`src/startup/logging.rs`)
- Two independent output layers under the same filter (the filter closure builds a fresh `EnvFilter` per layer):
  - **stdout**: human-readable text by default. `LOG_FORMAT=json` (case-insensitive) switches it to JSON, for a platform that collects stdout.
  - **file**: when `LOG_DIR` is set and non-empty, a JSON layer writes to daily-rotated files named `unitprep-api.YYYY-MM-DD.log` via `tracing_appender::rolling::Builder` (`Rotation::DAILY`, prefix `unitprep-api`, suffix `log`, `max_log_files(7)`), wrapped in `tracing_appender::non_blocking`. ANSI colours are off in the file.
  - If the appender cannot be built (bad directory), it prints one line to stderr (`LOG_DIR=<dir> unusable (...); file logging disabled`) and carries on with stdout only. The subscriber is not installed yet at that point, so plain `eprintln!`.
- The non-blocking writer's `WorkerGuard` must outlive the process or buffered lines are lost, so it is parked in a `static FILE_GUARD: OnceLock<WorkerGuard>`; `init()`'s signature and its single call site (`src/startup/mod.rs`) did not change.
- `Cargo.toml`: `tracing-subscriber` gained the `json` feature; new dependency `tracing-appender = "0.2"` (resolved 0.2.5; lockfile also added `crossbeam-channel`, `symlink`, `tracing-serde`, and bumped one existing `getrandom` from 0.3.4 to 0.4.3 as a resolver side effect).
- `cargo check` took 24 s; `cargo clippy --all-targets -D warnings` clean.

### The JSON line shape
One object per line, for example a request-completed event:
`{"timestamp":"...Z","level":"INFO","fields":{"message":"request completed","request_id":"...","status":200,"latency_ms":"0"},"target":"unitprep::api::router","span":{"method":"GET","path":"/health","request_id":"...","name":"http_request"},"spans":[{...}]}`
- Event fields are nested under `fields` (`message`, `status`, `latency_ms` as a string, `error`, `panic`, ...), the innermost span under `span`, the stack under `spans`. In LogQL after `| json` these flatten to `fields_message`, `fields_status`, `span_path`, `span_method`, `span_request_id`, `target`, and so on.
- Warning: `latency_ms` is logged as a string, but LogQL `unwrap` still works on it.

### The shipper (`docker-compose.yml`, `dev-tools/alloy/config.alloy`)
- `api-dev` sets `LOG_DIR=/app/logs`. `/app` is the bind-mounted checkout, so files appear in `./logs` on the host. `./logs` was created `chmod 777` (the container runs as root and its files would otherwise lock the host user out of writing), and `/logs/` was added to `.gitignore`.
- New `alloy` service, profile `logs` (a plain `--profile dev` is unchanged), image pinned `grafana/alloy:v1.10.0`, command `run --storage.path=/var/lib/alloy/data --server.http.listen-addr=127.0.0.1:12345 /etc/alloy/config.alloy`, config mounted read-only, `./logs` mounted read-only at `/logs`, named volume `alloy-data` for file read positions (a restart does not re-send everything).
- Config: `local.file_match` on `/logs/unitprep-api.*.log` with static labels `job=unitprep-api` and `env=dev` (later `env` from `LOG_ENV`, see [[Session 2026-10-16 (Part 2) — Sentry Setup, Log Correlation, Tools Dashboard]]); `loki.source.file`; `loki.process` with `stage.json` (extract `level`) and `stage.labels` (promote **only `level`**); `loki.write` to `https://logs-prod-021.grafana.net/loki/api/v1/push` with basic auth, username `1836339`, password from `sys.env("GRAFANA_API_KEY")`.
- **Labels are deliberately few** (job, env, level, plus Loki's own filename/service_name). `request_id`, paths, user IDs and messages stay in the line and are queried with `| json`: promoting them to labels would explode Loki's index (cardinality). Side effect: because `level` is a real stream label, `| json` exposes the JSON `level` field as `level_extracted`. Cosmetic.
- **Credentials**: `GRAFANA_API_KEY` arrives only through compose interpolation with `docker compose --env-file .env.local ...`, never `env_file:`, which would copy every secret in `.env.local` (including the Neon URLs, which compose files here must never touch) into the container.
- The first version used `${GRAFANA_API_KEY:?run with --env-file .env.local}`. **That was a bug**: Compose interpolates the whole file for every command whatever the profile, so every `docker compose exec`/`up` without `--env-file` failed. Fixed in `6b2cb6d` with the optional `${GRAFANA_API_KEY:-}` (alloy started without the key gets 401s from Loki, visible in `docker compose logs alloy`). See [[Gotchas]].

### Run it
`docker compose --env-file .env.local --profile dev --profile logs up -d`. A running server only picks up code or logging changes after a restart (`cargo run` does not reload).

## Decisions and the reasons Boris and Claude gave

| Decision | Reason |
|---|---|
| **Not in the database** (Boris agreed) | High volume, low value per line would bloat Neon and its backups; logging would depend on the DB being up exactly when the DB is what is broken. The business-level record already lives in the audit tables. |
| **JSON format** (Boris's call) | Makes a week of logs queryable by field after the fact. |
| **Local files, rotated, last 7 days; Docker size limits also fine** (Boris) | Simple retention with no cron job (the appender prunes by file count). |
| **Files, not Docker log capture** | The dev server is started with `docker compose exec api-dev cargo run`, an exec'd process whose output Docker's log capture never sees. The container's main process is the `cargo watch` test loop (Dockerfile.dev `CMD`). |
| **Grafana Cloud Loki to search them** | Hosted, free trial, no infrastructure; Boris was not worried about personal data in logs (redaction by recognising names was the fallback, best effort only). |
| **Near real-time** | Alloy follows the file like `tail -f`; measured file timestamp 12:06:58.757 vs Grafana 12:06:58.850, under a second end to end. |
| **stdout stays human-readable by default** | Dev terminal stays readable; `LOG_FORMAT=json` for platforms that collect stdout. |
| **Request IDs: nothing to add** | They already existed. |

## Considered and not built (so they are not re-derived)

- **An admin log viewer inside the app.** Reasonable later. Boris's point: if it is a page where you pick a JSON file from disk and the **browser** parses it, the server never touches the file and **no server-side permission is needed**; permissions only matter if the API reads its own log directory and serves it over HTTP (then it needs a gate, probably admin-only, and viewing should itself be audited). Deferred; Grafana Explore covers the need.
- **AI-assisted log analysis ("recommend a solution") inside the app.** Not built. Logs show symptoms, not causes; advice is generic without the code and schema. Better first step, used here: point Claude Code at the log directory when something breaks (now also `logcli` and the Grafana MCP server, see [[Reading Logs - Tools and Recipes]]). If ever built: pre-aggregate rather than send raw lines to an LLM, and handle the PII-to-a-third-party question deliberately.
- **Docker log-driver size limits as the retention mechanism.** Size-based, not time-based, and blind to exec'd processes.
- **Storing only WARN/ERROR in a small capped DB table** (so an in-app page could show them): offered as a later add-on, not chosen.
- **Self-hosted Grafana/Loki locally**: not chosen (Grafana Cloud free trial). Local models were also ruled out by the standing no-local-model-servers rule.

## Retention: where each kind of log is set (asked 2026-10-22)

| Log | Retention | Where it is set |
|---|---|---|
| Server log files `./logs/*.log` | last **7 daily files** by default | **`LOG_RETENTION_DAYS`** (environment variable read at startup; whole number 1-365; anything else prints one stderr warning and keeps 7), passed to the appender's `max_log_files`. Since 2026-10-22 (api commit `5a7b6eb`); before that a hardcoded constant. Counts files, not calendar days: a day with no writes creates no file, so the files kept can span more than that many days; pruning happens when a new daily file is created; a restart is needed to change it. |
| Grafana Cloud Loki | **14 days** on the Free plan (50 GB/month ingest), 30 days on Pro, custom on Enterprise | The Grafana plan. Nothing in the repo; the portal's Loki details page shows no retention figure ([[Grafana Cloud Setup and Objects]]). |
| Sentry | plan-based (about 30 days on the free tier, **unverified**) | The Sentry plan. |
| Database audit/activity logs and tool-run history | indefinite by design (`auth.auth_audit_logs` cannot be deleted: a trigger blocks updates and deletes) | Deferred decisions in [[Production Readiness Checklist]] and RUNBOOK "Stored tool runs (retention)". |

**Why the file retention is a constant: not recorded.** The constant arrived with the first version of the logging code (api commit `c840470`, 2026-10-16 12:08 PT, written by Claude when Boris asked for "a rolling week"). No note records a reason for choosing a constant over a setting; the likeliest honest explanation is expedience: "7 days" was treated as the requirement rather than as an operational knob. **That sits badly with the repo's own principle** ("prefer data over hardcoding": facts that can change without a deploy belong in config, `CLAUDE.md`), and there is a precedent for the better shape: `DB_POOL_MAX_CONNECTIONS` (api 1.9.132) reads an env var, validates it (1-200) and falls back to a safe default. A retention period is an operational knob that plausibly differs by environment (laptop disk vs a cloud host, a compliance rule later), so an env var `LOG_RETENTION_DAYS` (default 7, clamped to a sane range) would fit. **Changed on 2026-10-22 at Boris's request** ("yes, make log-file retention an env var LOG_RETENTION_DAYS, default 7, validated like DB_POOL_MAX_CONNECTIONS, with a test and a docs/LOGS.md line"): `parse_log_retention_days` / `log_retention_days` in `src/startup/logging.rs`, bounds 1-365 (a typo like `7000` must not keep logs for years), a warning on stderr for a bad value because logging is not initialised yet, two unit tests (default, both bounds, zero, over the cap, negative, text, empty, decimal), a `docs/LOGS.md` paragraph and a changelog entry under Unreleased. `cargo fmt`, the two tests and `cargo clippy --workspace --all-targets -D warnings` passed; the full preflight runs at push time. Committed locally, **not pushed**. This was a small deliberate exception to the freeze, requested by Boris.

General rule of thumb used in that discussion: a **constant** fits values that are part of the program's logic or safety (algorithm parameters, protocol limits, invariants whose change needs a code review and tests, one canonical value everywhere); a **setting** fits operational knobs that vary by environment or that someone may need to change without a rebuild; the middle path (a constant default plus a validated env override) costs about five lines.

## Forward-looking constraints (Boris, 2026-10-16)

There is no prod today and Fly.io is only the *possible* host. The architecture should be designed for the migration without building for it yet. For logging that means:
- The app emits JSON with `request_id` regardless of host. In the cloud leave `LOG_DIR` **unset** (ephemeral disks) and ship **stdout** (`LOG_FORMAT=json`), labelled `env=prod`.
- The `alloy` service, `LOG_DIR` files and the hardcoded values in the Alloy config are dev-only.
- Full checklist and the unverified Fly.io specifics: [[UnitPrep Fly.io and Deployment Notes]].

## Related

[[Server Logging and Grafana - Index]] · [[Grafana Cloud Setup and Objects]] · [[Reading Logs - Tools and Recipes]] · [[Findings - DB Connection Drops, Cold Starts and Latency]] · [[Key Decisions]] · [[UnitPrep Docker Standards]]
