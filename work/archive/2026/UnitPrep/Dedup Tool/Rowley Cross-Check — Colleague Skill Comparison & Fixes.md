---
date: 2026-08-10
description: "Real-client cross-check (Rowley Self Storage) between unitprep-dedup and a colleague's duplicate-tenant-check skill, across two rounds — five fixes total: separate-tenants mis-framing, phone-prefix exclusion, related-tenant household restructuring, Muise-typo wording, placeholder/phone-digit guardrails"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Rowley Cross-Check — Colleague Skill Comparison & Fixes

Part of [[Dedup Tool Index]]. A real onboarding engagement (Rowley Self Storage, 2nd pull) where a colleague, Sarah McDougall — described as more experienced at this than Boris — ran the reference `anthropic-skills:duplicate-tenant-check` skill independently against the same data and told Boris his results "aren't entirely accurate and cover a wider range than necessary." This note is the full trail: the delta analysis, a recorded call transcript that surfaced her *actual* current skill file, two real bugs found and fixed as a result, and final verification against the real production output. Continues the cross-check lineage in [[Real-Data Cross-Checks]] but promoted to its own note because real code changed, not just a fixture comparison.

## Round 1 (2026-08-10 morning) — delta analysis from her write-up alone

Sarah's write-up (technical findings + a client-facing draft) claimed two script bugs and flagged three CompanyName-only mismatches as noise. Before touching code, checked her two specific claims against the *actual* `unitprep-dedup` Rust source on WSL (not just her prose):

- **Stats were already identical between the two tools**: 244 rows, 184 unique tenants, 33 multi-unit, 9 flagged groups, 0 typo variants, 17 related-tenant candidates — same 9 tenants flagged on both sides. Her "wider than necessary" framing was about note wording/framing, not missed or extra detections. Consistent with the "extremely strong match" pattern already on record from the Pad-N-Loc and second-facility cross-checks in [[Real-Data Cross-Checks]].
- **Her bug #1 (P.O. Box punctuation)**: checked `dedup/src/normalization.rs` — periods are stripped *before* other punctuation is space-substituted (the 2026-07-14 fix, see [[Business Logic & Reference Script]]), so `"P.O. Box"` and `"PO Box"` already collapse identically. **Not a bug in this crate.** Corroborated empirically: Sarah's own write-up mentions an "Adriana address difference" false positive in *her* run that doesn't exist at all in the Rowley output — exactly what her punctuation bug would cause, and exactly what our normalizer already avoids.
- **Her bug #2 (Christopher Muise "may be separate tenants")**: confirmed real, but her cited root cause didn't hold up. She wrote: *"correction_note() checks only that emails are non-empty and distinct; SKILL.md line 141 also requires each unit to have a distinct non-empty address. The address condition was never implemented."* Reading the actual reference skill's SKILL.md and script directly (see Round 2 below for where the real files were found) showed no such requirement exists anywhere near that line — her citation was a misreading. The real root cause is structural: `note_composer.rs`'s old condition (`differing.len() == 1 && category == Email`) could **only ever fire when Address already matched**, because `find_differing_categories` only lists a category when it actually differs. "Email is the sole differing category" was mathematically equivalent to "everything else already matches" — the exact opposite of what a genuine-separate-tenants signal needs. It always fired for the same-person-typo case and could never fire for two genuinely different people.
- **CompanyName-only noise** (Glidden, Jeffrey, part of Barbookles): not a bug — `notes.rs`'s `NOTE_COMPANY` already hedges this ("check whether one value is a stray note... rather than an actual company name"), a deliberate earlier improvement. Flagged as an open policy question, not resolved yet at this point.

## Fix #1 — separate-tenants note now requires Address to also differ

User decision: implement immediately (CompanyName policy left undecided for the moment).

**Change**: `note_composer.rs`'s `compose_group_note` special case now requires `differing.len() == 2` with **both** Email and Address present (each present-and-distinct across the group), not Email alone. Added `phrasing::all_addresses_present_and_distinct` (mirrors the existing `all_emails_present_and_distinct`, reusing `relatedness::full_address` — made `pub(crate)` — so "what counts as the same address" never diverges between the two checks). When address matches (the Muise shape), it now correctly falls through to the plain "update the email to match" note.

