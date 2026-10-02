---
date: 2026-10-01
description: "Dedup now scans a whole folder by file headers, pre-selects the right file per PMS, and shows a Files required for deduplication panel; registry gained PMS, role, priority and guidance."
tags: [work-note, unitprep, dedup, vendor-format, design]
status: active
quarter: Q4-2026
project: unitprep
---

# Dedup Folder Scan and File Requirements

Status as of 2026-10-01: built, tested, **committed and pushed 2026-10-01** as `unitprep-api` `v1.9.54` (3 commits: `3ddb33f` the two vendor formats + transform split, `862c7cb` the folder scan, `7e750c3` version) and `unitprep-ui` `v1.6.52` (`632059d`, `e3415f8`); both preflights passed. Migration `20261001140000` **applied to the Neon dev DB** (prod DB branch NOT yet synced as of 2026-10-02: Boris approved the sync, but the permission classifier blocked the prod DB read, so it awaits his go-ahead in-tool or a manual run; the prod branch holds real data and has been behind since 2026-08-27, so far more than these four migrations are likely pending -- read each pending migration's SQL first). v1.9.56 CI (full suite) passed 2026-10-02; API restarted by Boris 2026-10-02; the Freeland leases export and Winsen/Sentinel sample are waiting on real data from Boris. The API caches the registry (4 h) and the dev server is a separate `cargo run`: restart it to pick up the new routes and rows. The UI container hot-reloads. **Not yet clicked through in a real browser** (see Verification).

Decisions from Boris, 2026-10-01: build folder scan + real multi-file selection together; local folders are scanned **by headers only** in the browser; guidance lives in data.

## What a user sees

Dedup page: pick a local folder (or files) or a Dropbox folder -> a checklist of every CSV/XLSX/XLS with a detected-format badge, Select all / none, the right file pre-ticked, alternatives noted -> a right-hand panel **Files required for deduplication** with a vendor selector (defaults to the detected PMS) listing each report, its role, and what it is for.

## Model (registry rows are file FORMATS)

`client_ops.vendor_format` gained: `pms` (the system), `report_name`, `file_role` (`primary` runs alone; `supporting` is recognized but not used alone yet), `selection_priority` (higher is pre-selected among a PMS's primaries), `guidance` (panel text). A "file role" is simply what job a file does for a system. Detection still takes the first matching row by id, so a format whose headers are a superset of another's must be registered first. The migration re-created two applied seed rows to get that order (it cannot edit applied migrations):

| Row | Why it exists |
|---|---|
| SiteLink Directory (prio 20) before SiteLink Rent Roll (prio 10) | Directory = Rent Roll headers + `TenantName`; Directory preferred, Rent Roll offered as the alternative |
| QuikStor Cloud Alternate Tenants (supporting) before QuikStor Cloud | AlternateTenants.csv has every Tenants.csv header plus its own |

Rules (`dedup/src/file_selection.rs`, pure logic): classify by headers (same case/separator-insensitive matching as ingest); pre-select the best primary of the best PMS; at run time refuse an unrecognized file, a supporting-only file, two files from different systems, two alternatives of one system (would count tenants twice), or the same format twice. Today exactly one primary file runs.

## API

`POST /dedup/classify-files` (name + headers only), `POST /dedup/classify-dropbox-folder` (server downloads each file transiently, reads headers, keeps nothing), `GET /dedup/file-requirements`, `POST /dedup/check` (multipart, many `file` parts), `POST /dedup/import-dropbox` (`paths`; legacy `path` still accepted). New `tenant_file_meta` snapshot in `AppState` (a separate cache, because adding fields to `VendorFormat` would change what Group Prep persists in its durable sessions).

## What this does NOT do yet

- **No joins.** Nothing can combine files. Freeland (QuikStor Cloud) still has no unit numbers: it needs a leases export linking tenants to units. When one exists: add its format as a new role, a join step before `report::run`, and a child table for multi-file run sources.
- **Run history is single-source.** `client_ops.tool_runs` keeps one source file per run (`source_bytes` = the whole original file). Fine while one file runs; needs a child table once several can.
- Admin UI for editing guidance does not exist (the permission exists, no routes/UI): guidance changes by migration for now.
- A first check of cell references: they point into the **exported report's** rows (`field_cell_refs` in `dedup_export_plan`), not the source files, so multi-file does not affect them. (An earlier worry that it would was wrong.)

## Decision (2026-10-02): store the raw source file, no redaction

Boris: **no need to redact; the raw file is fine.** Where it lives: `client_ops.tool_runs.source_bytes` (plain `BYTEA`, with `source_content_type`/`source_file_name`), migration `20260910130000`. **Not encrypted by the app** (unlike TOTP secrets, Dropbox/Process Street credentials and Merchant Account PII, which use ChaCha20-Poly1305); protection is Neon's own storage encryption (provider-level, not verified from this repo -- TBC) plus Postgres RLS. RLS `tool_runs_select_authenticated` lets **any signed-in user** read it, and `GET .../tool-runs/{id}/source` has no permission check beyond being signed in and the facility belonging to the company (`src/api/tool_runs.rs`); only DELETE needs `client_ops.perform`. So a stored SiteLink Directory (card ciphertext, tokens, gate codes, an SSN) is downloadable by every OO user. Offered follow-up, not done: gate the source download behind `client_ops.perform` (or `integrations.manage`) and/or encrypt `source_bytes` with the existing ChaCha20-Poly1305 helpers.

## Earlier framing of the question (now decided)

`tool_runs.source_bytes` stores the **entire original upload** in the OO database. A SiteLink Directory carries `sCreditCardNum` ciphertext, card tokens, gate/access codes, and an SSN (1 row on LG2). Boris: card numbers and SSNs are **not needed in the OO DB**; some analysis of them may be worthwhile later; he is still learning what QMS can use, so **leave it for now**. Options when picked up: redact sensitive columns before storing the source (CSV easy, XLSX needs a rewrite), store a redacted CSV copy, or store headers + Dropbox path only for files that contain such columns. Header-only scanning already keeps unselected files (e.g. Credit Card Roll) off the server for local folders; the selected file is still uploaded and stored whole. See also the `sitelink-migration-analysis` skill.

## Performance finding, 2026-10-01 (not Docker)

Boris saw the dedup check take ~9 s (was under 1 s) after moving to Docker, and the folder scan take seconds. Measured, not guessed: the same code natively in WSL took 8.7 s, against 9.2 s in the Docker log, so **Docker was not the cause** (the container has all 22 cores, no CPU limit).

- **Analysis (CPU):** the typo-variant pass compared every pair of groups (759 rows -> 597 groups -> ~178k pairs), rebuilding each name and running two Ratcliff/Obershelp matches with hash maps per pair. 8.5 s of the 8.7 s, in a **debug** build (a release build does it in 0.84 s; `cargo run` in the dev container is debug). Fixed in `dedup/src/similarity.rs` by preparing each name once and skipping any pair whose sorted-character-multiset upper bound is under the 0.85 threshold, which is exact (the matched total can never exceed the multiset intersection). A test compares the pruned pass to the unpruned loop pair-for-pair. Result: 8.74 s -> 91 ms in the same debug build, identical findings.
- **Dropbox folder scan (network):** the server downloaded each file one after another at ~0.4 s each (8 files ~ 4 s). Now six at a time, order preserved (`DROPBOX_SCAN_CONCURRENCY`).
- **Left alone:** the Neon round trips (`set_config` 240 ms, durable-session insert 375 ms, `tool_runs` insert 290 ms) are database latency from this machine, independent of Docker; the run re-downloads the chosen file (~0.4 s) rather than caching scanned bytes (would retain client data in memory).
- **Guards (v1.9.56):** a budgeted speed test over a synthetic facility, a 2 s slow-operation WARN log, dev-profile optimization of the hot-path crates, and a repo `CLAUDE.md` rule. See [[Gotchas]].
- Takeaway for later: any O(n^2) pass over tenants is a debug-build hazard; the dev server being a debug build makes it ~10x worse than production.

## Verification

- `cargo test --workspace`: 681 pass; `clippy -D warnings` clean. New: 13 selection-rule tests, 6 session-level selection tests, 5 endpoint tests, and a DB-backed test (`the_seeded_registry_classifies_real_export_headers`, added to the CI allowlist) that runs the whole migration chain on a throwaway Postgres and classifies real QSX / QuikStor Cloud / SiteLink header shapes.
- UI: `tsc`, `eslint`, full `vitest` (724), `npm audit` (0) all clean; one new dependency, `fflate` (xlsx header reading in the browser).
- Real-file check: the UI's actual readers over the LG2 folder (36 reports, Directory's 409 headers read correctly) and the Freeland folder (17 files), classified by the Rust rules against the seeded registry: Directory pre-selected over Rent Roll; `Tenants.csv` pre-selected, `AlternateTenants.csv` supporting, everything else ignored.
- Not done: a click-through of the real page against a running API (needs a signed-in session), and Playwright.

## Related

- [[SiteLink Tenants Vendor Format (Dedup)]]
- [[QuikStor Cloud Tenants Vendor Format (Dedup)]]
- [[Shared Vendor-Format Registry (Easy Storage Solutions)]]
- [[Dedup Tool Index]]
