---
date: 2026-08-17
description: "Two related changes to the QMS Template Tagging Assistant's blank-substitution UX, per Boris's direct request. First confirmed the exact mechanics via"
tags:
  - project-note
source_repo: bmaksimov
---

# Template Tagger: preserve-underscores checkbox replaced with conditional dialog; PreserveBlank now underlines the tag too

Two related changes to the QMS Template Tagging Assistant's blank-substitution UX, per Boris's direct request. First confirmed the exact mechanics via a clarifying question (dialog preview) before touching code, since "keep tags underscored" was ambiguous between the already-existing Replace-style underline behavior and the PreserveBlank (centered) path. Backend: PreserveBlank now underline-formats the tag it centers inside a blank's remaining underscores, matching Replace's own blank-case behavior, while leaving PreserveBlank on an already-filled (non-blank) value untouched (still plain text, nothing to underline there). Frontend: removed the always-visible "Preserve underscores" checkbox, replaced with PreserveUnderscoresDialog -- shown only when the document actually has at least one underscore-blank candidate, gating the Apply click.

## What changed

- tagger-pipeline/src/lib.rs - to_edit's PreserveBlank branches now build an UnderlineEdit (not a plain Edit) when the candidate being centered is a real blank (is_underscore_run), in both the fits-inside-blank and degrades-to-full-replace cases; unchanged (still plain) when centering inside an already-filled detect_candidates value. Updated 2 existing tests to the new expected XML, added a new test locking in the non-blank case stays plain.
- components/tagger/PreserveUnderscoresDialog.tsx (new, unitprep-ui) - modal shown only when the document has an underscore-blank candidate; Preserve/Replace/Cancel, calls back into TaggerResultsPage's existing handleApply with the chosen preserve_blanks value
- components/TaggerResultsPage.tsx - removed the always-visible checkbox and its preserveUnderscores state; added hasBlankCandidates (checks whether ANY candidate's matched_text is an underscore run, mirroring tagger-pipeline's own is_underscore_run) and gates the Apply button through the new dialog only when true
- e2e/tagger-flow.spec.ts - updated both tests that reach the Apply button to click through the new dialog (Preserve underscores / Replace outright) instead of checking a checkbox first


## Decisions

- Asked a clarifying question (AskUserQuestion, with a before/after text preview) before writing any code: 'keep tags underscored as well' was genuinely ambiguous between confirming already-existing Replace-style underline behavior vs. extending it to the PreserveBlank path too. Boris chose 'underline the tag too' for PreserveBlank -- this was the actual, real code change; without asking, I'd likely have assumed the request was already satisfied by existing behavior and shipped nothing.
- Scoped the dialog trigger to document-level (any candidate is a blank), not selection-level (only checked/confirmed candidates) -- matches Boris's literal framing ('for documents that DO have underscores'), and is simpler than re-deriving the trigger from the confirmed set every time a checkbox toggles.
- Did not touch a dev server already running on port 3000 (PID discovered mid-session, not started by this session) when Playwright's e2e run tried and failed to start its own -- verified the e2e edits via tsc's own type-check of e2e/ instead (tsconfig includes **/*.ts) plus full reasoning through the test's fixture data, rather than risk disrupting what might be Boris's own active dev session.



## Verification

Backend: cargo fmt --all -- --check, cargo clippy --workspace --all-targets, cargo test --workspace all clean -- 563 tests, 0 failed, 3 ignored (expected). Frontend: npx tsc --noEmit (clean, includes e2e/ per tsconfig), npx eslint . (0 errors, 1 pre-existing unrelated warning), npx vitest run (47 files, 333 tests, all passing including 3 new tests for PreserveUnderscoresDialog). Playwright e2e NOT run live -- a pre-existing dev server on port 3000 (not started this session) blocked Playwright's own webServer launch; deliberately did not kill it. e2e test edits verified via tsc type-checking and manual trace against the fixture data instead.

## Open

- The Playwright e2e suite (`e2e/tagger-flow.spec.ts`) was updated but never actually executed against a real browser this session -- a pre-existing `next dev` on port 3000 (not started by this session, likely Boris's own) blocked Playwright's own webServer launch, and it was deliberately left untouched. Worth a real `npx playwright test` run once that server is free, to confirm the dialog flow works end-to-end, not just type-checks.

## Related

- [[2026-08-14-filled-document-field-detection-shipped|Filled-document field detection]] -- same QMS Template Tagging Assistant work, the session immediately before this one
- [[2026-08-11-confidence-tiers-full-http-backend-for-the-qms-template-tagg|Confidence tiers + full HTTP backend for the QMS Template Tagger]] -- where PreserveBlank/Replace and the original checkbox were first built

_Recorded 2026-08-17T20:50:25.982Z from `bmaksimov` via the om MCP server (routing: fallback)._
