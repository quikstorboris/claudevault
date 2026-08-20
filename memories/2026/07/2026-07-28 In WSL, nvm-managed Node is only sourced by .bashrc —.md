---
date: 2026-07-28
description: "nvm's init lines (`export NVM_DIR=...`, `."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-28T17:37:59.823Z"
scope: platform
projects: []
platforms: ["wsl", "windows"]
confidence: verified
---

# In WSL, nvm-managed Node is only sourced by .bashrc — non-interactive/login shells silently fall through to Windows node.exe via PATH interop

nvm's init lines (`export NVM_DIR=...`, `. "$NVM_DIR/nvm.sh"`) are typically installed into `~/.bashrc` only, which bash only reads for interactive shells. Any non-interactive invocation of a WSL shell — `wsl.exe -e bash -lc "..."`, a login shell (`bash -lc`), a cron job, most automation/CI-style invocations — does not source `.bashrc`, so `node`/`npm`/`npx` resolve via PATH interop to the Windows binaries (`/mnt/c/Program Files/nodejs/...`) instead of the nvm-managed Linux Node.

This is not just "wrong version" — it can fail in confusing, unrelated-looking ways: observed `npx playwright test` under this condition produced `CMD.EXE was started with the above path as the current directory. UNC paths are not supported.` and `'playwright' is not recognized...`, because the Windows npx.exe was trying to interpret a WSL UNC working directory. Nothing in that error mentions Node versions or PATH at all.

Fix for reliable automated runs: explicitly source nvm in the command (`export NVM_DIR=$HOME/.nvm; . "$NVM_DIR/nvm.sh"; <command>`), or add the nvm init block to `~/.profile`/`~/.bash_profile` (login-shell files) as well as `.bashrc` so it's picked up regardless of how the shell was invoked.

Why this generalizes: any WSL-based project where Node is managed via nvm hits this the moment something drives it non-interactively — a test runner, a scheduled task, an agent invoking `wsl.exe -e bash -lc`. Same-session interactive terminal use never surfaces it, which is why it can go unnoticed for a long time.

## How this is known

Reproduced directly: wsl.exe -e bash -lc resolved node/npx to /mnt/c/Program Files/nodejs and failed with a CMD.EXE/UNC-path error; sourcing ~/.nvm/nvm.sh explicitly in the same command resolved node to ~/.nvm/versions/node/v24.18.0/bin and npx playwright test ran correctly.
