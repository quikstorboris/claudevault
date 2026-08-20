---
date: 2026-08-11
description: "Decisions from Boris on the QMS Template Tagging Assistant: (1) Dropping .doc (legacy binary Word format) support entirely -- OMs will be asked to res"
tags:
  - project-note
source_repo: bmaksimov
---

# 

Decisions from Boris on the QMS Template Tagging Assistant: (1) Dropping .doc (legacy binary Word format) support entirely -- OMs will be asked to resave as .docx before uploading, not worth building real binary .doc parsing for what's turned out to be a rare case (1 of 9 sample documents so far). (2) Checkbox/boolean field handling (military-status Yes/No, insurance opt-in/opt-out -- found recurring across 4+ of 9 real sample documents) is explicitly deferred/vaulted for later, not blocking current work -- our tier-1/2/3 design assumes text substitution and has no representation for "check this box" yet, needs its own design pass when picked back up.







_Recorded 2026-08-11T00:15:41.135Z from `bmaksimov` via the om MCP server (routing: fallback)._
