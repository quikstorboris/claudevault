---
description: "Recurring patterns and conventions discovered across work — architecture, naming, tooling, and implementation patterns"
tags:
  - brain
---

# Patterns

Recurring patterns discovered across work.

## This vault: a fix to `.claude/scripts/` is only half-done until it is mirrored into `.shardmind/templates/`

The vault vendors its own template at `.shardmind/templates/`, and `/om-vault-upgrade` applies *from there*. So infrastructure code exists in two places — the live copy under `.claude/scripts/` and the template copy under `.shardmind/templates/.claude/scripts/` — and a fix applied to only the live copy has an expiry date: the next template re-apply silently reverts it, with no error and no diff to notice.

**How to apply**: when editing anything under `.claude/scripts/` (hook scripts, `om-mcp.mjs`, `lib/`, `tests/`), copy the same change into `.shardmind/templates/.claude/scripts/` in the same pass, then `diff -q` both files to prove they agree. The same goes for root-level infrastructure (`AGENTS.md`, `GEMINI.md`, `.codex/`, `.gemini/`) — the manifest's `infrastructure` list is the set of files this applies to.

**Why**: found 2026-07-29 fixing the qmd `pathKey` bug (see [[Gotchas]]). The live fix worked; the vendored template still carried the buggy version, so the fix would have vanished on the next upgrade and the silent-search-failure would have returned with no record of the cause. The same pass also found `AGENTS.md`, `GEMINI.md`, `.codex/hooks.json` and `.gemini/settings.json` missing from the vault root entirely while present in the template — 3 failing tests, and Codex/Gemini sessions running with no vault instructions at all.

## UnitPrep: git branch policy — main only

Never create a new branch in `unitprep-api` or `unitprep-ui`, locally or on the remote, under any circumstance short of Boris explicitly requesting one. Everything stays on `main`. Treat this as a hard rule, not a case-by-case judgment call — if something seems to genuinely need isolation, say so and ask first, don't create it and explain after.

**The one anticipated exception**: Boris will introduce a `dev` branch himself, explicitly, when the project starts considering CI/CD ("waaaay down the line," his words). Don't propose this proactively.

**Why**: reinforced 2026-07-23 after a stray branch (`claude/orchestrator-db-organization-psnq8b`, authored as `Claude <noreply@anthropic.com>`, origin never conclusively identified) sat unmerged on `unitprep-api`'s origin for part of a day and caused a full-codebase review done from that branch's checkout to miss two full days of real feature work already on `main` — see [[Gotchas]] for the incident itself. Boris's own reasoning: he can't keep up with tracking commits spread across branches, so a second branch existing at all is the problem, independent of its content.

**How to apply**: every git operation in these two repos targets `main`, full stop. A local Agent/Task tool call with `isolation: "worktree"` or `"remote"` is still fine for purely local, ephemeral scratch work that never touches the shared GitHub remote — but nothing gets pushed to, or left on, a branch other than `main` on either repo's origin without Boris asking first.

## UnitPrep: "prep coherent commits" is a distinct request from the standing batch-commit rule, and needs its own technique

The standing rule below ("batch, don't checkpoint") is about *when* to
commit during a single work session — not what to do when explicitly
asked to split already-finished, uncommitted work into multiple
well-scoped commits. When Boris asks for "coherent commits" (2026-08-05),
that means real per-concern commits, not one giant dump — even when the
underlying edits were made in one continuous pass across overlapping
files.

**The technique that works when concerns share files** (e.g. one file's
diff mixes an early round's audit-plumbing change with a later round's
role-match-arm addition): reconstruct intermediate states by *temporarily
reverting* the later round's edits back to a known-good earlier state
(using the exact content already produced during the session, re-applied
via `Write`/`Edit`), commit that as the earlier commit, then restore the
later round's edits on top and commit that separately. Verify
build+tests pass at *each* intermediate state before committing it — that
property (every commit compiles and passes its own test suite) matters
more than perfect hunk-level atomicity, and is what actually makes a
history bisectable. New files (never partially staged) and pure
migrations split naturally along these same boundaries with no
reconstruction needed.

**Don't reach for `git add -p` for this** — non-interactive tool
environments can't reliably drive it, and the hunk-selection risk (a
wrong y/n silently mis-splits a file) is worse than the cost of
reconstructing content directly, which is fully deterministic since the
exact text of every intermediate state is already known from having
written it earlier in the same session.

## UnitPrep: commit cadence — batch, don't checkpoint

Don't make incremental checkpoint commits during multi-step UnitPrep development work, even when a step is complete, tested, and would otherwise be a reasonable commit boundary. Keep working through the full planned sequence and only commit once the work reaches something version-eligible (a real release-worthy milestone).

**Why**: explicit correction (2026-07-14, during the workspace/crate-split migration) after offering to commit a verified, passing mid-migration checkpoint — Boris would rather batch changes than have many small in-progress commits.

**How to apply**: don't propose or make a commit mid-task by default; wait for an explicit go-ahead or an actual milestone boundary. This is a stricter, project-specific version of the general rule to never commit without being asked.

