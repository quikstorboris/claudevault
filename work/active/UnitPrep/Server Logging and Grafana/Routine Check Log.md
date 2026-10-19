---
date: 2026-10-19
description: "Append-only log of the twice-daily UnitPrep anomaly check (07:30 and 19:30 PT): one entry per run with status, what was found, and what was done. Newest entries at the bottom."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Routine check log

Append-only record written by the scheduled task `unitprep-anomaly-check` (and by hand). Rules, known-benign patterns and the fix policy are in [[Routine Monitoring and Troubleshooting Playbook]]; index in [[Server Logging and Grafana - Index]]. One entry per run, newest at the bottom, even when everything is clear. Format:

`### YYYY-MM-DD HH:MM PT | STATUS (ALL_CLEAR / ATTENTION / BLIND) | ANOMALIES=n` then one or two lines: what was seen, classification, request_ids, and any action (auto-fix branch and worktree path, commit, preflight result) or "no change".

### 2026-10-19 09:25 PT | ALL_CLEAR | ANOMALIES=0 | (created by hand when the routine was set up)

Baseline run of `anomaly_check.py --hours 14 --include-resolved`: Sentry has 0 unresolved issues in `orchestrator` and `orchestrator-ui` (five resolved Friday test issues listed as information); 16 log lines in the window, 0 requests (idle app), 0 ERROR, 0 HTTP 5xx; information only: 2 pool `before_acquire` warnings, 3 ClickUp limiter waits. Freshness: `unitprep-api` behind origin/main by 3 commits, `unitprep-ui` by 1; the running server (last start 2026-10-16 22:14:24Z) is older than the checkout's newest commit. A 200 h window run was used to confirm the script detects the six real Friday ERRORs and six HTTP 500s (it did, ANOMALIES=12). Sentry token expires 2026-11-15 13:31 PT. No change made.
