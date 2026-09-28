---
date: "2026-09-28"
description: "The full tiered CI/CD design for unitprep-api/unitprep-ui — what's built now (solo-dev local safeguards), what's designed but dormant (multi-dev remote CI), and why each piece is shaped the way it is. The living policy doc — follow it, don't re-derive it."
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

**Explicitly not in Tier 0**: `cargo-audit`/`npm audit` (dependency vulnerability scanning) and a real secrets-scanning tool (`gitleaks`) — both genuinely worth having, neither installed yet (would need a one-time setup: `cargo install cargo-audit` needs no sudo and can be added anytime; `gitleaks` needs a binary download). Tracked as the next concrete Tier-0 addition, not urgent.

## Tier 1 — Minimal remote CI (designed, not yet enabled)

**Status: designed, `.github/workflows/` not yet created in either repo.** The moment a workflow file is committed, it goes live on the next push — so this tier is a deliberate, explicit decision to make separately, not something to fall into by finishing the design.

The key move that reconciles "fast" with "thorough": **split by cost, not by repo.**

- **On every push to `main`** (cheap, seconds-to-low-tens-of-seconds even for Rust with proper caching): `cargo check --workspace --all-targets` (type-check only — no codegen, no linking, dramatically faster than `cargo test` or `cargo build`) + `cargo fmt --check` + `cargo clippy -- -D warnings`, and the UI's `tsc --noEmit` + `eslint`. This is a *backstop* for Tier 0, not a replacement — it exists to catch "forgot to run preflight" or "works on my machine," not to be the primary gate.
- **On a version-tag push only** (i.e., at actual release cadence — the same boundary this project already uses for "this is real, shippable work," not per-commit): the full, slower `cargo test --workspace` / `npx vitest run`. This naturally throttles the expensive gate to roughly the release cadence already established (tens of times a month, not 100+), without needing an artificial rule about which commits get the heavy treatment.
- **Caching**: `Swatinem/rust-cache` (purpose-built for Cargo, meaningfully better than generic `actions/cache` for incremental Rust builds) for the Rust job; standard `actions/setup-node` with its built-in npm cache for the UI job.
- **Path-filtered triggers**: a docs-only or vault-only commit shouldn't trigger either job at all (matches this project's own "no version bump for docs-only" convention — CI should mirror that same judgment).

## The ephemeral-Postgres trick — solves "DB tests in CI" without ever touching Neon

The single most valuable piece of outside knowledge to bring into this design: GitHub Actions supports **service containers** — a throwaway Postgres instance spun up fresh for the duration of one job, migrations replayed against it, tests run against *that*, then discarded. Zero Neon compute, zero shared state, zero risk to real data, and it means the real-DB integration tests this project already has (session durability, RLS shape, schema round-trips) *can* run in CI without the compute-budget fear that's been the whole reason to keep them manual. This isn't a future nice-to-have contingent on a second developer — it's available today and worth wiring in whenever Tier 1 gets turned on, entirely independent of the multi-dev question. The tests that genuinely need real external state (live Process Street API calls) stay manual regardless; the tests that only need *a* real Postgres, not *the* real Neon branch, move to the ephemeral container.

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
| 1 | Split fast/slow GH Actions, ephemeral-Postgres DB tests | Designed, not enabled |
| 2 | Branch protection, PR review, `dev` branch, scheduled scans | Designed, dormant until 2nd developer |
| — | `cargo-audit`/`gitleaks` tooling install | Next concrete Tier-0 addition, not urgent |

## Related

- [[Compliance & Process Readiness]] — the earlier governance-level deferral decision this framework gives actual shape to
- [[CI Backlog]] — specific pre-framework check ideas (generate-types drift), now slotting into the tiers above
- [[Gotchas]] — the version-bump-skipped mistake Tier 0's new check exists to catch, and the leaked-credential incident behind the secret-scan step
- [[Patterns]] — the `dev`-branch anticipation from 2026-07-23, and the "batch, don't checkpoint" commit cadence Tier 0/1's push-vs-tag split is built around
- [[Key Decisions]]
