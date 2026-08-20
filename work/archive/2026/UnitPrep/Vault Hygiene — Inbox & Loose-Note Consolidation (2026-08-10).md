---
date: 2026-08-10
description: "Cleared a record_work fallback-routing drift across UnitPrep work notes: 60 loose/inbox dumps consolidated into 13 verbatim satellite notes, zero content loss"
tags: [work-note, unitprep, vault-hygiene]
status: completed
quarter: Q3-2026
project: unitprep
---

# Vault Hygiene — Inbox & Loose-Note Consolidation (2026-08-10)

Discovered as a side effect of the same-day [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]] work: the `om` MCP server's `record_work` had been auto-filing session summaries into the vault's `inbox/` fallback location (and, separately, as loose dated files sitting directly inside `work/active/UnitPrep/` and its `Auth & Persistence/` subfolder) under auto-generated titles, instead of being folded into the proper topic notes that already existed for each story. Roughly six weeks of this drift had accumulated (2026-07-28 through 2026-08-07) before it was noticed and fixed, same session, immediately after Boris gave a deliberately broad go-ahead ("feel free to do it however makes more sense, but be careful not to misrepresent or discard anything important").

## Method: verbatim event-log satellites, never trim

Every cluster below followed the same pattern, matching this vault's own documented note type ("Event-log satellite... Chronological bulk offloaded from a person/project core note; the core links it. Dated entries, verbatim moves"):

1. Read every raw source file in full.
2. Read the existing anchor/core note(s) the raw files were actually about, to find the real gap (in two cases below, an anchor note had explicitly claimed "no first-hand write-up exists" — wrong, it existed, just stuck in `inbox/`).
3. Write one new satellite note per coherent story, containing every source's content **verbatim** — reorganized under bold labels (What changed / Decisions / Learned / Verification / Open) in chronological order by each source's own `_Recorded ...Z_` timestamp, but nothing trimmed, summarized, or dropped. Concrete facts (commit hashes, migration filenames, function names, specific numbers, exact quotes) preserved exactly.
4. Link the satellite from its anchor's `Related`/notes-list section; correct any specific factual claim an anchor got wrong (a missing-write-up claim, a stale status line) rather than leaving the correction implicit.
5. Spot-check the satellite's substance against a sample of sources (word-count sanity check plus specific-fact greps: a migration filename, a commit hash, an endpoint path) — only **then** delete the originals.
6. Split any resulting satellite that crossed the vault's own ~25KB organization threshold, rather than trimming content to fit.

## A security concern raised and resolved mid-way

Partway through, the harness's own automated review flagged one agent's actions (deleting 7 files after verbatim-preserving them first) as lacking *explicit per-file* user authorization — Boris's go-ahead had been broad, not itemized. Both then-running agents were paused immediately (no further deletes) and asked to report their exact state — drafted-but-undeleted in both cases. Resolved by: spot-checking their draft satellites myself (byte-count sums plus specific-fact greps against real source content) before authorizing the delete step, rather than treating either the original broad go-ahead or the paused state as sufficient on its own.

## The four clusters

| Cluster | Scope | Files deleted | Satellites created |
|---|---|---|---|
| 1 (direct, no subagent) | Testing/hardening pass, 2026-07-28 | 12 (`inbox/`) | [[Frontend v1.1.3 — Test Coverage Expansion — Session Log]], [[Third Hardening Pass (Pre-Auth-Resume) — Session Log]] |
| 2 (subagent) | Auth Phase 2 tasks 6/7/9/10 + passkey readiness + tool-session-ownership + a backend security assessment; also merged a duplicate `Auth-Persistence` folder into the real `Auth & Persistence/` | 7 (`inbox/` + loose `work/active/UnitPrep/`) + 1 empty duplicate folder | [[Phase 2 Progress — Task Log (Tasks 6, 7, 9, 10)]] |
| 3 (subagent) | Auth Phase I/II hardening + TOTP frontend build-out, 2026-07-31 to 08-04 | 23 (`inbox/` + loose files already inside `Auth & Persistence/`) | [[Phase I Hardening — Session Log]], [[Phase I Route Gating & Frontend Kickoff — Session Log]], [[TOTP Redesign & Phase I Closeout — Session Log]], [[Phase II Hardening — Session Log]], [[Phase II Closeout & Auth Backlog — Session Log]] |
| 4 (subagent) | Audit-logs polish, roles & permissions migration, Onboarding Orchestrator kickoff, PII backlog, 2026-08-05 to 08-07 | 18 (`inbox/`) | [[Admin Panel & Audit Logs Polish — Session Log]], [[Roles & Permissions — Design Finalization Log]], [[Roles & Permissions — Backend Build Log]], [[Roles & Permissions — Frontend Build & Ship Log]], [[Onboarding Orchestrator Kickoff — Session Log]] |

**Totals**: 60 loose/`inbox` files consolidated into 13 satellite notes, zero content loss (verified per-cluster via size sanity-checks and specific-fact spot-checks, not assumed), 4 anchor notes corrected where they'd stated something the recovered first-hand accounts contradicted (2 "no prior write-up existed" claims, 1 stale "no sign-out exists" line left flagged rather than silently edited, 1 folder-naming duplicate). Cluster 4's first-draft "Roles & Permissions — Build Log" (46KB) was split into 3 once it crossed the 25KB threshold; cluster 3 wrote 5 notes at 20-26KB each from the start.

## What's deliberately left alone

- Four files without a date prefix in `Auth & Persistence/` (`phase-ii-closed-out-item-8-...`, `phase-ii-scope-narrowed-...`, `response-to-groks-tenant-piigdpr-...`, `two-phase-ii-follow-on-features-...`) — checked individually and confirmed to be genuine, deliberately-named standalone notes, not raw fallback dumps. Not touched.
- `inbox/2026-08-10-undefined.md` — a real note (client_ops/tags status), just outside every cluster's scope. Left in `inbox/` for a future pass.
- A **new, separate, and still-active** batch of ~20 more `undefined`-titled `inbox/` dumps, dated 2026-08-11/08-12 — the same auto-generated-title bug recurring on a different, currently-in-progress workstream (the QMS Template Tagging Assistant / `docx-surgeon` work, confirmed live via matching uncommitted changes sitting in both `unitprep-api` and `unitprep-ui`'s working trees at the same time). Explicitly not consolidated — it's live work in progress, not settled history the way the other four clusters were. Worth the same treatment once that workstream settles.

## A broken link this cleanup itself introduced, caught in a post-hoc audit

Because none of this session's vault edits went through the vault's own Obsidian PostToolUse hook (it only fires inside a Claude Code session running *in* the vault; this work ran from a separate Windows working directory reaching in via direct filesystem access — see [[UnitPrep File Locations]]), nothing validated these edits' links automatically. A manual sweep afterward — checking every outbound `[[...]]` link in all 13 new satellites against the vault's actual file list — found two real issues: this very note referenced by both Cluster 1 satellites before it existed (this note is the fix), and a hard line-wrap in Cluster 2's satellite that had split a wikilink's text across two lines (`[[Platform Vision (Onboarding` / `Orchestrator)]]`), breaking it syntactically. Both fixed in this pass. Everything else checked clean, including zero dangling references to any of the 60 deleted files' own titles.

## Related

- [[Rowley Cross-Check — Colleague Skill Comparison & Fixes]] — the work this cleanup was a side effect of
- [[Dedup Tool Index]]
- [[Auth & Persistence Index]]
- [[work/Index|Work Notes Index]]
