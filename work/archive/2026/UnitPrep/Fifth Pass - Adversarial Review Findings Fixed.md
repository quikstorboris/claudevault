---
date: 2026-07-29
description: "5 parallel adversarial reviewers (one per crate/layer boundary) found and this session fixed a re-opened TOCTOU race, a dead Cancel button, a mislabeled button, two sibling-hook-parity gaps, a regex bug, and more. Shipped as unitprep-api v1.1.5 + unitprep-ui v1.1.5."
tags:
  - work-note
  - unitprep
status: completed
quarter: Q3-2026
project: unitprep
---

# Fifth Pass — Adversarial Review Findings Fixed

Direct continuation of [[Fourth Pass - File Splits, Concurrency Fixes, Dead Code Removal]]. After that pass shipped as v1.1.4 (both repos), Boris asked to run a fresh review pass to check for anything missed before treating the refactor as concluded — "leave no stone unturned." Five parallel review agents (backend: core+unit-group, dedup, api+application layer; frontend: lib/hooks, components/pages) each read every non-test source file in their scope in full. Two of the five hit a session rate-limit mid-review and were resumed from their saved transcripts rather than restarted. Every finding reported here was independently re-verified against the live code by this session before being acted on — not taken on the reviewing agent's word.

Two implementation agents then fixed the confirmed findings; this session independently re-verified their diffs and re-ran the full build/test/lint suite itself before committing. **Committed and pushed**, 8 backend + 9 frontend cohesive commits, shipped as `unitprep-api` **v1.1.5** and `unitprep-ui` **v1.1.5**, both on `origin/main`.

## The one significant bug: a re-opened TOCTOU race

`Session::complete_discovery` (`unitprep-api`, `src/application/unit_group_session.rs`) never bumped `data_generation` — the exact counter [[Fourth Pass - File Splits, Concurrency Fixes, Dead Code Removal]] and the pass before it relied on to stop a correction/exemption/exclusion landing in `/analyze`'s or `/export`'s read→write-back gap from having its safety-net stage downgrade silently re-promoted. Since `complete_discovery` is the single funnel every discovery-affecting handler goes through, and since two of those handlers (`resolve_unit_format.rs`, `select_group_file.rs`) mutate `SessionData` fields directly without going through any generation-bumping method, the same class of bug that was just fixed for corrections was still open via a different door — and reachable, since `require_stage`'s `>=` check means these handlers stay callable even after a session reaches `Analyzed`/`Exported`. Fixed with one `touch_data()` call at the funnel. This is the kind of finding "another review pass" exists to catch — a fix in one place that didn't get applied everywhere the same guarantee was implied.

## Two real frontend UX bugs a fresh look caught

- **A dead "Cancel" button**: `UnitFileSelectionSection`'s Cancel button (shown when reopening unit-file selection after a prior confirm) was wired to the same callback that *opens* that reopened view — a no-op once already there. Three components deep, invisible to unit tests (which only assert the wrong callback fires, not that it does anything useful), and never caught because `DiscoveryPage`/`UnitFileResolutionPanel`/everything under `discovery/` had **zero E2E coverage** — the app's only integration-level tests covered export, dedup, and session-expiry. Fixed, and closed the actual coverage gap with a new `e2e/discovery-flow.spec.ts` that exercises the fix directly.
- **A mislabeled button**: `UndoImportAsIsButton` showed "Edit Groups (N)" — copy-pasted from the unrelated `EditGroupsButton` (which undoes an exclusion, not an acknowledgment). Now says "Undo Import As Is (N)".

## The recurring pattern worth remembering: sibling-hook parity doesn't stay in sync on its own

This is the second time in two passes that a fix applied to one hook wasn't mirrored to its documented "sibling": `useSessionAction`/`useSessionPost`'s `sessionExpired` asymmetry ([[Fourth Pass - File Splits, Concurrency Fixes, Dead Code Removal]]), and now `useExportDownload`/`useDedupExport` — the latter's own doc comment literally says "Mirrors `useExportDownload`" and was still missing both of that hook's stale-state and reentrancy fixes. See [[Gotchas]] for the standing note this earned.

## Everything else fixed, lower severity

**Backend**: `find_typo_variant_candidates` moved into `similarity.rs` (module-convention consistency); `dedup/RULES.md`'s stale "individually well-formed email" claim corrected to match actual code behavior (non-blank + distinct only); `FIELD_SPECS`/`CATEGORY_PRIORITY` completeness tests (compile-error-on-drift); `GroupCheckAcknowledgments` suppression now covered at the `unit-group` crate's own unit-test level (previously only default/empty values were ever tested); two no-op `STREET_SUFFIXES` entries removed; a zero-row dedup pipeline test added; a documentation comment added for `Location`'s alias-ordering safety.

**Frontend**: `extendedFilenameFrom`'s RFC 5987 regex fixed (only matched an empty language tag, silently failed on `UTF-8'en'...` — a real bug in code written in the *previous* pass, caught one pass later); `describeFetchError` wired into `useSessionAction`/`useSessionPost` (previously only used in 2 hand-rolled fetch sites, so most of the app showed raw browser errors on network failure instead of an actionable message); `useSessionPost` now resets `data` on a new fetch (previously masked everywhere by the `key={sessionId}` remount convention, not defended in the hook itself); `WarningsSection.tsx` split (464→378 lines, `ExcludedGroupsList`/`AcknowledgedGroupsList` extracted) and `ScanResultsPage.tsx`'s inline Errors/File-Errors blocks extracted, per the new standing split-mixed-concern-files rule.

## Deliberately NOT fixed this pass — flagged, not actioned

- Typo-variant/relatedness notes represent an entire tenant group by `records[0]` only, even though names can legitimately differ within a group — changing this needs a product decision about which record should represent the group, not a unilateral call.
- `find_typo_variant_candidates`'s O(G²) all-pairs comparison has no size guard — a latency/CPU concern on a very large or adversarial upload, but capping it needs an infra-level decision about acceptable upload sizes.
- `InMemorySessionStore::save`'s latent "silently detaches the old handle on overwrite" design gap — confirmed unreachable today (grepped every call site: `save` is only ever called once per session, at creation, with a fresh UUID), so left alone rather than guessed at.
- `aria-live` announcements around async completion states (export success, save confirmations) — a systemic, lower-confidence accessibility gap; not actioned given other a11y work has been incremental and deliberate.

## Verification

Backend: `cargo build/test/clippy/fmt --workspace` — 336 passing (up from 330), clippy at the same 17-warning baseline (all pre-existing, confined to `src/auth/`), fmt clean. Frontend: `tsc --noEmit` clean, `eslint .` clean, `vitest run` — 278 passing across 40 files (up from 270), plus the 2 new Playwright specs independently re-run and passing.

## Open

- Auth Phase 2 tasks 4-11 still fully pending — this was the explicit reason for holding off on auth until the refactor was genuinely finalized.
- `unitprep-api`'s untracked `README.sample.md`/`assets/readme/` still sitting uncommitted, unrelated to any of this work.
- Frontend npm audit (`next`/`postcss`/`sharp`/`brace-expansion`, 12 high-severity, no non-breaking fix) — re-checked this pass, unchanged, still tracked not fixed.
- The three deliberately-not-fixed items above remain open for a future pass if their trigger conditions change.

## Related

- [[Fourth Pass - File Splits, Concurrency Fixes, Dead Code Removal]]
- [[Post-Refactor Audit - Details]]
- [[Key Decisions]]
- [[Gotchas]]
