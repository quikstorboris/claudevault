---
date: 2026-10-19
updated: 2026-10-23
description: "Standing playbook for troubleshooting UnitPrep/Orchestrator: Claude can and should check Sentry and the server logs itself (where to look, in what order, known-benign patterns, what a real anomaly looks like), plus the twice-daily scheduled routine that does it unattended, with its guardrails for fixing."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Routine monitoring and troubleshooting playbook

Part of [[Server Logging and Grafana - Index]]. Written 2026-10-19 at Boris's request: "explain to yourself and anyone in the future that you can and should check Sentry and Grafana regularly ... this is a very significant improvement of how you and I are interacting and troubleshooting."

## The point, in one paragraph (read this first)

**Claude can read Sentry and the server logs by itself, and should, instead of asking Boris to paste output.** Until 2026-10-16 a session saw only what was pasted into the chat and the server's logs vanished when the terminal closed. Now every request and background job is logged as JSON (a week kept on disk, longer in Grafana Loki), errors and panics go to Sentry, and a session in the right place can query all of it. That turns "something is wrong" from a request for evidence into an investigation Claude can start alone, which is how the idle-connection 500s, the cold-start numbers, the stale-server mix-up and the weekend "missing logs" scare were each settled in minutes. **A future session that is asked about a bug, a slow page or a 500 should look first.** A scheduled routine now does the same every 12 hours without being asked.

## Look first: the order

1. **`python3 scripts/anomaly_check.py [--hours N] [--include-resolved]`** (from `~/Development/unitprep-api`; from Windows: `wsl.exe -e bash -lc 'cd ~/Development/unitprep-api && python3 scripts/anomaly_check.py --hours 14'`). Read-only. Prints unresolved Sentry issues for both projects, ERROR lines and HTTP 5xx in the window, benign counts as information, and whether the checkouts and the running server are stale. Ends with `ANOMALIES=n` and `STATUS=ALL_CLEAR` or `ATTENTION`. Tested 2026-10-19: all clear on a quiet window; with a 200 h window it found all six Friday ERRORs and six HTTP 500s.
2. **The log files** `unitprep-api/logs/unitprep-api.DATE.log` (JSON lines, 7 days) and **`scripts/logcli.sh query '{job="unitprep-api", level="ERROR"}' --since=24h`** for Grafana Loki. Match a report to its lines with `request_id` (also the `x-request-id` response header).
3. **Sentry** from the CLI: `sentry issue list quikstor-wf/orchestrator` and `.../orchestrator-ui` (**unresolved only by default**; add `--query "is:resolved"`), `sentry issue view <SHORT-ID>` for the stack trace and tags. Org `quikstor-wf`; projects `orchestrator` (Rust API) and `orchestrator-ui` (Next.js).
4. **Grafana**: the `grafana` MCP server (sessions started in `unitprep-api`) or Chrome for dashboards and alert rules. Detail: [[Reading Logs - Tools and Recipes]], [[Sentry and Grafana Access for Claude]].
5. **Dependencies and CI** (added 2026-10-23, in the same script; `--deps-only` runs just this part in about 15 s): `cargo audit` for the API, `npm audit` for the UI, review dates of dated advisory exceptions in `.cargo/audit.toml`, whether the UI's installed `node_modules` match `package-lock.json` (and Next.js specifically), and the latest GitHub Actions run per branch/tag in both repos (`gh`). See "Dependency and CI anomalies" below.
6. **Freshness before debugging**: is the running server older than the code? (`cargo run` does not reload; the 2026-10-16 20:27Z errors came from a server older than its fix.) Are the local checkouts behind origin? (`git fetch`; on 2026-10-19 they were behind by 3 and 1.)

