---
date: "2026-09-24"
quarter: "Q3-2026"
description: "A missed modularity flag on router.rs prompted a CLAUDE.md law in both repos, then three prioritized fixes: refresh.rs field-parity tests, the router.rs split, and a policy-handler DRY refactor"
tags:
  - work-note
  - project/unitprep
---

# Session 2026-09-24 — Modularity Standing Law, Router Split, Refresh Parity Tests & Policy-Handler DRY Refactor

Started from a second external-style codebase audit (large-file table, repetitive-pattern findings, N+1 insert observation). Verified every claim against the real repo before acting — the file-size table was accurate for every file except one: `router.rs`, listed as 842 lines and "cohesive," was actually **1909 lines**, entirely from the previous session's own `GatedRouter` work (see [[Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation]]).

## The miss, and closing the actual gap

This project already has a detailed standing rule for exactly this (see [[Patterns]]'s "flag modules approaching ~250 lines" and its 2026-08-14 generalization to unprompted architectural-drift flagging) — but it lived only in the vault, reached via `recall`/`search` on non-trivial *design* decisions. A routine multi-edit task that grows one file substantially doesn't reliably re-trigger that check once the design work itself is done, which is exactly what happened: the rule was applied to the *substance* of the GatedRouter session but never re-checked against the resulting file's own size afterward.

**Fix**: added the check directly to both `unitprep-api/CLAUDE.md` and `unitprep-ui/CLAUDE.md` as a standing repo law — "check file size and concern-mixing after finishing a task, not only when starting one" — rather than leaving it as a vault-only advisory. Full incident write-up in [[Patterns]].

Then worked through three fixes in priority order (ranked by where the vault's own "structural enforcement, not a comment" theme applied most, not by the audit's own ordering):

## 1. `refresh.rs` field-parity tests (highest priority)

The audit's sharpest finding: `apply_company_refresh`/`apply_facility_refresh` are full struct literals (the compiler already refuses to build if a `MappedCompany`/`MappedFacility` field is forgotten), but their siblings — `company_field_value`, `facility_field_value`, `facility_fields_that_differ`, and `clients::create::diff_company_fields` — are each a hand-written per-field `match`/`if` list with no catch-all failure, so a field added to the struct but forgotten in one of these four compiles fine and just silently never gets recognized.

Each new test reads the struct's own field names via `serde_json::to_value(..).as_object().keys()` rather than hand-listing them a second time, so it actually catches drift instead of re-asserting a second copy of the same list the code under test already has. `go_live_date` deliberately excluded, matching the module's own existing doc comments. All 4 new tests passed against current code — no live bug, now protected against a future one.

## 2. `router.rs` split (1909 → 3 files)

Two genuinely separable concerns had been sharing one file since before either existed: `router/routes.rs` (1055 lines — the route table itself) and `router/permission_gate_tests.rs` (534 lines, `#[cfg(test)]` — the runtime proof that table is enforced), leaving `router/mod.rs` (349 lines — the public entry point, response-shaping middleware, rate-limit error handling). Pure reorganization, `build()` unchanged internally beyond `pub(super)` visibility; same 654 tests, same clippy output.

`routes.rs` is still long (106 routes) — flagged rather than split further, since splitting a single `GatedRouter` builder chain by domain is a bigger, separate restructuring than "stop mixing routes with middleware." Confirmed with Boris as acceptable to leave for now: it's serving one concern.

## 3. Policy-handler DRY refactor

`fees.rs`/`taxes.rs`/`delinquency.rs`/`coverage.rs` (×2, tiers and commission) each hand-wrote the same "count existing rows, then delete them all" pair before their own insert loop. Factored into one shared `count_and_delete_existing(tx, table, facility_id)` helper. `specials.rs` was correctly left alone once actually read — it's a single-row `ON CONFLICT` upsert, not the delete-then-reinsert pattern the audit's own description had grouped it into.

The N+1-round-trips-to-Neon question these same insert loops raise (a `QueryBuilder::push_values` batch insert) stays explicitly deferred — a separate, previously-discussed optimization, not part of this DRY pass.

## Result

`unitprep-api` `v1.9.38`: `867a206` (CLAUDE.md law), `41c586b` (refresh parity), `cecc95f` (router split), `87569d0` (DRY refactor), `139ac65` (version bump). Full workspace suite (654 + 78 tests), clippy, and `cargo fmt --check` clean throughout. Tagged and pushed to `origin/main`. No `unitprep-ui` changes this session.

## Related

- [[Patterns]] — the router.rs miss's full write-up, and the standing 250-line rule this session reinforced.
- [[Key Decisions]] — the "check after finishing, not just before starting" refinement to the modularity rule.
- [[Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation]] — the session whose own growth this one caught and fixed.
