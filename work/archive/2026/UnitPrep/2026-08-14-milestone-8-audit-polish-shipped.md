---
date: 2026-08-14
description: "Milestone 8 (remaining low-severity polish) shipped across both repos -- unitprep-api v1.8.7, unitprep-ui v1.5.6. Closes the third audit's full fix plan (M1-M8)."
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 8 shipped — unitprep-api v1.8.7, unitprep-ui v1.5.6

Completed all 12 items of milestone 8 (remaining low-severity polish), closing the third audit's fix plan (M1-M8) started in [[2026-08-13-third-audit-fix-plan-full-session-handoff-m1-m2-done-m3-in-p]]. Backend was delegated to a subagent (verified each file/line location fresh, since several had moved since M5/M6's splits, exactly as warned it would need to); frontend done directly by the main session. Item #7 (below) surfaced a pre-existing, deliberate, already-documented decision — correctly left unchanged and surfaced rather than silently overridden, then reversed in a follow-up commit once Boris explicitly confirmed he wanted the IP captured after all.

## Backend — unitprep-api v1.8.7 (8 commits)

- docx-surgeon/src/read.rs - fixed RunSpan::run_start doc comment's dead link to nonexistent apply_hidden_blank_edits, now points at apply_underline_edits/apply_all_edits (confirmed both exist in edit/mod.rs post-M6)
- dedup/src/relatedness/mod.rs - find_related_tenant_candidates still lives in mod.rs (not moved to household.rs by M6); renamed a closure param `groups` that shadowed the outer `groups: &[TenantGroup]` parameter to `member_group`
- unit-group/src/validation/mod.rs - RowScan::group_fingerprint was a method that always .clone()'d the cached (bool, GroupFingerprint) tuple even on a hit; removed the method, inlined the HashMap entry access directly in record_row, and changed downstream reads to borrow the cached GroupFingerprint instead of cloning it (only bool is copied) since every caller only ever needed a reference
- src/application/dedup_session_service.rs - DedupSessionService::create_session now returns (String, DedupReport, Vec<TenantRecord>) instead of just the session id, since the report/records were already built locally before being stored
- src/api/dedup.rs - check() handler no longer re-fetches the just-created session via with_owned_session + double .clone() right after DedupSessionService::create_session saved it; uses the tuple create_session now returns directly
- src/api/tagger.rs - added a one-line comment on load_label_proximity_patterns noting sentence_pattern-kind rows and qms_tag.value_shape aren't consumed by that query yet (schema exists, consumer doesn't read them)
- src/api/auth_login.rs - added an accepted-residual-risk doc comment on login_begin's challenge-generation branch: it does real work (WebAuthn challenge build) only when a login candidate resolves, so response timing can in principle distinguish account-exists from account-doesn't-exist even though the HTTP body/status are identical; not mitigated with a dummy challenge because start_passkey_authentication requires a real credential, and the local crypto cost is small relative to the DB round trip both branches already pay
- src/api/auth_audit_logs_export.rs - export_audit_logs's render_audit_log_pdf(&report) call (synchronous, CPU-bound PDF layout/rendering) was NOT wrapped in spawn_blocking; wrapped it in tokio::task::spawn_blocking with a panic-safe match arm returning internal_error on JoinError
- src/api/auth_login.rs + auth_register.rs - follow-up commit reversing item 7's prior decision per Boris's explicit call (see Decisions below): login_begin and register_begin now take ConnectInfo<SocketAddr>, populate ip_address via request_context(), and reject_registration gained an ip_address parameter passed through from both its call sites

## Frontend — unitprep-ui v1.5.6 (4 commits)

