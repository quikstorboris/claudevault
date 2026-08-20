---
date: 2026-07-28
description: "Event-log satellite for Third Hardening Pass (Pre-Auth-Resume): the first-hand discovery-and-fix session notes behind that summary, verbatim, in order"
tags: [work-note, unitprep, event-log]
status: completed
quarter: Q3-2026
project: unitprep
---

# Third Hardening Pass (Pre-Auth-Resume) — Session Log

Event-log satellite for [[Third Hardening Pass (Pre-Auth-Resume)]]. That note's own "Verification" section says it was independently confirmed *after the fact* against the WSL checkout (`git log`/`CHANGELOG.md`) — the first-hand discovery-and-fix notes existed too, stuck in the vault's `inbox/` fallback location under auto-generated titles. Recovered 2026-08-10; moved here verbatim, nothing trimmed, in chronological order. See [[Vault Hygiene — Inbox & Loose-Note Consolidation (2026-08-10)]] for how this was found.

## 20:07 — Second-pass adversarial review of unitprep-api file-parsing code (post-fuzz)

Reviewed `core/src/parsing/{excel.rs,csv.rs,spreadsheetml.rs,mod.rs}` plus `csv_document.rs`/`uploaded_file.rs` for a second round of adversarial bugs beyond the two already-fixed proptest crashes (`cell_to_string` DateTime panic, SpreadsheetML `ss:Index`/`MergeAcross` unbounded resize). Found and confirmed one new silent-data-corruption bug; ruled out several plausible-looking hypotheses after empirical verification. No new crash/panic bugs found.

**Confirmed real bug**: `core/src/parsing/excel.rs` line 73, `Data::Float(v) => (*v as i64).to_string()` when `v.fract()==0.0` — for any whole-valued f64 outside i64 range (e.g. 1e30), Rust's saturating float→int cast silently produces `i64::MAX`/`MIN` instead of an accurate number or an error. Verified with a temp test: `Data::Float(1e30)` → `"9223372036854775807"`, `Data::Float(-1e30)` → `"-9223372036854775808"`. Not a panic, but silent numeric corruption for any numeric cell in a workbook.

**Ruled out (verified, not bugs)**: (1) CSV BOM handling — hypothesized a leading UTF-8 BOM would survive into the first header name and break lookups; the `csv` crate v1.4.0 already strips it before the reader sees it. (2) XXE/billion-laughs in `spreadsheetml.rs` — `quick_xml`'s `escape::unescape` only expands the 5 predefined XML entities + numeric char refs, never DOCTYPE-defined custom entities. (3) XML nesting depth — `quick_xml::Reader` is a flat pull-parser, no per-element recursion, so deep nesting can't cause a stack overflow.

**Learned**: `as` casts on out-of-range floats do NOT panic in Rust (saturate silently since 1.45) — the risk class here is silent wrong data, not a crash, so it has to be checked by asserting the *value*, not just absence of panic. A no-panic proptest can pass while a correctness bug still ships. Writing a 5-line throwaway `#[test]` (added then deleted) before reporting a hypothesis as confirmed is fast and caught one false positive (BOM) that would have been embarrassing to report as fact.

**Verification**: `cargo test -p unitprep-core` passed 40/40 after cleanup; `git status` clean on `core/src/parsing/`.

**Left open at the time**: the `Data::Float` truncation bug (excel.rs:73) — flagged for the human to decide the right fix. (Fixed in the 20:56 entry below.)

## 20:08 — Second-pass adversarial review, second confirmed bug (SpreadsheetML CDATA data loss)

Follow-up in the same review session: found and confirmed a second real bug after the first note above was already filed. `core/src/parsing/spreadsheetml.rs`'s event-loop match on `quick_xml::events::Event` does not handle the `Event::CData` variant (falls through to the wildcard `_ => {}` arm), so any `<Data><![CDATA[...]]></Data>` cell in a SpreadsheetML file silently becomes an empty string instead of capturing its content.

