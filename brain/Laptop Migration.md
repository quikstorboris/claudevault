---
description: "How Claude Desktop sessions, the Obsidian vault, and local dev repos were moved to a new laptop -- what's actually backed up where, and the exact restore steps"
tags:
  - brain
---

# Laptop Migration

Runbook from replacing this laptop (2026-08-20). Keep this updated if the process changes -- the next migration should be a checklist, not a rediscovery.

## The core trap: Claude Desktop's session list is not the conversation

The Desktop app's sidebar is backed by two things that live in **different places** and must both be restored, or a session shows up but says "session not found on disk":

1. **The session index** -- small JSON files under `LocalCache\Roaming\Claude\claude-code-sessions\<sessionId>\<workspaceId>\local_*.json` and the sibling `local-agent-mode-sessions\` folder. Each one holds `cwd`, `title`, `model`, `lastActivityAt`, and critically a `cliSessionId` pointer. This is metadata only -- no conversation content.
2. **The actual transcript** -- one `.jsonl` file per session, at `~/.claude/projects/<encoded-cwd>/<cliSessionId>.jsonl` (Windows: `C:\Users\<user>\.claude\projects\...`). This is the real content. `cliSessionId` from the index file is the filename here (no extension in the index).

Path encoding for the `projects/` folder name: take the cwd, replace `:` and `\` both with `-`. `C:\Users\bmaksimov` -> `C--Users-bmaksimov`.

**Why this bit us**: a prepared restore script (`merge-live-sessions.sh`) and the robocopy commands run from it only ever touched #1. It looked complete -- 39 session entries showed up in the sidebar -- but every one of them was empty, because #2 was never part of the backup at all. The Dropbox backup of `LocalCache\Roaming\Claude` (the whole app-data folder) genuinely does not include `~/.claude/projects/` -- that directory lives outside the Desktop app's own data folder entirely.

## Restoring the session index (folder 1)

Safe and idempotent -- never overwrites a live/current session file:

```powershell
robocopy "<staged>\claude-code-sessions" "<live>\claude-code-sessions" /E /XC /XN /XO
robocopy "<staged>\local-agent-mode-sessions" "<live>\local-agent-mode-sessions" /E /XC /XN /XO
```

`/XC /XN /XO` = exclude changed/newer/older -- robocopy only ever *adds* files that don't already exist at the destination, so re-running this is harmless and it can't clobber the session you're currently in.

## Restoring the real transcripts (folder 2) -- the part that's actually missing

This is not covered by any existing backup unless someone deliberately grabbed it. To get it off an old laptop you still have physical access to but can't network to directly:

1. On the **old** laptop, copy `C:\Users\<olduser>\.claude\projects` (just that subfolder, not all of `.claude` -- skip logs/shell-snapshots, they're not needed and bloat the transfer) into a synced cloud folder (Dropbox, etc.)
2. Wait for sync
3. On the **new** laptop, robocopy each per-project folder from the synced copy into `C:\Users\<newuser>\.claude\projects\<same-encoded-folder-name>\`, same `/E /XC /XN /XO` flags
4. **Fully quit Claude Desktop first** (check Task Manager for a lingering `claude.exe`) before doing the real restore pass, then relaunch and check the sidebar

Confirm a specific fix worked by testing that the exact `cliSessionId` named in a "not found" session's index file now exists as a `.jsonl` under the right encoded-cwd folder -- don't just trust the file count.

## The vault's own git repo: this was a first push, not a recovery

Two places looked like they had git history and didn't:

- The live vault folder on the new laptop (`git status` showed "On branch main, No commits yet") -- it had been `git init`'d fresh with the files copied in, no history.
- A separate Dropbox folder (`Obsidian Vault Backup/my-vault`) that *did* have a `.git` directory -- but `find .git/objects -type f | wc -l` was `0`. Its own `RESTORE.md` said explicitly: "Everything on disk was copied byte-for-byte... this is a raw folder mirror, not a git export." Any `.git` folder found inside a raw file-mirror backup should be assumed empty until `git fsck` or an object count says otherwise -- don't trust it just because the folder exists.

Net effect: no history was actually lost, because none had ever been created. The GitHub repo (`quikstorboris/claudevault`, private) was also genuinely brand new -- this was the first-ever push, not a restore.

## SSH + git identity setup done on the new machine

- Copied the existing WSL Ubuntu SSH key (`~/.ssh/id_ed25519` + `.pub`, comment `bmaksimov@quikstor.com`) to Windows-native `C:\Users\bmaksimov\.ssh\`
- Windows OpenSSH refuses a world-readable private key -- lock it down after copying:
  ```powershell
  icacls "C:\Users\bmaksimov\.ssh\id_ed25519" /inheritance:r
  icacls "C:\Users\bmaksimov\.ssh\id_ed25519" /grant:r "$($env:USERNAME):(R)"
  ```
- Verified with `ssh -T git@github.com` (look for "Hi \<username\>! You've successfully authenticated")
- Git had **no identity configured at all** on the new machine (neither `--global` nor repo-local) -- set before the first commit:
  ```bash
  git config --global user.name "Boris Maksimov"
  git config --global user.email "bmaksimov@quikstor.com"
  ```
- Before the first push of a personal vault (even a private repo), ran `git add -A -n` and grepped the file list for `env|secret|credential|token|pem|key|password` as a cheap sanity check -- two hits, both just memory-note titles describing lessons *about* credentials, not actual secret files. Worth doing once per repo's first push, not every commit.

## Local dev repos vs. the vault: different transfer path entirely

The vault and Desktop sessions came through Dropbox app-data mirrors. **Local dev repos are separate** -- they live in WSL Ubuntu (`~/Development/`) and were restored by cloning from GitHub (`unitprep-api`, `unitprep-ui`), which only brings back what's actually tracked in git. Anything gitignored on the old laptop (`.env`, `.env.local`, local config, uploaded test fixtures, etc.) needed a separate manual sweep: a raw file-copy backup of the old laptop's `Documents` folder in Dropbox, reconciled by hand against the freshly-cloned repos to find and move over exactly the untracked files a repo needs to actually run locally.

## Checklist for the next time this happens

- [ ] Back up `LocalCache\Roaming\Claude\{claude-code-sessions,local-agent-mode-sessions}` (the index)
- [ ] **Also** back up `~/.claude/projects/` (the real transcripts) -- easy to forget, not in the same folder
- [ ] Back up the vault as an actual `git bundle`/push, not just a raw file mirror, if you want real history preserved
- [ ] For each dev repo: confirm it's pushed to its remote, then just re-clone on the new machine
- [ ] Separately sweep the old machine's gitignored files per repo (`.env*`, local config, fixtures) -- git clone will never bring these back
- [ ] Set up SSH key + git identity on the new machine before any of the above pushes are attempted

## Related

- [[Gotchas]] -- the raw-mirror-vs-git-export trap is filed there too, short form
