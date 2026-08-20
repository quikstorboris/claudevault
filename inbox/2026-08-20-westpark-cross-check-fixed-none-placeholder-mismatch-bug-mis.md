---
date: 2026-08-20
description: "Boris ran dedup against a real Westpark facility file, then had a colleague's independent skill review the output. The review surfaced a real regressi"
tags:
  - project-note
source_repo: bmaksimov
---

# Westpark cross-check: fixed None-placeholder mismatch bug, misleading typo-variant wording, and XLSX export formatting

Boris ran dedup against a real Westpark facility file, then had a colleague's independent skill review the output. The review surfaced a real regression of a previously-fixed bug class (the "None" placeholder), a genuinely misleading UI label, and several real XLSX export formatting defects (255-char column blowout, no wrap/freeze/autofilter, unmerged banner rows, a leading-apostrophe artifact on PhoneNumberPrefix). Investigated each against the actual code and the vault's own prior fix history, fixed the real bugs, and left one finding (duplicate rows across the three report sections) as an open product decision rather than picking a fix unilaterally.

## What changed

- dedup/src/normalization.rs - moved PLACEHOLDER_TOKENS/is_placeholder here from relatedness/mod.rs (now pub(crate), shared) so comparison.rs could reuse the exact same list rather than growing a second copy
- dedup/src/comparison.rs - field_matches_across/blank_aware_key now treat a FieldKind::Plain placeholder ("None", "N/A", ...) as blank, via a new is_blank_for_comparison + comparison_key pair; deliberately scoped to Plain only, NOT Phone/Address, to preserve the existing (tested) rule that a garbage phone value still counts as a real mismatch against blank
- dedup/src/relatedness/mod.rs - now imports is_placeholder from normalization instead of defining its own copy; no behavior change
- src/api/dedup_view.rs - TypoVariantView gained differing_categories (via unitprep_dedup::comparison::find_differing_categories on the combined pair, Name category filtered out) so the UI can name what actually differs instead of a bare matches/differs boolean
- unitprep-ui/types/api.ts + components/dedup/TypoVariantsSection.tsx (+ .test.tsx) - render "Contact info differs: {categories}" instead of a bare "Contact info differs"
- src/infrastructure/dedup_xlsx_export.rs - removed csv_safety::sanitize_cell (verified via rust_xlsxwriter's own store_string source: it never inspects a string's leading character, so the CSV-specific CWE-1236 mitigation guards against nothing in a real .xlsx and was only producing the reported '+1' artifact); added set_autofit_max_width(300) before autofit() (the library's own documented fix for the 255-char blowout), an explicit 60-wide wrapped Note column, set_freeze_panes(1,0), autofilter over the full range, and merge_range+fill for section banner rows (previously a bare unstyled cell in column A)
- src/infrastructure/csv_safety.rs - doc comment now explicitly scopes the mitigation to CSV writers and cross-references why dedup_xlsx_export.rs deliberately doesn't use it
- dedup/RULES.md - updated rules 2, 3, and the Export section in the same change, per this file's own "update in the same change, not after" convention


## Decisions

- The None-placeholder carve-out is scoped to FieldKind::Plain fields only in comparison.rs, NOT extended to Phone/Address there (unlike relatedness.rs, which excludes placeholders from every signal regardless of kind) - a garbage Phone/Address value is still meaningfully different from blank for a facility manager's correction purposes; verified this wouldn't regress by writing a placeholder-token-as-phone-value regression test alongside the fix, and confirmed the existing 'garbage phone differs from blank' test still passes
- Removed sanitize_cell from the XLSX writer entirely rather than keeping it 'just in case' - verified via direct inspection of rust_xlsxwriter 0.96.0's store_string source that it performs zero leading-character type inference, so the mitigation had no security value there, only a cosmetic cost. Kept it unchanged for the CSV writer and auth_users.rs's own CSV export, where the threat model genuinely applies
- Did NOT implement either of the reviewer's two suggested fixes for duplicate rows across the flagged/typo-variant/related-tenant sections (dedupe to one row per unit, or split into separate tabs) - this is the same 'output format is an unresolved product decision' question already on record in project memory, and picking one unilaterally would be a real UX decision affecting how a facility manager reads the report, not a bug fix. Surfaced back to Boris instead.
- Left the two 'substantive findings' (Alvaro Lazo's cross-contaminated email, Eduardo Villalobos unit 517 possibly a different person) and the 'field misuse' observations (free-text notes stuffed into address fields) as data-quality findings with no code change - the tool correctly reported what the source data actually contains; there's nothing to fix in the comparison logic itself for these.


## Learned

- rust_xlsxwriter's set_autofit_max_width()/autofit() combination is the library's own documented, recommended fix for the exact 255-character/1790-pixel column-blowout problem a long free-text column (like a correction note) causes - found by reading the method's own doc comment, which describes the symptom almost verbatim before recommending 300px as 'a good compromise'
- A CSV-injection mitigation (leading-apostrophe prefix for cells starting with =/+/-/@) that's correct and necessary for a real CSV writer can be actively harmful (a visible artifact, zero security benefit) when applied uniformly to an XLSX writer too - genuine XLSX cells carry explicit type metadata the spreadsheet app trusts instead of re-inferring from raw text, so there's no formula-reinterpretation risk to guard against there. Worth checking the actual writer library's source (not just assuming 'CSV and XLSX need the same treatment') before applying a CSV-specific mitigation to a binary spreadsheet format.


## Verification

cargo test --workspace: all crates green (unitprep bin 330 passed incl. 5 new/changed dedup_view + dedup_xlsx tests, unitprep-dedup 74 passed incl. 2 new comparison.rs regression tests + 1 new ingest-level ESS test carried over from a prior session, others unchanged), 0 failed, 5 ignored (real-fixture/real-Postgres tests needing external setup). cargo clippy --workspace --all-targets -- -D warnings: clean. The XLSX formatting fixes were verified against the real generated file's raw OOXML (unzipped sheet1.xml checked directly for <pane ySplit="1">, <autoFilter>, <mergeCell>, and an explicit width on the Note column) rather than trusting the API calls compiled - calamine (the existing read-back test helper) has no concept of formatting metadata, so this required a new raw-XML test. Frontend: tsc --noEmit and eslint clean on every changed file; vitest itself could not run (see Open).


## Open

- Duplicate rows across the three report sections (a tenant flagged AND a typo-variant AND a related-tenant can each independently re-emit that tenant's full row set) - genuinely unresolved, needs Boris's direction: de-duplicate to one row per unit with stacked notes, split into separate tabs/sections, or leave as-is now that each section's own findings are individually more precise.
- Could not run the frontend's actual vitest suite in this session - only a Linux-native rolldown native binding is installed in unitprep-ui's node_modules, but only Windows-side Node was reachable from this WSL session, so `npm test` fails on a missing native binding before any test runs. Verified via tsc --noEmit and eslint instead (both clean) plus careful manual review of the Testing Library matcher logic. Whoever normally runs `npm test` on this machine should confirm the new/changed TypoVariantsSection tests actually pass.



_Recorded 2026-08-20T16:33:34.698Z from `bmaksimov` via the om MCP server (routing: fallback)._
