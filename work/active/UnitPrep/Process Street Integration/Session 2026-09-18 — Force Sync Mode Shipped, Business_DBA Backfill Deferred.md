---
date: 2026-09-18
description: "Verified and shipped the Business_DBA correlation signal (from 2026-09-17) plus a new force-sync mode that can bypass the delta check on manual syncs. Boris explicitly decided not to run the ~363-run historical backfill this mode enables. Also fixed Main Street Storage's wrong Elavon link via the app's own Unlink/Link Manually flow -- no code or SQL needed."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-18 — Force Sync Mode Shipped, Business_DBA Backfill Deferred

## Context

Continuation of [[Session 2026-09-17 — Merchant Account Correlation, Business_DBA Signal & Two Live Data Bugs]]. That session's `business_dba` correlation signal was code-complete but uncommitted, and had one open item: the new column is `null` for every already-indexed `ps_sync_state` merchant_account row (~363 of them) until each one's `ps_updated_at` moves on its own, since the delta-check sync has no way to force a re-fetch of unchanged runs.

## Shipped: a force mode for the manual sync trigger

`unitprep-api`: `force: bool` threaded through `sync_runs_within` → `run_all_workflows_with_progress` → the `start_sync` handler (`?force=true` query param, defaults to `false`). When forced, every run in every workflow is treated as never-synced-before, bypassing `needs_refresh` entirely. The nightly background task always passes `force: false` explicitly -- forcing stays a deliberate, occasional manual action, never automatic. Real Process Street API cost (see [[Gotchas#Process Street's real API rate limit is undocumented publicly, but the live headers reveal it_ 2,500 requests/API-key/hour|the rate-limit gotcha]]) -- this is exactly the cost the delta check exists to avoid, so forcing pays it back in full.

`unitprep-ui`: a separate "Force Full Resync…" button next to the existing "Sync Now" on the search page, gated behind a `window.confirm` warning about the API cost so it can't be triggered by accident or muscle memory next to the cheap default.

Verified before shipping: backend `cargo test` (605 passed), `cargo clippy --all-targets` (clean, only 3 pre-existing unrelated warnings), frontend `tsc --noEmit`, `eslint`, and the full vitest suite (439 passed). Couldn't click through the UI live -- login is passkey-only (Windows Hello), which browser automation can't satisfy.

## Decision: not running the backfill

Boris's call, explicit: don't run the ~363-run historical backfill this force mode was built to enable. **Why:** OO is currently properly organized and working; spending a meaningful fraction of the shared 2,500/hour PS API budget on a backfill isn't worth it against no active problem. **How to apply:** leave `business_dba` `null` on old rows as-is. Don't revisit this until the missing-signal issue (a real Merchant Account run invisible to correlation because it lacks both a useful parenthetical *and* has already synced before this signal existed) actually resurfaces on a real client -- at that point, either a targeted resync of that one run or the full `?force=true` pass are both already available, no new code needed.

## Fixed: Main Street Storage's wrong Elavon link

Main Street Storage (facility under company "MSS Jenks, LLC", `01a08c8e-5a92-7850-bd73-da1b7ec91569`) was showing Dubuqueland Mini Storage's own rate/parties/EIN/bank/credentials as its own, via a stale `facility_merchant_accounts` row pointing at Dubuqueland's `(Main)` run (`swSvLUdhV9zhe9sAludIHw`) -- the leftover from the pre-fix "Main" false-positive incident, see [[Session 2026-09-17 — Merchant Account Correlation, Business_DBA Signal & Two Live Data Bugs]].

Fixed entirely through the app's existing Elavon-tab controls, driven live in Boris's own already-authenticated Chrome session (no login step needed, no code changes, no raw SQL):
1. Elavon tab → **Unlink** → confirmed "Yes, unlink" (`DELETE /clients/{companyId}/{facilityId}/elavon/link`) -- clears `facility_merchant_accounts`, `facility_merchant_account_parties`, and `ps_task_status` (workflow='merchant_account') for this facility in one transaction.
2. Entered Main Street Storage's own real run id (`ij83agH69Jmz6qEyzkBDyg`) in "Link Manually" → **Link** (`POST .../elavon/link`) -- fetched fresh from Process Street and re-ingested.

Verified visually: Process Street Run ID now reads `ij83agH69Jmz6qEyzkBDyg`; QMS/pinpad credentials changed to Main Street Storage's own values (previously Dubuqueland's); Financials and Owner(s)/Signer now show blank/"None on file" rather than Dubuqueland's real EIN/bank/owner data -- consistent with this being a distinct, separately-filled application, not a data-loss regression.

## Shipped versions

- `unitprep-api`: `v1.9.32` -- `7f099aa` (Business_DBA signal), `882a126` (force mode), `0db1dd0` (version bump). Pushed to `origin/main`.
- `unitprep-ui`: `v1.6.35` -- `5001afa` (Force Full Resync control), `c05d9d8` (version bump). Pushed to `origin/main`.

## Still open

1. The cross-run-disagreement gap (two signals pointing at different intake runs both resolve `Unambiguous`) -- a real design question, not urgent, not fixed.
2. Owner phone/address as a third corroborating signal -- not built, deferred.

## Related

[[Session 2026-09-17 — Merchant Account Correlation, Business_DBA Signal & Two Live Data Bugs]] -- the investigation and design work this session shipped.
[[Gotchas#Process Street's real API rate limit is undocumented publicly, but the live headers reveal it_ 2,500 requests/API-key/hour|PS rate-limit gotcha]] -- the cost this decision was weighed against.
