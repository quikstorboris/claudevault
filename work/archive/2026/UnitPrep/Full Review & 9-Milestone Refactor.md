---
date: 2026-07-27
description: "Full front+back UnitPrep code review (2026-07-24): ~36 findings, then a 9-milestone plan of real bug fixes + file splits, fully executed and pushed same session."
tags: [work-note, unitprep]
status: completed
quarter: Q3-2026
project: unitprep
---

# Full Review & 9-Milestone Refactor

Boris asked for a very thorough review of the entire UnitPrep codebase
(front + back): bugs/gaps, elegance, maintainability, ease of future
feature work by an unfamiliar developer, line-heavy files worth
splitting, and performance — auth explicitly excluded (early-stage, and
the no-auth gap in the rest of the codebase is a deliberate, known
state, not a surprise finding). Four parallel review agents covered
`core`+`unit-group`, `dedup`, the
binary's API/session/export layers, and the whole `unitprep-ui` frontend,
reading every non-test source file in full rather than sampling.

Findings were published as an HTML Artifact (severity-coded, ~36
findings: 5 High, 17 Medium, 14 Low):
https://claude.ai/code/artifact/19d2d796-6ce7-41b0-b649-f37534777ca8
(artifact link, may not remain accessible indefinitely).

Boris then asked for a plan to address high-priority bugs plus
separation-of-concerns work (both High and borderline-flagged items), not
immediate execution. Used plan mode; the approved plan is saved at
`C:\Users\bmaksimov\.claude\plans\encapsulated-squishing-rain.md`,
structured as 9 milestones sized so work could pause/resume across
sessions. **All 9 were completed in this same session** and pushed to
`origin/main` on both repos (31 commits total: 21 on `unitprep-api`, 10
on `unitprep-ui`).

## What got fixed (real bugs, not just style)

- **`dedup/src/grouping.rs`** — blank/whitespace-only `FirtLast` values no
  longer collapse into one shared bogus group (each gets a unique
  synthetic key instead), which previously produced nonsense
  "contact-info mismatch" notes between unrelated tenants.
- **`dedup/src/report.rs`** — removed an early skip that discarded the
  *strongest* duplicate-tenant signal: two different `FirtLast` keys that
  happen to produce an identical display name (e.g. differently
  formatted/ordered) were never being compared for similarity at all.
- **`core/src/parsing/excel.rs`** — Excel date/datetime cells were
  stringifying to the raw serial-number float (e.g. `"45678.5"`) instead
  of a real date; now formats via `calamine`'s `dates` feature + `chrono`.
- **`unit-group/src/analysis/mod.rs`** — `similar_groups` produced one
  literal duplicate `SimilarityMatch` per facility for a group name
  recurring across facilities (the normal case); now cached/deduped per
  distinct group name.
- **`unit-group/src/validation/row_checks.rs`** —
  `dimensions_mismatch_group` compared group-name-derived vs.
  column-derived dimensions as raw strings (`"10"` vs `"10.0"`
  false-positived); now parses both as `f64` first.
- **`src/api/discover.rs` / `application/unit_group_session.rs`** — the
  real find of the whole review: `discovered_group_names` was computed by
  a hand-rolled block that duplicated `Session::effective_documents()`'s
  format-mapping/correction logic but *omitted* its exclusion filter — an
  excluded group could still appear in this display-only list. Fixed by
  extending `effective_documents()` with the missing auto-detect-vendor
  fallback (making it the one canonical source) and repointing
  `discover.rs` to call it. Live-verified via curl against a real
  DoorSwap-shaped session: excluding a group correctly disappears it from
  the next `/discover` response.
- **Phone-number normalization** — `FieldKind::Phone` added (digits-only
  comparison) so `"(831) 555-1234"` and `"8315551234"` register as the
  same value; found and fixed in *two* places (`comparison.rs` via
  `FIELD_SPECS`, and a second hardcoded `FieldKind::Plain` in
  `relatedness.rs`'s `phone_values` that would have silently kept the
  same gap for the shared-phone relatedness signal even after the first
  fix).
