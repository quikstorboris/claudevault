---
date: "2026-09-28"
description: "Backlog of specific CI check ideas that don't yet have a home in a Tier of UnitPrep CI-CD Framework — recorded so nothing has to be rediscovered as the framework's later tiers get built"
tags:
  - brain
---

# CI Backlog

> [!note] Superseded in part, 2026-09-28
> This note originally recorded the whole "CI/CD is deliberately deferred, solo developer" position. That's no longer the full picture: [[UnitPrep CI-CD Framework]] now exists as the actual living design — Tier 0 (local `preflight.sh` in both repos) is built and shipped, Tiers 1-2 (remote CI, multi-dev gates) are fully designed and deliberately dormant. [[Compliance & Process Readiness]] still holds for the governance-level question (no formal delivery process, no second reviewer), but "CI is deferred" as a blanket statement is stale — check the framework doc first.

This note is now specifically for check ideas that don't yet have an obvious home in one of the framework's tiers — usually because they're cross-repo (like the entry below) or otherwise don't fit a simple per-repo hook shape. As specific CI-check ideas come up during ordinary development, they get recorded here; once the framework's later tiers actually get built, each one gets slotted into wherever it fits rather than re-derived from scratch.

## Backlog

### `unitprep-ui`: enforce generated types stay in sync with their Rust source

**Identified**: 2026-09-24, from an external code review (Grok) plus this session's own follow-up.

**The gap**: `unitprep-ui/types/generated/` is produced by `ts-rs` from Rust structs in `unitprep-api` (`UploadResponse`, `DiscoverResponse`, `ValidateResponse`, `AnalyzeResponse`, and their transitive dependencies — see [[Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation]]). `npm run generate-types` has to be run and its output committed by hand whenever a covered Rust struct changes. Nothing currently forces that — it already drifted silently once before ts-rs was adopted (a hand-mirrored `output_path` field removal broke at runtime, which is the whole reason ts-rs generation exists now).

**What the check would do**: re-run the generator and fail if the regenerated output differs from what's committed in `unitprep-ui`. Doesn't fit either repo's own Tier 0/1 cleanly since it needs both repos checked out together — explicitly named as out of scope in [[UnitPrep CI-CD Framework]] for exactly that reason, its own separate shape of problem.

**Built 2026-09-30** (`unitprep-api` `v1.9.50`, `unitprep-ui` `v1.6.48`; in both repos `scripts/preflight.sh` is now 9 steps): `unitprep-api/scripts/check_ts_bindings.sh` runs the same `cargo test export_bindings` generation into a temp dir and diffs it against `unitprep-ui/types/generated` (hand-written `README.md`/`index.ts` excluded; a stale extra file counts as drift). Wired as preflight step 9/9 in both repos (sibling checkout, skips if absent) and as a tag-push step in `unitprep-api`'s `full-tests` CI job against a checkout of `unitprep-ui` `main` -- tag-only on purpose, since checking every push would fail in the gap between the API commit and the UI commit. The cross-repo checkout needs no token only because `unitprep-ui` is public; making it private would need a secret, which `check_workflow_secrets.sh` would block until deliberately updated. Negative-tested (modified file, stale file, missing sibling). Covers only structs marked `#[ts(export)]`; hand-mirrored shapes in `types/api.ts` remain unchecked. Not yet seen in a live CI run.

**Previous mitigation (still valid as the fix procedure)**: the manual-discipline version (remember to run `npm run generate-types` after touching a covered struct) is documented in `types/generated/README.md` and is working so far.

## Related

- [[UnitPrep CI-CD Framework]] — the actual tiered design; check here first
- [[Compliance & Process Readiness]] — the broader delivery-process/governance decisions this backlog sits under
- [[Patterns]] — the git branch-policy note anticipating a future `dev` branch "when the project starts considering CI/CD"
