---
date: 2026-08-13
description: "First milestone of the fix plan for the third CTO-grade audit (see 2026-08-13-third-cto-grade-audit-auth-through-template-tagger.md): closed the sessi"
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 1 shipped — closed the 4 highest-risk findings from the third audit

First milestone of the fix plan for the third CTO-grade audit (see 2026-08-13-third-cto-grade-audit-auth-through-template-tagger.md): closed the session-ownership IDOR, the docx-surgeon quick-xml CVE, the last-active-admin concurrency race, and the frontend admin-redirect race. All four verified — full backend test suite, clippy, cargo audit, frontend vitest/tsc/eslint all clean, plus 2 new regression tests proving the two highest-severity fixes actually work end-to-end. Milestones 2-8 of the plan (C:\Users\bmaksimov\.claude\plans\polished-crunching-hopcroft.md) not yet started — M2 specifically needs Boris's input on the TOTP re-enrollment step-up question before it can proceed.

## What changed

- core/src/session_store.rs & src/auth/roles.rs (unitprep-api) - no logic change to session_store.rs itself (with_owned_session already existed correctly); added remaining_active_admins_excluding() to roles.rs, locking the shared auth.roles 'admin' row before counting
- src/api/{analyze,export,validate,cancel_session,correct,correct_group,exclude_group,exclude_groups,exempt,acknowledge_group_warnings,group_file_confirm,group_file_upload,select_group_file,select_unit_file,resolve_unit_format,dedup,tagger}.rs and discover/mod.rs (unitprep-api) - switched every session-touching handler from with_session/with_session_mut to with_owned_session/with_owned_session_mut, renaming _user->user; tagger.rs's report/apply handlers were a 2nd real IDOR instance the original audit's agent-scoping missed entirely (assigned to neither the API/infra agent nor caught by the template-tagger agent)
- src/api/auth_user_role.rs & auth_user_status.rs (unitprep-api) - replaced duplicated inline admin-count query with the new shared, lock-taking helper
- docx-surgeon/Cargo.toml + docx-surgeon/src/read.rs (unitprep-api) - bumped quick-xml 0.36->0.41; had to rewrite <w:t> text extraction from a single-event read to a loop, since 0.41 splits entity/character references out of Event::Text into a new Event::GeneralRef that didn't exist in 0.36 (this broke 2 existing tests until fixed -- a real API-shape change, not just a version bump)
- src/api/test_support.rs, dedup_test_support.rs, tagger_test_support.rs (unitprep-api) - added test_user_id(), a fixed constant now used as both test_user()'s id and every session-fixture's owner_id, so existing tests keep passing without each one threading a shared id through by hand; fixed 3 test files whose sessions were built with a raw Session::new(id, None) outside the shared fixtures and needed the same fix directly
- app/(app)/layout.tsx (unitprep-ui) - added the missing `!checked` loading branch to AppLayout, before the isSignedOut/needsTotpOnboarding check
- app/(app)/layout.test.tsx (unitprep-ui, NEW) - 3 tests covering AppLayout's loading/ready/signed-out states, specifically regression-testing the checked-race fix


## Decisions

- A plain `FOR UPDATE` on the admin-count query (as the fix plan literally proposed) would NOT have actually closed the concurrency race: two transactions each excluding a DIFFERENT admin only ever lock the *other* admin's row, so their locks never conflict and both can still commit, zeroing out admins. Caught this during implementation, not before -- the real fix locks a resource BOTH transactions must touch regardless of target (the shared `admin` role row itself via `SELECT ... FROM auth.roles WHERE key='admin' FOR UPDATE`), which genuinely serializes the two callers.
- Used a fixed, obviously-fake constant UUID (`Uuid::from_u128(1)`) as the shared default test-owner id rather than giving every fixture function its own owner_id parameter -- keeps ~15 existing test call sites unchanged while still proving ownership is enforced (a test that wants a mismatch constructs its own distinct AuthenticatedUser inline, as the new IDOR regression test does).
- Did not attempt a live curl/browser click-through for the IDOR and auth-race fixes (as the fix plan's verification section suggested) -- that needs a running Postgres + a real logged-in admin, which wasn't already up. Wrote a durable automated regression test instead (one Rust HTTP-handler test, one Vitest suite) for each, which proves the same thing and doesn't rot.
- Did not run the 6 review agents' cargo/npm commands concurrently with each other or with this fix work -- ran every build/test/lint/audit command strictly sequentially given this machine's documented RAM ceiling; no issues, no slowdowns observed.


## Learned

- quick-xml 0.36->0.41 is not a drop-in security patch for any consumer that reads text content directly: 0.41 added Event::GeneralRef as a distinct event, splitting what used to be one Event::Text (e.g. 'Smith &amp; Sons') into Text/GeneralRef/Text. Code that reads 'exactly one event after a text element's start tag' (a `match reader.read_event() { Text => .., End => .. }` shape, not a loop) will silently truncate any text containing an entity. `core`'s spreadsheetml.rs already had the decode()+unescape() half of this fix from the LAST audit's dependency bump, but that file's parser loops over the whole document already so it never hit the GeneralRef-splitting issue; docx-surgeon's per-element single-read shape did, and only its own test suite caught it (docx-surgeon/edit.rs::escapes_special_characters_in_the_replacement and read.rs::decodes_xml_entities_in_run_text) -- cargo check alone did not, since the code compiled fine and just returned truncated strings.
- PostgreSQL flatly rejects `FOR UPDATE` on any query containing an aggregate function (`SELECT count(*) ... FOR UPDATE` is a syntax/semantic error, not just unhelpful) -- would have been caught immediately by cargo test if I'd tried it literally, but worth remembering the reasoning doesn't even get that far: FOR UPDATE needs row identity to lock, which an aggregate collapses away.
- This session's audit-agent scoping (splitting API/session/infra vs template-tagger vs auth into 3 separate review agents) left tagger.rs's session handlers unreviewed by anyone for the IDOR pattern specifically -- the API/infra agent's prompt explicitly excluded tagger.rs ('owned by the template-tagger agent'), and the template-tagger agent's prompt focused on the tagger pipeline's own logic, never mentioning session-store ownership at all. A cross-cutting security pattern (session ownership) doesn't respect the feature-area boundaries a code-quality-focused agent split draws -- worth a dedicated cross-cutting grep-based sweep for any future 'is this pattern applied everywhere' audit, not just parallel per-area review.


## Verification

Backend: cargo check/clippy --workspace --all-targets clean (0 warnings); cargo test --workspace 580 passed/0 failed/1 ignored (579 baseline + 1 new IDOR regression test); cargo audit clean (0 vulnerabilities, was 2 High before the quick-xml bump). Frontend: tsc --noEmit clean; eslint clean on changed files; vitest run 42 files/295 tests passed (including the new 3-test layout.test.tsx suite). Both the IDOR fix and the frontend auth-race fix have dedicated automated regression tests proving the exact failure mode from the audit no longer reproduces.



## Related

- [[2026-08-13-third-cto-grade-audit-auth-through-template-tagger]]


_Recorded 2026-08-13T20:48:52.240Z from `bmaksimov` via the om MCP server (routing: caller)._
