---
date: 2026-10-14
description: "Second-pass backlog after the efficiency refactor: Grok's 2026-10-14 list (api v1.9.122 / ui v1.6.95) checked against the real code, corrected, and re-ranked. Short, targeted; not another program."
tags: [work-note, unitprep, efficiency, refactor, backlog]
status: active
quarter: Q4-2026
project: unitprep
---

# Efficiency Refactor - Second Pass List (2026-10-14)

Source: a fresh external review (Grok) at `unitprep-api` v1.9.122 / `unitprep-ui` v1.6.95, **each claim re-checked against the WSL checkouts the same day**. Several of its Tier A items were already done or mis-stated; the corrected picture is below. Plan context: [[Efficiency Refactor - Master Plan and Progress]]. Prior measurements: [[Efficiency Refactor - Concurrent Load Results]].

Working-tree note: both repos had uncommitted Tagger edits at review time (api `src/api/tagger/tests.rs`; ui `TaggerResultsPage*`, `tagger/CandidateRow/CandidateSection/usePreserveBlanksGate`). Not part of this review; left untouched.

## Verdict on Grok's list

| Grok item | Checked result |
|---|---|
| A1 ClickUp raw `join_all` | **Mostly a non-issue.** Every upstream ClickUp fan-out is already bounded another way: `clickup_copy/copy.rs` chunks by `WRITE_CONCURRENCY`, `exec.rs` by `CHUNK_SIZE = 4`, `bulk.rs:313` by `LIST_READ_CONCURRENCY`, `clickup/tasks.rs` by a 2-then-`LATER_PAGE_BATCH` page batch, plus a per-user `clickup::rate_limit`. The two `join_all`s in `clients_clickup_links.rs` (285, 412) are **audit-log DB writes after the commit**, not ClickUp calls. Real residue is style only (see S1). |
| A2 XLSX cost | **Already on the blocking pool** (`api/dedup_blocking.rs` -> `generate_export`). Measured 154 ms release at 5,000 rows. Brief already says do nothing unless operators complain. One genuine micro-waste found (S2). |
| A3 record load baseline | **Already recorded** in the vault note above (1/4/8/16 operators, blocking-vs-inline A/B). Only gap: numbers are not in the repo's CHANGELOG/RUNBOOK (CHANGELOG only mentions the benchmark exists). |
| A4 tx held across HTTP | **Read-only audit came back clean.** `clickup_copy/bulk.rs` prepare (76-94) is begin -> 2 reads -> commit before any ClickUp call; `jobs.rs` transactions are short single-purpose; `clickup_connection.rs` calls `identify` before the save tx and after the commit; `clickup_run_update.rs` tx (194-250) has no HTTP inside. No code change needed. Optional: pin it with a test (S3). |
| C1 dead allowlist | **Not dead, not duplicated.** None of the 18 entries contain `_db_`, so nothing runs twice. But it costs 18 separate `cargo test` invocations; renaming them to `_db_` would collapse that to one (S4). |
| C2 Playwright | **Stale.** `e2e/` already has 6 specs (dedup, discovery, export, session-expired, session-remount, tagger). The real gap is that UI `ci.yml` (tag + PR) runs only tsc, eslint, vitest, never Playwright, and has no login/TOTP spec. |
| C3 UI `check_workflow_secrets.sh` | Real: API has it (ci.yml:33 and preflight step 8/9), UI workflow has neither. |
| C4 SCHEMA drift | Real: `regenerate_schema_sql.sh` is in no preflight step or workflow, and needs Docker, so it is a release-checklist item, not a push gate. |
| C6 stale docs | **Only one hit**: `RUNBOOK.md:77` describes the session store's in-memory layer as the reason for single-instance. True but worth one line saying the DB is the source of truth (post-refactor). No "ignore = Neon only" text left. |
| C5 squash | Agree: defer. 226 migration files (~113 up/down pairs). |

## Second-pass backlog (what is actually left)

Ordered by ROI. Each is a candidate chunk, not a mandate.

### Do next (small, clear value)

| # | Item | Repo | Size | Notes |
|---|---|---|---|---|
| S4 | Fold the 18-name CI allowlist into the `_db_` convention | api | S | Rename tests (or keep the list but drop to one invocation). Cuts CI runtime and removes the two-mechanism confusion explained in the script's own header. Keep the rule that live-account tests never contain `_db_`. |
| S5 | UI CI parity: add `check_workflow_secrets.sh` + a Playwright smoke job on tags | ui | S-M | Reuse the 6 existing specs on tag only (not every PR) if runtime is a concern. Add a login + TOTP step-up spec afterwards. |
| S6 | SCHEMA.sql drift guard | api | S | Add "regenerate SCHEMA.sql if a migration changed" to the release checklist, or a CI step that builds the service-container DB, dumps, and diffs (CI already has the Postgres). |
| S3 | Pin the "no tx across ClickUp HTTP" rule | api | S | One structural test or a doc comment in `clickup_copy` mirroring the PS rule. Audit found no violation today; this stops a future one. |

