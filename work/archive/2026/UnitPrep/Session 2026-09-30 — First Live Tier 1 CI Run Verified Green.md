---
date: "2026-09-30"
quarter: "Q3-2026"
description: "The first real GitHub Actions run of unitprep-api's Tier 1 CI workflow (v1.9.48 tag push) verified green end to end -- ephemeral Postgres service container, migrations, bootstrap script, full test suite plus all 17 DB-only ignored tests, closing the (TBC) verification gap Part 3 left open"
tags:
  - work-note
  - project/unitprep
  - ci-cd
---

# Session 2026-09-30 — First Live Tier 1 CI Run Verified Green

Direct continuation of [[Session 2026-09-29 (Part 3) — sqlx-test Rejected, GitHub Actions Tier 1 Workflow Built]], which shipped Tier 1 but left one explicit gap: no `gh` CLI/token in that session, so the actual live GitHub Actions run couldn't be confirmed, only the YAML (`actionlint`) and the underlying scripts (run locally). Boris checked the Actions tab himself and pasted the full `full-tests` job log for `unitprep-api`'s `v1.9.48` tag push.

## Result: genuinely green, not just YAML-valid

Read the full log end to end rather than trusting the job's own pass/fail summary alone, since a green checkmark can hide a test that's accidentally a no-op. Confirmed real:

- **Ephemeral Postgres, not a mock**: a real `postgres:18` service container spun up fresh on GitHub's runner, health-checked, then torn down at job end (the post-job log dump shows the exact container lifecycle, including its own boot log).
- **`bootstrap_test_db.sh` ran unmodified** against it via `TEST_DB_HOST=localhost TEST_DB_PORT=5432` env overrides — the same parameterization built in Part 3 specifically so this script wouldn't need CI-specific duplication. All 91 migrations applied cleanly in the ephemeral container, in the same order as local Docker.
- **`cargo test --workspace`**: 654 passed, 0 failed, 35 `#[ignore]`d (correctly left alone at this stage), across all workspace crates.
- **All 17 DB-only allowlisted tests** (`scripts/run_ci_db_tests.sh`) ran via `--ignored <name>` in a loop, connecting as `app_service` (not superuser) against the same ephemeral Postgres — all 17 passed, confirming the RLS-respecting connection path built in [[Session 2026-09-29 (Part 2) — Grok Review Follow-Through, TEST_DATABASE_URL Isolation Control & a Real Postgres DO-Block Bug|Part 2]] works identically in CI as it did locally.
- **Isolation controls held**: no `DATABASE_URL`/Neon credential appears anywhere in the job's env or log; `TEST_DATABASE_URL` is the only one referenced, pointed at `localhost:5432` (the ephemeral container), never anything `.neon.tech`.

## Three things in the raw log that look alarming but are expected, by design

Worth recording precisely, since a future session (or Boris skimming the log again later) could easily mistake any of these for a regression:

1. **Dozens of `password authentication failed for user "test"` lines in the Postgres container's own log**, clustered during the `cargo test --workspace` step. These are not CI infrastructure failing — they're the test suite itself deliberately exercising the app's graceful-degradation path: several HTTP-handler tests (e.g. `get_company_detail_returns_404_for_the_unreachable_test_pool_as_a_500`, and the broader family of `..._reaches_the_database` tests) construct a pool pointed at a nonexistent/wrong-credential target on purpose, to assert the app returns a clean 500/404 rather than panicking when a DB call fails. Real Postgres logs the connection attempt at `ERROR` regardless of intent, so the server log looks alarming even though the test that caused it passed.
2. **`role "neondb_owner" does not exist` errors, twice**, during `bootstrap_test_db.sh`'s grant step. This is the exact scenario the `DO $$ ... EXCEPTION WHEN undefined_object ...` fix from [[Session 2026-09-29 (Part 2) — Grok Review Follow-Through, TEST_DATABASE_URL Isolation Control & a Real Postgres DO-Block Bug|Part 2]] was built for — a non-Neon Postgres (this ephemeral one) genuinely has no `neondb_owner` role, the nested exception handler catches it and emits a `NOTICE` instead of aborting the whole grant block, and the script's own `psql` output confirms the catch worked (`NOTICE: role "neondb_owner" does not exist (not running on Neon) -- skipping...`). Postgres still logs the underlying attempt at `ERROR` server-side even though it was caught client-side — that's normal Postgres logging behavior, not a sign the catch failed.
3. **One `new row ... violates check constraint "policy_delinquency_entries_check"` error**, during the DB-only test phase. This is the single assertion inside `policy_delinquency_entries_trigger_check_matches_the_apps_own_validation` — a test whose entire purpose, per its own name, is confirming the database's CHECK constraint rejects the same invalid category/trigger combination the app's own validation layer rejects. The test deliberately inserts a bad combination, expects Postgres to refuse it, and passed. Again, Postgres logs the refusal at `ERROR` server-side; the test result is `ok`.

None of these three are gotchas or regressions — they're expected noise from tests that are *supposed to* provoke a rejection and then assert on it. Recording this explicitly so a future skim of a similar log doesn't misread "the word ERROR appears in the Postgres log" as "something broke."

## `fast-checks` did not run on this push — also expected

Boris noted `fast-checks` didn't fire and asked if that was a problem. It isn't: `fast-checks` carries `if: github.ref_type != 'tag'` by design (see [[UnitPrep CI-CD Framework]]'s Tier 1 section) — it's meant for ordinary pushes to `main`, and `full-tests` is meant for tag pushes. This push was the `v1.9.48` tag itself, so only `full-tests` was supposed to run, and it did. **Still open**: a plain non-tag commit hasn't yet been pushed since Tier 1 shipped, so `fast-checks` itself remains unconfirmed live (though its steps — `cargo fmt`/`clippy`/`cargo check` — are exactly what Tier 0's `preflight.sh` already runs locally, so the risk of it being broken is low; it just hasn't had its own live data point yet).

## Status

The `**(TBC)**` marker on Tier 1's verification note in [[UnitPrep CI-CD Framework]] is resolved for `unitprep-api`'s `full-tests` job. Two smaller gaps remain, both low-risk and not blocking anything: `unitprep-api`'s `fast-checks` job and all of `unitprep-ui`'s CI (both jobs) still await their own first live confirmation — normal pushes/tags will surface these naturally without needing a dedicated verification session.

## Related

- [[Session 2026-09-29 (Part 3) — sqlx-test Rejected, GitHub Actions Tier 1 Workflow Built]] — shipped Tier 1, left the verification gap this session closes
- [[Session 2026-09-29 (Part 2) — Grok Review Follow-Through, TEST_DATABASE_URL Isolation Control & a Real Postgres DO-Block Bug]] — built the `TEST_DATABASE_URL`/`connect_test()`/DO-block-exception machinery this run just confirmed works identically in CI
- [[UnitPrep CI-CD Framework]] — Tier 1 status line updated to confirmed-live
