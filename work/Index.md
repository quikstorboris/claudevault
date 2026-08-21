---
description: "Central map of all work notes — active projects, completed work by quarter, decisions log"
tags:
  - index
  - moc
---

# Work Notes

Central map of content. All work notes and decisions link back here. For quick navigation, use [[Home]] or open `bases/Work Dashboard.base`.

**Folder structure**: `active/` = current projects, `archive/` = completed (by year), `incidents/` = incident docs, `1-1/` = meetings.

## Incidents

Incident docs live in `work/incidents/`. See `Incidents.base` for overview.

-

## Active Projects

- [[Auth & Persistence Index|UnitPrep — Auth & Persistence]] — self-hosted WebAuthn/TOTP + Postgres/Neon+RLS auth system. **As of 2026-08-05: both Phase I (ship/enforce) and Phase II (hardening) closed out, plus a full post-Phase-II backlog shipped** — disable-user, an admin audit-log viewer, three new audit event types, the `onboarding_manager` role and a way to assign it, a last-remaining-admin guard, and a dormant-account indicator. `unitprep-api`/`unitprep-ui` both pushed to `origin/main`, 8 commits across the two repos this pass. **Roles & Permissions is now its own standing, ongoing sub-effort** — see [[Roles & Permissions — Design Discussion]] — and a separate deferred bucket [[Compliance & Process Readiness]] tracks SOX/SOC2/CCPA posture, CI/CD, and availability/recovery for when those actually matter. **Next up, per Boris: QMS API integration** (the reason this whole auth effort exists) — see the Auth & Persistence Index's "Still open" section for what to keep in mind going in.
- [[Platform Vision (Onboarding Orchestrator)]] — long-term vision for UnitPrep becoming a full client-onboarding orchestrator; nothing built yet, planning stage.
- [[2026-08-13-third-audit-fix-plan-full-session-handoff-m1-m2-done-m3-in-p|UnitPrep — Third CTO-Grade Audit \& Fix Plan]] — third full front+back audit (7 High/20 Medium/21 Low findings) after auth/RBAC/admin and the new Template Tagging Assistant shipped; a risk-ordered 8-milestone fix plan is underway. **As of 2026-08-13: M1 and M2 done and pushed** (session-ownership IDOR closed across all 3 session stores, a docx-surgeon CVE, an admin-guard concurrency race, a passkey-based step-up gating TOTP re-enrolment, plus several smaller fixes) — `unitprep-api` v1.8.2, `unitprep-ui` v1.5.1. **M3 in progress** (2 of 3 regression tests added; the real-DB integration test just caught and fixed a second live instance of the exact incident it exists to prevent — an unapplied migration). **M4-M8 not started** — dependency hygiene, DRY consolidation, file splits, broader test coverage, low-severity polish. Full milestone detail in the plan file referenced from the handoff note.

## Review Prep

-

## Recently Completed

- [[New Laptop Migration — QSLP14]] — moved from `QSLP15` to `QSLP14` mid-session; re-cloned both repos (full history intact on `origin/main`, nothing lost), frontend fully verified (native Linux Node via `nvm`, 333/333 vitest passing — a strict improvement on the old setup). Backend build still blocked on missing `pkg-config`/`libssl-dev` — needs Boris's own sudo, see Open Questions.

## Completed

### Current Quarter
- [[Dedup Tool Index|UnitPrep — Dedup Tool]] — duplicate-tenant-check module, built/shipped as its own `unitprep-dedup` crate with full UI; full build history split across domain notes in `work/archive/2026/UnitPrep/Dedup Tool/`.
- [[Code Review Watchlist]] — architecture punch-list closed 2026-07-17; a 2026-07-23 follow-up found and fixed a real CSV-injection gap plus 3 frontend state-scoping bugs. Full item-by-item log in [[Code Review Watchlist - Findings]].
- [[Full Review & 9-Milestone Refactor]] — full front+back codebase review (~36 findings) then all 9 milestones executed and pushed on both repos, 2026-07-24.
- [[Multi-Vendor Unit-File Discovery]] — QSX/DoorSwap/Storage Commander vendor registry for Group Prep's unit-file discovery; committed and pushed 2026-07-25. (Was miscategorized as active/uncommitted until corrected 2026-07-28 — the work and its tests were already live on `main`.) Superseded 2026-08-18 by [[Shared Vendor-Format Registry (Easy Storage Solutions)]] — same recognition mechanics, generalized off hardcoded consts onto one shared, DB-backed registry.
- [[Shared Vendor-Format Registry (Easy Storage Solutions)]] — generalized vendor recognition (Group Prep + dedup) into a shared `client_ops.vendor_format` registry, to onboard Easy Storage Solutions tenant exports; committed and pushed 2026-08-18.
- [[Westpark Cross-Check — Placeholder, Wording, and XLSX Fixes]] — a second colleague cross-check (Westpark) fixed a regressed placeholder bug, misleading typo-variant wording, and real XLSX export formatting defects; committed and pushed 2026-08-20.
- [[Validation & Warnings Redesign]] — validation/warnings pipeline architecture (exclude vs. per-check acknowledge); committed and pushed 2026-07-25, same commit batch as the discovery work above.
- [[Post-Refactor Audit]] — 2nd CTO-grade pre-auth review, all 5 milestones done (incl. a real CORS bug found+fixed+verified); organized into commits and shipped as **v1.1.1** on both repos, 2026-07-28. Full detail in [[Post-Refactor Audit - Details]], commit-by-commit breakdown in [[Post-Refactor Audit - Shipped as v1.1.1]].
- [[Frontend Test Tooling Setup]] — Vitest/RTL + Playwright + coverage tooling wired into `unitprep-ui` (had zero automated tests before this); 18 unit/component tests + 1 E2E test (key={sessionId} regression) all passing. Shipped as part of **v1.1.2** alongside backend property-based/HTTP-integration/race tests and 2 real crash-bug fixes found through fuzzing — full account in [[Shipped as v1.1.2]].
- [[Third Hardening Pass (Pre-Auth-Resume)]] — third layer of hardening on top of v1.1.2: 12 real bugs found via 6-agent adversarial review, each fixed with a regression test. Shipped as `unitprep-api` **v1.1.3**, pushed to `origin/main`, confirmed 2026-07-28. Auth scaffolding (Phase 2 tasks 1-3) correctly stays under `[Unreleased]`.
- [[Frontend v1.1.3 - Test Coverage Expansion]] — unrelated, same-day `unitprep-ui` **v1.1.3**: test coverage 18→262 tests (~9%→~73%), 3 new E2E flows, a flaky-local-E2E fix. Found via `git log`, never previously recorded in the vault.
- [[Fourth Pass - File Splits, Concurrency Fixes, Dead Code Removal]] — closes out the refactor before auth resumes: `validate.rs`/`discover/compute.rs` split, both previously-deferred concurrency races actually fixed, 5 test-coverage gaps closed, `acknowledge_errors` deleted BE+FE (recovery snapshot kept), 6 frontend bugs fixed. 330 BE tests / 270 FE tests, independently re-verified. Shipped as `unitprep-api` v1.1.4 + `unitprep-ui` v1.1.4, both pushed to `origin/main` 2026-07-28.
- [[Fifth Pass - Adversarial Review Findings Fixed]] — 5 parallel reviewers caught a re-opened TOCTOU race (`complete_discovery` missing a generation bump), a dead Cancel button, a mislabeled button, a recurring sibling-hook-parity gap, and more. 336 BE tests / 278 FE tests. Shipped as `unitprep-api` v1.1.5 + `unitprep-ui` v1.1.5, pushed 2026-07-29. Refactor treated as concluded — auth can resume.

