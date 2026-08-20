---
date: 2026-08-13
description: "Second milestone of the fix plan for the third audit. Closed all 4 M2 items, including one that grew into a real new feature: passkey-based step-up ga"
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 2 shipped — invite role gate, TOTP lockout, passkey step-up for TOTP re-enrolment, upload 401 fix

Second milestone of the fix plan for the third audit. Closed all 4 M2 items, including one that grew into a real new feature: passkey-based step-up gating self-service TOTP re-enrolment (Boris's own security call after clarifying that admin-driven onboarding TOTP setup was never the gap -- self-service re-registration was). unitprep-api shipped as v1.8.2 (4 commits after M1's v1.8.1), unitprep-ui as v1.5.1 (3 commits after M1's v1.5.0). Both pushed to origin/main.

## What changed

- src/api/auth_invites.rs (unitprep-api) - create_invite now requires users.manage_roles in addition to users.manage, closing a latent privilege-escalation seam; regression test added
- src/api/auth_totp.rs (unitprep-api) - enroll_confirm's wrong-code branch now checks the pending secret's lock state and calls auth.record_totp_failure, matching step_up's existing lockout
- NEW src/api/auth_passkey_reverify.rs + auth_passkey_reverify_tests.rs, migrations/20260813150000_add_passkey_reverify_step_up.{up,down}.sql (unitprep-api) - passkey-based step-up (auth.sessions.passkey_reverified_until + auth.record_passkey_reverify, modeled directly on TOTP's own elevated_until/record_step_up), reusing AuthenticationCeremony wholesale; gates enroll_begin whenever a confirmed TOTP secret already exists
- src/auth/authenticated_user.rs, ceremony_cookie.rs, audit_log.rs, mod.rs; src/api/mod.rs, test_support.rs, analyze_tests.rs, auth_login.rs (unitprep-api) - plumbing for the new field/endpoints (AuthenticatedUser.passkey_reverified_until + is_passkey_reverified(), new ceremony cookie constant, 2 new audit event constants, route wiring, load_credentials_for_user/persist_credential_use made pub(crate) and reused rather than duplicated)
- components/discovery/MasterGroupFileSection.tsx (unitprep-ui) - manual upload's hand-rolled fetch now treats 401 the same as 404 (session-expired), closing the gap the audit found; regression test added
- lib/auth.ts, app/(app)/account/page.tsx (unitprep-ui, + new page.test.tsx) - passkeyReverify() (mirrors loginBegin/loginFinish's WebAuthn glue, combined into one function since there's no intermediate user-input step like login's email); account page runs it before revealing the TOTP update form, with inline error handling on failure


## Decisions

- Boris explicitly clarified the TOTP-reenrollment scope before any code was written: admin-driven registration/re-registration forcing TOTP setup was NOT the gap (that's intended, already-built behavior) -- the gap was self-service re-registration having zero re-authentication, which he wants gated by passkey specifically, not by another TOTP code (that would be circular -- TOTP protecting TOTP).
- Chose to build passkey step-up as its own bespoke mechanism (new passkey_reverified_until column/endpoint pair) rather than folding it into the existing admin-configurable step_up_actions config table -- that table's enforcement path is TOTP-specific (is_elevated()/totp step-up), and reusing it for a different factor would conflate 'requires proof' with 'requires proof of THIS SPECIFIC factor', which the whole point of having two factors depends on keeping distinct.
- Gated only enroll_begin, not enroll_confirm, behind passkey reverification -- once a re-enrolment is legitimately started (begin succeeded), confirming it is just completing what was already authorized; mirrors TOTP's own two-step design, which doesn't re-check anything at confirm beyond the code itself.
- Reused auth_login.rs's load_credentials_for_user/persist_credential_use (made pub(crate)) rather than writing new copies for the reverify ceremony -- same query, same anti-cloning signature-counter persistence, no reason to duplicate.
- Traced several unexpected working-tree diffs (analyze.rs, auth_roles.rs, auth_user_role.rs, client_ops_qms_tags.rs, dedup.rs, export.rs, group_file_upload.rs) to leftover cargo-fmt reflow from M1 that never got committed at the time -- rustfmt produced a different (also valid) layout for several long with_owned_session/with_owned_session_mut call chains across separate invocations. Committed as its own zero-functional-change 'apply cargo fmt' commit rather than bundling into feature commits.


## Learned

- rustfmt is not perfectly idempotent across separate `cargo fmt --all` invocations for long method-chain-ending-in-closure expressions sitting near the line-width boundary (e.g. `state.store.with_owned_session_mut(id, owner, |session| {...})`) -- it can flip between 'each arg own line' and 'everything grouped' layouts run to run. Not a correctness issue (both are valid formattings and `--check` reports 0 diffs against whichever state is currently on disk), but it means a `cargo fmt --all` run's changes can't be assumed fully captured by an earlier commit's file list -- worth a `git status` sanity check for stray fmt-only diffs before starting a new batch of work, not just after.
- PostgreSQL's SECURITY DEFINER + DROP/CREATE FUNCTION pattern this project already established for resolve_session (touched 3 times now: elevated_until, permission_keys, passkey_reverified_until) is a clean, low-risk way to extend a session-resolution row -- CREATE OR REPLACE cannot change return type, so drop-and-recreate is the correct move each time, not a workaround.


## Verification

Backend: cargo test --workspace 583 passed/0 failed/1 ignored; cargo clippy --workspace --all-targets 0 warnings; cargo fmt --all -- --check 0 diffs; cargo audit clean. Frontend: tsc --noEmit clean; vitest run 43 files/304 tests passed (one earlier failure in an unrelated, untouched test file confirmed flaky on rerun). Both repos pushed to origin/main with clean working trees.



## Related

- [[2026-08-13-third-cto-grade-audit-auth-through-template-tagger]]
- [[2026-08-13-m1-fixes-committed-versioned-and-pushed-to-github-both-repos]]


_Recorded 2026-08-13T22:09:11.851Z from `bmaksimov` via the om MCP server (routing: caller)._
