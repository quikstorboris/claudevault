---
date: 2026-07-27
description: How to reliably run commands in the real unitprep-api WSL dev environment (Ubuntu-22.04) from a Windows Git Bash session via wsl.exe.
tags: [reference, environment, wsl, unitprep]
---

# WSL Execution Technique

Discovered 2026-07-21 while building the Onboarding Orchestrator auth schema migrations (see [[Auth & Persistence/Database Schema|Database Schema]]). The Bash tool in this session runs in Git Bash/MSYS on Windows (`C:\Users\bmaksimov`), a different shell than the WSL Ubuntu environment Boris actually develops in — but the same physical machine (`QSLP15`) has a running `Ubuntu-22.04` WSL distro reachable via `wsl.exe`, which is where `unitprep-api`, `.env.local`, `psql`, `sqlx-cli`, and the real Neon dev-branch access actually live.

## The working pattern

`wsl.exe -d Ubuntu-22.04 -- bash -lc '<command>'` reaches the real environment. Two problems showed up, both with fixed workarounds:

1. **MSYS auto-converts POSIX-looking paths to Windows paths before `wsl.exe` even sees them** — e.g. `~/Documents/unitprep-api/foo.sh` silently became `C:/Users/bmaksimov/Documents/unitprep-api/foo.sh`, meaningless inside WSL. Fix: prefix the whole call with `MSYS_NO_PATHCONV=1` to disable that conversion.
2. **Nested quotes get mangled crossing the Git Bash → `wsl.exe` → WSL bash boundary** — command substitution (`$(...)`), variable expansion (`${...}`), and embedded single/double quotes inside an already-quoted argument do not survive reliably. This showed up concretely as `source .env.local` silently producing empty variables (the file's `&` characters in Postgres connection strings broke naive parsing), and as heredoc bodies having their `$(...)` evaluated at write-time instead of preserved literally.

**The reliable fix for both: write a small script file first, then execute it plainly — never try to pack a multi-step command with substitutions directly into one `wsl.exe` call.**

```bash
# Step 1: write the script, escaping every $ that should survive literally
wsl.exe -d Ubuntu-22.04 -- bash -lc 'cat > ~/Documents/unitprep-api/some_script.sh << '"'"'EOF'"'"'
#!/usr/bin/env bash
set -euo pipefail
cd ~/Documents/unitprep-api
DEV_URL=\$(grep "^NEON_DEV_DATABASE_URL=" .env.local | cut -d "=" -f2-)
echo "LEN=\${#DEV_URL}"
sqlx migrate run --database-url "\$DEV_URL"
EOF
'

# Step 2: execute it plainly, with MSYS path conversion disabled
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-22.04 -- bash -lc 'bash /home/bmaksimov/Documents/unitprep-api/some_script.sh'
```

Note the `'"'"'EOF'"'"'` pattern for the heredoc delimiter — even though the delimiter's quoting itself may or may not survive the mangling, **backslash-escaping every `$` in the body is what actually matters**; it works regardless of whether the outer quoting comes through intact.

**Never `source` `.env.local` directly** — its connection-string values contain unescaped `&` (multiple query params), which a raw `source` mis-parses. Always extract the specific value with `grep '^KEY=' .env.local | cut -d '=' -f2-` into a shell variable instead, and pass that variable quoted.

**Housekeeping**: any scratch script written this way should be deleted after use (`rm`) and `git status --short` checked afterward — these are session scratch files, not meant to be committed.

## Practical implication

This means routine dev-environment tasks for `unitprep-api` (running migrations, querying the dev DB, checking file state) can be executed directly in future sessions rather than relayed through Boris pasting terminal output back — worth defaulting to this technique first before asking Boris to run something himself.

## Second gotcha, found 2026-07-24: apostrophes silently stripped from `git commit -m`

During the [[Full Review & 9-Milestone Refactor]] work, a `git commit -m '...'` message containing an apostrophe (e.g. "hook's own state") crossed the Git Bash → `wsl.exe` → WSL bash boundary with the apostrophe silently dropped ("hook own state") — no error, just a quietly wrong commit message. Same root cause as the nested-quoting issue above, but this one doesn't show up as a visible failure, so it's easy to miss.

**Fix**: for any commit message containing an apostrophe or other special character, write it to a temp file with `Write` first and use `git commit -F <file>` instead of `-m` — never trust `-m` with literal punctuation across this boundary.

## Related

- [[Auth & Persistence/Database Schema|Database Schema]]
- [[Full Review & 9-Milestone Refactor]]
- [[UnitPrep File Locations]]
