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

## Related

[[UnitPrep Fly.io and Deployment Notes]] · [[Production Readiness Checklist]] · [[UnitPrep Docker Standards]] · [[UnitPrep Tech Stack]] · [[Key Decisions]] · [[Gotchas]]
