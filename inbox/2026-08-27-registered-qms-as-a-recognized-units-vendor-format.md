---
date: 2026-08-27
description: "The Pyott Road unit-list CSV that needed the manual-upload workaround turned out not to be a one-off — it's an export from QMS, QuikStor's new PMS rep"
tags:
  - project-note
source_repo: development
---

# Registered QMS as a recognized units vendor format

The Pyott Road unit-list CSV that needed the manual-upload workaround turned out not to be a one-off — it's an export from QMS, QuikStor's new PMS replacing QSX, so future imports of the same shape should auto-classify. Added a new migration seeding QMS into client_ops.vendor_format (content_type='units') with the four fields that have an unambiguous direct mapping; left Active unmapped since it needs Boris to explain QMS's UnitStatus codes first.

## What changed

- unitprep-api/migrations/20260827200000_seed_qms_units_vendor_format.up.sql + .down.sql (new) - inserts/deletes the QMS row: content_type='units', signature_headers=[UnitNumber,SizeCode,SizeDescription,UnitStatus], field_mapping maps Number<-UnitNumber, UnitGroup<-SizeDescription, Category<-UnitType, StandardRate<-StandardRate
- Applied to the dev DB directly via sqlx-cli (installed fresh, v0.9.0, via `cargo install sqlx-cli --no-default-features --features postgres,rustls`) against NEON_DEV_DATABASE_URL_DIRECT -- sqlx migrate info showed only this one migration pending, ran clean
- Restarted the running dev API a second time (0 active sessions at the time, confirmed via GET /health first) so AppState's unit_vendors cache (loaded at startup, otherwise a 5-min refresh) picked up the new row immediately instead of waiting


## Decisions

- Left `Active` unmapped rather than guessing at QMS's UnitStatus code semantics (R0/L0/D3/E0/O3/U0/A0 seen in the real file) -- Active is optional/informational only (unit-group::format::REQUIRED_TARGET_FIELDS is just [Number, UnitGroup]), so this doesn't block anything; safe to add via a follow-up migration or per-import through the manual mapping UI once Boris explains the codes.
- Registered only content_type='units' (Group Prep), not 'tenants' (the dedup duplicate-tenant-checker) -- the file in hand is a unit list with zero tenant/contact columns, so it can't serve as a dedup signature regardless of terminology; flagged this distinction back to Boris rather than silently assuming 'the dedup vendor list' meant the tenants registry.
- Wrote a new append-only migration rather than editing the original 20260818120000 seed migration -- that one's already applied on dev (locked in via checksum in _sqlx_migrations), so editing it in place would either be silently ignored or break checksum verification for anyone re-running migrations from scratch.


## Learned

- sqlx-cli wasn't installed in this dev environment at all -- installing v0.9.0 fresh (project's own sqlx crate dependency is v0.8.6) via cargo took under 30s and worked against the same DB with no version friction; `sqlx migrate info --database-url <direct-url>` before running is a cheap way to confirm exactly one migration is pending before applying.


## Verification

sqlx migrate run applied cleanly (190ms) against the dev DB; verified the row directly via psql (SELECT ... WHERE name='QMS' returns the expected signature_headers and field_mapping). Restarted the API (confirmed 0 active sessions first via GET /health) and re-ran the full backend suite: 334 passed / 0 failed / 3 ignored, unchanged from before the migration.


## Open

- QMS's UnitStatus code meanings (R0/L0/D3/E0/O3/U0/A0 -> active/vacant/damaged/etc.) still need Boris's input before Active can be mapped for this vendor.
- Whether a QMS tenant/customer export (for the actual dedup content_type='tenants' tool) also needs registering is unresolved -- no such file has been provided yet; asked Boris to clarify if that's separately needed.



_Recorded 2026-08-27T19:45:39.755Z from `development` via the om MCP server (routing: fallback)._
