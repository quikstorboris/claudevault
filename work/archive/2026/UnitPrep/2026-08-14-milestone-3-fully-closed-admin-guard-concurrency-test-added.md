---
date: 2026-08-14
description: "Third and final M3 item done: a real concurrency test proving the last-active-admin lock (from M1) genuinely serializes concurrent callers, using two "
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 3 fully closed — admin-guard concurrency test added, real bug found while testing

Third and final M3 item done: a real concurrency test proving the last-active-admin lock (from M1) genuinely serializes concurrent callers, using two real Postgres connections and a timing assertion. Writing it surfaced a real, generalizable Postgres/RLS gotcha (recorded in brain/Gotchas.md) that had nothing to do with the fix itself. Milestone 3 of the fix plan is now fully closed -- all 8 milestones' status: M1/M2/M3 done and pushed, M4-M8 not started.

## What changed

- src/auth/roles.rs (unitprep-api) - added remaining_active_admins_excluding_serializes_concurrent_callers, an #[ignore]'d real-DB concurrency test (two genuine connections, one holds the FOR UPDATE lock for 400ms, the other's call is timed to prove it was blocked, not racing); expanded the function's doc comment to spell out the RLS+FOR UPDATE interaction the test writing surfaced


## Decisions

- Attempted the concurrency test rather than settling for a documented decision not to (the plan's own fallback option) -- a DB row lock is deterministically testable (unlike sub-microsecond in-process races elsewhere in this codebase, which genuinely aren't), so 'if practical' turned out to mean yes.


## Learned

- Postgres RLS: SELECT ... FOR UPDATE is checked against the table's UPDATE policy in addition to its SELECT policy, since acquiring a lock is treated as a preliminary step toward a possible update -- even though the statement itself never writes anything. A non-admin caller's FOR UPDATE against auth.roles silently returned 0 rows (hard RowNotFound) even though the identical plain SELECT with the same RLS context returned all 4 rows. This is now in brain/Gotchas.md as a generalizable Postgres lesson, not just a UnitPrep note -- it will recur on any RLS-protected table where the SELECT and UPDATE/DELETE policies differ.
- In practice this doesn't affect the shipped fix at all: both real callers (revoke_role/deactivate_user) already require an admin caller to reach this code path, so their RLS context always satisfies the UPDATE policy too. It only surfaced because a test author (me) defaulted to an empty/generic role context instead of matching the real caller's actual context.


## Verification

cargo test --workspace: 585 passed/0 failed/3 ignored (2 real-DB tests from earlier + this new one). cargo clippy --workspace --all-targets: 0 warnings. cargo fmt --all -- --check: 0 diffs. The new ignored test run standalone: passed in ~1.3s (a realistic duration matching genuine lock-wait time, not an instant pass-through that would suggest the lock isn't really being exercised). Committed and pushed to origin/main.



## Related

- [[2026-08-13-third-audit-fix-plan-full-session-handoff-m1-m2-done-m3-in-p]]
- [[2026-08-13-cross-owner-idor-regression-tests-extended-to-dedup-and-tagg]]


_Recorded 2026-08-14T15:17:53.218Z from `bmaksimov` via the om MCP server (routing: caller)._
