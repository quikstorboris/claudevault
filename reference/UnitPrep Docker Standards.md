---
date: "2026-09-28"
description: "The non-negotiable technical standard for every Docker/container artifact in unitprep-api and unitprep-ui — Rust build optimization, Next.js build optimization, dev-container pattern, production image pattern, security. LAW, not a suggestion — never deviate without recording why here first."
tags:
  - reference
  - unitprep
  - ci-cd
  - docker
---

# UnitPrep Docker Standards

**Status: LAW.** Boris's explicit framing (2026-09-28): "we should be careful to the point of obsession... it must be flawless and spectacularly impressive to any pro dev looking at it in the future." Every rule below is binding on every Docker artifact this project ever produces — a Dockerfile, a compose file, a CI workflow step that builds an image. If a future session needs to deviate from something here, that's a decision to record in this doc's own Amendments section, not a silent exception.

This is a living document — update it as containerization phases 2-5 (see [[UnitPrep CI-CD Framework]]) actually get built, so it always describes what's real, not just what was planned.

## Verified facts about this codebase, checked 2026-09-28 (don't re-derive, don't assume otherwise without re-checking)

- **Rust toolchain pinned**: `rust-toolchain.toml` already exists, `channel = "1.96.0"`, components `rustfmt`/`clippy`. Every Docker build stage must use this exact version, not `rust:latest` or an unpinned tag — matching what local dev already runs is the whole point.
- **TLS backend is `rustls` everywhere it's a choice** (`sqlx` → `tls-rustls`, `reqwest` → `rustls-tls`) — correct, no OpenSSL needed for either.
- **BUT: `webauthn-rs` transitively pulls in real `openssl-sys`** (via `webauthn-attestation-ca`, for X.509 attestation certificate validation — a genuine cryptographic need, not a lazy default). **This rules out a trivial Alpine/musl build** — `openssl-sys` needs a real OpenSSL, either the system one (easy on Debian, painful on Alpine/musl without extra work) or Cargo's `vendored` feature (builds and statically links OpenSSL itself — possible, adds build time, worth revisiting once phase 4 is real). **Base image family is Debian, not Alpine, until this is deliberately revisited** — don't reach for `alpine`/`scratch` without first solving the `openssl-sys` question explicitly.
- **`unitprep-ui`'s `next.config.ts` does not yet set `output: "standalone"`** — required for the minimal-runtime-image pattern below. Not yet added; phase 3 needs to add it.
- **Neither repo has a `.dockerignore` yet** — needed before any Docker build to keep the build context small and fast (exclude `target/`, `.git/`, `node_modules/`, `.next/`).
- **`unitprep-ui` has no `.nvmrc`/`package.json` `engines` field pinning a Node version** — should be added alongside containerization so the Docker image's Node version and local dev's `nvm`-selected version are provably the same, mirroring the Rust toolchain pin.
- **Real Postgres version in use: 18.6** (confirmed via `pg_dump`'s own header when generating `SCHEMA.sql`) — the local ephemeral test container (phase 1) should match this, not default to whatever tag happens to be `latest` at build time.
- **Public, unauthenticated health endpoint**: `GET /health` (`unitprep-api/src/api/router/routes.rs`) — use this for every container's `HEALTHCHECK` instruction and compose `healthcheck:` block.
- **Workspace has 6 member crates** (`core`, `unit-group`, `dedup`, `template-tagger`, `docx-surgeon`, `tagger-pipeline`) plus the root binary — any dependency-caching strategy must handle the whole workspace correctly, not just the root crate (rules out naive single-crate "dummy main.rs" tricks; `cargo-chef` handles workspaces correctly, see below).

## Rust build optimization — non-negotiable technique stack

Applies to any Dockerfile that builds `unitprep-api`, whether a dev-container image or a production image.

1. **`cargo-chef` for dependency-layer caching**, not a hand-rolled dummy-`main.rs` trick. Hand-rolled tricks are fragile across a multi-crate workspace (this one has 6 members) — `cargo-chef` computes a proper recipe covering the whole workspace's dependency graph. Standard three-stage pattern:
   ```dockerfile
   FROM rust:1.96.0-slim-bookworm AS chef
   RUN cargo install cargo-chef
   WORKDIR /app

   FROM chef AS planner
   COPY . .
   RUN cargo chef prepare --recipe-path recipe.json

   FROM chef AS builder
   COPY --from=planner /app/recipe.json recipe.json
   RUN cargo chef cook --release --recipe-path recipe.json
   COPY . .
   RUN cargo build --release --bin unitprep
   ```
   The `cook` step only reruns (and only recompiles dependencies) when `recipe.json` changes — i.e., when `Cargo.toml`/`Cargo.lock` actually change, not on every source edit.
2. **BuildKit cache mounts on top of `cargo-chef`, not instead of it** — `RUN --mount=type=cache,target=/usr/local/cargo/registry --mount=type=cache,target=/app/target cargo chef cook ...` persists the registry and target directory *across separate builds*, not just within layers of one build. Requires `# syntax=docker/dockerfile:1` at the top of the Dockerfile and BuildKit enabled (default in modern Docker, confirm with `docker buildx version`).
3. **For dev containers (phases 2-3) specifically — don't rebuild the image per code change at all.** This is the single most important rule for keeping the "100+ commits/month, don't slow shipping down" constraint (see [[UnitPrep CI-CD Framework]]) true inside a container too:
   - The image itself only needs the toolchain installed — built once, rebuilt rarely (only when `rust-toolchain.toml` or system deps change).
   - Source code is **bind-mounted** from the host, never `COPY`'d into a dev image.
   - `~/.cargo/registry`, `~/.cargo/git`, and `target/` are **named volumes**, declared explicitly in compose (not anonymous — anonymous volumes are hard to inspect/prune deliberately and easy to lose track of).
   - Run `cargo watch -x check` (or `-x "test --workspace"` for a slower but more thorough loop) inside the long-lived container, or just `docker exec` in for ad hoc commands — the container behaves like a remote shell with the right toolchain pre-installed, not a build artifact that gets thrown away and rebuilt.
4. **Multi-stage separation of build vs. runtime is mandatory for any image meant to actually run the app** (production, phase 4) — never ship the `rust:*` build image itself; the final stage copies only the compiled binary into a minimal runtime base.
5. **Runtime base image, given the `openssl-sys` constraint above**: `debian:bookworm-slim` (simplest, correct, includes glibc) as the default; `gcr.io/distroless/cc-debian12` (smaller, no shell, more secure — the more "pro-grade impressive" choice) as the target once the OpenSSL linking question is explicitly resolved (either install `libssl3`/`ca-certificates` in that runtime stage for dynamic linking, or switch to `openssl/vendored` for a fully static binary that needs neither). Record whichever gets chosen, and why, in this doc's Amendments section when phase 4 actually happens — don't leave it implicit in a Dockerfile comment only.
6. **Non-root user in every runtime image** — `RUN useradd -m -u 10001 unitprep` and `USER unitprep` before the final `ENTRYPOINT`. This project already applies least-privilege everywhere else (`app_service`'s narrow DB grants, column-level restrictions — see [[Dev Principles]] #9); the container should hold the same line.
7. **`HEALTHCHECK` instruction** hitting the real, public, unauthenticated `GET /health` endpoint.

## Next.js build optimization

Applies to `unitprep-ui`'s Dockerfile (phase 3).

1. **`output: "standalone"` in `next.config.ts`** — not yet set (see Verified Facts above); must be added as part of phase 3, not assumed. Produces a minimal, self-contained `.next/standalone` output that doesn't need the full `node_modules` tree copied into the runtime image.
2. **Multi-stage build mirroring the official Next.js Docker pattern**: a `deps` stage installs dependencies with a BuildKit cache mount over `~/.npm` (`RUN --mount=type=cache,target=/root/.npm npm ci`), a `builder` stage runs `next build` against those deps, a minimal `runner` stage copies only `.next/standalone`, `.next/static`, and `public/` — never the full source tree or `node_modules`.
3. **Node version pinned and matched** — add `.nvmrc` (or `package.json` `engines.node`) to the repo first (currently missing, see Verified Facts), then use the exact same version as the Docker base image tag (`node:<version>-slim`).
4. **Dev container (phase 3), same "don't rebuild per change" rule as Rust** — bind-mount source, named volumes for `node_modules` and `.next` (the Next.js build cache — losing this on every container restart makes rebuilds dramatically slower), run `next dev` inside the long-lived container.
5. **Non-root user** in the runner stage, same reasoning as Rust.

## `.dockerignore` — required in both repos before any build

At minimum: `target/`, `.git/`, `node_modules/`, `.next/`, `*.md` (except where a Dockerfile `COPY`'s one intentionally), `.env.local`, any local scratch/test artifacts. **`.env.local` must never be copyable into a build context or an image layer** — this is the same discipline as the real leaked-credential incident already in [[Gotchas]]; a Docker image layer is just as permanent and just as easy to accidentally publish as a git commit.

## Compose orchestration conventions

1. **Named volumes, always** — `cargo-registry`, `cargo-git`, `api-target`, `ui-node-modules`, `ui-next-cache`, `local-test-pgdata` (if the ephemeral test Postgres is ever configured to persist between runs, which phase 1's actual test use case should NOT do — see below). Never anonymous volumes.
2. **`healthcheck:` + `depends_on: condition: service_healthy`** for correct startup ordering — e.g., `unitprep-api`'s dev container should wait for the local Postgres service to report healthy before starting, not just "container started" (which doesn't mean "accepting connections yet").
3. **Compose profiles or separate files for distinct purposes, never one file trying to do everything**: a `test` profile/service for the ephemeral, always-fresh Postgres (phase 1 — this one should NOT use a persistent named volume for its data directory; it's supposed to be thrown away, that's the entire point of the mission-critical isolation requirement in [[UnitPrep CI-CD Framework]]) versus a `dev` profile for the long-lived dev containers (phases 2-3, which DO want persistent volumes for cache/registry/node_modules, just not for app data).
4. **Secrets never in compose YAML or an image layer.** Local dev credentials (if the ephemeral test setup ever needs any beyond a throwaway local Postgres password) come from `.env.local` at the compose `env_file:` level, never hardcoded in `docker-compose.yml` itself, and `docker-compose.yml` itself is safe to commit while `.env.local` never is (already true today, unchanged by adding Docker).
5. **The ephemeral test Postgres container must never be reachable by, or configured to look anything like, the real Neon connection.** No service in any compose file should ever read `NEON_DEV_DATABASE_URL*`/`NEON_PROD_DATABASE_URL*` — see [[UnitPrep CI-CD Framework]]'s isolation-controls section, control #1 (credential absence), which applies to local Docker exactly as much as it applies to CI.

## Security baseline (every image, every stage)

- Non-root user in every runtime image (stated above, repeated here as the security-specific reason: a container escape or RCE inside a root-user container is categorically worse).
- No secrets baked into any layer — use BuildKit secret mounts (`--mount=type=secret`) for anything a build step genuinely needs at build time (rare for this project; most config is runtime env, not build-time).
- `.dockerignore` excludes `.env.local` unconditionally (stated above, repeated here for the same reason).
- Once Tier 1 of the CI/CD framework is live, image scanning (`docker scout` or `trivy`) belongs in that pipeline, not as a manual step — tracked in [[CI Backlog]] if it doesn't already have a home by the time Tier 1 gets built.

## Amendments

Record any deliberate deviation from the rules above here, with the date and why — never silently.

- *(none yet)*

## Related

- [[UnitPrep CI-CD Framework]] — the phased containerization plan (phases 1-5) this doc is the technical standard for
- [[Gotchas]] — the real leaked-credential incident behind the `.env.local`/`.dockerignore` rule
- [[Dev Principles]] — #9 (least privilege) behind the non-root-user rule, #12 (verify empirically) behind this doc's own "verified facts" section
- [[Key Decisions]] — the Debian-over-Alpine base image decision, the Redis deferral