Hard rules: everything above is **read-only**; never `source` `.env.local`; never paste a token into chat or the vault (names and scopes only); never switch branches, reset, stash or revert in the main checkouts (Boris's server runs from them and other sessions keep uncommitted work there; on 2026-10-19 both repos had an uncommitted "add facility" feature in progress).

## What is normal here (known-benign; the check never counts these)

| Pattern | Why it is fine | Source |
|---|---|---|
| `WARN before_acquire ... expected to read 5 bytes, got 0 bytes at EOF` **with no ERROR beside it** | The pool tested an idle connection, found it dead (Neon suspended its compute) and replaced it. Recurs at 4-hour offsets from server start (a background job). | [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]] |
| `WARN Rate limiter full, call is waiting` bursts around 10:00Z (03:00 PT), field `limiter=process_street` | The nightly Process Street sync's own pacer (6 calls per 10 s) delaying its calls; none fail. Until api 1.9.135 (2026-10-22) the message wrongly said "ClickUp rate limiter full" (25 lines on 10-17, then 3 a day); `limiter=clickup` waits are the real per-user ClickUp limiter (80 calls per 60 s) and are also benign unless a 429 follows. | [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]] (with its correction) |
| `Process Street call` INFO lines and `sync scheduled`/`person-index sync completed` daily at ~10:00Z | The nightly sync. | same |
| Occasional `slow statement` WARN (200 ms threshold) | Neon round trips (~50 ms each, about five per request). Only a pattern of them matters. | [[Findings - DB Connection Drops, Cold Starts and Latency]] |
| First request after about 5+ idle minutes takes 1.5-2.5 s and returns 200 | Neon cold start (accepted by Boris on 2026-10-16). | same |
| Almost no log lines when nobody uses the app; no request lines | Idle, not broken. Compare the newest local line with the newest Loki line before suspecting Alloy. | same |
| The five resolved Sentry issues from 2026-10-16 (`ORCHESTRATOR-1`, `ORCHESTRATOR-UI-1..4`) and `GET /grafana-live-check-*` 404s | Test events and marker requests. | [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]] |

## Known failure mode: Grafana empty because the shipper is stopped (2026-10-23)

If Grafana shows no data but `./logs` has fresh lines, check `docker compose ps -a` for `alloy-1` (it needs the `logs` profile: `docker compose --env-file .env.local --profile dev --profile logs up -d`). The anomaly script does **not** detect this (it reads local files and Sentry only). Full account: [[Incident 2026-10-23 - Alloy Stopped, Grafana Showed No Data]]. Separately, Loki's error "queries require at least one regexp or equality matcher that does not have an empty-compatible value" just means a query has no non-empty label filter (use `{job="unitprep-api"}`).

## What a real anomaly looks like

An **unresolved Sentry issue**; any **ERROR** log line; any **HTTP 5xx**; a **panic**; the DB message `expected to read 5 bytes` as an ERROR/500 **without** a `before_acquire` warning before it (the pre-fix pattern); the Sentry CLI not authenticated or Sentry/Loki unreachable (a blind check is **never** "all clear"); no readable logs at all while the server is supposed to be up.

## Dependency and CI anomalies (added 2026-10-23)

Why: on 2026-10-23 Next.js flagged a critical advisory in the browser, and the daily check could not have seen it (it only watched Sentry and logs). The same day the check was extended; its first run found that the UI checkout's `node_modules` was still on Next.js 16.4.0 while the lockfile (after a pull) pinned the fixed 16.4.3, so `npm audit` said "0 vulnerabilities" while the dev server ran the vulnerable code.

Counted as anomalies (STATUS=ATTENTION):
- any `cargo audit` vulnerability (exceptions in `.cargo/audit.toml` are applied automatically; unmaintained/unsound/yanked warnings are information only);
- an advisory exception **past its `REVIEW by YYYY-MM-DD` date** (today: the `zip` extract exceptions, review **2026-11-16**; 14 days before, the report prints "due soon" as information);
- any `npm audit` finding (preflight blocks on the same);
- UI `node_modules` that differ from `package-lock.json` (`npm ls` problems, or Next.js installed != locked): fix is `npm ci` in `unitprep-ui` and a dev-server restart, which is **Boris's call** because it replaces the tree his server runs from;
- the latest GitHub Actions run on any branch or tag in either repo concluded `failure`/`timed_out`;
- the Sentry CLI login expiring within 7 days (it currently expires 2026-11-15);
- any of the tools above unable to run (blind), never reported as clear.
Information only: newer Next.js release available, still-running CI, unmaintained/unsound/yanked crates.

