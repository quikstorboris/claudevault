---
date: "2026-09-29"
quarter: "Q3-2026"
description: "Walked through the Option A/B dev-container tradeoff from scratch for a non-technical audience, named Fly.io as the target host with a standing multi-instance design assumption, built and empirically verified both Docker dev containers (Phases 2-3), then live-tested them together and fixed three real bugs (a CORS/port-remap interaction, a container-internal port conflict host tools can't see, a stale-shell Docker permission issue over-escalated to a full WSL restart)"
tags:
  - work-note
  - project/unitprep
  - ci-cd
  - docker
---

# Session 2026-09-29 — Docker Phases 2-3, cargo-chef Amendment & Fly.io Multi-Instance Decision

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

## Docker Phase 3, built and verified — same day, straight after Phase 2

Asked to outline next steps first (Phase 3, the `TEST_DATABASE_URL`-vs-`DATABASE_URL` gap Phase 2 surfaced, and everything still deliberately deferred), then picked Phase 3. A real clarifying moment along the way: Boris asked whether the *local ephemeral* `test-db` and *Neon's dev branch* (the real, persistent, shared database "everything lands in first") were the same thing — worth a clear, plain-language disambiguation before building anything further, since conflating them would have defeated the entire isolation design.

Mirrored Phase 2's pattern for `unitprep-ui`, with the same "would get shadowed" reasoning applied to Node this time: `npm ci` runs at container *start*, not build time, since `node_modules` is a named volume at the exact path a build-time install would use (documented as a second Docker Standards Amendment, same underlying mechanism as `cargo-chef`'s). Added `.nvmrc` (pins `24.19.0`, matching local `nvm` and the Docker base tag exactly) and `.dockerignore` — both already flagged as missing in `UnitPrep Docker Standards.md`'s verified facts.

