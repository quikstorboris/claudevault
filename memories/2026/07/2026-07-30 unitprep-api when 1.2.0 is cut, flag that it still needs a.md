---
date: 2026-07-30
description: "**Trigger: raise this the moment 1.2.0 is being released, or the version in `Cargo.toml` is bumped past 1.2.0 — whichever comes first.** Boris asked…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-30T21:37:16.585Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# unitprep-api: when 1.2.0 is cut, flag that it still needs a git tag — v1.1.1 through v1.1.5 were tagged retroactively but v1.2.0 was deliberately left untagged

**Trigger: raise this the moment 1.2.0 is being released, or the version in `Cargo.toml` is bumped past 1.2.0 — whichever comes first.** Boris asked explicitly to be reminded rather than have it silently accumulate.

**The state as of 2026-07-30.** `unitprep-api` carries `version = "1.2.0"` in `Cargo.toml` and a `[1.2.0]` section in `CHANGELOG.md`, but there is **no `v1.2.0` git tag**. That is deliberate, and it is Boris's decision, not an oversight: 1.2.0 is the *working* version with commits still landing on it, so tagging it now would mark a point that understates the release.

Tags `v1.1.1` through `v1.1.5` were created **retroactively** on 2026-07-30, each pointing at the last commit that still carried that version in `Cargo.toml` — derived from where the bump to the next version happened, and verified against the file contents at each commit. Before that, only `v1.0.0` and `v1.1.0` existed, despite the changelog documenting every release in between.

**So when 1.2.0 is actually cut:** tag it, at the commit that genuinely closes it rather than at the old `Bump version to 1.2.0` commit (`0bf3343`), which predates the bootstrap CLI, the audit-logging fix, and invite acceptance — all of which the 1.2.0 changelog entry covers or should cover.

**Two things worth stating precisely, because they were initially overstated in conversation and corrected:**

- Adding tags **rewrites nothing**. No commits change; a tag is just a named pointer, and pushing new ones is purely additive.
- The one real caution is that git treats tags as immutable and does not update them on fetch. Moving a tag after it has been pushed means deleting the remote tag, re-pushing, and anyone who already fetched keeps the stale pointer until they prune. With a single developer that is a minor chore, not a risk — do not inflate it.

**Generalises as**: a project whose version lives in a manifest and a changelog but not in tags has a release history that looks complete and is not. The gap is invisible until someone runs `git describe` or tries to diff two releases. Worth checking once per project rather than discovering later.

## How this is known

Verified against the repo 2026-07-30: `git tag` listed only v1.0.0 and v1.1.0 before the change; `Cargo.toml` read version = \"1.2.0\"; CHANGELOG.md documented 1.0.0 through 1.2.0. Each retroactive tag was checked with `git show <commit>:Cargo.toml` confirming the version at that commit matched the tag being applied (all five OK). `git push --dry-run --tags` confirmed all five were new on the remote and that no existing ref would be modified. Boris chose 'tag v1.1.1-v1.1.5 only' from an explicit set of options and asked for this reminder to be recorded."

## Related

- [[Phase 2 Progress]]
