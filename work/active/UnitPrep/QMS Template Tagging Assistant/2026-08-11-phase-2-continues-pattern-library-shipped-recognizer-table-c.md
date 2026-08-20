---
date: 2026-08-11
description: "Continued the Phase 2 build from the prior session's recap: designed and shipped the tag_pattern DB schema, built the first-pass label-proximity recog"
tags:
  - project-note
source_repo: bmaksimov
---

# Phase 2 continues: pattern library shipped, recognizer + table-cell extraction built, DBs synced

Continued the Phase 2 build from the prior session's recap: designed and shipped the tag_pattern DB schema, built the first-pass label-proximity recognizer against it, extended docx-surgeon to treat table cells as independent text regions, synced prod's client_ops schema (never existed there before), and fixed a real CORS bug found incidentally while testing. All work committed and pushed to origin/main across 4 commits.

## What changed

- migrations/20260811210000_*.up/down.sql - client_ops.tag_pattern (label_proximity/sentence_pattern rows, one per confirmed real phrasing) + qms_tag.value_shape (phone/email/zip, backfilled for 15 tags). RLS mirrors qms_tag's current widened policies, not the original admin-only ones -- caught by checking live schema, not the creation migration.
- template-tagger/src/recognize.rs (new) - recognize_blanks(): label_proximity matcher for literal underscore-run blanks (3+ chars), reuses detect_candidates' word-bounded ASCII matching. sentence_pattern deliberately deferred to its own pass.
- docx-surgeon/src/read.rs - extract_flat_text now returns FlatDocument{body, table_cells} instead of one FlatText; each <w:tc> becomes its own independently-addressable region so adjacent cells can never read as one run-on string. edit_docx/apply_edits still only touch the body region.
- src/api/mod.rs - CORS allow_methods widened from [GET,POST] to include PUT/PATCH -- was silently blocking qms_tag update/deactivate/reactivate and auth_configuration's update at the browser preflight, surfacing as a misleading 'could not reach the API server' error.
- rust-toolchain.toml (new) - pinned to 1.96.0 after finding a codebase-wide rustfmt --check diff caused by version drift (confirmed pre-existing on a clean main checkout, unrelated to any of tonight's changes).


## Decisions

- Pattern aliases get one tag_pattern row per confirmed real phrasing (not an aliases array in one row) -- mirrors qms_tag's own corpus-driven growth philosophy; Boris's explicit call over the array alternative.
- Shape validation (phone/email/zip) is a qms_tag.value_shape column, not a third tag_pattern kind -- it's generic cross-cutting regex logic applied to whatever tag a match resolved to, not per-tag authored content.
- Pattern library stays migration-seeded for now, no admin UI -- same trajectory qms_tag itself started on.
- First recognizer pass scoped to label_proximity + literal underscore blanks only; sentence_pattern (prose blanks, composite fields) deferred to its own pass rather than building both at once.


## Learned

- The plan's premise that 'Price Rite's table-based layout' needs table-cell extraction doesn't hold for the actual price-rite-lease-FORMATTED.docx file -- it has zero <w:tbl> elements; that two-column look is tab stops. Rowley Self Storage's lease is the one that actually uses real tables (3 <w:tbl> elements, verified with a throwaway example against the real Dropbox file, not committed -- real PII risk).
- A CORS allow_methods list that only lists GET/POST fails PUT/PATCH at the browser preflight with no server-side error at all -- the backend log shows nothing wrong, and the frontend's generic fetch-failure handling reports it as 'could not reach the API server', which is actively misleading when the server is up and other methods work fine.
- sqlx migrations applied with a checksum are meant to be immutable once applied -- caught a stale-policy mistake in the tag_pattern migration by reverting (sqlx migrate revert) and editing in place, rather than stacking a fix-up migration, since it was still uncommitted and only applied to my own dev branch.


## Verification

Full unitprep-api workspace test suite green throughout (304+18+23+2 = 347 tests across crates, 0 failures), clippy clean on every touched crate. docx-surgeon's table-cell extraction verified against a real production document (Rowley's tagged lease) via a throwaway, uncommitted example -- 11 cells extracted cleanly with no cross-cell bleed. Prod DB migration + setup_app_service_role.sql re-run confirmed via information_schema.role_table_grants: qms_tag/tag_pattern have full CRUD, audit_log correctly restricted to INSERT/SELECT only, matching dev exactly. All 4 commits pushed to origin/main.


## Open

- sentence_pattern matching (prose-embedded blanks, composite date/amount fields) not yet built.
- Steps 7-8 of the original plan (wire detect_candidates + recognize_blanks + docx-surgeon into one pipeline; build the review UI and upload tab) not started.
- Table-cell editing (apply_edits against a table_cells region) not wired up -- only body-region edits work today.
- The 5 lower-confidence tag labels (e.int, m.ins, m.liens, m.vi.vt, m.vi.nor) still not checked against live QMS tooltips -- explicitly skipped this session, not resolved.
- Codebase-wide rustfmt drift only stopped from getting worse (via rust-toolchain.toml), not actually fixed -- a full reformat commit is still outstanding if ever wanted.



_Recorded 2026-08-11T22:17:01.606Z from `bmaksimov` via the om MCP server (routing: caller)._