## UnitPrep: commit message style — dry and technical, no provenance

Keep UnitPrep commit messages dry, technical, and focused on what changed and why — never mention where a finding came from ("an external review flagged...", "Grok noted...").

**Why**: explicit correction (2026-07-15) after a draft commit message opened with "An external architecture review (Grok) flagged that...". Provenance like that belongs in conversation/memory, not permanent commit history.

**How to apply**: when a fix originates from an external review/analysis (another AI tool, a colleague's comment, etc.), describe the technical problem and fix directly — skip the "X flagged this" framing entirely.

## UnitPrep: keep server logs greppable

Whenever adding or improving a server log line in `unitprep-api`, keep it structured and greppable — consistent field names (`session_id`, `file`/`file_name`, `error`, etc.) via `tracing`'s structured fields rather than free-form interpolated strings.

**Why**: Boris said this explicitly (2026-07-16): "I like all things 'greppable'. let's keep that in mind every time we improve our log." A standing preference, not scoped to one fix.

**How to apply**: any time a `tracing::warn!`/`error!`/`info!` call is added or touched, use named structured fields — treat "is this greppable" as a real review criterion going forward.

## UnitPrep: flag modules approaching ~250 lines

Whenever a single source file in `unitprep-api` or `unitprep-ui` is approaching or has crossed roughly 250 lines, explicitly flag it and ask whether it should split — don't silently keep adding to it. Not a hard cap: overage is fine when warranted and elegance/maintainability are preserved. The obligation is to *flag and review*, not to reflexively split.

**Why**: Boris asked for this as a standing check (2026-07-09), matching the project's own precedent of splitting `analysis.rs` after it grew into a god-module.

**How to apply**: check line count when writing to, extending, or reviewing a source file in either repo; only split when there's a genuinely separable concept living inside the file. Not a mandate to proactively audit the whole codebase unprompted every session.

**Applied at scale 2026-07-24** during a full-codebase review + 9-milestone refactor — see [[Full Review & 9-Milestone Refactor]] — which split `discover.rs` (612→4 files), `fingerprint.rs` (681→3 files), `note_composer.rs` (472, partial split), `ScanResultsPage.tsx` (2392→690), `UnitFileResolutionPanel.tsx` (983→122), `DiscoveryPage.tsx` (924→436), `unit-groups/page.tsx` (360→75). `csv_export.rs`/`export.rs` (~363/~299 lines) were reviewed and deliberately left as-is — cohesive enough despite the length. Treat any newly-large file found later as a fresh finding.

**Applied 2026-09-09**: `audit-logs/page.tsx` (477 lines, by then renamed upstream to `security-logs/page.tsx` mid-session) split into 6 extracted `components/audit/` pieces plus a new shared `lib/useInfiniteLogFeed.ts` pagination hook — the split widened once a git pull revealed a near-duplicate `activity-logs` page shipped in the same window, so the hook was written generic over both. `security-logs/page.tsx` 485→209 lines, `activity-logs/page.tsx` 267→156. Full detail, including the M5/M6 backlog connection, in [[Session 2026-09-09 — Security & Activity Logs Page Split (DRY Pagination Refactor)]].

## UnitPrep: prioritize architectural discipline over feature velocity, standing (2026-08-14)

Generalizes the ~250-line-flag rule above into a broader standing instruction, given after the third full audit + fix plan closed its highest-risk milestones: pause proactively any time there's an opportunity of *long-term benefit* to keeping the architecture lean, efficient, secure, and elegant — the same dimensions [[Dev Principles]] already names — even when nobody has asked and it isn't blocking the task at hand. Don't wait for line-count thresholds or audit passes to surface these; flag them the moment they're noticed, the same way the 250-line rule already does for size specifically.

**Why**: Boris's explicit framing (2026-08-14), after reviewing both this session's own audit-and-fix-plan work and a second opinion (Grok) on it: shipping features fast is not the priority right now — keeping the foundation disciplined is, and that means catching architectural drift *before* it becomes a backlog item in the next audit, not just cataloguing it after the fact.

**How to apply**: this is a *pause-and-flag* instruction, not a *stop-and-fix* one — same restraint as the 250-line rule (flag and let Boris decide, don't reflexively refactor unprompted mid-task). Applies to anything with genuine long-term payoff: a duplicated pattern about to be copied a third time, a new feature reaching for a hand-rolled solution where a shared helper already exists, a growing file, a dependency pin drifting from its patched sibling, a test gap on newly-shipped surface. Ordinary feature work continues at normal pace; the instruction is to notice and surface the opportunity, not to gate every commit on a architecture review.

**Context**: landed the same session the [[2026-08-13-third-audit-fix-plan-full-session-handoff-m1-m2-done-m3-in-p|third audit and its fix plan]] closed milestones 1-3 (session-ownership IDOR, a docx-surgeon CVE, an admin-guard concurrency race, a passkey step-up feature, and their regression tests) and after cross-checking the audit and remaining plan against a second opinion (Grok) that mostly confirmed the same findings and confirmed no resequencing was needed.
