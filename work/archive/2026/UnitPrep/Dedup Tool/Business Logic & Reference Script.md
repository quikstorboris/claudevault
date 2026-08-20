---
date: 2026-07-27
description: "How the dedup tool's matching/comparison rules were reverse-engineered from the reference Python skill, including two corrective re-reads"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Business Logic & Reference Script

Part of [[Dedup Tool Index]]. Origin and business-rule history for the "Duplicate Tenant Check" — evaluated as a new [[UnitPrep Architecture Overview]] module, originally an ad hoc script/Claude skill run manually during QMS onboarding by **implementation managers** (internal Quikstor staff, not storage customers, not self-serve — keeps the tool inside UnitPrep's no-auth internal-tool posture per [[Gotchas#UnitPrep has no auth by design — don't flag it as a surprise finding]]).

Reference materials: `Documents\Duplicate_Tenant_Check_Training_Guide.docx` and sample data under the KoBre Dropbox QMS Onboarding tree (see [[UnitPrep File Locations]]).

## First read (2026-07-08, prose training guide — later found to be wrong in places)

- Pass 1 (grouping): primary key is normalized tenant name (`FirtLast`, trim+uppercase). Guide claimed a same-email-different-name backup grouping existed; **this turned out to be false** (see below). Single-unit groups skipped.
- Pass 2 (comparison): within a multi-unit group, compare name/email/phone/address/alternate-contact fields after normalization (lowercase+trim, address equivalences like "PO Box"="P.O. Box", "Ave"="Avenue", blank/N-A placeholders treated as empty). Blank vs. filled counts as a mismatch, not a match. Gender/DOB deliberately excluded (too inconsistently filled to be signal).
- Pass 3 (reporting): one correction note per flagged group, priority phone > email > address > alternate contact > name. Special case: if the *only* difference is every unit has a different email, the note suggests confirming separate tenants rather than "fix this."
- Safety net: separate fuzzy-name-similarity pass (85%+ threshold, e.g. "DAWN" vs "DON ANTHONY") surfaced for human review only, never auto-merged.

**Why a good architectural fit for UnitPrep**: exact-match-determines-identity / fuzzy-is-advisory-only is UnitPrep's core design principle, and this dedup logic independently follows the same rule. Same `strsim` dependency could serve both. Same validate→correct→re-validate→export session loop already exists in UnitPrep and maps onto report→human-decides→regenerate→export here.

**Output format, originally assumed (later revised — see below)**: match an "existing" two-sheet xlsx format (`Draft_1` = all rows across the 71-column PMS export schema with `Group`/`Duplicate`/`Issues` populated where relevant; `Duplicate Tenants` = same schema filtered to flagged groups).

## Update 2026-07-09: real skill script obtained (`duplicate-tenant-check.skill` — SKILL.md + `duplicate_tenant_check.py`)

Corrected several things the prose guide got wrong:

- **No email-based backup grouping exists in the code.** Grouping is `FirtLast` (trim+lowercase) only — a real gap vs. the business rule "email is the unique identifier."
- **Typo-variant matching is two-tiered**, using `difflib.SequenceMatcher` on display names: ≥90% → always merged into output with a "verify" note; 85–90% → merged only if all non-name contact fields already match, otherwise pushed to a review-only text section (never written to output). Below 85% ignored. Overlapping pairs chain via union-find.
- Address normalization is a concrete street-suffix/direction lookup table (avenue→ave, north→n, etc.), applied to both primary and alternate-contact address fields.
- Excluded fields: Gender, DateOfBirth, PhoneNumberType, AddressCountry, plus structural/key columns.
- The `Duplicate` composite-key input column is never used by the script's logic — confirmed upstream artifact only.
- **Real script output ≠ the two-sheet xlsx sample first inspected.** Script output is single-sheet CSV, keeps `CustNumb`, drops all clean/single-unit tenants, blank-row-separated groups, one full-sentence note on each group's first row only. The two-sheet `Draft_1`/`Duplicate Tenants` xlsx (full row passthrough, `Group` id column, per-row `Issues` labels, flagged groups sorted first) was confirmed by Boris to be **Claude's own improvised presentation** from an earlier conversation where a colleague ran the skill — SKILL.md itself only says to present the CSV with a summary. Conclusion: trust the script for matching/comparison logic; treat the xlsx's presentation choices as a reasonable but non-canonical precedent to deliberately confirm, not silently inherit.
- **Real output sample**: `Documents\temp\duplicate_check_results.csv`. Contains a good edge case: `CompanyName` was bucketed in the same field-category as FirstName/LastName ("name"), so a stray junk value (e.g. "$25 security deposit" typed into the wrong field) produced the nonsensical note "Change the name if these should be two separate tenants." (Resolved later — see below.)

## Design decision RESOLVED: always flag, never auto-merge

Even at the script's ≥90% "verify" tier, this became settled UnitPrep-wide policy: the fuzzy-name safety net still runs the same two-tier similarity logic, but surfaces every match for human confirmation rather than writing merged/verify-tier pairs directly into output. Brings the dedup tool fully in line with UnitPrep's exact-match-decides/fuzzy-is-advisory-only principle, no per-pipeline exception.

## Skill revision re-read (session continuation, now a registered Claude skill `anthropic-skills:duplicate-tenant-check`)

Re-read both SKILL.md and the script from the registered skill's install path and found real behavior changes — treated as current source of truth over the earlier `.skill` read:

