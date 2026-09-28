---
date: "2026-09-28"
quarter: "Q3-2026"
description: "Built the last Tier-0 gap the CI/CD framework doc flagged (cargo-audit, gitleaks), wired into both repos' preflight.sh, and fixed every real finding the first runs surfaced: a medium RUSTSEC rustls advisory and a critical Next.js RCE"
tags:
  - work-note
  - project/unitprep
  - ci-cd
---

# Session 2026-09-28 (Part 4) — Tier 0 CI Tooling Built (cargo-audit, gitleaks) with Real RUSTSEC and npm-audit Fixes

Same-day continuation of [[Session 2026-09-28 (Part 2) — Migration-Squash Alternative & CI-CD Framework Design|Part 2]] and [[Session 2026-09-28 (Part 3) — Containerization Plan, Docker-Rust Standards & Redis Deferral|Part 3]], run from a **Windows Claude Code session** reaching into the real repos over `wsl.exe` (per this vault's own STRICT rule: `unitprep-api`/`unitprep-ui` exist only in WSL, never trust a Windows clone). Boris first asked to review the CI/Docker plans (no build), then asked for a recommendation on introducing a `dev` branch (answered: not yet — no second developer, no branch protection to make it more than ceremony), then explicitly asked to start building in small, empirically-testable chunks. Given a choice of three candidate first chunks (Docker phase 1, Tier-0 tooling gaps, Docker prerequisites), Boris picked **Tier-0 tooling gaps**: install `cargo-audit` and `gitleaks`, wire into `preflight.sh`.

## What shipped

**`unitprep-api` → `v1.9.42`** (3 commits, tagged, pushed):
1. `Fix RUSTSEC-2026-0285 by updating rustls` — the first `cargo audit` run against this codebase ever found a real, medium-severity vulnerability (TLS 1.3 handshake messages incorrectly accepted across encryption level boundaries). `rustls` is transitive (via `reqwest`/`sqlx`, not pinned directly), so `cargo update -p rustls` (0.23.42 → 0.23.45) was the whole fix. Full workspace test suite reconfirmed green after.
2. `Add cargo-audit and gitleaks to Tier 0 preflight` — new preflight steps 4/7 and 5/7. `cargo audit` blocks only on real vulnerabilities (confirmed empirically: exits 0 when only `unmaintained`/`yanked` advisory warnings remain). `gitleaks` is diff-scoped (`merge-base(origin/main, HEAD)..HEAD`, same scope the grep backstop already used) so it never re-scans history on every push. A full-history scan (`gitleaks git --log-opts='--all'`) found 6 hits, all in `src/clients/testdata/highway20_*.json` — verified as false positives (synthetic Process Street workflow/task IDs sitting next to a `"key"` field trip the `generic-api-key` entropy rule) by reading the actual file content, not assumed. Allowlisted narrowly in a new `.gitleaks.toml`, scoped to those two files, not the whole `testdata/` directory.
3. `Bump version to 1.9.42`.

Two advisory-grade `cargo audit` warnings left open, correctly non-blocking: `bincode 1.3.3` (unmaintained, direct dep) and `chacha20 0.10.1` (yanked, transitive via `printpdf`→`lopdf`→`rand` — unrelated to the app's actual ChaCha20-Poly1305 encryption code for Dropbox credentials).

**`unitprep-ui` → `v1.6.42`** (3 commits, tagged, pushed):
1. `Add gitleaks to Tier 0 preflight` — new preflight step 4/6, same diff-scoping. Full-history scan found zero leaks; no allowlist needed.
2. `Fix npm audit vulnerabilities (critical Next.js RCE + 4 others)` — `npm audit` had never been run in this repo either; running `npm install --package-lock-only` to update the version field incidentally surfaced 8 findings. Fixed via `npm audit fix` (all safe patch/minor bumps within existing `package.json` ranges, no manifest edits): **`next` 16.3.1 → 16.3.6** (critical — unauthenticated RCE on Windows-hosted servers, `GHSA-p293-qw3h-jr36`, and via the Image Optimization API with AVIF files, `GHSA-2xp9-vwfh-vxw4`), `sharp` (high, libheif), `browserslist`/`js-yaml` (high, DoS patterns), `baseline-browser-mapping` (moderate, DoS). Full `preflight.sh` re-run afterward (86 test files / 669 tests, tsc, eslint) confirmed nothing broke from the `next` bump. Left open: 3 moderate `@vitest/mocker` findings needing a `vitest` 4→5 major bump — dev-only (test runner, never shipped), deliberately deferred to its own verification pass rather than riding along on this commit.
3. `Bump version to 1.6.42`.

## A real gotcha hit and worked around

Editing `scripts/preflight.sh` via the `\\wsl.localhost\Ubuntu\...` UNC path (the mechanism a Windows-side Claude Code session uses to reach WSL files with the Edit/Write tools) **silently strips the executable bit** — `git status`/`git diff` show no content change, but the file mode flips from `100755` to `100644`, and running it fails with `Permission denied`. Caught immediately (`ls -la` showed `-rw-r--r--`, `preflight.sh` wouldn't execute) and fixed with `chmod +x` before every commit; `git ls-files -s` was used to positively confirm `100755` was restored before pushing. Recorded in [[Gotchas]] so a future session doesn't lose an hour rediscovering it.

## Vault updated

[[UnitPrep CI-CD Framework]]'s Tier 0 section and status-summary table updated to reflect `cargo-audit`/`gitleaks` as **built**, not "next, not urgent" — the framework doc's own instruction ("this table gets updated as each phase actually ships") applied to itself.

## Related

- [[Session 2026-09-28 (Part 2) — Migration-Squash Alternative & CI-CD Framework Design]] — designed the framework this session executes one piece of
- [[UnitPrep CI-CD Framework]] — Tier 0 status updated this session
- [[Gotchas]] — the new WSL-UNC-path executable-bit entry
