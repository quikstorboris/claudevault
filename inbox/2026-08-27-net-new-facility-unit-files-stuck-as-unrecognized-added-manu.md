---
date: 2026-08-27
description: "A net-new facility's own hand-built unit-list CSV (no PMS export) can never match any of the 3 registered vendor header signatures, so discovery perma"
tags:
  - project-note
source_repo: development
---

# Net-new facility unit files stuck as "unrecognized" — added manual unit-file upload

A net-new facility's own hand-built unit-list CSV (no PMS export) can never match any of the 3 registered vendor header signatures, so discovery permanently buckets it as "unrecognized" and the UI dead-ends on "No unit files found — check your folder selection" even though the file uploaded fine. Fixed by adding a `/unit-file/upload` manual-override endpoint mirroring the existing `/group-file/upload` one, plus a one-line fix to `reconcile_unit_file_selection`'s preservation filter so a forced selection survives the next discovery recompute even though it never vendor-matches.

## What changed

- unitprep-api/src/api/discover/selection.rs - reconcile_unit_file_selection's previous-selection filter now checks session.data.documents (existence) instead of the freshly recomputed candidates list (vendor-match) -- mirrors resolve_group_file_readiness's existing existence-only check for the group file
- unitprep-api/src/api/unit_file_upload.rs (new) - POST /unit-file/upload: upserts the document, pushes it onto discovery.selected_unit_file_names, clears any stale format_resolutions entry for that name, then calls compute_discovery -- exact mirror of group_file_upload.rs's apply_group_file_upload
- unitprep-api/src/api/discover/compute.rs - updated a stale 'Unreachable today' comment on the no-detected-vendor branch of compute_discovery's mapping-suggestion logic; it's reachable now that a file can be forced in without matching a vendor
- unitprep-api/src/api/router.rs, src/api/mod.rs - registered the new endpoint/module
- unitprep-ui/components/discovery/useManualUnitFileUpload.ts (new) - mirrors useManualGroupFileUpload.ts, posts to /unit-file/upload via useFileUploadAction
- unitprep-ui/components/discovery/UnitFileSelectionSection.tsx - added a third render branch (0 candidates AND 0 selected) with a 'No unit file recognized... Select File' manual-upload control, replacing what used to silently fall through to a misleading '0 files selected' summary
- unitprep-api/.env.local - added SESSION_TIMEOUT_SECS=14400 (4h, in-memory discovery/dedup/Tagger session store) and SESSION_LIFETIME_HOURS=8 (passkey login absolute lifetime) -- both were previously unset, running on 10min/12h code defaults


## Decisions

- Chose 'build the manual-upload + column-mapping bypass' over 'register this file's headers as a new vendor_format DB row' (the data-over-hardcoding default this repo prefers) -- because interpreting this file's UnitStatus codes (single-letter+digit codes like R0/L0/D3/E0/O3/U0/A0 from an old system nicknamed 'Winsen' in the filename) and confirming SizeDescription as the UnitGroup source requires business knowledge only Boris has. The already-built generic manual-mapping UI (FormatResolutionActiveView, gated on requires_format_resolution/detected_vendor_name==null) lets him choose the mapping himself at upload time instead of me guessing and baking a wrong interpretation into a shared DB row.
- Did NOT add a manual-upload affordance to the already-has-files-selected state (only to the true empty state) -- kept to the minimum needed to fix the reported bug rather than also building a 'select different/additional file' flow group files have; can extend later if a facility needs multiple manually-forced unit files.
- Restarted the running dev API (release build) to pick up both the code fix and the new SESSION_* env vars, since InMemorySessionStore state and dotenv-loaded env are both read once at process start. The in-flight dedup session from the bug report had already expired, so nothing live was destroyed by the restart.


## Learned

- client_ops.vendor_format currently has exactly 3 'units' rows (QSX, Storage Commander, DoorSwap) and 2 'tenants' rows (QSX, Easy Storage Solutions) in the dev DB -- confirmed by querying as the neondb_owner role directly (app_service/psql without app.current_user_id set returns 0 rows due to the table's own RLS SELECT policy, not because the table is empty).
- select_unit_file.rs's FileNotDiscovered check and reconcile_unit_file_selection's candidates list both require a vendor-signature match -- unlike the group-file path, there was no way at all (auto or manual) to designate a non-vendor-matching file as a unit file before this change.
- requires_format_resolution and its whole manual-column-mapping pipeline (validate_manual_mapping, format_resolutions, effective_documents_for) were already fully vendor-agnostic and already had UI copy for the no-detected-vendor case -- the actual gap was one layer up, at selection, not in format resolution itself.


## Verification

Backend: cargo build --bin unitprep clean; 4 new tests in unit_file_upload_tests.rs pass (404 missing session, 409 pre-discovery, forced file becomes selected+requires_format_resolution with null detected_vendor, and the key regression test -- forced selection survives a second /discover call); full suite 334 passed/0 failed/3 ignored (up from 330). Frontend: tsc --noEmit and eslint clean; 2 new tests in UnitFileSelectionSection.test.tsx (empty-state renders Select File instead of a misleading summary; uploading a file posts to /unit-file/upload and forwards the response) pass; full vitest suite 335 passed/0 failed (up from 333). Restarted the actual dev API afterward and confirmed GET /health returns 200 with 0 active sessions (clean restart, no stuck state).


## Open

- The exact field_mapping for this specific facility's CSV (UnitNumber/SizeCode/SizeDescription/UnitStatus/CurrentRate/StandardRate/CurrentDeposit/InterfaceNumber/WalkOrder/UnitType -> canonical targets, esp. what each UnitStatus code like R0/L0/D3/E0/O3/U0/A0 means for Active/occupied semantics) still needs to be worked out by Boris via the manual mapping UI -- not resolved by this change, just unblocked.
- No manual-upload affordance exists yet for adding a second/different unit file once one is already selected (group files have 'Select Different File' / 'Choose From Discovered'; unit files don't) -- fine for the single-file net-new case this was built for, would need extending if a facility needs multiple manually-forced files.



_Recorded 2026-08-27T19:29:01.684Z from `development` via the om MCP server (routing: fallback)._
