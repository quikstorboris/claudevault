---
date: 2026-07-28
description: "Third hardening pass after v1.1.2: 12 real bugs found via 6-agent adversarial review, fixed with regression tests each. Shipped as unitprep-api v1.1.3, pushed to origin/main."
tags:
  - work-note
  - unitprep
status: completed
quarter: Q3-2026
project: unitprep
---

# Third hardening pass on unitprep-api/ui: 12 concurrency/correctness bugs fixed, 12 more items deliberately deferred

Direct continuation after v1.1.2 shipped (two prior audit passes already brought the codebase to a clean, tested, fmt/clippy-clean state to prepare for resuming auth). This third pass added another layer of hardening on top: 12 more real correctness/concurrency bugs found and fixed, including session data races and request-validation issues — exactly the class of bug that matters most once real user identity enters the picture via auth. Reported zero regressions, 321 tests passing (up from 284 at v1.1.2's end). Auth scaffolding (Phase 2 tasks 1-3: AuthBackend trait, session cookies, AuthenticatedUser extractor + RLS transaction helper) was left untouched and remains verified against live Neon dev.


## Decisions

- Session-cleanup sweep lock scope and cancel_session's concurrent-mutation race: mitigation logged, not fixed — evaluated as disproportionate to fix given actual single-operator scale/risk, not an oversight.
- Dedup name-similarity asymmetry (inherited from Python difflib) and Unicode/diacritic-insensitive matching (inherited, matches the Python reference): treated as behavior characteristics carried over from the reference implementation, not confirmed bugs — asymmetry never observed to flip a real classification.
- api/validate.rs (367 lines) and discover/compute.rs (464 lines) still mix concerns; extraction plans already exist in the prior audit (see Post-Refactor Audit - Details) but were judged lower priority than the correctness/concurrency fixes in this pass.
- rsa crate's Marvin-attack timing-side-channel advisory (RUSTSEC-2023-0071, pulled in transitively via sqlx-mysql even though only the postgres feature is enabled) re-confirmed as accepted/non-reachable, already documented in .cargo/audit.toml.
- Load/perf benchmarking remains queued by Boris but was not run this pass.
- No CI/GitHub Actions on either repo — explicitly out of scope per Boris, reaffirmed for a second time.



## Verification

Per the outgoing session's own report: 321 tests passing, up from 284, zero regressions, fmt/clippy clean. Auth scaffolding separately reported as verified against live Neon dev in the Phase 2 Progress note.

**Independently confirmed 2026-07-28 by this session**, directly against the WSL checkout (`git log`, `CHANGELOG.md`): shipped as `unitprep-api` **v1.1.3** (commit `47fce24`, "Bump version to 1.1.3"), all 12 fixes itemized in `CHANGELOG.md` under `[1.1.3]` match this note's decisions/summary, and `main`/`origin/main` are in sync (nothing unpushed). The auth scaffolding (AuthBackend, session cookies, AuthenticatedUser, plus a `Postgres connectivity via sqlx` / `app_service` role item this note hadn't captured) correctly still sits under `[Unreleased]`, consistent with the project's one-bump-per-release-boundary philosophy.

**Correction**: this note originally claimed `unitprep-ui` had no corresponding commits. Wrong — `unitprep-ui` independently shipped its *own* v1.1.3 the same day, a much larger and entirely separate frontend test-coverage expansion (18→262 tests, ~9%→~73% coverage, 3 new E2E flows) that this pass's write-up never mentioned. See the new note [[Frontend v1.1.3 - Test Coverage Expansion]] — that work is unrelated in content to this backend pass; the two repos' version numbers matching (1.1.3/1.1.3) is coincidental, not a joint release (the two repos version independently per `unitprep-ui`'s own `CHANGELOG.md` header). Frontend confirmed bugs below are still unfixed on `unitprep-ui`'s `main` as of this check — the coverage expansion added tests, not fixes.

**One loose end found during this check, unrelated to the hardening pass**: `unitprep-api`'s working tree has two untracked, uncommitted paths — `README.sample.md` and `assets/readme/` (a `hero.svg` + directory, timestamped Jul 28 08:03) — that look like an in-progress README redesign never committed or discarded. Not part of this pass; flagged for Boris to commit or clean up.


## Open

- Frontend confirmed-but-unfixed bugs in unitprep-ui: dead acknowledge_errors export pathway (real feature-gap regression from a past refactor), export-download success state never resets on a new attempt, sessionExpired never resets in useSessionAction (asymmetric with its sibling hook), no reentrancy guard on the export action (double-click risk). Lower priority: ClientTabs/LeftNav missing aria-current, dormant Content-Disposition regex fragility, dormant clients.tsx module-singleton risk.
- Frontend npm audit: next/postcss/sharp/brace-expansion High-severity advisories, no non-breaking fix currently exists — tracked, re-check periodically.
- Auth Phase 2 tasks 4-11 of 11 still pending: WebAuthn registration HTTP endpoints (next up), WebAuthn login HTTP endpoints, invite creation, invite acceptance, first-Admin bootstrap, TOTP fallback, logout, audit-coverage closing check.
- app_service's real password still not in unitprep-api/.env.local (Boris's own credential to add), and not yet repeated on the prod branch.
- Admin UI (Phase 3) and step-up re-auth (Phase 4) not started. totp_credentials.secret_encrypted encryption-at-rest mechanism still undecided.
- Heads-up for whoever wires auth into /analyze and /export: with_owned_session/with_owned_session_mut already exists (built in the session-ownership milestone) but no handler uses it yet — every handler, plus the new generation-check logic, will need the one-line with_session_mut -> with_owned_session_mut swap.
- Every bug-hunt agent's suggested test-coverage gaps beyond what was actually fixed this pass (Unicode name tests, 1-2-record pipeline tests, non-UUID session_id test, oversized-multipart test, error-shape sweep test, etc.) were not implemented.


## Related

- [[Third Hardening Pass (Pre-Auth-Resume) — Session Log]] — the recovered first-hand discovery-and-fix account, verbatim
- [[Post-Refactor Audit - Details]]
- [[Shipped as v1.1.2]]
- [[Phase 2 Progress]]
- [[Build Plan & Infra Checklist]]
- [[Gotchas]]


_Recorded 2026-07-28T21:19:49.233Z from `bmaksimov` via the om MCP server (routing: fallback)._
