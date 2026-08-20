---
date: 2026-07-27
description: Second CTO-grade pre-auth audit of UnitPrep — all 5 milestones resolved same session; real CORS bug found+fixed+browser-verified; npm audit findings tracked, not fixed.
tags: [work-note, unitprep]
status: completed
quarter: Q3-2026
project: unitprep
---

# Post-Refactor Audit (Second Pre-Auth Review)

Second full-codebase pre-auth CTO-grade audit, 2026-07-27, requested by Boris after the first review+refactor's 9 milestones landed. **Committed and shipped 2026-07-28** as v1.1.1 on both repos — see [[Post-Refactor Audit - Shipped as v1.1.1]] for the commit-by-commit breakdown. The `npm install`/`npm audit fix` follow-up was run by Boris directly; see the dependency findings section below for the (corrected) outcome.

See [[Post-Refactor Audit - Details]] for the full milestone-by-milestone technical breakdown (core/unit-group fixes, session ownership design, dedup correctness fixes, API/export hygiene, frontend DRY+splits, Rust dependency-audit specifics).

## Why this happened

Boris asked for a second full review pass after the prior review+refactor's 9 milestones landed, scored across 8 dimensions — elegance, bloat, coherence/splitting of line-heavy files, efficiency, performance, overengineering, future-readiness for the incoming auth work, and general optimization opportunities — explicitly framed as "make this hackathon-judge/CTO-impressive before we resume auth." Four parallel review agents (core+unit-group, dedup, api/session/export, frontend) each read every non-test source file in full; the highest-impact claims were then personally re-verified directly against the live code (not just trusting agent output) before reporting. Full findings were also published as an HTML artifact (may not remain accessible indefinitely — this note is the durable record): `https://claude.ai/code/artifact/83a1dfed-edcd-4995-af75-4ef4ec70f179`

## Verdict going in

Both repos built/tested/linted completely clean (`cargo test --workspace`, `cargo clippy --workspace --all-targets` net of 17 accepted auth-WIP warnings, `tsc --noEmit`, `eslint .`), and every fix from the prior refactor verified still in place at the code level, not just in commit messages. What was left was not new bugs — four repeating cross-cutting patterns plus per-crate polish.

## Cross-cutting themes

1. **Formatting was never mechanized** — no `rustfmt.toml` anywhere in `unitprep-api`; `cargo fmt --all -- --check` reported 808 diff hunks across 102 files workspace-wide. The "fragmented one-identifier-per-line" style flagged in prior reviews wasn't a deliberate house style — it was hand-typed AST, never run through a formatter.
2. **The prior refactor's own DRY helpers didn't reach every call site** — `ScanResultsPage.tsx` hand-rolled the exact pattern `useSessionPost` was built to replace; 3 `discovery/*` components (6 fetches) never migrated to `useSessionAction`; dedup's CSV/XLSX writers independently enumerated the same 25 fields; `csv_export.rs`'s 6 generators never got a shared-writer helper.
3. **Sessions have no owner** — `core::session::SessionMetadata` was exactly `{id, created_at, last_accessed}`, no owner field anywhere in the session stack. Auth will answer "who's calling" but nothing stopped that caller acting on someone else's `session_id`. A ~20-handler design decision, cheaper made once now than retrofitted per-handler later.
4. **Frontend has no single seam for auth-awareness** — no fetch wrapper, ~15 raw `fetch()` call sites, none set `credentials: "include"`, only 404 handled anywhere (no 401 branch existed at all). Closing #2 first shrinks this to ~6 sites before adding a wrapper.

## Status summary — all 5 milestones resolved 2026-07-27

Boris approved a 5-milestone follow-on plan (saved at `C:\Users\bmaksimov\.claude\plans\witty-enchanting-bird.md`) to close every outstanding item before resuming auth. Explicitly out of scope per Boris: load/perf benchmarking (queued as the *next* thing after this plan) and CI/GitHub Actions setup (neither repo has CI; not being added now).