Scoped conservatively to exactly `{Email, Address}` differing, not "Email differs AND Address differs regardless of what else also differs" — keeps the special case matching the original "only difference is X" framing (now "only differences are X and Y") rather than overreaching into cases (e.g. phone also differs) the rule was never written to cover. Those still get the standard priority-based multi-category note, just without the special framing.

**Files touched**: `dedup/src/note_composer.rs`, `dedup/src/phrasing.rs`, `dedup/src/relatedness.rs`, `dedup/src/note_composer_tests.rs`. Added a named regression test (`distinct_emails_with_matching_address_is_a_typo_not_separate_tenants`) using the real Muise B207/B256 shape.

**Verified**: `cargo test -p unitprep-dedup` 58 passed (+2 new), `cargo test --workspace` 304+46+58+71 passed, clippy clean, `cargo fmt --check` clean on the touched files (workspace-wide fmt drift confirmed pre-existing and unrelated via `git diff --stat`).

## Round 2 (2026-08-10 afternoon) — the call transcript and her *actual* skill file

Boris supplied a recorded call transcript (him + Sarah reviewing the report live) and the literal `.skill` file she runs, downloaded fresh — a different, more current copy than the one a prior session had found sitting in `/tmp/claude/.../scratchpad/dedup-skill/`. Unzipped and read both `SKILL.md` and `duplicate_tenant_check.py` directly rather than trusting either the paraphrase or the stale copy.

**Live confirmation of Fix #1**: Sarah, looking at the pre-fix report, said out loud: *"Cell phone, everything is exactly matching... why does it think that? ... I think that's an error. Everything looks the same to me."* — a domain expert independently hitting the exact bug already found by code inspection. Treated as strong corroborating evidence, not just a requirements source.