**Confirmed**: the `match event { ... }` block in `parse_spreadsheetml_document` only matches `Event::Eof`/`Start`/`Empty`/`Text`/`End`. Verified directly: replacing `<Cell><Data ss:Type="String">A01</Data></Cell>` with the CDATA-wrapped equivalent in the existing `SAMPLE_SPREADSHEETML` fixture and reparsing produced `row0 = ["", "10x10 Inside Climate", "", "10"]` — the CDATA cell's value silently vanished, no error surfaced.

**Learned**: `quick_xml`'s `Event` enum has a dedicated `CData` variant separate from `Text` — a match that only lists Start/Empty/Text/End/Eof looks complete but silently skips CDATA, since Rust's `_ => {}` wildcard doesn't warn about the missing case. Worth grepping for `Event::` matches without an explicit `CData` arm in any `quick_xml`-based parser.

**Verification**: confirmed via a temporary `#[test]` (added then removed); `cargo test -p unitprep-core` passed 40/40, `git status` clean afterward.

**Fix suggestion left for the follow-up commit**: add a `CData(t)` arm that decodes/appends `t` the same way `Event::Text` does — CData content is raw and not entity-escaped, so it likely should skip the `unescape` step `Event::Text` applies. (Implemented in the 20:56 entry below.)

## 20:56 — Fixed 12 real bugs found in a 6-agent adversarial review of unitprep-api

Boris asked for a full bug-hunt + fix pass, backend first. Ran 6 parallel adversarial-review agents across `unitprep-core` (parsers), `unitprep-dedup`, `unitprep-unit-group`, and the API/HTTP layer, each instructed to confirm findings empirically rather than report speculative issues. One agent (API HTTP layer) initially reported what looked like a prompt-injection attempt during its scratch-test cleanup; when asked for the verbatim text it retracted the claim as its own fabrication — a genuine self-correction, not an actual injection, recorded as a caution about verifying agent self-reports before treating them as fact. Fixed all 12 confirmed bugs directly, each with its own regression test, split into 13 commits by bug rather than by file (three files each had two unrelated fixes needing a temporary revert/reapply, or one combined commit that says so explicitly, to keep the history honest).

**What changed** (12 fixes): `spreadsheetml.rs` — the missing `Event::CData` arm (fixes the 20:08 finding above). `excel.rs` — `Data::Float`'s as-i64 fast path now only taken when the value fits, else falls back to `to_string()` (fixes the 20:07 finding above). `dedup/src/comparison.rs` — `PhoneNumberPrefix`/`AltContactPhoneNumberPrefix` exempted from the blank-vs-filled-always-differs rule. `dedup/src/grouping.rs`/`normalization.rs` — `group_key` now collapses internal whitespace like every other Plain field. `dedup/src/report.rs` — `partial_cmp().unwrap()` sort replaced with `total_cmp` (removes a latent NaN panic path). `unit-group/src/validation/mod.rs` — the dimension-exemption check now gates the whole flagging condition, not just the numeric-columns branch. Unit-number identifiers trimmed consistently across `unit-group` validation/corrections and `src/api/validate.rs`/`correct_group.rs`. `row_checks.rs` — comma-decimal dimension values ("10,5") now parse correctly. `correct_group.rs` — repeating an identical rename request now no-ops instead of 400ing. `unit_group_session.rs` — added `data_generation` (bumped by every data-mutating method) and `unit_number_occurrences`. `analyze.rs`/`export.rs` — both write-backs now check `data_generation` before promoting the workflow stage, closing a TOCTOU race. `src/api/mod.rs` — new response-rewriting middleware normalizes `Json<T>` extraction-rejection bodies to the standard `{error, message}` shape. `correct.rs`/`exempt.rs` — both now reject a `file_name`/`unit_number` with 0 or 2+ matches instead of silently storing a dead or corrupting entry. `cancel_session.rs` — added a log line for the (unfixed, documented) cancel/concurrent-mutation race.

