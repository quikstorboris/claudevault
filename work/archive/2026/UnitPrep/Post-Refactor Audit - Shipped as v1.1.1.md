---
date: 2026-07-28
description: "Organized the post-refactor-audit's ~115 uncommitted files into coherent commits and shipped both repos as v1.1.1"
tags:
  - work-note
  - unitprep
status: completed
quarter: Q3-2026
project: unitprep
---

# Split post-refactor-audit work into commits, ship as 1.1.1 on both repos

Organized ~115 files of uncommitted post-refactor-audit changes (M1-M5 milestones: session ownership, dedup fixes, API/export hygiene incl. a real CORS bug, dependency security bumps) across unitprep-api and unitprep-ui into coherent, individually-described commits, then bumped both repos from 1.1.0 to 1.1.1 (patch release — bug fixes and hygiene only, no new functionality) and pushed to main.

## What changed

- unitprep-api: isolated the entire workspace's cargo fmt pass (808 hunks, no rustfmt.toml existed) into its own commit by stashing real changes, formatting HEAD, committing, then popping the stash and resolving 26 conflicts by taking the real-change side per file and re-running cargo fmt once more — cleanly separates mechanical reformatting from logic in history.
- unitprep-api: 8 further commits — .gitignore (REFACTOR.md), dependency bumps (quick-xml/calamine RustSec fixes, uuid, tokio features, catch-panic), unit-group efficiency/dead-code cleanup, M1 session ownership, M2 dedup correctness fixes, M3 API/CORS/panic-middleware hygiene, cargo-audit acceptance doc, om MCP plumbing — then a version-bump commit (1.1.0 -> 1.1.1) with a new CHANGELOG section; auth-in-progress items stayed under Unreleased since no endpoint uses them yet.
- unitprep-ui: 4 commits — om MCP plumbing, shared-hook credentials/401 handling, remaining fetch migration + 2 component splits, npm audit fix (7 packages, 4 High findings remain unfixable without a breaking change) — then the matching 1.1.1 version bump via `npm version`.
- README.sample.md + assets/readme/hero.svg (unitprep-api) deliberately left uncommitted per Boris's explicit choice — still local-only, not part of this push.


## Decisions

- Isolated cargo fmt as its own commit via stash+reformat+commit+pop+resolve-conflicts-by-taking-theirs+refmt, rather than letting formatting and logic changes stay interleaved across 113 files — verified safe by rerunning cargo test --workspace (284 passing) and cargo fmt --all -- --check (0 diffs) after reconstruction.
- Accepted a few intermediate commits that don't compile in isolation (e.g. unit-group's Issue->AdvisoryIssue rename lands one commit before csv_export.rs's matching import fix) rather than spending disproportionate effort on perfect hunk-level splitting for an internal, no-CI, single-operator repo — final pushed state is what was verified.
- Single 1.1.1 patch bump covering the whole batch, not several consecutive patch versions, since nothing was actually released between these fixes — versions should mark real release boundaries, not manufactured ones.
- Left the in-progress auth work (Postgres/RLS/session-cookie plumbing, no endpoint enforces it yet) under CHANGELOG's Unreleased section rather than folding it into 1.1.1 — it's not a shippable feature yet.


## Learned

- The Git Bash -> wsl.exe -> WSL bash quoting boundary breaks heredocs/apostrophes/parens even inside single-quoted bash -lc scripts when the script itself contains an apostrophe (e.g. "it's") — writing the commit message to a file first (Write tool) and using `git commit -F <file>` sidesteps this reliably, same as the established write-a-script-file-first pattern for multi-step wsl.exe calls.
- A `git stash pop` after reformatting HEAD is a genuine 3-way merge, not a naive patch apply — files untouched by real logic changes merge with zero conflict, and only files where formatting and logic changes textually overlap conflict (26 of 113 here). Resolving via `git checkout --theirs` per conflicted file then re-running `cargo fmt --all` once at the end is far cheaper than manual hunk surgery and produces an identical result, since rustfmt is deterministic.
- Writing/mkdir-ing directly to a `//wsl.localhost/...` UNC path from Git Bash works for file writes but not always for `mkdir -p` (silently fails as read-only) — creating the directory via `wsl.exe -d Ubuntu-22.04 -- bash -lc 'mkdir -p ...'` first, then writing files into it over the UNC path, works around this.


## Verification

unitprep-api: cargo build --workspace and cargo test --workspace (284 passing, 2 ignored, matching the audit's own documented baseline) both clean after the full commit sequence; cargo fmt --all -- --check reports 0 diffs. unitprep-ui: tsc/eslint were not re-verified this session (a WSL/npx interop quirk made npx tsc fall through to Windows cmd.exe rather than a real code problem) — relying on the original session's own tsc/eslint-clean verification for the code itself, since only commit organization happened here, not new edits. Both repos pushed to origin/main successfully.



## Related

- [[Post-Refactor Audit]]
- [[Post-Refactor Audit - Details]]
- [[Patterns]]
- [[Gotchas]]


_Recorded 2026-07-28T15:36:19.972Z from `bmaksimov` via the om MCP server (routing: fallback)._
