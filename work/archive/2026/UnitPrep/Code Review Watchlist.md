---
date: 2026-07-27
description: "UnitPrep code-review punch list opened 2026-07-09, closed 2026-07-17; 2026-07-23 follow-up found+fixed a CSV-injection gap and 3 frontend state-scoping bugs same day."
tags: [work-note, unitprep]
status: completed
quarter: Q3-2026
project: unitprep
---

# Code Review Watchlist

Closed punch list of known-but-not-yet-fixed concerns flagged during code
review of `unitprep-api` and `unitprep-ui`. See
[[UnitPrep Architecture Overview]] for overall architecture and
[[Code Review Watchlist - Findings]] for the exhaustive item-by-item log
(all 14 numbered items, verification detail, commit hashes).

## Closure summary

- **Original punch list (opened 2026-07-09) — fully closed 2026-07-17.**
  Every item was either fixed, resolved as documentation-only, or
  explicitly deferred as deliberate future work (not forgotten, not a
  gap): lock-ordering invariant documented, dead `src/shared/` module
  deleted, lock-poisoning eliminated via `parking_lot`, a validation
  aggregate edge case fixed (fake `ready: true` on zero files checked),
  a `fingerprint.rs` audit closed with one new regression test, a
  bespoke header-lookup bug fixed (`build_batch_from_documents`), HTTP
  error-contract gaps closed on two endpoints, clippy strict mode
  (`-D warnings`) brought clean, and the full `unit-group` crate
  extraction completed in two phases (Group Prep's domain logic fully
  out of the binary and into its own crate). Deliberately left open at
  closure, as accepted future work: similarity-matching algorithmic
  complexity (O(net_new × reference)) and in-memory-only sessions (no
  persistence) — both fine at current data volumes, revisit only if
  volumes grow.
- **Follow-up review, 2026-07-23 — all High/Medium items fixed same
  day.** A second, independent front+back review (run while auth Phase 2
  was mid-flight — see [[Phase 2 Progress]]) found two things worth
  calling out on their own:
  - A **CSV/formula-injection gap** (Medium, backend): tenant/facility/
    group fields written into CSV/XLSX exports weren't sanitized against
    formula injection. Fixed same day with a new
    `src/infrastructure/csv_safety.rs::sanitize_cell` (OWASP-standard
    leading-apostrophe prefix on cells starting with `=`/`+`/`-`/`@`/tab/
    CR), applied across all three export paths.
  - **Three frontend bugs, one root cause** (High): unscoped local UI
    state surviving past the data it gates, in `DiscoveryPage.tsx`,
    `UnitFileResolutionPanel.tsx`, and `ScanResultsPage.tsx`'s
    index-keyed issue cards. Fixed same day via `key={sessionId}`
    remounting and a stable composite issue key.

  Auth code itself (session tokens, RLS transaction scoping, cookie flags)
  was audited as part of this pass and found clean; no login/registration
  handlers existed yet at the time, so there was nothing further to
  exploit there. Deliberately left open from this pass: an RLS
  admin-bypass gap on the WebAuthn/TOTP credential tables (design
  question, not a bug — may be intentional for v1). Full detail,
  including the medium/low frontend fixes and backend perf notes, is in
  [[Code Review Watchlist - Findings]].

## Git reconciliation (2026-07-23, same day)

While applying the fixes above, found `unitprep-api` had accumulated a
second, bot-authored branch (`claude/orchestrator-db-organization-psnq8b`,
`Claude <noreply@anthropic.com>`, origin unclear) diverged from `main`.
It was invisible to the review itself (both agents worked from `main`),
but explains why an earlier pass had undercounted tests by 32. Reconciled
same day: confirmed zero file overlap, cherry-picked the orphan branch's
one commit onto `main` (`c780a7e`), re-verified the full suite (181
tests), committed the CSV-injection fix on top (`841eff9`), pushed both
repos to `origin/main`, and deleted the orphan branch (local + origin).
This is the incident that established the standing branch policy: main
only going forward, no incidental branches, ask first before creating
one.

## Related

- [[Code Review Watchlist - Findings]] — exhaustive item-by-item log (all 14 items)
- [[Full Review & 9-Milestone Refactor]] — the later, larger review pass that picked up several items this one deferred (e.g. `ScanResultsPage.tsx` size/organization)
- [[UnitPrep Architecture Overview]]
- [[Post-Refactor Audit]]
