---
date: "2026-09-28"
quarter: "Q3-2026"
description: "Implemented the Tier 2 trigger-review mixture (durable scheduled task, not the session-scoped CronCreate), then designed a full 5-phase containerization roadmap and a LAW-level Docker/Rust standards doc, and deferred Redis to the same trigger as production containers"
tags:
  - work-note
  - project/unitprep
  - ci-cd
  - docker
---

# Session 2026-09-28 (Part 3) — Containerization Plan, Docker/Rust Standards & Redis Deferral

Direct continuation of the same day's [[Session 2026-09-28 (Part 2) — Migration-Squash Alternative & CI-CD Framework Design|CI/CD framework session]]. Boris pushed back once, gently, on Claude jumping straight to *building* Tier 0 when he'd only asked to *discuss* CI — acknowledged directly, and the rest of this session deliberately separated "design/discuss" from "build" until explicitly told to build.

## Tier 2 trigger review: the durable mixture, actually implemented

Boris: "passive is ok for now... mixture of measures if that's a safer thing to do... as long as we're on top of it." Built:

- **Discovered and avoided a real trap**: `CronCreate` (the first tool reached for) is session-scoped and auto-expires after 7 days — would have silently stopped working and given false confidence, the exact opposite of "on top of it." Checked its actual documented behavior before using it rather than assuming a scheduling tool is automatically durable.
- **Used `mcp__scheduled-tasks__create_scheduled_task` instead** — genuinely disk-persisted (`C:\Users\bmaksimov\.claude\scheduled-tasks\`), survives across sessions. Created `unitprep-ci-tier2-review`, monthly (1st of the month), checks git-detectable triggers (dev branch existence, commit velocity, `.github/workflows/` appearance) and reminds Boris to self-assess the ones that aren't (second developer, real prod deployment, compliance requirement). Logs every run to a new Review Log table in [[UnitPrep CI-CD Framework]], so a silently-stopped task shows up as a visible gap rather than being assumed fine.
- **Passive layer**: [[Compliance & Process Readiness]]'s own stale "CI/CD explicitly deferred" framing corrected and cross-linked back to the framework doc — same staleness pattern already caught once in `brain/CI Backlog.md` earlier the same day, swept here too per this vault's own correction-sweep protocol.

## Containerization: a real phased plan, not a yes/no

Boris's framing shifted the whole calculus: time/token cost is irrelevant (company-paid), and he's explicitly taking the orchestrator role while Claude executes/debugs container tooling in future sessions — so the usual "will this slow the solo developer down day to day" argument doesn't land the way it would if Boris were the one running `docker compose up` by hand every day.

**Distinguished two different questions that are easy to conflate**: "Docker for a local throwaway test Postgres" (small, immediately justified, ties directly into the mission-critical test-isolation requirement from earlier the same day) versus "containerize the whole dev/prod workflow" (a much bigger commitment). Landed on a 5-phase plan:

1. DB-only compose (ephemeral local test Postgres) — in the pipeline now.
2. `unitprep-api` dev container — in the pipeline now.
3. `unitprep-ui` dev container — in the pipeline now.
4. Production-shaped multi-stage image — documented in full, execution deliberately gated on the same trigger as CI Tier 2 (a real multi-instance/deployment decision), not built now. Argued for consistency with Tier 2's own "dormant until a real trigger" logic rather than treating containers as a special case just because building them is now cheap — a point Boris didn't push back on, suggesting the consistency argument landed.
5. Full `docker compose up` for everything — documented, falls out naturally once 1-3 exist.

Full plan recorded in [[UnitPrep CI-CD Framework]]'s new "Containerization" section.

## `UnitPrep Docker Standards` — a new LAW-level reference doc

Boris's explicit words: "careful to the point of obsession," "the LAW," "never deviate," "flawless and spectacularly impressive to any pro dev looking at it in the future." Wrote [[UnitPrep Docker Standards]] to that standard — not generic Docker advice, but verified against this actual codebase first:

- **A real, load-bearing technical finding, checked before writing any recommendation**: `webauthn-rs` transitively pulls in real `openssl-sys` (for X.509 attestation certificate validation) even though `sqlx`/`reqwest` both correctly use `rustls`. This rules out a naive Alpine/musl build — the standards doc specifies Debian-family base images as the default, with the reasoning and the `vendored`-OpenSSL alternative both spelled out, rather than reaching for the smallest-possible-image advice generically found online and hitting this wall later.
- **`cargo-chef` for dependency-layer caching** (not a hand-rolled dummy-`main.rs` trick, which handles this project's 6-crate workspace poorly), **BuildKit cache mounts on top of it**, and — the single most important rule for dev containers specifically — **never rebuild the image per code change**: source bind-mounted, `cargo`/`target` as named volumes, a long-lived container running `cargo watch`. Getting this wrong would turn "containerize for parity" into "regress the exact iteration speed the whole CI framework exists to protect."
- Mirrored the same rigor for `unitprep-ui` (Next.js `output: "standalone"`, not yet set — a real gap found and recorded, not assumed), non-root users, `.dockerignore` (with an explicit callback to the real leaked-credential incident already in [[Gotchas]] — a Docker image layer is exactly as permanent and exactly as easy to leak as a git commit), and compose conventions (named volumes always, healthchecks, and an explicit restatement that the ephemeral test Postgres must never be configured anywhere near a real Neon credential — the mission-critical isolation requirement, extended to local Docker).
- Includes an **Amendments** section — any future deviation from the LAW gets recorded there with a date and reason, never silently.

## Redis: considered, deferred, tied to the same trigger as phase 4

Asked directly: "would introducing redis at this point be beneficial?" Answer grounded in the actual `DurableSessionStore` design from earlier this week: its hot path never leaves in-process memory, so Redis cannot improve the path that matters — it would only speed up the cold rehydration path (once per process lifetime, already cheap). Redis's real value (shared state across multiple processes) doesn't exist until there's more than one process, which is exactly the phase 4 / multi-instance question. Distinguished explicitly from the Docker decision: Docker phase 1 has a real payoff *today* regardless of anything else; Redis has none until the same trigger that gates phase 4 fires. Recorded as deferred-and-tied-to-that-trigger in [[Key Decisions]], not decided independently just because "cost doesn't matter" made it tempting to build anyway.

## Related

- [[Session 2026-09-28 (Part 2) — Migration-Squash Alternative & CI-CD Framework Design]] — same-day predecessor, the framework this session extends
- [[UnitPrep CI-CD Framework]] — the containerization phases and Tier 2 review-log mechanism, both added this session
- [[UnitPrep Docker Standards]] — the new LAW document, the primary technical artifact of this session
- [[Key Decisions]] — the containerization-as-investment and Redis-deferral decisions
- [[Compliance & Process Readiness]] — corrected cross-link
