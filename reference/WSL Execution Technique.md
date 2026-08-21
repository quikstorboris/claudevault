---
date: 2026-07-27
description: How to reliably run commands in the real unitprep-api WSL dev environment from a Windows Git Bash session via wsl.exe.
tags: [reference, environment, wsl, unitprep]
---

# WSL Execution Technique

Discovered 2026-07-21 while building the Onboarding Orchestrator auth schema migrations (see [[Auth & Persistence/Database Schema|Database Schema]]). The Bash tool in this session runs in Git Bash/MSYS on Windows (`C:\Users\bmaksimov`), a different shell than the WSL Ubuntu environment Boris actually develops in — but the same physical machine has a running WSL distro reachable via `wsl.exe`, which is where `unitprep-api`/`unitprep-ui`, `.env.local`, `psql`, `sqlx-cli`, and the real Neon dev-branch access actually live.

> [!warning] The distro name, machine, and repo path are all per-laptop, not a fixed fact
> Originally `Ubuntu-22.04` on `QSLP15`, repos at `~/Documents/`. **As of 2026-08-21, on `QSLP14`, the distro is plain `Ubuntu` (Ubuntu 26.04 base) and the real checkouts live at `~/Development/unitprep-api` / `~/Development/unitprep-ui`** — a new laptop got a freshly-provisioned distro with a different name, and every `-d Ubuntu-22.04` / `~/Documents/...` reference below is stale. Check the distro first: `wsl.exe -l -v` (or, from inside a session, just try the plain distro-less form — a single registered distro is used as the default). Check the repo path with `ls ~/Development/ ~/Documents/` before assuming either — a session that skipped this once ended up cloning a second, redundant copy into the wrong one. See [[New Laptop Migration — QSLP14]] for the full story and what else a fresh distro needs redone (git identity, `pkg-config`/`libssl-dev`, `nvm`).

## The working pattern

`wsl.exe -d Ubuntu -- bash -lc '<command>'` reaches the real environment. Two problems showed up, both with fixed workarounds:

