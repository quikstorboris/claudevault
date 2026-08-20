---
date: 2026-07-27
description: "Custom-notes mechanism (NoteComposer), field/value enrichment, and the 2026-07-22 plain-English/real-names copy redesign for dedup correction notes"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Note Enrichment & Copy Redesign

Part of [[Dedup Tool Index]]. How dedup's human-facing correction notes evolved from flat category labels to real per-field, per-unit, plain-English copy — culminating in the **2026-07-22 redesign** (this section's most current state; earlier subsections are superseded but preserved for history).

## "Custom notes" mechanism, implemented 2026-07-15

Boris raised that Claude-driven skill runs produce tailored, human-toned explanations per finding, and asked for a mechanism to do this without an LLM in the runtime path — explicitly flagged as a future AI-integration point.

Implemented as a clean seam rather than folding phrasing into the matching logic:

- `types::FieldMismatch` now carries a `FieldValueMismatch` per differing field (field name + the actual distinct raw values seen, blank shown as `"(blank)"`, sorted blank-last) — not just *that* a field differs, but *what* the differing values are. `comparison::find_differing_categories` updated accordingly.
- New `note_composer` module: a `NoteComposer` trait (`compose_group_note`, `compose_variant_note`) plus `TemplateNoteComposer`, the v1 deterministic, no-I/O default — produces notes naming actual units and, for typo-variant candidates, actual tenant names (e.g. "Please update the email address to match across units 2008, 2123." instead of "across all units"). `notes.rs` now holds only text templates (placeholders) — no decision logic. `report::run` delegates to `run_with_composer(records, composer)`, defaulting to `TemplateNoteComposer`; a future `LlmNoteComposer` would implement the same trait against the same structured input and could be swapped in via that same injection point — nothing else in the pipeline would need to change.
- Distinguished from a separate, coarser concern: the *overall report's* tone/layout for a non-technical facility manager (plain-English bullets by unit, no tables) is an export/presentation-layer question, not the same thing as per-finding note text.
- 5 new unit tests, plus the 2 real-data integration tests updated for the new wording. 99 workspace tests total, zero failures/warnings.

## Correction-note enrichment, implemented and verified 2026-07-16

Prompted by the Pad-N-Loc comparison (see [[Real-Data Cross-Checks]]). The real gap: for the 6 non-typo flagged groups, the exported `CorrectionNote` only ever named the *category* that differs ("Please update the alternate contact info to match across units D-11, J-10, J-48, K-9") — never *which* field or *what* the actual differing values are, even though that data was already computed and already rendered in the UI's "what differs" detail. Deliberately did **not** copy the chat skill's spreadsheet-cell-reference format (`AF10=6194431007, AF11=...`) — coupled to a row/column layout that doesn't exist in this pipeline's model (that format was later built properly at the export layer instead — see [[Cell References]]).

`dedup/src/note_composer.rs`'s `TemplateNoteComposer::compose_group_note` now appends a second sentence describing every differing field with real per-unit attribution, computed directly from `TenantGroup.records` (e.g. `"AltContactPhoneNumber: 3605525629 on unit S-31, 3607281619 on units D-216, H-8, S-10, S-52, S-53, (blank) on unit S-51."`). Caught and fixed a related latent bug: the old code picked only the single highest-priority differing category for the whole note and silently dropped every other differing category's detail if a group had more than one (didn't affect Pad-N-Loc's results, which only ever had one category — `AltContact` — per group, but would have on a group with both a phone and an address mismatch). The new version still leads with the same category-priority sentence but the detail sentence now covers every differing category.

Verified: 2 tests updated/added (exact-string assertion on the new detail format, plus a new 3-way multi-field test mirroring the real Carlos Humberto Pascual Alejandro shape), 16/16 dedup-crate tests, full workspace (108 tests, 2 real-data integration tests correctly `#[ignore]`d) passing, clippy clean. Live-verified against the real Pad-N-Loc file a second time after rebuilding — confirmed enriched notes render correctly both in the `/dedup/check` JSON and the `/dedup/export` CSV (proper quoting held up with the longer, comma-and-semicolon-bearing note text). No frontend API/type changes needed — `note` was already a plain `string` field.

## Note-copy/presentation redesign — implemented and verified 2026-07-22

