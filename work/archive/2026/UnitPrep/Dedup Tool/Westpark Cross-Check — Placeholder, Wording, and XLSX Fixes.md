---
date: 2026-08-20
description: "A colleague's independent skill review of a real Westpark dedup run surfaced a regressed placeholder bug, misleading typo-variant wording, and real XLSX export formatting defects — investigated and fixed."
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Westpark Cross-Check — Placeholder, Wording, and XLSX Fixes

Boris ran dedup against a real Westpark facility file, then had a colleague's independent skill review the output — the same cross-check pattern as [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]]. The review surfaced a real regression of a previously-fixed bug class (the "None" placeholder, see [[Related-Tenant Detection]]), a genuinely misleading UI label, and several real XLSX export formatting defects (255-char column blowout, no wrap/freeze/autofilter, unmerged banner rows, a leading-apostrophe artifact on `PhoneNumberPrefix`). Investigated each against the actual code and this vault's own prior fix history, fixed the real bugs, and left one finding (duplicate rows across the three report sections) as an open product decision rather than picking a fix unilaterally.

**Shipped**: committed and pushed to `origin/main` as `unitprep-api@73638e0..77896be` (the placeholder fix, the typo-variant wording fix, the XLSX export fixes, and a RULES.md doc-only commit covering all three) and `unitprep-ui@3f4881e` (the typo-variant wording UI change) — see [[New Laptop Migration — QSLP14]] for how the actual commit history was later re-verified against `origin/main` from a fresh clone.

## What changed

