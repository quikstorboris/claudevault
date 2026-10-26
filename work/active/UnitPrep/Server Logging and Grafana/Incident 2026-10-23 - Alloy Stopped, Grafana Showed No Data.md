---
date: 2026-10-23
description: "Incident 2026-10-23: Grafana showed no logs because the Alloy shipper container had been stopped for about 24 hours (it lives in its own compose profile and was not restarted with the dev containers); how it was found, fixed and verified, the blind spot it exposed in the twice-daily routine, and the separate Loki 'empty-compatible matcher' parse error."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Incident 2026-10-23: Grafana showed no logs (Alloy was stopped)

Part of [[Server Logging and Grafana - Index]]. Related: [[Routine Monitoring and Troubleshooting Playbook]], [[Reading Logs - Tools and Recipes]], [[Server Logging Design and Decisions]].

## What Boris saw

At about 16:15 PT on Friday 2026-10-23 he opened his Grafana logs and saw no logs, plus an error: `parse error: queries require at least one regexp or equality matcher that does not have an empty-compatible value. For instance, app=~".*" does not meet this requirement, but app=~".+" will` (trace ID `c97120b44c1a96bd1edcb27ac310a9de`). He had just asked for "my Grafana logs url".

## Two separate things

### 1. No data: the Alloy shipper had been stopped for 24 hours (the real problem)
- Drilldown > Logs (last 24 hours) said **No data** for `unitprep-api`.
- Evidence: the local files were fine (newest line 23:18:38Z, today's file 29 KB, 51 lines); **Loki's newest line was 2026-10-22T20:35:09Z**; `docker compose ps -a` showed **`alloy-1` "Exited (0) 24 hours ago"** while `api-dev` and `test-db` were "Up 52 minutes". Alloy's own log ended with a clean shutdown at **2026-10-22T23:06:35Z (16:06 PT)**: every tailer "stopped tailing file", `node exited without error`.
- **Why it stayed down**: Alloy is in its own compose profile (`logs`). Starting the dev containers with only `--profile dev` does not start it, so after the containers were stopped and the dev ones brought back at about 15:29 PT today, the shipper stayed off. The most likely sequence is a `docker compose ... down` yesterday at 16:06 PT followed by `up --profile dev` today (not proven; a WSL or Docker Desktop restart also stops containers cleanly). Nothing was lost: the server kept writing its files.
- **Fix** (done at 16:21 PT, read-only for the data, one container started): `docker compose --env-file .env.local --profile dev --profile logs up -d alloy`. Alloy resumed from its saved read positions (`alloy-data` volume): it continued yesterday's file at the end (offset 44,345) and read today's file from offset 0. **Verified**: ten seconds later Loki held **all 51 of today's lines**, matching the local file, and its newest line was from three minutes earlier. The dashboard rendered with data again.
- **To avoid it**: bring everything up with `docker compose --env-file .env.local --profile dev --profile logs up -d`, not `--profile dev` alone (this command is also in `docs/LOGS.md`). A one-line alias would do it.

### 2. The parse error (cosmetic, a query with no usable label)
- It means Loki was sent a selector whose only filters match empty values (for example an empty builder, `{}` or `{x=~".*"}`). Loki needs at least one matcher that cannot be empty, such as `job="unitprep-api"` or `app=~".+"`.
- Checked 2026-10-23: the Drilldown link and the dashboard load without it. The bare `https://joyfulpelican1551.grafana.net/explore` link opens on the **Prometheus** data source with an empty query, and switching to the Loki source leaves an **empty label builder**; running that raised an error alert (shown as "Unknown error" in my test, so I could not reproduce the exact wording, the cause class is the same). The likeliest source of Boris's error is Explore on Loki before a label was chosen. The exact page that raised it was not confirmed.
- **Working link, tested** (Explore, Loki, `{job="unitprep-api"}`, last 24 hours): `https://joyfulpelican1551.grafana.net/explore?schemaVersion=1&panes=%7B%22a%22%3A%7B%22datasource%22%3A%22grafanacloud-logs%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22expr%22%3A%22%7Bjob%3D%5C%22unitprep-api%5C%22%7D%22%2C%22queryType%22%3A%22range%22%2C%22datasource%22%3A%7B%22type%22%3A%22loki%22%2C%22uid%22%3A%22grafanacloud-logs%22%7D%2C%22editorMode%22%3A%22code%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%22now-24h%22%2C%22to%22%3A%22now%22%7D%7D%7D` (or in Explore pick the Loki data source, label `job`, value `unitprep-api`).

## The blind spot this exposed

`scripts/anomaly_check.py` (the twice-daily routine) reads the **local log files and Sentry**, not Loki and not the containers. So the routine reported ALL_CLEAR all along while **Grafana had been silently empty for a day**; nobody was alerted that the shipper had stopped. The check as written cannot see this. A cheap fix, **not made** (the stack is frozen; Boris decides): have the script also (a) check that the `alloy` container is running, and/or (b) compare the newest local log line with the newest Loki line and flag a gap of more than a few minutes while the server is active. Also relevant: the routine would not notice if Loki rejected lines (for example over a plan limit).

## Related facts noticed

- The Grafana trial banner read "7 days left" on 2026-10-23 (trial ends 2026-10-30); Boris plans to use the forever-free plan (14 days retention, 50 GB/month, verified on the pricing page, see [[Grafana Cloud Setup and Objects]]).
- Today's request lines now carry `user_id` and `roles` (api 1.9.131), visible in the Explore result.

## Fix applied 2026-10-26 (unitprep-api commit 4a13290, local, not pushed)

- **Likely cause, corrected:** `docker compose --profile dev down` does not touch alloy (it lives in the `logs` profile), so a Docker/WSL restart is the more likely reason it stopped. Not proven.
- **Option 1, remove the cause:** `scripts/dev_up.sh` starts test-db, api-dev and alloy with the right profiles and `--env-file`; DOCKER.md and LOGS.md point at it; alloy has `restart: unless-stopped`, so it returns after a Docker/WSL restart.
- **Option 2, warn only:** `scripts/anomaly_check.py` ends with a "DEV STACK STATE" section (API answering on :8080, containers running, age of the last request) and a `WARNINGS=n` line. Warnings never count as anomalies, never change STATUS, and nothing notifies or acts on them. Simulated both failure cases; both fire.
- **Option 3 not built:** an in-app idle/heartbeat log with an admin-settings menu. Boris: "there's not need to control anything in admin with that". Revisit only if the settings menu gets ~3 real candidates or prod exists.
