# ClickUp logging in Grafana (2026-10-16)

`unitprep-api` commit `3b9c01e`. Previously the ClickUp integration emitted no `tracing` lines.

## What is logged
- **INFO `ClickUp call`**: method, endpoint (path, query string dropped), status, latency_ms. One per call, from `get` and `send_json` in `src/clickup/client.rs`, the only two places a ClickUp request is sent.
- **WARN `ClickUp rate limiter full, call is waiting`**: the in-process 80 calls/60 s limiter (`rate_limit.rs`) made a call wait. Logged once per call, with wait_ms.
- **WARN `ClickUp rate limit hit (429)`**: a 429 came back. `send_with_retry` already retries 429s, so this only fires when the retries ran out.
- **ERROR `ClickUp request failed`**: any non-success status (including 404/401), body bounded to 512 bytes. Also `...no response` for connect/timeout errors.
- **Copy jobs** (`api/clickup_copy/jobs.rs`, `bulk.rs`): INFO started, INFO results (copied/failed), INFO finished, ERROR if finished with a non-`done` status, WARN `was interrupted`.
- The personal API token is never logged.

## Known limits
- "Interrupted" is only detected when a job is read (status computed in SQL), so the WARN repeats on every read of that job.
- 404s from list lookups count as "failed requests" (ERROR); they are often expected.
- Tests: only the `endpoint()` helper; the rest is log output, no behavior change.

## Dashboard
`dev-tools/grafana/unitprep-api-logs.dashboard.json` is now version 3 with two new panels (ids 16-17): ClickUp calls by HTTP status, and limiter waits / 429s / failures / failed or interrupted copy jobs. **Re-import** (Grafana > Dashboards > Import, same uid overwrites).
