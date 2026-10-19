---
date: 2026-10-16
description: "Every way to read UnitPrep server logs (files, Grafana UI, logcli, curl, the Grafana MCP server, Claude's browser access), exactly what was installed and how it was verified, plus the LogQL and shell recipes used. How a Claude session should look at logs."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Reading logs: tools and recipes

Part of [[Server Logging and Grafana - Index]]. The repo-side copy of the user-facing parts is `unitprep-api/docs/LOGS.md`. Where the logs come from: [[Server Logging Design and Decisions]]. Token inventory: [[Grafana Cloud Setup and Objects]].

## The ways to read logs, best first for a Claude session

| # | Way | Needs | Notes |
|---|---|---|---|
| 1 | **The JSON files** `unitprep-api/logs/unitprep-api.YYYY-MM-DD.log` | WSL access only | Always works, no network, no tokens; last 7 days only. Read with `grep`/`python`/`jq`. A Windows session reaches them through `wsl.exe -e bash -lc '...'`. |
| 2 | **`scripts/logcli.sh`** (Loki CLI) | `GRAFANA_LOGS_READ_TOKEN` in `.env.local` | Queries Grafana Cloud Loki from the terminal; any time range Grafana still holds. |
| 3 | **The `grafana` MCP server** | `GRAFANA_SERVICE_ACCOUNT_TOKEN`; a session **started in `unitprep-api`** and the one-time project-MCP approval | Read-only: dashboards, alert rules, Loki queries. |
| 4 | **Claude in Chrome driving Grafana** | the extension connected and Boris logged in; only while a conversation is running | Used on 2026-10-16 for everything before the tools existed. Not usable unattended. |
| 5 | **Grafana UI by hand** | a browser | Explore, Drilldown > Logs, the dashboard, Alerting. |
| 6 | **`curl` against the Loki HTTP API** | the read token | What `logcli` wraps; example in `docs/LOGS.md`. |

## What was installed (all in WSL, no sudo)

- **logcli 3.7.8** (`~/.local/bin/logcli`): downloaded `logcli-linux-amd64.zip` (37,460,587 bytes) from the `grafana/loki` GitHub release `v3.7.8` (published 2026-09-17), **SHA256 verified** against the release's `SHA256SUMS`, extracted with Python's `zipfile` (no `unzip`), installed with `install -m 0755`.
- **mcp-grafana 2.0.2** (`~/.local/bin/mcp-grafana`): `mcp-grafana_Linux_x86_64.tar.gz` (17,925,836 bytes) from the `grafana/mcp-grafana` release `v2.0.2` (published 2026-10-07), SHA256 verified against `mcp-grafana_2.0.2_checksums.txt`.
- Boris approved the install in chat ("install and configure everything in the 'for what we're doing' section"); the exact files, sources and sizes were stated before downloading. The temporary download directory was deleted. `~/.local/bin` was already on `PATH`.
- Upgrade by downloading the newer release asset the same way and replacing the file.

## The wrapper scripts (committed `0999d9a`)

- `scripts/logcli.sh`: extracts only `GRAFANA_LOGS_READ_TOKEN` from `.env.local` (`grep -m1 '^NAME=' | cut | sed` for quotes; **never `source`** the file, see [[Gotchas]]), exports `LOKI_ADDR=https://logs-prod-021.grafana.net`, `LOKI_USERNAME=1836339`, `LOKI_PASSWORD=<token>`, then `exec logcli "$@"`. Exits 1 with a clear message if the token is missing (tested before the token existed).
- `scripts/grafana-mcp.sh`: extracts `GRAFANA_SERVICE_ACCOUNT_TOKEN`, exports `GRAFANA_URL=https://joyfulpelican1551.grafana.net`, then `exec mcp-grafana --disable-write --enabled-tools "search,datasource,loki,alerting,dashboard,folder,navigation" --max-loki-log-limit 500 --usage-stats disabled`.
  - `--disable-write` removes every create/update tool. `--enabled-tools` drops groups we do not use (the default list also includes incident, oncall, asserts, pyroscope, tempo, annotations, rendering, snapshot, plugin, api, config, provisioning, docs, user, prometheus).
  - The server prints "Anonymous usage statistics are being reported to Grafana Labs" by default; `--usage-stats disabled` removed that notice (checked).
  - Verified that it accepts `GRAFANA_URL` and `GRAFANA_SERVICE_ACCOUNT_TOKEN`: with a fake token it logged `api_key_set=true` and the stack answered 401.
- Both scripts must be executable. **Editing a WSL script through the `\\wsl.localhost\...` path silently strips the exec bit** (it happened again on `grafana-mcp.sh`) and a first edit via a Python heredoc inside `bash -lc '...'` dropped a line-continuation backslash that `bash -n` did not catch. Re-`chmod +x`, then run the script to check. Both are in [[Gotchas]].
- **Registration**: repo-local `unitprep-api/.mcp.json` (untracked, not in git) gained a `grafana` entry (`command: bash`, `args: [/home/bmaksimov/Development/unitprep-api/scripts/grafana-mcp.sh]`) beside the existing `om` entry. Claude Code asks for approval the first time a session starts there. A Windows session at `C:\Users\bmaksimov` does not see it.