### Opportunistic (do it when you are in the file anyway)

| # | Item | Repo | Notes |
|---|---|---|---|
| S1 | Optional: a shared bounded helper for ClickUp fan-outs | api | Style unification only; behavior already bounded. Skip unless touching those files. |
| S2 | XLSX: build the 4 cluster `Format`s once | api | `dedup_xlsx_export.rs` constructs a new `Format` per data row; precompute one per `CLUSTER_COLORS` entry and reuse. Pure cleanup, output identical; measure before/after with `print_baseline`. |
| B1 | Tagger: avoid re-parsing stored docx bytes in report/apply | api | Wait for the in-flight tagger edits to land first. |
| B2 | Split big ClickUp modules (`clickup_connection.rs` 25 KB, `clickup_run_update.rs` 25 KB, `clickup_copy/bulk.rs`, `clickup_copy_db_tests.rs` 52 KB) | api | Per the standing split-mixed-concerns rule; tests file is the best first target. |
| B5 | Rust-own the remaining hand-written TS types (`UserSummary`, `CreateInviteRequest`, `SyncStatus`, tool-run `report_summary`) | both | Do when those APIs next change. |
| B6 | Measure frontend bundle once | ui | One-off `@next/bundle-analyzer` run (not installed); only split admin routes if the shell is heavy. Next 16 build no longer prints per-route JS. |

### Hygiene / ops

| # | Item | Notes |
|---|---|---|
| C-A | Put the load baseline table into `RUNBOOK.md` (or CHANGELOG) | Two paragraphs copied from the vault note so repo readers see the numbers. |
| C-B | `RUNBOOK.md:77` wording | Add that session state is durable in Postgres; the in-memory layer is only a per-process cache. |
| C-C | Tool-run retention policy | ~1.9 MB per dedup run (see load note); already tracked under [[project_cloud_move_triggers]]-type triggers. Decide before volume grows or before the cloud move. |
| C-D | Remote-DB sizing | With 20 ms RTT the pool (20 of 20 at 8 operators) saturates before CPU. Revisit pool size when the DB goes remote. |

### Explicitly not reopened

In-memory session cache (revocation correctness), manifest-driven permission middleware, shared AEAD core merge, dedup matcher micro-opts (C1-C4 measured), wholesale split of every 250-350-line UI file, facility `useAsyncResource`, `src/ai` placeholder, durable-session payload trim (B3) and facility over-fetch (B4) until a measured TTFB or hydrate problem shows up, migration squash (C5).

## Suggested order

1. S4 + S6 + S3 in one small api release (all hygiene, no behavior change).
2. S5 as one ui release.
3. Everything else only when touching the area.

Honest size: **two small releases**, not the 3-6 Grok guessed. The first pass already removed the systemic cost; most of Grok's Tier A was verifying work that is done.

## Update 2026-10-15 (shipped + a new finding)

Shipped: api v1.9.123 (XLSX cluster formats reused, one-pass CI DB tests, `check_schema_sql_fresh.sh` guard, ClickUp no-tx-across-HTTP rule documented, RUNBOOK wording) and ui v1.6.96 (workflow secret guard in both CI jobs). Done from the backlog: S2, S3, S4, S6, C-B, part of S5.

**New finding: the Playwright suite is broken, not just un-wired.** After installing Chromium in WSL (needs `libnspr4`/`libnss3`/`libasound2t64` fetched with `apt-get download` + `dpkg -x` into `~/pwlibs/root`, and `LD_LIBRARY_PATH=~/pwlibs/root/usr/lib/x86_64-linux-gnu`, because there is no sudo), all 11 specs fail. Cause: the specs still visit `/clients/{id}/unit-groups/...` etc., but the app moved those routes under `/clients/{id}/facilities/{facilityId}/...` and clients now come from the API, not `sessionStorage` (`seedClient`). `session-expired` just renders Next's 404. The suite was never in CI, so it rotted silently. Do NOT add a tag e2e job until the specs are repaired. Repair = update URLs + seeding/mocks in `e2e/helpers.ts` and the 6 spec files, then add the job and a login/TOTP spec. Treat as its own chunk (S5b).