1. **MSYS auto-converts POSIX-looking paths to Windows paths before `wsl.exe` even sees them** — e.g. `~/Documents/unitprep-api/foo.sh` silently became `C:/Users/bmaksimov/Documents/unitprep-api/foo.sh`, meaningless inside WSL. Fix: prefix the whole call with `MSYS_NO_PATHCONV=1` to disable that conversion.
2. **Nested quotes get mangled crossing the Git Bash → `wsl.exe` → WSL bash boundary** — command substitution (`$(...)`), variable expansion (`${...}`), and embedded single/double quotes inside an already-quoted argument do not survive reliably. This showed up concretely as `source .env.local` silently producing empty variables (the file's `&` characters in Postgres connection strings broke naive parsing), and as heredoc bodies having their `$(...)` evaluated at write-time instead of preserved literally.

**The reliable fix for both: write a small script file first, then execute it plainly — never try to pack a multi-step command with substitutions directly into one `wsl.exe` call.**

```bash
# Step 1: write the script, escaping every $ that should survive literally
wsl.exe -d Ubuntu -- bash -lc 'cat > ~/Development/unitprep-api/some_script.sh << '"'"'EOF'"'"'
#!/usr/bin/env bash
set -euo pipefail
cd ~/Development/unitprep-api
DEV_URL=\$(grep "^NEON_DEV_DATABASE_URL=" .env.local | cut -d "=" -f2-)
echo "LEN=\${#DEV_URL}"
sqlx migrate run --database-url "\$DEV_URL"
EOF
'

# Step 2: execute it plainly, with MSYS path conversion disabled
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -lc 'bash /home/bmaksimov/Development/unitprep-api/some_script.sh'
```

Note the `'"'"'EOF'"'"'` pattern for the heredoc delimiter — even though the delimiter's quoting itself may or may not survive the mangling, **backslash-escaping every `$` in the body is what actually matters**; it works regardless of whether the outer quoting comes through intact.

**Never `source` `.env.local` directly** — its connection-string values contain unescaped `&` (multiple query params), which a raw `source` mis-parses. Always extract the specific value with `grep '^KEY=' .env.local | cut -d '=' -f2-` into a shell variable instead, and pass that variable quoted.

**Housekeeping**: any scratch script written this way should be deleted after use (`rm`) and `git status --short` checked afterward — these are session scratch files, not meant to be committed.

## Practical implication

This means routine dev-environment tasks for `unitprep-api` (running migrations, querying the dev DB, checking file state) can be executed directly in future sessions rather than relayed through Boris pasting terminal output back — worth defaulting to this technique first before asking Boris to run something himself.

## Second gotcha, found 2026-07-24: apostrophes silently stripped from `git commit -m`

During the [[Full Review & 9-Milestone Refactor]] work, a `git commit -m '...'` message containing an apostrophe (e.g. "hook's own state") crossed the Git Bash → `wsl.exe` → WSL bash boundary with the apostrophe silently dropped ("hook own state") — no error, just a quietly wrong commit message. Same root cause as the nested-quoting issue above, but this one doesn't show up as a visible failure, so it's easy to miss.

**Fix**: for any commit message containing an apostrophe or other special character, write it to a temp file with `Write` first and use `git commit -F <file>` instead of `-m` — never trust `-m` with literal punctuation across this boundary.

## Third gotcha, found 2026-08-21: hand-crafting a git patch across this same boundary is fragile

Splitting one file's diff into two separate commits (so each lands with its own logically-matching commit) means writing a unified-diff patch by hand and applying it with `git apply --cached`. Doing that via a heredoc through the same Git-Bash → `wsl.exe` → WSL-bash boundary hits the same class of corruption as the quoting gotcha above, but in a new shape: a blank *context* line in a unified diff must be a single literal space, not a truly empty line — and a heredoc built through nested shell layers can silently drop that space, or mis-encode backticks inside double-quoted content as command substitution in the *outer* shell (Git Bash) before `wsl.exe` ever sees it, producing `error: corrupt patch` with no useful indication of which of several possible causes it was.

**Fix**: don't build the patch through any shell layer at all. Write it directly with the `Write` tool (or equivalent — anything that writes bytes to the file without going through a shell parser), which bypasses every quoting boundary above entirely. Verify with `git apply --cached --check <patch>` before actually applying, and if it still fails, use `cat -An <patch>` to look for a missing leading space on a blank context line first — the single most common cause.

## Fourth gotcha, found 2026-08-21: a fresh distro needs system packages `cargo`/`sqlx-cli` silently assume exist

`cargo build`/`cargo test`/`cargo install sqlx-cli` all fail identically on a brand-new WSL distro with "Could not find openssl via pkg-config: pkg-config command could not be found" — `openssl-sys` (pulled in transitively by `sqlx`/`reqwest`/etc.) needs the system `pkg-config` and `libssl-dev` packages, which aren't part of a bare Ubuntu WSL image and aren't something `rustup`/`cargo` install for you. Needs `sudo apt-get install -y pkg-config libssl-dev` — requires an interactive sudo password, so this is a step for Boris to run himself, not something a session can push through non-interactively.

Also on a fresh distro: `node`/`npm` may already be installed via `nvm` but **not on `PATH`** in a plain `bash -lc` invocation — `nvm`'s shell function needs sourcing explicitly first: `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"`. Once sourced, a genuinely native Linux Node works — this is actually a strict improvement over the old `QSLP15` setup, which had no native Linux Node at all (only Windows' own `node.exe` reachable via `/mnt/c/Program Files/nodejs/`, which broke `vitest`'s native `rolldown` binding; see [[New Laptop Migration — QSLP14]]). Same root-cause family as [[Gotchas#WSL: `bash -lc` doesn't reliably source `nvm`, so `npx` silently runs the Windows toolchain instead]] — that note's version silently fell through to a Windows Node install instead of erroring; worth reading both.

## Related

- [[Auth & Persistence/Database Schema|Database Schema]]
- [[Full Review & 9-Milestone Refactor]]
- [[UnitPrep File Locations]]
- [[New Laptop Migration — QSLP14]]
