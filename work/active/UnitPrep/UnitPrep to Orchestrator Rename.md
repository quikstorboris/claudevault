---
date: 2026-08-07
description: "Deferred task: rename UnitPrep to Orchestrator throughout — repos, crate/package names, folders, branding. Scoped 2026-08-07, not started, no timeline."
tags: [work-note, unitprep]
status: active
quarter: Q3-2026
project: unitprep
---

# UnitPrep → Orchestrator Rename

Boris, 2026-08-07: wants to fully retire "UnitPrep" in favor of "Orchestrator"
— not just product-facing copy, but repo/crate/folder names too. **"You don't
have to act on it now"** — vaulted as a scoped, deferred task, same treatment
as the still-pending `unit-group`/`UnitGroup` code rename already flagged in
[[Platform Vision (Onboarding Orchestrator)]]. The product-facing name
already changed once before without a code rename (UnitPrep → Group Prep for
the dedup-adjacent tool), so there's precedent for the two moving on
different timelines — this note is about closing that gap deliberately, not
urgently.

## Why now, not urgent

No functional trigger — this is a naming/clarity cleanup, not something
blocking other work. Worth being deliberate about specifically *because* it's
wide-blast-radius and easy to do sloppily under time pressure; better as its
own dedicated session with real repo access than a rename squeezed in as a
side effect of something else.

## Access note, corrected 2026-08-07

Initially told Boris this session lacked WSL repo access. **Wrong** —
confirmed same session: `wsl.exe` is present and
`\\wsl.localhost\Ubuntu-22.04\home\bmaksimov\Documents\` is reachable,
listing both `unitprep-api` and `unitprep-ui` directly. Whatever the earlier
hesitation was, it wasn't a real access limitation — treat WSL repo access as
available by default in this Windows working-directory context, per
[[WSL Execution Technique]].

## Scope, as currently understood (not yet verified against the actual repos)

- **`unitprep-api` (Rust)**: crate directory rename, `Cargo.toml` package
  name(s) (workspace + member crates if more than one), any workspace member
  paths that reference the old directory name, binary-name references in
  deploy scripts/systemd units/Dockerfiles if any exist, env var names if any
  embed "unitprep".
- **`unitprep-ui` (Next.js)**: `package.json` name + directory, a text sweep
  for "UnitPrep"/"unitprep" in UI copy and page titles, `NEXT_PUBLIC_*` env
  var prefixes if any embed the name.
- **The GitHub repos themselves** — renaming affects remotes, CI, and any
  webhooks; larger blast radius than an in-repo rename, worth deciding
  separately whether the repos get renamed at all or just their contents.
- **Database/role names** (`app_service`, etc.) — not believed to be
  name-coupled from what's in [[Database Schema]] and [[RLS Implementation]],
  but not actually verified; confirm with a grep pass rather than assuming.

## Suggested approach, whenever this gets picked up

1. Grep both repos for every case variant (`UnitPrep`, `unitprep`,
   `unit_prep`, `unit-prep`) *before* touching anything — build the full
   change inventory first, don't rename incrementally and discover misses.
2. Decide the repo-rename question (contents only vs. GitHub repo names too)
   before starting, since it changes whether remotes/CI need touching.
3. Do the Rust crate rename and the Next.js package rename as separate,
   independently-verifiable passes — each has its own build/test cycle to
   confirm nothing broke before moving to the next.

## Related

- [[Platform Vision (Onboarding Orchestrator)]] — the product-facing
  UnitPrep → Orchestrator rename this note tracks the code side of, and the
  still-pending `unit-group`/`UnitGroup` rename it's grouped with
- [[WSL Execution Technique]] — how to actually run commands against these
  repos from a Windows session
- [[UnitPrep File Locations]] — where both repos live
