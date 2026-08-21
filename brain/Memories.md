---
description: "Index of memory topics — key decisions, patterns, gotchas, people context"
tags:
  - brain
  - index
---

# Memories

Persistent context and knowledge retained across sessions. Each topic lives in its own note — follow the links.

- [[Key Decisions]] — architectural and workflow decisions worth recalling
- [[Patterns]] — recurring patterns and conventions discovered across work
- [[Dev Principles]] — the ~15 code-quality/security/workflow principles actually enforced across UnitPrep work, compiled from Patterns + Key Decisions + audit practice
- [[Gotchas]] — things that have bitten before and will bite again
- [[Collaboration Style]] — how Boris likes to work through hard technical decisions
- [[People & Context]] — org structure, teams, review history, dynamics
- [[North Star]] — living goals document, read at session start
- [[Skills]] — custom slash commands and workflows
- [[Laptop Migration]] — runbook for moving Claude Desktop sessions, this vault, and local dev repos to a new machine

## Recent Context

- 2026-08-20: replaced this laptop. Restored Claude Desktop sessions (discovered the session index and the actual `.jsonl` transcripts live in two different places — see [[Laptop Migration]]), did the vault's first-ever git push to `quikstorboris/claudevault` (no history was actually lost — neither the local repo nor the Dropbox mirror had any), and set up SSH + git identity on the new machine. Full steps and a checklist for next time in [[Laptop Migration]].
- 2026-07-27: ported all UnitPrep project memory from the old `~/.claude/projects/.../memory/` auto-memory system into this vault (`brain/`, `reference/`, `work/active/UnitPrep/`, `work/archive/2026/UnitPrep/`). The `om` MCP server is now wired into the home-dir session, `unitprep-api`, and `unitprep-ui` so future work gets recorded here going forward, alongside the local auto-memory.
- 2026-07-28: organized the accumulated post-refactor-audit work into coherent commits and shipped **v1.1.1** on both repos, then implemented the outstanding test-coverage brainstorm (property-based/HTTP-integration/race tests on the backend — finding and fixing 2 real crash bugs — plus Vitest/Playwright/coverage tooling on a frontend that had zero tests before, debugged into an actually-passing E2E test) and shipped **v1.1.2**. Full account in [[Shipped as v1.1.2]] and [[Post-Refactor Audit - Shipped as v1.1.1]]; new standing decisions/gotchas from this session are in [[Key Decisions]] and [[Gotchas]].
