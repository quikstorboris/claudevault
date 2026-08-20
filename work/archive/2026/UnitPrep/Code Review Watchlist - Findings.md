---
date: 2026-07-27
description: "Exhaustive item-by-item log of the unitprep-api code-review watchlist (2026-07-09 through 2026-07-23), split out from the main note for size."
tags: [work-note, unitprep]
status: completed
quarter: Q3-2026
project: unitprep
---

# Code Review Watchlist — Findings

Full item-by-item detail behind [[Code Review Watchlist]]. Split into a
companion note because the source memory ran ~30KB — this note holds the
exhaustive log; the main note keeps the closure summary and the two
highest-signal findings prominent.

Concerns originally identified in a review of `unitprep-api` as of
2026-07-09. Numbering below matches the original watchlist items.

## 1. Lock ordering in `InMemorySessionStore` — RESOLVED (documentation only), 2026-07-09

The invariant (outer collection lock before an individual session lock,
never the reverse; never hold a session lock across `.await`) is now
written directly on the `SessionStore` trait in `session_store.rs`,
binding on any future implementation (Redis-backed, or a second store for
the tenant-dedup workflow). No behavior changed — this was purely making
an implicit rule explicit before a second store implementation could
accidentally violate it.

## 2. Empty `src/shared/` module — RESOLVED (deleted), 2026-07-17

Turned out simpler than "delete or document": it was a genuinely empty
directory (zero files), not referenced by any `mod shared;` declaration
anywhere in the codebase, and **not tracked in git at all**
(`git ls-files`/`git log` showed nothing for the path) — a stray local
filesystem leftover, not compiled code, not version-controlled. Removed
via a plain `rmdir`, no commit needed (git never knew about it). Build
(all crates) and full test suite (114 tests) reconfirmed passing after
removal. Unlike `src/ai/` (item 9 below), this one had nothing to
preserve.

## 3. `.expect("...lock poisoned")` throughout `in_memory_session_store.rs` — RESOLVED, 2026-07-09

Switched `SessionStore`/`InMemorySessionStore` from `std::sync::RwLock` to
`parking_lot::RwLock` (new dependency). parking_lot has no poisoning
concept — a panic while holding a lock just releases it, so this failure
mode is eliminated architecturally rather than given a recovery policy.
All `.expect("...poisoned")` calls removed (parking_lot's
`.read()`/`.write()` return guards directly, not `Result`). Separately
hardened the background cleanup task with `std::panic::catch_unwind`
around each tick, so *any* panic in a tick (not just lock-related) logs
and skips that tick instead of silently ending the cleanup loop forever —
directly addresses the original "2am silent failure" concern. UX decision
made alongside this: if a session is ever genuinely unrecoverable, treat
it like the existing `SessionExpiredPage` case rather than building
bespoke recovery UI — no frontend changes needed. Full test suite (65
tests) passed after the change; no behavior change for callers.

## 4. Unverified CHANGELOG claim — confirmed clean, 2026-07-17

The CHANGELOG stated the "Area doesn't match width×length" check was
removed entirely; this was flagged as unconfirmed against
`validation/row_checks.rs`/`validation/group_checks.rs`. Also flagged for
closer look: `analysis/fingerprint.rs` (the project's historically
bug-prone module — see [[Code Review Watchlist]]'s link to the
architecture note for the past false-positive matching incident).
Verified 2026-07-17 as part of item 8's validation-aggregate fix: the
CHANGELOG claim is accurate, no drift found.

## 5. Line-heavy files — Phase 1 DONE 2026-07-15, Phase 2 DONE 2026-07-15

**Phase 1** used Rust's `#[path = "..."] mod tests;` to physically
relocate each file's inline `#[cfg(test)] mod tests { ... }` block into a
sibling file, keeping it a true child module (`use super::*` and all
private-item access keep working — zero behavior change, purely
mechanical). Applied to 8 files:

- `src/api/discover.rs`: 362 → 210 (`discover_tests.rs`)
- `src/api/mod.rs`: 485 → 225 (`test_support.rs` — shared test helper module)
- `src/api/correct.rs`: 260 → 90 (`correct_tests.rs`)
- `src/domain/validation/mod.rs`: 732 → 284 (`validation_tests.rs`)
- `src/api/validate.rs`: 397 → 267 (`validate_tests.rs`)
- `core/src/in_memory_session_store.rs`: 629 → 375 (`in_memory_session_store_tests.rs`)
- `src/api/analyze.rs`: 460 → 344 (`analyze_tests.rs`)
- `src/api/export.rs`: 509 → 368 (`export_tests.rs`)