**Two new, real divergences found in her *current* skill** (not present in the stale /tmp copy, so a prior session's read of "what the reference skill does" was itself out of date):

1. **Legacy phone-prefix fields.** Her current `SKILL.md`: *"PhoneNumberPrefix and AlternateContactPhoneNumberPrefix... legacy QSX did not expose the prefix field to users, so differences there are migration noise, not correctable."* The Rust crate had a weaker rule (`comparison.rs`): blank-vs-filled was tolerated, but two *different non-blank* prefix values still flagged a Phone/AltContact mismatch. Her skill excludes the field outright, regardless of values.
2. **CompanyName categorization.** Her skill buckets `CompanyName` into the same "name" category as FirstName/LastName (priority 5) — producing "Change the company name if these should be two separate tenants," which is literally what Sarah read aloud before manually greying out 2 of the 9 groups as not mattering ("*that kind of eliminates 2 that might not really matter*"). The Rust crate has `CompanyName` as its own category with softer "may be a stray note" wording — a deliberate earlier design choice. Also affects typo-variant tier-2 classification: her skill ignores CompanyName differences when deciding "does contact info match," the Rust crate (before any change here) did not.

**Also noted, no action**: her skill's typo-similarity check is plain `SequenceMatcher.ratio()` — no token-sort step. The Rust crate already has `max(straight, token-sort)` similarity (catches transposed names hers would miss, e.g. "Ted Beach" vs "Beach Ted"). This is the crate being *ahead*, not behind — "match her results" should not mean regressing to a weaker algorithm here.

**User decisions** (asked directly): fully exclude the two prefix fields, matching her skill exactly (recommended and chosen). Keep the Rust crate's separate CompanyName category with its softer wording — **not** folding it into Name to match her skill's blunter phrasing (recommended and chosen; a deliberate keep-as-is, not a bug left unfixed).

## Fix #2 — PhoneNumberPrefix / AlternateContactPhoneNumberPrefix excluded entirely

Removed both fields from `FieldName`/`FIELD_SPECS` entirely — same treatment as `Gender`/`DateOfBirth`, which were never represented in the comparison taxonomy at all. Required removing the enum variants outright (not just their `FIELD_SPECS` rows), because the crate enforces one comparison-scope entry per `FieldName` variant via a dedicated exhaustiveness test — leaving the variants in place while dropping their `FIELD_SPECS` entries would have failed that test by design.

`TenantRecord` still stores `phone_number_prefix`/`alt_contact_phone_number_prefix` as raw `String` fields, and both remain real columns in `dedup_export_plan.rs`'s `COLUMNS` list — confirmed the export is a passthrough of original column data plus a `CorrectionNote`, so the raw values still need to round-trip even though they're no longer compared. Only the comparison-taxonomy layer needed touching; `ingest.rs` and `dedup_export_plan.rs` needed zero changes.

**Files touched**: `dedup/src/types/fields.rs` (enum + FIELD_SPECS + exhaustiveness test), `dedup/src/types.rs` (`field()` accessor, doc comments marking the two struct fields passthrough-only), `dedup/src/comparison.rs` (deleted the now-dead blank-tolerant branch in `field_matches_across`, replaced its two tests with one regression test `differing_phone_prefixes_never_flag_a_mismatch`), `dedup/src/phrasing.rs` (`human_label`), and — in the binary crate — `src/infrastructure/dedup_export_plan/cell_refs.rs` + `cell_refs_tests.rs` (`csv_column_name`).

**Verified**: `cargo build --workspace` clean (caught and fixed one missed match arm via a compiler error, not a test). `cargo test --workspace` 304+46+57+71 passed (dedup went 58→57: −2 obsolete tests, +1 replacement), clippy clean, `cargo fmt --check` on every touched file individually — 0 diffs. `git status` confirmed exactly the 9 intended files changed.

## Final verification (2026-08-10, against the real production xlsx)

Boris re-ran the tool and shared the new dashboard summary — textually identical to before at the group/category level (244/184/33/9/0/17, same 9 groups), since neither fix changes counts on *this* facility's data (its `PhoneNumberPrefix` happens to be uniform `+1` everywhere; the Muise fix changes wording, not detection). To verify the fix landed in the artifact a facility manager would actually receive — not just in the dashboard text, which doesn't show the lead sentence — opened the real exported file directly with `openpyxl`:

`C:\KoBre Dropbox\QS Fileserver\Shared\QMS Onboarding\Rowley Self Storage\Rowley Self Storage\Preliminary Data\2nd Pull\DEDUP_duplicate_tenant_check.xlsx`

- Muise's `CorrectionNote` cell (row 33) reads: *"Please update the email address to match across units B207 and B256. Email address is mammamoose7@gmail.com for unit B256 and mommamoose7@gmail.com for unit B207."* — no separate-tenants framing.
- Scanned every `CorrectionNote` cell in the file for the phrase "separate tenants": **zero occurrences**.
- `PhoneNumberPrefix`/`AlternateContactPhoneNumberPrefix` columns are present in the export (raw passthrough, `'+1` for both Muise units) but never appear in any note text or cell-reference bracket — confirms the exclusion is in effect while the raw data still round-trips.
- Company-category notes (Glidden, Jeffrey) retain the softer hedge wording, per the kept-as-is decision.
- One thing initially flagged and then ruled out: the Company/related-tenant notes render a `�` in this terminal — checked the actual cell's Unicode codepoint directly (`0x2014`, a real em dash) rather than trusting the terminal's rendering. **Not a bug** — a console-display artifact of the inspection method, not a defect in the file.

**Point-by-point against the call transcript**: every item Sarah raised (Adriana/Deacetis/Borzych/DiMento flags, the Christine Faro two-row relatedness display, the Company noise she manually greys out) matches what's in the current output, either unchanged-and-already-correct or fixed. No open discrepancies remained against her reasoning at this point in the session.

## Round 3 (2026-08-10, same day) — a second post-fix cross-check finds two more real bugs plus a real design gap

Boris re-ran the tool on the same Rowley data (unchanged: 244/184/33/9/0/17, same 9 groups — neither Fix #1 nor Fix #2 changes counts on this facility's data) and had a colleague-skill session independently review the new output against the pre-fix one. Findings:

- **Both fixes confirmed holding on a third independent check**: no bogus separate-tenants note, no P.O. Box false positive.
- **Two new real bugs, in the related-tenant signal specifically** (untouched by Fix #1/#2):
  1. The literal string `"None"` in `AlternateContactLastName` (a placeholder for "no alternate contact," not a real name) connected four otherwise-unrelated tenants as a false "shared alternate contact."
  2. A 3-digit fragment (`"978"`) in `AlternateContactPhoneNumber` connected an unrelated tenant to *the facility's own account* (`Rowley Self-Storage`, `info@rowleyselfstorage.com`) as a false "shared phone number."
- **A real design gap, independently corroborated by Sarah's own live call transcript** ("Christine A. Faro... making it look like it's more records than it is"): the "Possible Related Tenants" section emitted one row per (signal, value), not per tenant pair — the Nelsons (identical on phone ×2, email, alt contact, and address) produced 5 separate rows for one obvious spousal pair, and a 3-tenant chain (Bruce Wile / Robert Wiley / Linda Wiley, connected via two *different* signals) read as two disjoint pairs rather than one household with a probable surname typo sitting in plain sight.
- **A wording suggestion** for the Muise-shape note: state "likely a typo" outright when address and phone both already match, instead of leaving the reader to notice.
- **A policy suggestion, not implemented**: hold the whole related-tenant section back from the client-facing artifact by default, since none of it is directly actionable — a workflow decision, not a code change; not acted on this session.

**Decisions**: proceed with the household restructuring (bigger change, explicit go-ahead) and the Muise wording addition (small, explicit go-ahead) immediately. The two narrow bug fixes were deliberately deferred for a scoping discussion first — see Fix #5 below for how that resolved.

## Fix #3 — related-tenant households instead of one row per signal

**Change**: `relatedness.rs`'s `find_related_tenant_candidates` now merges every (signal, value) cluster into a *household* by transitive closure (union-find over group keys) — two clusters sharing even one tenant become one household, regardless of which signal connected them. `RelatedTenantCandidate` gained a `RelatedTenantEvidence` list (signal + value + the specific subset of the household that shares it) in place of the old single `signal`/`shared_value` fields. A household over `MAX_HOUSEHOLD_SIZE` (8, deliberately more generous than the existing per-value `MAX_CLUSTER_SIZE` of 3) is excluded entirely — guards against a pathological chain of individually-small clusters accreting into one implausibly large "family."

`note_composer.rs`'s `compose_relatedness_note` composes accordingly: one piece of evidence keeps the original single-signal wording verbatim (no visible change for the common case); more than one groups by which specific members it connects first (so a pair matching on multiple signals gets one combined clause, e.g. "share the same phone numbers (X and Y), email address (Z), and alternate contact (W)"), then joins distinct-subset clauses with "; " and one shared closing sentence — this is what turns the Nelsons' 5 rows into 1 and correctly keeps the Wile/Wiley/Wiley evidence in two clauses naming only the pairs each actually connects.

Flowed through the full stack: `dedup_view.rs`'s `RelatedTenantView` (API JSON shape) gained an `evidence` list resolved to display names/units; `types/api.ts` mirrors it; `RelatedTenantsSection.tsx` replaced its Signal/Shared-Value columns with an Evidence column that names only the specific members each item applies to when smaller than the full household.

**Files touched**: `dedup/src/relatedness.rs`, `note_composer.rs`, `notes.rs`, `phrasing.rs` (`oxford_join` made `pub(crate)`), `lib.rs`, `report.rs` (test), plus (binary crate) `dedup_view.rs`, `dedup_export_plan_tests.rs`, `dedup_csv_export_tests.rs`, `dedup_xlsx_export_tests.rs`, and (frontend) `types/api.ts`, `RelatedTenantsSection.tsx`, `RelatedTenantsSection.test.tsx`.

**Verified**: 65 dedup tests (+8 new: the Nelson-style multi-signal merge, the Wile/Wiley-style transitive chain, the household-size-cap exclusion, plus 5 note-composer tests). Full workspace suite green. Frontend: 292 vitest tests passing (6 new/updated), `tsc`/`eslint` clean. A full authenticated browser click-through wasn't possible (the app now requires passkey sign-in, no credentials available in this session) — treated the React Testing Library component tests (real DOM render, exact text assertions including the subset-annotation case) as the practical substitute.

## Fix #4 — Muise-style note names the typo outright

**Change**: when an email-only mismatch has a matching, non-blank address *and* phone across the group, `compose_group_note` now appends: *"The matching address and phone suggest this is one person with a mistyped email, not two separate tenants."* Added `phrasing::address_present_and_shared`/`phone_present_and_shared` (the "identical and present" mirror of the existing "distinct and present" checks used by Fix #1).

**Verified**: 2 new note-composer tests (the enhancement firing when both match; NOT firing when address is blank, confirming it requires real corroborating evidence, not just "nothing else differs").

## Fix #5 — two narrow related-tenant guardrails: placeholder tokens, phone-digit floor

Resolved the deferred scoping questions directly with Boris: the placeholder-token filter applies **uniformly across all four relatedness signals** (not just alt-contact-name, where the "None" bug was actually observed) — a literal "n/a"/"none"/"tbd"/etc. is exactly the same failure mode wherever it's typed. The phone-digit floor (`MIN_PHONE_DIGITS` = 10) is scoped to **`relatedness.rs`'s phone signal only**, not `comparison.rs`'s mismatch detection — a short/garbage phone *difference between two units of the same tenant* is still a real mismatch under the existing blank-vs-filled-always-differs policy; only the cross-tenant relatedness signal needed the floor.

**Change**: added `PLACEHOLDER_TOKENS`/`is_placeholder` (checked against the raw trim+lowercased value, before any field-kind-specific normalization, so it isn't fooled by e.g. Address-kind normalization mangling `"n/a"` into `"n a"`) and gated all four value-extraction functions plus `full_address`'s existing blank-gate — the latter meaning the placeholder guard also benefits `phrasing.rs`'s separate-tenants and Muise-typo checks (Fix #1/#4) for free, since they reuse that same gate. Added the `MIN_PHONE_DIGITS` floor to `phone_values()` specifically.

**Files touched**: `dedup/src/relatedness.rs` only (plus its own test file).

**Verified**: 69 dedup tests (+4 new regression tests: literal-"None", placeholder-street-address, short-phone-fragment, and a full-length-number-still-works sanity check; +3 existing tests updated from unrealistic short phone stand-ins, like `"5551234"`, to real 10-digit numbers, since the new floor would otherwise have filtered them for the wrong reason and silently stopped testing what they claimed to). Full workspace suite green, clippy clean, fmt clean.

## Documentation debt caught and fixed: `dedup/RULES.md`

This crate has a standing, explicit convention (`RULES.md`'s own header: *"when you add, change, or remove a rule, update this file in the same change, not as a follow-up"*) that was skipped across every fix above. Caught and fixed retroactively, same session: rule 2's special case rewritten to describe the corrected Email-**and**-Address condition (with the old, buggy wording called out as the shipped bug it was) and the new Fix #4 corroborating-typo wording; an "Excluded fields" note added under rule 2 for the Fix #2 phone-prefix exclusion; rule 4 substantially rewritten to describe household merging (Fix #3) and both new guardrails (Fix #5), with dates attached per the vault's own date-stamp-volatile-facts convention.

## Verdict

Dedup is now in full agreement with Sarah's reasoning across two independent rounds of cross-checking, with exactly two *deliberate, documented* divergences remaining (CompanyName category/wording; token-sort typo-similarity, a strict improvement over her skill, not a gap) — both decided explicitly with Boris, not silently left unreconciled. Five real fixes shipped this session (separate-tenants mis-framing, legacy phone-prefix exclusion, related-tenant household restructuring, Muise-typo wording, placeholder/phone-digit guardrails), all verified against the actual test suite and/or the real production xlsx, plus the crate's own rules documentation brought current. No open bugs against this dataset as of 2026-08-10. Not yet committed or pushed as of this note.

## Related

- [[Real-Data Cross-Checks]]
- [[Business Logic & Reference Script]]
- [[Core Engine Implementation]]
- [[Related-Tenant Detection]]
- [[Note Enrichment & Copy Redesign]]
- [[Dedup Tool Index]]