### Previous Quarters
-

## Reference

- [[UnitPrep Architecture Overview]] — what UnitPrep is, its Cargo-workspace + Next.js architecture, pipeline, and principles.
- [[UnitPrep File Locations]] — where UnitPrep docs, sample data, source code, and the QMS OpenAPI spec live across drives.
- [[UnitPrep UI Dev Environment]] — running `unitprep-ui`'s dev server from non-interactive WSL, node quirks, build-vs-dev gotchas.
- [[UnitPrep Context Skill]] — the portable Claude Skill file with UnitPrep architecture/history; stale as of 2026-07-16.
- [[WSL Execution Technique]] — reliably running commands in the real `unitprep-api` WSL environment from Windows.
- [[Python Environment]] — confirms a real Python 3.14.6 + pip install on PATH (Windows side).
- [[Deleted Code - acknowledge_errors Export Override (Recovery Snapshot)]] — verbatim BE+FE code for the dead export-override pathway, deleted 2026-07-28; restore from here if needed during testing.

## Decisions Log

| Date | Decision | Status | Link |
|------|----------|--------|------|
| 2026-07-20 | Self-hosted WebAuthn/TOTP auth, opaque session cookies (not JWT/DPoP), Postgres via Neon with RLS, single Admin role for v1 | Final (architecture) | [[Architecture]] |
| 2026-07-23 | Git branch policy: `main` only on `unitprep-api`/`unitprep-ui`, no incidental branches without explicit ask | Standing rule | [[Patterns]] |
| n/a | UnitPrep has no auth by design for current single-operator internal use — revisit only when scope goes client-facing | Standing, revisited 2026-07-20 | [[Gotchas]] |
| n/a | Patch versions bump once per real release boundary (batched), not once per fix; `cargo-llvm-cov` is the primary coverage tool, `cargo-tarpaulin` an occasional cross-check only | Standing | [[Key Decisions]] |
| 2026-08-05 | `onboarding_manager` role added, schema-only (no permissions) until a deliberate allowlist decision is made; any admin may assign either role | Standing | [[Key Decisions]] |
| 2026-08-05 | Permissions/roles design work is its own ongoing effort, tracked separately from routine feature work | Standing | [[Roles & Permissions — Design Discussion]] |

## Open Questions

- **Significant, deliberately deferred**: the two `#[ignore]`'d real-PII fixture tests in `unitprep-api/dedup/tests/reference_fixtures.rs` never run automatically (no CI exists). Revisit once the rest of the outstanding, non-deferred test/refactor work is complete — not before. See [[Dedup Tool Index]].
- On the new laptop (`QSLP14`): install `pkg-config`/`libssl-dev` (`sudo apt-get install -y pkg-config libssl-dev`, needs Boris's own sudo password) so `cargo build`/`test`/`sqlx-cli` work again, then restore `.env.local` from wherever it's actually backed up (not documented anywhere in this vault — worth fixing once found). See [[New Laptop Migration — QSLP14]].
- Duplicate rows across dedup's flagged/typo-variant/related-tenant report sections — the same tenant can independently appear in all three with no cross-reference between them. Two options on the table (de-dupe to one row per unit, or split into separate tabs), neither picked yet. See [[Westpark Cross-Check — Placeholder, Wording, and XLSX Fixes]].

## Archive

-