Boris ran a real file through the live UI and pushed back hard on tone: raw grouping keys as headers ("johnhawkins" not "John Hawkins"), ALL-CAPS names, one dense "Specifically: Field: v1 on units X; ..." paragraph, and "unit(s)" not agreeing in number ("units 2" when there's only one unit). Iterated wording examples in chat first (several rounds) before writing any code — landed on:

- Organize strictly per tenant (never regroup by mismatch category).
- A "Mismatches: Phone, Email, ..." summary line per card (every differing category, not just the priority-picked lead).
- One plain-English bullet per **actually differing field** (no collapsed "full address" — only the field(s) that disagree get a bullet).
- Real cell references into the **exported** CSV/xlsx specifically (confirmed, not the source file) — see [[Cell References]] for the mechanism.
- A ❓ tooltip only on Company-name mismatches (tenant-portal-login consequence) — explicitly not yet extended to other categories.

Key implementation points:

- `TenantRecord::display_name()` (`types.rs`) now Title Cases instead of uppercasing — a private `title_case()` helper, no new dependency.
- Every note template in `notes.rs` changed its placeholder from hardcoded `"units {units}"` to bare `"{units}"` — a new `note_composer::units_phrase()` substitutes the whole word+number phrase ("unit 13" / "units 54, 67, and 77", Oxford comma) so singular/plural is never wrong again. `describe_field` picked "but" vs "and" as the final connector based on whether the blank value sorts last — comma-before-"but" always, comma-before-"and" only at 3+ items.
- **The one real architectural addition**: cell references for the on-screen UI reuse the *exact same* `dedup_export_plan::build_export_plan` the real CSV/xlsx export already uses (pure/deterministic given `report`+`records`, no I/O) — a new `src/api/dedup_view.rs` calls it at `/dedup/check`/`/dedup/report` time (before any real export happens) and walks the returned row plan to recover each flagged group's first-row/record-count, so an on-screen reference is guaranteed to point at the same cell a subsequent real export would. New `field_cell_refs()` in `cell_refs.rs` is the structured (not flat-string) counterpart to `note_with_cell_refs`. `dedup`'s own domain types deliberately stay untouched (no column-layout concept leaks in) — the enrichment happens entirely at the API layer, in new response DTOs (`FlaggedGroupView`/`BulletView`/`TypoVariantView`/`RelatedTenantView`/`DedupReportView`) that replace the raw `DedupReport` as what `/dedup/check`/`/dedup/report` return. `/dedup/export` itself is untouched.
- Frontend: new `components/Tooltip.tsx` (no tooltip component existed before; minimal hover/focus popover, no dependency), new `lib/format.ts` (`formatUnits`, mirrors the Rust phrasing rule for the couple of UI spots that format a raw `units: string[]` client-side). `FlaggedGroupsSection.tsx` rewritten around the new view shape (real name/units header, mismatches line, bullet list with cell refs + Company tooltip, old raw "what differs" table retired). Typo-variant and related-tenant sections also updated for real display names (`group_keys`/`key_a`/`key_b` replaced with resolved names+units end-to-end) even though their note *text* needed no separate fix.

**Verified three ways**: full workspace `cargo test` (209 tests, all crates) after fixing several stale test assertions the rewrite broke on purpose (old exact-uppercase-name and old comma-joined-units expectations, including two `#[ignore]`d real-data reference-fixture assertions, corrected to check only the part re-verifiable without the external files, with an explicit comment left about the pre-existing unrelated gap found there); `tsc`/`eslint` clean on every changed frontend file; and a live end-to-end run — rebuilt+restarted the real server, drove a synthetic CSV through `/dedup/check` then `/dedup/export` (xlsx), unzipped the actual xlsx and read its raw XML directly to confirm the on-screen bullet's cell reference (`I2`/`I3`) really corresponds to the real `PhoneNumber` column and the real per-unit blank/filled cells in the exported file.

## Open, not fully reconciled

The `client_summary_style_guidance` tension flagged in [[Business Logic & Reference Script]] (plain-English guidance vs. an increasingly technical internal CSV) was substantially addressed by this redesign for the on-screen UI, but the underlying question — is the exported CSV itself ever handed directly to a facility manager, or is it strictly an internal-review artifact — was never explicitly re-confirmed with Boris as closed.

## Related

- [[Dedup Tool Index]]
- [[Cell References]]
- [[Business Logic & Reference Script]]
- [[Real-Data Cross-Checks]]
- [[Dedup UI]]
