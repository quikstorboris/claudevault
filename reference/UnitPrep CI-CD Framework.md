---
date: "2026-09-28"
description: "The full tiered CI/CD design for unitprep-api/unitprep-ui — what's built now (solo-dev local safeguards), what's designed but dormant (multi-dev remote CI), why each piece is shaped the way it is, and the mission-critical defense-in-depth controls guaranteeing tests never reach real Neon data. The living policy doc — follow it, don't re-derive it."
tags:
  - reference
  - unitprep
  - ci-cd
---

# UnitPrep CI/CD Framework

Prompted by CI/CD coming up in nearly every outside review of this codebase (most recently a CTO-level board assessment) without ever being properly designed — see [[Compliance & Process Readiness]] for the earlier, purely governance-level "CI/CD is deliberately deferred" decision this framework now supersedes with an actual shape, and [[CI Backlog]] for the specific check ideas that predate this doc and now slot into the tiers below.

**This is a framework, not a mandate to implement everything.** Tier 0 is built and should be used starting now. Tiers 1–2 are fully designed and ready to enable, but deliberately not turned on yet — see each tier's own "status" line. Building the *design* now, while the reasoning is fresh, is cheap; building the *infrastructure* before it's needed is exactly the kind of premature investment this project's own [[Dev Principles]] (#4, #7) warn against.

## The constraint that shapes everything else

