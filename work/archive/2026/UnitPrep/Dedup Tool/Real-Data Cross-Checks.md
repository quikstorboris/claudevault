---
date: 2026-07-27
description: "Fixture verification and independent real-facility cross-checks (New Castle, No Ka Oi, Pad-N-Loc, a third facility) confirming the Rust port matches the reference skill"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Real-Data Cross-Checks

Part of [[Dedup Tool Index]]. Findings from running the dedup tool (both the reference Python skill and the eventual `unitprep-dedup` Rust crate) against real client exports. See [[Business Logic & Reference Script]] for the rule reverse-engineering these checks were validating.

## New Castle Self Storage — sample-pair usability, resolved 2026-07-15

The `New Castle Self Storage _ Duplicate Tenants.xlsx` sitting next to `NCSS_QMS_End_Users_Template.csv` under `KoBre Dropbox\...\New Castle Self Storage\...\1st PrePull - 03-06-2026\` turned out to be the two-sheet `Draft_1`/`Duplicate Tenants` improvised-presentation format (confirmed by opening it: `Group`/`Issues` columns, 71-col passthrough) — **not** the reference script's real output shape, so it couldn't be diffed against a Rust port's output to verify correctness.

Fixed by generating real ground truth instead of relying on the found file:
1. Re-ran the current reference script against the No Ka Oi input and diffed the result against `KAH_duplicate_check_results_first_pass.csv` — **byte-for-byte identical**, confirming the installed skill script is exactly the version already verified.
2. Ran the same script against `NCSS_QMS_End_Users_Template.csv` to generate a genuine New Castle output: 168 rows, 116 unique tenants, 15 multi-unit, exactly one flagged group — Louis Williams units F3/F5, alternate-contact mismatch — and zero typo-variant candidates.

Both regenerated outputs saved to that session's scratchpad (`dedup-fixtures/KAH_regenerated.csv`, `dedup-fixtures/NCSS_generated.csv`) for use as `unitprep-dedup` crate test fixtures. Cross-check: the Louis Williams flag matches the F3/F5 rows independently visible in the (non-canonical) xlsx, so the two sources agree on substance even though the xlsx's format itself isn't usable as a diff target.

**Net**: No Ka Oi is the only pair with an independently-confirmed expected output; New Castle's expected output is real and trustworthy (generated from the verified script) but self-generated rather than externally confirmed.

## Third historical sample — no paired input

`Documents\temp\duplicate_check_results.csv` (the `CompanyName` = "$25 security deposit" edge case, Kaitlyn Draper / Tony Dulaney rows, Great Falls MT facility) has **no paired source input file** locatable under `Documents\temp` or `Test Data`. It can still anchor a hand-built unit test for the `notes`/`comparison` modules' edge-case handling, but isn't usable as a full ingest-to-report pipeline fixture like the other two.

## No Ka Oi facility (Kahului, HI) — second confirmed real input/output pair

`KAH_QMS_End_Users_Template.csv` (292 data rows) and `KAH_duplicate_check_results_first_pass.csv`, both under `KoBre Dropbox\...\QMS Onboarding\No Ka Oi\...\Prelim Pull\`. Verified the flagged rows trace back correctly to real rows in the source CSV (spot-checked Paula Bacay, Warren Carroll(e), CHP Maui Inc, Barbara Smith groups). Useful confirmations:

- `FirtLast` can be a **business/company name**, not a person (".CHP MAUI INC") — same grouping/comparison/note logic applies uniformly regardless of entity type.
- A genuine near-miss casing+typo cluster in production data: "PAULABACAY" (x2, exact key match) + "PAULABacay" (casing-only variant, groups identically after normalization) + "PAULABacay***" (extra characters, caught via typo-variant merge) — confirms transitive union-find merging across an exact-key group plus a near-match key works as designed.
- Confirms merged/typo-variant groups are written directly into the primary output today (not held back pending confirmation) — already the operational status quo on live customer data, relevant context for the (then still-open) auto-merge design decision, since implementation managers were already relying on today's auto-merge-with-verify-note behavior in production.

## unitprep-dedup crate: real bugs caught by fixture tests (2026-07-15)

Two integration tests (`dedup/tests/reference_fixtures.rs`, `#[ignore]`d — read real tenant PII straight from its existing KoBre Dropbox location rather than copying it into the repo) run the full pipeline against both real facility exports and assert on the exact known-good numbers above. Both pass.

Two real bugs caught and fixed during this pass:
- `report::run` was computing typo-variant candidates over only the multi-unit groups; the reference script runs that pass over *every* tenant, including single-unit ones (two single-unit tenants can still be the same person under two misspelled keys). Fixed before it ever shipped.
- **A real gap in `unitprep-core`'s shared CSV parser**, found only because the fixture tests initially failed against real data: both facility exports have a trailing empty column on *every* data row that the header doesn't name (confirmed uniform across all 292 and 168 rows respectively — a benign export-tool quirk). `unitprep-core`'s `parse_csv_document` used the `csv` crate's strict default, which rejects any row whose field count doesn't match the header — meaning it failed on every row of these real files, and would fail identically for *any* UnitPrep tool fed a file with this same trailing-column pattern. Fixed with `ReaderBuilder::flexible(true)` plus `row.resize(headers.len(), "")` per row (trim extra trailing fields, pad short ones). Two regression tests added to `core/src/parsing_tests.rs`. Full workspace test suite (92 tests plus the 2 real-data integration tests) passed.

