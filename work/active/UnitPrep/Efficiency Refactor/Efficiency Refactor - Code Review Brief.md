---
date: 2026-10-09
description: "Self-contained, LLM-friendly brief of the 2026-10 UnitPrep efficiency refactor (49 delivered tasks across api v1.9.62-1.9.117 and ui v1.6.56-1.6.92) for a third-party code review: scope, task catalog, behavior changes, evidence, review focus."
tags: [work-note, unitprep, efficiency, refactor, code-review]
status: completed
quarter: Q4-2026
project: unitprep
---

# UnitPrep efficiency refactor - code review brief

**Audience:** an external reviewer (human or LLM) with NO prior context. This document is self-contained. Companion notes inside the owner's vault (not needed to read this): [[Efficiency Refactor - Master Plan and Progress]], [[Efficiency Refactor - Session Log]], [[Efficiency Refactor - G1 Log Audit]].

**Period:** 2026-10-05 to 2026-10-09. **Outcome:** every planned task delivered or deliberately closed; all work pushed to `main` with per-release tags.

---

## 0. How to use this document

1. Read section 1 (system context) and section 2 (scope boundary) first. The commit ranges also contain work that is NOT part of this refactor (section 2.2) - do not attribute it to the refactor.
2. Section 4 is the task catalog (one row per task: id, release, what, where, how verified, review risk).
3. Section 5 lists every deliberate **behavior change** (the refactor otherwise claims "no behavior change"). Review these hardest.
4. Section 6 lists security-relevant changes. Section 8 lists suggested review questions.
5. Every task shipped as one feature commit plus one `Bump version to X` commit plus a lightweight tag, with a CHANGELOG entry that states what changed, what was measured and what was deliberately not done. `git log --oneline <range>` and `CHANGELOG.md` in each repo are the primary evidence trail.

## 1. System context

UnitPrep ("Onboarding Orchestrator") is an internal web app for a self-storage software company's onboarding team: it imports client/facility data from Process Street, runs data-quality tools (tenant duplicate check, unit-group analysis, Word-template tagging), and integrates Dropbox and ClickUp.

| | Repo `unitprep-api` | Repo `unitprep-ui` |
|---|---|---|
| Stack | Rust workspace (axum, sqlx/Postgres on Neon, tokio, reqwest, tower-http, ts-rs). Crates: root `unitprep` (binary), `unitprep-dedup`, `core`, `unit-group`, `tagger-pipeline`, `template-tagger`, `docx-surgeon` | Next.js 16 / React 19 / TypeScript, Vitest, ESLint |
| Size | ~81k lines of Rust | ~130 test files |
| Auth model | Passkey (WebAuthn) login only; TOTP is a step-up factor; cookie sessions in `auth.sessions`; Postgres row-level security (RLS) enforced per request by setting `app.current_user_id` / `app.current_user_roles` inside a transaction | Cookie-based, `whoAmI` provider |
| Gate before every push | `scripts/preflight.sh` (9 steps: fmt, `clippy -D warnings`, workspace tests, cargo-audit, gitleaks, secret-pattern scan, version/tag consistency, workflow-secret guard, ts-rs drift check) - a pre-push hook | same idea: `tsc`, `eslint`, `vitest`, `npm audit`, gitleaks, ts-rs drift check |

Conventions that matter for review: RLS is a second, independent enforcement layer behind handler-level permission checks; real-DB tests are `#[ignore]`d and named `*_db_*` (run with `cargo test --bin unitprep -- --ignored db`); one release = feature commit + version-bump commit + tag; CHANGELOG entries are mandatory.

## 2. Scope boundary

### 2.1 In scope: the refactor
An audit on 2026-10-05 (five read-only reviewers over api v1.9.61 and ui v1.6.5x, plus three targeted risk investigations) produced 25 findings; all were approved with dispositions. They became a 36-chunk plan (phases A-G), executed 2026-10-05 to 2026-10-09 with additions and end-of-refactor tasks.

