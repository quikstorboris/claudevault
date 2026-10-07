---
date: 2026-10-06
description: "How the ClickUp duplicate-check update went from ~15 s to ~1.7 s: measured steps, the concurrency, caching, prefetch and stored-share-link changes, what was deliberately not made fire-and-forget, and the floor."
tags: [work-note, unitprep, clickup, performance, dropbox]
status: active
quarter: Q4-2026
project: unitprep
---

# ClickUp Duplicate Check — Speed Work and Share-Link Capture

Part of the [[ClickUp Integration — Design Log]]; the feature itself is in the [[ClickUp Integration — Build Log]] (2026-10-05 entry). Boris found "everything involving ClickUp" slow on 2026-10-05; this is what was measured and changed (released in `unitprep-api` v1.9.80 and later).

## Measured (dev, Neon dev database, this laptop)

| Request | Before | After |
|---|---|---|
| Update the ClickUp task (`duplicate-check-results`) | ~15 s (6.5 s in an earlier run) | **~1.75 s** |
| Find candidate tasks (`duplicate-check-tasks`) | 3.1 s then 10 s (two calls back to back) | ~0.4 s once prefetched |
| Save Link ClickUp (`PUT clickup/links`) | 8.2 s | ~0.7 s |
| Link dialog (`clickup/lists` + `suggestions`, cold) | 1.7 s and 2 s | shared single load; instant once prefetched |

Per-step timings of the final update (logged as `ClickUp duplicate-check step`): credentials 0.19 s, read task 0.2-0.3 s, read statuses 0.2-0.3 s, write comment 0.2-0.3 s, add assignee 0.4 s, set status 0.8-1.0 s. The earlier Dropbox link step (0.8-1.0 s) no longer appears.

## What changed

- **Concurrency.** Independent reads run together (task, list statuses, Dropbox link) and so do the three writes (comment, assignee, status); credentials and the facility/run lookup are one wait; the credentials read is one query (token plus ClickUp user id). Audit rows for a link save are written together.
- **Fewer ClickUp calls.** A list already in the loaded onboarding hierarchy is confirmed from it instead of a `GET /list/{id}` each (`Hierarchy::find_list`). Consequence for tests: the "token has gone bad" test now resolves a list that is *not* cached, because a cached one makes no ClickUp call.
- **Task list reading.** Pages are fetched in parallel batches (2 first, then 3) instead of one after another; the result is cached per user and list for **5 minutes** and dropped for a list the moment Orchestrator writes to it (`clickup::task_cache`). The update itself always re-reads the chosen task, so the cache never decides a write.
- **Single-flight loading.** Concurrent cold requests share one load: per user for the hierarchy, per (user, list) for tasks. React's dev double-mount fires every effect twice, which used to cost two full reads.
- **Prefetch (fire and forget).** `POST /integrations/clickup/prefetch` and `POST .../clickup/prefetch-tasks` answer 202 and warm the caches in a spawned task; the UI calls them when the Company page loads and when the dedup results page opens. Safe *only because the work is read-only and repeatable*: a failure or an unused result loses nothing, and a real request that arrives mid-warm-up waits for it.
- **Share link captured at save time.** Saving a dedup export to Dropbox creates the file's share link in a background task and stores it (`client_ops.tool_runs.output_dropbox_link`, migration `20261005140000`; reset to NULL whenever a new file is saved for the run, matched on path so an old link never attaches to a newer file). The update uses the stored link and only asks Dropbox when it is missing (then stores it). `sharing.write` is enabled on the Dropbox app (Boris, 2026-10-05); if Dropbox refuses, the comment falls back to the file's `dropbox.com/home/<path>?preview=<file>` URL.

## Decisions

- **Writes are not fire-and-forget.** The update posts as the user and must report each step (comment, assignee, status); a spawned task would answer "done" before knowing, lose a failed status change to the logs, and die on an API restart. Also rejected: `202 Accepted` plus polling (job state and a polling UI to save about a second).
- **Axum adds nothing here**; the tool is `tokio` (`join!`, `try_join!`, `join_all`, `spawn`).

## The floor

What remains is Neon database round trips (about 200 ms each from this laptop) and ClickUp's own status write (about 1 s, probably its automations). Not removed on purpose: the audit row is written before the response.

## Gotchas learned

- A browser tab keeps running the old bundle after a UI change; "I do not see it" can be a stale tab. Check the served bundle directly: `docker exec unitprep-ui-ui-dev-1 sh -c 'grep -rl "<string>" /app/.next/dev/static'` (see [[Gotchas]]).
- The running API caches the vendor registry (4 h) and reads Neon dev, so a migration or registry change needs the API restarted and the migration applied to Neon dev, not just the test DB.