- **Core & unit-group crates** — fully resolved: `cargo fmt` applied, several real efficiency fixes (removed unnecessary clones in `analyze_batch`, added a group-fingerprint cache, indexed `apply_corrections` instead of O(rows × corrections)), dead/duplicate type cleanup in `models.rs`, `core/Cargo.toml`'s `tokio` features narrowed. See details note.
- **M1 — Session ownership**: `SessionMetadata` gained `owner_id: Option<Uuid>`; new `with_owned_session`/`with_owned_session_mut` return `None` (not a distinct error) for both "missing" and "not yours," so a caller can't tell them apart. Both session-creating handlers currently pass `None` (no `AuthenticatedUser` exists yet) — wiring auth in later is "change `None` to `Some(user.id)` at 2 call sites," not a data-model change under pressure. Deliberately did **not** touch the ~20 existing handlers to call the new owned variant — that's the first step of auth-wiring itself, not this cleanup.
- **M2 — Dedup crate**: all 8 audit findings fixed with new regression tests (blank-vs-normalized-blank comparison bugs in 3 files, an address-join collapsing bug, a title-casing bug for names like O'Brien, a stale RULES.md line, a test-file split, a hoisted-out-of-loop redundant computation, plus a new full-pipeline synthetic test). See details note for the complete list.
- **M3 — API/session/export hygiene**: router-wide panic-catching middleware added; shared CSV-writer and dedup-field helpers added; a `DiscoverResponse::from` conversion replaced ~60 lines of hand-copying with ~15; `Session::effective_documents_for` added and wired into 3 call sites; `AnalysisResults` wrapped in `Arc` (refcount bump instead of deep clone); upload handler got its first test coverage (4 tests via real multipart requests); the remaining ~496 of 808 fmt hunks applied workspace-wide.
- **M4 — Frontend**: `ScanResultsPage.tsx`'s hand-rolled fetch replaced with `useSessionPost`; 3 discovery components migrated to `useSessionAction` (one fetch deliberately left hand-rolled — a real multipart file upload, not JSON); `credentials: "include"` + 401 handling added to the two shared hooks; two oversized components split into 4 new files; `deriveScanResults` memoized. Also found that the "2 custom ESLint rules" this project was said to need **already exist** as bundled defaults in `eslint-plugin-react-hooks@7.1.1` — a from-scratch custom plugin was written, verified correct, then deleted as redundant duplication.
- **M5 — Dependency audit + security review**: Rust side fully clean via `cargo-audit` (bumped `quick-xml`/`calamine` to fix 2 High-severity RustSec advisories reachable via uploaded files; documented one Medium `rsa` advisory as an accepted, non-reachable transitive-only finding via `.cargo/audit.toml`). Frontend `npm audit` findings tracked but not fixed — see below.

## Real bug found and fixed: CORS gap from the frontend credentials change

M4 added `credentials: "include"` to the two shared frontend fetch hooks, ahead of auth actually issuing cookies. Per the Fetch/CORS spec, a credentialed request's response is invisible to the browser unless the server responds with `Access-Control-Allow-Credentials: true` — **regardless of whether an actual cookie exists to send** — and the backend's `CorsLayer` didn't set this. Left as-is, every request through `useSessionPost`/`useSessionAction` would have started failing as a CORS violation the moment the frontend change landed.

Fixed: added `.allow_credentials(true)` to the `CorsLayer` in `src/api/mod.rs` (safe alongside the existing specific-origin allowlist, which credentialed CORS requires anyway — never a wildcard). **Verified empirically, not just by reading code**: started both the real backend (`cargo run`) and frontend (`next dev --webpack`) and drove an actual browser to a fake-session-id URL — the network tab confirmed the `OPTIONS` preflight returned 200, the `POST /validate` returned a normally-readable 404, and the page correctly rendered "Session Expired" with zero console errors. This is exactly the kind of runtime-only bug `tsc`/`eslint` cannot catch, and confirms cross-cutting theme #4 above is now genuinely closed, not just plumbed.

Other security-review findings from the M1-M4 diff: CSV/XLSX formula-injection sanitization (`sanitize_cell`) confirmed still called correctly in every consolidated export function after the refactors (verified by grep, not assumed); M1's session-ownership mechanism reviewed as an IDOR control — the design is correct, but it's confirmed to be **only the mechanism, not yet applied**: none of the ~20 real handlers call `with_owned_session` yet, so the actual IDOR gap (any caller can act on any session_id today) remains exactly as open as before this audit, unchanged, until auth wiring adds `AuthenticatedUser` to handlers; the new panic-catching middleware confirmed not to leak internals (real panic payload only goes to `tracing::error!`, HTTP response is the same generic 500 as elsewhere); no new user-input-handling surface was added that could introduce injection.

## Frontend dependency findings: tracked, not fixed — includes a corrected read

`npm audit` found 4 High-severity advisories: `next` (16.2.9), its own bundled `postcss`/`sharp`, plus `brace-expansion` (transitive, via `@typescript-eslint`).

**My first-pass conclusion was wrong, and got corrected once Boris actually ran the fix for real.** Original read: a `npm audit fix --dry-run` from this Windows session showed `next 16.2.9 => 16.2.12` in the "would change" list, which I wrongly concluded resolved all 4 findings since it was inside the existing `"^16.2.9"` semver range. **I never actually confirmed this by checking a post-fix audit — I should have.** The real fix wasn't run that session for an unrelated, still-valid reason: it would have swapped Linux-native optional binaries for Windows-native ones over the WSL UNC boundary.

**What actually happened when Boris ran it for real** (from his own WSL terminal, correctly bypassing the UNC-path risk): `npm install` → no changes (already at latest permitted by range). `npm audit fix` (no force) → changed 7 packages, but a following `npm audit` still listed `next` as vulnerable — because **16.2.12 was never a patched version for these CVEs, just the latest existing 16.2.x patch**; the stated vulnerable range (`9.3.4-canary.0 - 16.3.0-preview.7`) includes 16.2.12. **There is currently no non-breaking fix available** — a real Next.js patch (16.3.0 stable, or a backported 16.2.x release) apparently hasn't been published to the registry yet. `npm audit fix --force` offers to "fix" this by downgrading to `next@9.3.3` — a nonsensical, purely mechanical resolver artifact (7 major versions back) — **never take an audit-fix `--force` suggestion at face value; verify what it's actually proposing first.** Same story for `brace-expansion`, whose only non-force fix path is an `eslint` 9→10 major bump.

**Risk assessment done before deciding not to force anything**: grepped the real `unitprep-ui` source for the specific features these 9 Next.js CVEs target — zero `"use server"` (Server Actions), no `middleware.ts`, no custom server, no `next/image` usage, no `rewrites()` in `next.config.ts`. That rules out the attack vector for 6 of the 9 advisories outright. Combined with being a local dev-only server today (no public deployment, no auth yet), real exposure right now is low, though not zero — worth re-checking once this app is ever actually deployed, not urgent before then.

**Decision, agreed with Boris**: do not force-downgrade Next.js or force the eslint major bump. Leave both as accepted, tracked, currently-unfixable-without-worse-tradeoffs findings. Re-run `npm audit` periodically (or next time this repo is touched) to catch a real Next.js patch release when one ships; consider the eslint 9→10 bump only as part of a deliberate future ESLint major-version upgrade, not a security-driven rush.

## Master punch list — all 12 items done

All 12 items from the original prioritized punch list are resolved (fmt, session ownership, frontend fetch migration, credentials/401 wrapper + the CORS fix it required, the 8 dedup fixes, RULES.md update, upload test coverage, panic middleware, `analyze_batch` clone/cache fixes, backend duplication collapse, component splits + memoization, the ESLint-rules discovery). The only open item is Boris running `npm install`/`npm audit fix` himself, which he already did — see the dependency findings above for what that turned up. Full itemized list with resolution notes is in [[Post-Refactor Audit - Details]].

Also queued, not part of this plan, per Boris: a lightweight synthetic-data benchmark to empirically validate this audit's Big-O performance findings, scheduled right after this plan closes out, before resuming the auth work itself.

## Verification summary

After every milestone: `cargo test --workspace` (ended at 284 passing), `cargo clippy --workspace --all-targets` (17 accepted auth-WIP warnings throughout, zero new ones introduced), `cargo fmt --all -- --check` (0 diffs, whole workspace), `cargo audit` (0 findings), `tsc --noEmit` + `eslint .` clean across all of `unitprep-ui`.

Committed and pushed 2026-07-28 as v1.1.1 on both repos — see [[Post-Refactor Audit - Shipped as v1.1.1]].
