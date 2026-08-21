---
date: 2026-08-21
description: "Moved from QSLP15 (WSL Ubuntu-22.04) to QSLP14 (fresh WSL Ubuntu). Verified git history against origin, got the real ~/Development/ checkouts fully working (backend + frontend), deleted a redundant clone made along the way."
tags: [work-note, unitprep, environment, wsl]
status: completed
quarter: Q3-2026
project: unitprep
---

# New Laptop Migration — QSLP14

Boris moved to a new laptop (`QSLP14`, replacing `QSLP15`) mid-session, discovered when a routine WSL command from the [[Shared Vendor-Format Registry (Easy Storage Solutions)|previous session's work]] suddenly failed: `wsl -d Ubuntu-22.04` — the exact distro name [[WSL Execution Technique]] is written around — no longer resolves. `wsl.exe -l -v` on the new machine shows exactly one distro, plain `Ubuntu` (Ubuntu 26.04 base, WSL2 kernel 6.18), freshly provisioned the same day. See [[WSL Execution Technique]] for the corrected living reference (distro name, quoting gotchas); this note is the one-time record of what the migration actually required.

**The good news first**: nothing was lost. Both repos' full commit history (including that session's 9 unitprep-api + 3 unitprep-ui commits) was already pushed to GitHub before the old distro became unreachable — confirmed by cloning fresh from `origin/main` on the new machine and seeing every commit present.

## What the new distro already had

- SSH already configured and authenticated to GitHub as `quikstorboris` (`ssh -T git@github.com` → "Hi quikstorboris!... does not provide shell access", the expected success message) — someone (Boris, presumably as part of setting up the new machine) had already done this before this was discovered.
- Rust via rustup, `cargo 1.98.0`.
- `psql (PostgreSQL) 18.6`.
- Node via `nvm`, `v24.19.0` installed — but **not on `PATH` by default**; needs `nvm`'s shell function sourced first (see below).

## What was missing / needed doing

1. **Git identity** — `git config --global user.name`/`user.email` were unset. Set to match the existing commit history exactly:
   ```bash
   git config --global user.name "Boris Maksimov"
   git config --global user.email "bmaksimov@quikstor.com"
   ```
2. **Re-clone both repos** (the old distro's checkouts are gone with it) — got this wrong the first time:
   ```bash
   mkdir -p ~/Documents && cd ~/Documents
   git clone git@github.com:quikstorboris/unitprep-api.git
   git clone git@github.com:quikstorboris/unitprep-ui.git
   ```
   **Correction**: Boris had already restored his real working checkouts at `~/Development/unitprep-api` / `~/Development/unitprep-ui` (with `.env.local` already in place, `.mcp.json`, and other real project files) *before* this was ever discovered — this session just hadn't found them yet, and cloned a second, redundant copy into `~/Documents/` instead. No conflict (both were exact copies of the same `origin/main`), but it meant two checkouts existed briefly. **The real path is `~/Development/`, not `~/Documents/`** — the redundant `~/Documents/unitprep-api`/`unitprep-ui` clones were deleted once this was noticed (confirmed `git status` clean in both first). `[[WSL Execution Technique]]` corrected to match. Lesson for next time: `ls ~/Development/ ~/Documents/` (or similar) *before* cloning anything on a fresh distro, not after.
3. **Resolved a real open question this way**: [[Dedup Tool Index]]'s status section claimed the 2026-08-13 Rowley cross-check fixes were "not yet committed/pushed." Checking the fresh clone's own history directly settled it —
   ```bash
   git log --oneline --all -- dedup/src/relatedness.rs dedup/src/relatedness/
   ```
   shows `b3e016e Restructure related-tenant detection into households, add typo callout and two guardrails` (2026-08-13 09:47 -0700) already present in a clone that came straight from `origin/main` — so it was committed and pushed at some point after that note was last written, and the note was simply never updated. Corrected there (and swept for other restatements of the same stale claim).
4. **Node needs `nvm` sourced explicitly** — a login shell doesn't do it automatically here:
   ```bash
   export NVM_DIR="$HOME/.nvm"
   . "$NVM_DIR/nvm.sh"
   node --version   # v24.19.0
   ```
   Once sourced: `cd unitprep-ui && npm install` (487 packages, clean) and `npx vitest run` — **333/333 tests passing**, including the two `TypoVariantsSection` tests the prior session could only verify by manual review (that session's WSL had no native Linux node at all, only Windows' `node.exe` reachable via `/mnt/c`, which broke `vitest`'s native `rolldown` binding — see that session's own note for the workaround it used instead). This new setup is a strict improvement on that front.
5. **`cargo test`/`cargo install sqlx-cli` both failed at first**, same root cause: no system OpenSSL dev headers.
   ```
   Could not find openssl via pkg-config: pkg-config command could not be found
   ```
   Needed `sudo apt-get install -y pkg-config libssl-dev` — Boris's own sudo password, not something Claude could supply non-interactively. **Fixed same day**: Boris ran it himself; `cargo test --workspace` in `~/Development/unitprep-api` came back **330+58+74+15+32+71 tests, all passing, 0 failed** (3 ignored, needing a real reachable Postgres — expected).
6. **`.env.local` was already restored** — Boris had it in place at `~/Development/unitprep-api/.env.local` (dated 2026-07-30, so carried over from wherever he actually backs it up) before this was ever an open question. Where that backup lives is still not documented anywhere in this vault — worth fixing next time it comes up.
7. **The `client_ops.vendor_format` migration itself needed no action** — it was applied directly against the real Neon dev database in the *previous* session, before this laptop swap was ever noticed; that state lives in Postgres, not in WSL, so the distro swap doesn't touch it. Confirmed still correct by a live `psql` query against the dev branch that same prior session.

## Verified

- `git clone` of both repos from `origin/main`: clean, full history present, matches what was pushed.
- `unitprep-ui`: `npm install` clean, `npx vitest run` → 333/333 passing.
- `unitprep-api`: after `pkg-config`/`libssl-dev` landed, `cargo test --workspace` in the real `~/Development/unitprep-api` checkout — every crate green, 0 failed.
- Python on the Windows side (not WSL) also confirmed working for this machine: `python`/`python3` both resolve to 3.14.7 via the WindowsApps alias, `pip` 26.2.1, a basic script runs fine — same shape as the old laptop's setup (see [[Python Environment]]), just a newer patch version.
- The redundant `~/Documents/unitprep-api`/`unitprep-ui` clones this session created were deleted (confirmed clean `git status` in both first, per Boris's explicit go-ahead) — `~/Development/` is the one real checkout of each repo on this machine.

## Open

- Where `.env.local` is actually backed up is still not written down anywhere in this vault — only that a copy already existed and got restored. Worth capturing once/if that comes up again.

## Related

- [[WSL Execution Technique]] — the living reference this note's facts feed into (distro name, repo path, `nvm`/`pkg-config` gotchas all added there).
- [[UnitPrep File Locations]]
- [[Python Environment]] — same Windows-side Python setup re-confirmed on this machine, newer patch version.
- [[UnitPrep UI Dev Environment]] — its whole node-symlink workaround was `QSLP15`-specific; flagged as superseded here, Turbopack behavior on the new machine still unverified.
- [[Dedup Tool Index]] — status correction landed there as part of this note.
- [[Shared Vendor-Format Registry (Easy Storage Solutions)]]
- [[Westpark Cross-Check — Placeholder, Wording, and XLSX Fixes]]
