---
date: 2026-07-27
description: "Overview and navigation for the UnitPrep dedup (Duplicate Tenant Check) tool build — status, what it does, and links to each domain note"
tags: [work-note, unitprep, dedup, index]
status: completed
quarter: Q3-2026
project: unitprep
---

# Dedup Tool Index

Consolidated from a single 1100+ line build-history memory file (`project_unitprep_dedup_tool.md`) into the domain notes below, 2026-07-27.

## What the tool does

The **Duplicate Tenant Check** (internally "dedup") is a UnitPrep module that reads a QMS End Users CSV export from a self-storage facility and finds tenants who hold multiple units but have inconsistent contact information across those units — plus two related finding types. Its audience is internal Quikstor **implementation managers** running it during onboarding, not the storage customers themselves, and not self-serve (see [[Gotchas#UnitPrep has no auth by design — don't flag it as a surprise finding]] on why no-auth is fine here).

It started as an ad hoc Python script/Claude skill (`anthropic-skills:duplicate-tenant-check`) and was reverse-engineered, then reimplemented as a real Rust crate (`unitprep-dedup`) plus session/API/export/UI layers inside the UnitPrep workspace, following the same crate-per-tool architecture as [[UnitPrep Architecture Overview]]'s other tool ("Group Prep," formerly UnitGroup).

Three finding categories, all **flag-only, never auto-merge or auto-correct** (a deliberate, considered UnitPrep-wide policy):
1. **Flagged groups** — same tenant (exact name key, or backup grouping), inconsistent contact info across units.
2. **Typo-variant candidates** — different name keys that are likely the same tenant (fuzzy name match), surfaced for human confirmation only.
3. **Related-tenant candidates** — different tenants who share one specific identifying value (phone/email/alt-contact-name/address), a genuinely new third category with no analog in name-based grouping.

## Status as of 2026-08-10

Shipped and stable, still under active real-world correctness maintenance. Backend (crate + session/API/CSV+xlsx export) and frontend (`unitprep-ui` dedup screens) core build is committed and pushed to `origin/main` as of 2026-07-27. **Five more fixes landed 2026-08-10** via a real onboarding engagement's two-round colleague cross-check (Rowley Self Storage) — separate-tenants mis-framing, legacy phone-prefix exclusion, related-tenant household restructuring (one row per tenant pair instead of per signal), a Muise-style "likely a typo" wording addition, and two relatedness guardrails (placeholder-token filter, phone-digit floor) — see [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]] for the full trail. **Not yet committed/pushed as of this note** — the core build above is on `main`; this latest batch is still local. No open blocking items otherwise. A handful of small, explicitly-deferred loose ends remain — see each domain note's own "not yet fixed" callouts (the reviewed-checkbox default in [[Dedup UI]], the CSV-audience tension in [[Note Enrichment & Copy Redesign]], and the CompanyName-category-vs-reference-skill divergence recorded as a deliberate keep-as-is in the Rowley note). The "Xxx" placeholder false positive previously deferred in [[Related-Tenant Detection]] is now resolved — see that note's update.

**Also deliberately deferred**: the two `#[ignore]`'d real-PII fixture tests in `tests/reference_fixtures.rs` never run automatically (no CI exists yet). Flagged as significant, revisit once the rest of the outstanding, non-deferred test/refactor work is complete — see [[work/Index#Open Questions|Open Questions]].

## Domain notes

- [[Business Logic & Reference Script]] — how the matching/comparison/grouping rules were reverse-engineered from the reference Python skill across two corrective re-reads, plus the settled always-flag-never-auto-merge policy.
- [[Core Engine Implementation]] — the `unitprep-dedup` domain crate itself: the six core algorithms, 250-line file splits, and the architecture decisions (output format, MVP scope, unit-group extraction ordering) made alongside it.
- [[Session, API & Scope Decisions]] — `DedupSession`, the three HTTP routes, commit history, and the "Group Prep" naming decision.
- [[Real-Data Cross-Checks]] — fixture verification against New Castle, No Ka Oi, and Pad-N-Loc/a fourth facility, including two real bugs the fixture tests caught and two real gaps found via independent chat-skill comparisons.
- [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]] — a real onboarding engagement's two-round colleague cross-check (Rowley Self Storage) that led to five fixes: separate-tenants mis-framing, legacy phone-prefix exclusion, related-tenant household restructuring, Muise-typo wording, and two relatedness guardrails — verified against the real production xlsx and the full test suite.
- [[Note Enrichment & Copy Redesign]] — from flat category notes to real per-field/per-unit plain-English copy, ending in the 2026-07-22 real-names/tone redesign.
- [[Cell References]] — the bracketed spreadsheet cell-reference feature in exported notes, later made shared and reused for on-screen references too.
- [[Related-Tenant Detection]] — the shared-contact-info relatedness check, its guardrails, and the real false positive it surfaced in production data.
- [[XLSX Export & RULES]] — the `.xlsx` export path (clickable cell refs, cluster colors) built alongside CSV via a shared export-plan module, plus `dedup/RULES.md`.
- [[Dedup UI]] — the `unitprep-ui` frontend build and the WSL/Node environment quirks hit while verifying it.

## Related

- [[UnitPrep Architecture Overview]]
- [[Platform Vision (Onboarding Orchestrator)]]
- [[Code Review Watchlist]]