- **Frontend state-scoping** — the exact bug class already fixed once in
  `DiscoveryPage.tsx` (missing `key={sessionId}` letting stale local
  state survive a session change — see
  [[Code Review Watchlist#Closure summary|the earlier watchlist fix]])
  was still present on 3 more routes (`ScanResultsPage`,
  `ExportCompletePage`, `DedupResultsPage`) — same fix applied to all
  three.
- Plus: a narrow session-consistency race in `analyze.rs`/`export.rs`
  (now logged, not silently swallowed), 5 handlers that logged success
  but never rejections, `/upload` silently returning 200 on total
  failure, a button-race guard in `DiscoveryPage`, and missing
  client-side extension validation on the dedup upload flow.

## What got split (separation of concerns)

**Backend:** `discover.rs` (612 lines →
`discover/{mod,dto,compute,format_helpers}.rs`), `fingerprint.rs` (681 →
`fingerprint/{mod,attributes,heuristics}.rs`), `note_composer.rs` (472 →
+`phrasing.rs`), plus a shared `respond<T>()` helper collapsing 5
near-identical handlers and a `RowScan` struct replacing 8 loose
accumulator locals in `validation/mod.rs`.

**Frontend:** `ScanResultsPage.tsx` (2392 → 690 lines, extracted 7 action
components + `IssueCard` + `WarningsSection` + a pure, independently
testable `deriveReasonSections.ts`), `UnitFileResolutionPanel.tsx` (983 →
122, 3 sections extracted to `components/discovery/`), `DiscoveryPage.tsx`
(924 → 436, `MasterGroupFileSection` extracted), plus 2 shared hooks
(`useSessionPost`, `useSessionAction`+`downloadBlob`) collapsing 4
duplicated fetch hooks and `unit-groups/page.tsx`'s inline reducer moved
into `useDiscoveryFlow` for convention consistency (360 → 75 lines).

This directly enacted the project's 250-line-module-alarm policy at
scale across both repos.

## Verification discipline held throughout

**Backend:** `cargo test --workspace` (ended at 267 tests) + `cargo
clippy --workspace --all-targets -- -D warnings` after every milestone —
the pre-existing WIP-auth dead-code errors (17, all in `src/auth/`) were
the only ones ever present, confirmed as the stable baseline each time.

**Frontend:** `tsc --noEmit` + `eslint` after every change, plus two full
production `next build` passes (dev server stopped first, `.next` wiped
and dev restarted fresh immediately after each — see
[[UnitPrep UI Dev Environment]] for the corruption lesson this follows).

**Live verification:** end-to-end smoke tests via direct `curl` against a
running backend for the highest-risk backend fixes, and one real browser
click-through (via the in-app Browser pane, a throwaway client + a real
curl-built session) fully exercising `ScanResultsPage`'s post-split
group-ownership model and 3 of its 7 extracted action components —
confirmed working end-to-end including a real
exclude→import-as-is→auto-resolve sequence. The Discovery-side splits
(`UnitFileResolutionPanel`, `DiscoveryPage`) could **not** get the same
browser click-through — no folder-picker automation available in the
browser tool — so those rest on careful code-level verification plus the
clean builds only; flagged as worth a manual pass by Boris if he wants
full confidence there.

## Not touched (explicitly deferred, not forgotten)

Low-severity/cosmetic items from the original review: `title_case`
apostrophe/hyphen handling, incomplete street-suffix table, index-keyed
table rows in a few read-only tables, `csv_export.rs`'s repetitive
generator functions, `validate.rs`'s derivation logic possibly moving to
the domain crate, case-insensitive de-duplication of displayed mismatch
values. See the plan file (`encapsulated-squishing-rain.md`) for the full
list.

## Related

- [[UnitPrep Architecture Overview]] — now slightly stale on file-path
  specifics given the splits above (`discover.rs` and `fingerprint.rs`
  are directories now, not single files)
- [[Code Review Watchlist]] — the prior review history this one built on
- [[Post-Refactor Audit]] — the follow-up CTO-grade review after this
  refactor landed
