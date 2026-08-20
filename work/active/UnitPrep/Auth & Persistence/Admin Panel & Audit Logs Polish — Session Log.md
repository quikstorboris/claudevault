---
date: 2026-08-05
description: "Event-log satellite for the admin-panel polish batch (reactivate-user, last-admin guard, dormant indicator, nav restriction) and audit-log steps 2-5 (cosmetics, lazy-load, CSV export, PDF export polish), verbatim, chronological."
tags: [work-note, unitprep, event-log]
status: active
quarter: Q3-2026
project: unitprep
---

# Admin Panel & Audit Logs Polish — Session Log

Event-log satellite for [[Auth & Persistence Index]] and [[Logging & Observability]]. Covers six first-hand build sessions from 2026-08-05 to 2026-08-06: the last-admin-guard/dormant-indicator/nav-restriction polish batch, the reactivate-user action, and audit-log steps 2 through 5 (cosmetics, lazy-load, CSV export, PDF export polish) of the six-step admin-panel plan Boris approved. Recovered from the vault's `inbox/` auto-filed notes 2026-08-10; moved here verbatim, nothing trimmed, in chronological order by each note's own `_Recorded ...Z_` timestamp.

## 2026-08-05 16:36 — Polish batch: last-admin guard, dormant indicator, admin-nav restriction; roles/compliance vaulted as ongoing efforts

Implemented the concrete, clearly-scoped items from a roles/permissions/compliance discussion: a last-remaining-admin guard on role changes and deactivation, a last-activity/dormant-account indicator on the admin Users table (no ESP exists, so in-app only), and frontend restriction of the Users/Audit Logs nav+routes to the admin role. Everything more open-ended (role philosophy, dual-approval for role changes, profile page, SOX/SOC2/CCPA framework, CI/CD, availability/recovery) was deliberately captured in two new ongoing vault notes rather than built, per Boris's explicit request to track permissions as its own ongoing effort.

**What changed**

- unitprep-api `src/api/auth_user_role.rs`, `auth_user_status.rs` — both refuse a change that would leave zero active admins (count remaining active admins excluding the target, refuse at 0); verified the exact count query against real dev data (returns 0 for the current single-admin state)
- unitprep-api `migrations/20260804190000_add_last_seen_at_to_list_users_for_admin.{up,down}.sql` — `auth.list_users_for_admin()` gains `last_seen_at` (MAX across `auth.sessions` per user), drop+recreate since the return shape changed
- unitprep-api `src/api/auth_users.rs` — `UserSummary`/query tuple threaded to include `last_seen_at`
- unitprep-ui `components/nav/LeftNav.tsx` — Users/Audit Logs nav items gain `adminOnly`, filtered by `user?.role`
- unitprep-ui `components/auth/RequireAdmin.tsx` (new) — route-level guard wrapping both admin pages, redirects a non-admin to `/clients` (UX only, backend already enforces this)
- unitprep-ui `lib/auth.ts` — `UserSummary.last_seen_at: string | null`
- unitprep-ui `app/(app)/admin/users/page.tsx` — Last active column, 90-day dormant threshold with an amber indicator, wrapped in `RequireAdmin`
- unitprep-ui `app/(app)/admin/audit-logs/page.tsx` — wrapped in `RequireAdmin`
- my-vault: two new notes under `work/active/UnitPrep/Auth & Persistence/` — "Roles & Permissions — Design Discussion" (ongoing, ordinary-priority effort) and "Compliance & Process Readiness" (deferred/preemptive bucket: SOX ITGC gap summary, CCPA/GDPR/GLBA/PCI/SOC2 assessed against UnitPrep's actual data profile, CI/CD and availability/recovery explained and deferred). Auth & Persistence Index updated to link both and mark the long-standing "raise least privilege at the right moment" item as raised.

**Decisions**

- Last-remaining-admin guard is scoped to what a single request can cause (count excludes the target, refuse at 0), not a general multi-step guarantee — two admins alternately demoting each other down to one is still possible, only the final self-target step is blocked. Judged proportionate: closing the single-request case is cheap and closes the `THREAT_MODEL.md`-named gap; the multi-step scenario needs a real second admin to even attempt, at which point the Roles & Permissions note's dual-approval discussion becomes relevant instead.
- Dormant-account "alert" built as an in-app indicator only, not a real notification — no ESP/webhook exists anywhere in this system (a standing, deliberate deferral), so a push alert has no infrastructure to ride on. Explicit tradeoff communicated to Boris rather than silently under-delivering on the word "alert."
- Access-review-report question answered by pointing at the existing admin Users table (already shows every user/role/status) rather than building a dedicated review workflow — the real gap was archivability (a point-in-time export as review evidence), not a missing view. A CSV export button was identified as the cheap next step but NOT built this session — named in conversation, not yet in the vault as a tracked item, since Boris didn't explicitly greenlight it.
- Roles/permissions philosophy (financial-data visibility, `onboarding_manager`'s own audit-log visibility, self-role-edit dual-approval) deliberately NOT resolved — captured as open questions in the new ongoing vault note per Boris's explicit instruction to treat this as its own gradual effort, not a one-shot decision.
- SOX/SOC2/CCPA/GLBA/PCI compliance-framework assessment and CI/CD/availability-recovery education given directly in conversation and archived to a second vault note, explicitly marked low-priority/preemptive per Boris's own framing — not scheduled as work.

**Learned**

- Given only one active admin exists in dev today, the last-remaining-admin guard's actual refusal branch (count reaching 0) could only be verified by running the exact SQL count query directly against real data (confirmed: returns 0 for the current admin, proving the guard would correctly fire) — the guard lives in the Rust handler layer, not in the SQL primitives themselves (mirroring how self-target refusal was already handled), so it can't be exercised by calling `auth.set_user_role` directly, and the existing lazy-pool unit tests can't reach real data to exercise it either. No test gap was introduced beyond what already existed for the self-refusal checks this mirrors.

**Verification**

Backend: `cargo test` 248/248 passing after both changes; migration applied cleanly to the Neon dev branch; the last-admin guard's count query and the extended `list_users_for_admin()` both verified directly against real dev data via psql (admin GUC set), confirming correct behavior against the actual single-admin state. Frontend: `tsc --noEmit` clean, eslint clean (one pre-existing unrelated warning), vitest 289/289 passing (2 new LeftNav tests covering admin-only nav visibility). Browser-verified against the real running dev server: navigating to `/admin/users` and `/admin/audit-logs` while signed out correctly chains through `RequireAdmin`'s redirect into the existing signed-out redirect, landing cleanly on `/login` with no console errors — confirms the new guard doesn't break the existing auth-gating flow. Did not verify the guard's behavior for a signed-in non-admin or a second-admin scenario, since no real passkey credential for a second account exists in this environment.

**Open**

- A CSV export button on the admin Users table (turns the existing live view into archivable access-review evidence) — named as the cheap next step for the access-review-report question, not yet built or vaulted as a tracked item. (Shipped later this session — see the 2026-08-05 22:00 entry below.)
- Everything in the two new vault notes: `onboarding_manager`'s actual permission set, admin's visibility into financial data (once financial data exists in this system), self-role-edit dual-approval / a future Manager role (explicitly trigger-gated on a second real admin existing), the profile-page idea (personal info/logs/avatars), SOX segregation-of-duties gap, change-management evidence (never assessed), Neon backup/PITR settings (a 10-minute check, not yet done), and CI/CD (explicitly deferred to another team).

**Related (as recorded)**

- Added role selection: invite-time role picker + standalone role-change action _(no note yet)_
- Shipped all six "approved, not yet built" auth backlog items _(no note yet)_
- [[Auth & Persistence Index]]
- [[Architecture]]

## 2026-08-05 20:56 — Built the reactivate-user action, the deliberately-deferred other half of disable-user

`recover_account` has, since 2026-08-03, explicitly refused a deactivated account with "reactivating an account is a separate decision from recovering a lost credential." Built that separate decision: a new `POST /auth/users/{id}/reactivate` endpoint (unitprep-api) and a Reactivate button on the admin Users page (unitprep-ui), both mirroring the existing deactivate/recover patterns exactly. First of six steps in a larger admin-panel plan (audit log PDF export, users CSV export, audit log cosmetics/lazy-load, roles follow-ups) that Boris approved and asked to execute one step at a time with a coherent commit per step.

**What changed**

- unitprep-api `src/api/auth_user_status.rs` — added `reactivate_user` handler: validates target status is exactly 'deactivated', flips it straight to 'invited' via the existing generic `auth.set_user_status` primitive (no intermediate deactivated step needed, unlike `recover_account`, since the revoke-all-access-paths trigger already fired when the account originally entered deactivated), inserts a fresh `user_invites` row, returns the raw token once via the reused `CreateInviteResponse` type.
- unitprep-api `src/auth/audit_log.rs` — added `USER_REACTIVATED` event constant, documented against `ACCOUNT_RECOVERY_INITIATED` to make the distinction explicit (recovery starts from active and passes through deactivated only as a mechanism; reactivation starts from deactivated and never re-enters it).
- unitprep-api `src/api/mod.rs` — registered `POST /auth/users/{id}/reactivate` next to the existing `/deactivate` route.
- unitprep-ui `lib/auth.ts` — added `reactivateUser(userId)`, same `AuthResult<InviteIssued>` shape as `recoverAccount`.
- unitprep-ui `app/(app)/admin/users/page.tsx` — added a Reactivate button for `status==="deactivated"` rows, same two-click confirm pattern as Disable, surfaces the returned invite link through the same `issued` banner used by create/reissue/recover.

**Decisions**

- Reactivate goes deactivated → invited, not deactivated → active — an account's credentials are already wiped by the time it's deactivated, so "active with zero passkeys" would be unable to sign in at all. Mirrors `recover_account`'s destination exactly.
- No intermediate pass through "deactivated" inside `reactivate_user` itself (unlike `recover_account`, which cycles active → deactivated → invited) — the revoke-all-access-paths trigger already fired once, at the original deactivation, so re-triggering it here would be redundant.
- Reused `CreateInviteResponse` (from `auth_invites.rs`) rather than defining a near-identical response type — same fields, same meaning (a freshly issued invite token, shown once).

**Learned**

- Backgrounding a dev server via `nohup cmd & disown` inside a `wsl.exe -d <distro> -- bash -lc '...'` invocation only survives if that specific tool call itself stays alive as a tracked background task (e.g. Claude Code's Bash tool with `run_in_background:true`) — a separate, later `wsl.exe` invocation checking on it finds nothing, and a `nohup ... &; disown; echo done` pattern where the *launching* call itself returns quickly also loses the child. What reliably works: give the tool's own `run_in_background` flag the literal foreground command (`exec next dev`), with no internal `&`/disown/setsid at all, and let the harness hold the process open.
- WSL's default PATH resolves `node`/`npm`/`npx` to the Windows-side install first (confirms an existing vault memory) — `npx tsc` failed with a cmd.exe/UNC-path error, and a plain `npm run dev` produced an empty log with no process at all. Fix: prepend the real WSL-native node bin dir (`$HOME/.nvm/versions/node/<version>/bin`) to PATH explicitly, or invoke `node_modules/.bin/<tool>` directly, bypassing the npm/npx wrapper entirely.

**Verification**

Backend: `cargo build`, `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check` (0 diffs in touched files; 6 pre-existing diffs elsewhere, unrelated), `cargo test --bin unitprep -- --test-threads=1` (250/250 passed including 2 new tests). Frontend: `tsc --noEmit` (0 errors), eslint on both changed files (0 issues), vitest run (288/289 passed; the 1 failure is a pre-existing, unrelated LeftNav branding-text test broken by an in-progress logo swap that predates this session and was left uncommitted by someone else). Live: both servers started against the real dev DB; `GET /health` and `/health/db` returned ok/`connected_as:app_service`; frontend correctly 307-redirects an unauthenticated visitor to `/login`. Full click-through of the new button itself not yet done — see Open.

**Open**

- The Reactivate button's actual click-through (deactivate a test user, reactivate them, confirm the invite link works, confirm redemption) still needs a real WebAuthn passkey login to reach the admin Users page — browser automation cannot satisfy an OS-level biometric/security-key prompt, so this one step needs Boris (or whoever holds a passkey on this dev environment) to do manually. Both dev servers are up right now (localhost:3000 UI, localhost:8080 API, against the real Neon dev branch) for exactly that purpose.
- Steps 2-6 of the approved plan (audit log cosmetics + lazy-load, users CSV export, audit log PDF export, roles/vault write-back) not started yet — proceeding one at a time per Boris's instruction, pending his confirmation this step is good.

**Related (as recorded)**

- [[Roles & Permissions — Design Discussion]]
- [[Auth & Persistence Index]]

## 2026-08-05 21:43 — Shipped Step 2: Audit Logs cosmetics — event multiselect, fuzzy user search, name resolution

Second of six steps in the approved admin-panel plan. Reworked the Audit Logs filter bar per Boris's cosmetic feedback: Event type is now a checkbox+search dropdown backed by a new canonical event-types endpoint, the User field is a fuzzy name/email/UUID autocomplete instead of a raw-UUID box, actor/target resolve to name+email above the UUID, and the Filter button was removed since every control already reloads dynamically. One real bug fixed along the way (clearing all events silently showed everything instead of nothing) and one design question resolved (drop the Filter button) via Boris's own live testing feedback.

**What changed**

- unitprep-api `src/auth/audit_log.rs` — added `event::ALL` (all 19 event-type constants) plus a no-duplicates test, so the frontend's canonical list can never hand-drift from what `audit_log::record()` actually writes.
- unitprep-api `src/api/auth_audit_logs.rs` — new admin-gated `GET /auth/audit-logs/event-types` returning `event::ALL`; extended the existing `event_type` query param to accept a comma-separated list (single value → `=`, multiple → `IN (...)`) instead of exactly one value, since the frontend filter became a multi-select.
- unitprep-api `src/api/mod.rs` — registered the new route.
- unitprep-ui `lib/auth.ts` — added `listAuditLogEventTypes()`.
- unitprep-ui `components/audit/EventTypeMultiSelect.tsx` (new) — checkbox-list-with-search dropdown, select-all/clear-all, closes on outside click. Built reusable on purpose — the planned audit-log PDF export page (a later step) needs the identical control.
- unitprep-ui `app/(app)/admin/audit-logs/page.tsx` — swapped the Event type text input for `EventTypeMultiSelect`; replaced the User ID text input with a fuzzy autocomplete (matches name/email/UUID substring against the already-loaded Users list, clear button, dropdown of matches) while still accepting a directly-pasted UUID; actor/target cells now show resolved name+email above the UUID (client-side join against `GET /auth/users`, no backend change); removed the Filter button and its `<form>` entirely.

**Decisions**

- Zero events selected must mean "show nothing," handled client-side (short-circuit before calling the API) rather than server-side — an omitted `event_type` param and an empty one are indistinguishable to the backend (both read as "no filter"), so there's no clean way to express "match nothing" by what's sent; the omission-means-no-filter convention already existed and was worth keeping rather than inventing a sentinel value.
- Comma-separated single string param for multi-value `event_type`, not repeated query keys (`event_type=a&event_type=b`) — axum's `Query` extractor (serde_urlencoded) has no reliable support for collecting repeated keys into a `Vec`, so comma-splitting a single string sidesteps that pitfall entirely.
- User field became fuzzy-autocomplete-with-directly-pasted-UUID-fallback rather than either a pure free-text box or a full multi-select — multi-select-with-chips was explicitly scoped to the later PDF-export filters page (a bigger, different UI); this inline filter only ever needed to find and apply one person at a time, so a single-select autocomplete was the right-sized fix for what was actually broken (fuzzy matching didn't exist — the box only ever supported exact UUID equality).
- Removed the Filter button rather than keeping it as a no-op affordance — confirmed via reading the existing effect chain that `loadFirstPage` already re-runs on every filter-state change (its `useCallback` dependency chain terminates in the filter state itself), so the button was doing nothing a plain control edit hadn't already done. Boris asked for an opinion on this specifically and this was it, confirmed correct by his own testing.

**Learned**

- A cosmetic ask ("make these two boxes the same size, is a dropdown a good idea") surfaced a real correctness bug once actually used (clear-all showing everything) that no amount of code review would have caught, because the bug only exists at the intersection of two states (backend's "omitted == unfiltered" convention + frontend's "selected some" vs "selected none" distinction) that isn't visible from either side's code alone. Worth remembering: multi-select filter UIs need an explicit test/thought for the empty-selection case, since it's the one state most filter backends can't represent by what's absent from the request.
- Backgrounding a WSL dev server via nohup/disown/setsid from a Bash tool call is unreliable across separate tool invocations regardless of technique — confirmed again this session. What actually works: pass the literal foreground command (no internal `&` at all) to a single Bash call with `run_in_background:true`, and let the harness hold that process open. Mixing internal backgrounding with the tool's own `run_in_background` caused a silent, un-logged process death more than once.

**Verification**

Backend: `cargo build`, `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check` (0 diffs in touched files), `cargo test --bin unitprep -- --test-threads=1` (254/254, including 4 new tests). Frontend: `tsc --noEmit` (0 errors), eslint (0 issues), vitest run (288/289 — the 1 failure is the same pre-existing, unrelated LeftNav branding-text test from a prior uncommitted logo swap, unchanged from before this step). Live: Boris tested against a real running dev server pair and reported three issues (clear-all bug, unfriendly/broken user field, unnecessary Filter button), all three fixed and re-verified live by Boris, who then confirmed "all is fixed."

**Open**

- Steps 3-6 of the approved plan not started: audit log lazy-load (replace Load More with IntersectionObserver), Users CSV export (compile-enforced auto column sync via exhaustive struct destructuring), the audit-log PDF export (the big remaining feature — `EventTypeMultiSelect` built this step is meant to be reused there), and the roles/compliance vault write-back.
- Both repos' working trees still carry the same pre-existing, unrelated, uncommitted logo/favicon/layout-rebrand changes (`app/layout.tsx`, `components/nav/LeftNav.tsx`, `public/favicon.svg`, `public/orchestrator-logo-dark.svg`, plus untracked `.claude/`, `assets/`, `README.sample.md`) that predate this session — deliberately left alone and excluded from every commit made this session and last. Someone should eventually commit or discard those; not this session's call to make.

**Related (as recorded)**

- [[Roles & Permissions — Design Discussion]]
- [[Auth & Persistence Index]]

## 2026-08-05 21:48 — Shipped Step 3: Audit Logs lazy-load via IntersectionObserver

Third of six steps in the approved admin-panel plan. Replaced the Audit Logs page's "Load more" button with scroll-triggered pagination, keeping the existing keyset (`before_id`) pagination model unchanged — only the trigger moved from a click to an IntersectionObserver on a sentinel at the list's end.

**What changed**

- unitprep-ui `app/(app)/admin/audit-logs/page.tsx` — `loadMore` converted to `useCallback`; new `sentinelRef` + IntersectionObserver effect (200px `rootMargin`, recreated when exhausted/loadingMore/loadMore change) calls `loadMore()` when the sentinel nears the viewport; removed the Load more button, added an "End of results" message when exhausted and a lightweight "Loading..." text while a page is in flight.

**Decisions**

- Kept the button's identical keyset pagination (`before_id`, `PAGE_SIZE=50`) — only the trigger mechanism changed, not the pagination model. No reason to touch a working, already-correct backend contract for a purely frontend UX change.
- Let `loadMore`'s `useCallback` identity change on every entries update (it closes over `entries` to read the last id) and simply let the observer effect recreate the IntersectionObserver each time, rather than threading a ref through to avoid that — cheap to tear down/reconnect at this list's scale, and simpler than the alternative.

**Verification**

`tsc --noEmit` (0 errors), eslint (0 issues), vitest run (288/289 — same pre-existing unrelated LeftNav failure as every prior step this session). Boris tested live against his own running dev server (frontend hot-reloaded via Turbopack, no restart needed since this was frontend-only) and confirmed "works fine."

**Related (as recorded)**

- [[Auth & Persistence Index]]

## 2026-08-05 22:00 — Shipped Step 4: Users CSV export

Fourth of six steps in the approved admin-panel plan. Added a CSV export of the admin Users list, admin-gated, sharing the exact same query as the JSON listing so the two views of "who are the users" can't diverge. The interesting part is how the "keep the CSV in sync when columns change" ask got solved: not a vault reminder (forgettable) but an exhaustive struct destructure with no `..`, making a forgotten column a compile error.

**What changed**

- unitprep-api `src/api/auth_users.rs` — extracted `fetch_users_for_admin()` (shared by `list_users` and the new `export_users`) so the JSON listing and CSV export read from one query, not two independently-maintained copies; added `USER_CSV_HEADER`, `user_csv_record()` (exhaustive `UserSummary` destructure, no `..`), and `export_users` handler (admin-gated, CSV via the shared `write_csv`, filename `unitprep-users-YYYY-MM-DD.csv`).
- unitprep-api `src/infrastructure/csv_export.rs` — `write_csv` (header+rows → CSV bytes) changed from private to `pub(crate)` so `auth_users.rs` can reuse it instead of writing a second copy of the same `csv::Writer` boilerplate.
- unitprep-api `src/api/mod.rs` — registered `GET /auth/users/export`.
- unitprep-ui `lib/auth.ts` — added `exportUsersCsv()` and `ExportUsersResult`, mirroring `AuthResult`'s shape but keeping the raw `Response` (not parsed as JSON) since the caller reads it as a blob.
- unitprep-ui `app/(app)/admin/users/page.tsx` — Export CSV button next to Invite a user, downloads via the existing `downloadBlob` helper (same one the tool export buttons use).

**Decisions**

- Compile-enforced column sync via exhaustive struct destructuring (`let UserSummary { id, email, ... } = user;` with no `..`) rather than a vault reminder to update the export when columns change — a reminder can be forgotten or skipped under time pressure; a missing field in an exhaustive destructure is a compile error, full stop. Costs nothing extra to write this way once you know the pattern.
- Factored the JSON-listing and CSV-export queries into one shared `fetch_users_for_admin()` rather than each handler running its own copy of the same 12-column SELECT — the whole point of the compile-enforced column sync is undermined if the query itself could drift between the two call sites even while each one's own mapping stays internally consistent.
- Raw ISO 8601 (`to_rfc3339()`) for `created_at`/`last_seen_at` in the CSV, not the on-screen "Last active: 3 days ago" formatted string — a data export is for further processing/analysis, where a parseable timestamp is more useful than a human-relative one; the on-screen page still shows the friendly format, this just doesn't duplicate that choice into the export.
- CSV-injection sanitization (`sanitize_cell`) applied to every text field even though this data is admin-entered, not facility-file-derived like the dedup/unit-group exports that guard already existed for — an admin-entered `first_name`/`job_title` starting with `=` is just as capable of becoming a live formula in Excel as facility data would be; the guard doesn't care about provenance.

**Verification**

Backend: `cargo build`, `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check` (0 diffs in touched files), `cargo test --bin unitprep -- --test-threads=1` (257/257, including 3 new tests: role-gating, and two tests on `user_csv_record` itself — column-for-column content match against a real `UserSummary`, and CSV-injection sanitization on name/job-title fields). Frontend: `tsc --noEmit` (0 errors), eslint (0 issues), vitest run (288/289 — same pre-existing unrelated LeftNav failure as every prior step). Live: backend restarted against Boris's own running dev server pair to pick up the new route (confirmed 401 unauthenticated), Boris tested the actual Export CSV button end-to-end and confirmed "works fine."

**Related (as recorded)**

- [[Auth & Persistence Index]]

## 2026-08-06 16:14 — Step 5 polish: Audit Log PDF export — Details wrapping, column rebalance, keyboard nav, commits

Closed out the multi-round polish pass on the audit-log PDF export (Step 5 of the admin-panel plan): wrapped the Details column instead of hard-truncating it, reclaimed dead Actor/Target/IP width by narrowing/repositioning columns, and added keyboard navigation (arrows + Enter) to both audit-log dropdown filters. Verified via full test suite, clippy, fmt, ESLint, tsc, and a visual re-render of the sample PDF (sent to Boris) before committing.

**What changed**

- unitprep-api `src/infrastructure/audit_log_pdf.rs` — added `wrap_lines()` (greedy word-wrap with truncation-marking), `row_height_mm()` (variable row height from wrapped line count), replaced fixed-capacity `rows_per_page()` with greedy-packing `paginate_rows()` that always makes progress even over budget; rebalanced `COLUMNS` (Actor/Target narrowed 23→16 chars, IP moved left next to Target, Details widened 35→50 chars as a per-line budget, `DETAILS_MAX_WRAP_LINES=3`)
- unitprep-ui `components/audit/UserMultiSelect.tsx` (new) — fuzzy-search-to-chips multi-select with keyboard nav (ArrowUp/Down/Enter/Escape) via a `highlightedIndex` over a discriminated `DropdownItem` union (resolved users + raw-UUID-paste option); shared by the export page and the upgraded main Audit Logs page
- unitprep-ui `components/audit/EventTypeMultiSelect.tsx` — added the same keyboard nav pattern; Enter *toggles* (checkbox semantics) rather than select-and-close, unlike `UserMultiSelect`'s pick-one semantics
- unitprep-ui `app/(app)/admin/audit-logs/export/page.tsx` (new) — export filters page: date range, `EventTypeMultiSelect`, `UserMultiSelect`, IP input, live debounced preview, Export PDF buttons top+bottom
- unitprep-ui `app/(app)/admin/audit-logs/page.tsx` — upgraded main page's User filter from single-select autocomplete to `UserMultiSelect`; added an Export link to the new export page
- unitprep-api `src/api/auth_audit_logs.rs` — `format_generated_at()` adds a DST-aware Pacific-time parenthetical via `chrono-tz` alongside UTC; `summarize_details()` uses "->" not "→" (WinAnsi encoding gap); `user_id` validation moved before `begin_rls_transaction`

**Decisions**

- Wrapping Details (up to 3 lines, variable row height) over hard truncation: endorsed as the right call for a formal report once the user raised it — truncated security-log details are a worse tradeoff than variable-height rows.
- Reclaimed Actor/Target/IP dead space for Details rather than leaving the layout as-is: those columns were sized for content that never reaches that width; moving IP next to Target and giving the freed width to Details was a straightforward win, not a hard tradeoff.
- Split the frontend polish into 2 commits, not the originally planned 3: the Export-link addition and the main-page multi-select upgrade landed in the same `page.tsx` diff in a way that wasn't cleanly hunk-splittable non-interactively, so they were committed together rather than forcing an artificial split.
- Left 6 pre-existing unrelated backend fmt diffs (`auth_user_role.rs`, `session_cookie.rs` x2, `step_up_policy.rs`, `totp.rs` x2) and unrelated frontend changes (`app/layout.tsx`, `components/nav/LeftNav.tsx`, favicon/logo assets, `.claude/`) untouched in both repos — not part of this work, not staged or committed.

**Learned**

- printpdf's `Op::SetTextCursor` compiles to PDF's relative `Td` operator despite the field being named `pos: Point` — use `Op::SetTextMatrix{TextMatrix::Translate}` for genuinely absolute positioning. Root-caused by reading printpdf's `serialize.rs` directly rather than guessing.
- The 14 standard PDF fonts render via WinAnsiEncoding/CP1252, not Unicode — arrows (→, U+2192) silently render as "?" with no error, while em dash and ellipsis happen to be in CP1252 and work fine. Caught only by visually re-reading a rendered PDF, not by any build/test signal.
- chrono has no timezone database; chrono-tz (a light dependency, just phf/siphasher for IANA lookup tables) is needed for real DST-aware conversions like `America::Los_Angeles`.
- A test fixture's magic-number assumptions rot silently when a constant it depends on changes: `row_height_grows_for_wrapped_details` asserted `line_count > 1` using a fixed sentence that fit on one line once the Details per-line budget widened from 35→50 chars. Caught by the test suite, not by review.

**Verification**

Backend: `cargo build` clean, `cargo clippy --all-targets -- -D warnings` clean, `cargo fmt --check` clean (only 6 pre-existing unrelated diffs in other files), full `cargo test --bin unitprep -- --test-threads=1`: 294 passed / 0 failed / 1 ignored. Regenerated the `#[ignore]`'d sample-PDF test with an injected long-Details row and visually re-read the rendered PDF via the Read tool: Details wraps to 3 lines with a trailing ellipsis, only that row's height grows, pagination has no overlap, IP sits next to Target. Sent the PDF to Boris directly for his own visual confirmation before committing. Frontend: ESLint clean on the changed audit-log files, `tsc --noEmit` clean across the whole project.

**Related (as recorded)**

- [[Session 2026-07-29 — Auth Tasks 4, 5, 8 and Infrastructure Fixes]]
- [[Phase 2 Progress]]

## Related

- [[Auth & Persistence Index]] — admin-panel status this satellite provides first-hand detail for
- [[Logging & Observability]] — audit-log assessment/roadmap these audit-log steps build on
- [[Roles & Permissions — Design Discussion]]
- [[Roles & Permissions — Design Finalization Log]], [[Roles & Permissions — Backend Build Log]], [[Roles & Permissions — Frontend Build & Ship Log]] — the build phase of the roles/permissions effort this polish batch's vaulted design discussion led into