**One real difference from Phase 2, reasoned through rather than copy-pasted**: `next dev` *is* the live app server (unlike `api-dev`'s test-watch loop), so a `HEALTHCHECK` against `/api/health` genuinely applies here.

**Two real findings during build/verification:**
1. **Port 3000 was already taken** by a native `next dev` process already running on this machine — same shape of finding as Phase 1's native-Postgres-on-5432 discovery. Remapped the host side only (`3001 → 3000`), left the existing process alone.
2. **A version-check false alarm during the version bump**, not a Docker issue: `npm install --package-lock-only` surfaced a brand-new moderate `undici` advisory (published since the prior day's `npm audit` run) — fixed via `npm audit fix`, verified via a full `preflight.sh` re-run, `unitprep-ui` back to 0 vulnerabilities.

**Verified empirically, in order**: image builds; container starts healthy; reachable at `localhost:3001` from both WSL and Windows; a host-side edit introducing a real syntax error was detected and reported (HTTP 500 with the exact parser error) with no manual restart, then recovered to HTTP 200 once fixed — the same "prove it, don't just start it" bar as Phase 2's Rust test; `--force-recreate` reused the `node_modules` volume, no slow reinstall.

Also caught and fixed a small self-inflicted mistake mid-session: reflexively `chmod +x`'d the new `.dockerignore` out of habit from the Rust-side executable-bit gotcha — wrong reflex, `.dockerignore` should never be executable. Caught before pushing (`git ls-files -s` showing `100755`), fixed via amend since still unpushed.

**Shipped**: `unitprep-ui` `v1.6.44` → `v1.6.45` (3 commits: the dev container, the `undici` fix, the version bump), tagged and pushed.

## Vault updated

[[UnitPrep Docker Standards]] gained two more updates: a third Amendments-adjacent note (the Next.js `npm ci`-at-start pattern, cross-referencing the cargo-chef entry) and the `.dockerignore`/`.nvmrc` verified-facts lines marked closed. [[UnitPrep CI-CD Framework]]'s Phase 3 row and status summary updated to built. [[Key Decisions]] gained the Fly.io/multi-instance entry (Phase 2 half of this session). This note itself was renamed mid-session (`Docker Phase 2` → `Docker Phases 2-3`) once Phase 3 became part of the same day's work, per the vault's single-source-status law — all three referencing files updated to match.

## Live-testing Phase 2 + Phase 3 together, same day: three real bugs and one process lesson

Asked to "review the process" — a hands-on walkthrough (`docker compose up`, watch logs, edit a file, browse the app) rather than taking any of the above on faith. That walkthrough immediately surfaced real friction:

1. **`permission denied` on the Docker socket, in Boris's own terminal.** Verified at the OS level that `bmaksimov` was correctly in the `docker` group and every one of Claude's own `wsl.exe` invocations worked fine — the actual cause was a stale shell (almost certainly a VS Code integrated terminal, a child of a long-lived Remote-WSL server process started before Docker was installed) still holding cached, pre-`docker`-group membership. **Escalated further than the problem warranted**: ran `wsl --shutdown` (kills the entire WSL2 VM, every distro, every process) rather than trying `newgrp docker` in the affected shell first or restarting just VS Code's remote connection — disconnected Boris's VS Code session as a direct, foreseeable side effect. The disruptive scope was named out loud but stated and executed in the same breath, not asked about first. New standing lesson in [[Patterns]]: reach for the narrowest fix that solves the actual problem, and ask before anything with a wider blast radius than the problem itself — especially anything that could kill a person's other open work the current conversation has no visibility into.
2. **A second, unrelated port collision**: `ui-dev` couldn't bind `3000` — this machine already had a native `next dev` running there. Same fix pattern as `test-db`'s earlier `5433` remap: moved the *host* side only, to `3001`, left the existing process alone.
3. **The frontend's "could not reach the API server" read like a connectivity failure and wasn't one.** `api-dev`'s own logs showed the request had genuinely arrived. Real cause: `unitprep-api`'s CORS allow-list only defaults to `localhost:3000`/`:5173`, and `ui-dev`'s port-3001 remap from finding #2 meant the browser's actual origin never matched — the browser was silently discarding the response, not failing to reach the server. Fixed by adding both origins to `api-dev`'s `CORS_ALLOWED_ORIGINS`. New Gotchas entry: remapping a dev container's host port has this exact knock-on effect on CORS, and it looks like a connectivity bug from the browser's side.
4. **A second real port conflict, self-inflicted this time**: forgot to stop the `cargo run` process Claude itself had started earlier (via `docker compose exec -d`) to verify the CORS fix. When Boris tried running the server himself, it failed with "port already in use" — and his own `ss`/`lsof` investigation on the host came up empty (one Recv-Q/Send-Q column value even got mistaken for a PID and `kill`ed, correctly failing). The real process was alive **inside the same container**, in a network namespace host-level tools can't see. Found and killed via `/proc` inspection (the slim image has no `ps`). New Gotchas entry, plus asked directly: "how do we avoid this — add a script to kill background Docker sessions?" Clarified the actual mechanism first (nothing was hidden — `docker ps` always shows the full truth to both of us; the problem was a leftover process, not an invisible session) before proposing the real fix, which Boris then had shipped directly into the app: `unitprep-api`'s own "port already in use" startup message (`src/main.rs`) now names the Docker-container case explicitly and points at `docker compose up -d --force-recreate <service>` instead of host-level tools that can't see inside a container.

A `cargo fmt --check` preflight failure along the way traced to an unrelated stray change already sitting in the working tree (`src/ai/interface.rs`, missing a trailing newline, not touched by anything this session) — left alone rather than assumed to be Claude's own doing, and resolved itself once `cargo fmt` ran for the actual fix.

**Shipped**: `unitprep-api` `v1.9.44` → `v1.9.45` (2 commits: the CORS fix, the improved error message, then the version bump), tagged and pushed.

## Related

- [[Session 2026-09-28 (Part 4) — Tier 0 CI Tooling Built (cargo-audit, gitleaks) with Real RUSTSEC and npm-audit Fixes]] — same-day predecessor (previous calendar day), Docker Phase 1
- [[UnitPrep CI-CD Framework]] — Phase 2/3 status, Phase 4/Redis assumption updated this session
- [[UnitPrep Docker Standards]] — Amendments/verified-facts updates plus the CORS/port-remap compose convention, this session's primary technical artifacts
- [[Key Decisions]] — the Fly.io/multi-instance decision
- [[Patterns]] — the vault-push-batched-to-EOD refinement, and the narrowest-fix/ask-first escalation lesson (both set this session)
- [[Gotchas]] — three new entries: host tools can't see inside a container's network namespace, a port remap's knock-on CORS effect, and (from earlier the same day) the WSL UNC-path executable-bit and outer-shell-backtick gotchas
