---
date: 2026-09-22
description: "Per-client Re-sync button refreshed company/facility fields from Process Street but never rebuilt ps_person_index, so a person added to PS after import never became an Add User candidate no matter how many times Re-sync was clicked. Fixed in unitprep-api; also caught a stale local release binary masking the fix on first verification."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-22 — Re-sync Never Refreshed ps_person_index (Users Tab Candidates Went Stale)

## Context

Real bug report against a live client: Boris added a new Manager-level user on Main Street Storage's Corp/Facility Info step in Process Street, clicked "Re-sync" on the facility's own OO page, and the new person never showed up.

## What was actually wrong

Two separate code paths write PS-sourced data into OO, and only one of them ever touched people:

- **Scheduled sync / "Sync Now"** (`clients::sync::orchestrator::sync_one_run`) — rebuilds `clients.ps_person_index` (delete-then-insert) for every intake run it processes, on the normal delta-check schedule.
- **Per-client "Re-sync" button** (`api::clients_resync::apply_resync`) — a separate, purpose-built endpoint (2026-09-02) that re-fetches the company's + each facility's own PS run right now and refreshes `clients.companies`/`clients.facilities` row fields via `apply_company_refresh`/`apply_facility_refresh`. It never wrote to `ps_person_index` at all, despite its own module doc claiming a full re-pull "from Process Street right now."

The Users tab's "Add User" candidate chips (`api::clients_facility_people::get_facility_people`) are sourced entirely from `ps_person_index`. So a person added to PS after a facility was already imported into OO would never appear as a candidate via the Re-sync button — only the separate background/Sync-Now path ever refreshed that table. This is not the same bug as the roster (`clients.facility_people`) staying human-gated — that part of the design is deliberate and correct (see `api::clients_facility_people`'s own module doc: roster changes need a click). The actual gap was narrower: the candidate list itself was silently stale under this one specific button.

## The fix

`apply_resync` now also extracts people (`clients::person_index::extract_intake_people`, the same projection the background sync already uses) from the same PS fields it was already fetching for the field-refresh comparison, and rebuilds `ps_person_index` per run — same delete-then-insert shape as `sync_one_run`. `run_name` (`NOT NULL`) is pulled from the existing `ps_sync_state` row when one exists, falling back to the entity's own current name otherwise (no run-listing API call available at this call site to get it fresh).

Shipped: `unitprep-api` commit `afa95ae` ("Refresh ps_person_index during per-client Re-sync"), scoped to `src/api/clients_resync.rs` only. 615 tests green, clippy clean on the touched file. Left other pre-existing WIP in the working tree (`process_street_settings.rs`, `vendor_format.rs`, `orchestrator.rs`, a new daily-schedule migration pair) untouched and uncommitted at Boris's explicit direction — that's separate in-flight work from an earlier session.

## Verification gotcha: the running dev server was stale

First live retest after the fix still failed — the person still didn't show up. Root cause wasn't the code: the locally running `unitprep-api` binary (`target/release/unitprep`, WSL, port 8080, no systemd/supervisor — just a `cargo run --release` left in a terminal tab) had been built **2026-09-21 13:55**, well before the fix landed at **2026-09-22 10:32**. The dev server the browser was actually hitting had never seen the new code.

Rebuilt (`cargo build --release`) and restarted (killed the stale PID, launched fresh detached with output to `/tmp/unitprep-api.log`). Worth remembering as a standing check before declaring any backend fix "still broken": confirm the *running* binary's build time is actually after the fix's commit time, not just that the fix compiled and passed tests. This environment has no auto-restart on rebuild.

## Tangent: slow-statement WARNs, not investigated further here

Boris also asked about `sqlx::query: slow statement` WARN lines for trivially cheap queries (`SET config`, a PK lookup) taking 200–580ms, seen right after this fix's retest. Traced to `db.rs`'s `connect_lazy_with` pool (no `min_connections`) against Neon's pooled endpoint, following a ~13-minute gap with no DB traffic — consistent with the pool reaping idle connections and/or Neon's own compute auto-suspend, so the first queries in the next burst pay a one-time reconnect cost. Not a regression from this session's fix, and explicitly **not chased further here** since a separate, concurrent session is already working Neon compute-consumption root cause — see [[Session 2026-09-21–22 — Neon Compute-Usage Root Cause & Login-Stuck-After-Idle Fix]]. Also saw one duplicate back-to-back `GET .../tool-runs` request pair (~800ms apart), consistent with Next.js dev Strict Mode double-invoking effects — dev-only, not a real duplicate-fetch bug.

## Related

[[Process Street Integration — Kickoff & Findings]]
[[Session 2026-09-10 — Developer Role, Merchant Account Nickname Fix, Elavon Resync Redesign & Session Timeout Fix]] — the same `clients_resync.rs`/Re-sync surface, different redesign (Elavon tab).
[[Session 2026-09-21–22 — Neon Compute-Usage Root Cause & Login-Stuck-After-Idle Fix]] — the slow-query tangent's real owner.
[[Gotchas#The application's own Postgres connection pool can be the bottleneck, not Neon or its pooler|Gotchas — the app's own pool can be the bottleneck]] — same family as the slow-statement tangent above.
