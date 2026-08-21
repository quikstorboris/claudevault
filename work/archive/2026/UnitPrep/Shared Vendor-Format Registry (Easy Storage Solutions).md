---
date: 2026-08-18
description: "Generalized vendor-format recognition (previously hardcoded per-tool) into one shared, DB-backed registry, to onboard Easy Storage Solutions tenant exports in dedup."
tags: [work-note, unitprep, dedup, unit-group, architecture]
status: completed
quarter: Q3-2026
project: unitprep
---

# Shared Vendor-Format Registry (Easy Storage Solutions)

Boris needed dedup to handle a real onboarding file (Easy Storage Solutions' "Full Tenant Data.csv", Affordable Storage LLC - Thibodaux, LA) instead of hard-erroring with "missing FirtLast column" — dedup only ever recognized QSX. Rather than a one-off special case, generalized vendor recognition (previously hardcoded separately in unit-group's own `format.rs`, see [[Multi-Vendor Unit-File Discovery]]) into one shared module read by both tools, backed by a new `client_ops.vendor_format` Postgres table, per Boris's explicit direction to prefer data over hardcoding wherever feasible (see [[UnitPrep Architecture Overview]]'s design-principles section).

**Shipped**: committed and pushed to `origin/main` as `unitprep-api@c61ca9a..2162d82` (5 commits: the migration, the shared `core::vendor_format` module + cache, the "prefer data over hardcoding" CLAUDE.md principle, Group Prep's migration onto the registry, and dedup's Easy Storage Solutions support + `/dedup/detect-vendor` endpoint) and `unitprep-ui@b8e5f35` (the confirm-gate UI) — see [[New Laptop Migration — QSLP14]] for how that was later verified to have actually landed on GitHub. The `client_ops.vendor_format` migration itself was applied against the real Neon dev database the same day this was recorded, and confirmed readable by `app_service` under RLS with a live `psql` query.

## What changed

- `unitprep-api/migrations/20260818120000_create_vendor_format_registry.{up,down}.sql` — `client_ops.vendor_format` table (name, content_type, signature_headers text[], field_mapping jsonb, transform_key), new permission `client_ops.manage_vendor_formats` (admin/onboarding_manager/department_manager), seeded with QSX/Storage Commander/DoorSwap (units) and QSX/Easy Storage Solutions (tenants)
- `unitprep-api/core/src/vendor_format.rs` (new) — `ContentType` enum, owned `VendorFormat` struct, `detect_vendor`/`apply_field_mapping` (generic, DB-agnostic), plus `transforms::split_ess_address` — the one real parsing transform (ESS packs street+city/state/zip into one Address column across an embedded newline); verified against all 160 real rows of the actual export before trusting it
- `unitprep-api/src/client_ops/vendor_format.rs` (new) — `load_vendor_formats` (RLS-scoped via `begin_rls_transaction`), `VendorFormatCache` + `initial_cache`/`start_refresh_task` (5-min background refresh) — deliberately not queried per HTTP request; wired into `AppState` + `main.rs`
- `unitprep-api/src/application/unit_group_session.rs` — `SessionData` gained `unit_vendors: Vec<VendorFormat>`, a snapshot taken by `compute_discovery` so `effective_documents`' auto-detect fallback doesn't need every unrelated caller (validate/analyze/correct/exclude_group) to thread the registry through themselves
- `unitprep-api/unit-group/src/format.rs` — removed hardcoded `QSX`/`STORAGE_COMMANDER`/`DOOR_SWAP`/`VENDOR_FORMATS` consts; `detect_vendor` now re-exported from core; `CANONICAL_TARGET_FIELDS`/`REQUIRED_TARGET_FIELDS` stayed (tool-specific pipeline requirements, not vendor data)
- 5 unit-group HTTP handlers (discover, select_unit_file, select_group_file, group_file_confirm, group_file_upload) — read `state.unit_vendors.read().clone()` before the session lock and pass it into `compute_discovery`/`resolve_confirm_action`
- `unitprep-api/dedup/src/ingest.rs` — `records_from_csv_document` now takes `tenant_vendors`, runs `detect_vendor`+`apply_field_mapping` before the existing per-column extraction (the `COLUMNS` table itself unchanged — zero vendor-specific branching survives outside the format module)
- `unitprep-api/src/api/dedup.rs` — new `POST /dedup/detect-vendor` endpoint (parses headers only, returns `vendor_name`, no session/ingest/report) for the frontend's pre-Run-Check gate
- `unitprep-ui/components/DedupUploadPage.tsx` — calls `/dedup/detect-vendor` on file select, shows "Vendor: {name}" + a confirm checkbox, Run Check disabled until confirmed — mirrors Group Prep's own recognize-then-confirm flow rather than special-casing QSX
- `unitprep-api/CLAUDE.md`, `unitprep-ui/CLAUDE.md`, [[UnitPrep Architecture Overview]] — added the "prefer data over hardcoding" design principle with this work as the concrete precedent

