---
date: 2026-08-14
description: "Closed 8 of the 9 M5 items from the third audit's fix plan across both repos: shared session_lifetime_hours/request_context/audit-log-filter helpers, "
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 5 (DRY consolidation) shipped — unitprep-api v1.8.3, unitprep-ui v1.5.4

Closed 8 of the 9 M5 items from the third audit's fix plan across both repos: shared session_lifetime_hours/request_context/audit-log-filter helpers, an assign_tiers O(n²)→O(n) fix plus a tagger-specific 10MB body cap and 2000-candidate hard cap, a shared dedup blank-sort helper, and on the frontend a shared useFileUploadAction hook, a shared useAuditLogFilterData hook, and a previously-silent QMS tag catalog fetch failure now surfaced as a real banner. Item 4 (with_tx_and_audit in client_ops_qms_tags.rs) was investigated and declined — the four call sites aren't structurally uniform enough. Backend work was delegated to one subagent, frontend to another (both running in parallel/background), then independently re-verified by the main session before committing.

## What changed

- unitprep-api src/auth/session_cookie.rs + auth/mod.rs - session_lifetime_hours() deduped from auth_login.rs/auth_register.rs into one shared, exported function
- unitprep-api src/api/mod.rs - added request_context()/user_agent_from() helpers, used across ~17 call sites in 10 handler files; also added a tagger-specific 10MB DefaultBodyLimit via a route-scoped merge
- unitprep-api src/api/auth_audit_logs.rs - push_event_type_filter/push_user_id_filter extracted, shared by list_audit_logs and fetch_filtered_audit_logs (also unified a special-cased '=' filter into the same IN (...) shape both functions now use)
- unitprep-api tagger-pipeline/src/lib.rs - assign_tiers rewritten from an O(n^2) nested scan to a single-pass HashMap count keyed on (region, start, end); docx-surgeon RegionRef gained Hash to serve as the key
- unitprep-api src/api/tagger.rs - added MAX_CANDIDATES=2000 hard cap in check, returning 422 rather than processing an unbounded candidate list
- unitprep-api dedup/src/comparison.rs + phrasing.rs - blank_aware_key/blank_last_sort_key extracted into comparison.rs, phrasing::units_by_value now uses them instead of its own copy
- unitprep-ui lib/useFileUploadAction.ts (new) - shared multipart-upload hook (mirrors useSessionAction's SessionActionResult shape); adopted by TaggerUploadPage, DedupUploadPage, MasterGroupFileSection (the latter two previously had NO session-expiry fold at all -- a 401 just showed as a raw error message, now fixed as a side effect)
- unitprep-ui lib/useAuditLogFilterData.ts (new) - shared event-type/user-list fetch + selection state for both admin/audit-logs/page.tsx and its export/page.tsx
- unitprep-ui components/TaggerResultsPage.tsx - QMS tag catalog fetch failure surfaced as an inline banner (previously silently swallowed by an if(ok)-only branch)


## Decisions

- Declined M5 item 4 (with_tx_and_audit() helper in client_ops_qms_tags.rs) after real investigation: create/update/set_active have genuinely different early-exit shapes (unique-violation branch, not-found check, already-in-state conflict), so a generic wrapper would need an awkward closure signature for minimal savings. Left as three near-identical but not identical call sites per the codebase's own 'three similar lines beats a premature abstraction' principle -- this is now the second M5 item (after M4's Next.js CVE reachability re-check) where the audit's original framing turned out to be slightly wrong on inspection, not just execution detail.
- useDiscoveryFlow's /upload call was deliberately left OUT of the shared useFileUploadAction hook: it has no session_id yet (it's what creates the session) and chains into a second, non-multipart /discover call with bespoke error messages already covered by its own tests -- forcing it through the hook would have been a different shape, not the same duplication.
- Delegated backend (items 2,3,5,9; item 6 done directly by the main session first) and frontend (items 1,7,8) to two separate general-purpose subagents given the well-specified, mechanical nature of the remaining DRY work and the size of the remaining milestone -- each ran its own verification loop (cargo fmt/clippy/test; tsc/eslint/vitest) before reporting back, and the main session independently re-ran the same checks against the actual working tree before committing rather than trusting the reports at face value.


## Learned

- This machine's WSL distro has NO native Linux Node reachable from a non-interactive `bash -lc` login shell's default PATH -- nvm IS installed (real node at ~/.nvm/versions/node/v24.18.0/bin) but `bash -lc` doesn't reliably run the .bashrc lines that source nvm.sh in this invocation shape, so PATH falls through to the Windows npm install at /mnt/c/Program Files/nodejs. Running `npx <anything>` there resolves to Windows npx.cmd, which shells out via cmd.exe with a UNC cwd (\\wsl.localhost\...), fails on the UNC path, and SILENTLY falls back to npm's placeholder joke 'typescript' package printing a Star Wars pun -- it does not error loudly, it just runs the wrong thing and reports success-looking output for a tool that never really ran. Same failure mode independently hit both the main session's direct wsl.exe invocations AND a subagent's first attempt within the same session, so it isn't a one-off fluke. Fix: prepend the real node bin dir explicitly in the same command string, e.g. `wsl.exe -e bash -lc 'export PATH="$HOME/.nvm/versions/node/v24.18.0/bin:$PATH" && cd ... && npx tsc --noEmit'`, and confirm with `node --version` inside the same invocation before trusting any npx/npm output from this box.
- cargo commit-splitting across files with independent, non-overlapping concerns (no shared file touched by two different logical changes) needs no hunk-level surgery at all -- just `git add <specific files>` per commit in sequence, verifying build/test at each intermediate state. Only genuinely mixed single-file changes need the reconstruct-and-revert technique already in Patterns.md.


## Verification

Backend: cargo fmt --all -- --check, cargo clippy --workspace --all-targets, cargo test --workspace all clean at every intermediate commit and the final state (546 tests, 0 failed, 3 ignored as expected). Frontend: npx tsc --noEmit (clean), npx eslint . (0 errors, 1 pre-existing unrelated warning in generated coverage/), npx vitest run (330/330 passing across 46 files) -- run independently by the main session after discovering and fixing the WSL/nvm PATH issue that had made an earlier direct verification attempt silently run the wrong tool.



## Related

- [[2026-08-14-milestone-6-file-splits-shipped|Milestone 6]]
- [[Patterns]]
- [[Gotchas]]


_Recorded 2026-08-14T17:09:11.327Z from `bmaksimov` via the om MCP server (routing: fallback)._
