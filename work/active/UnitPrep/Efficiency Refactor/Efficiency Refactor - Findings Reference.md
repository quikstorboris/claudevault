---
date: 2026-10-05
description: "Evidence base for the Efficiency Refactor: the full 25-item prioritized findings list from the 2026-10-05 audit (5 reviewers), with file:line pointers, what was spot-checked, and what is unverified."
tags: [work-note, unitprep, efficiency, refactor, reference]
status: active
quarter: Q4-2026
project: unitprep
---

# Efficiency Refactor - Findings Reference

The original audit output, kept so chunk work can start from evidence rather than re-scanning. The actionable breakdown is in [[Efficiency Refactor - Master Plan and Progress]] (chunk specs repeat the key file:line pointers); risk analysis is in [[Efficiency Refactor - Decisions and Investigations]].

**Method and limits.** Five parallel read-only reviewers on 2026-10-05 (backend structure, backend runtime performance, backend dead code + deps, auth/DB, frontend), repos at `unitprep-api` v1.9.61 (clean tree) and `unitprep-ui`. Static analysis only: no cargo, no npm, no profiler. "Unused" claims are textual greps (`git grep`), not compiler-verified. Line numbers are approximate where the reviewer only grepped. **Re-verify each pointer when you start its chunk.**

**Spot-checked by the main session (confirmed):** `resolve_session` UPDATE on every call; `begin_rls_transaction` = BEGIN + 2 `set_config`; `spawn_blocking` appears twice; `Client::new()` at `dropbox/client.rs:133` and `process_street/client.rs:128`; `clients/ingest.rs` has no live callers (doc comments + `pub mod` only); nine module-level `#![allow(dead_code)]` in `src/clients/`; no index on `ps_intake_run_id` / `ps_new_merchant_run_id`.

**Baseline sizes.** Backend: 267 `.rs` files, ~85k lines; 60 non-test files >= 400 lines (including inline tests). ~45 functions >= 100 lines. 121 route entries. ~180-200 migration files (~100 pairs). Frontend: 162 non-test tsx files; only 3 source files > 400 lines; 22 raw fetch sites; 44 memo/callback uses.

## The 25 findings (priority order as presented) and where they live in the plan

| # | Finding | Impact | Chunk(s) |
|---|---|---|---|
| 1 | `resolve_session` writes `last_seen_at` every request | High | A1 |
| 2 | RLS setup = 3 round trips (195 call sites) | High | A1 |
| 3 | No timeouts/retries (PS, Dropbox); ClickUp client rebuilt per call; Dropbox mutex across refresh; PS logs full body | High | A2 |
| 4 | CPU-heavy work on async workers | High | A4, A5, A6 |
| 5 | Missing indexes | Med | A3 |
| 6 | `clients_detail` fan-out (10 RLS txs, ~50 round trips) | High | B1 |
| 7 | Transactions held open across PS HTTP | High | B2, B3 |
| 8 | Dedup O(n x groups), repeated grouping, many clones | High | C0-C4 |
| 9 | Session persistence cost/ordering | Med | A6, B5 |
| 10 | `/dedup/check` heavy inline work | Med | B6 |
| 11 | Sequential work that could be parallel | Med | B4 |
| 12 | No response compression | Low-Med | A7 |
| 13 | `build()` 1,197 lines, `main()` 397 | Med | D3a, D3b |
| 14 | Handler boilerplate (RLS tx, gate, ApiError) | High payoff | D2a-d |
| 15 | Copy-pasted helpers | Med | D1 |
| 16 | Backend god files | Med | D4a-i |
| 17 | Duplicated subsystems (AEAD x3, integration settings, dedup/tagger session IO) | Med | D5a-c, D4c |
| 18 | Frontend wrappers/dupes/perf | Med | F1-F9 |
| 19 | Stale `allow(dead_code)` + dead modules | Med | E1 |
| 20 | detect-vendor routes | Med | E2 |
| 21 | DB redundant indexes/unused objects | Low | E3 |
| 22 | Dropbox `has_more` ignored (functional bug) | Med | E4 |
| 23 | Workspace dependency hygiene | Low-Med | E5 |
| 24 | Stale files | Low | E6 |
| 25 | Frontend dead code | Low | E7 |

