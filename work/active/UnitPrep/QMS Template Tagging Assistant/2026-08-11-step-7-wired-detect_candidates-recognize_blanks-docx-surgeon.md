---
date: 2026-08-11
description: "Built the real pipeline connecting the three previously-standalone crates. Made docx-surgeon's editor region-aware (Edit/apply_edits now carry a Regio"
tags:
  - project-note
source_repo: bmaksimov
---

# Step 7: wired detect_candidates + recognize_blanks + docx-surgeon into one pipeline

Built the real pipeline connecting the three previously-standalone crates. Made docx-surgeon's editor region-aware (Edit/apply_edits now carry a RegionRef so a body edit and a table-cell edit can apply in one call) as a prerequisite, then built a new unitprep-tagger-pipeline crate that runs both template-tagger matchers across every region of a document. Verified against real production documents throughout, which surfaced one genuine, previously-unknown gap.

## What changed

- docx-surgeon/src/read.rs - added RegionRef (Body | TableCell(usize)) and FlatDocument::region() lookup.
- docx-surgeon/src/edit.rs - Edit gained a `region: RegionRef` field; apply_edits now takes &FlatDocument instead of &FlatText and groups by (region, run_index) not just run_index (a run index is only unique within its own region); check_no_overlaps is now scoped per-region -- two edits in different regions can share identical flat_start/flat_end without conflicting.
- tagger-pipeline/ (new crate, unitprep-tagger-pipeline) - find_candidates() runs detect_candidates + recognize_blanks across the body and every table cell, returning RegionCandidate (candidate + which region). to_edit() builds the resulting docx_surgeon::Edit from a confirmed candidate + caller-chosen replacement text.


## Decisions

- Pipeline logic lives in its own new crate (unitprep-tagger-pipeline), not folded into template-tagger or docx-surgeon -- keeps 'run every matcher against every region' as its own coherent piece of logic without either dependency needing to know about the other, matching the project's established one-crate-per-tool convention.
- Got the per-region overlap-check scoping right on the first pass rather than shipping the naive global version and fixing it later -- the bug (rejecting valid cross-region edits with identical coordinates) was obvious in hindsight once regions existed at all.


## Learned

- Real, previously-unknown gap found verifying against Rowley's actual document: recognize_blanks only searches within one region, so a label in one table cell and its value in the ADJACENT cell (a common row layout: label column, value column -- confirmed concretely with Rowley's 'Total' cell followed by a separate '$____________' cell) is invisible to it. Confirmed this is a real limitation, not a bug, by testing the same mechanism intra-cell (works) vs inter-cell (doesn't) -- would need a new, deliberately-scoped row-aware pattern kind, not a patch to label_proximity.


## Verification

Full unitprep-api workspace test suite green (304+18+25+2+6 = 355 tests, 0 failures), clippy clean on every touched/new crate. End-to-end find-and-apply proven both synthetically (unit test: body value + table-cell value, both substituted correctly in one apply_edits call) and against Rowley's real tagged production lease (two independent table cells edited in one call via a throwaway, uncommitted example; a neighboring untouched cell confirmed unaffected).


## Open

- Cross-cell (row-aware) label-proximity not designed or built -- a real gap for table layouts with the label-column/value-column shape.
- sentence_pattern matching still not built (deferred from step 5).
- Step 8 (review UI + upload tab) not started.
- Not yet committed to git history as pushed -- awaiting Boris's go-ahead per the established push-confirmation pattern.



_Recorded 2026-08-11T22:28:53.110Z from `bmaksimov` via the om MCP server (routing: caller)._
