---
date: 2026-07-28
description: "File splits (validate.rs, discover/compute.rs), both previously-deferred concurrency races actually fixed, 5 test-coverage gaps closed, acknowledge_errors deleted BE+FE, 6 frontend bugs fixed. All independently re-verified by this session, not just agent-reported."
tags:
  - work-note
  - unitprep
status: completed
quarter: Q3-2026
project: unitprep
---

# Fourth Pass — File Splits, Concurrency Fixes, Dead Code Removal

Direct continuation of [[Third Hardening Pass (Pre-Auth-Resume)]]. Boris asked to hold off resuming auth until the refactor is fully finalized and reviewed for code quality; this pass closes out the remaining backend refactor items ([[Post-Refactor Audit - Details]]'s two deferred file splits, plus the two concurrency issues [[Key Decisions]] had recorded as deliberately-not-fixed) and the frontend confirmed-bug list from the third pass's `open` items. Two parallel subagents did the implementation (one per repo); this session independently re-ran `cargo build/test/clippy/fmt` and `tsc`/`vitest` itself and read the actual diffs for the two riskiest pieces (the concurrency fixes) rather than trusting the agent reports at face value.

**Committed and pushed 2026-07-28**, organized into 8 backend + 6 frontend cohesive commits (one concern per commit, matching this project's existing convention), each independently re-verified clean before pushing. Shipped as `unitprep-api` **v1.1.4** (commit `4ea2757`) and `unitprep-ui` **v1.1.4** (commit `9d94db0`), both on `origin/main`. `src/auth/` (WIP), `README.sample.md`, and `assets/readme/` (Boris's own uncommitted README redesign) were explicitly excluded from both agents' scope and remain untouched/uncommitted.

## Backend (`unitprep-api`)

### File splits (pure reorganization, zero behavior change)
- `src/api/validate.rs` (285 lines, not the previously-recorded 367 — that figure was stale) → 211 lines. Extracted `build_unit_to_group_map`/`issue_to_summary` into new `src/api/validate/summary.rs` (109 lines), following the existing `file.rs` + `file/submodule.rs` convention already used by `dedup_export_plan.rs`.
- `src/api/discover/compute.rs` (335 lines, not 464) → 176 lines. Extracted `reconcile_unit_file_selection`/`resolve_group_file_readiness`/`compute_discovered_group_names` (+ their result structs) into new `src/api/discover/selection.rs` (179 lines, `pub(super)`).

### Both previously-deferred concurrency issues actually fixed (not just logged)
- **Session-cleanup sweep lock scope** (`core/src/in_memory_session_store.rs`): was a single `sessions.write()` held for the entire O(n) `.retain()` scan, blocking every concurrent `save`/`get_handle`/`delete` for the whole sweep. Now two-phase: `scan_expired_candidates` finds candidates under a READ lock (no blocking), `remove_still_expired` takes the write lock only for the candidate list and re-verifies each one is still expired under its own write lock immediately before removal (closes the TOCTOU where a session gets touched between scan and removal). Verified this respects the documented lock-ordering invariant in `session_store.rs` (outer lock acquired before any per-session lock, never the reverse).
- **`cancel_session` concurrent-mutation race** (`core/src/cancel_session.rs`, `core/src/session.rs`, `core/src/session_store.rs`): added `cancelled: bool` to `SessionMetadata`; `cancel_session` now reads age AND sets `cancelled = true` in one `with_session_mut` call (write-locked on the session itself) before removing the map entry; `SessionStoreExt`'s four default methods (`with_session`/`with_session_mut`/`with_owned_session`/`with_owned_session_mut`) now treat a cancelled session exactly like a nonexistent one — mirroring the existing `owner_id`-mismatch gate exactly, so zero individual handlers needed changes. Verified `unitprep-dedup`'s `DedupSession` goes through the same machinery (confirmed via `main.rs`) and has no separate cancel path, so the fix covers it automatically.

### 5 test-coverage gaps closed
Unicode/diacritic test (`dedup/src/normalization.rs`), two pipeline tests at 1 and 2 records (`dedup/src/report.rs`), a malformed non-UUID `session_id` test (`cancel_session.rs`), an error-shape sweep test and an oversized-body test (`http_integration_tests.rs` — the oversized-multipart test as literally specified turned out to be structurally impossible in `upload_tests.rs`, since those tests call `Multipart::from_request` directly, bypassing the router's `DefaultBodyLimit` layer entirely; redirected to a `Json<T>`-handler endpoint instead, with a pointer comment left in `upload_tests.rs` explaining why).

### Dead `acknowledge_errors` override deleted (backend half)
`ExportRequest.acknowledge_errors` field and both branches in `export.rs` removed; export now unconditionally blocks on unresolved `Severity::Error` issues. `README.md` updated. The one existing test exercising a genuine 200-OK export (`export_succeeds_with_acknowledge_despite_errors`) was replaced with a new clean-validation fixture + test rather than simply deleted, to avoid silently losing the only happy-path export coverage.

### Verification (independently re-run by this session, not just agent-reported)
`cargo build --workspace` clean. `cargo test --workspace`: **330 passing** (up from 321), 2 pre-existing ignored real-PII fixtures unchanged. `cargo clippy --workspace --all-targets`: exactly 17 warnings, all confined to `src/auth/` (unchanged baseline, zero new). `cargo fmt --all -- --check`: clean.

## Frontend (`unitprep-ui`)

Dead `acknowledge_errors` pathway deleted (frontend half) — verified via repo-wide grep that nothing dangling remained. Plus 6 confirmed bugs fixed:
- Export success state (`downloadComplete`) now resets at the start of each `handleExport` attempt.
- `sessionExpired` in `useSessionAction` now resets at the start of each `run`, matching `useSessionPost`'s existing symmetry exactly.
- Reentrancy guard added to `useExportDownload` via a `useRef` (state alone isn't synchronous enough to catch a same-tick double-invoke) — deliberately scoped to just this hook rather than the shared `useSessionAction.run`, since that hook's 3-variant result type is consumed by ~9 other call sites that would have silently mis-treated a 4th "already in flight" variant as success.
- `aria-current="page"` added to `ClientTabs` and `LeftNav`.
- `Content-Disposition` parsing in `downloadBlob` now prefers the RFC 6266 extended `filename*=` form over the plain form (with malformed-encoding safety), currently dormant since the backend only sends the plain form today.
- `clients.tsx` module-singleton risk: confirmed `ClientsProvider` mounts exactly once by construction (wraps the single App Router root layout in `app/layout.tsx`) — added a documenting comment rather than a mount-counter guard, proportionate to a confirmed-safe, low-priority, dormant risk.

### Verification (independently re-run by this session)
`tsc --noEmit` clean. Full `vitest run`: **270 passing across 40 files** (up from 262/40 baseline, +8 new regression tests, zero regressions).

## Decisions

- Both previously-accepted-as-disproportionate backend concurrency issues (session-cleanup lock scope, `cancel_session` race) were revisited and fixed at Boris's explicit request, superseding the [[Key Decisions]] entry that had judged them not worth fixing at single-operator scale. That judgment wasn't wrong for its own context (real risk was low) — Boris chose to close them anyway as part of finishing the refactor before a code-quality review, not because the risk assessment changed.
- `acknowledge_errors` was deleted rather than restored as a real "Export anyway" feature: confirmed distinct from the still-live "Import As Is" per-group feature, and confirmed both real `Severity::Error` issue types already have inline correction UI, so the override was purely dead weight. Full original code preserved verbatim at [[Deleted Code - acknowledge_errors Export Override (Recovery Snapshot)]] in case testing later shows a real need for a bulk override.
- New standing behavioral rule adopted mid-session or [[Patterns]]: proactively split/modularize line-heavy files that mix multiple concerns whenever spotted, in any repo, without waiting to be asked each time.

## Open

- Both repos' changes are uncommitted, sitting in the working tree — Boris still needs to review and commit/push both.
- Next step per Boris's own sequencing: a fresh code-quality review pass across both repos now that the refactor is fully closed out, before auth resumes.
- `unitprep-api`'s untracked `README.sample.md`/`assets/readme/` (an in-progress README redesign) still sitting uncommitted, unrelated to this pass — Boris's call, low priority.
- Auth Phase 2 tasks 4-11 still fully pending, unchanged from [[Phase 2 Progress]].

## Related

- [[Third Hardening Pass (Pre-Auth-Resume)]]
- [[Frontend v1.1.3 - Test Coverage Expansion]]
- [[Post-Refactor Audit - Details]]
- [[Deleted Code - acknowledge_errors Export Override (Recovery Snapshot)]]
- [[Key Decisions]]