Details for items 1-25 with pointers are in each chunk's specification in the master plan. Additional material that did not fit a chunk, preserved here:

## Backend - extra evidence

**Per-request round trips.** resolve_session (1) -> BEGIN (1) -> `set_config` x2 (2) -> handler queries -> COMMIT (1); rejected session adds `check_session_expired` (~`authenticated_user.rs:258`); write handlers add one inline pooled `audit_log::record` (56 call sites: `src/client_ops/audit_log.rs:205`, `src/auth/audit_log.rs:378`). `begin_owner_rls_transaction` (~`:454-490`) = BEGIN + 1 `set_config`; `/health/whoami` (`health.rs:~100-130`) uses it.

**RLS policy cost (low; no per-row subqueries).** All policies are GUC-based; `auth.current_user_has_role()` is `STABLE sql` over `string_to_array(current_setting(...))` (`20260806120000_add_roles_permissions_tables.up.sql:70-78`); ~88 `CREATE POLICY` across 26 files. Improvements (optional, E3): initplan wrap `(SELECT auth.current_user_has_role('admin'))`; reuse `auth.current_user_is_client_ops_role()` (`20260909170000_add_developer_role.up.sql:49`) in older policies (`'onboarding_manager'` ~10x and `'department_manager'` ~9x repeated); `auth.is_authenticated()` for the repeated `NULLIF(current_setting('app.current_user_id', true),'') IS NOT NULL` (11+). Check legacy singular GUC `app.current_user_role` (migrations `20260721200546`, `20260721202617`; four old `current_setting('app.current_user_role', true) = 'admin'` occurrences - confirm migrated).

**Indexes.** `sessions.token_hash` UNIQUE (good); `user_roles` has an index on `role_id`, `user_id` presumably covered by PK/unique (unconfirmed); audit logs have actor/target/created_at indexes; `event_type` filter alone is a scan (low). `ps_person_index` has btree on `lower(full_name)`, `lower(email)` (migration `20260831140000:60-61`) that cannot serve `ILIKE '%q%'` (`clients_search.rs:~447`; `clients_companies.rs:189-222` hits 5+ facility columns, `facility_people`, `people`); no `pg_trgm` extension anywhere (only `citext` is created; migration comment at `20260831140000:57` records the deferral).

**Startup.** `main.rs:~150-250`: Dropbox `from_db` (config decrypt), PS `from_db`, three `initial_cache` loads (unit vendors, tenant vendors, tenant file meta) are serial; Dropbox/PS config is fixed at boot (saved settings change needs restart per comment at `main.rs:~170`) while the PS sync interval is live - `ArcSwap`/`RwLock` would allow live reload (optional idea). Migrations are not run at app start (only the `bootstrap-admin` subcommand).

**PS data caching (low-med).** Every client search/preview/resync fetches PS runs and form fields live; only caches are the per-company `ResyncPreviewCache` and the `ps_person_index` sync. `list_workflows` is dead. A 30-60 s TTL cache keyed by (workflow, name query), or answering facility-name search from local `ps_sync_state`, would cut live calls. `clickup/hierarchy.rs:102` caches per user with a TTL but never evicts old users (small unbounded growth).

**Robustness notes.** `.unwrap()/.expect()` are mostly test code; request-path ones: `CookieJar::from_request_parts(...).expect("infallible")` (`authenticated_user.rs:169`), `getrandom::fill(...).expect` (`auth/session_token.rs:12`, `auth/totp.rs:148,162`), rate-limit config `.expect()` at route build, CORS origin `.parse().unwrap()` on constants (`router/mod.rs:48-49`); `CatchPanicLayer` installed (`router/mod.rs:123`); `main.rs:421` `unwrap()` on serve; `db::connect()` panics if `DATABASE_URL` unset. `normalize_extraction_rejection_body` (`router/mod.rs:290`) calls `axum::body::to_bytes(body, usize::MAX)` on error responses only - cap at 64 KB. Handler `return` paths that skip explicit `rollback` rely on sqlx drop-rollback, which queues the rollback until the connection is reused. `tool_runs` list (`api/tool_runs.rs:~200-225`) windows `ROW_NUMBER()` over the whole facility+tool partition and selects `report_summary` JSONB before `LIMIT` (compute `sequence_number` after the limit if run counts grow); `auth.list_users_for_admin()` (`auth_users.rs:73`) and `GET /clients` (`clients_companies.rs`, `array_agg DISTINCT` + two `auth.staff_directory()` joins, no LIMIT) return everything - paginate if counts grow.