`core/src/parsing.rs` (667) deliberately skipped in Phase 1 since its
Phase 2 restructure would reshape its test file anyway.

Result: `discover.rs`, `mod.rs`, `correct.rs` landed comfortably under
250. `validate.rs` (267) and `validation/mod.rs` (284) landed close
enough that no further splitting was planned — each is one cohesive
concept. `analyze.rs` (344), `export.rs` (368), and
`in_memory_session_store.rs` (375) still had real implementation bulk
test-extraction couldn't fix — the session store file was deliberately
left alone beyond this (one implementation of one trait, a legitimately
singular responsibility). Verified: 80/80 tests passing, zero warnings
throughout.

**Phase 2** (due diligence performed first — read all three candidate
files fully before proposing any split):

- `core/src/parsing.rs` (667) → split into
  `core/src/parsing/{mod,csv,excel,spreadsheetml}.rs`, mirroring the
  existing split-by-concern pattern
  (`domain/analysis/{batch,fingerprint,reference}.rs`). `mod.rs` (72)
  keeps just the dispatch; `csv.rs` (43) and `excel.rs` (132) are clean;
  `spreadsheetml.rs` (452 incl. tests, ~312 real) stays the largest piece
  deliberately — a hand-rolled XML event-loop parser is inherently
  verbose. All external call sites (`session_service.rs`,
  `parsing_tests.rs`) unchanged via re-exports from `parsing/mod.rs`.
- `api/analyze.rs` (344) → 321: extracted the ~25-line "which document is
  the master group file" selection into
  `domain::analysis::reference::select_group_document` — a genuine
  business-logic misplacement fix, not just a line-count trim.
- `api/export.rs` (368) → 305, and `infrastructure/csv_export.rs` (~363)
  → 403: moved the ~70-line ZIP-packaging block (build cursor, write each
  file, finalize) into a new `csv_export::build_zip` function. Fixes a
  genuine layering violation (ZIP construction is an infrastructure
  concern that was living in the HTTP handler layer), and incidentally
  collapses three duplicated ad hoc 500-response blocks into one shared
  `internal_error()` call. Explicit, considered trade-off: this relocates
  size into a file already flagged as large, accepted deliberately since
  "properly modular and readable" matters more than an absolute line
  count once a file legitimately owns more content (Boris's explicit
  call, 2026-07-15).

Verified after every step: 80/80 tests passing, zero warnings.

## 6. Similarity matching is O(net_new × reference) — deferred, not a bug

Full fingerprint parse each time; fine at current facility data volumes,
not free forever. Explicitly deferred 2026-07-15 as real algorithmic
work, not infrastructure hygiene — revisit only if actual data volumes
grow enough to justify it (e.g. caching parsed fingerprints instead of
re-parsing per comparison).

## 7. Sessions are in-memory only — deferred, future work

