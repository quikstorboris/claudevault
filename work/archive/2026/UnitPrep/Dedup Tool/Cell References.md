---
date: 2026-07-27
description: "The spreadsheet cell-reference feature: bracketed CSV cell refs (2026-07-16), and the later shared on-screen/export cell-ref plumbing (2026-07-22)"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Cell References

Part of [[Dedup Tool Index]]. How dedup's correction notes came to cite specific spreadsheet cells.

## Spreadsheet cell-reference feature — implemented 2026-07-16

Explicitly requested after the second real-data cross-check (see [[Real-Data Cross-Checks]]), which surfaced `spreadsheet_cell_references_in_notes` as a pattern the reference tooling had that this crate lacked.

`dedup_csv_export.rs` now appends a bracketed cell-reference clause to each flagged group's/typo-variant's `CorrectionNote`, e.g. `"...  [AlternateContactAddressStreet1: U2=(blank), U3=(blank), U4=(blank), U5=160 NE Santa Maria Ln; ...]"` — same bracket format as the reference script (`note + "  [" + refs + "]"`), but column letters/values computed from **our own** output layout (`COLUMNS`), not copied from the reference script's differently-shaped CSV (confirmed by comparing real output: same values, different letters, because the two tools' column layouts differ — expected and correct).

Architecture, deliberately kept layered: the plain-English per-field/per-unit detail (from the prior day's note-enrichment change, see [[Note Enrichment & Copy Redesign]]) still lives in `unitprep-dedup`'s `note_composer.rs` — spreadsheet-agnostic, useful in the JSON/UI too. The cell-reference suffix is computed **only** in `dedup_csv_export.rs` (the export/infrastructure layer, already the only place that knows the actual column order and can track row numbers as it writes) — keeps the domain crate free of export-format concerns.

Row numbers are assigned with a single running counter threaded through the write functions (starts at 2, since row 1 is the header) rather than a separate two-pass "assign all row numbers first" step like the reference script uses — possible here because groups are always written as contiguous blocks, so a group's own row range is just arithmetic from the counter's current value, no pre-scan needed.

`FieldName` (internal enum, `AltContact*`) needed a new explicit mapping to the CSV's own column names (`AlternateContact*`) since the two naming schemes diverge — `csv_column_name()`, a plain exhaustive `match` (compiler-enforced, so a typo'd column name is a compile error, not a silent no-op). Typo-variant candidates don't store field-level mismatch detail themselves (`TypoVariantCandidate` only carries a `contact_info_matches: bool`), so their cite-list is recomputed on demand via `unitprep_dedup::comparison::find_differing_categories` over the two groups' combined records — always cites `FirstName`/`LastName` (the whole premise of a typo-variant candidate), plus every other differing field when contact info doesn't already match.

**Verified**: 5 new unit tests in `dedup_csv_export_tests.rs` — `col_letter` spreadsheet-letter math, the `FieldName`→CSV-column mapping (asserts every mapped name actually exists in `COLUMNS`, catching drift), exact-string cell-reference formatting, and — the most load-bearing one — an end-to-end `generate_csv` test with two flagged groups proving the *second* group's cell references land on the rows it's actually written at (after group one's rows *and* the blank separator row), not just "starting from row 2" — exactly the bug class the reference script's own implementation notes warn about. Full workspace suite: 113 tests passing (2 correctly `#[ignore]`d), clippy clean. Live-verified against the real Pad-N-Loc file a third time: rebuilt, re-ran, confirmed the exported CSV's cell references match the reference script's own values (differing only in column letters, as expected given the two tools' different column layouts).

**250-line flag**: `dedup_csv_export.rs` grew to 315 lines (was 173 before this change) — crossed the alarm threshold ([[Patterns#UnitPrep: flag modules approaching ~250 lines]]). Flagged rather than silently split; genuinely cohesive ("build the one CSV artifact"), so a split wasn't obviously warranted, but worth a deliberate look next time this file is touched.

## Shared cell-ref plumbing extracted for xlsx (2026-07-17)

When xlsx export was added (see [[XLSX Export & RULES]]), the `cell_refs` submodule (col-letter math, the `FieldName`→column-name map, `note_with_cell_refs`) moved out of being CSV-specific and into the new shared `dedup_export_plan.rs` module, gaining `first_cell_ref` for the xlsx hyperlink target — see that note for the full extraction rationale (avoiding CSV/xlsx logic drift) and the real `PlannedRow` lifetime issue hit along the way.

## On-screen cell references (2026-07-22 redesign)

As part of the note-copy redesign (see [[Note Enrichment & Copy Redesign]]), cell references also needed to appear in the live UI, not just in exported files — and had to be *guaranteed* to match whatever a subsequent real export would produce. Solved by reusing the exact same `dedup_export_plan::build_export_plan` function the real CSV/xlsx export already calls (pure/deterministic given `report`+`records`, no I/O): a new `src/api/dedup_view.rs` calls it at `/dedup/check`/`/dedup/report` time (before any real export happens) and walks the returned row plan to recover each flagged group's first-row/record-count. New `field_cell_refs()` in `cell_refs.rs` is the structured (not flat-string) counterpart to `note_with_cell_refs`, feeding the new `FlaggedGroupView`/`BulletView` API response DTOs. `unitprep-dedup`'s own domain types stay untouched — no column-layout concept leaks into the domain crate; the enrichment happens entirely at the API layer. `/dedup/export` itself was untouched by this change.

Live-verified: unzipped a real exported xlsx and read its raw XML directly to confirm the on-screen bullet's cell reference (`I2`/`I3`) really corresponds to the real `PhoneNumber` column and the real per-unit blank/filled cells in the exported file.

## Related

- [[Dedup Tool Index]]
- [[XLSX Export & RULES]]
- [[Note Enrichment & Copy Redesign]]
- [[Real-Data Cross-Checks]]
- [[Patterns#UnitPrep: flag modules approaching ~250 lines]]