- `dedup/src/normalization.rs` — moved `PLACEHOLDER_TOKENS`/`is_placeholder` here from `relatedness/mod.rs` (now `pub(crate)`, shared) so `comparison.rs` could reuse the exact same list rather than growing a second copy
- `dedup/src/comparison.rs` — `field_matches_across`/`blank_aware_key` now treat a `FieldKind::Plain` placeholder ("None", "N/A", ...) as blank, via a new `is_blank_for_comparison` + `comparison_key` pair; deliberately scoped to `Plain` only, NOT `Phone`/`Address`, to preserve the existing (tested) rule that a garbage phone value still counts as a real mismatch against blank
- `dedup/src/relatedness/mod.rs` — now imports `is_placeholder` from `normalization` instead of defining its own copy; no behavior change
- `src/api/dedup_view.rs` — `TypoVariantView` gained `differing_categories` (via `unitprep_dedup::comparison::find_differing_categories` on the combined pair, `Name` category filtered out) so the UI can name what actually differs instead of a bare matches/differs boolean
- `unitprep-ui/types/api.ts` + `components/dedup/TypoVariantsSection.tsx` (+ `.test.tsx`) — render "Contact info differs: {categories}" instead of a bare "Contact info differs"
- `src/infrastructure/dedup_xlsx_export.rs` — removed `csv_safety::sanitize_cell` (verified via `rust_xlsxwriter`'s own `store_string` source: it never inspects a string's leading character, so the CSV-specific CWE-1236 mitigation guards against nothing in a real `.xlsx` and was only producing the reported `'+1` artifact); added `set_autofit_max_width(300)` before `autofit()` (the library's own documented fix for the 255-char blowout), an explicit 60-wide wrapped Note column, `set_freeze_panes(1,0)`, an autofilter over the full range, and `merge_range`+fill for section banner rows (previously a bare unstyled cell in column A)
- `src/infrastructure/csv_safety.rs` — doc comment now explicitly scopes the mitigation to CSV writers and cross-references why `dedup_xlsx_export.rs` deliberately doesn't use it
- `dedup/RULES.md` — updated rules 2, 3, and the Export section in the same change, per this file's own "update in the same change, not after" convention

## Decisions

- The None-placeholder carve-out is scoped to `FieldKind::Plain` fields only in `comparison.rs`, NOT extended to `Phone`/`Address` there (unlike `relatedness.rs`, which excludes placeholders from every signal regardless of kind) — a garbage Phone/Address value is still meaningfully different from blank for a facility manager's correction purposes; verified this wouldn't regress by writing a placeholder-token-as-phone-value regression test alongside the fix, and confirmed the existing "garbage phone differs from blank" test still passes.
- Removed `sanitize_cell` from the XLSX writer entirely rather than keeping it "just in case" — verified via direct inspection of `rust_xlsxwriter` 0.96.0's `store_string` source that it performs zero leading-character type inference, so the mitigation had no security value there, only a cosmetic cost. Kept it unchanged for the CSV writer and `auth_users.rs`'s own CSV export, where the threat model genuinely applies.
- Did NOT implement either of the reviewer's two suggested fixes for duplicate rows across the flagged/typo-variant/related-tenant sections (dedupe to one row per unit, or split into separate tabs) — this is the same "output format is an unresolved product decision" question already on record in project memory, and picking one unilaterally would be a real UX decision affecting how a facility manager reads the report, not a bug fix. Surfaced back to Boris instead (still open as of this note).
- Left the two "substantive findings" (a tenant's cross-contaminated email, a unit possibly belonging to a different person) and the "field misuse" observations (free-text notes stuffed into address fields) as data-quality findings with no code change — the tool correctly reported what the source data actually contains; there's nothing to fix in the comparison logic itself for these.

## Learned

- `rust_xlsxwriter`'s `set_autofit_max_width()`/`autofit()` combination is the library's own documented, recommended fix for the exact 255-character/1790-pixel column-blowout problem a long free-text column (like a correction note) causes — found by reading the method's own doc comment, which describes the symptom almost verbatim before recommending 300px as "a good compromise."
- A CSV-injection mitigation (leading-apostrophe prefix for cells starting with `=`/`+`/`-`/`@`) that's correct and necessary for a real CSV writer can be actively harmful (a visible artifact, zero security benefit) when applied uniformly to an XLSX writer too — genuine XLSX cells carry explicit type metadata the spreadsheet app trusts instead of re-inferring from raw text, so there's no formula-reinterpretation risk to guard against there. Worth checking the actual writer library's source (not just assuming "CSV and XLSX need the same treatment") before applying a CSV-specific mitigation to a binary spreadsheet format.

## Verification

`cargo test --workspace`: all crates green (unitprep bin 330 passed incl. 5 new/changed `dedup_view` + `dedup_xlsx` tests, `unitprep-dedup` 74 passed incl. 2 new `comparison.rs` regression tests, others unchanged), 0 failed, 5 ignored (real-fixture/real-Postgres tests needing external setup). `cargo clippy --workspace --all-targets -- -D warnings`: clean. The XLSX formatting fixes were verified against the real generated file's raw OOXML (unzipped `sheet1.xml` checked directly for `<pane ySplit="1">`, `<autoFilter>`, `<mergeCell>`, and an explicit width on the Note column) rather than trusting the API calls compiled — `calamine` (the existing read-back test helper) has no concept of formatting metadata, so this required a new raw-XML test.

Frontend `tsc --noEmit`/`eslint` were clean at the time, but the actual `npm test` (vitest) suite could **not** be run in that session — the WSL environment only had a Linux-native `rolldown` binding installed with Windows-side Node reachable, so it failed before any test ran. **Resolved in [[New Laptop Migration — QSLP14]]**: on the replacement machine, native Linux Node (via `nvm`) actually works, and a full `npx vitest run` came back 333/333 passing, including both `TypoVariantsSection` tests this note's fix added.

## Open

- Duplicate rows across the three report sections (a tenant flagged AND a typo-variant AND a related-tenant can each independently re-emit that tenant's full row set) — genuinely unresolved, needs Boris's direction: de-duplicate to one row per unit with stacked notes, split into separate tabs/sections, or leave as-is now that each section's own findings are individually more precise.

## Related

- [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]] — the earlier colleague-cross-check session this one repeats the pattern of, including the original "None" placeholder fix this note found a gap in.
- [[Related-Tenant Detection]] — where the placeholder-token guardrail originally shipped, scoped to relatedness only.
- [[XLSX Export & RULES]]
- [[Dedup Tool Index]]
- [[Shared Vendor-Format Registry (Easy Storage Solutions)]] — the preceding piece of work in the same session.
- [[New Laptop Migration — QSLP14]] — where the vitest gap this note flagged as open actually got resolved.
