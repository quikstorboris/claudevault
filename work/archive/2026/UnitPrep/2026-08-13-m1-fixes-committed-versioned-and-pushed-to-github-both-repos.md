---
date: 2026-08-13
description: "Organized all uncommitted work in both repos (M1's security fixes plus several pre-existing uncommitted changes from before this session) into coheren"
tags:
  - project-note
source_repo: bmaksimov
---

# M1 fixes committed, versioned, and pushed to GitHub (both repos)

Organized all uncommitted work in both repos (M1's security fixes plus several pre-existing uncommitted changes from before this session) into coherent per-fix commits, bumped both versions, and pushed to origin/main. unitprep-api: 1.8.0 to 1.8.1 (5 commits). unitprep-ui: 1.4.0 to 1.5.0 (5 commits, catching up prior unversioned feature work already on GitHub too). Left .claude/launch.json (unitprep-ui) untracked -- local dev-server tooling config, not a feature/fix.

## What changed

- unitprep-api commits (1.8.0 -> 1.8.1): step_up_actions JSON-column type fix (pre-existing, unrelated to the audit); session-ownership IDOR fix; admin-role-row-lock concurrency fix; docx-surgeon quick-xml CVE fix; version bump
- unitprep-ui commits (1.4.0 -> 1.5.0): added the missing orchestrator-logo-dark.svg asset LeftNav had referenced since the Orchestrator rename but was never actually committed (a real broken-image bug, found while triaging uncommitted files, not previously known); added a favicon; fixed stale Preserve-underscores checkbox copy; AppLayout admin-redirect race fix + its new test; version bump


## Decisions

- Grouped commits by logical change, not by when the edit happened -- e.g. the pre-existing auth_configuration.rs fix and the 3 unrelated frontend fixes (logo, favicon, checkbox copy) got their own commits separate from the security work, even though all were sitting uncommitted together when this pass started.
- unitprep-ui got a full minor bump (1.4.0->1.5.0) rather than a patch bump, since several already-pushed-but-unversioned commits (household rendering, the whole Template Tagger UI, an E2E fix) had accumulated on top of 1.4.0 before this session even started -- the bump catches up that real feature work, not just this session's small fixes.
- Wrote long commit messages to a temp file and committed via `git commit -F file` instead of inline heredocs through the wsl.exe -e bash -lc wrapper -- an apostrophe in a commit message (e.g. "user's") breaks out of the outer single-quoted wsl.exe command string early and corrupts the commit. Safe pattern for any future commit message with contractions/possessives when working through this WSL-wrapped Bash tool.



## Verification

Both repos: working tree clean after all commits (git status -s empty except the intentionally-untracked .claude/launch.json in unitprep-ui). Re-ran tsc --noEmit clean on unitprep-ui immediately before push. Both `git push origin main` succeeded with no conflicts (fast-forward pushes, both repos' local HEAD had matched origin/main exactly before this session's uncommitted work began).



## Related

- [[2026-08-13-milestone-1-shipped-closed-the-4-highest-risk-findings-from]]


_Recorded 2026-08-13T21:36:50.318Z from `bmaksimov` via the om MCP server (routing: caller)._
