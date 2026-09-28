---
date: "2026-09-24"
quarter: "Q3-2026"
description: "Verified an external (Grok) code review point by point via two parallel fact-check agents, found the CHANGELOG.md gap in both repos was far larger than the review itself flagged, backfilled it, split 5 oversized unitprep-ui files, and shipped cancel/elapsed-time/partial-failure UI across all three tools"
tags:
  - work-note
  - project/unitprep
---

# Session 2026-09-24 — Grok Review Follow-Through: CHANGELOG Backfill, 5-File Split & Cancel/Progress UI

Boris pasted an external code review (Grok, champion-grade/solo-builder framing) of both repos at `unitprep-api v1.9.38` / `unitprep-ui v1.6.39`. Per this project's own standing discipline (see [[Patterns]]'s "review a previous session's uncommitted work like a stranger's PR" entry, same principle applied to an external review's claims), every finding was independently re-verified against the live repos — via two parallel fact-check agents, one per repo — before acting on anything, rather than trusting the review at face value.

## Verification found the review itself needed correcting in three places

- **"`docx-surgeon`... not yet wired into the template-tagging pipeline or any HTTP endpoint" was false.** `src/api/tagger.rs` already imported and called `docx_surgeon::{edit_docx_all, read_docx, ...}` directly, wired to live `/tagger/*` routes. The review's P2 "wire it or quarantine it" suggestion needed no action.
- **"Types mirrored 1:1" overclaimed the scope.** `types/generated/README.md` already correctly scoped `ts-rs` codegen to 4 response families; the rest of `types/api.ts` (dedup, tagger) is intentionally hand-mirrored. Not a gap, already honestly documented.
- **Both repos' README test counts were already stale at review time** (claimed 556/414; actual then were 685/633 — and both have grown further since, see below).

## The CHANGELOG gap turned out to be much bigger than anything the review itself flagged

While fixing the review's minor "timeout documentation drift" P1-3 item, discovered `unitprep-api/CHANGELOG.md` had stopped at `1.8.0` while the repo had shipped to `1.9.38` — **48 tags, 213 commits, completely undocumented**. `unitprep-ui/CHANGELOG.md` had the same problem: stopped at `1.4.0` against actual `1.6.39` (148 commits). Backfilled both: 60 entries for `unitprep-api` (v1.8.1→v1.9.38, including untagged intermediate version bumps found via `Cargo.toml` diffs, not just git tags), 51 entries for `unitprep-ui` (v1.4.1→v1.6.39) — sourced primarily from this vault's own session notes where they existed, git log as the fallback for the less-documented stretches, deliberately staying terse rather than embellishing where the source material itself was thin (per [[Dev Principles]] #11, "name gaps honestly").

Also found and fixed while in the docs: `REFACTOR.md` (an internal audit-report artifact, not git-tracked) described file sizes and paths that no longer matched reality — its own recommended `ScanResultsPage.tsx` split (2392→claimed still-current) had already happened (actual: 535 lines), same for `UnitFileResolutionPanel.tsx` (983→119) and `DiscoveryPage.tsx` (924→523, partially). Marked it as a dated historical snapshot rather than rewriting the whole audit. `dedup/RULES.md`'s own previously-flagged export-architecture drift turned out to already be fixed by an earlier session — verified, left alone, corrected the *claim* about its staleness in `REFACTOR.md` instead.

## 5 oversized `unitprep-ui` files split

Per this project's own ~250-line file-size discipline: `clients/new/page.tsx` (656→169), `clients/search/page.tsx` (586→162), `facility/UsersTab.tsx` (579→137), `DiscoveryPage.tsx` (523→132, further split beyond the earlier partial one above), `ScanResultsPage.tsx` (535→257). Pure reorganization into sibling `components/<area>/` subdirectories, following the same pattern as the earlier [[Session 2026-09-09 — Security & Activity Logs Page Split (DRY Pagination Refactor)|security/activity-logs split]] and the same day's own `router.rs` split. New tests added for extracted hooks where warranted (`useScanResultsDerivedState.ts`), matching existing test density.

## Cancel / elapsed-time / partial-failure UI across all three tools

The review's own P3 suggestion ("extend session-expired discipline to long-running tool jobs — progress, cancel, partial failure") was verified as a real, live gap: `DedupUploadPage.tsx` tracked only a boolean `loading`, no cancel affordance, no distinction between total and partial failure. Built once, shared everywhere — `lib/useAbortableOperation.ts` (elapsed-time ticking + `AbortController` bookkeeping; no endpoint here streams a real percentage back, so this is an honest indeterminate-progress affordance, not a fake bar) and `lib/useFileUploadAction.ts` (rewritten from `fetch` to `XMLHttpRequest` specifically to get real `upload.onprogress` events, which `fetch` has no equivalent for). Wired into `useSessionAction`/`useSessionPost` and rippling into ~20 call sites app-wide. `UploadResponse`'s `files_uploaded`/`files_failed`/`multipart_errors` counters — computed by the backend already, never surfaced distinctly before — are now shown as an explicit partial-failure state in Group Prep's `UploadIntegritySummary.tsx`. Dedup/Tagger's single-file check endpoints genuinely have no such counters (confirmed against their Rust response structs), so no partial-failure UI applies there — a real design difference, not a gap left unaddressed.

## Commit-splitting technique used for real, not just documented

The `DiscoveryPage.tsx`/`ScanResultsPage.tsx`/`SourceFolderSection.tsx` split and the progress-UI feature landed on the same files back to back, with no commit in between — genuinely entangled. Rather than accept a muddled combined commit, reconstructed the true intermediate ("split only, no progress-UI yet") state by hand for those 3 files, verified it independently (tsc/eslint/vitest — 84 files/637 tests, matching the actual checkpoint the split work had reached), committed that, then restored the full state and verified again (86 files/669 tests) before committing the feature work. See [[Patterns]]'s existing "how to split commits when concerns share a file" entry — this session additionally used `git stash push -- <specific paths>` to isolate whole-file-revert cases cleanly (new files/hooks nobody else had touched), reserving manual `Write`-based reconstruction only for the 3 genuinely mixed-within-one-file cases. See [[WSL Execution Technique]] for the mechanics.

## Shipped

`unitprep-api`: 3 docs-only commits (CHANGELOG backfill, repo-URL/README fix, an incidental `cargo fmt` cleanup on 7 unrelated files caught mid-session) — no version bump, per Boris's explicit call that version bumps are for real code changes only. `unitprep-ui`: CHANGELOG backfill, README fix, 2 split commits, 1 feature commit — shipped as **`v1.6.40`** (a version-bump omission caught and fixed the following session, see [[Gotchas]]).

## Related

- [[Session 2026-09-24 — Durable Session Store for WebAuthn and All Three Tool Sessions]] — the next piece of Grok-review follow-through, same day
- [[Session 2026-09-09 — Security & Activity Logs Page Split (DRY Pagination Refactor)]] — the split pattern this session's 5-file split followed
- [[Patterns]] — the commit-splitting technique, and the "review external claims like a stranger's PR" principle
- [[Dev Principles]] — #5 (file-size discipline), #11 (name gaps honestly)
- [[Gotchas]] — the version-bump-forgotten catch
