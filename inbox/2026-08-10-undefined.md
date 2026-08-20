---
date: 2026-08-10
description: "Resolved an apparent vault contradiction about client_ops/tags status by reading the real repo. Ground truth: Phase 1 (client_ops schema, qms_tag cata"
tags:
  - project-note
source_repo: bmaksimov
---

# 

Resolved an apparent vault contradiction about client_ops/tags status by reading the real repo. Ground truth: Phase 1 (client_ops schema, qms_tag catalog seeded with 13 tags, full CRUD API, client_ops.manage_tags permission, client_ops.audit_log) is genuinely shipped on main (commits fa8e179, 0cb1a12, both 2026-08-07, ahead of the v1.6.0 version-bump commit). Phase 2 (rule-based candidate detection, a new template-tagger crate) genuinely has not started — Cargo.toml workspace members are only [core, unit-group, dedup]. The "Open Questions & Mismatches" note's 'Status 2026-08-08 — paused, nothing built yet' language was about Phase 2 only, but read ambiguously as if Phase 1 hadn't shipped either. Also found: unitprep-ui has zero tag-related files (no admin UI for the catalog yet), and CHANGELOG.md's [1.6.0] entry (already released) doesn't document the client_ops commits, which are sitting undocumented past the last version bump.







_Recorded 2026-08-10T16:34:59.577Z from `bmaksimov` via the om MCP server (routing: fallback)._