## Verification results (2026-10-16, ~13:45 and again 16:19 PT)

- `scripts/logcli.sh query '{job="unitprep-api", level=~"ERROR|WARN"}' --since=24h --limit=5` returned the real 13:27 lines (slow statement, `error occurred while testing the connection on-release`, `session resolution query failed`).
- MCP driven over stdio by a small Python client (`initialize`, `tools/list`, `tools/call`): server `mcp-grafana 2.0.2`; **20 tools**: `alerting_manage_routing`, `alerting_rules_read`, `alerting_silences_read`, `analyze_loki_labels`, `check_datasources_health`, `generate_deeplink`, `get_dashboard_by_uid`, `get_dashboard_panel_queries`, `get_dashboard_property`, `get_dashboard_summary`, `get_datasource`, `list_dashboard_versions`, `list_datasources`, `list_loki_label_names`, `list_loki_label_values`, `query_loki_logs`, `query_loki_patterns`, `query_loki_stats`, `search_dashboards`, `search_folders`. No create/update/delete/add tool names. (`alerting_manage_routing` has a "manage" name; under `--disable-write` it is presumably read-only, **not verified**.)
- `list_datasources` returned the stack's datasources; `query_loki_logs` (`datasourceUid: grafanacloud-logs`) returned real ERROR lines; `alerting_rules_read` needs `operation: list|get|versions` (a call without it fails with `unknown operation ""`), and `list` returned both alert rules with state `normal`, health `ok`.
- At 16:19 PT both reads still worked (`logcli` exit 0, empty because no new logs in the last 10 minutes).

## Recipes used (LogQL)

```
{job="unitprep-api"}                                              everything
{job="unitprep-api", level="ERROR"}                               errors (level is a stream label)
{job="unitprep-api"} |= "request completed" | json | fields_status >= 500
{job="unitprep-api"} |= "passkey"                                  login ceremony lines
{job="unitprep-api"} |= "grafana-live-check"                       a marker request (see below)
sum by (target, fields_message, span_method, span_path, err) (count_over_time({job="unitprep-api", level="ERROR"} | json | label_format err=`{{ trunc 140 .fields_error }}` [3h]))
```
- Instant metric queries from the shell: `scripts/logcli.sh instant-query '<metric query>' --quiet -o jsonl`. Plain log queries: `query '<selector>' --since=1h --limit=50 --quiet -o raw`.
- Because `level` is a stream label, a `| json` that also extracts `level` surfaces it as `level_extracted`.
- Per-route statistics were computed by piping `logcli ... -o raw` into a short Python script (route normalisation with a UUID regex, then min/median/p90/max); results are in [[Findings - DB Connection Drops, Cold Starts and Latency]].
- **Marker-request technique** to prove the pipeline end to end: `curl localhost:8080/grafana-live-check-<epoch>` (a harmless 404), then search Grafana for that string. It showed up about 10 ms after the file timestamp. (That 404 line, `GET /grafana-live-check-1792181828`, is now permanently in the dev logs.)
- A throwaway test server can run beside the user's on a spare port: `PORT=8081 LOG_DIR=./logs ./target/debug/unitprep` (never stop Boris's own server on 8080).

## Reading logs correctly: quiet is not broken (learned 2026-10-19)

- The server logs one line per request plus a few background jobs, so an idle server writes almost nothing (66, 15 and 16 lines on the three days after the build day). A silent Grafana tab can mean "nothing happened", "the view is stale" or "the default window is too short" (Explore and Drilldown default to 1 hour, the dashboard to 6). **Before concluding the pipeline is broken**, compare the newest line in `./logs/*.log` with the newest line in Loki (`scripts/logcli.sh query '{job="unitprep-api"}' --since=192h --limit=5000 -o raw`, take the maximum timestamp) and read `docker compose logs alloy`.
- **Sentry from the terminal**: the Sentry CLI is installed in WSL and logged in (see [[Sentry and Grafana Access for Claude]]). `sentry issue list quikstor-wf/orchestrator` shows only **unresolved** issues by default; add `--query "is:resolved"` to see the rest.

## Other tools Grafana offers (answer given to Boris; versions and some details are **recalled, not verified**)

- **`logcli`** (installed), **Loki HTTP API** (what logcli wraps), **`mcp-grafana`** (installed).
- **Grafana HTTP API**: dashboards, alert rules, contact points; needs a service-account token with write rights. Everything done in the browser today could be done this way more reliably; the installed service account is Viewer, so it cannot.
- **`grafanactl`** (Grafana's newer CLI for managing resources) and the **Terraform provider**: not installed or checked.
- **Grafana Foundation SDK** (dashboards as code in TypeScript/Go/Python/...): our generated dashboard JSON is a hand-rolled version of that idea.

## Related

[[Server Logging and Grafana - Index]] · [[Grafana Cloud Setup and Objects]] · [[Server Logging Design and Decisions]] · [[WSL Execution Technique]] · [[Gotchas]]
