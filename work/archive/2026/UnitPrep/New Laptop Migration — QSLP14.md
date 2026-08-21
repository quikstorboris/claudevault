---
date: 2026-08-21
description: "Moved from QSLP15 (WSL Ubuntu-22.04) to QSLP14 (fresh WSL Ubuntu). Re-cloned both repos, verified git history against origin, ran the environment up as far as it goes without sudo."
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
2. **Re-clone both repos** (the old distro's checkouts are gone with it):
   ```bash
   mkdir -p ~/Documents && cd ~/Documents
   git clone git@github.com:quikstorboris/unitprep-api.git
   git clone git@github.com:quikstorboris/unitprep-ui.git
   ```
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
5. **`cargo test`/`cargo install sqlx-cli` both fail**, same root cause: no system OpenSSL dev headers.
   ```
   Could not find openssl via pkg-config: pkg-config command could not be found
   ```
   **Not fixed this session** — needs `sudo apt-get install -y pkg-config libssl-dev`, which needs Boris's own sudo password (not something Claude can supply non-interactively). Re-run `cargo install sqlx-cli --version 0.9.0 --locked` and `cargo test --workspace` in `unitprep-api` after that lands.
6. **`.env.local` is not restorable by Claude** — gitignored, never touched GitHub, so a fresh clone genuinely has none. Wherever Boris keeps a backup of it (a password manager, a synced copy — not documented anywhere in this vault as far as this session found), it needs to be copied back into `~/Documents/unitprep-api/.env.local` by hand. Not needed to *build*, but needed for anything that talks to the real Neon dev/prod database (migrations, the bootstrap CLI, running the server for real).
7. **The `client_ops.vendor_format` migration itself needed no action** — it was applied directly against the real Neon dev database in the *previous* session, before this laptop swap was ever noticed; that state lives in Postgres, not in WSL, so the distro swap doesn't touch it. Confirmed still correct by a live `psql` query against the dev branch that same prior session.

## Verified

- `git clone` of both repos from `origin/main`: clean, full history present, matches what was pushed.
- `unitprep-ui`: `npm install` clean, `npx vitest run` → 333/333 passing.
- `unitprep-api`: **not yet verified end-to-end** — `cargo build`/`test`/`clippy` all blocked on the missing `pkg-config`/`libssl-dev` system packages (see above). This is the one real gap left open by this note.

## Open

- Install `pkg-config`/`libssl-dev` (needs Boris, needs sudo), then re-verify `cargo test --workspace` + `cargo clippy --workspace --all-targets -- -D warnings` on the new machine.
- Reinstall `sqlx-cli` (same blocker).
- Restore `.env.local` from wherever it's actually backed up — worth documenting that location here once it's done, since this vault currently has no record of it at all.

## Related

- [[WSL Execution Technique]] — the living reference this note's facts feed into (distro name, `nvm`/`pkg-config` gotchas added there).
- [[UnitPrep File Locations]]
- [[Dedup Tool Index]] — status correction landed there as part of this note.
- [[Shared Vendor-Format Registry (Easy Storage Solutions)]]
- [[Westpark Cross-Check — Placeholder, Wording, and XLSX Fixes]]
