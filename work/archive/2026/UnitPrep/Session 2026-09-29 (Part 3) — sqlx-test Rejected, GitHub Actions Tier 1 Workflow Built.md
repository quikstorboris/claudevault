---
date: "2026-09-29"
quarter: "Q3-2026"
description: "Verified sqlx::test is hardcoded to DATABASE_URL with no override in any version (rejected, kept connect_test() instead), then built and shipped Tier 1 of the CI/CD framework -- GitHub Actions workflows for both repos, an ephemeral-Postgres service container for unitprep-api's DB-only tests, and a generalized bootstrap script shared between local Docker and CI"
tags:
  - work-note
  - project/unitprep
  - ci-cd
---

# Session 2026-09-29 (Part 3) — sqlx-test Rejected, GitHub Actions Tier 1 Workflow Built

Same-day continuation of [[Session 2026-09-29 (Part 2) — Grok Review Follow-Through, TEST_DATABASE_URL Isolation Control & a Real Postgres DO-Block Bug|Part 2]]. Asked what's next for CI; given the choice between the small remaining named item (`#[sqlx::test]` adoption) and the actual big one (building Tier 1 itself), Boris asked for both, small one first.

## `#[sqlx::test]`: checked properly, rejected with evidence, not assumed

The framework doc's own text suggested adopting sqlx's `#[sqlx::test]` macro as "the sqlx-idiomatic version" of the isolation guarantee. Before touching any test code, checked the actual crate source rather than trusting the suggestion was still current: `sqlx-postgres`'s `Testing` trait implementation is hardcoded to `dotenvy::var("DATABASE_URL")` — verified in both the project's pinned `0.8.6` and the latest `0.9.0` (fetched into an isolated scratch project specifically to check, never touching the real repo's dependencies). The attribute macro's own argument parser (`sqlx-macros-core`'s `test_attr.rs`) only accepts `fixtures`/`migrations` — no URL or env-var override exists in the syntax at all, in either version.

Adopting it as originally suggested would have been an active regression, not a neutral trade-off: it would make these tests read plain `DATABASE_URL` again — the same variable the real app uses, sourced from bind-mounted `.env.local`, pointed at real Neon — silently undoing the `TEST_DATABASE_URL` isolation control built in Part 2 the same day. Recorded as **checked and rejected** in [[UnitPrep CI-CD Framework]], not left as a stale "worth adopting" suggestion; `connect_test()` already provides the actual guarantee that line wanted.

Boris asked, given "no override at all in either version," whether this gap is worth building and contributing back to the Rust community — answered at the end of this note.

## Tier 1 built: GitHub Actions for both repos

Split by cost, exactly as designed: `fast-checks` (fmt/clippy/`cargo check` for `unitprep-api`, `tsc`/`eslint` for `unitprep-ui`) on every push to `main`; `full-tests` (the complete suite, plus `unitprep-api`'s DB-only tests) only on a version-tag push.

**The one piece that needed real care**: which `#[ignore]`d tests are safe to run automatically in CI. Read every single test's own `#[ignore = "..."]` reason string across the whole codebase rather than guessing from test names — a real, concrete reason this mattered: one of the 17 genuinely DB-only-safe tests is literally named `attach_output_dropbox_runs_cleanly_against_the_real_schema`, which a naive `--skip dropbox` name-pattern heuristic would have wrongly excluded despite it needing no real Dropbox access at all (it just persists a Dropbox-*sourced* reference to the database). Cargo's own test harness only accepts one filter substring per invocation anyway, so there's no single flag for "all ignored tests except these" — the correct, safe-by-default shape (isolation control #5) is an explicit allowlist (`scripts/run_ci_db_tests.sh`, new), where a newly-added `#[ignore]`d test does not get picked up in CI automatically; adding it is a deliberate, visible, one-line edit.

`bootstrap_test_db.sh` (from Part 1/2) had its host/port/credentials hardcoded to the local Docker setup's specific values — parameterized via env vars (defaulting to the existing values, so nothing changed for local use) specifically so the same script also works unchanged against GitHub Actions' service container, rather than near-duplicating similar-but-different bootstrap logic in the workflow YAML itself.

**Verified before wiring anything into CI, not after**: ran the new allowlist script locally via `docker compose exec api-dev` against the real ephemeral test-db — all 17 tests passed. Installed `actionlint` (binary download, same pattern as `gitleaks` earlier this week) and validated both workflow YAML files — schema plus embedded shellcheck, both clean. Could not verify an actual live GitHub Actions run from this environment: no `gh` CLI or token available, and none was set up for this session. This is a real, named verification gap — the first genuine live run needs confirming by checking the Actions tab directly.

**Shipped**: `unitprep-api` `v1.9.47` → `v1.9.48` (3 commits: bootstrap script parameterization, the Tier 1 build, version bump), `unitprep-ui` `v1.6.45` → `v1.6.46` (2 commits: the Tier 1 build, version bump), all tagged and pushed.

## Is the sqlx::test gap worth contributing upstream?

Boris asked directly. Honest answer: **plausibly yes, but not obviously so**, and it's the kind of thing worth raising as an issue/discussion before writing code, not assuming a PR is wanted.

What's actually missing: `sqlx::test`'s per-database-server-provisioning logic (`TestSupport`/`Testing` trait implementations for each driver) reads exactly one hardcoded env var name per driver, with no way to override it — not via the attribute macro's arguments, not via a Cargo feature, nothing. A natural fix shape: an optional `url_var = "..."` (or similar) argument on the attribute macro, defaulting to `"DATABASE_URL"` for full backward compatibility, threaded through to the `Testing` trait's provisioning calls. That's a modest, additive, non-breaking change in principle.

Why it's not a slam dunk to just go build: (1) `sqlx` is a mature, widely-used crate with existing maintainer conventions and an issue tracker that may already have a rejected or in-flight proposal for this exact thing — worth searching before writing anything. (2) The workaround this project already has (`connect_test()`, built the same day) is genuinely fine long-term, not just a stopgap — meaning the motivation for contributing upstream is "this would help others," not "we're blocked without it." (3) A real contribution needs the actual maintainers' buy-in on the design (arg name, default behavior, whether it belongs on the macro or a lower-level config), which means opening a discussion/issue first, not arriving with a finished PR they might want shaped differently.

**Recommendation, not yet acted on**: worth opening a GitHub issue on `sqlx` describing the gap precisely (as verified here — hardcoded env var, no override, checked across two versions) and proposing the `url_var` shape, before writing any actual patch. Genuinely useful to the wider Rust/sqlx community if the maintainers agree it's a real gap, since anyone wanting a distinctly-named test-database env var (for exactly this kind of isolation reason, not necessarily this project's specific naming) would hit the identical wall.

## Related

- [[Session 2026-09-29 (Part 2) — Grok Review Follow-Through, TEST_DATABASE_URL Isolation Control & a Real Postgres DO-Block Bug]] — same-day predecessor, built the `TEST_DATABASE_URL`/`connect_test()` machinery Tier 1 reuses
- [[UnitPrep CI-CD Framework]] — Tier 1 marked built, isolation control #1 and the `#[sqlx::test]` rejection recorded
- [[Gotchas]] — no new entry this part; the verification-gap (no live GH Actions run confirmed) is named here instead, deliberately not overstated as a Gotcha since nothing went wrong, it just wasn't checkable
