---
date: 2026-08-12
description: "Fixed three live-testing bugs in the QMS Template Tagging Assistant and shipped to prod: (1) redesigned SubstitutionStyle::PreserveBlank to center the"
tags:
  - project-note
source_repo: bmaksimov
---

# 

Fixed three live-testing bugs in the QMS Template Tagging Assistant and shipped to prod: (1) redesigned SubstitutionStyle::PreserveBlank to center the tag inside the matched blank (splitting leftover underscores evenly on both sides) instead of inserting it before the span — the user explicitly wanted centered placement, not prepend; degrades to full replace when the blank is too short. (2) Added a PrecedingAnchor mechanism to label_proximity patterns: a pattern can now require a distinct anchor label within a measured character window immediately before it, solving the case where a bare label (ADDRESS:, PHONE, EMAIL ADDRESS) is reused verbatim for both the occupant and their alternate contact in the real Sumas Mini Storage template — previously these were skipped entirely for ambiguity. (3) Seeded 9 more label_proximity patterns from real corpus measurements: 4 unanchored (DATE, CONTACT PHONE, STATE, ALTERNATE NAME — verified unique/unambiguous, had been skipped out of excess caution in the first seed pass) and 5 anchored (e.address/e.a.address/e.email/e.a.email/e.a.phone), bringing the pattern library to 16 total. Also explained (not a bug) that post-export line-shift is expected Word reflow from the template's tab-based layout, not something the tagger causes. All work verified via full workspace test suite (15 suites green) + clippy clean, committed as 3 commits (b12475b, 320ea46, abda69b) pushed to origin/main, and both new seed migrations applied to prod (previously only the first 7-pattern batch had been synced to prod — confirmed via `sqlx migrate info` that these two were the only pending ones, then applied and re-verified installed).







_Recorded 2026-08-12T22:09:17.940Z from `bmaksimov` via the om MCP server (routing: fallback)._
