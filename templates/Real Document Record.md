---
date: "{{date}}"
description: "{{one sentence: what the document is and what it taught us}}"
project:
status: active
tags:
  - real-document
  - fixture
---

# Real Document Record - {{title}}

Written for Claude: exact over narrative, long over short. Rule: [[Real Documents Are the Spec]].

## 1. Provenance
- Original path / URL:
- Obtained (date, from whom):
- Produced by (system / app / export):
- Size / SHA-256:
- Repo fixture path:
- Fixture is: original | redacted copy (what was redacted, how values were replaced):

## 2. Structure facts (measured, not remembered)
<!-- docx: text boxes, tables, groups, underlined tabs, underscore runs, Fallback copies, page size/margins.
     csv/xlsx: header row verbatim, delimiter, encoding, row count, sheet names.
     json/api: top-level keys, notable shapes. Include the command that produced each number. -->

## 3. Field-by-field table
| Location | Label / column | Meaning | Tag or mapping | Tier | Why |
|---|---|---|---|---|---|

Fields deliberately left alone, and why:

## 4. Decisions
<!-- Who decided, in their words where given; reasoning; alternatives rejected. -->

## 5. Expected output
- `expected.json` path:
- Reproduce with:
- Applied-output checks (tags that must appear, text that must stay byte-identical):

## 6. Open questions and known gaps
<!-- Each with the concrete thing that would resolve it. -->

## 7. Raw excerpts
<!-- Smallest verbatim XML / CSV / JSON fragments that explain a surprising behavior. -->

## 8. Links
- Commits / versions:
- Session work note:
- Related records:
