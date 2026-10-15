---
date: 2026-10-14
description: "First full audit of UnitPrep's automated tests: measured coverage of both repos, a risk map of thin spots, and a prioritized plan. Coverage is a map, not a target (Boris: 90% would be nice but is not the goal)."
project: UnitPrep
status: active
quarter: Q4-2026
tags:
  - work-note
  - testing
  - audit
---

# Test Audit 2026-10-14

Requested by Boris: "make sure we have all that we need and all important enough areas are covered. i'm all for tests... no amount of autotests at this point seems like too much. continue following industry's best practices when finding that perfect balance. 90% coverage would be nice, but is not the goal here."

Principle used: **spend tests where a failure is expensive and hard to notice**, not where lines are cheap to cover. Coverage is read as a map of thin spots, then weighed against risk. Related rule from the same day: [[Real Documents Are the Spec]].

## 1. Method (reproducible)

- **Backend:** `cargo llvm-cov 0.9.1` (installed 2026-10-14; added to [[UnitPrep Tech Stack]]), whole workspace, default tests **plus** the DB-backed `#[ignore]`'d tests (the same selection `scripts/run_ci_db_tests.sh` runs: 18 allowlisted + every `*_db_`) against a fresh throwaway database `unitprep_cov` in the local test-db container. Neon was never touched. Test files and test support are excluded from the numbers. Repeat with `scripts/coverage.sh` (new; prints the per-area table below).
- **Frontend:** `vitest run --coverage` (v8). The config already excludes `app/**/page.tsx` and `app/**/layout.tsx` (route glue) and `*.test.*`.
- **Not measured:** the 6 Playwright specs (they exercise the UI against mocked network routes, so they do not add backend coverage); live-account tests (Process Street, Dropbox, ClickUp) which are manual by design.

## 2. The numbers (2026-10-14)

| | Lines covered | Notes |
|---|---|---|
| **Backend, whole workspace** | **31,768 / 41,622 = 76.3%** | 968 default + 129 + 3 DB tests = ~1,100 tests ran; 0 failed |
| **Frontend** | **72.6%** lines (statements 71.4%, branches 64.5%, functions 71.6%) | 1,046 tests, 133 files, ~21 s |

Backend by area:

| Area | Lines | Reading |
|---|---|---|
| `dedup` (crate) | 97.0% | the core data logic is thoroughly covered |
| `core` (parsing, sessions, vendor formats) | 94.0% | proptest on parsers; weakest file `durable_session_store.rs` (82% covered; 48 of 263 lines uncovered) |
| `unit-group`, `docx-surgeon`, `template-tagger`, `tagger-pipeline` | 96-98% | |
| `src/clickup` | 99.1% | |
| `src/integrations`, `src/application` | ~94-95% | |
| `src/infrastructure` (exports) | 86.1% | |
| `src/auth` (primitives) | 81.8% | TOTP math has 15 tests; `step_up_policy.rs` has none of its own |
| `src/clients` | 79.2% | `create.rs` 42%, `sync/refresh.rs` 25% |
| **`src/api` (HTTP handlers)** | **64.3%** | the weakest large area; see risk map |
| `src/client_ops`, `src/dropbox`, `src/process_street` | 64% / 67% / 58% | external-service clients |
| `src/(root)` (`bootstrap.rs`, `db.rs`) | 46.1% | |
| `src/startup` | 0.0% | state/tasks wiring; never booted by a test |

Frontend by area: `components/clickup` 93.9%, `scan-results` 92.3%, `clients-new` 96.6%, `lib` 81.6%, `tagger` 82.1%, `dedup` 81.2%; weak: `components/facility` 47.7%, `components/audit` 50.6%, `components/auth` 40.5%, `OrchestratorLoader.tsx` 40.2%. Zero-covered files with real logic: `components/TaggerUploadPage.tsx`, `auth/TotpEnrollForm.tsx`, `facility/{Specials,Coverage,Taxes}Tab.tsx`, `lib/useInfiniteLogFeed.ts`, `facility/users/useFacilityUsers.ts`; `app/(app)/admin/users/InviteUserForm.tsx` 2.7%.

## 3. What is already strong (do not redo)

- Pure logic: dedup, unit groups, parsing (with proptest), the tagger crates, ClickUp copy and its permission paths (~100 `_db_` tests against a real Postgres with RLS as `app_service`, so policies actually apply).
- Guards in `scripts/preflight.sh` and CI: fmt, clippy `-D warnings`, `cargo-audit`, gitleaks, secret-pattern scan, workflow-secrets guard, ts-rs type drift check against the UI, `SCHEMA.sql` freshness.
- Regression tests written from real bugs (the CORS DELETE preflight, person identity, tool-run RLS, session idle timeout).
- Durability tests that simulate a process restart for registration, tagger, dedup and group-prep sessions.
- The frontend: 133 files of component, hook and helper tests; tight coverage on the newer features.

## 4. Gaps, ranked by risk (what a failure costs, and whether we would notice)

### A. Security-critical handlers with thin tests (highest priority)

| File | Lines covered | Why it matters |
|---|---|---|
| `src/api/auth_totp.rs` | 17% | TOTP enrollment/verification/step-up: the gate in front of sensitive actions |
| `src/api/auth_login.rs` | 52% | lockout, cookies, session issuance |
| `src/api/auth_user_role.rs`, `auth_user_status.rs` | 54% / 63% | role and status changes: the area of the 2026-07-30 role-escalation bug |
| `src/api/auth_invites/{invite,recovery}.rs` | 65% / 22% | invite and recovery tokens (expiry, single use) |
| `src/api/auth_passkey_reverify.rs`, `src/auth/webauthn_backend.rs` | 22% / 17% | passkey re-verification; needs an authenticator, see E2E below |
| `src/api/auth_audit_logs_export.rs` | 35% | exports of the audit trail |
| `app/(app)/admin/users/InviteUserForm.tsx`, `auth/TotpEnrollForm.tsx` (UI) | 2.7% / 0% | the user-facing half of the same flows |

There is also **no test that every route demands a session**. A forgotten gate (the "gate every route behind a real session" incident) would pass every current test.

### B. The business's headline flows through real data

- `src/clients/create.rs` (42%), `clients_create.rs` (63%), `clients_manual_link.rs` (21%), `clients_resync/*`, `clients_elavon/*` (10-20%), `dedup_rematch.rs` (10%), `dedup/upload.rs` (0%), `dedup/export_dropbox.rs` (10%): client creation from Process Street, linking, resync, Elavon, dedup upload/rematch. Their pure logic is covered; the handler glue and real payload shapes are not.
- **Real-document fixtures are nearly absent.** The whole backend has one real-document fixture (`docx-surgeon/tests/fixtures/atherton-storage-contract.docx`) and `src/clients/testdata`. Vendor formats (SiteLink, QuikStor Cloud, Syrasoft, Easy Storage Solutions, Westpark/Rowley) were each learned from a real export and then tested with synthetic rows. The 2026-10-14 tagger case showed what that costs: all tests green while a real lease got 2 wrong hits.

### C. Data isolation as a property, not an anecdote

Row-level security is the core isolation guarantee (69 policies repointed at one function on 2026-09-10). Tests prove individual policies; nothing enumerates `pg_policies` and asserts, for every table and every role, what is allowed and denied. A new table added without a policy, or a policy loosened, is not caught.

### D. Boot and migrations

- `src/startup/*` and most of `bootstrap.rs` are 0-55%: no test boots the app against a database and hits `/health`.
- Down migrations are never executed (up-down-up). Seed migrations are data (this week alone: 5 pattern/registry seeds), and only the schema is checked.
- The local test-db carried a stale applied copy of a migration (`20261014120000` checksum mismatch), so `bootstrap_test_db.sh` failed on it; `scripts/coverage.sh` sidesteps this by using a fresh database each time. `bootstrap_test_db.sh` itself should offer a reset.

### E. End to end

The 6 Playwright specs mock the API at the network layer, so they prove the UI against what we *think* the API returns, not the API. Nothing runs UI + real API + real DB together, nothing covers the passkey flow (Playwright's virtual authenticator can drive it), and there are no accessibility tests (the grep hits for `axe` were substrings of "Taxes").

### F. Test quality itself

Coverage says a line ran, not that an assertion would fail if it broke. The corpus test below was verified by mutation (removing one pattern made it fail). Nothing measures this for the core logic crates.

## 5. Plan, in order (with rough effort and why)

| # | Item | Effort | Why this order |
|---|---|---|---|
| 1 | **Real-document corpus** (started today: `tagger-pipeline/tests/corpus/`, case 1 = Longview lease, with `patterns.json` + `expected.json`, enforcing well-formed XML, byte-identical untouched parts and `mc:Fallback` copies). Add the other real templates already seen (Atherton, Stowaway, Rest Stop, Sumas, Budget Self Storage, No Ka Oi late notice) as cases; then the same shape for dedup vendor formats (redacted sample + expected recognition) | 1-2 days, ongoing | the biggest demonstrated gap; each case is a folder, never a code change |
| 2 | **Route inventory test**: walk the router, call every route without a session and with each role, assert the expected 401/403/200 from an explicit allowlist | 0.5-1 day | one test guards the "forgot to gate a route" class forever |
| 3 | **Auth handler tests**: TOTP (enroll, verify, replay, rate limit, step-up required for sensitive actions), role/status change matrix (who may change whom, last-admin guard, self-demotion, audit row written), invite/recovery token expiry and single use, login lockout | 2-3 days | highest cost of a miss; history of real bugs here |
| 4 | **RLS matrix test**, generated from `pg_policies`: every table x every role x select/insert/update/delete, against an explicit expected-access table; fails on a table with RLS enabled and no policy | 1-2 days | turns isolation into a checked property |
| 5 | **Client creation / Process Street**: record real (redacted) Process Street payloads and replay them through a loopback mock into `clients::create` (DB test) | 1-2 days | headline flow, and real payload shapes are the thing synthetic tests got wrong before |
| 6 | **Boot smoke test**: start the app against the test DB, hit `/health` and one authenticated route; plus up-down-up for migrations in CI | 0.5 day | closes `startup/*` and migration reversibility |
| 7 | **Full-stack E2E** (3-5 journeys against the real API + test DB, with a Playwright virtual authenticator for passkeys): login, create a client, run dedup, run the tagger, admin invite | 2-3 days | the only place UI-to-API drift would show |
| 8 | **Frontend zero-coverage logic**: TotpEnrollForm, InviteUserForm, TaggerUploadPage, the facility Specials/Coverage/Taxes tabs, `useInfiniteLogFeed`, `useFacilityUsers`; add `jest-axe` checks on the main pages | 1-2 days | cheap, and two are auth forms |
| 9 | **Mutation testing** (`cargo-mutants`) on `dedup`, `unit-group`, `core::parsing`, `docx-surgeon`, scheduled (weekly), never a CI gate | 0.5 day setup | measures whether assertions bite |
| 10 | **Coverage ratchet**: record today's per-area numbers as the baseline; CI (tag job) fails if an area drops by more than a point. No absolute target | 0.5 day | prevents slow erosion without chasing 90% |

## 6. What we are deliberately not chasing

- A blanket 90%. The logic crates are already 94-98%; the remainder is I/O wiring, `startup`, and external-service clients where a test would mostly restate a mock.
- Tests that run live Process Street / Dropbox / ClickUp / Elavon accounts in automation. They stay manual and named for what they hit (existing convention).
- Snapshot-everything UI tests. They create churn; component tests on behavior plus the corpus on documents carry more signal.

## 7. Done today as part of this audit

- Rule: [[Real Documents Are the Spec]], template `templates/Real Document Record.md`, linked from `brain/Memories.md`, the vault `CLAUDE.md` Rules and the `MEMORY.md` index.
- First record: [[Real Document Record - Longview Self Storage Rental Agreement]].
- Corpus harness + case 1 in the repo; `scripts/coverage.sh` + `scripts/coverage_by_area.py` to repeat the measurement.

## 8. Open questions for Boris

- Which of items 2-5 to start with? Recommendation: 2 (route inventory) first because it is a day of work for a permanent guarantee, then 3.
- Do you want the weekly mutation run and the coverage ratchet in the tag-push CI job (cost: a few more CI minutes per release)?
- For fixtures from real *filled* documents and exports: send redacted samples as they come up, or should I redact them myself from the originals in Dropbox (the original path and hash go in each record either way)?