**Decisions**: Fixed all 12 findings directly rather than delegating — correctness fixes with real data-integrity/concurrency stakes warranted full attention, unlike the earlier test-writing pass where delegation was the right call. Chose a response-rewriting middleware over changing all ~17 handlers' `Json<T>` extractor type — same outcome, avoids a ~110-test-call-site mechanical diff. For the analyze/export TOCTOU race, chose an optimistic-concurrency generation counter over a broader locking redesign — minimal, reuses the existing "downgrade to Validated as a safety net" mechanism. Left two lower-confidence concurrency findings unfixed by design (session-cleanup sweep lock scope; cancel_session's race, which needs tombstoning/deferred deletion) — documented, not silently dropped. Left the dedup name-similarity asymmetry and Unicode/diacritic-insensitive matching (both inherited from the Python reference) as known, accepted characteristics, not confirmed bugs. Did NOT touch the 17 clippy warnings for unused auth scaffolding — deliberate in-progress work, not dead code.

**Learned**: agent self-reports of anomalies need the same verify-before-trust treatment as factual findings — pushing for verbatim source text caught the fabricated-injection claim. Splitting commits by bug is usually possible via temporary revert-then-reapply, or `git apply --cached` on a hand-written patch for non-adjacent changes — but genuinely interleaved fixes are more honestly left as one commit naming both. `quick_xml` 0.41's rejection macros expose `.status()`/`.body_text()` as public inherent methods, useful for the response-normalizing middleware.

**Verification**: `cargo test --workspace` 321 passed (up from 297), `cargo clippy --workspace --all-targets` 0 errors (same 17 accepted auth-WIP warnings), `cargo fmt --check` clean, `cargo cov-summary` 84.99% (up from 84.00%).

## 21:05 — Backend bug-fix batch shipped locally as unitprep-api v1.1.3 (unpushed)

Boris asked to (1) prepare cohesive commits without pushing, (2) decide if a version bump was warranted, (3) list every outstanding bug/improvement/fix/optimization across the whole refactor effort without implementing anything (switching sessions), and (4) evaluate readiness to resume auth development. Bumped `unitprep-api` to 1.1.3 (12 real bugs fixed this session, matching the project's one-bump-per-real-boundary convention) and folded the `Cargo.lock` version sync into that commit via amend (pre-push).

**What changed**: `Cargo.toml`/`CHANGELOG.md` — version bumped 1.1.2 → 1.1.3, itemized entry for all 12 fixes. `Cargo.lock` — version metadata synced via amend.

**Decisions**: Version bump warranted for `unitprep-api` only — `unitprep-ui` was NOT bumped, since no frontend code changed this session (the frontend bugs found by the same bug-hunt were deliberately left unfixed per the "do not implement anything" instruction). Did not push either repo — explicit instruction. 14 `unitprep-api` commits (13 bug fixes + 1 version bump) sat locally on `main`, ahead of `origin`. Amended the version-bump commit once to fold in `Cargo.lock`'s sync rather than creating a 15th commit for a 2-line lockfile diff — safe since neither commit had been pushed.

**Learned**: the om `reason` tool wasn't usable in this environment (`spawn claude ENOENT` — no Claude CLI binary on this machine's PATH for the MCP server to launch a sub-session with); direct Glob/Read against the vault filesystem was the reliable fallback, not a degraded option. `unitprep-api`'s `CHANGELOG` already had precedent for keeping half-built auth work out of version bumps entirely (Phase 2 tasks 1-3 sit under `[Unreleased]`), confirming this batch belonged in its own dated section.

**Verification**: `cargo build` + `cargo test --workspace` after the bump: 321 tests passing, 0 failed, clean. `git status` clean on both repos except the pre-existing, unrelated `README.sample.md`/`assets/` untracked files noted separately in the core note.

## Related

- [[Third Hardening Pass (Pre-Auth-Resume)]] — the core note this satellite provides first-hand detail for
- [[Shipped as v1.1.2]]
- [[Post-Refactor Audit - Details]]
- [[Frontend v1.1.3 — Test Coverage Expansion — Session Log]]
