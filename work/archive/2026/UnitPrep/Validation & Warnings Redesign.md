---
date: 2026-07-27
description: Group Prep's validation/warnings pipeline architecture — exclude vs. per-check acknowledge, single-owner group-name model; committed and pushed 2026-07-25.
tags: [work-note, unitprep]
status: completed
quarter: Q3-2026
project: unitprep
---

# Validation & Warnings Redesign

Group Prep's validation/warnings pipeline and `ScanResultsPage.tsx` UI were reworked over 8 iterative rounds during the 2026-07-24 session, driven entirely by Boris's real-data testing (mostly against his 46-file `Wave 3` folder). Consolidated 2026-07-25 into current-state + reusable lessons below; the round-by-round history exists in git history/diffs if the literal blow-by-blow is ever needed.

**Committed 2026-07-25**: `unitprep-api@ace8ff6` ("Rework Group Prep discovery and validation pipelines", 40 files) and `unitprep-ui@0cd2130` ("Rebuild ScanResultsPage around per-reason review, exclude, and acknowledge", 10 files) — one commit per repo, deliberately not split further despite covering two describable sub-themes (discovery continuation, see [[Multi-Vendor Unit-File Discovery]], plus this validation redesign). Almost every shared core file (`mod.rs`, `models.rs`, `test_support.rs`, `unit_group_session.rs`, `types/api.ts`) turned out to be genuinely bipartite between the two themes at the hunk level — mechanically splittable in principle, but reconstructing verified-compiling intermediate states across ~10 shared files for ~8000 combined lines of change carried real risk for modest git-log benefit, especially right before pushing to shared main. Pushed to `origin/main` immediately after.

## Current architecture (as of 2026-07-24 session end)

**Severity**: only `Blank UnitGroup values` and `Duplicate unit numbers` are `Severity::Error` (block export outright). Everything else — `Invalid dimensions`, `Climate status does not match UnitGroup`, `Locality does not match UnitGroup`, `UnitGroup dimensions do not match Width/Length`, `Odd UnitGroup values`, `Rare UnitGroup detected`, `Inconsistent unit-number casing` — is `Severity::Warning`: advisory, reviewable, never blocking on its own.

**Four independent overlay mechanisms**, each its own session-state HashMap/HashSet + endpoint, all layered by `Session::effective_documents` in this order — format resolution → corrections → excluded groups. Acknowledgments are applied inside `validate_document` itself, not as a document-layer filter:

1. **Correction** (`/correct`, `/correct-group`) — rewrites a cell value (one unit, or every unit sharing a UnitGroup name). Data changes.
2. **Dimension exemption** (`/exempt-dimensions`) — one unit opts out of the Invalid Dimensions check specifically. Data unchanged.
3. **Group exclusion** (`/exclude-group`, `/exclude-groups` bulk) — drops a UnitGroup and every unit in it entirely, downstream of every stage (validation, analysis, export), as if never uploaded. Resolves *every* check that group was ever flagged under, since the units themselves are gone.
4. **Group-check acknowledgment** (`/acknowledge-group-warnings`, bidirectional via `acknowledged: true/false`) — the newest mechanism, added specifically for "Import as is": accepts a group "as is" for *one specific check* (`GroupCheckAcknowledgments { odd, rare }`, filtered out of `odd_group_names`/`rare_pairs` before `issues::build` ever raises the issue). Data unchanged, and unlike exclusion, only suppresses the named check — a group shared between Odd and Rare needs its own acknowledgment for each.

**Ownership model — a group name belongs to exactly one warning section, everywhere, not just its editable card.** Odd and Rare commonly overlap (an odd-named group is very often also rare); Boris's end-state preference, reached after several rounds of tightening, is that a shared group's name appears in exactly one section's bullets, review cards, *and* excluded/acknowledged history — never cross-referenced or repeated elsewhere. Implemented in `ScanResultsPage.tsx` via a single `claimedGroupCards: Map<groupName, description>`, first-claim-wins, seeded in two passes before rendering:

- Pass 1: from `reasonSnapshots` (persisted history, see below) in its own stable insertion order — a description's snapshot is first created the first time it's ever live, so this order never changes once established (in practice: Odd before Rare, since `issues::build` always raises Odd first).
- Pass 2: live reasons claim any name pass 1 left unclaimed.
- A name already claimed *by the reason processing it* still counts as "mine," not "taken" — checked explicitly (`owner === undefined || owner === description`), not just "is this claimed by anyone," or a reason's own historically-owned names look unclaimed and get silently emptied.
- Bullets, review cards, and excluded/acknowledged-history entries are all filtered through this same map. A non-owning reason shows nothing for that name — no cross-reference note (an earlier "(see X)" pointer was tried and explicitly rejected).
- **Exclude vs. acknowledge must NOT use the same scoping for their bulk buttons.** `ExcludeAllButton`/`ImportAsIsButton` look similar but differ critically: Exclude is scoped to `reviewGroupNames` (owned-only) because removing a shared group's units resolves every check at once regardless of who clicks it. Acknowledge must use the full `groupNames` (every group *this reason* flags, owned-card or not) because it's per-check — scoping it to owned-only silently leaves shared groups half-resolved forever (a real bug caught live: Continue stayed disabled after clicking "Import as is" in both sections).

