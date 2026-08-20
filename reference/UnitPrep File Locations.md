---
date: 2026-07-27
description: Where to find UnitPrep docs, sample data, source code, and the QMS OpenAPI spec across drives, OneDrive, and WSL.
tags: [reference, unitprep]
---

# UnitPrep File Locations

> [!note] Staleness
> Ported from a memory note last touched 2026-07-16. Paths are believed current but not re-verified for this port — cross-check before relying on specifics.

## Docs (project history, business logic, principles)

`C:\Users\bmaksimov\OneDrive - Kobre Holdings, LLC\Documents\unitPrepDocumentation`

Key files: `UnitPrep_Project_History_And_Architecture.json`, `unitprep_project_handoff.json`, `UnitPrep_Development_Principles.json`, `UnitPrep_Engineering_Standards.json`, `UnitPrep_Product_Principles.json`, plus dated `context_unitprep_*.json` snapshots and changelogs of past work (bug fixes, architecture improvements, UI improvements).

Treat these as **point-in-time chat-session summaries, not live docs** — cross-check against actual code/README before relying on specifics. Example: the handoff doc listed 6 API endpoints; the real README/CHANGELOG as of v1.0.0 show more (`/correct`, `/exempt-dimensions`, `/group-file/select` were added since).

## Sample/test data

`C:\Users\bmaksimov\OneDrive - Kobre Holdings, LLC\Documents\temp\Test Data`

One folder per real facility (e.g. "Ponchatoula Storage", "Main Street Storage"), each typically containing:
- a "Preliminary Data" subfolder — raw PMS exports: `activeCustomers`, `rentRollDetail`, `emailAddress`, `tenantAddress`, `unitStatus`, `unit` (all `.xlsx`)
- a "Units Migration" subfolder — the cleaned `*_Units_For_Import.csv` and a duplicate-tenant-check CSV

A top-level `Absolute Storage Management  Unit Groups.csv` is a sample master Unit Group catalog (Name, Description, Assigned to, Status, Last Updated).

## Source code

On WSL (Ubuntu-22.04), accessed from Windows via `\\wsl.localhost\Ubuntu-22.04\home\bmaksimov\Documents\`:

- `unitprep-api` — Rust/Axum backend, has its own README.md/CHANGELOG.md that are authoritative and more current than the OneDrive handoff docs.
- `unitprep-ui` — Next.js frontend, same pattern (own README/CHANGELOG).

Both repos are git repos, versioned and released independently. See [[WSL Execution Technique]] for how to actually run commands against this environment from a Windows session, and [[UnitPrep UI Dev Environment]] for `unitprep-ui`-specific dev-server quirks.

## QMS OpenAPI spec

`C:\Users\bmaksimov\OneDrive - Kobre Holdings, LLC\Documents\api-1.json`

The real API doc for QMS — the modern, cloud/API-capable PMS platform UnitPrep actually targets going forward, distinct from QSX, the legacy desktop system the No Ka Oi/New Castle sample data came from, which is being sunset and has no real API.

**Read in full 2026-08-07** — a verbatim copy plus a full readable breakdown now lives in the vault: see [[QMS API Index]] (auth shape, base-URL gap, the placeholder-tag question answered), [[QMS API - Endpoint Catalog]] (all 92 endpoints), and [[QMS API - Domain Model & PII]] (Company/Facility/Unit/UnitGroup/Lease/EndUser field shapes). Check those first — re-reading the raw spec from scratch should rarely be necessary now. Re-pull from this OneDrive path and re-copy into the vault (new dated filename, don't overwrite) only if QMS ships a newer version.

## Dedup pattern-discovery reference docs (2026-07-16)

Same `unitPrepDocumentation` folder as above:

- `duplicate_tenant_check.py` — a from-spec Python rebuild of the reference skill, kept as a design reference. Includes an explicit `spreadsheet_cell_references_in_notes` implementation with worked column/row math.
- `dedup_patterns_reference.json` — a living log of dedup edge cases/fixes discovered across real chat-mode runs at multiple real clients. Read this before assuming a dedup pattern is either "already handled" or "still a gap" in `unitprep-dedup` — check the actual crate code too, since this doc can get ahead of what's actually been ported.

See [[Dedup Tool Index|Dedup Tool]] for the cross-check against the actual implementation.

## Related

- [[UnitPrep Architecture Overview]] — what the app actually does
- [[WSL Execution Technique]]
- [[UnitPrep UI Dev Environment]]
