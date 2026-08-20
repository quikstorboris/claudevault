---
date: 2026-08-14
description: "Milestone 6 (modularity/file splits) shipped across both repos -- unitprep-api v1.8.4, unitprep-ui v1.5.5. 6 backend files and 4 frontend files split along genuine seams."
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 6 shipped — unitprep-api v1.8.4, unitprep-ui v1.5.5

Split 10 large files (6 backend, 4 frontend) per the CTO-grade audit's milestone 6 (modularity), following [[2026-08-14-milestone-5-dry-consolidation-shipped|Milestone 5]]. Both halves were delegated to a subagent, each reading every target file fully first and adjusting the plan where the real structure differed from the audit's original guidance -- none of the 10 splits were purely mechanical chops. Every split preserved its existing tests untouched or moved them alongside the code they test; none were deleted or weakened. The main session independently re-verified full build/lint/test suites on both repos before committing and organized the diffs into 8 coherent commits total (5 backend, 3 frontend) rather than one per file, where a real cross-file dependency forced two splits to land together.

## Backend — unitprep-api v1.8.4 (5 commits)

- `docx-surgeon/src/edit.rs` (665 non-test lines) → `edit/{mod,fragment,run_xml,overlap}.rs`: fragment/splice computation, XML rebuilding, and overlap validation were three genuinely separate concerns; `mod.rs` kept the public API and all existing tests unmoved since they exercise that API directly.
- `src/api/mod.rs` (858 lines) + `src/api/auth_audit_logs.rs` (1175 lines) split together in one commit, because `router.rs`'s route table directly references the new `auth_audit_logs_export` module — the two splits weren't independently committable. Produced `state.rs`, `router.rs`, `health.rs`, and `auth_audit_logs_export.rs` (PDF-export/preview, split from the listing/query logic that stayed put); `mod.rs` kept the module registry and shared response helpers (including M5's `request_context`/`user_agent_from`).
- `src/api/resolve_unit_format.rs` (415 lines) → moved `resolve_confirm_action`/`validate_manual_mapping` into `discover/format_resolution.rs`, alongside the rest of the `discover` module's own earlier split (they build directly on `discover::format_helpers`).
- `src/infrastructure/audit_log_pdf.rs` (794 lines) → `layout.rs` (page/column/wrapping math) + `render.rs` (PDF op emission).
- `dedup/src/relatedness.rs` (444 lines) → `relatedness/household.rs` (the union-find grouping algorithm, a self-contained concept distinct from note composition and per-signal evidence gathering).

Verified: `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets`, `cargo test --workspace` all clean at the final state — 546 tests, 0 failed, 3 ignored (expected: 2 need a real Postgres, 1 is a manual-inspection PDF writer).

## Frontend — unitprep-ui v1.5.5 (3 commits)

- lib/auth.ts (694 lines) deleted, replaced by lib/auth-shared.ts (118 lines: authFetch/tryAuthFetch/parseAuthResult/AuthResult/Role/FileDownloadResult/fetchForDownload -- the plumbing all four other files need), lib/auth-session.ts (308 lines: WhoAmI/hasPermission/whoAmI/passkey register+login+reverify/TOTP/logout), lib/auth-users.ts (152 lines: UserSummary/listUsers/exportUsersCsv/VALID_COMPANIES/roles/invites/disable/reactivate/grantRole/revokeRole), lib/auth-audit.ts (113 lines: audit log list/event-types/export/preview), lib/auth-config.ts (36 lines: KNOWN_STEP_UP_ACTIONS/AuthConfiguration get+update). Role type re-exported from both auth-session.ts and auth-users.ts since both need it.
- Updated all 13 files across app/ and components/ that imported from '@/lib/auth' to import from the correct new module(s) instead -- two of them (lib/useAuditLogFilterData.ts, app/(app)/admin/audit-logs/page.tsx) needed splitting into two import statements since they crossed the users/audit boundary. Updated the one test that mocked '@/lib/auth' directly (app/(app)/account/page.test.tsx) to mock '@/lib/auth-session'.
- app/(app)/admin/users/page.tsx (805 lines) split into page.tsx (172 lines, composition only), InviteUserForm.tsx (182 lines, owns its own field/submit/error state), UserRow.tsx (358 lines, owns its own confirm-toggle and role-picker state per row instead of the parent tracking maps keyed by user id), useUsersAdmin.ts (240 lines, all data-fetching/mutations), and a small styles.ts (20 lines) for the shared Tailwind class constants all three now need -- mirrors an existing precedent already in this codebase at app/(app)/admin/client-ops/qms-tags/. No pre-existing test file existed for this page, so there was no test-preservation constraint here.
- components/discovery/MasterGroupFileSection.tsx (355 -> 208 lines) had its manual-upload flow (hidden file input ref, the useFileUploadAction wiring, the change handler that builds FormData and forwards the result) pulled into components/discovery/useManualGroupFileUpload.ts (70 lines); confirm/select-candidate logic stayed in the component since only the manual-upload path was asked for. MasterGroupFileSection.test.tsx needed no changes -- it only exercises the component's public props/DOM.
- components/scan-results/WarningsSection.tsx (378 -> 75 lines) had its per-reason-card JSX (the issue list, Groups Needing Review section, exclude-all/import-as-is actions, excluded/acknowledged lists) extracted into WarningReasonCard.tsx (196 lines). WarningsSection.test.tsx needed no changes for the same reason as above.


## Decisions

- Same cross-file-dependency constraint hit on both repos: whenever a split's new module is referenced by another file that's ALSO being split (backend: `router.rs` referencing the new `auth_audit_logs_export`; frontend: `admin/users/page.tsx` importing from the new `lib/auth-*.ts` files), the two splits were bundled into one commit rather than forced apart, since an isolated intermediate commit would reference a module that doesn't exist yet in that commit's tree. Confirmed by checking actual cross-references (`grep`) before deciding commit boundaries, not by assumption.
- Deleted lib/auth.ts outright rather than keeping it as a re-export barrel: only 13 importers existed, so updating each was cheap, and a barrel would have papered over what's supposed to be a real modularity split.
- For admin/users, kept pendingUserId centralized in the hook (disables that row's own buttons while a request is in flight) but moved every 'confirming/adding X for user id' map into UserRow as local booleans -- matches the task's explicit ask ('owning its own confirm/role-picker state') without also moving the pending-request tracking, which still needs to be visible across the whole row set.
- In UserRow, wrapped the hook's async mutation calls (recover/disable/reactivate/grantRole) in small local handlers that await the call and then reset the row's own confirm/picker boolean -- this reproduces the exact original timing (confirmation UI stays visible with a '...ing' label until the request settles) without the parent needing to know about row-local UI state at all.
- In InviteUserForm, replaced a would-be 'sync role default from availableRoles' useEffect with a derived value (`role || availableRoles?.[0]?.key || ""`) instead -- an effect calling setState synchronously from its own body is exactly what this repo's `react-hooks/set-state-in-effect` ESLint rule flags (caught by the final eslint run), and a derived value was strictly simpler anyway.
- Added a small per-directory styles.ts for admin/users' shared Tailwind class constants (primaryButtonClass, dangerButtonClass, etc.) since three new files needed them -- mirrors the existing app/(app)/admin/client-ops/qms-tags/styles.ts precedent already in the codebase rather than inventing a new pattern.


## Learned

- This repo already has a working precedent for exactly this kind of split: app/(app)/admin/client-ops/qms-tags/ co-locates CreateTagForm.tsx, TagRow.tsx, TagFilters.tsx, and styles.ts next to its page.tsx. Worth checking for existing sibling patterns before inventing file layout for a new split -- it settled several naming/placement questions immediately.
- The `react-hooks/set-state-in-effect` ESLint rule in this codebase will flag a useEffect that calls setState directly from a prop-driven default-value calculation, not just the async-then-setState case the codebase already had commentary about (TotpEnrollForm's queueMicrotask workaround). When splitting a component and a 'sync this state from a prop once it loads' effect shows up, check first whether a derived value read at point of use avoids needing the effect at all.


## Verification

Ran `npx tsc --noEmit` after each of the 4 splits individually (all clean). After all 4: `npx eslint .` (0 errors -- 1 pre-existing unrelated warning in coverage/block-navigation.js, a generated file) and `npx vitest run` (46 test files, 330 tests, all passing, 0 skipped/modified). No tests were deleted or weakened.



## Related

- [[2026-08-14-milestone-5-dry-consolidation-shipped|Milestone 5]]
- [[2026-08-14-milestone-7-test-coverage-debt-shipped|Milestone 7]]
- [[Patterns]]
- [[Gotchas]]

_Recorded 2026-08-14 from `bmaksimov`._