**Dedup-path facts for C-chunks.** `DedupSession` stores records + report (+ `stage` placeholder, never read); `with_owned_session` clones under the read lock; `build_report_view` -> `build_export_plan` -> `group_records` chain (3+ groupings per call); `dedup_export_plan.rs:~305 push_group_rows` boxes cloned records. Unit-group: `Arc<Vec<CsvDocument>>` in sessions; `apply_corrections` indexes corrections by unit already (fine); analysis caches per distinct group name (fine). Existing perf harness: `dedup/src/performance_tests.rs` and `src/api/slow_operation.rs` (`warn_if_slow`, WARN >2 s on dedup check/folder scan). A dev-profile `opt-level = 2` for dedup/core/unit-group/calamine/csv is in the root `Cargo.toml` (do not remove; add new hot-path crates to it).

**Dependency findings (E5).** See the E5 chunk; additionally `reqwest` appears as both dep and dev-dep (merge features or keep split deliberately).

**Repo hygiene facts (E6).** Untracked-but-present: `.env.local.bak`, `.env.local.bak2`, `.env.local.pre-prod-app-pw`, `CLAUDE-SECURITY-20260815-001808/` and `-20260817-150801/` (each with own `.gitignore`), `REFACTOR.md` (28 KB gitignored), empty `.sqlx/`, empty `examples/`. Tracked: `README.sample.md` (unreferenced), `SCHEMA.sql` (drifted), `RUNBOOK.md` + `docs/DOCKER.md` (unlinked), `scripts/prod_db_status.sh`, `scripts/prod_db_sync.sh` (no references), `dev-tools/`. The five other scripts are wired into CI or the pre-push hook. Assets in use: logo PNG by `src/infrastructure/audit_log_pdf/layout.rs`, `hero.svg` by both READMEs. No TODO/FIXME/HACK markers and no commented-out code blocks anywhere in `*.rs, *.sql, *.toml, *.yml, *.sh`.

## Frontend - extra evidence

Overall the UI is already disciplined (hooks extracted for big flows, 162 non-test tsx, 3 files > 400 lines). No `Regex`-type hot paths; polling is limited to `SyncButton` (self-stops on unmount; no visibility pause) and a 1 Hz elapsed ticker in `useAbortableOperation.ts:70-89` (fine). `app/(app)/layout.tsx` is a client layout (needs `useCurrentUser`); 30 of 31 `page.tsx` are client components; converting to server components is a large project with limited payoff because auth is cookie-based against a separate-origin API - only static content (field reference help) is a cheap server-component candidate. `next.config.ts` has no bundle analyzer, `images`, `compiler.removeConsole` or `optimizePackageImports`. Only one `<img>` (`TotpEnrollForm.tsx:167`, data-URL QR, correct as is). The facility page correctly runs `getFacilityDetail` + `getFacilityPolicies` with `Promise.all` (only 3 files use `Promise.all` at all); `CompanyDetailProvider` avoids refetching the company per facility. Facility `loadPolicies`/`loadFacility` are recreated each render and passed as `onSaved` to 5 tabs (harmless unless tabs get memoized). `lib/api.ts` has a misplaced doc comment (the "Extracts a human-readable message..." block sits above `describeFetchError` instead of `errorMessageFrom`).

## Out of scope / explicitly not planned
- In-memory session cache; `OnceLock` key cache (see Decisions).
- Server-side rendering conversion of the whole UI.
- Reviving the old detect-vendor endpoints.
- `src/ai/` placeholder (kept on purpose).
- Moving audit inserts into the request transaction / spawning them (raise with Boris if wanted).
