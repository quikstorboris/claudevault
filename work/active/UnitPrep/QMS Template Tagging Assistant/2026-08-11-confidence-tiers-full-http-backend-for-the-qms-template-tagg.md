---
date: 2026-08-11
description: "Built the first real HTTP surface for the whole Phase 2 pipeline: a session-based upload/review/apply flow mirroring dedup's exact shape, plus the con"
tags:
  - project-note
source_repo: bmaksimov
---

# Confidence tiers + full HTTP backend for the QMS Template Tagging Assistant (step 8, backend half)

Built the first real HTTP surface for the whole Phase 2 pipeline: a session-based upload/review/apply flow mirroring dedup's exact shape, plus the confidence-tier logic the review UI needs that hadn't been designed yet. Frontend (review UI, upload tab) is still to come -- this closes out the backend half of step 8.

## What changed

- tagger-pipeline/src/lib.rs - added ConfidenceTier (Auto | NeedsReview); find_candidates now assigns a tier per candidate based on exact-span ambiguity (O(n^2), deliberately -- candidate counts are small enough that this is simpler than giving RegionRef a Hash impl just for this).
- src/api/tagger.rs (new) - POST /tagger/check (upload+recognize in one step, loads active client_ops.tag_pattern rows, no known values supplied -- the blank-template case only), /tagger/report (re-fetch), /tagger/apply (confirmed substitutions -> finished .docx download). Mirrors dedup.rs's structure almost exactly.
- src/application/tagger_session_service.rs (new) - TaggerSession stores original_bytes + candidates, not a parsed FlatDocument -- re-parsing on report/apply is cheap and avoids a second possibly-drifted copy in memory.
- src/api/mod.rs, src/main.rs - new tagger_sessions field on AppState, same InMemorySessionStore/cleanup-task pattern as unit_group_sessions/dedup_sessions.
- src/api/test_support.rs, dedup_test_support.rs, tagger_test_support.rs (new) - empty_tagger_store() helper + tagger_state_with_session() fixture, mirroring the dedup test-support pattern exactly.


## Decisions

- /tagger/check supplies no known values to detect_candidates -- only recognize_blanks (the pattern library) runs for now. detect_candidates is fully wired into find_candidates already, it just has no caller yet since there's no UI step for an OM to type in known values.
- Confidence tier is exact-span ambiguity only (do N candidates share identical (region,start,end)?) -- the simplest signal actually available today, confirmed with Boris before building rather than inventing something more elaborate unprompted.
- TaggerSession stores raw bytes + candidates, re-derives FlatDocument on every report/apply call rather than caching it -- cheap to re-parse, and avoids a stale-cache class of bug entirely.


## Learned

- cargo fmt -- <file1> <file2> ... does NOT scope rustfmt to just those files the way it looks like it should -- it reformatted the whole workspace anyway, silently reintroducing several instances of the already-known, already-flagged rustfmt-version drift (auth_invites.rs, auth_roles.rs, auth_user_role.rs, auth/mod.rs, client_ops_qms_tags.rs) into what was meant to be a tightly-scoped feature commit. Caught via git status showing unexpected unrelated files touched; reverted each one individually with git checkout -- before committing. Use `cargo fmt -p <package>` (crate-scoped) instead of file-argument scoping when a specific-files-only fmt is actually needed.
- WSL background-process detachment via `nohup cmd > log 2>&1 & disown` from a `wsl -e bash -lc "..."` Bash-tool call is unreliable -- the process would sometimes not survive past the tool call returning, with no error and an empty log. Adding `setsid` and redirecting stdin from `/dev/null` (`setsid nohup cmd ... < /dev/null & disown`) fixed it reliably every time after that.


## Verification

5 new handler-level tests (2x 404, 1x 400 bad index, a full /tagger/report round trip, and a full /tagger/apply round trip against the real Atherton fixture -- downloaded bytes re-parsed and confirmed to actually contain the substitution). Full workspace suite green at 309 tests, clippy clean. Live-server check: started the real release binary, hit all three new routes unauthenticated over real HTTP and got 401 (correctly routed + auth-gated), not 404.


## Open

- Frontend (review UI grouped by tier, in-context snippets, searchable dropdown; upload tab next to Unit Group) not started -- the other half of step 8.
- client_ops.tag_pattern is still empty (zero rows) on both dev and prod -- the recognizer has no real patterns to match against yet. Seeding a real starter set (Move-In Date, Unit No., etc. from the already-confirmed corpus) is an open task, not yet done or even asked about.
- sentence_pattern matching, cross-cell (row-aware) label-proximity, and detect_candidates' known-values UI path all remain unbuilt, per earlier sessions' notes.
- Not yet pushed to origin/main -- awaiting Boris's go-ahead per the established push-confirmation pattern.



_Recorded 2026-08-11T22:53:40.047Z from `bmaksimov` via the om MCP server (routing: caller)._
