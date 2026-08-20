---
date: 2026-07-28
description: "When a file is both line-heavy AND mixes multiple distinct concerns or responsibilities (long-but-single-purpose is NOT a match — the trigger is…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-28T21:31:35.074Z"
scope: general
projects: []
confidence: unverified
---

# Proactively split/modularize line-heavy files that mix multiple concerns — don't wait to be asked

When a file is both line-heavy AND mixes multiple distinct concerns or responsibilities (long-but-single-purpose is NOT a match — the trigger is length combined with mixed concerns), treat splitting/modularizing it as standing default behavior rather than something to flag and wait on. Extract cohesive sub-functions or sub-modules along concern boundaries, following whatever convention the codebase already uses for similar splits (e.g. this project's own pattern of extracting `_tests.rs` via `#[path]`, or pulling a picker/summary component out of a page component).

Apply this proactively during code review, bug-hunting, or general exploration in any repo — not only when a refactor is explicitly requested. When you spot the pattern but aren't already touching that file as part of the current task, name a concrete extraction plan (which functions/components move where) rather than a vague "this file is big" comment, so it's actionable the next time someone picks it up.

This generalizes beyond any one repo: it's a rule about how to treat file organization whenever it's noticed, not a project-specific style preference.

## Related

- [[Post-Refactor Audit - Details]]
