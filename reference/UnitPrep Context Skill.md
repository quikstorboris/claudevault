---
date: 2026-07-27
description: A portable Claude Skill packaging full UnitPrep context exists on disk — load it instead of re-deriving context, but check it's registered and know it's stale.
tags: [reference, unitprep, skill]
---

# UnitPrep Context Skill

A Claude Skill named `unitprep-context` exists at:

`C:\Users\bmaksimov\OneDrive - Kobre Holdings, LLC\Documents\unitPrepDocumentation\Skills\unitprep-context.skill`

Built 2026-07-15 from an earlier session's accumulated context. Unlike memory (which is personal to this Claude account and auto-loads only in Boris's own sessions), this is **portable** — invokable by name, shareable, usable by any Claude session including a future teammate's.

## Contents

`SKILL.md` + four detail files, load only what's relevant:

- `architecture.md` — current Cargo workspace structure, pipeline, session engine
- `principles.md` — the project's own stated engineering/development/product principles
- `decision-history.md` — why things are shaped the way they are, including the header-normalization bug class and the never-fake-a-zero-value-success rule
- `workflow.md` — commit cadence, commit message style, the 250-line check, treat-external-review-as-a-collaborator posture

## Registration

**If asked to work on UnitPrep and this skill isn't already visible/triggered, check whether it needs to be installed/registered.** The duplicate-tenant-check skill in the same folder auto-registered as an invokable skill after being referenced once — the same is expected here, but verify rather than assume.

## Currency vs. memory

See [[UnitPrep Architecture Overview]] for the same information in memory/vault-note form, which is kept in sync going forward as things change. **If the two ever disagree, the vault note is likely more current** — it gets updated every session, while the skill file is a static snapshot as of 2026-07-15 and needs manual refreshing.

**Now significantly stale as of 2026-07-16** — the skill file predates the entire dedup crate build/mount, the `unit-group` extraction (both phases), and the "Client Prep" platform vision (see [[Platform Vision (Onboarding Orchestrator)]]). If a teammate or future session actually needs the portable skill to be current, it needs a real refresh pass, not a light touch-up — treat the vault notes ([[UnitPrep Architecture Overview]], [[Dedup Tool Index|Dedup Tool]], [[Code Review Watchlist]], [[Platform Vision (Onboarding Orchestrator)]]) as the authoritative source until that happens.

## Related

- [[UnitPrep Architecture Overview]]
- [[Platform Vision (Onboarding Orchestrator)]]
- [[Dedup Tool Index|Dedup Tool]]
- [[Code Review Watchlist]]
