---
date: 2026-08-13
description: "Consolidated handoff for a fresh session picking up this work: the third CTO-grade audit (report: https://claude.ai/code/artifact/b6f97ff5-f573-4c25-9"
tags:
  - project-note
source_repo: bmaksimov
---

# Third Audit + Fix Plan — Full Session Handoff (M1-M2 done, M3 in progress)

Consolidated handoff for a fresh session picking up this work: the third CTO-grade audit (report: https://claude.ai/code/artifact/b6f97ff5-f573-4c25-99b0-646b2e3b2c01) found 7 High/20 Medium/21 Low findings across auth, the new Template Tagger, and the original engine. A sequenced fix plan (C:\Users\bmaksimov\.claude\plans\polished-crunching-hopcroft.md, 8 milestones ordered by risk) is underway: M1 and M2 are fully shipped and pushed; M3 is 2/3 done. unitprep-api is at v1.8.2, unitprep-ui at v1.5.1, both origin/main clean.

## What changed

- M1 (unitprep-api v1.8.0->v1.8.1): fixed the session-ownership IDOR (every session-touching handler across unit-group/dedup/tagger stores now uses with_owned_session/_mut, not the unowned variant -- including tagger.rs's report/apply, which the original audit's agent-scoping had missed entirely); bumped docx-surgeon's quick-xml 0.36->0.41 for 2 RustSec CVEs (required rewriting <w:t> text extraction into a loop, since 0.41 splits XML entities out of Event::Text into a new Event::GeneralRef that 0.36 didn't have); fixed a real concurrency race in the last-active-admin guard (a plain FOR UPDATE would NOT have worked -- Postgres rejects FOR UPDATE on aggregate queries outright, and even reshaped, it doesn't stop two txns each removing a DIFFERENT admin; the real fix locks the shared auth.roles 'admin' row itself); fixed an unrelated pre-existing bug in auth_configuration.rs (step_up_actions read/written as a Postgres array when the column is actually JSON)
- M1 (unitprep-ui v1.4.0->v1.5.0): fixed the AppLayout admin-redirect race (missing `!checked` branch let RequirePermission mount with user=null on every fresh load, silently bouncing legitimate admins); added a favicon; added the orchestrator-logo-dark.svg asset LeftNav.tsx had referenced since the Orchestrator rename but was never actually committed (a real broken-image bug found while triaging uncommitted files); fixed stale 'Preserve underscores' checkbox copy
- M2 (unitprep-api v1.8.1->v1.8.2): create_invite now requires users.manage_roles in addition to users.manage (closes a latent privilege-escalation seam); added a passkey-based step-up (NEW auth_passkey_reverify.rs + migration 20260813150000, auth.sessions.passkey_reverified_until + auth.record_passkey_reverify, modeled directly on TOTP's own elevated_until/record_step_up) gating self-service TOTP re-enrolment -- Boris's own design call after clarifying admin-driven onboarding TOTP setup was never the gap; fixed a real lockout gap in enroll_confirm (wrong-code branch never checked the lock or recorded failures, unlike step_up's identical branch)
- M2 (unitprep-ui v1.5.0->v1.5.1): MasterGroupFileSection's manual upload now treats 401 the same as 404 (session-expired) -- was live-reachable now that passkey auth has shipped; added passkeyReverify() to lib/auth.ts + account page UI gating TOTP re-enrolment behind it
- M3 in progress: added cross-owner session-access regression tests for dedup and tagger sessions (unit-group's equivalent was added during M1); added an #[ignore]'d integration test (authenticated_user.rs::query_sessions_own_sql_is_valid_against_the_real_schema) proving query_session's SQL is valid against the REAL migrated schema -- running it immediately found a second live instance of the exact incident-class bug this test exists to prevent: the M2 passkey_reverify migration had never actually been applied to the dev database, so the just-shipped passkey step-up feature was silently broken in practice. Applied the pending migration (sqlx migrate run against NEON_DEV_DATABASE_URL_DIRECT, the owner connection) to fix it -- confirmed via `sqlx migrate info` that this was the only pending migration and it now shows installed.


## Decisions

- Ran the 6 original audit review agents as static-read-only (no cargo/npm commands), then did ONE centralized build/lint/dependency verification pass myself afterward -- this machine's documented RAM ceiling made 6 concurrent Rust/Next builds a real freeze risk; sequential verification throughout this whole session (never ran cargo test/clippy/fmt from multiple agents or in parallel with frontend checks).
- Independently re-read the two highest-severity audit claims (IDOR, frontend auth race) against live code before trusting them, matching the prior two audits' own discipline of not just trusting agent output.
- Sequenced the fix plan strictly by security/integrity risk per Boris's explicit ask, not by area -- M1 = live unexploited gaps with no design ambiguity, M2 = security items needing a human confirmation first, M3 = regression tests locking in M1/M2, M4 = dependency/process hygiene, M5-M8 = quality work with no security stakes.
- For TOTP re-enrolment, built a bespoke passkey-reverify mechanism (new column/endpoint pair) rather than reusing the existing admin-configurable step_up_actions table -- that table's enforcement path is TOTP-specific; reusing it for a different factor would conflate 'requires proof' with 'requires proof of THIS factor', defeating the point of having two distinct factors.
- Organized all uncommitted work (both this session's fixes AND several pre-existing uncommitted changes from before the session started) into coherent per-fix commits rather than one dump, matching this codebase's own commit-message conventions exactly (learned from git log, not assumed).
- Committed the ignored real-DB integration test even though neither repo has CI to run it automatically -- it's still strictly better than the status quo (auth_totp.rs/auth_invites.rs's existing comments describe this whole class of gap as 'exercised against the real dev database' meaning purely manual curl checks, not anything runnable/repeatable).


## Learned

- quick-xml 0.36->0.41 is not a drop-in security patch for any consumer reading text content directly -- 0.41 added Event::GeneralRef as a distinct event, splitting what used to be one Event::Text ('Smith &amp; Sons') into Text/GeneralRef/Text. Code that reads 'exactly one event after a text element's start tag' will silently truncate any text containing an entity.
- PostgreSQL flatly rejects FOR UPDATE on any query containing an aggregate function -- and even restructured to avoid that, locking the COUNTED rows doesn't stop a last-admin race, since two txns each excluding a DIFFERENT admin never lock the same row. The fix has to lock a resource BOTH txns touch regardless of target (here: the shared auth.roles 'admin' row).
- This session's own 6-agent audit review, split by feature area (API/infra vs template-tagger vs auth), left a real IDOR instance (tagger.rs) unreviewed by anyone for the ownership pattern specifically -- a cross-cutting security pattern doesn't respect the area boundaries a code-quality-focused split draws. Worth a dedicated cross-cutting grep sweep for 'is this pattern applied everywhere', not just parallel per-area review, on any future audit.
- rustfmt is not perfectly idempotent across separate `cargo fmt --all` invocations for long method-chain-ending-in-closure expressions near the line-width boundary (e.g. `state.store.with_owned_session_mut(id, owner, |session| {...})`) -- can flip between two valid layouts run to run. Not a correctness issue, but means a fmt run's changes can't be assumed fully captured by an earlier commit -- worth a `git status` sanity check for stray fmt-only diffs before starting new work.
- A migration being committed to the repo does NOT mean it's been applied to the real dev database -- these are two entirely separate steps (`sqlx migrate run` against the owner/direct connection, not the pooled app_service one used for DATABASE_URL day-to-day). This session's own M2 work proved this gap exists in practice, not just in theory: the passkey_reverify migration sat committed-but-unapplied through several rounds of 'all tests pass' verification, because nothing in the fast offline test suite touches a real database at all. `sqlx migrate info` (with the owner connection) is the way to check this directly.
- Real DB credentials live in unitprep-api's .env.local (NEON_DEV_DATABASE_URL / _DIRECT / _APP variants for dev, NEON_PROD_* for prod, plus DATABASE_URL = the app_service pooled connection used day-to-day and TOTP_ENCRYPTION_KEY). _DIRECT is the non-pooled owner connection, correct for schema migrations; the pooled owner one likely also works but DIRECT avoids any PgBouncer transaction-mode DDL surprises. Treat this file's contents as sensitive -- avoid echoing values into shell output or logs when working with it.


## Verification

Backend (unitprep-api): cargo test --workspace 585 passed/0 failed/2 ignored (including the new real-DB test, run separately with --ignored and confirmed passing against the corrected schema); cargo clippy --workspace --all-targets 0 warnings; cargo fmt --all -- --check 0 diffs; cargo audit clean; sqlx migrate info confirms every migration installed, none pending. Frontend (unitprep-ui): tsc --noEmit clean; vitest run 43 files/304 tests passed. Both repos pushed to origin/main, working trees clean.


## Open

- M3 remaining item: a concurrency-shaped test for the admin-guard fix (auth_user_role.rs/auth_user_status.rs's remaining_active_admins_excluding) if practical against the current test harness -- otherwise explicitly document why the FOR UPDATE-on-the-shared-role-row fix is accepted as a DB-level guarantee without an application-level concurrency test. Not yet started.
- M4 (not started): npm audit fix (no --force) for brace-expansion/js-yaml/nanoid; redo the Next.js CVE reachability assessment from scratch -- 2 of the 6 factors the LAST audit used to rule out exposure are now false (proxy.ts is Next 16's renamed middleware; next/image is now used in TotpEnrollForm.tsx/LeftNav.tsx).
- M5 (not started, DRY consolidation): shared multipart-upload hook (closes the 401-handling duplication across 4 call sites at once); request_context() helper for repeated (user_agent, ip_address) extraction across ~13 admin handlers; shared audit-log filter-building helpers; shared tx+audit helper in client_ops_qms_tags.rs; comparison.rs/phrasing.rs shared blank-sort helper (dedup crate); session_lifetime_hours() dedup between auth_login.rs/auth_register.rs; useAuditLogFilterData() shared hook; surface TaggerResultsPage.tsx's silently-swallowed tag-fetch failure.
- M6 (not started, file splits): docx-surgeon/edit.rs, api/mod.rs, infrastructure/audit_log_pdf.rs, auth_audit_logs.rs, resolve_unit_format.rs, dedup/relatedness.rs, lib/auth.ts, admin/users/page.tsx, MasterGroupFileSection.tsx, WarningsSection.tsx -- full file-by-file breakdown is in the plan file.
- M7 (not started, test-coverage debt beyond M3's incident-linked gaps): Template Tagger UI test suite (useTaggerReport/useTaggerApply/TagPicker); dedup/ingest.rs round-trip + missing-FirtLast tests; tagger.rs::check direct test.
- M8 (not started, low-severity polish): ~12 small items, full list in the plan file (stale doc comment, closure shadowing, RowScan clone perf, dedup.rs re-clone perf, duplicated button, error-message consistency, naming drift, schema-ahead-of-code comment, timing side-channel note, missing ConnectInfo, spawn_blocking boundary check, missing name/email in nav).
- Full milestone detail (exact files, exact reasoning per item) lives in the plan file: C:\Users\bmaksimov\.claude\plans\polished-crunching-hopcroft.md -- read this first when resuming, it was kept accurate as milestones completed.
- Current versions: unitprep-api v1.8.2, unitprep-ui v1.5.1. Both repos' working trees are clean and origin/main is up to date as of this note.


## Related

- [[2026-08-13-third-cto-grade-audit-auth-through-template-tagger]]
- [[2026-08-13-milestone-1-shipped-closed-the-4-highest-risk-findings-from]]
- [[2026-08-13-m1-fixes-committed-versioned-and-pushed-to-github-both-repos]]
- [[2026-08-13-milestone-2-shipped-invite-role-gate-totp-lockout-passkey-st]]
- [[2026-08-13-cross-owner-idor-regression-tests-extended-to-dedup-and-tagg]]


_Recorded 2026-08-13T22:29:55.117Z from `bmaksimov` via the om MCP server (routing: caller)._