Boris ships **100+ commits/month**, solo, on `main` directly (no branches, no PR gate — see [[Patterns]]'s branch-policy entry). A CI design that makes every one of those pushes wait on a slow Rust test suite is not a safety net, it's a tax that will get bypassed, resented, or will visibly throttle real shipping velocity to something like 10 commits/month — which is worse for quality, not better, since it pressures batching real work into fewer, larger, riskier pushes. **Every tier below is designed around "cheap and fast enough to never be worth skipping," not "as thorough as possible."**

The second constraint: Neon free-tier compute is scarce (93.5% of the monthly allowance used as of 2026-09-28 — see [[Session 2026-09-28 — client_ops Schema Split, Runbook, Live-DB Audit & CI Backlog]]). **Nothing in this framework may run automated, unattended queries against the real Neon dev branch.** This is solved architecturally, not just avoided — see the ephemeral-Postgres section below, which is the one piece of this design most worth understanding even if nothing else changes.

## Tier 0 — Local pre-flight (built, use starting now)

**Status: implemented.** `unitprep-api/scripts/preflight.sh` and `unitprep-ui/scripts/preflight.sh` — run before every push, not before every commit (matches this project's own "batch, don't checkpoint" commit cadence; gating on push, not commit, means the fast local edit-commit loop is never slowed down, only the moment code actually becomes shared).

Runs, in order, fast-fail:
1. **Format check** (`cargo fmt --check` / handled by `eslint` for the UI, which is already format-aware) — near-instant, catches the single most common "oops."
2. **Type/lint check** (`cargo clippy --workspace --all-targets -- -D warnings` / `tsc --noEmit` + `eslint .`) — fast, no test execution, catches the large majority of real mistakes before anything runs.
3. **Fast test suite** (`cargo test --workspace` / `npx vitest run`) — excludes anything `#[ignore]`d. Every real-DB integration test in `unitprep-api` is `#[ignore]`d specifically so this stays fast and never touches Neon; running those stays a deliberate, manual, pre-release action (`cargo test -- --ignored <name>`), never automatic.
4. **Version/tag consistency check** (new, closes a real mistake made this session — see [[Gotchas]]'s "a real-code-change batch can silently skip the version bump" entry): compares the manifest version (`Cargo.toml` / `package.json`) against the latest git tag. Warns if there are commits past the last tag with no version bump — the exact signature of the mistake that slipped through undetected for 6 commits.
5. **Secret-pattern scan** (grep-based today, not a dedicated tool — see "not yet installed" below) — a cheap, fast check for the shape of a leaked credential (a real incident already happened once, a cleartext DB password in a `.env.local` comment — see [[Gotchas]]). Not a substitute for `.gitignore` discipline, a last-line backstop.

**Not wired as an enforced git hook yet** — runnable manually (`./scripts/preflight.sh`) rather than auto-triggered on `git push`, so it can be adopted gradually and never silently blocks a push in a way that's confusing to debug. Worth revisiting once it's been run by hand enough times to trust it completely; a `pre-push` hook is a two-line addition once that trust exists.

**Built 2026-09-28** (see [[Session 2026-09-28 (Part 4) — Tier 0 CI Tooling Built (cargo-audit, gitleaks) with Real RUSTSEC and npm-audit Fixes]]): `cargo-audit` (via `cargo install`, no sudo) and `gitleaks` (user-local binary in `~/.local/bin`, no sudo) are now steps 4-5 of `unitprep-api`'s preflight (7 steps total) and step 5 of `unitprep-ui`'s (7 steps total) — diff-scoped to `merge-base(origin/main, HEAD)..HEAD`, blocking only on real findings (advisory-grade `unmaintained`/`yanked` `cargo audit` warnings print but don't fail). `unitprep-api` also has a `.gitleaks.toml` allowlisting 6 confirmed false positives in sanitized Process Street test fixtures. The first real runs found and fixed a medium RUSTSEC `rustls` advisory and a critical Next.js RCE. `npm audit --audit-level=high` was then also wired in as `unitprep-ui`'s preflight step 4/7 (same session day, follow-up chunk) — mirrors `cargo-audit`'s block-on-real/don't-block-on-triaged split: the 3 known moderate `@vitest/mocker` findings (needed a `vitest` 4→5 major bump) printed but didn't fail. **That bump landed the same day** (`v1.6.44`) — reassessed given zero production blast radius (dev-only test runner, never shipped) and done rather than carried as an open gap; `vite` was already compatible (8.1.5), `@types/node` bumped 20→24 to match vitest 5's peer requirement, `tsc`/`eslint`/full suite (669 tests)/coverage all verified clean before and after. `npm audit` is back to the full default (blocks on anything, no `--audit-level` override) and reports 0 vulnerabilities.

**Still not in Tier 0**: a real secrets-scanning tool beyond `gitleaks`'s default rules (e.g. `trufflehog`) hasn't been evaluated. Not urgent.

## Tier 1 — Minimal remote CI

**Status: built 2026-09-29**, `.github/workflows/ci.yml` in both repos (`unitprep-api` `v1.9.48`, `unitprep-ui` `v1.6.46`) — see [[Session 2026-09-29 (Part 3) — sqlx-test Rejected, GitHub Actions Tier 1 Workflow Built]]. All 6 isolation controls were true before this shipped (see the isolation-controls section above) — built as its own deliberate step, not fallen into.

The key move that reconciles "fast" with "thorough": **split by cost, not by repo.**

- **On every push to `main`** (cheap, seconds-to-low-tens-of-seconds even for Rust with proper caching): `cargo check --workspace --all-targets` (type-check only — no codegen, no linking, dramatically faster than `cargo test` or `cargo build`) + `cargo fmt --check` + `cargo clippy -- -D warnings`, and the UI's `tsc --noEmit` + `eslint`. This is a *backstop* for Tier 0, not a replacement — it exists to catch "forgot to run preflight" or "works on my machine," not to be the primary gate.
- **On a version-tag push only** (i.e., at actual release cadence — the same boundary this project already uses for "this is real, shippable work," not per-commit): the full, slower `cargo test --workspace` / `npx vitest run`, plus (`unitprep-api` only) the DB-only `#[ignore]`'d tests against the ephemeral Postgres service container (see below). This naturally throttles the expensive gate to roughly the release cadence already established (tens of times a month, not 100+), without needing an artificial rule about which commits get the heavy treatment.
- **Caching**: `Swatinem/rust-cache` (purpose-built for Cargo, meaningfully better than generic `actions/cache` for incremental Rust builds) for the Rust job; standard `actions/setup-node` with its built-in npm cache for the UI job.
- **Path-filtered triggers**: `paths-ignore: ['**.md']` in both — a docs-only commit doesn't trigger either job (matches this project's own "no version bump for docs-only" convention — CI mirrors that same judgment).
- **Verification note**: no `gh` CLI/token available in the session that built this, so both workflows were validated with `actionlint` (schema + embedded-shellcheck, both clean) and the underlying scripts tested locally against a real Postgres before wiring in.
- **Confirmed live, 2026-09-30** (see [[Session 2026-09-30 — First Live Tier 1 CI Run Verified Green]]): the `v1.9.48` tag push triggered `unitprep-api`'s `full-tests` job for real on GitHub's own runners — ephemeral `postgres:18` service container, all migrations replayed, `bootstrap_test_db.sh` ran unmodified against it (the same script Docker Phase 1 uses locally), full `cargo test --workspace` (654 passed, 0 failed, 35 intentionally-ignored) plus all 17 DB-only `#[ignore]`'d tests via the CI-only allowlist script — genuinely green end to end, closing the verification gap this line used to carry as **(TBC)**. `fast-checks` correctly did *not* run on this push — it's gated to non-tag pushes by design (isolation control intact, not a bug); still needs a plain non-tag commit to confirm that job fires too.

## The ephemeral-Postgres trick — solves "DB tests in CI" without ever touching Neon

The single most valuable piece of outside knowledge to bring into this design: GitHub Actions supports **service containers** — a throwaway Postgres instance spun up fresh for the duration of one job, migrations replayed against it, tests run against *that*, then discarded. Zero Neon compute, zero shared state, zero risk to real data, and it means the real-DB integration tests this project already has (session durability, RLS shape, schema round-trips) *can* run in CI without the compute-budget fear that's been the whole reason to keep them manual. This isn't a future nice-to-have contingent on a second developer — it's available today and worth wiring in whenever Tier 1 gets turned on, entirely independent of the multi-dev question. The tests that genuinely need real external state (live Process Street API calls) stay manual regardless; the tests that only need *a* real Postgres, not *the* real Neon branch, move to the ephemeral container.

### Isolation from real data — mission-critical, non-negotiable, defense in depth (2026-09-28)

**Boris's explicit framing**: any automated test run reaching the real Neon dev or prod branch and writing test data into it is a MAJOR no-no — a mission-critical requirement, not an ordinary design preference. Treated accordingly: no single control below is trusted alone. This is the same "defense in depth" posture this project already applies to auth (an app-level check *and* an RLS policy — see [[Dev Principles]] #8), extended to test infrastructure.

1. **Credential absence, not just credential discipline.** Any CI job that runs an automated test suite never receives `NEON_DEV_DATABASE_URL*` / `NEON_PROD_DATABASE_URL*` / `DATABASE_URL` as a secret at all. If the credential literally isn't present in that job's environment, no code path — buggy, copy-pasted, or misconfigured — can reach it. GitHub Actions "environments" can additionally gate which secrets are visible to which workflow, so this is enforceable at the platform level, not just by carefully-written YAML. **Built 2026-09-29**: `unitprep-api`'s `ci.yml` satisfies this by omission rather than an "environment" gate — no such secret is referenced anywhere in the workflow, so there's none for a gate to withhold in the first place. A GitHub "environment" gate remains a stronger, platform-enforced option worth adding if this workflow ever needs to reference *any* secret in the future.
2. **A distinct env var name for test connections, never reused from the app's real ones** — e.g. `TEST_DATABASE_URL`, pointed only at the ephemeral service-container Postgres. Any DB-touching test reads from this var and hard-fails (panics, never silently falls back to `DATABASE_URL`) if it's unset. The unsafe fallback pattern — "use the real one if the test one isn't set" — is exactly the shape of mistake this control exists to make structurally impossible, not just unlikely. **Built 2026-09-29** for the local/Docker case (`unitprep-api` `v1.9.47`, see [[Session 2026-09-29 (Part 2) — Grok Review Follow-Through, TEST_DATABASE_URL Isolation Control & a Real Postgres DO-Block Bug]]): `db::connect_test()` reads only `TEST_DATABASE_URL`, panics with a clear message if unset or malformed; all 24 `#[ignore]`d-test call sites across 12 files migrated off `db::connect()`/`DATABASE_URL`. Still not wired into any GitHub Actions workflow (Tier 1 itself remains dormant) — this closes the control for local dev per item 6 below, not for CI, which doesn't exist yet.
3. **A runtime guard inside the test harness itself, as a backstop against #1 and #2 both failing at once**: before any DB-touching test runs, assert the connected database is not a Neon host (check the connection string / `current_database()` against known Neon hostnames or project ids) and abort loudly if it is. **Built alongside #2, same commit**: `connect_test()` asserts the resolved host doesn't end in `.neon.tech`, verified empirically with a fake Neon-looking `TEST_DATABASE_URL` (rejected as designed).
4. **Two genuinely different categories of `#[ignore]`d test, never conflated**:
   - Tests needing *a* real Postgres, not *the* real data — schema shape, RLS enforcement, migration correctness, the session-durability round-trip tests already in this codebase. These are the ones that move to the ephemeral container.
   - Tests needing real *external* state — live Process Street API calls, real Dropbox folders. These can never run against a throwaway anything; they stay manual, deliberately triggered by a human, never wired into any automated job, regardless of how this framework's other tiers evolve.
   ~~Worth adopting sqlx's own `#[sqlx::test]` macro for the first category~~ — **checked and rejected, 2026-09-29** (see [[Session 2026-09-29 (Part 3) — sqlx-test Rejected, GitHub Actions Tier 1 Workflow Built]]): its `Testing` trait implementation is hardcoded to read plain `DATABASE_URL` (`dotenvy::var("DATABASE_URL")`, verified in both the pinned `0.8.6` and the latest `0.9.0` — a version bump doesn't fix it), and the attribute macro's own argument parser only accepts `fixtures`/`migrations`, no URL/env-var override at all. Adopting it would silently *undo* the `TEST_DATABASE_URL` isolation control this framework just built (`v1.9.47`) — it's not a neutral choice, it's an active regression for this specific project's constraint. `connect_test()` (built 2026-09-29) already provides the actual guarantee this line originally wanted; kept instead of the macro.
5. **The safe path has to be the default path, not an equally-easy alternative.** A new DB-touching test should reach for the ephemeral pattern by default; using real external state should require a specific, visible, justified reason — never the path of least resistance.
6. **Local development gets the same guarantee, not just CI.** A developer (or an AI agent working locally) running `#[ignore]`d tests by hand is exactly as capable of hitting real Neon as an automated job is — see the Docker discussion below for extending this protection to local dev, not just what runs remotely.

**Before Tier 1 is ever turned on**, every one of the 6 controls above should be true, not just the workflow YAML's use of a service container. A first Tier-1 PR that only adds the GitHub Actions workflow file without also making these guarantees structural (env var naming, the runtime guard — both built 2026-09-29, `connect_test()`) should be treated as incomplete, not shippable. (`#[sqlx::test]` adoption dropped from this list, 2026-09-29 — checked and rejected, see control #4 above.)

## Containerization — phased plan (2026-09-28)

Boris's framing: time/token cost is irrelevant here (company-paid, no schedule pressure) — the only real cost is his own attention and future maintenance burden, and he's explicitly taking on the "orchestrator" role while Claude executes/debugges the container tooling across future sessions. That changes the calculus from the CI tiers above (which are paced by *his* daily friction) to being paced by *genuine engineering payoff*, not urgency. All technical standards for every phase below are LAW, not suggestions — see [[UnitPrep Docker Standards]] for the full, non-negotiable technical detail (base image choices, caching strategy, security baseline). This section is the phased roadmap; that doc is the how.

| Phase | What | Status | Why this phase, why this order |
|---|---|---|---|
| 1. DB-only | `docker-compose.yml`, one `postgres:18` service (matches the real Neon version), for local ephemeral test isolation | **Built 2026-09-28** — see [[Session 2026-09-28 (Part 4) — Tier 0 CI Tooling Built (cargo-audit, gitleaks) with Real RUSTSEC and npm-audit Fixes]] | Already justified independent of everything else below — the local half of the mission-critical isolation requirement above. Zero impact on the existing native dev workflow otherwise. |
| 2. `unitprep-api` dev container | Long-lived container (not rebuilt per code change), source bind-mounted, `cargo` registry + `target/` as named volumes, `cargo watch` inside | **Built 2026-09-29**, `v1.9.44` — see [[Session 2026-09-29 — Docker Phases 2-3, cargo-chef Amendment & Fly.io Multi-Instance Decision]] | Environment parity + a genuine engineering exercise; must follow [[UnitPrep Docker Standards]]'s caching rules exactly or it becomes an iteration-speed regression instead of an improvement. |
| 3. `unitprep-ui` dev container | Same pattern — bind-mounted source, `node_modules`/`.next` as named volumes, `next dev` inside | **Built 2026-09-29**, `v1.6.45` — see [[Session 2026-09-29 — Docker Phases 2-3, cargo-chef Amendment & Fly.io Multi-Instance Decision]] | Same reasoning as phase 2, mirrored for the frontend. Unlike phase 2, `next dev` IS the live server, so its `HEALTHCHECK` (against `/api/health`) genuinely applies rather than being skipped. |
| 4. Production-shaped multi-stage image | Minimal runtime image (`debian:bookworm-slim` or `distroless`, given the `openssl-sys`/webauthn constraint documented in [[UnitPrep Docker Standards]]) for actual deployment | **Documented now, execution trigger-gated** | Same "dormant until a real trigger" logic as CI Tier 2 — deliberately kept consistent rather than special-cased for containers. **Target platform and topology assumption now decided (2026-09-29, see [[Key Decisions]]): Fly.io, designed assuming multiple machines from the start** — not designing against a guess anymore, just not building yet since there's still no real deployment to build against. |
| 5. Full `docker compose up` for everything | Combines 1-3 into one command | **Documented now, falls out naturally once 1-3 exist** | The "clone and run one command" onboarding win — real value once there's a second developer, negligible extra work once 1-3 already exist. |

**Maintenance note**: this table and [[UnitPrep Docker Standards]] both get updated as each phase actually ships — "documented now" must not silently calcify into stale planning once the phase either happens or gets explicitly re-deferred.

### Redis — a known future requirement, not built yet

Considered alongside Docker since `core/src/session_store.rs`'s own doc comment already anticipated it ("FUTURE: RedisSessionStore will implement this trait exactly as InMemorySessionStore does"). `DurableSessionStore`'s hot path never leaves in-process memory — Redis cannot improve on already-local-RAM access, so it would only speed up the cold rehydration path (once per session per process lifetime, already cheap). Redis's actual structural value — shared session cache and distributed rate limiting across multiple processes — only matters once there's more than one process.

**Updated 2026-09-29** (see [[Key Decisions]]): that's no longer an open "if" — Fly.io is the target host, and the standing assumption is now multiple machines from the start. So this is a **known, planned dependency, not a maybe** — the open question was timing, not whether. Still not built today: there's no second process yet to make it useful, and the existing `SessionStore` trait abstraction means implementing `RedisSessionStore` later is additive, not a rearchitecture, so there's no cost to waiting for phase 4 to actually become real. **Tied to the same trigger as phase 4** — revisit together, not separately.

## Tier 2 trigger conditions — dormant is a decision, not a default to drift into

Since Tier 2 is deliberately dormant rather than abandoned, these are the concrete conditions that should prompt an *active* decision about turning some part of it on — not something to silently notice six months late:

- A second developer (even part-time, even a contractor) starts touching either repo.
- A `dev` branch gets created for any reason — per [[Patterns]]'s 2026-07-23 anticipation of exactly this moment.
- A real production deployment (as opposed to just the current dev branch) becomes real — changes the blast radius of an untested change landing.
- Commit velocity drops sharply for a sustained period — could mean the "don't slow down 100+/month shipping" tradeoff this whole framework is built around no longer applies the same way.
- A compliance/audit requirement arrives that specifically names change-control or review process (see [[Compliance & Process Readiness]]).
- Any of the isolation controls above get bypassed, fail, or reveal a real near-miss — a signal the framework needs to mature faster than planned, not proof it's working as designed.

**Mechanism for noticing** (decided 2026-09-28, Boris's call — "passive is fine, mixture if safer, as long as we're on top of it"): a mixture, layered so no single piece has to work perfectly —
1. **Passive, durable**: this doc plus [[Compliance & Process Readiness]] both carry the trigger list and cross-link each other, so either one being read (which the vault's own SessionStart hook already surfaces for active work) resurfaces the other.
2. **Active, durable**: a monthly scheduled task (`unitprep-ci-tier2-review`, `mcp__scheduled-tasks`, not the session-scoped `CronCreate` — that one auto-expires in 7 days and would have silently stopped working) checks the mechanically-checkable triggers (does a `dev` branch exist yet? commit velocity vs. the ~100/month baseline? has `.github/workflows/` appeared?) and reminds Boris to self-assess the ones that aren't git-detectable (a second developer, a real production deployment, a compliance requirement). Logs one line below every run, so a silently-stopped task is visible (a gap in the log), not just assumed to still be running.

## Review Log

One line per monthly check — a gap here is the tell that the scheduled task stopped running, not a reason to assume everything's still fine.

| Date | Dev branch exists? | Commits (trailing 30d, api / ui) | `.github/workflows/` present? | Notes |
|---|---|---|---|---|
| 2026-09-28 | No | — (framework just created) | No | Baseline entry, framework just established. |

## Tier 2 — Multi-dev framework (designed, dormant until a second developer)

**Status: fully designed, zero infrastructure exists, not needed yet.**

- A `dev` branch, introduced explicitly when this tier actually activates — already anticipated in [[Patterns]]'s branch-policy entry from 2026-07-23 ("Boris will introduce a `dev` branch himself, explicitly, when the project starts considering CI/CD 'waaaay down the line'"). This is that moment's design, not its trigger.
- Branch protection on `main`: require Tier 1's checks to pass before merge, once merges (not direct pushes) are how code lands.
- At least 1 required PR review before merge.
- The ephemeral-Postgres-backed full integration suite becomes a *required* check, not advisory.
- A `CODEOWNERS` file once there's more than one owner to route review to.
- Scheduled (not per-push) `cargo audit`/`npm audit` + `gitleaks` — weekly cadence is plenty; these don't need to gate any individual change.

## Explicitly out of scope, not on any tier's near-term list

Cross-repo type-generation drift enforcement (tracked separately in [[CI Backlog]] as its own item, since it needs both repos checked out together — a different shape of problem than anything above), full Playwright E2E in CI, any deployment automation (no real production deployment exists yet to automate against).

## Status summary

| Tier | What | Status |
|---|---|---|
| 0 | Local pre-flight scripts | **Built** — `scripts/preflight.sh` in both repos |
| 1 | Split fast/slow GH Actions, ephemeral-Postgres DB tests | **Built 2026-09-29, confirmed live 2026-09-30** (`unitprep-api` `full-tests` job green on the real `v1.9.48` tag push) — all 6 isolation controls were true first |
| 2 | Branch protection, PR review, `dev` branch, scheduled scans | Designed, dormant until 2nd developer |
| — | `cargo-audit`/`gitleaks`/`npm audit` tooling install | **Built 2026-09-28** — all wired into preflight in both repos |
| Docker 1 | Local ephemeral-DB compose (`docker-compose.yml`, `postgres:18`) | **Built 2026-09-28**, `unitprep-api` `v1.9.43` — verified empirically (up/healthy/connect/down, zero volumes left) |
| Docker 2 | `unitprep-api` dev container | **Built 2026-09-29**, `v1.9.44` — verified empirically (bind-mount live-edit, cargo-watch, on-demand server + port-forward, on-demand `#[ignore]`d test against `test-db`) |
| Docker 3 | `unitprep-ui` dev container | **Built 2026-09-29**, `v1.6.45` — verified empirically (bind-mount live-edit via an injected syntax error, `npm ci`-at-start + volume reuse, port-forward) |
| Docker 4-5 | Production image, full compose orchestration | Documented, execution gated on the same trigger as CI Tier 2 |
| Redis | Session-store backend option | Documented, deferred, tied to the Docker phase 4 trigger |

## Related

- [[Compliance & Process Readiness]] — the earlier governance-level deferral decision this framework gives actual shape to
- [[CI Backlog]] — specific pre-framework check ideas (generate-types drift), now slotting into the tiers above
- [[UnitPrep Docker Standards]] — the non-negotiable technical LAW for every Docker artifact this project produces, referenced by the containerization phases above
- [[Gotchas]] — the version-bump-skipped mistake Tier 0's new check exists to catch, and the leaked-credential incident behind the secret-scan step
- [[Patterns]] — the `dev`-branch anticipation from 2026-07-23, and the "batch, don't checkpoint" commit cadence Tier 0/1's push-vs-tag split is built around
- [[Key Decisions]]
- [[Session 2026-09-28 (Part 4) — Tier 0 CI Tooling Built (cargo-audit, gitleaks) with Real RUSTSEC and npm-audit Fixes]] — built this framework's last flagged Tier-0 gap, fixed the real RUSTSEC/npm-audit findings it surfaced
