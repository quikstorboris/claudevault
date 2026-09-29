---
date: "2026-09-29"
quarter: "Q3-2026"
description: "Had Grok review the freshly-built Docker setup, verified its findings independently rather than accepting them at face value, then implemented the two real ones -- building the CI/CD framework's TEST_DATABASE_URL isolation control for real and fixing an RLS-bypass regression that led to discovering a genuine, pre-existing bug in a shared production script"
tags:
  - work-note
  - project/unitprep
  - ci-cd
  - docker
---

# Session 2026-09-29 (Part 2) — Grok Review Follow-Through, TEST_DATABASE_URL Isolation Control & a Real Postgres DO-Block Bug

Same-day continuation of [[Session 2026-09-29 — Docker Phases 2-3, cargo-chef Amendment & Fly.io Multi-Instance Decision|the Docker Phases 2-3 session]]. After the dev containers were built, verified, and live-tested (including three real bugs fixed the hard way), Boris asked for a short prompt to hand the finished Docker setup to Grok for a second opinion, then pasted Grok's review back for a plain-language verdict before deciding what to act on.

## Evaluating Grok's review — not accepting it at face value

Went through each finding independently rather than treating the review as authoritative:

- **"Next.js may be listening on the wrong interface"** — already disproven. Boris had already browsed `localhost:3001` and logged in successfully through it earlier the same session; a real login through the full stack settles this more conclusively than the theoretical concern.
- **"Possible missing C toolchain"** — already disproven. The workspace had already compiled successfully inside `api-dev` multiple times, including `webauthn-rs`'s native OpenSSL code.
- **"`#[ignore]`d real-DB tests likely bypass RLS"** — real. `TEST_DATABASE_URL` connected as the `postgres` superuser, which bypasses row-level security entirely regardless of any application-level role simulation within a transaction (Postgres skips RLS evaluation for table owners/superusers before any policy is even considered). Confirmed by reasoning through how `begin_rls_transaction`'s GUC-based role simulation actually interacts with Postgres's RLS mechanism, not just taking the finding on faith.
- **"Bind-mounted `.env.local` undercuts the 'no Neon in Docker' guarantee"** — real, but not a new risk: manually running `cargo run` inside the container reads the same `.env.local`/`DATABASE_URL` it always has, hitting real Neon dev — identical to pre-Docker native behavior. The actual gap was that this wasn't written down anywhere, so it read as contradicting the "never touch Neon automatically" rule when it's actually a deliberate, human-driven action that rule was never about.
- **Minor/polish items** (exact Postgres patch pinning, host-tool-dependent bootstrap script) — acknowledged, deliberately not acted on, consistent with this project's own "don't over-invest" principle.

## Building the TEST_DATABASE_URL isolation control for real

The two real findings both trace back to the same underlying gap the previous session had already flagged but not yet closed: the CI/CD framework's isolation control #2 (a distinct `TEST_DATABASE_URL`, never `DATABASE_URL`, hard-fail if unset) was designed but never actually implemented in code — every `#[ignore]`d test still called `crate::db::connect()` directly, reading the same `DATABASE_URL` the real application uses.

Added `db::connect_test()`: reads `TEST_DATABASE_URL` only, panics with a clear message if unset or malformed, and asserts the resolved host doesn't end in `.neon.tech` (control #3, the runtime guard) — a second, independent backstop, not just discipline. Migrated all 24 call sites across 12 files off `db::connect()`; `main.rs`'s real application startup is untouched. Verified empirically, not assumed: unset → clear panic; malformed → clear panic; a fake `*.neon.tech` URL → rejected; correctly configured → passes.

## The RLS fix uncovered a real, pre-existing bug in shared tooling

Fixing the superuser-bypass issue meant pointing `TEST_DATABASE_URL` at `app_service` instead — which meant giving `app_service` a real (throwaway, local-only) password via `bootstrap_test_db.sh`, since the shared `setup_app_service_role.sql` deliberately never sets one (correct for real Neon, where a human sets it by hand).

Doing this surfaced something new: `app_service` had **no access to `auth` at all** — not a permissions nuance, a hard `permission denied for schema auth`. Traced to a real bug in `setup_app_service_role.sql` that had nothing to do with anything built this session: each schema's `GRANT USAGE`/`GRANT SELECT,INSERT,UPDATE,DELETE` statements are bundled into the same `DO $$ ... $$` block as an `ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner ...` statement that always fails on a non-Neon Postgres. An uncaught exception anywhere inside a `DO` block aborts the *entire* block as one transaction — so that one already-understood, seemingly-harmless error was silently rolling back the two useful grants sitting right next to it. This bug has presumably existed in this script since it was written; it only surfaced now because this was the first time anyone tried to actually *use* `app_service` against a local, non-Neon Postgres and check the result with a real query, rather than just watching the script's own output for errors and treating the expected one as accounted for.

Fixed by wrapping just the `neondb_owner` statement (5 occurrences: `auth`, `client_ops`, `integrations`, `clients` ×2) in its own nested `BEGIN ... EXCEPTION WHEN undefined_object THEN ... END;` sub-block — a real Postgres savepoint, isolating that one statement's failure from its neighbors. Verified against a fresh local `test-db`: clean `NOTICE`s instead of aborting `ERROR`s, and `app_service` provably able to query `auth.*` afterward (the previously-passing-but-not-really-proving-anything test now genuinely exercises RLS). Behavior against real Neon is unchanged — the exception never fires there, confirmed by reading the logic rather than assumed.

**Shipped**: `unitprep-api` `v1.9.46` → `v1.9.47` (4 commits: the `connect_test()` wiring, the SQL script fix, the `app_service`/RLS fix, then the version bump), tagged and pushed.

## A repeat mistake, caught and fixed before moving on

One of the four commits (the `app_service`/RLS fix) opened with "Found via external review, 2026-09-29:" — a direct violation of the standing commit-message rule below, first established 2026-07-15 after the exact same kind of slip. Caught by checking [[Patterns]] *after* already writing the commits, not before — the check should have happened first. Fixed properly rather than left alone, since Boris confirmed it was worth doing: `git reset --hard` to the commit before it, `cherry-pick --no-commit` to reapply the same change with a corrected message, re-applied the version-bump commit on top, verified the resulting tree was byte-identical to the original (`git diff` between old and new tip, empty), then `--force-with-lease` pushed both the branch and the moved `v1.9.47` tag. Low-risk in practice (solo-dev repo, pushed only minutes earlier, nothing else could have pulled it), but still a real history rewrite, done deliberately and verified rather than assumed safe.

## Vault updated

[[UnitPrep CI-CD Framework]]'s isolation controls #2 and #3 marked built for the local/Docker case (Tier 1 CI itself remains dormant — this closes the control for local dev specifically, per the framework's own item 6). New [[Gotchas]] entry on the `DO`-block transaction-scope finding — general Postgres/PL-pgSQL knowledge, not specific to this project. [[Patterns]]'s commit-message-provenance rule updated with this second occurrence.

## Related

- [[Session 2026-09-29 — Docker Phases 2-3, cargo-chef Amendment & Fly.io Multi-Instance Decision]] — same-day predecessor, built the containers this session's review was actually about
- [[UnitPrep CI-CD Framework]] — isolation controls #2/#3 marked built this session
- [[Gotchas]] — the `DO`-block transaction-scope entry, the CORS/port-remap entry from earlier the same day
- [[Patterns]] — the commit-message-provenance rule this session violated once and then fixed; also the file where verifying an external review's claims independently (rather than acting on them at face value) has been noted as a recurring practice in past sessions (2026-08-14, 2026-09-09), applied again here but not itself written up as its own titled rule
