---
date: 2026-07-27
description: "The related-tenant/shared-contact-info detection feature: guardrails, implementation, and the real Xxx-placeholder false positive it later surfaced"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Related-Tenant Detection

Part of [[Dedup Tool Index]]. A genuinely new, third finding category — implemented 2026-07-17.

## Origin and framing

Resolves the long-parked adjacent-unit-number idea (see [[Business Logic & Reference Script]]'s "Known Limitations" section), but **not** the way it was originally framed — Boris agreed bare adjacency is too weak a trigger on its own. Instead, the actual implementation is an independent check: flag different-name-key tenants who share one specific, non-blank identifying value (a phone number, an email, an alternate-contact *name*, or a full home address). This catches a real relationship (business + owner, family, subdivided unit) that neither exact-name grouping nor typo-variant similarity could ever find, since both hinge entirely on name. Adjacency itself was **not** implemented as a signal at all — deliberately rejected, not deferred.

## Guardrails (agreed explicitly before writing any code)

Boris: "very careful and deliberate," "don't want false positives."

- Blank values never count as shared.
- A value connecting more than 3 distinct tenants (`MAX_CLUSTER_SIZE`) is excluded entirely — a value that popular is far more likely a shared office number/generic mailing address than a real relationship.
- A blank street address is never treated as a real address to compare (prevents "same city" alone from counting).
- All normalization reuses the crate's existing functions — no second comparison logic.

One idea explicitly considered and deferred, not rejected: cross-referencing `CompanyName` against other tenants' personal names (owner+business pattern) — higher false-positive risk from common surnames, meaningfully more complex, left for a future carefully-scoped pass.

## Implementation

New module `dedup/src/relatedness.rs` (`RelatednessSignal`, `RelatedTenantCandidate`, `find_related_tenant_candidates`) — same one-module-per-kind-of-rule pattern as `similarity.rs`/`comparison.rs`, not a generalized rules-config system (see [[Core Engine Implementation]] for that architecture discussion). `NoteComposer` trait gained a third method, `compose_relatedness_note`, so all three finding categories' text composition stays behind the same swappable seam. `DedupReport` gained `related_tenant_candidates: Vec<RelatedTenantCandidate>` — flows through `/dedup/check` and `/dedup/report` with zero API-layer changes (same pattern as `typo_variant_candidates`). CSV export gained a third section, "Possible related tenants (shared contact info, different names)" — deliberately **no** cell-reference annotation here (unlike flagged groups/typo variants, see [[Cell References]]), since a shared value doesn't point at one well-defined differing cell the way a `FieldMismatch` does; a scoped-out decision, not an oversight.

Frontend: `types/api.ts` gained `RelatednessSignal`/`RelatedTenantCandidate`; new `components/dedup/RelatedTenantsSection.tsx` (table, same pattern as `TypoVariantsSection.tsx`, defaults collapsed); `DedupSummaryStats.tsx` gained a 6th tile ("Related Tenants", grid widened to `grid-cols-6`); `DedupResultsPage.tsx`'s "no issues found" check now also requires `related_tenant_candidates` to be empty.

**Verified**: 8 new unit tests in `dedup/src/relatedness_tests.rs` (all four signals individually, the blank-never-counts guardrail for both plain values and addresses, the too-popular-value exclusion, the no-candidates-when-nothing-shared baseline), 1 new end-to-end CSV export test. Full workspace suite: 124 tests passing, clippy clean. Live-verified against the real running server twice — once confirming a synthetic shared-phone pair surfaces correctly in the `/dedup/check` JSON (including a UTF-8 sanity check: the note's em-dash showed up garbled in one terminal display, traced to raw bytes and confirmed correct `\xe2\x80\x94` UTF-8 — a display artifact, not a real bug) and in the exported CSV's new section; a second time confirming the frontend's changed routes (`/dedup`, `/dedup/[sessionId]`) compile and serve a real session without a server-side crash (`tsc`/`eslint` also clean).

## Real false positive found in production data (2026-07-17)

Two unrelated tenants ("Becky Green" and "The Hat Fox And...," an 8-unit business) both had the literal placeholder text `"Xxx"` typed into `AlternateContactAddressStreet1` as a stand-in for "not applicable" instead of leaving it blank — this passed the address guardrail above (which only excludes a truly *blank* street address) and got flagged as a shared address. Confirmed real in the crate's own code: `normalization.rs`'s `is_empty()` is a pure `.trim().is_empty()` check with zero placeholder-token awareness. This is scoped narrowly to the related-tenant signals specifically; it does **not** affect the flagged-groups mismatch check, where a difference between "Xxx" and blank on the same tenant's two units is legitimately worth flagging.

**Original decision (2026-07-17): not worth fixing right now** — one instance found across all real data seen so far, and "Xxx" is trivially recognizable as noise by a human reviewer. Proposed fix if revisited: a conservative placeholder-token list (`n/a`, `na`, `none`, `tbd`, `unknown`, `n.a.`, `not applicable`, `null`, `nil`, `xxx`) gating `relatedness.rs`'s four signal functions specifically (not a blanket change to `is_empty()`). Full detail and the parallel naming-inconsistency finding from the same cross-check session are in [[Real-Data Cross-Checks]].

## Resolved 2026-08-10 — the deferred trigger condition recurred

The stated condition for revisiting ("one instance found... revisit only if this pattern recurs") was met: a second real facility (Rowley Self Storage) had the literal string `"None"` in `AlternateContactLastName` connecting four otherwise-unrelated tenants — same failure class, different field and different placeholder token. Implemented exactly the proposed fix, verbatim token list included, plus a second related guardrail (a minimum-digit floor on shared phone values, after a 3-digit fragment produced a similar false positive in the same facility's data). See [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]] (Fix #5) for the implementation and verification detail — `dedup/RULES.md` rule 4 is the current source of truth on both guardrails going forward.

## Related

- [[Dedup Tool Index]]
- [[Business Logic & Reference Script]]
- [[Core Engine Implementation]]
- [[Real-Data Cross-Checks]]
- [[Cell References]]
- [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]] — where the deferred fix above actually landed
