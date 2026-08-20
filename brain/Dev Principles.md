---
date: "2026-08-13"
description: "The ~15 code-quality/security/workflow principles actually enforced across UnitPrep work, compiled from Patterns, Key Decisions, and repeated audit practice"
tags:
  - brain
---

# Dev Principles

Compiled 2026-08-13 from three sources that had never been pulled together before: the scoring language repeated verbatim across all three [[UnitPrep Architecture Overview|UnitPrep]] CTO-grade audits ("elegance, bloat, coherence/splitting of line-heavy files, efficiency, performance, overengineering, future-readiness"), the concrete house rules already in [[Patterns]], and things watched being enforced repeatedly across this session's own audit-and-fix work. No single document held all of this before now — this note is that document, so it can be recalled directly instead of re-derived each time.

Boris asked for this after a 3rd audit + fix pass, expecting "about 15" — it landed at exactly 15.

## Code quality

1. **Elegance** — code reads as intentional, not accidental.
2. **Maintainability** — an unfamiliar developer can extend it without archaeology.
3. **Modularity / separation of concerns** — one file, one concept.
4. **Leanness, no bloat** — nothing built for a hypothetical future need.
5. **File-size discipline** — flag (don't auto-split) files approaching ~250 lines; split only when there's a genuinely separable concept inside, never by mechanical line count alone. See [[Patterns]]'s original statement of this rule.
6. **DRY, actually enforced** — a shared helper only counts if every call site adopts it. Every audit this project has run found helpers built once and not reused everywhere they applied.
7. **Efficiency without premature optimization** — watch clones/allocations/algorithmic complexity, but don't over-engineer for load that doesn't exist yet.

## Security & correctness

8. **Defense in depth, redundant by design** — an app-level check *and* a DB-level RLS policy/constraint, so one forgotten layer isn't total exposure.
9. **Least privilege** — grant exactly what a role/service needs (e.g. `app_service` holding column-level `UPDATE` grants, not table-level).
10. **Don't build a control until it's real** — dual-approval, extra roles, etc. wait for the second actual actor that would make them function; before that, it's theater. See the Roles & Permissions "Manager role" decision in [[Key Decisions]].
11. **Name gaps honestly** — an "alert" with no notification service is an in-app indicator, said plainly, not oversold as the bigger thing it isn't yet. See the dormant-account-alert decision in [[Key Decisions]].

## Verification

12. **Verify empirically, not just by reading code** — real browser/curl/live-DB checks catch what static review can't. Three confirmed instances so far: the CORS-credentials bug (post-refactor audit), the frontend auth-check race (third audit), and a migration that had been committed but never actually applied to the dev database (found only by running a real-DB integration test, third audit's fix pass).
13. **Every real bug gets a regression test** — one that actually reproduces the failure mode, not a cosmetic assertion.

## Workflow

14. **Commit cadence: batch, don't checkpoint** — work through to a real milestone before committing; when asked for "coherent commits" on already-finished work, split by actual concern, not by file. Full technique (including how to split commits when concerns share a file) in [[Patterns]].
15. **Structured, greppable logging** — named `tracing` fields, never interpolated free-form strings. Boris's own words: "I like all things 'greppable'."

## Related

- [[Patterns]] — several of these principles' fullest statements live here; this note is the compiled index, Patterns often has the deeper "why" and incident history.
- [[Key Decisions]] — worked examples of #10 and #11 in practice.
- [[North Star]] — links here from its Aspirations section.
