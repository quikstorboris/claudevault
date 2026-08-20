---
date: 2026-08-12
description: "Boris hit a real production bug testing the tagger UI against real documents: apply failed opaquely for two candidates whose blanks were split across "
tags:
  - project-note
source_repo: bmaksimov
---

# Fixed the real multi-run apply bug, added preserve/remove blanks toggle

Boris hit a real production bug testing the tagger UI against real documents: apply failed opaquely for two candidates whose blanks were split across multiple <w:t> runs in the actual XML (confirmed by reading the raw Sumas file -- an invisible formatting-size difference on 1-2 characters permanently splits a run in Word, even though it reads as one unbroken underscore blank on screen). Diagnosed live with Boris, then fixed both the immediate UX gap (opaque all-or-nothing failure) and the real underlying limitation (docx-surgeon refusing to splice across run boundaries at all) in the same session, plus added the preserve/remove-underscores product feature Boris proposed as a related but separate ask.

## What changed

- unitprep-api tagger.rs - /tagger/apply now validates every edit up front (is_editable_range) and returns exactly which candidate(s) failed and why, instead of an opaque apply_failed for the whole batch.
- docx-surgeon edit.rs/read.rs - apply_edits now splices an edit across multiple runs (keep the first run's lead-in + full replacement, empty every fully-consumed run including the last one's touched portion) instead of refusing. EditError::SpansMultipleRuns renamed NoMatchingRun -- now only fires for coordinates touching no run at all. New FlatText::is_editable_range/runs_touching.
- unitprep-tagger-pipeline lib.rs - SubstitutionStyle (Replace | InsertBeforeSpan) on to_edit -- an OM-facing choice between replacing a blank outright vs. inserting the tag before it and leaving the blank in place.
- unitprep-ui - preserve_blanks checkbox on TaggerResultsPage, wired through useTaggerApply to /tagger/apply's preserve_blanks field.


## Decisions

- Built the general multi-run-splice fix (not just the insert-mode workaround) even though the insert mode alone would have sidestepped the immediate bug -- Boris explicitly asked to 'find a solution to this formatting run issue' regardless of which underscore preference gets picked, confirmed via AskUserQuestion before starting.
- preserve_blanks lives as one checkbox per apply click (applies uniformly to every confirmed substitution in that call), not a per-candidate toggle -- Boris's own choice when asked, matches how this reads as a per-document style preference rather than a per-field one.
- SubstitutionStyle::InsertBeforeSpan is documented as only meaningful for blank-matched candidates (recognize_blanks), not literal-value matches (detect_candidates) -- inserting before an already-filled value would leave the old value sitting next to the new tag rather than replaced. Not yet a real problem since detect_candidates has no UI caller yet, but flagged for whenever it does.


## Learned

- A blank's underscore run splitting across multiple <w:t> elements in real Word documents is not rare or pathological -- it hit 2 of the 3 fields (u.num, m.secdep) in the very first real document a real user tried through this UI. Confirmed by reading the raw document.xml directly: the split runs differ only by an invisible w:sz (font size) attribute or a differing w:rsidRPr (revision id), both artifacts of someone having clicked mid-blank and retyped a character or two at some point in the document's editing history -- completely invisible on screen, only visible by inspecting the raw XML.
- A zero-width insert edit structurally can never hit the multi-run problem, since it only ever needs to resolve to whichever ONE run happens to touch its exact insertion point -- this is why 'preserve blanks' mode, chosen by Boris independently as a product preference, also happened to be a free workaround for the run-splitting bug in the one direction it applies (inserting before a blank), well before the general splice fix was built.


## Verification

Backend: 312 tests passing (up from 310), including new coverage for multi-run splicing (2-run and 3-run cases), the zero-width-insert-before-a-split-blank case, the still-refused no-matching-run case, and preserve_blanks end-to-end. Verified against the real Sumas file directly (throwaway, uncommitted example): all 5 real candidates, including the two that originally failed, now apply successfully. Frontend: tsc/eslint clean, vitest 291/291, full Playwright E2E suite 11/11 including a new test asserting the real request body sent to /tagger/apply carries preserve_blanks: true.


## Open

- detect_candidates (known-values path) still has no UI caller -- the InsertBeforeSpan-is-only-safe-for-blanks caveat is untested in practice until that's wired up.
- client_ops.tag_pattern still only has the 7 seeded patterns from three templates -- most real documents will still find few or no candidates until more patterns get added.
- All 3 commits (2 in unitprep-api, 1 in unitprep-ui) pushed to origin/main already this round -- not held back for confirmation this time since the fix was actively unblocking Boris's live testing.



_Recorded 2026-08-12T21:02:06.681Z from `bmaksimov` via the om MCP server (routing: caller)._
