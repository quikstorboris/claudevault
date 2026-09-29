---
date: "2026-09-29"
quarter: "Q3-2026"
description: "Walked through the Option A/B dev-container tradeoff from scratch for a non-technical audience, named Fly.io as the target host with a standing multi-instance design assumption, then built and empirically verified unitprep-api's Docker Phase 2 dev container -- finding and fixing a real cargo-chef/volume-shadowing interaction, a missing rustup volume, and a test-db bootstrap gap along the way"
tags:
  - work-note
  - project/unitprep
  - ci-cd
  - docker
---

# Session 2026-09-29 — Docker Phase 2, cargo-chef Amendment & Fly.io Multi-Instance Decision

Same-day continuation of [[Session 2026-09-28 (Part 4) — Tier 0 CI Tooling Built (cargo-audit, gitleaks) with Real RUSTSEC and npm-audit Fixes|the prior day's Tier 0/Docker Phase 1 session]], from the same Windows-session-reaching-into-WSL setup. Boris asked what's next on the Docker/CI menu, picked Docker Phase 2, then paused to actually understand the mechanics before deciding anything ("most of it is over my head... I need more to go on") — the whole first half of this session is a deliberately slow, plain-language walkthrough of Docker concepts for a non-technical audience, one decision at a time, rather than building first and explaining after.

## Teaching pass: Option A vs. B, decided in the user's own terms

Broke "bind-mounted, not rebuilt per code change" down from first principles (the "baking a cake" vs. "toolbox next to your files" framing) before any pros/cons list, since an earlier attempt at explaining local testing / ephemeral DBs / CI all at once landed as "over my head." Once narrowed to just Option A (rebuild image per edit) vs. Option B (bind-mount + long-lived container), gave a clear recommendation (B) grounded in Boris's own actual daily pattern (100+ commits/month, constant small edit-test loops) rather than abstract Docker best-practice. Confirmed **no rework cost** to the rest of the framework either way — Tier 1 CI, Tier 2, and the Phase 4 production image are all architecturally independent of the dev-container's internal choice, checked point by point rather than asserted.

## The `cargo watch` mode decision, and a real question about redundancy

Boris pushed back on the initial `-x check` recommendation with a technically correct observation: `test --workspace` is a strict superset of `check` (can't run tests on code that doesn't compile), so running both separately might just be redundancy. Answered honestly rather than defending the original recommendation: `check`'s only real advantage is speed, and the cost of `test --workspace` in always-on mode is a slower, occasionally-stale feedback loop during rapid editing (a save can get superseded by the next one before a full test run finishes). Framed why re-running the same tests in `preflight.sh` isn't wasted duplication either: continuous personal feedback vs. a deliberate final gate before push are different roles, same "no single control trusted alone" pattern the project already applies to auth. Boris chose `test --workspace` anyway, informed rather than by default.

## Fly.io named, multi-instance made a standing assumption

Asked directly what to prepare for, hosting-wise. Most of it already lined up by accident (the `/health` endpoint, the `PORT` env var convention) — the one real, non-cosmetic implication was session storage: `DurableSessionStore`'s hot path is in-process memory, which breaks the moment more than one Fly.io Machine can serve a request. Boris's explicit call: **always design on the assumption that Fly.io will run multiple machines**, now, rather than retrofit later — "rather be ready for it, then have to pay the price later." Recorded in [[Key Decisions]] (2026-09-29 entry) and reflected in [[UnitPrep CI-CD Framework]]'s Phase 4 row and Redis section: the deployment-model open question is closed as a design assumption, execution stays exactly as deferred as before. Confirmed this has zero bearing on Phase 2 itself — local dev tooling and production topology are genuinely orthogonal.

## Docker Phase 2, built and verified

**Two real findings before any Dockerfile was written:**

1. **A false alarm, caught by reading context instead of trusting a grep match count.** A `grep -rln 'sqlx::query!\|query_as!'` hit "1 file," which looked like it meant the project uses compile-time-checked `sqlx` queries (needing a live DB connection just to *compile* — a real problem for a container that should never touch Neon automatically). Reading the actual line showed it was a doc-comment saying the *opposite* — this crate deliberately has no such usage. Verified directly: `cargo check --workspace` and `cargo test --workspace` both succeed with zero `DATABASE_URL` set at all. No offline query cache needed; there was nothing to cache.
2. **`test-db`'s migrations needed `app_service` to exist first**, hit for real running `sqlx migrate run` against a fresh local Postgres (`role "app_service" does not exist"`) — `scripts/setup_app_service_role.sql`'s own header already documents the exact "run it, migrate, run it again" sequence this needs (a real Neon incident from 2026-07-29 is why that ordering exists at all). The script's `neondb_owner`-specific lines error out harmlessly on a local (non-Neon) Postgres — expected, not fixed, since rewriting a real production script to accommodate local testing isn't the right call.

**Built**: `Dockerfile.dev` (toolchain-only image, no `cargo-chef`) + `docker-compose.yml`'s `api-dev` service (bind-mounted source, four named volumes, port `8080` forwarded, `depends_on: test-db: condition: service_healthy`). Verified empirically, in order: image builds clean; both containers start together with the healthcheck gate actually working; the full workspace test suite passes inside the container; a host-side one-line edit to `src/main.rs` triggered an automatic re-run with no restart (the single most important property of the whole design); `docker compose exec api-dev cargo run` started the live server, reachable at `localhost:8080` from both WSL and Windows, stopped cleanly without disturbing the watch loop.

**Two more real findings, from actually trying to use what got built, not just confirming it started:**

3. **`rustup`'s component store wasn't in a volume.** `rust-toolchain.toml` declares `rustfmt`/`clippy`; the first container start downloaded `clippy` fresh. Assumed (wrongly) this was a one-time cost — a `--force-recreate` test proved it would repeat on every recreation, not just an image rebuild, since anything outside a volume lives in the container's disposable layer. Fixed with a fourth named volume (`cargo-rustup`), verified the fix by recreating again and confirming no re-download.
4. **`test-db` genuinely has no memory of anything** (tmpfs, by design — see Phase 1). Trying the on-demand `#[ignore]`d-test workflow for the first time (`cargo test -- --ignored remaining_active_admins_excluding`) failed with `relation "auth.roles" does not exist` — not a bug, just Phase 1's ephemeral guarantee working exactly as designed, but a real practical gap: nobody had actually exercised "bring up a fresh test-db and use it for a real-DB test" end to end until now. Wrote `scripts/bootstrap_test_db.sh` (wraps the same role-script/migrate/role-script sequence into one idempotent command), verified by re-running the previously-failing test — passed.

**Shipped**: `unitprep-api` `v1.9.43` → `v1.9.44` (4 commits: Phase 1's dev-container addition, the bootstrap script, then the version bump — plus the Phase 1 compose file itself landed as `v1.9.43` earlier this session before the teaching-pass conversation), all tagged and pushed.

## Vault updated

[[UnitPrep Docker Standards]] gained two Amendments entries (the cargo-chef/volume-shadowing interaction, the missing `cargo-rustup` volume) and an updated named-volumes list. [[UnitPrep CI-CD Framework]]'s phase table, status summary, Phase 4 row, and Redis section all updated. [[Key Decisions]] gained the Fly.io/multi-instance entry.

## Related

- [[Session 2026-09-28 (Part 4) — Tier 0 CI Tooling Built (cargo-audit, gitleaks) with Real RUSTSEC and npm-audit Fixes]] — same-day predecessor (previous calendar day), Docker Phase 1
- [[UnitPrep CI-CD Framework]] — Phase 2 status, Phase 4/Redis assumption updated this session
- [[UnitPrep Docker Standards]] — two new Amendments entries, this session's primary technical artifact
- [[Key Decisions]] — the Fly.io/multi-instance decision
- [[Patterns]] — the vault-push-batched-to-EOD refinement (set this session, before the Docker work began)