- **`CompanyName` now has its own field category** (priority 5, between altcontact and name) — exactly resolves the earlier edge case; a stray "$25 security deposit" value now gets its own note explicitly calling out that a `CompanyName` mismatch may be a stray operational note, not a real company name.
- **Address normalization fixed a real gap**: periods stripped *before* other punctuation is collapsed, so `"P.O. Box"` and `"PO Box"` both normalize to `"po box"` (previously produced different token sequences).
- **Typo-variant similarity is now `max(straight ratio, token-sort ratio)`** — token-sort ratio alphabetically sorts each name's words before comparing, catching transposed first/last names (e.g. "TED BEACH" vs "BEACH TED", ~56% straight but 100% token-sort). A real detection improvement, not just a threshold tweak.
- New calibration set: Zachary Cuddeback/Zachary P Cuddeback ≈94% (merge), Stephen/Stephan Tucker ≈92% (merge), Ted Beach/Beach Ted =100% via token-sort (merge), Dawn/Don Anthony ≈86% (tier-2 conditional), Elaine/Leslie Hofstadter ≈88% differing contact (review-only, likely family), Chris/Tim Neufeld ≈73% (below threshold, ignored).
- **New "re-check / second pass" workflow mode** (re-running against a file previously checked): do a structured field-by-field diff keyed on `CustNumb` against the prior pull, watching for records disappearing entirely, field contamination (e.g. an old removed phone number's digits pasted into `CompanyName` instead of deleted while the phone field itself now matches), and unexplained identity changes. Reported as a separate category — a data-integrity-across-time problem, not a grouping problem. **Genuinely new capability the eventual UnitPrep module would need to consider** (comparing two pulls of the same facility over time). This was later tabled entirely for the Rust port — see [[Core Engine Implementation]].
- **New client-facing tone requirement**: summaries for the facility manager should be short plain-English bullets organized by unit number ("Please open unit X and add Y"), no tables, no jargon — detailed tables/breakdowns are for internal analysis only. This shaped the eventual note redesign — see [[Note Enrichment & Copy Redesign]].
- **New "Known Limitations" section**:
  - Facility-internal flag conventions appended directly to `LastName` (e.g. trailing asterisks like `"SMITH****"`) are sometimes a manual marker for something else (past-due, lien, auction), not a typo. The typo-variant logic still correctly merges these with the unmarked name (contact info matches), but the tool should **not** describe it as a data-entry error to the client. Confirmed real: the `BARBARASMITH****` row in the No Ka Oi sample data (see [[Real-Data Cross-Checks]]) is exactly this pattern.
  - Adjacent/sequential unit numbers (e.g. 81F/81G/81H) as a relatedness signal — observed as a real pattern at least once but not implemented as a standalone trigger; became the seed for the actual related-tenant check (see [[Related-Tenant Detection]]), which explicitly did **not** implement bare adjacency.

## Status as of 2026-07-15 (architecture-focus recap)

Business logic considered solid, not guessed — reverse-engineered from two versions of the reference script and verified against three independent real input/output sample pairs (see [[Real-Data Cross-Checks]]), every discrepancy reconciled. The workspace/crate pattern this tool built into (generic session engine, "new tool = new crate depending only on `unitprep-core`") is proven by having already been used.

**Remaining open items at that point (none blocking the crate build)**, later resolved — see [[Core Engine Implementation]] and [[Session, API & Scope Decisions]] for how each landed:
1. Output format ("match the existing xlsx") — unresolved product decision, no settled spec.
2. No `.xlsx` writer existed anywhere in `unitprep-api`.
3. The dedup tool's own session/stage shape was undrafted.
4. "Re-check two pulls over time" scope undecided.
5. Residual honesty flag: Boris was never fully certain the New Castle sample files are a genuinely correct input/output pair — proceeding was a working assumption, not confirmed fact (later independently strengthened, see [[Real-Data Cross-Checks]]).

## Later cross-check against design-reference docs (2026-07-16)

Cross-checked `duplicate_tenant_check.py` and `dedup_patterns_reference.json` (design-reference docs, not code run in production, capturing patterns from real chat-mode runs at multiple clients — see [[UnitPrep File Locations]] for where these live) against the actual `unitprep-dedup` crate:

- `word_order_invariant_name_matching` (max of straight/token-sort ratio) — already implemented, matches `similarity.rs`.
- `po_box_normalization` (periods stripped first) — already implemented, matches `normalization.rs`.
- `company_name_is_not_identity` (`CompanyName` its own category) — already implemented.
- `spreadsheet_cell_references_in_notes` — was missing at the time; built this same session (see [[Cell References]]).
- The three `known_limitations_not_yet_implemented` entries (facility-internal flag markers, adjacent-unit-number relatedness, cross-pull diffing) all matched what's recorded here — nothing new to act on.
- `client_summary_style_guidance` (plain-English, no jargon, organized by unit) — flagged as **not yet reconciled** at the time: the CSV's `CorrectionNote` was getting more technical with each change (field names, then cell coordinates) — fine for an internal-review artifact, but a real problem if this exact CSV is ever handed directly to a facility manager as-is. This tension was substantially addressed by the 2026-07-22 redesign (see [[Note Enrichment & Copy Redesign]]), though the underlying audience question (internal CSV vs. client-facing copy) was never explicitly re-confirmed with Boris as fully closed.

## Related

- [[Dedup Tool Index]]
- [[Core Engine Implementation]]
- [[Real-Data Cross-Checks]]
- [[Note Enrichment & Copy Redesign]]
- [[Related-Tenant Detection]]
- [[UnitPrep Architecture Overview]]
- [[Gotchas#UnitPrep has no auth by design — don't flag it as a surprise finding]]
- [[UnitPrep File Locations]]