### 2.2 Same commit ranges, NOT part of this refactor (do not review as such)
- ClickUp integration and ClickUp Copy (duplicate-check automation, bulk copy jobs, "every Onboarding Phase"): api 1.9.80, 1.9.92-1.9.95, 1.9.117; ui 1.6.60-1.6.67, 1.6.92. Migrations `20261005130000`, `...5140000`, `...7130000`, `...7140000`.
- Process Street task-roles / hidden-tasks work (api 1.9.84, ui 1.6.61), migration `20261006120000`.
- "Implementation Completed" feature (api 1.9.87, ui 1.6.63), migration `20261007120000`.
- QuikStor Cloud header formats (api 1.9.94), migration `20261007150000`.

### 2.3 Ranges
| | From | To | Commits (incl. version bumps) | Diff |
|---|---|---|---|---|
| `unitprep-api` | tag `v1.9.61` (pre-audit baseline) | tag `v1.9.117` | 116 (61 non-bump) | 303 files, +36,339 / -19,526 (includes the 2.2 work) |
| `unitprep-ui` | tag `v1.6.55` | tag `v1.6.92` | 75 | 293 files, +15,256 / -5,088 (includes the 2.2 work) |

Refactor-owned database migrations (3, all reversible, applied to dev and prod): `20261005100000_throttle_session_last_seen_bump`, `20261005110000_index_process_street_run_id_columns`, `20261005120000_drop_redundant_single_column_indexes`. Dev and prod are at the same migration state (110 migrations, identical checksum hash).

## 3. Summary at a glance

**49 tasks delivered.** The original plan listed 36 chunks; 8 of those were deliberately closed after analysis (B1b, B5, B6, C1-C4, D5c; D2d was delivered in reduced form), and the work grew with additions (A4b, A6b, the six F7 generated-type domains, G1a/G1b, and the end-of-refactor items). Breakdown of the 49: 9 hot-path performance (phase A), 4 query/transaction restructuring (B), 1 benchmark baseline (C0), 18 backend structure/consolidation (D), 7 cleanup (E), 9 frontend (F; F7 itself spans six generated-type domains), 1 log/observability audit (G1, two releases). The end-of-refactor items (prod migrations, TOTP step-up UI, dev-tooling fix) are listed separately after the catalog.

Headline results (all measured; method in section 7):
- **Session lookup** `resolve_session`: 10.8k -> 37.4k calls/s; average 0.74 -> 0.21 ms; session-row writes under load 86,650 -> 0.
- **Handler transaction latency** at 20 ms DB round-trip: 105.5 -> 84.2 ms (pool ping-on-acquire removed).
- **Process Street run-id lookup** (30 ids over 200k rows): 26.96 -> 0.31 ms (~88x) via partial indexes.
- **Server startup** (through a 20 ms latency proxy): 0.63-0.72 s -> 0.32-0.35 s.
- **Resync person-index rewrite**: about 70 round trips -> 2 for a ten-run company.
- **Structure**: `routes.rs::build()` 1,197 lines and `main()` 397 lines split; ~15 god files in each repo split; ~100 hand-written TS types replaced by ts-rs output guarded by a CI drift check (100 generated files).
- **Correctness bugs found along the way**: Dropbox `list_folder` silently ignored `has_more` (truncated results); a facility-page refresh race; hand-written TS `FieldName` listed two values the backend never sends.
- **Audit gaps closed**: admin edits of integration settings, activity-log exports and the `bootstrap-admin` CLI previously left no audit row.
- **A real lock-out bug fixed**: the login-time TOTP step-up flow had no UI, so an enrolled account signing in from an unseen browser+network got an app where every request returned 403.

Test totals at the end: ~1,350 hermetic Rust tests across the workspace, 106 real-DB tests (`-- --ignored db`), 1,032 Vitest tests in 131 files. Every release passed the 9-step preflight on a clean checkout.

## 4. Task catalog

Legend for "Risk": **L** low (mechanical/behavior-preserving, covered by pre-existing tests), **M** medium (touches concurrency, SQL, auth-adjacent or many call sites), **H** high (security/identity/DB semantics - review first). "Verified by" names the safety net actually used.