**Fixture-test path hygiene**: the first version of `reference_fixtures.rs` hardcoded the two real KoBre Dropbox file paths as `const`s in checked-in test code. Boris caught this — the repo should hold no opinion on where real facility data lives. Fixed by moving both paths to environment variables (`UNITPREP_DEDUP_KAH_FIXTURE`, `UNITPREP_DEDUP_NCSS_FIXTURE`), read at test time with a clear panic message if unset. General principle: never hardcode a personal/company file-system location into committed code, tests included.

## Pad-N-Loc Self Storage — third-facility validation (2026-07-16)

Boris independently cross-checked the tool: fed the same real 234-row `PAD_QMS_End_Users_Template.csv` (a 3rd-pass re-check after the client made fixes) to both a Claude chat session running the `duplicate-tenant-check` skill directly and to the Rust tool via its new UI, then had the chat session diff its own output against ours. Verified independently (not taken on faith) by reading both output CSVs directly and re-running the real source file through the live backend fresh: **exact agreement** — 234 rows, 175 unique tenants, 42 multi-unit, the same 6 flagged groups (same tenants/units), the same 3 typo-variant candidates (ratios 95.0%/94.7%/87.5%). A strong real-world correctness signal on a facility never used to build/tune either implementation.

**Real gap found on the chat skill's side, not ours**: the skill's 3-tier merge policy (≥90% auto-merged, 85–90% conditional, below ignored) means its lowest-tier typo-variant candidate (Erick Martin Miguel Montejo / Martin Miguel Montejo, ~88%) never made it into its output CSV at all — only into the chat summary text. Our tool's CSV had all 3 candidates in the "Possible name/typo variants" section (no merge-tier concept — every candidate gets identical "verify before consolidating" treatment, per the always-flag-never-auto-merge policy); the skill's CSV had only 2. Exactly what that policy is for: a client-safe CSV where nothing found gets silently dropped depending on a score threshold.

This comparison also prompted the correction-note enrichment work — see [[Note Enrichment & Copy Redesign]].

## Second independent real-data cross-check (2026-07-17, different facility than Pad-N-Loc)

Boris ran another comparison — Claude chat, independently, running the skill against a real tenant file, diffed group-by-group against the tool's actual xlsx output (not just counts). **Result: extremely strong match** — flagged discrepancies 6/6 identical, typo variants 0/0, related tenants 2/2 identical. No asymmetry either direction.

Two real, verified-against-our-own-code findings:

1. **A genuine false positive — confirmed real in the crate itself, deliberately deferred, not fixed.** Two unrelated tenants ("Becky Green" and "The Hat Fox And...," an 8-unit business) both had the literal placeholder text `"Xxx"` typed into `AlternateContactAddressStreet1` (a stand-in for "not applicable" instead of leaving it blank) — this passed the related-tenant address guardrail (which only excludes a truly *blank* street address) and got flagged as a shared address. Verified directly: `normalization.rs`'s `is_empty()` is a pure `.trim().is_empty()` check with zero placeholder-token awareness. Confirmed scoped narrowly to the *related-tenant* signals specifically ([[Related-Tenant Detection]]) — does **not** affect the flagged-groups mismatch check, where a difference between "Xxx" and blank on the same tenant's two units is legitimately worth flagging regardless of whether the value is junk text. **Decision: not worth fixing right now** — one instance found across all real data seen so far, and "Xxx" is trivially recognizable as noise by a human reviewer. Proposed fix if revisited: extend the "does this count as a real, comparable value" gate in `relatedness.rs`'s four signal functions (not a blanket change to `is_empty()`) with a conservative placeholder-token list (`n/a`, `na`, `none`, `tbd`, `unknown`, `n.a.`, `not applicable`, `null`, `nil`, `xxx` — deliberately excluding bare single characters like `x`/`-`). Revisit only if this pattern recurs in real data.
2. **A naming-style inconsistency — confirmed real, deliberately not fixed.** `note_composer.rs`'s "Specifically:" clause used `{field:?}` (Rust's short internal `FieldName` variant name, e.g. `AltContactPhoneNumber`), while the export layer's cell-reference bracket (`cell_refs.rs`'s `csv_column_name()`) used the full QMS column name (`AlternateContactPhoneNumber`) for the exact same field in the exact same note. Assessment given to Boris directly (pushing back on a "this was already documented" framing): not sloppiness, a side effect of a deliberate architectural boundary — the domain crate is export-format-agnostic and has no business knowing the CSV/xlsx column-naming convention, which only exists in the binary's infrastructure layer. Each was written correctly within its own layer's convention, independently, without cross-checking how the two would read side by side in one note. **Boris agreed it is not worth worrying about.** Left alone.

## Rowley Self Storage cross-check (2026-08-10) — two real bugs found and fixed

A colleague cross-check on a live onboarding engagement — not a fixture comparison — went further than the two above: it led to actual code changes. Full trail (delta analysis, a recorded call transcript that surfaced the colleague's *actual* current skill file, both fixes, and final verification against the real production xlsx) split out to its own note given the depth: [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]]. Headline: a genuine bug in the separate-tenants note framing (shared with the reference skill, not Rust-specific) and a legacy phone-prefix field that needed full exclusion, not partial tolerance — both fixed and verified; one raised concern (P.O. Box normalization) confirmed already correct; one design question (CompanyName categorization) explicitly decided to keep as-is.

## Related

- [[Dedup Tool Index]]
- [[Business Logic & Reference Script]]
- [[Core Engine Implementation]]
- [[Related-Tenant Detection]]
- [[Note Enrichment & Copy Redesign]]
