---
date: "2026-09-28"
description: "Running backlog of specific, concrete CI check ideas identified during normal UnitPrep development — not being implemented now (solo developer, no CI/CD infrastructure yet), but recorded so nothing has to be rediscovered when CI eventually gets adopted"
tags:
  - brain
---

# CI Backlog

[[Compliance & Process Readiness]] already records the standing decision that CI/CD is deliberately deferred — pre-POC, solo developer, will likely be handed off to whichever team owns CI/CD for Quikstor's other software once there's a real team around this product. That decision doesn't change here.

This note is the narrower, concrete companion to that decision: as specific CI-check ideas come up during ordinary development (a code review flags something, a bug reveals a class of drift a check could catch, etc.), they get recorded here instead of implemented — so when CI/CD infrastructure eventually does get stood up, there's a ready-made punch list instead of having to re-derive it from scratch or re-discover ideas that already came up once.

**Standing rule going forward**: any time a CI-shaped idea surfaces (in a review, an audit, a bug postmortem, anything), add it here rather than building it, unless Boris explicitly asks for it to be implemented now.

## Backlog

### `unitprep-ui`: enforce generated types stay in sync with their Rust source

**Identified**: 2026-09-24, from an external code review (Grok) plus this session's own follow-up.

**The gap**: `unitprep-ui/types/generated/` is produced by `ts-rs` from Rust structs in `unitprep-api` (`UploadResponse`, `DiscoverResponse`, `ValidateResponse`, `AnalyzeResponse`, and their transitive dependencies — see [[Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation]]). `npm run generate-types` has to be run and its output committed by hand whenever a covered Rust struct changes. Nothing currently forces that — it already drifted silently once before ts-rs was adopted (a hand-mirrored `output_path` field removal broke at runtime, which is the whole reason ts-rs generation exists now).

**What the check would do**: in CI, after `unitprep-api` changes, re-run the generator and fail the build if the regenerated output differs from what's committed in `unitprep-ui`. Cross-repo, so it'd need to run wherever both repos are checked out together, or as a scheduled/manual cross-repo job rather than a simple per-repo hook.

**Why deferred**: solo developer, no CI runner set up at all yet. The manual-discipline version (remember to run `npm run generate-types` after touching a covered struct) is documented in `types/generated/README.md` and is working so far.

## Related

- [[Compliance & Process Readiness]] — the broader "CI/CD is deliberately deferred" decision this backlog sits under
- [[Patterns]] — the git branch-policy note anticipating a future `dev` branch "when the project starts considering CI/CD"
