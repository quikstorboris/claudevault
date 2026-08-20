---
date: 2026-08-14
description: "Closed the two remaining M7 items from the third audit's fix plan (the Template Tagger UI test suite item was already done separately by Boris on 2026"
tags:
  - project-note
source_repo: bmaksimov
---

# Milestone 7 (test-coverage debt) shipped — unitprep-api v1.8.5

Closed the two remaining M7 items from the third audit's fix plan (the Template Tagger UI test suite item was already done separately by Boris on 2026-08-14): round-trip and missing-column tests for dedup's ingest.rs, and direct tests for tagger.rs::check's two DB-free branches. Backend-only milestone, no frontend changes. Done directly by the main session, not delegated, given the small scope (2 items, ~4 tests).

## What changed

- dedup/src/ingest.rs - added a round-trip test (headers -> TenantRecord, confirming an unrecognized/absent column defaults to blank rather than erroring) and a test for the required-FirtLast-column error path
- src/api/tagger.rs (via tagger_tests.rs) - added check_tests module with two tests: no-file-uploaded (400) and a file that fails to parse as a .docx (400). Both reachable without touching the DB, unlike the happy path and the MAX_CANDIDATES cap which both require the pattern-library lookup (begin_rls_transaction + load_label_proximity_patterns) to succeed first


## Decisions

- Scoped tagger.rs::check's new coverage to only the two branches reachable before the DB round trip, rather than writing an #[ignore]d real-DB test (the M3 precedent for query_session) to reach the MAX_CANDIDATES/success paths. Reasoning: crafting a real pattern-library fixture with enough rows to trigger a 2000+ candidate count for a genuine end-to-end test was judged not worth the setup complexity for this pass -- the two DB-free branches were the actual zero-coverage gap the plan flagged, and were closed cleanly using the exact same real-Multipart-construction convention upload_tests.rs already established.
- Reused (duplicated) the multipart_from/file_part/closing_boundary test-helper pattern from upload_tests.rs locally in tagger_tests.rs's new check_tests module rather than extracting a shared test helper -- now duplicated in exactly 2 places. Flagged as a minor, low-priority DRY opportunity per the standing architecture-discipline instruction, not acted on since it's test-only scaffolding and out of this milestone's stated scope.



## Verification

cargo fmt --all -- --check, cargo clippy --workspace --all-targets, cargo test --workspace all clean -- 550 tests total (546 + 4 new), 0 failed, 3 ignored (expected).



## Related

- [[2026-08-14-milestone-6-file-splits-shipped]]
- [[2026-08-14-milestone-5-dry-consolidation-shipped]]
- [[2026-08-14-milestone-8-audit-polish-shipped|Milestone 8]]


_Recorded 2026-08-14T18:18:11.419Z from `bmaksimov` via the om MCP server (routing: fallback)._