**What the routine does about them**: logs and alerts, nothing more. It does **not** upgrade dependencies, edit lockfiles, run `npm ci`/`cargo update`, or change `.cargo/audit.toml`: a dependency change needs preflight, the e2e suite and a release, and the allowance decision is Boris's. A fix is a normal session (recipe: [[Session 2026-10-23 - Next.js 16.4.3 Security Upgrade]]).

## The routine (scheduled task `unitprep-anomaly-check`)

- **When**: twice a day, 12 hours apart, outside working hours: **07:30 and 19:30 Pacific** (cron `30 7,19 * * *`, local time; scheduled tasks add a few minutes of jitter). Boris's days have run roughly 08:15-17:00 PT. **It only runs while the Claude desktop app is open and the laptop awake;** if the app was closed it runs at the next launch (the laptop also went into Modern Standby on 2026-10-16).
- **What it does** (each run is a fresh session with no memory of this conversation, so its prompt is self-contained): reads this note; runs `anomaly_check.py --hours 14` (which now includes the dependency and CI section); appends an entry to [[Routine Check Log]] (even when all clear); if `STATUS=ALL_CLEAR` stops; otherwise investigates each anomaly read-only (`sentry issue view`, the matching log lines by `request_id`, freshness, whether it is already known), classifies it (real bug in our code, environmental, test noise, already fixed in newer code), and acts per the policy below. If a push notification tool is available it alerts Boris for real findings.
- **Fix policy (Boris: "fix them if anything comes up")**, with guardrails Claude chose because unattended code changes are risky:
  - It may fix only when the cause is clear from the stack trace and logs, the fix is small and local to our code, and it is not security, auth, a migration or anything data-destructive. Otherwise it writes findings and a proposed fix in the log and changes nothing.
  - **It never touches the main checkouts** (`~/Development/unitprep-api`, `unitprep-ui`): no edits, stash, reset, checkout, pull or commit there. It works in a **separate git worktree** under `~/Development/autofix/` on a new branch `auto-fix/<id>`, runs the repo's `scripts/preflight.sh` there, adds a regression test when feasible, and **commits locally only**.
  - **It never pushes, tags, merges, bumps a version, resolves/ignores/assigns a Sentry issue, runs a migration or touches any prod database URL or prod script.** Boris reviews and merges.
  - It never prints or sources secrets.
- **Reviewing an auto-fix**: `git -C ~/Development/unitprep-api worktree list`, `git log auto-fix/<id>`, read the diff and the log entry; to adopt it merge or cherry-pick into main yourself, then `git worktree remove ~/Development/autofix/<name>` and `git branch -d auto-fix/<id>`.
- **Where results go**: [[Routine Check Log]] (vault, left uncommitted for Boris to commit with other notes), the run itself in Claude desktop's Scheduled section, and a push notification for real findings if available.
- **Change or stop it**: the Scheduled section of the desktop app (pause, edit prompt or schedule), or ask Claude to update/disable task `unitprep-anomaly-check`.
- **Dependencies**: the Sentry CLI login (OAuth, auto-refresh, expires 2026-11-15 unless refreshed; if it lapses the run reports "BLIND" and Boris must log in again), WSL running, the `scripts/anomaly_check.py` script (committed in the API repo).
- **Cost**: each run is a handful of tool calls when quiet; investigations cost more. Exact token cost was not measured.

## The decision to freeze (Boris, 2026-10-19)

"No new starts is fine. Freeze it until something comes up." Nothing is added to the observability stack (no new alerts, panels, metrics, traces or tools) unless a real problem calls for it. This routine and these notes are the deliberate exception: they make the existing stack useful without growing it. The honest scale check is in [[Observability Stack as a Demonstration of Skill]].

## Related

[[Server Logging and Grafana - Index]] · [[Routine Check Log]] · [[Sentry and Grafana Access for Claude]] · [[Reading Logs - Tools and Recipes]] · [[Gotchas]] · [[Patterns]]

## `WARNINGS=n` line (added 2026-10-26)

The report now ends with `WARNINGS=<n>` after `STATUS`. It comes from the warnings-only DEV STACK STATE section (API not answering, a dev container not running, last request age). It is informational: do not treat it as an anomaly, do not notify, do not fix anything because of it. Boris said he does not need it checked. Start everything with `scripts/dev_up.sh`.