## Decisions

- DB-backed from day one for ALL vendors (including existing QSX/Storage Commander/DoorSwap), not just the new ESS one — Boris's explicit call after the hybrid option (hardcode well-known vendors, DB only for self-service) was raised; he preferred consistency and left the persistence-vs-code judgment call to the implementer.
- Vendor registry is cached in `AppState` (5-min background refresh), never queried per HTTP request — discovered mid-implementation that ~190 existing discovery tests call the HTTP handlers directly against a lazily-connected pool that never touches Postgres (`test_support::test_db_pool`); a per-request DB read would have turned every one of those into a ~50ms failure instead of an instant in-memory result.
- `SessionData` carries a `unit_vendors` snapshot (taken at discovery time) rather than threading the live registry through validate/analyze/correct/exclude_group's own handlers — those callers only need `effective_documents`' auto-detect fallback to work, and a session-scoped snapshot is an acceptable few-minutes staleness against rippling one more parameter through 5 unrelated handler files.
- The address-split transform (`split_ess_address`) stays as hand-authored Rust code keyed by a `transform_key` string, NOT expressible from a future self-service "add a vendor" UI — `client_ops.vendor_format` has no code column by design; a self-service vendor that turns out to need real parsing logic is meant to graduate into a hand-authored row, the same path Storage Commander/DoorSwap followed historically.
- Self-service "add an unrecognized vendor on the fly" UI (naming it, mapping fields, persisting) explicitly deferred to a follow-up — this piece of work only built the shared registry + detection/confirm-gate UX for known vendors.

## Learned

- Postgres RLS on `client_ops` tables requires `app.current_user_id` to be set via `begin_rls_transaction`; a query against the raw pool doesn't error, it just silently returns zero rows — would have looked exactly like "vendor not recognized" rather than "this call is wired wrong" if not caught before shipping.
- `AppState::db` is deliberately lazy (`connect_lazy`, never blocks startup) specifically so a temporarily-unreachable Postgres doesn't crash boot — the vendor-format cache's initial load had to respect that same stance (best-effort, empty-and-retry-on-first-tick rather than panic).
- Verified the ESS address-splitter against all 160 real rows of the actual export (not just the 2 sample rows first seen) before trusting it — found 6 blank addresses and a couple of zip+4/no-zip edge cases the splitter needed to degrade gracefully on, not error on.

## Verification

Full `cargo test --workspace`: 326 (unitprep bin) + 72 (dedup) + 58 (unit-group) + others, 0 failed, all passing (5 ignored: real-fixture tests needing env vars / real Postgres). `cargo clippy --workspace --all-targets -- -D warnings`: clean. Frontend: `tsc --noEmit` and `eslint` on the two changed files clean. Address-splitter specifically checked against all 160 real rows of the actual "Full Tenant Data.csv" (154 two-line addresses, 6 blank, including a zip+4 and a city/state-with-no-zip row) via a standalone Python simulation of the exact Rust logic before writing it.

## Open

- Self-service "add vendor on the fly" UI (unrecognized file → name + content-type + field-mapping → persist to `client_ops.vendor_format`) is a distinct, not-yet-scheduled follow-up.
- The generalized manual-mapping UI (extending Group Prep's existing `UnitFileResolutionPanel.tsx` to take an arbitrary canonical-field list, for reuse by the self-service add-vendor flow) is also not built yet.

## Related

- [[Multi-Vendor Unit-File Discovery]] — the earlier, per-tool (hardcoded) version this generalized.
- [[Dedup Tool Index]]
- [[UnitPrep Architecture Overview]]
- [[Westpark Cross-Check — Placeholder, Wording, and XLSX Fixes]] — the follow-on bug-fix pass in the same area.
- [[New Laptop Migration — QSLP14]]
