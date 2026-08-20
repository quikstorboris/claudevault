---
date: 2026-08-13
description: "First item of M3 (the fix-plan milestone for the third audit): added cross-owner session-access regression tests for dedup and tagger sessions, matchi"
tags:
  - project-note
source_repo: bmaksimov
---

# Cross-owner IDOR regression tests extended to dedup and tagger sessions

First item of M3 (the fix-plan milestone for the third audit): added cross-owner session-access regression tests for dedup and tagger sessions, matching the one already added to analyze_tests.rs during M1. All three of the codebase's independently-implemented session stores now have direct proof that a session belonging to one user 404s for a different authenticated caller. No version bump -- test-only change, no behavior affected.

## What changed

- src/api/dedup_tests.rs, src/api/tagger_tests.rs (unitprep-api) - added report_returns_404_for_a_session_belonging_to_a_different_user to each, mirroring analyze_tests.rs's existing equivalent




## Verification

cargo test --workspace: 585 passed, 0 failed (was 583). cargo clippy --workspace --all-targets: 0 warnings. cargo fmt --all -- --check: 0 diffs. Committed and pushed to origin/main.



## Related

- [[2026-08-13-milestone-1-shipped-closed-the-4-highest-risk-findings-from]]


_Recorded 2026-08-13T22:21:21.450Z from `bmaksimov` via the om MCP server (routing: caller)._
