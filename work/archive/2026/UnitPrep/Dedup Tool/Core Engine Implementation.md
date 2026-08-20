---
date: 2026-07-27
description: "The unitprep-dedup domain crate: algorithm implementation, module architecture, 250-line file splits, and the RULES-vs-config-file decision"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Core Engine Implementation

Part of [[Dedup Tool Index]]. The domain-logic-only `unitprep-dedup` crate — grouping/normalization/comparison/note-assignment engine plus the fuzzy-name safety net — built after the business rules were settled (see [[Business Logic & Reference Script]]) and before session/API wiring (see [[Session, API & Scope Decisions]]).

## Agreed starting point (2026-07-15)

Start with `unitprep-dedup` as a pure crate, tested directly against three real fixture pairs (New Castle, No Ka Oi, `duplicate_check_results.csv` — see [[Real-Data Cross-Checks]]). Fully unblocked at the time since it depended on none of the open product/architecture decisions (output format, session shape). Session wiring, the API layer, and the export format were deliberately deferred.

## Implemented and verified against real data (2026-07-15)

All six deliberately-stubbed algorithms were filled in: address normalization, the `difflib.SequenceMatcher.ratio()`-compatible similarity port, grouping, category comparison, the email-special-case note, and typo-variant candidate detection. 10 unit tests cover the ported algorithms directly (similarity calibration set, address normalization edge cases); see [[Real-Data Cross-Checks]] for the two integration-test bugs this pass caught (typo-variant scope, the CSV parser trailing-column gap).

## Architecture/scope decisions (2026-07-15, continued)

- **`unit-group` domain-extraction inconsistency, acknowledged as real**: `dedup` was built fully extracted from day one while `unit-group`'s real domain logic still lived in the binary's `src/domain/`. Agreed as a genuine inconsistency worth fixing, scoped as its own future migration chapter — riskier than adding dedup, since it means moving live, tested, wired-in code, not writing in empty space. **Order agreed: finish dedup first, then do the unit-group extraction** — a firm commitment. See [[Code Review Watchlist]] item on full `unit-group` extraction. (Both were subsequently completed and pushed together — see [[Session, API & Scope Decisions]].)
- **Output format fully resolved, simpler than expected**: CSV only — QMS is CSV-only on the input side, so no `.xlsx` writer was needed at first (later reversed — see [[XLSX Export & RULES]] for the follow-up decision to add xlsx alongside CSV). The old two-sheet `Draft_1`/`Duplicate Tenants` presentation was downgraded to a low-priority future enhancement at most — multi-tab source files are rare in practice.
- **"Re-check two pulls over time" tabled entirely**, not just deprioritized. Considered a stateless variant (operator supplies both new and previous pull as two inputs to one request, no server-side persistence) but even that was judged awkward — belongs with whatever future conversation introduces real persistence/a database.
- **MVP scope clarified**: the tool's job stops at *identifying and listing* inconsistencies. No corrective action, no in-app confirm/dismiss step — corrections happen entirely outside the platform, by the client (facility manager) the report is prepared for. "Always flag, never auto-merge" means *list everything*, not *make the platform decide*.

## 250-line file splits (standing practice — see [[Patterns#UnitPrep: flag modules approaching ~250 lines]])

Boris's guidance refined 2026-07-15: the 250-line number itself was always arbitrary and isn't a strict cap — overage is fine when warranted and elegance/maintainability are preserved. What matters is flagging it for a deliberate look whenever a file crosses it, not silently continuing to grow it.

- `core/src/parsing_tests.rs` — **RESOLVED 2026-07-15**: was 312 lines (265 before this session's 2 added CSV tests). Split into `core/src/parsing/{csv_tests,excel_tests,dispatch_tests}.rs`, mirroring the existing `parsing/{csv,excel,spreadsheetml}.rs` module split. `core/src/lib.rs`'s old `mod parsing_tests;` removed. All 25 core tests still passed unchanged. Resulting sizes: 15/134/164 lines respectively — `spreadsheetml.rs` (452, own inline tests) deliberately left alone.
- `dedup/src/types.rs` — **RESOLVED 2026-07-15**: was 255 lines. Split into `dedup/src/types/fields.rs` (the field taxonomy — `FieldCategory`/`FieldKind`/`FieldName`/`FieldSpec`/`FIELD_SPECS`/`CATEGORY_PRIORITY`, 103 lines) and `types.rs` itself (record/result types — `TenantRecord`, `TenantGroup`, `FlaggedGroup`, `FieldMismatch`, `FieldValueMismatch`, `TypoVariantCandidate`, 161 lines), with `types.rs` re-exporting the taxonomy so every existing `crate::types::X` import elsewhere kept working — purely mechanical, zero behavior change. All 99 workspace tests still passed.

## RULES.md vs. a centralized config file (architecture side-discussion, 2026-07-17)

Boris asked whether dedup's rules should move into one centralized module or an external config file, anticipating more rules surfacing over time. Recommended against both: the crate is already organized by *kind* of rule (one module per concern — taxonomy, comparison, similarity, normalization, notes), which scales by adding a new module per new kind of rule (exactly what `relatedness.rs` did, see [[Related-Tenant Detection]]); a config file would trade away this project's deliberate compile-time-safety principle (closed enums so a typo'd field name is a compile error, not a silent no-op — the same reasoning that already fixed three header-normalization bugs elsewhere) for marginal convenience on values that change rarely and deliberately.

What actually addresses the underlying want (one place to see all current rules) is `dedup/RULES.md` — written this session: plain-English, one section per rule with a pointer to its implementing module, an explicit "update this file in the same change" instruction, and a documented "how to add a new rule" section at the end. Meant to be useful to both a human and a future AI session picking this crate back up.

## Related

- [[Dedup Tool Index]]
- [[Business Logic & Reference Script]]
- [[Real-Data Cross-Checks]]
- [[Related-Tenant Detection]]
- [[Session, API & Scope Decisions]]
- [[XLSX Export & RULES]]
- [[Patterns#UnitPrep: flag modules approaching ~250 lines]]
- [[Code Review Watchlist]]