- components/discovery/FormatResolutionActiveView.tsx - collapsed a literally duplicated "Confirm {vendor}" button (same onClick/disabled/label logic, rendered once above the manual-mapping table and once beside it) into a shared ConfirmVendorButton
- components/unit-groups/useDiscoveryFlow.ts + its test - upload/discover failures threw "Upload failed (500)"-style bare-status messages instead of the backend's actual error body via errorMessageFrom, unlike every sibling upload page; fixed, and updated the two test assertions to the resulting fallback shape ("HTTP 500"/"HTTP 404") for their body-less mock responses
- components/TaggerResultsPage.tsx + components/tagger/useTaggerApply.ts - renamed the local preserveBlanks state/prop to preserveUnderscores to match the "Preserve underscores" checkbox copy the user actually sees; the wire field sent to /tagger/apply stays preserve_blanks (the backend's own contract), translated at the call site
- components/nav/LeftNav.tsx - flagged (comment only, no fix) that the signed-in shell shows roles instead of a name/email because WhoAmI never surfaces auth.users' first_name/last_name/email columns, even though they exist -- a product/schema question, not a frontend bug


## Decisions

- Item 6: found no existing 'timing leak accepted risk' doc comment anywhere in the repo (grepped for timing/side-channel/constant-time across all crates) -- the milestone plan's premise that one already exists was stale/incorrect. Treated login_begin's conditional WebAuthn-challenge-generation timing gap as the real, previously-undocumented instance and documented it as an accepted risk rather than building a dummy-challenge mitigation, since webauthn-rs's start_passkey_authentication needs a real credential set to build a challenge against (no cheap no-op equivalent), and the timing delta is small relative to the DB round trip every branch already pays -- making a reliable network-timing exploit impractical. A password-style 'always do a dummy expensive operation' mitigation was judged not cheap/low-risk enough to justify over documenting.
- Item 7: found src/api/auth_register.rs (reject_registration, ~line 214) already carries an explicit, cross-referencing comment: 'No ConnectInfo here -- every call site of this helper is on the /begin leg, which does not take it (see login_begin for the same shape of decision on the login side).' This is a deliberate, symmetric, already-documented decision applied identically to both login_begin and register_begin's rejection paths, not an oversight or asymmetry -- so the subagent correctly left it alone and flagged it back rather than reversing it unilaterally. Asked Boris directly (AskUserQuestion): keep as-is, or add ConnectInfo/IP now for better probing-attempt correlation. He chose to add it -- done in a follow-up commit (main session, not delegated): both /begin handlers now take ConnectInfo<SocketAddr>, reject_registration gained an ip_address parameter, and the stale "No ConnectInfo here" comment was removed since it no longer describes the code.


## Learned

- auth_register.rs's reject_registration helper explicitly cross-references login_begin's identical decision in its own doc comment -- worth grepping sibling files' comments before assuming a described gap is real, since the codebase sometimes documents symmetric decisions in only one of the two places they apply.
- RowScan::group_fingerprint's clone was avoidable entirely (not just reducible to miss-only) once traced downstream: every caller only ever read the cached GroupFingerprint by reference (never took ownership), so inlining the HashMap::entry access directly in the caller (rather than going through a &mut self method) let the borrow checker split self's fields and return a live reference into the cache with zero clones, on both hit and miss.


## Verification

Backend: cargo fmt --all -- --check, cargo clippy --workspace --all-targets (zero warnings after fixing 3 needless_borrow warnings the item-3 edit introduced), cargo test --workspace -- all clean, 550 tests, 0 failed, 3 ignored (expected). Frontend: npx tsc --noEmit, npx eslint . (0 errors, 1 pre-existing unrelated warning in generated coverage/), npx vitest run -- 330/330 passing across 46 files.


## Related

- [[2026-08-14-milestone-7-test-coverage-debt-shipped|Milestone 7]]
- [[2026-08-14-milestone-6-file-splits-shipped|Milestone 6]]
- [[2026-08-13-third-audit-fix-plan-full-session-handoff-m1-m2-done-m3-in-p|Third audit and its fix plan]]
- [[Patterns]]
- [[Gotchas]]

_Recorded 2026-08-14 from `bmaksimov`._
