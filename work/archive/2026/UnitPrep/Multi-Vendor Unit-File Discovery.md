---
date: 2026-07-27
description: QSX/DoorSwap/Storage Commander vendor registry for unit-file discovery — master-file unification, multi-candidate picker, discovered-groups list; committed and shipped 2026-07-25.
tags: [work-note, unitprep]
status: completed
quarter: Q3-2026
project: unitprep
---

# Multi-Vendor Unit-File Discovery

Group Prep's discovery step originally hard-coded QSX's own export headers as the only recognized shape. This workstream generalizes it into a real vendor registry, then went through several rounds of live-data-driven correction after real usage exposed wrong assumptions. First slice was implemented, verified, and pushed 2026-07-22; a large continuation happened 2026-07-23/24, and all of it — including the 2026-07-24 work (Storage Commander, master-file unification) — was committed 2026-07-25 as `unitprep-api@ace8ff6` / `unitprep-ui@0cd2130`. See the Status section at the end for confirmation this is live on `main` and well-tested (3 dedicated Storage Commander tests in `format_tests.rs`, bulk-confirm/header-mismatch coverage in `resolve_unit_format_tests.rs`), re-verified 2026-07-28.

## Why

Boris needed to onboard a DoorSwap export (`Units List.csv`: `Unit, Status, Unit Type, Customer, Phone, Cell Phone, Email, Balance`) alongside QSX's real raw export (`KAH_QMS_Units_Template.csv`, 27 fields), and wanted a repeatable pattern for future vendors rather than a one-off special case.

## Key design decisions

- Every vendor, QSX included, goes through the same recognize → confirm-or-map flow. QSX is not special-cased as "just works."
- The manual field-mapping UI's target-field list is the literal union of known vendors' real raw headers (35 fields), not an invented canonical schema — reuse real vendor vocabulary. Only `Number` and `UnitGroup` are actually required by the pipeline.
- Vendor default mappings are hand-authored, not derived by identity-matching target names against a vendor's headers — DoorSwap's own vocabulary (`Unit`, `Unit Type`) is itself part of the canonical union list, so naive matching would leave `Number`/`UnitGroup` empty for DoorSwap.
- Manual mappings are ephemeral/session-only — no persistence layer for reusable vendor profiles yet (deliberate, not an oversight).

## What was built (initial slice, 2026-07-22)