A process restart loses everything. Fixing this means real persistence
(a backing store — Redis was the originally envisioned swap-in per
`SessionStore`'s own doc comments — or similar), a new dependency, and
real design decisions. Explicitly agreed 2026-07-15 as valid future work
once the current foundation effort is done, not something to fold into
it now.

## 8. Second external review pass, 2026-07-15 — mostly RESOLVED same day

A follow-up review (after the item-3/5 fixes shipped) found:

- (a) error response shape was only ~80% uniform (`session_not_found`,
  and two places in `export.rs`, still used plain text instead of
  `ApiErrorBody`) — FIXED.
- (b) `domain::analysis::reference::load_reference_groups_from_document`
  had the exact same ad hoc lowercase-only header lookup bug already
  fixed elsewhere — FIXED, switched to `header_index`.
- (c) `AppState`'s `session_store` field should be named for the tool it
  serves now, before a second tool needs its own field — FIXED, renamed
  to `unit_group_sessions`.
- (d) README/CHANGELOG had drifted from the actual post-workspace-split
  architecture — FIXED (README rewritten, one `[Unreleased]` CHANGELOG
  entry added for the real API-contract change).

Frontend gap also closed: it wasn't reading the `message` field from
error bodies at all, just showing a bare "HTTP {status}" — added
`errorMessageFrom()` in `unitprep-ui`'s `lib/api.ts`, applied across all
6 error-handling call sites.

**The validation aggregate edge case — FIXED 2026-07-17.** If literally
every discovered unit file hit the loud-Err path, the endpoint could
still report `files_checked: 0, ready: true` — a fake zero-value success,
the exact anti-pattern this project already fixed for session-404s and
stage-conflicts elsewhere. Verified first that no 4th instance of the
header-normalization bug exists anywhere in the workspace (the thing that
would actually trigger this path) and that the CHANGELOG's "Area check
removed" claim is accurate (item 4, above) — both confirmed clean.

Fix: `unit-group/src/models.rs`'s `ValidationResult` gets a new
`files_errored: Vec<FileValidationError>` field (`{file_name, message}`);
`run_validation` (`src/api/validate.rs`) now records one entry per file
whose `validate_document` call errors, instead of silently skipping it,
and `ready` is `error_count == 0 && files_errored.is_empty()`.
Deliberately did **not** add a new HTTP status (no 500) — reused the
exact mechanism already built for unresolved `Severity::Error` issues
(`ready` gates export, `/export`'s existing `acknowledge_errors` override
covers this too) rather than inventing a parallel one. Per-file log line
bumped from `warn!` to `error!`.

Frontend (`ScanResultsPage.tsx`): new `files_errored` stat tile, a
distinct red banner naming each file and its reason, and the acknowledge
checkbox/label generalized to cover both blocking reasons — this also
fixed a **real latent frontend bug** found along the way: `canExport`
only ever checked `error_count > 0`, so if `ready` were ever false for
any other reason there'd have been no checkbox shown and no way to
override at all. Now `canExport = results.ready || acknowledged`,
trusting the backend's own `ready` computation rather than re-deriving
it.

Verified: 1 new handler-level test forcing a discovered "unit file" to
fail `validate_document`. Full workspace suite (114 tests) passing,
clippy clean, and a live run confirming the normal (non-error) path still
returns `files_errored: []` correctly. Frontend verified via `tsc`/
`eslint` (both clean) and confirming the dev server compiles/serves the
changed route without a server-side crash; full interactive browser
click-through wasn't possible this session — a real verification-depth
gap, not a claim of full manual QA.

Confirmed still correctly deferred at this point (no new information):
`/tools/...` route prefixes, golden test fixtures, fingerprint property
tests, the similarity-algorithm complexity, persistence/Redis, auth.

**`analysis/fingerprint.rs` follow-up audit — DONE 2026-07-17.** Read the
full file and traced its actual consumer (`analysis/mod.rs`'s
`analyze_batch`) to understand the whole pipeline, not just the isolated
matching function. Conclusion: **no bug found in the matching logic
itself** — the fingerprint gate (exact equality on
width/length/location/climate/area_code/floor_access) is strict, and the
remainder-based Levenshtein score it gates only ever feeds an *advisory*
warning, never net-new determination. Found one real, narrow **test
coverage gap** instead of a bug: `FloorAccess::ALIASES` deliberately
orders `"first floor access"` before `"first floor"` (the shorter one is
a literal substring of the longer), and nothing actually tested that
ordering. Added `first_floor_access_and_first_floor_do_not_match` to
close it. Verified: 7/7 fingerprint tests passing, full workspace (115
tests) passing, clippy clean. Two purely theoretical, unconfirmed edge
cases noted but not acted on: `DIMENSION_REGEX` only captures the first
"NxM"-shaped substring in a name; `Location::ALIASES`'s substring
relationships were checked by hand and confirmed not to overlap.

## 9. `src/ai/` — deliberately left alone, per Boris (2026-07-15)

A near-empty placeholder (`AiDecisionContext`,
`describe_ai_ready_contract()`, `#[allow(dead_code)]` throughout)
explicitly commented as a "Future AI integration point for UnitPrep
decision support." Noticed during the `unitprep-dedup` note-composer work
since that work built a much more concrete real version of the same idea
(a `NoteComposer` trait with an actual default implementation). Asked
whether to delete or repurpose this stub — Boris's answer: leave it
as-is. The vision is real future AI integration, possibly even a local ML
module, and an inert placeholder for that is fine to leave alone rather
than force a decision now. Not a candidate for deletion or "dead code"
cleanup going forward.

## 10. `build_batch_from_documents` header lookup — FIXED, 2026-07-16

Same bug class as the header-normalization gap fixed twice before
(discover.rs, `reference.rs`'s Name lookup): used a bespoke
`h.to_lowercase() == "unitgroup"` check instead of `header_index`, so a
header like `Unit_Group` would silently miss it — the file would be
accepted by discovery/validation, then silently dropped from analysis
inventory. Caught by an external review pass (Grok), verified against the
actual code before fixing. Switched to `document.header_index("unitgroup")`.
Added 3 tests to `batch.rs` (previously untested): exact-header case, the
underscore/casing regression case, and the no-group-column skip path.

## 11. Clippy strict mode (`-D warnings`) — clean as of 2026-07-16

External review (Grok) correctly flagged that `cargo test`/`cargo build`
being clean doesn't mean clippy's stricter lints are. Verified and fixed
three real issues: `type_complexity` on `dedup/src/ingest.rs`'s
column-setter table (factored into a `ColumnSetter` type alias),
`needless_range_loop` in `dedup/src/similarity.rs`'s `longest_match`
(switched to `.iter().enumerate().take().skip()`), and
`empty_line_after_doc_comments` in `api/mod.rs`. Also fixed two
`manual_repeat_n` lints in the new `dedup_csv_export.rs` along the way.
`cargo clippy --workspace --all-targets -- -D warnings` was clean as of
that commit.

## 12. HTTP error contract unevenness — FIXED, 2026-07-16

Two endpoints predated the error-shape uniformity work: `POST
/group-file/select` returned `200 { success: false }` for both "discovery
hasn't run yet" and "that file wasn't discovered" — now `409 Conflict`
(stage_conflict) for the former, `400 Bad Request` (`group_file_invalid`)
for the latter. `POST /session/cancel` stays deliberately idempotent
(always `200`, even for an unknown id — a documented design choice) but
now returns `deleted: bool` so a caller that cares can tell the two cases
apart without changing the success contract. Caught by an external review
pass (Grok), verified against the actual code before fixing.

## 13. `unit-group` crate extraction — Phase 1 & 2 DONE 2026-07-16

**Phase 1 (commit `cac4567`)**: the long-deferred extraction finally
started, once `unitprep-dedup` had proven the target shape twice over.
Moved analysis (batch/fingerprint/reference), validation (all row/group
checks), corrections, and models (`AnalysisResults`, `BatchRun`,
`Facility`, `AdvisoryIssue`, `Severity`, `SimilarityMatch`) out of
`src/domain/` into the previously-empty `unit-group` crate — same
boundary as dedup: pure logic + result data only, zero session/HTTP
awareness. `DiscoveryResult` moved too, ahead of the rest of
`session.rs`. `regex`/`once_cell`/`strsim`/`tracing` migrated to the new
crate's own `Cargo.toml`; `serde` added for the same reason dedup carries
it. Six call sites repointed: `analyze.rs`, `validate.rs`, `correct.rs`,
`exempt.rs`, `discover.rs`, `test_support.rs`, plus
`infrastructure/csv_export.rs` (found only during the build — not part
of the originally-catalogued import surface).

Verified three ways: full workspace build, full test suite (same 109
tests as before, now split 34 binary / 25 core / 15 dedup / 2
dedup-fixture / 33 unit-group), and a live run — started the real
server, pushed a real unit/group CSV pair through the actual
upload→discover→validate→analyze→export HTTP pipeline, confirmed correct
net-new-group detection, validation warnings, and export ZIP contents.
Clippy clean under `-D warnings`. `src/domain/` held only `mod.rs` and
`session.rs` after Phase 1.

**Phase 2 (commit `94a5444`), same session.** `ValidationResult`/
`ValidationIssueSummary` moved to `unit-group`'s `models.rs` alongside
`DiscoveryResult`. `Session`/`WorkflowStage`/`StageError`/`SessionData` —
the actual stage machine — moved into the binary's new
`src/application/unit_group_session.rs`, alongside the pre-existing
`session_service.rs`. `src/domain/` is now gone entirely (both files
deleted, directory removed); every `crate::domain::session::*` reference
across `api/*.rs`, `main.rs`, and `application/session_service.rs`
repointed to `crate::application::unit_group_session::*`.
`unit_group_session.rs` crossed 250 lines with its inline test module
attached — extracted to `unit_group_session_tests.rs`, the same
`#[path]` pattern already used 8 times elsewhere in this codebase.

Verified three ways, same discipline as Phase 1: full build, full test
suite (same 109 tests, same 34/25/15/2/33 crate split — nothing
lost/duplicated across *both* phases), and a second live server run of
the full pipeline, this time specifically confirming the 409
stage-conflict response still fires correctly before validation
completes. README/CHANGELOG updated — `unit-group` is no longer described
as an empty stub anywhere. Clippy clean under `-D warnings`.

The extraction is now fully complete — both phases done,
`unitprep-unit-group` holds all of Group Prep's domain logic,
`src/domain/` no longer exists, the binary holds only session/HTTP
orchestration for both tools. This was the last piece of the
"domain-first" workspace-migration story that started 2026-07-15; the
platform reached full architectural consistency between its two tools.

## 14. Full front+back review, 2026-07-23 — all High/Medium items FIXED same day

Two parallel agent reviews (backend `unitprep-api`, frontend
`unitprep-ui`), done while auth Phase 2 was mid-flight — auth code itself
audited and found clean (session tokens, RLS transaction scoping,
SECURITY DEFINER `search_path` pinning, cookie flags all correct); no
login/registration handlers existed yet, so nothing further to exploit
there at the time.

**CSV/formula-injection gap (Medium, backend) — FIXED.** New
`src/infrastructure/csv_safety.rs::sanitize_cell` prefixes any cell value
starting with `=`/`+`/`-`/`@`/tab/CR with a leading apostrophe (standard
OWASP mitigation). Applied to every tenant/facility/group field written by
`dedup_csv_export.rs`, `dedup_xlsx_export.rs` (including the
note/hyperlink-text cell), and `csv_export.rs` (group names, facility
name, source-file list, advisory issue text). Full workspace test suite
(147 tests) still passed; clippy showed zero new issues in the touched
files (pre-existing WIP-auth clippy failures were unrelated).

**RLS admin-bypass gap on credential tables (backend, design question,
not fixed — deliberately left open).** `webauthn_credentials_owner_only`/
`totp_credentials_owner_only` have no admin-bypass clause the way
`users`/`sessions` do, so there's no RLS-level path for an admin to help a
locked-out user recover/revoke a passkey. May be deliberate for v1 —
confirm before building the recovery flow.

**Three frontend bugs sharing one root cause (High) — FIXED.** All three
were unscoped local UI state surviving past the data it gates:

1. `DiscoveryPage.tsx` `localReady` set once, never reset.
2. `UnitFileResolutionPanel.tsx` `mapping`/`showManualMapping` not
   reseeded on a second discovery cycle.
3. `ScanResultsPage.tsx` issue cards keyed by array index, with
   `CorrectionField`/`ExemptButton` keyed only by field name.

Fix for #1/#2: `app/clients/[clientId]/unit-groups/page.tsx` now passes
`key={sessionId}` to `<DiscoveryPage>` — a new session (assigned on every
successful re-upload/re-discover) forces a full remount of
`DiscoveryPage` and its child `UnitFileResolutionPanel`, wiping stale
local state at exactly the right boundary. Fix for #3:
`ScanResultsPage.tsx` now keys each `IssueCard` on a stable composite
identity (`issueKey()`: file_name + description + affected_unit_ids)
instead of array index, so a correction removing an issue and shifting
the list can no longer make a later issue inherit a previous one's
"saved" state.

**Medium/low frontend items — mostly FIXED:**

- Duplicate "Files Selected" label confusion — FIXED: the raw
  folder-picker count in `DiscoveryPage.tsx` is now labeled "Files Found
  in Folder", distinct from the filtered post-upload "Files Selected"
  stat.
- Dormant no-abort-on-sessionId-change race in `useAnalysis.ts`,
  `useDedupReport.ts`, and `ScanResultsPage.tsx`'s validate effect —
  FIXED: all three now use a `startedFor`/`ignore`-flag pattern (an
  `AbortController`-style guard) so a genuine sessionId change gets its
  own fetch and a stale in-flight response can't overwrite newer state.
- First-paint "client not in session" flash on refresh, `lib/clients.tsx`
  — FIXED: added a second `useSyncExternalStore`-backed `hydrated` flag
  (module-level, alongside the existing `cache` store — not
  `useState`-in-effect, which this project's ESLint config flags as
  `react-hooks/set-state-in-effect`) so
  `app/clients/[clientId]/layout.tsx` shows a neutral "Loading…" state
  instead of asserting "not in session" before sessionStorage has been
  read.
- Not fixed (accepted as-is, per the review's own read): `ScanResultsPage.tsx`
  (735 lines, 4 concerns) not split — no functional issue, just a
  size/organization note (later addressed by the [[Full Review & 9-Milestone Refactor]]);
  duplicated download/fetch-once hook logic between dedup and export;
  inconsistent client-side file-type filtering between the two upload
  flows. Low-priority style/organization notes, not correctness bugs.

Backend perf notes (not bugs, fine at current data volumes, not touched):
`dedup/src/grouping.rs::group_records` is O(n) linear-scan per record;
`report.rs::find_typo_variant_candidates` and `relatedness.rs` are O(g^2)
over tenant groups.

**Verification.** Backend — full workspace `cargo test` (147 tests) and
targeted clippy diff, both clean. Frontend — `tsc --noEmit`, `eslint`
(both zero errors after fixing one `react-hooks/set-state-in-effect`
violation the first `lib/clients.tsx` draft introduced), and `next build`
(production build) all clean. Live-verified in the browser: recreated
the `/mnt/c/Users/bmaksimov/bin/node` symlink (had gone stale — pointed
at a `.vscode-server` build-hash directory that no longer existed;
re-pointed at the current one), started both dev servers, created a real
client, confirmed the info page resolves correctly on a hard refresh (no
lingering error state), and confirmed the "Files Found in Folder" label
renders as expected on `/unit-groups`. Full interactive file-upload
click-through (to visually exercise the `key={sessionId}` remount and
`issueKey` fixes end-to-end) wasn't possible — the in-app browser tool
has no file-upload action — so those two rest on code-level verification
plus the clean tsc/eslint/build passes, not a manual click-through. Both
dev servers were stopped after verification.

No dead code, no path-traversal surface, no XSS/secret-exposure found on
either side.

**Git reconciliation, same day (2026-07-23).** While applying the fixes
above, discovered `unitprep-api` had a second branch,
`claude/orchestrator-db-organization-psnq8b`, diverged from `main` right
after "Add AuthenticatedUser extractor" — bot-authored (`Claude
<noreply@anthropic.com>`, not Boris), origin unclear (no scheduled
task/cron explains it; `gh` wasn't authenticated to check GitHub PR/Actions
history further). This branch is exactly why the backend half of this
review missed the dedup-note-copy-rework and multi-vendor-discovery
commits (both on `main`, not on that branch) and undercounted tests by 32
(147 vs. main's real 179).

Reconciled per Boris's direction: confirmed zero file overlap between the
orphan branch's one commit and both `main`'s exclusive commits and this
review's own fix, checked out `main`, cherry-picked the orphan branch's
commit (`470a457`, clean, no conflicts) as `c780a7e`, full workspace test
suite re-verified (181 tests passing) before committing the CSV-injection
fix as `841eff9` on top. Both repos pushed to `origin/main` same day, then
the orphan branch (`claude/orchestrator-db-organization-psnq8b`, local +
origin) was deleted — `main` now has everything it had, both repos are
back to a single branch each.

Also noted, not fixed (out of scope for this pass): `cargo clippy
--workspace --all-targets -- -D warnings` currently fails on
`dedup/src/note_composer.rs:264` (`needless_lifetimes` on
`units_by_value`) — pre-existing on `main`'s dedup-rework commit,
unrelated to anything touched this session. Trivial one-line fix (`fn
units_by_value(group: &TenantGroup, ...)`, drop the `'a`), just never
asked for.

## Related

- [[Code Review Watchlist]] — closure summary and highest-signal findings
- [[Full Review & 9-Milestone Refactor]] — the later, larger review pass that picked up several deferred items above (ScanResultsPage split, discover.rs/fingerprint.rs splits)
- [[UnitPrep Architecture Overview]]
