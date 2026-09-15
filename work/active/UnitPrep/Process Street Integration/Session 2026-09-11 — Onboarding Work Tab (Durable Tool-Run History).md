---
date: 2026-09-11
description: "New Onboarding Work tab on the facility page: a durable, queryable per-facility record of every tool run (Dedup first), replacing the audit-log-only trail with a real history the tab lists, paginates, and serves output/source downloads from. Found and fixed a real RLS bug along the way — output attachment silently affected zero rows."
tags: [work-note, unitprep, process-street, rls]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-11 — Onboarding Work Tab (Durable Tool-Run History)

> [!note] Reviewed and shipped, not live-narrated
> This feature was built in a separate session not captured in this note's own live context — reviewed line-by-line, verified against the real dev database, and organized into coherent commits by a follow-up session (2026-09-11) at Boris's explicit request ("that substantial work is yours, done in another session... review it, sort out coherent commits and push it"). Content below reflects what was actually reviewed and confirmed, not reconstructed guesswork.

## What shipped

`client_ops.tool_runs` — a real, queryable row per tool run (Dedup only for now; `tool` will grow `'unit_groups'`/`'template_tagger'` CHECK values once those tools get wired up the same way, not before). Deliberately distinct from `client_ops.audit_log`, which stays exactly as it was (a generic, facility-blind append-only event note fired on export): this table is what the new **Onboarding Work tab** on the facility page lists and joins against — created the moment a check succeeds, updated in place with output info once (if ever) the user exports.

`facility_id` is `NOT NULL`, deliberately stricter than the dedup export endpoints' previous loose, audit-only optional client id — the whole point of the feature is that a run can't exist unrelated to a facility. The source file's own bytes are stored alongside `source_dropbox_path` (not instead of it), since a Dropbox-sourced file can later be moved, renamed, or deleted out from under that path — the DB copy is the one reference that always still works. (Landed across two migrations: `20260910120000` created the table without this pair of columns, `20260910130000` added `source_bytes`/`source_content_type` immediately after — both confirmed applied and consistent with the live schema at review time.)

Frontend: new tab reusing the existing `useInfiniteLogFeed` pagination hook (the same one Security Logs/Activity Logs already share, from [[Session 2026-09-09 — Security & Activity Logs Page Split (DRY Pagination Refactor)]]) — now its third real caller. Each run shows its ordinal ("1st Duplicate Check"), who ran it and when, its source file (downloadable straight from the DB), and its output (a download button, or an "Open in Dropbox" link, whichever the user chose at export time).

**Route restructuring bundled in**: Dedup/Unit Groups/Template Tagger moved from client-scoped (`/clients/{id}/dedup`) to facility-scoped (`/clients/{id}/facilities/{id}/dedup`) — every tool run is now recorded against a facility, so the URL says which one. `ClientTabs` dropped its old "Client Info" entry and renders no tab bar at all until a facility is selected, since the company page itself has nothing left for a tab to point at.

**Bundled bug fix**, found while wiring the completion screen's new "View in Onboarding Work" link: a Dropbox-only export (no local download ever clicked) previously left the user staring at the same Export Format panel with no completion state at all — only the download path used to flip it.

## Real bug found and fixed during review

`attach_output_bytes`/`attach_output_dropbox` (the two writers that fill in a run's output columns after export) originally ran their UPDATE against the raw connection pool with no RLS GUCs set. Postgres requires an updated row to satisfy **both** the UPDATE policy's USING clause and the table's own SELECT policy's USING clause — and `tool_runs_select_authenticated` depends on the `app.current_user_id` GUC. A bare `.execute(db)` never sets that GUC, so every UPDATE silently affected zero rows: a real check's row inserted fine (INSERT's policy is unconditional), but its later export never attached output, with no visible error anywhere (`execute()` returning `Ok` with `rows_affected() == 0` isn't an error). Fixed by moving both writers onto `begin_rls_transaction`, same as every other write in this codebase — confirmed via two `#[ignore]`d live-schema tests run directly against the real migrated dev database, not just a green default test run.

**Also found during review**: `api::tool_runs` (the read-side handler module) had zero tests at all — the one handler module in the whole codebase without at least permission/reaches-the-database smoke tests. Added 3, matching the established `empty_state()`/`test_user()` convention every other handler module already uses.

## Shipped

`unitprep-api` `v1.9.28` (`dae802a` + version bump) and `unitprep-ui` `v1.6.31` (`bfbc0e9` + version bump). 569 Rust tests (including the 2 live-schema regression tests, run explicitly against the real dev DB) and 415 vitest tests, both green; clippy/tsc/eslint clean.

## Related

[[Session 2026-09-09 — Security & Activity Logs Page Split (DRY Pagination Refactor)]] — `useInfiniteLogFeed`, now reused a third time here.
[[Gotchas#Never hold a database transaction open across a live external API call|Never hold a database transaction open across a live external API call]] and the RLS `FOR UPDATE` gotcha — same family of "RLS enforcement is invisible until you hit real Postgres" bug as this session's own `attach_output_*` fix.