### Phase A - hot-path performance (api)
| ID | Release | What changed | Key files / entry points | Verified by | Risk |
|---|---|---|---|---|---|
| A1 | api 1.9.62 | `auth.resolve_session` no longer updates `last_seen_at` on every request: a read-only validity CTE plus a throttled bump CTE (`LEAST(60 s, 6 s per idle minute)`); `begin_rls_transaction` sets both RLS GUCs in ONE statement (was two). **No in-process session cache was added** (explicit decision: revocation must stay instant). | migration `20261005100000`, `src/auth/authenticated_user.rs`, `src/api/session_resolution_db_tests.rs` | 5 real-DB tests (throttle proven to FAIL against the old function), pgbench | **H** |
| A2 | 1.9.63 | Shared HTTP client policy `integrations::http`: connect 5 s / request 30 s timeouts, retry helper (3 tries, backoff+jitter, honours `Retry-After` up to 10 s, only connect errors/timeouts/429/5xx), body truncation in logs (512 B), one shared ClickUp client, Dropbox 401 -> refresh -> retry once, bounded token-refresh mutex hold. Uploads are NOT retried. | `src/integrations/http.rs`, `src/dropbox/client`, `src/process_street/client.rs`, `src/clickup/client.rs` | 11 loopback-server tests + mock-Dropbox tests | M |
| A3 | 1.9.64 | 3 partial indexes on Process Street run-id columns | migration `20261005110000` | EXPLAIN + timing on 200k rows | L |
| A4 | 1.9.66 | `spawn_blocking` (via `run_blocking`) for upload parsing, Dropbox import, dedup check, per-file header parse | `src/blocking.rs`, `src/api/blocking.rs` | existing handler tests + 3 `run_blocking` tests (single-thread runtime proves non-blocking; panic -> 500; tracing span follows) | M |
| A4b | 1.9.68 | same for Unit Groups session-lock compute (discover/select/resolve/upload/validate/analyze/export) | `src/api/blocking.rs` (`with_owned_session_mut_blocking`) | existing tests | M |
| A5 | 1.9.67 | same for dedup report/view/export generation | `src/api/dedup_blocking.rs` | existing tests | M |
| A6 | 1.9.69 | same for sealing (encrypting stored source/records) BEFORE opening the DB transaction | `create_dedup_run` | `tool_run_create_db_*` real-DB test | M |
| A6b | 1.9.115 | Template Tagger check/report/apply CPU steps on the blocking pool | `src/api/tagger/{recognize,report,apply}.rs` | 23 existing tagger tests unchanged | L |
| A7 | 1.9.65 | gzip response compression (`tower-http`), skipping ZIP/OOXML/PDF and already-encoded responses | `src/api/router/compression.rs` | real-router test; not measured over a network | L |