- `unit-group/src/format.rs` (new, ~230 lines): `VendorFormat` registry (`QSX`, `DOOR_SWAP`), `CANONICAL_TARGET_FIELDS`/`REQUIRED_TARGET_FIELDS`, `detect_vendor`, `mapping_from_vendor`, `apply_field_mapping` (mirrors `corrections::apply_corrections`'s shape).
- `DiscoveryResult`/`DiscoverResponse` extended with `unit_file_candidates`, `selected_unit_file_name`, `requires_unit_file_selection`, `requires_format_resolution`, `detected_vendor_name`, `source_headers`, `suggested_mapping`, `canonical_target_fields`, `required_target_fields`.
- Two new endpoints: `POST /unit-file/select` (modeled on the existing `/group-file/select`) and `POST /unit-file/resolve-format` (`action: "confirm" | "map"`).
- `discover.rs` refactored around a shared `compute_discovery(session)` helper reused by `/discover`, `/unit-file/select`, and `/unit-file/resolve-format`.
- `SessionData` gained `format_resolutions: HashMap<String, FieldMapping>`; `effective_documents()` now applies format mapping before corrections.
- Frontend: `components/UnitFileResolutionPanel.tsx` (new) renders the candidate picker and confirm/manual-mapping UI inside `DiscoveryPage.tsx`; upload sends a new `file_modified_times` sidecar field alongside the existing multipart file parts (needed since a discovery session is scoped to one facility, and 2+ unit files found are treated as duplicate re-pulls of that facility — the user picks one, shown with each candidate's modified date).

Verified: all 167 Rust tests passing, `tsc --noEmit`/`eslint` clean, plus a real end-to-end smoke test via `curl` against actual sample files (QSX-alone, DoorSwap-alone, both-together forcing the multi-candidate picker). Frontend UI itself was not visually exercised in a browser that day (Turbopack dev-server issue at the time); Boris tested it himself.

## Real bug found and fixed, 2026-07-22

Boris ran the real DoorSwap file through validate and got "Invalid dimensions" flagged on all 223 units. Root cause: `apply_field_mapping`'s first version included every one of the 35 canonical target fields as headers on the normalized document, filling unmapped ones with `""` rather than omitting them. `validate_document`'s optional-column checks use header presence as "this file declares this column, check it" — a canonical column that's always present but blank (DoorSwap has no separate Width/Length columns; dimensions live inside the UnitGroup descriptor string) reads as "real data, and it's wrong" for every row.

Fix: `apply_field_mapping` now drops any target field with no resolved source column entirely, so a vendor that never supplies an optional field simply doesn't have that header. Re-verified against the real file: `/validate` reports `issue_count: 0`. Lesson: synthetic test fixtures for a new vendor format should include at least one canonical field the vendor *doesn't* map, not just the ones it does — this kind of bug only surfaces against real vendor data.

## Extensibility confirmed, committed+pushed 2026-07-22

Before committing, Boris asked directly whether this actually created a reusable framework for future vendors, not just a hardcoded two-vendor case. Re-verified against the real code and confirmed: adding vendor #3 is a pure data addition (one new `VendorFormat` const, plus extending `CANONICAL_TARGET_FIELDS` only if the new vendor has genuinely new field names). No vendor-specific branching exists anywhere outside `format.rs`.

Committed as `unitprep-api@b066c4b` and `unitprep-ui@5d5da69`, pushed to `origin/main`. These landed after the separate dedup note-copy-redesign commits — both features were developed with dirty working trees at once, so committing required splitting `unitprep-ui`'s `types/api.ts` at the hunk level (write a dedup-only version, stage, restore full working tree, verify the leftover unstaged diff was discovery-only).

## Real bug found in first post-push usage, 2026-07-23 (fixed, committed)

Boris processed a real DoorSwap file for a net-new client and saw a stale "No unit files found" message despite the file being found and correctly awaiting confirmation. Root cause: `DiscoveryPage.tsx`'s status-line ternary predated this feature, only branching on `ready`/`requires_group_selection` — every new state fell through to the hardcoded fallback text. Fixed by adding explicit branches for `requires_unit_file_selection` and `requires_format_resolution`, plus a genuine `unit_files_found === 0` check, with a generic "Not ready" catch-all. Committed and pushed: `unitprep-ui@1b9ef84`.

Also confirmed (re-reading real code at Boris's request): the manual-mapping dropdowns are genuinely vendor-agnostic — `document.headers.clone()` in `discover.rs` feeds `source_headers` directly, no vendor-specific branching in that path.

## "Discovery takes 7-10 seconds" report — inconclusive

Same day, server and network path were ruled out by direct measurement: `curl` from within WSL2 to the running `--release` server was 1-4ms round trip; Windows→WSL2 boundary timed via PowerShell was ~114ms cold, 3-6ms warm. Neither explains a 7-10 second gap. Remaining candidates are browser-side (real file size/read time, untested; or Next.js dev-server compile-on-first-hit given Turbopack fragility). Boris was asked to check DevTools timing — not yet followed up.

## Major rework, 2026-07-23: single-file selection replaced with multi-file confirmation

The "one facility per session" assumption turned out to be false: Boris's real test folder (`.../Absolute Management/Wave 3`) had 13 genuinely distinct unit files, and the single-select radio UI silently discarded the rest. Investigation showed `build_batch_from_documents` already treated every unit document as its own `Facility` — the multi-file capability existed in the analysis pipeline the whole time; the artificial constraint was entirely in the discovery/selection layer.

Reworked to checkbox multi-select (all checked by default, select-all/none) with a "Confirm Selection" step; each confirmed file then goes through the existing confirm-or-map flow one at a time via new `current_unit_file_name`/`pending_unit_file_names` fields, with "File X of Y" progress shown. `selected_unit_file_name: Option<String>` became `selected_unit_file_names: Vec<String>` throughout (breaking change, no external consumers).

Per Boris's explicit decision, the same-day "Select File Manually" escape hatch was removed entirely (the checkbox list now gives full visibility/control, making it redundant) — its backend endpoint (`POST /unit-file/upload`) was deleted outright. The equivalent for the *master group* file (`POST /group-file/upload`) was unaffected and stays.

Also fixed: the "vendor not detected" branch had `requires_format_resolution` hardcoded to `false` instead of `true` — dead code before that day, briefly reachable during the manual-upload experiment, then unreachable again after removal. Left the corrected value in place regardless (defensive correctness).

Verified: 191 Rust tests (up from 167), clippy clean; frontend `tsc`/`eslint`/production `next build` clean. Not click-through-tested in a real browser by Claude this session (Claude-in-Chrome wasn't connected) — Boris's own live testing was the verification path.

Two files exceeded the ~250-line alarm from this work: `discover.rs` (386 lines) and `UnitFileResolutionPanel.tsx` (657 lines, now three distinct sections) — flagged, not split yet.

## Follow-up same day (2026-07-23): bulk-confirm, safeguards, navigation redesign

All driven by Boris's own live testing; not committed at the time.

- **Bulk confirm**: "Confirm {vendor}" now resolves every selected file at once instead of one click per file, on the assumption (confirmed correct by Boris) that a folder's confirmed unit files normally share one vendor/shape. Safeguarded by a new `find_header_mismatches` check (order-insensitive header-set comparison, majority-group-wins) exposed as `mismatched_header_files` — non-empty blocks bulk confirmation with an error naming the outlier file(s); `resolve_unit_format.rs` re-verifies server-side rather than trusting the frontend gate. Per-file "Map Fields Manually" is unaffected.
- **Uncommon group name detection**: `unit-group/src/analysis/fingerprint.rs` gained `is_uncommon_group_name()`, reusing existing fingerprint-parsing machinery (no parseable width/length, or a degenerate 0x0, counts as uncommon). Verified against Boris's real Wave-3 examples ("1 bd, 1 ba", "165 sq ft", "Hertz Office Space", "0X0 OFFICE SPACE CLIMATE") as literal test cases. Surfaced as `uncommon_group_names`, shown as a red "Uncommon Group Names" subsection plus a new stat line.
- **Group file format validity**: `group_file_format_valid: Option<bool>` computed via the same `is_group_document` check discovery's own classification uses, applied uniformly whether auto-detected or manually uploaded. `ready` now also requires `group_file_format_valid !== false` and `mismatched_header_files` empty.
- **Navigation redesign**: sections (Unit Files Selection → Confirm Unit File Format → Master Group File) now stack — each completed step renders as a read-only summary that stays visible, with "Return to Unit Files Selection" buttons. The override state (`forceShowUnitFileSelection`) lives in `DiscoveryPage.tsx`, shared by both the panel's own return button and the master-group-file section's equivalent button.
- Fixed a duplicate-button bug: the outer Confirm/Map button row wasn't hidden while manual mapping was open, so "Confirm {vendor}" briefly rendered twice.

Verified: 198 Rust tests (up from 191), clippy clean; frontend clean. Not click-through-tested in a real browser by Claude this session either — same caveat, Boris's live test is the verification path.

## Master-file selection unified + rebuilt, 2026-07-24 session

A regression surfaced first: an unexpected "Select Reference Group File" radio picker appeared, traced to a prior round's relaxation of `is_group_document`'s header check (accepting a minimal 3-header set generic enough to false-positive-match unrelated files). Per Boris's direction, the ambiguous-candidate radio-picker concept was removed entirely in favor of one unified select→validate→confirm flow: "Net New Client" only for the true zero-candidates case, otherwise "Select File" → validity message → an explicit "Confirm" step (`POST /group-file/confirm`, `group_file_confirmed: bool` on session state) → "Select Different File" stays available. `POST /group-file/select` and `requires_group_selection` were deleted at this point.

**Then a legitimate multi-candidate case turned up in real data**, requiring the picker back — but correctly scoped this time. Investigated via direct `curl` end-to-end testing against Boris's real 46-file `Wave 3` folder tree: `group_files_found` came back **14**, not a bug — one master file at the root plus 13 genuinely distinct per-facility copies (confirmed via line-count diff, not duplicates). Re-added `POST /group-file/select`, this time gated correctly on `group_files_found > 1` (not a false-positive header-match inflating the count), with candidates displayed as `parent_folder/filename`. A "Change Vendor"-style "Choose From Discovered Files" button lets the user reopen the list.

**Storage Commander vendor added.** Real export ("Absolute Storage Management ... Franklin Park Units Template.csv") is identical to QSX except `InsideOutside` is named `Locality`, plus two extra columns (`MonitoringEnabled`, `SmartLockEnabled`). Added as a new `VendorFormat`, deliberately listed *before* `QSX` in `VENDOR_FORMATS` since its signature is a strict superset of QSX's own (`detect_vendor` returns the first match, so checking QSX first would misclassify every Storage Commander export). The two comparison files Boris first gave turned out to be mismatched (a tenant export vs. a real unit file in the same reference folder) — caught by actually reading both files rather than trusting file names.

**Discovered-groups list** iterated through a few placements before landing inside `UnitFileResolutionPanel.tsx`, right after "Unit Files Selected" is confirmed and before "Confirm Unit File Format" — the only way to literally interleave it given React's component tree. Required `discovered_group_names`'s backend computation to stop waiting on full format resolution — it now uses each selected file's detected-or-already-resolved vendor mapping directly, so the list populates as soon as file selection is confirmed.

## Browser verification technique (new capability this session)

Created a throwaway client through the actual UI (via the in-app Browser pane) to get a real browser-trusted `clientId`, then drove real backend session IDs (built via direct `curl` calls replaying upload→discover→select→confirm against Boris's real 46-file folder) through that client's actual pages. This combination — real backend state via curl, real frontend rendering via the browser tool — let Group Needing Review cards, radio-picker candidates, and file-name formatting all get checked against literal real output rather than inferred from code reading. Worth reusing for future UI verification in this project, since a folder-picker dialog itself can't be automated.

## Status

The 2026-07-23/24 continuation described above (master-file unification, Storage Commander, bulk-confirm, uncommon-group-name detection, navigation redesign) was **committed 2026-07-25** as part of `unitprep-api@ace8ff6` / `unitprep-ui@0cd2130` — see [[Validation & Warnings Redesign]] for the commit details (both repos' discovery and validation work landed together in one commit each, not split further).
