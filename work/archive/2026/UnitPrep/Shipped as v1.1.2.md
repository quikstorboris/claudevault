---
date: 2026-07-28
description: "Coverage tooling both sides, 2 crash-bug fixes found via fuzzing, and the key={sessionId} E2E test debugged into actually passing -- shipped as v1.1.2"
tags:
  - work-note
  - unitprep
status: completed
quarter: Q3-2026
project: unitprep
---

# Shipped as v1.1.2

Direct continuation of [[Post-Refactor Audit - Shipped as v1.1.1]], same day. Boris asked for the outstanding test-coverage brainstorm items to actually be implemented, in order: backend tests first, then frontend tooling, then coverage tooling both sides, then fold the 2 crash fixes already found into a version bump.

## What shipped

**Backend (`unitprep-api`)** — property-based/fuzz tests (`proptest`) for all three file parsers, which found and fixed 2 real crash bugs:
- `cell_to_string` (Excel): an extreme date-serial value could panic inside chrono's `TimeDelta` construction rather than returning `None` as calamine's own doc comment claims. Wrapped in `catch_unwind`.
- SpreadsheetML parsing: `ss:Index`/`ss:MergeAcross` were parsed from untrusted XML into unbounded `usize`, fed straight to `Vec::resize` — a crafted cell could abort the whole process via an astronomical allocation, worse than a catchable panic. Now clamped to `1..=16384` (Excel's real column limit).

Also added: real HTTP-level integration tests (binds the actual router to a loopback port, drives it with `reqwest`) including an automated CORS regression test, and regression tests for the analyze/export session write-back race.

**Frontend (`unitprep-ui`)** — went from zero automated tests to a working harness: Vitest + React Testing Library (18 tests: the two shared fetch hooks, `ScanResultsStatTiles`), then Playwright for E2E. See [[Frontend Test Tooling Setup]] for the full account, including three real bugs found getting the E2E test to actually run (not just type-check): a CORS-preflight mocking gap, Next.js 16's `allowedDevOrigins` requirement, and the app's own sessionStorage-scoped client model.

**Coverage tooling, both sides:**
- `cargo-llvm-cov` (primary) + `cargo-tarpaulin` (occasional cross-check only) — `cargo cov` / `cargo cov-tarpaulin` aliases in `unitprep-api/.cargo/config.toml`. Baseline: 84% / 81%, consistent.
- `@vitest/coverage-v8` in `unitprep-ui` (`npm run test:coverage`). Baseline ~9% — honest starting point, not a completed effort.
- See [[Key Decisions]] for why both coverage tools are kept but only one is meant for routine use.

## Final state

`unitprep-api`: 297 tests passing, 84% coverage, clippy clean (17 accepted auth-WIP warnings), fmt clean.
`unitprep-ui`: 18 unit tests + 1 E2E test passing, ~9% coverage, `tsc`/`eslint` clean.

Both repos bumped 1.1.1 → 1.1.2 and pushed to `origin/main`. See each repo's own `CHANGELOG.md` for the itemized entry.

## Related

- [[Post-Refactor Audit - Shipped as v1.1.1]]
- [[Frontend Test Tooling Setup]]
- [[Key Decisions]]
- [[Gotchas]]
- [[Third Hardening Pass (Pre-Auth-Resume)]] — the next session's follow-on hardening pass, built on top of this state