### Phase B - query/transaction restructuring (api)
| ID | Release | What changed | Verified by | Risk |
|---|---|---|---|---|
| B1a | 1.9.70 | Pool: removed sqlx ping-on-every-acquire (idle-gated), `acquire_timeout` 10 s. The audit's "single transaction" recommendation was investigated and found wrong for latency; this was the real win | `dev-tools/latency_proxy.py` measurement | M |
| B2 | 1.9.71 | `clients_resync` preview/apply: fetch Process Street FIRST, then a short transaction; person-index rebuild is one `DELETE ... ANY` + one `INSERT ... UNNEST` | new real-DB test written against the OLD loop first, passes unchanged after | **H** |
| B3 | 1.9.73 | Sync orchestrator: prefetch run fields concurrently, short batched write transactions, `UNNEST` inserts; per-run failures non-fatal | real-DB `sync_*` tests | **H** |
| B4 | 1.9.72 | `join_all_bounded` (max 6 concurrent upstream calls) replaces unbounded `join_all` at 8 fan-outs; parallel status listings/search/imports/startup loads | boot-time measurement; compiler gotcha documented | M |
Skipped by the owner after analysis: **B5** (session persistence coalescing) and **B6** (`/dedup/check` off the response path - would race with export's UPDATE).

### Phase C - dedup algorithms
| C0 | 1.9.83 | Baseline benchmarks at realistic size (800/2,400/5,000 rows, debug and release). Finding: dedup is already fast (5,000 rows: report ~140 ms, matched-by-name ~580 ms; the one slow stage is XLSX generation). **C1-C4 closed as not worth it.** | `src/api/dedup_pipeline_performance_tests.rs`, `dedup/src/performance_tests.rs` | L |

### Phase D - backend structure and consolidation
| ID | Release | What changed | Verified by | Risk |
|---|---|---|---|---|
| D1 | 1.9.81 | Deleted 12 copies of `request_context`, 7+3 not-configured responders, 6 `bad_request` copies; canonical helpers in `api/mod.rs` | grep proves zero leftovers; full suite | L |
| D2a | 1.9.102 | `api/rls.rs`: `begin_for` + `try_response!` replace 73 uniform RLS-transaction opening sites (-300 lines). Closure-style `with_rls_tx` was rejected (readability, commit-point control) | hermetic + 100/100 real-DB | M |
| D2b | 1.9.103 | `api::error_response(status, code, msg)` is the single constructor of `ApiErrorBody` (74 inline literals migrated). Handlers still return `Response` (hundreds of tests call them directly) | full suite | L |
| D2c | 1.9.103 | `api::paging::clamp_limit` (3 sites) | tests | L |
| D2d | 1.9.104 | REDUCED: `try_response!(user.require_permission(..))` on 69 sites (-110 lines). The manifest-driven permission-gate LAYER was closed (see section 9) | `permission_gate_tests` (every manifest route) | M |
| D3a | 1.9.85 | `routes.rs::build()` (1,197 lines) split into per-domain `router/routes/*.rs` | temporary test dumping `method path access` for all 136 routes before/after - sorted diff identical | M |
| D3b | 1.9.86 | `main()` (486 -> 21 lines) split into `startup/{cli,config,logging,state,tasks,serve}` | booted the real binary with `env -i` against the test DB (health, SIGTERM, port-in-use, `--help`) | M |
| D4a | 1.9.82 | Moved large inline test modules out (`*_tests.rs`) | test counts identical (804 / 77 ignored) | L |
| D4b | 1.9.88 | `clients_elavon.rs` 1,233 lines -> 8 files | normalized line-multiset diff vs original | L |
| D4c | 1.9.97, 1.9.100 | `dedup.rs` 988 and `tagger.rs` 947 lines split; shared `api/session_io.rs` (7 hand-built attachment responses, 3 identical save-location structs) | tests 849 -> 855 unchanged | L |
| D4d | 1.9.89 | `clients_resync.rs` -> 8 files; `apply_resync` 300 -> ~120 lines + `ApplyError` | tests | M |
| D4e | 1.9.90 | `clients_search.rs` -> 8 files; `search_clients` ~380 -> ~120; 9-param fn -> structs | tests + new real-DB `lookup::load` test | L |
| D4f | 1.9.91 | `clients_detail.rs` 942 -> company/facility/policies modules | tests | L |
| D4g | 1.9.95 (shipped inside another release) | `auth_register.rs` (1,102 lines) split, **tests first**: 6 real-DB characterization tests (mutation-checked) | real-DB | **H** (auth) |
| D4h | 1.9.98, 1.9.101 | `auth_invites`, `clients_facility_people`, `clients/repository` split; 5-tuple/6-tuple rows -> named structs; 4 long functions hand-split | 97 real-DB `db_` tests; bootstrap smoke-tested | M |
| D4i | 1.9.99 | `DropboxClient` private `rpc` helper (7 copies of request/response dance); orchestrator `schedule.rs`; `merchant_account_mapping` crypto split (AAD untouched); 6 new mock-Dropbox tests | tests | M |
| D5a | 1.9.106 | `ConfigSource` marker shared by the Dropbox and Process Street settings; generic settings skeleton deliberately NOT built | tests | L |
| D5b | 1.9.105 | Golden-vector ("known-answer") tests for the 3 encryption formats + negative tests + unified serial-lock names | tests | L (reduces risk) |

Tooling built for the splits: `carve_module.py` (splits `X.rs` into `X/` from a JSON segment list) and `fix_tests.py`, followed by `cargo fix`, `cargo fmt`, and a `clippy -D warnings` loop.

### Phase E - cleanup, dead code, hygiene
| ID | Release | What changed | Risk |
|---|---|---|---|
| E1 | api 1.9.74 | Deleted `clients::ingest` and `staff_resolution` (516 lines) and `list_workflows`; lifted 7 blanket `#![allow(dead_code)]` (compiler then found only 3 real cases) | L |
| E2 | api 1.9.75, ui 1.6.58 | Removed dead `POST /dedup/detect-vendor*` routes; classify responses gained `closest_vendor` and `missing_headers` ("looks like X, missing: ...") | M (API surface) |
| E3 | api 1.9.78 | Dropped 4 redundant single-column indexes (covered by UNIQUE composites); reversible | M (DB) |
| E4 | api 1.9.76 | **Bug fix**: Dropbox `list_folder` now follows `has_more` (was silently truncating) | M |
| E5 | api 1.9.77 | `[workspace.dependencies]` for 13 deps; Cargo.lock byte-identical; resolved feature graph verified identical via `cargo tree -e features` | L |
| E6 | api 1.9.79 | `SCHEMA.sql` regenerated (was 15 migrations behind) by new `scripts/regenerate_schema_sql.sh`; RUNBOOK/README docs; stale files removed (after zipping) | L |
| E7 | ui 1.6.58 | Dead frontend code removed; `@types/qrcode` to devDependencies | L |

### Phase F - frontend (`unitprep-ui`)
| ID | Release | What changed | Risk |
|---|---|---|---|
| F1 | 1.6.70 | One `lib/http.ts` (`apiRequest`, `ApiResult`) behind the five fetch wrappers. **Deliberate header-policy decision**: JSON `Content-Type` on every non-GET (forces a CORS preflight on bodyless POSTs, blocking cross-site form forgery); none on bodyless GET | **M** |
| F2 | 1.6.71 | `useLatestRequest` abort/stale-response guard; clients directory fetched lazily (provider fetches on first `useClients()`) | M |
| F3 | 1.6.62 | Lazy-load 9 facility tabs, `qrcode`, `fflate`, `OrchestratorLoader` (bundle size not measured) | L |
| F4 | 1.6.68 | Memoized 3 context provider values | L |
| F5 | 1.6.73 | Security/activity log export pages merged into one generic `LogExportPage` (590 -> ~130 lines + shared) | L |
| F6 | 1.6.72, 1.6.82, 1.6.89 | `useCopyToClipboard`, `formatDateTime`, `useAsyncResource`; facility page split into hook/tab bar/tab content; in-place refresh stale-response guard (bug fix, regression test fails without it) | L |
| F7 | api 1.9.107-1.9.116 / ui 1.6.83-1.6.90 | ts-rs generated types, six domains: dedup report views; Template Tagger; dedup file classification; facility+policy; company/people/Elavon; companies/resync/search/import/settings/auth. ~100 generated files guarded by CI drift check. Found real mismatches (see section 5) | M |
| F8 | 1.6.74-1.6.81 | God files split: `clientsDetail`, `DedupResultsPage`, `ElavonTab`, `DropboxFolderPicker`, `TaggerResultsPage`, `useDiscoveryFlow`, clients page, `fieldProvenance` (byte-identical JSON dump proves the data split) | L |
| F9 | 1.6.68 | `SyncButton` polling rewritten (self-scheduling, pauses when hidden, no overlap); `cancelSession` `keepalive` | L |

### Phase G - observability
| ID | Release | What changed | Risk |
|---|---|---|---|
| G1a | api 1.9.111, ui 1.6.86 | New security-trail event `integration_settings_updated` (admin edits to Dropbox settings, Process Street settings, task-role mappings: caller IP, what was set, only THAT a secret was replaced) and client-ops event `activity_log_exported`; 6 real-DB tests, mutation-checked, secrets proven absent from rows | **H** |
| G1b | api 1.9.112 | `bootstrap-admin` writes an `invite_created` row (no actor, `via: bootstrap_cli`); distinct "database connection pool exhausted" log; one `warn` when retries give up; `warn_if_slow` wired into 7 more handlers; redacted `Debug` on 4 secret-bearing request structs | M |

### End-of-refactor items
- **Prod migrations applied** 2026-10-09 (3 additive migrations); dev == prod.
- **TOTP step-up UI** (ui 1.6.91): `StepUpPrompt` + shell gate.
- **Dev-tooling fix** (api 1.9.108): the `api-dev` container's `cargo watch` (runs as root) wrote root-owned ts-rs output into the bind-mounted checkout, making later host `cargo test` runs fail with PermissionDenied; fixed by `TS_RS_EXPORT_DIR=/tmp/ts-bindings` in `docker-compose.yml`.
- **ts-rs features** `uuid-impl` + `chrono-impl` enabled workspace-wide (api 1.9.113).

## 5. Deliberate behavior changes (the refactor is otherwise behavior-preserving)

| # | Change | Where | Why / blast radius |
|---|---|---|---|
| 1 | Stored `last_seen_at` may lag real activity by up to the throttle (<= 60 s, never more). Idle expiry therefore can fire up to that much EARLY, never late. Revocation is still instant. | A1 | Removes a row lock + WAL write per request. Fails safe. |
| 2 | Upstream (Process Street, Dropbox, ClickUp) calls now time out and retry; Process Street retries consume its 2,500 req/hour budget (worst case 3x for a persistently failing endpoint). Dropbox uploads are not retried. | A2 | New failure modes become visible instead of hanging. |
| 3 | Responses are gzip-compressed (except ZIP/OOXML/PDF/already-encoded). | A7 | Redundant behind Cloudflare, harmless. |
| 4 | `create_dedup_run` seals source/records on the blocking pool BEFORE opening its transaction. | A6 | Frees a pooled connection during CPU work. |
| 5 | Pool `acquire_timeout` 10 s: exhaustion now surfaces as a handler error (and its own log line). | B1a | Was effectively unbounded waiting. |
| 6 | Resync apply builds its comparison BEFORE the write transaction; rows are a few seconds old at write time (same window the 5-minute preview cache always had). | B2 | Removes a transaction held across Process Street HTTP. |
| 7 | Sync orchestrator: a failed run no longer fails the whole sync; it is recorded and the rest continue. | B3 | Partial progress is kept. |
| 8 | `axum::serve(..).unwrap()` became log-and-`exit(1)`. | D3b | No panic backtrace on bind failure. |
| 9 | Removed `/dedup/detect-vendor*` routes (confirmed dead); classify responses gained two fields. | E2 | API surface change. |
| 10 | Dropbox `list_folder` follows pagination. | E4 | Bug fix; results that were silently cut off now appear. |
| 11 | UI JSON `Content-Type` header policy changed (see F1). | F1 | Tests that pinned the old differences were updated. |
| 12 | `clients` directory fetched on first `useClients()` instead of on every signed-in page. | F2 | Fewer requests. |
| 13 | Generated types are stricter than the hand-written ones they replaced: `duplicate_customer_records`, `unidentified`, `closest_vendor`, `missing_headers` are now required (the backend always sent them); two phantom `FieldName` values were removed. | F7 | Found by generating; UI code tolerant of old stored reports still compiles. |
| 14 | Four request/credential structs print `<redacted>` through `Debug`. | G1b | Hardening only. |
| 15 | `bootstrap-admin` and integration-settings edits now write audit rows. | G1 | New durable events. |

## 6. Security-relevant changes (review first)
- **A1 session resolution** (`auth.resolve_session` SQL function, `SECURITY DEFINER`): verify the live-check CTE keeps every validity condition (revoked, deactivated, idle, absolute expiry), that `CREATE OR REPLACE` preserved the `app_service` EXECUTE grant, and that the bump CTE cannot extend a session that the live CTE rejected. The decision NOT to add an in-memory session cache is deliberate and recorded.
- **RLS GUC merge** (`begin_rls_transaction`): both `app.current_user_id` and `app.current_user_roles` are set `is_local = true` in one statement; confirm no code path reads them from a pooled connection without a transaction.
- **D4g `auth_register` split**: characterization tests were written BEFORE the split; one was mutation-checked (changing `rollback` to `commit` on the unconsumable-invite branch fails it). Confirm the split changed no ordering of consume-invite / insert-credential / issue-session.
- **D2d reduced**: handler-level permission checks are unchanged in behavior; only the call shape changed. `permission_gate_tests` asserts for every manifest route that an unprivileged caller is refused.
- **D5b encryption**: golden vectors were generated ONCE from the shipped code and hard-coded; they prove the wire formats (AAD, byte layout) did not change. The three AEAD modules were deliberately not merged.
- **G1 audit rows**: confirm no secret value reaches `metadata` (tests assert absence), that rows are written after commit and are infallible-by-design (a failed audit write is logged, not propagated - a documented trade-off), and that the IP is taken from `ConnectInfo`.
- **Redacted `Debug`**: confirm no remaining struct that carries a credential derives plain `Debug` AND is logged (scan found none logged today).
- **F1 header policy**: confirm the preflight-forcing `Content-Type` on non-GET requests matches the backend's CORS configuration (allowed methods include DELETE; allowed headers include Content-Type).
- **TOTP step-up** (ui 1.6.91): UI-only; backend unchanged. Confirm the gate renders only when `totp_enrolled && step_up_required` and that Sign out is reachable while step-up is pending (logout reads the cookie directly).

## 7. Evidence and measurement method

| Claim | Method | Result |
|---|---|---|
| A1 throughput | `pgbench`, 8 clients, one session, local Postgres (worst-case contention; real network gains smaller) | 10.8k -> 37.4k calls/s; updates 86,650 -> 0; dead tuples 2,910 -> 0 |
| B1a latency | `dev-tools/latency_proxy.py --delay-ms 10` (20 ms round trip), handler-style transaction | 105.5 -> 84.2 ms |
| A3 index | 200k synthetic facilities in a rolled-back transaction, `= ANY` over 30 ids | 26.96 -> 0.31 ms |
| B4 startup | real binary booted from `/tmp` with a cleared environment through the proxy | 0.63-0.72 -> 0.32-0.35 s |
| C0 dedup baseline | `cargo test [--release] -- --ignored --nocapture print_baseline` | 800 rows ~10 ms (default) / ~45 ms (by name); 5,000 rows 0.14 / 0.58 s; XLSX 154 ms release at 5,000 |
| D3a route table | temporary test dumping all 136 `method path access` entries before/after | identical sets |
| F8 `fieldProvenance` | JSON dump of the exported array before/after, `cmp` | byte-identical (80 entries) |
| Characterization-first | tests written and run green against the OLD code, then the refactor, then the SAME tests | used for B2, D4g, F8 (ElavonTab, DropboxFolderPicker, TaggerResultsPage, facility page) |
| Mutation checks | deliberately break the new code/guard, confirm the test fails, restore | A1, D4g, F6 stale guard, G1a, TOTP layout gate |

Not measured: A4-A6 event-loop stall improvement (the benefit is under concurrent load; no load test was run), A7 over a real network, F3 bundle size.

Reproduce the gates: `cd unitprep-api && ./scripts/preflight.sh`; real-DB suite `TEST_DATABASE_URL=postgres://app_service:app_service@127.0.0.1:5433/unitprep_test cargo test --bin unitprep -- --ignored db` (needs the `test-db` container and `./scripts/bootstrap_test_db.sh`); UI `npx tsc --noEmit && npx eslint . && npx vitest run`.

## 8. Suggested review questions
1. **A1/A6/B2/B3**: any path where a session could outlive revocation, or where work now runs outside the RLS identity it should be under (e.g. a `spawn_blocking` closure that touches the DB or uses a captured user)?
2. **`run_blocking` ownership**: closures must own their data (`'static`); look for accidental clones of large buffers and for locks held across `.await` after the conversion.
3. **B3 batch writes**: partial-failure semantics (a failed run is non-fatal) - are `ps_sync_state` and dependent tables left consistent?
4. **D2a/D2b**: every handler that used to roll back explicitly on error - does the `begin_for`/`try_response!` form still drop (and therefore roll back) the transaction on every early return?
5. **E3 index drops and A3 indexes**: any query plan regressions on production-sized data? (Verified only on synthetic data and via EXPLAIN on dev.)
6. **F7 generated types**: places where the UI is tighter than Rust can express and was intentionally left hand-written (section 9) - is any of those a drift risk worth a Rust enum?
7. **G1**: any state-changing route still without an audit event that should have one? (The route cross-reference was heuristic; the route table is `src/api/router/routes/*.rs`.)
8. **Behavior-change list (section 5)**: anything that should have been feature-flagged or documented for operators?

## 9. Deliberately NOT done (and why) - do not report these as omissions
- **C1-C4 dedup algorithm tuning**: the C0 baseline showed the payoff is tens of milliseconds at the largest realistic size.
- **B1b bundled client-detail query**: pool starvation was never observed; B1a was the real win.
- **B5 / B6**: analyzed and skipped (B6 would race with export's UPDATE and silently lose output).
- **D2d permission-gate layer**: replacing per-handler checks with a manifest-driven layer would remove an independent enforcement layer and require rebuilding the router-level proof first; only the call shape was simplified.
- **D5c shared AEAD core**: ~40 duplicated lines x3, module docs argue for separate small per-purpose modules; D5b's golden vectors make a future merge safe.
- **Session cache / OnceLock key cache**: refused on security grounds (instant revocation).
- **Hand-written types kept**: `UserSummary`, `CreateInviteRequest` (UI narrows `role`/`company` to unions), `SyncStatus` (Rust `state` is a bare string), `PsWorkflow`, `PreviewRunSelection`, `EditableFacilityFields` (intersection type), and the tool-run summary union (the Rust side builds `report_summary` as untyped JSON).
- **Facility-page loads do not use `useAsyncResource`** (its refetch returns to "loading", which would blank the page after every save); no shared `Tabs` component (nav tabs are route-driven links); `key={index}` sites left (editable draft rows / id-less static lists).
- **Frontend 250-350-line files** not split (diminishing returns).

## 10. Known limitations and open items
- **Pre-existing failing live test** (not a regression): `clients::sync::orchestrator::live_tests::refresh_matching_facility_updates_unprotected_fields_and_skips_protected_ones` needs a real Process Street key and a real imported facility; a blanket `cargo test -- --ignored` always shows it. Use `-- --ignored db`.
- TOTP step-up prompt is covered by component tests only, not driven in a real browser (login is passkey-only).
- Latent: tagger handlers re-parse the stored .docx on every `report`/`apply`; fine for template sizes.
- A shared-working-tree practice note: during this work a second session had uncommitted changes in the same repos; releases were isolated with staged-only commits and clean-worktree pushes (documented in the vault `brain/Patterns.md`).

## 11. Where to look
- `CHANGELOG.md` in each repo: one section per release; the section text is the authoritative per-task record.
- `git log --oneline v1.9.61..v1.9.117` and `v1.6.55..v1.6.92`; messages end with the chunk id (for example "(refactor chunk D4c)").
- Cross-cutting building blocks introduced: `src/blocking.rs`, `src/api/blocking.rs`, `src/api/dedup_blocking.rs`, `src/api/rls.rs`, `src/api/session_io.rs`, `src/api/paging.rs`, `src/integrations/http.rs`, `src/integrations/config_source.rs`, `src/startup/`, `src/api/router/routes/`, `src/api/integration_settings_audit.rs`; UI `lib/http.ts`, `lib/useLatestRequest.ts`, `lib/useAsyncResource.ts`, `types/generated/` (+ `scripts/check_ts_bindings.sh` in the API repo).
