---
date: 2026-08-27
description: "Boris flagged the '✅ Master file is good' message as a little misleading — investigation showed it's not actually a net-new/no-master-file bug (a real"
tags:
  - project-note
source_repo: development
---

# Tightened GroupFileSummary's format-valid guard from "not false" to explicit "=== true"

Boris flagged the "✅ Master file is good" message as a little misleading — investigation showed it's not actually a net-new/no-master-file bug (a real master file was found and correctly validated in his repro), but the fallback branch was written as "not false" rather than an explicit "=== true" check, which would silently treat a null (not-yet-evaluated) validity as good. Tightened it to be explicit and added a genuine neutral state, even though the null case is unreachable today given current backend invariants.

## What changed

- unitprep-ui/components/discovery/GroupFileSummary.tsx - split the format-valid ternary into three explicit branches (=== false / === true / neither) instead of false-check-then-catch-all; the new third branch renders a neutral 'Checking file format...' message instead of silently reading as good. Also tightened the Confirm button's visibility condition from `!== false` to `=== true`.
- unitprep-ui/components/discovery/GroupFileSummary.test.tsx - added a test asserting group_file_format_valid: null renders the neutral message, not the 'good' or 'confirmed' one, and hides Confirm


## Decisions

- Made this change defensively even though group_file_format_valid is currently always Some(bool) whenever this component renders (verified: resolve_group_file_readiness in unitprep-api sets format_valid and selected_group_file_name together, and GroupFileSummary only mounts once selected_group_file_name is set) -- the point was removing an accidental-looking guard, not fixing a live defect, per Boris's own framing ('harmless, but a little misleading, I'd rather fix it').


## Learned

- The actual repro Boris described ("master file valid" during what he thought was a net-new/no-master-file analysis) turned out to be a real, correctly-detected master group file (Units Migration/.../Unit Groups.csv, Master Group Files Found: 1) -- not a genuine zero-group-file net-new case. He'd only intended to flag the accidental-guard code smell, not a functional bug in the net-new path itself.


## Verification

npx tsc --noEmit and eslint clean on both edited files; GroupFileSummary.test.tsx: 8/8 passing (7 existing + 1 new); full frontend suite: 336/336 passing (up from 335).




_Recorded 2026-08-27T20:43:42.668Z from `development` via the om MCP server (routing: fallback)._
