---
date: "2026-09-23"
quarter: "Q3-2026"
description: "GatedRouter closes the require_permission audit gap, 13 handlers fixed for audit-before-commit ordering, and ts-rs generates the core tool-session response types instead of hand-mirroring them"
tags:
  - work-note
  - project/unitprep
---

# Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation

Three independent pieces of `unitprep-api` work in one session, all shipped as `v1.9.37` (plus a paired `unitprep-ui` type-consumption commit). Each started from a real, verified gap rather than a hypothetical one.

## 1. GatedRouter — closing THREAT_MODEL.md's named permission-gate gap

`THREAT_MODEL.md`'s own "Known gaps" section named this directly: since roles/permissions moved from a closed `Role` enum to data-driven tables (2026-08-06), the old compiler backstop (an exhaustive `match admin.role` failing to compile on a new role) disappeared, and nothing catches a new handler that simply forgets to call `require_permission`.

**Design**: `GatedRouter` (`src/api/route_access.rs`) wraps `axum::Router` and never re-exposes `.route()` — the only way to register a route is `gated_route(path, method_router, [(Method, RouteAccess), ...])`, so a route cannot be wired up without declaring what authorizes it at that exact call site. `RouteAccess` is `Public | AuthCeremony | Authenticated | RlsRead | RlsWrite | Permission { keys, action }`. This only forces the *declaration* — `router.rs`'s `permission_gate_tests` module closes the other half by calling the real handler behind every `Permission`-classified route with a caller holding zero permissions and asserting 403, so a handler that declares `Permission` but forgets to actually call `require_permission` fails a real test, not just a manifest check.

**Classifying all 106 routes required verifying against handler source, not router.rs's own comments** — one comment turned out to be stale: `/integrations/process-street/settings` GET was documented as "any authenticated caller" but `get_settings` actually gates on `integrations.manage` (it returns the live API key). Fixed in the same pass. Also surfaced a genuine, pre-existing test gap: `auth_configuration.rs`'s two handlers had *zero* tests of any kind before this — not even a negative-permission test, unusually for this codebase's convention of the same one per require_permission-calling handler.

Full technical detail (design rationale, the RouteAccess enum, the closures-based test harness) in the conversation transcript; durable pattern recorded in [[Key Decisions]].

## 2. Client-ops audit log recorded before commit, not after, in 13 handlers

A pasted external review claimed `client_ops::audit_log::record` (writes on `state.db` directly — a separate connection from the handler's own RLS transaction) was being called *before* `tx.commit()` in several policy/company/facility handlers, meaning a commit failure after a successful audit write would leave a permanent "X updated" row for a change that never actually landed — a false positive, worse than the false negative (a rare missed row) the fixed ordering produces instead.

**Verified independently before acting** (this codebase's own established discipline — see [[Patterns]]'s "review a previous session's uncommitted work like a stranger's PR" entry, same principle applied to an external claim): read `audit_log::record`'s real signature, confirmed it takes `&PgPool` not `&mut Transaction`, and grepped every named handler to confirm the exact line ordering. All 13 claims checked out exactly, and `clients_elavon.rs`/`clients_manual_link.rs` were confirmed as the pre-existing *correct* pattern (commit, then audit) that the fix brings the other 13 in line with.

**Fixed**: `fees.rs`, `taxes.rs`, `coverage.rs`, `delinquency.rs`, `specials.rs` (the 5 policy-edit handlers), `clients_facility_people.rs` (×3), `clients_companies.rs` (×2), `clients_dropbox_folder.rs`, `tool_runs.rs`. Pure reordering, no logic changes — full suite (646 tests at the time) and clippy stayed clean.

## 3. ts-rs generates the tool-session response types instead of hand-mirroring them

`types/api.ts` in `unitprep-ui` hand-mirrors Rust response structs by eye, and its own header comment already claimed "a backend field rename should show up here as a TypeScript error" — but nothing enforced that, and it had already drifted silently once (the `output_path` field removal broke at runtime).

**Considered three options** (discussed at length before building anything):
- **A cross-repo schema-diff test** (generate a JSON shape from Rust, check it against a file committed in `unitprep-ui`) — rejected once it became clear there's no way to actually *compare* a JSON shape against a hand-written TS type without either a second hand-maintained manifest (same drift risk, just moved) or full codegen.
- **A same-repo Rust-only "tripwire" snapshot test** — cheap, but only reminds the developer something changed; doesn't verify the frontend at all.
- **Generate the actual `.ts` file from the Rust struct** (chosen) — `ts-rs`, replacing the hand-written type entirely for the covered structs. Nothing left to diff against, since the generated file *is* the type.

**Scoped deliberately** to the four response families `types/api.ts`'s own header names (`UploadResponse`, `DiscoverResponse`, `ValidateResponse`, `AnalyzeResponse`) plus their transitive dependencies (11 types total, spanning the main crate and the `unit-group` library crate) — not the dedup/tagger types further down that file, which stay hand-mirrored for now.

**A real gotcha found empirically, not from docs** — see [[Gotchas]] for the full ts-rs `export_to`/`TS_RS_EXPORT_DIR` path-resolution writeup. One real type-shape fix needed along the way: `ts-rs` defaults `i64` to `bigint`, but `UnitFileCandidate.modified_at` is a browser-supplied epoch-millis value the frontend already treats as a plain `number` — overridden with `#[ts(type = "number | null")]` rather than forcing a bigint refactor onto working code.

`npm run generate-types` (added to `unitprep-ui`'s `package.json`) is the one command to re-run after touching a covered struct; `types/generated/README.md` documents the mechanism and its scope.

## Shipped

`unitprep-api` `v1.9.37` (`37d4f89` GatedRouter, `afbc642` audit ordering, `aab7452` ts-rs export), `unitprep-ui` type-consumption commit (`e8ad7b0`, landed as part of that repo's own `v1.6.39` batch — see [[Session 2026-09-23 — Frontend Test Coverage Priorities 1-4 (Auth, Admin, API-Client Libs, Facility Policy Tabs)]]). Both tagged and pushed to `origin/main`.

## Related

- [[Key Decisions]] — GatedRouter as the structural replacement for the lost `Role`-enum compiler backstop; the ts-rs-over-schema-diff decision.
- [[Gotchas]] — ts-rs `export_to` path resolution.
- [[Patterns]] — the router.rs size growth this session caused is its own entry there, linked from [[Session 2026-09-24 — Modularity Standing Law, Router Split, Refresh Parity Tests & Policy-Handler DRY Refactor]].
