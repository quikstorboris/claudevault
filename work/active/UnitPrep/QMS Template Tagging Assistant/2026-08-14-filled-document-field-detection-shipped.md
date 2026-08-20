---
date: 2026-08-14
description: "Diagnosed why /tagger/check found zero candidates for a real filled rent late-notice letter (first_late_notice.docx): the tool only ever detected blan"
tags:
  - project-note
source_repo: bmaksimov
---

# Template Tagger now recognizes fields in already-filled documents, not just blank templates

Diagnosed why /tagger/check found zero candidates for a real filled rent late-notice letter (first_late_notice.docx): the tool only ever detected blank underscore runs or known literal values, neither of which exist in a document where every field is already filled with real content. Built recognize_filled_values (template-tagger crate) to propose the value sitting next to a recognized label even when it's not blank, wired it into tagger-pipeline::find_candidates forced to always need review, and seeded 3 real label patterns from the actual letter. Verified end-to-end against the real file: now finds facility name, tenant name, and unit number. Also fixed an unrelated but adjacent bug found in passing: a duplicate e.zip tag_key in the QMS catalog (should have been e.post).

## What changed

- template-tagger/src/recognize.rs - added recognize_filled_values(): for each label_proximity pattern with no blank nearby, proposes the label-adjacent real text instead, bounded by whichever comes first -- a paragraph break (\n, which read_docx already inserts between paragraphs), a tab, another matched label's position, or max_gap_chars. Returns None rather than a truncated fragment if no real boundary is found within budget. 11 new tests.
- template-tagger/src/lib.rs - exported recognize_filled_values alongside recognize_blanks/detect_candidates
- tagger-pipeline/src/lib.rs - find_candidates now also calls recognize_filled_values per region; every candidate from it is forced into ConfidenceTier::NeedsReview via a force_review flag threaded through the raw candidate tuple, regardless of span competition -- a boundary guess is inherently less certain than an exact blank or known-value match. 2 new/updated tests.
- migrations/20260814220000_seed_filled_value_late_notice_patterns - seeded 3 real label_proximity patterns (f.name via 'FROM:', e.name via 'TO:', u.num via 'Unit') measured against the actual late-notice letter's flattened text, applied to dev DB
- migrations/20260814210000_remove_duplicate_zip_tag_keys - removed e.zip (Tenant category), an accidental duplicate of the already-correct e.post added by an earlier production-sweep migration; no code or tag_pattern row referenced it


## Decisions

- Chose 'value ends at the nearest real boundary (\n/\t/another label), or nothing at all' over 'truncate at max_gap_chars' -- discovered mid-implementation that docx_surgeon::read_docx already inserts \n between paragraphs (confirmed by actually running read_docx against the real file, not by re-deriving from the raw XML by hand -- my own first manual extraction attempt was wrong and suggested paragraphs had zero separator, which would have meant a much bigger docx-surgeon change was needed; the real behavior was already there). Falling back to an arbitrary budget cutoff would silently truncate mid-word (e.g. 'No K' out of 'No Ka Oi Self Storage') and read as a confident wrong answer instead of no answer.
- Scoped new pattern authoring (f.name, e.name, u.num) to template-tagger's already-locked 'safe scope' (name/address/phone/email/DL#/unit number) -- deliberately did NOT add patterns for the rent amount ($303.66) or Total Amount Due, even though both are real, cleanly-labeled fields in this letter, because they'd be l.* tags and the crate's own doc comment locks out m.*/l.*/d.* context-dependent tags until a real disambiguation mechanism exists. Left that gap for whoever tackles that mechanism, rather than quietly working around a documented boundary.
- Every recognize_filled_values candidate is forced to ConfidenceTier::NeedsReview unconditionally (not just when it competes with another candidate for the same span) -- a boundary guess is categorically less certain than recognize_blanks' self-delimiting blank match or detect_candidates' exact literal match, so it should never auto-apply even when it's the only candidate for its span.
- e.a.zip vs e.a.post (the identical duplicate-tag bug, one category over from e.zip/e.post) was found but deliberately NOT touched -- flagged to Boris as a separate open question rather than fixed opportunistically, since he only asked about e.zip specifically.



## Verification

cargo fmt --all -- --check, cargo clippy --workspace --all-targets, cargo test --workspace all clean -- 561 tests total, 0 failed, 3 ignored (expected). Additionally ran a scratch #[ignore]d test (not committed) that read the real first_late_notice.docx via read_docx and ran find_candidates with the 3 newly-seeded patterns: confirmed 3 real candidates found (f.name="No Ka Oi Self Storage", e.name="ABM PARKING SERVICE", u.num="1000"), all correctly tiered NeedsReview.

## Open

- Rent amount ($303.66) and Total Amount Due (0.00) in the same letter are real, cleanly-labeled fields left untagged on purpose -- both are l.* (Lease) tags, and template-tagger's locked scope excludes m.*/l.*/d.* context-dependent tags until a real move-in-vs-lease disambiguation mechanism exists. Whoever builds that mechanism should revisit this letter as a ready-made test case. Logged as a research item, with the concept-pair table and a to-fill tracking table, in [[QMS Template Tags — Open Questions & Mismatches]] -- Boris needs to check which real client templates actually exercise both sides of the m.*/l.*/d.* pairs before this can be resolved.
- e.a.zip vs e.a.post (Alternate Contact category) is the identical duplicate-tag bug as e.zip/e.post, found in passing but not fixed -- needs Boris's explicit call the same way e.zip did.

## Related

- [[2026-08-11-confidence-tiers-full-http-backend-for-the-qms-template-tagg|Confidence tiers + full HTTP backend for the QMS Template Tagger]]
- [[2026-08-14-milestone-8-audit-polish-shipped|Milestone 8 audit polish]]
- [[QMS Template Tags — Open Questions & Mismatches]] -- where the m.*/l.*/d.* research item and tracking table live
- [[QMS Template Tags — Catalog & Editor Design]] -- the tag-family legend (e.a.*, m.*/l.* duality) this session's answers were drawn from
- [[2026-08-17-preserve-underscores-dialog-shipped|Preserve-underscores dialog shipped]] -- the next session's blank-substitution UX work on this same tool
- [[Gotchas]]

_Recorded 2026-08-14T21:33:56.579Z from `bmaksimov` via the om MCP server (routing: fallback)._