**History preservation**: `reasonSnapshots` (`Map<description, {groupNames, occurrenceCounts}>`, React state) remembers the fullest group-name list ever seen live for each reason — critically, it must only ever **grow** (union), never shrink to match the current live list, or excluding/acknowledging a group erases the very history needed to show it as resolved. `excludedGroupNames`/`acknowledgedGroupNames` (two parallel `Set<string>`, global) track what's been done. A reason with 0 live issues still renders (as `isLive: false`) if it has any excluded/acknowledged history, with an "Excluded Groups"/"Imported As Is" block and an undo button (`EditGroupsButton`/`UndoImportAsIsButton`, POSTing the same bulk endpoint with the boolean flipped).

**Page layout**: "Validation Details" collapses on its own the moment everything resolves (controlled `<details>`, one-shot via a `useState` compared against the previous render — never a `useRef` read/written during render, see lint note below), but still shows every section's full preserved history if reopened. The top "Warnings" stat tile is frozen at its last non-zero total (grey, not reset to 0) once resolved. "Export Status" has three states: `❌ Blocked` (errors), `⚠️ Resolve Warnings` (no errors, warnings remain), `✅ Allowed` (clean). Bottom of page: "Continue" (green, requires zero issues of any severity) plus a per-section "Import as is" (requires no errors; warnings don't block it) inside each reason's own block — there is *no* page-bottom global "Import as is" anymore, removed once the per-section ones covered the same need. Back buttons exist on Discover (→ client info, cancels session), Validate (→ Discover, cancels session), and Export Review (→ Validate, does *not* cancel — going back there means "let me fix something," not "start over").

## Reusable lessons (apply beyond this file)

- **WSL nested-quoting/`$`-sigil pitfall keeps recurring — hit a third time, this time destructively.** A `perl -0777 -pi` regex with `\$1`/`\$2` backreferences, run through `wsl.exe bash -lc "..."`, silently lost the backreferences crossing the boundary and deleted 15 of 16 target call sites' actual code instead of editing them (caught via the Rust compiler's own error location, fixed with plain `Edit`/`replace_all`). Don't use shell regex with `$`/backreferences across this boundary for anything `Edit`'s literal-string matching can do instead — write a script file first, or just don't.
- **This project's ESLint config is stricter than plain React**: `react-hooks/set-state-in-effect` forbids calling `setState` inside a `useEffect` body, and `react-hooks/refs` forbids reading/writing `ref.current` during render. For "remember something across renders and adjust state in response" needs, use the plain `if (condition) { setX(...) }` render-time-conditional pattern (guarded so the condition goes false after the update — convergent, not an infinite loop), backed by `useState`, never `useRef`, for anything read/written outside an event handler or effect.
- **Never run `next build` while a `next dev` process is live against the same project** — it corrupts the dev server's `.next/dev/*` cache, producing a real "white unformatted page"/500 for whoever's looking at it. Hit twice before the rule registered. If a build check is genuinely needed, restart `next dev` immediately after, every time.
- **Live-verification technique for this app**: craft a synthetic CSV with the `Write` tool over the `\\wsl.localhost\...` UNC path (not via `wsl.exe` shell heredocs, which hit the pitfall above), drive it through upload→discover→select→confirm→validate via direct `curl`, then load that real session through the actual UI in the Browser pane (a throwaway client created through the real UI first, for a browser-trusted `clientId`). Dispatching real DOM `.click()` via `document.querySelectorAll('button')` is more reliable than ref/coordinate-based clicks on this page's nested `<details>` accordion, which shift across re-renders.

## Operational logging pass, 2026-07-24/25

Boris asked for an opinion on the server log's readability after seeing a real 46-file session's output, plus a survey for other gaps. Surveyed every `api/*.rs` file's `tracing::` coverage; most (`correct`, `correct_group`, `exclude_group`, `exempt`, `select_group_file`, `group_file_confirm`, `cancel_session`, `export`, `analyze`, `validate`) already logged a clean success line at the right altitude — no changes needed there. Fixed:

- `select_unit_file.rs`/`resolve_unit_format.rs` (both bulk-confirm and reset paths) were dumping a whole `Vec<String>` into one field (`unit_file_names=?names`), unreadable for a real dozen-plus-file selection. Changed to one `tracing::info!` per file plus a summary line with just the count — matches the pattern `exclude_groups`/`acknowledge_group_warnings` already used.
- `discover.rs`'s "Classified discovered documents" line was missing `session_id` entirely (every other line in the system has it) — fixed via `session.metadata.id`.
- `group_file_upload.rs` (manually designating a master group file) had zero logging for a meaningful state change — added a success line mirroring `group_file_confirm.rs`'s own style.

Verified live: uploaded 2 files, walked through select+confirm, confirmed the real log now shows one "Unit file selected"/"Unit file format resolved" line per file plus a summary count line, and `session_id` present throughout. 245 backend tests still passing, clippy clean.

## Status at session end

Committed and pushed to `origin/main` 2026-07-25 (`unitprep-api@ace8ff6`, `unitprep-ui@0cd2130` — see note at top of file). 245 backend tests passing, clippy clean; frontend `tsc`/`eslint` clean throughout (production `next build` deliberately not re-run late in the session per the `next dev`-corruption lesson above). See [[Multi-Vendor Unit-File Discovery]] for the same overall session's discovery/master-file work.
