---
date: 2026-07-27
description: How to start unitprep-ui's dev server from outside interactive WSL/VS Code, plus a running log of Turbopack/npm/node gotchas hit in that environment.
tags: [reference, environment, wsl, unitprep, nextjs]
---

# UnitPrep UI Dev Environment

> [!warning] Written for `QSLP15` (Ubuntu-22.04) — node resolution below doesn't apply on `QSLP14`
> As of 2026-08-21, on the new laptop, real checkouts live at `~/Development/unitprep-ui` (not `~/Documents/`, used below), and Node is genuinely native Linux via `nvm` (`export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"`) — no VS-Code-server symlink hack needed at all, and `npm install`/`npx vitest run` both work directly (333/333 tests passing, confirmed). See [[New Laptop Migration — QSLP14]]. **Not yet re-verified on this machine**: whether the Turbopack worker-spawn failure documented below still reproduces — a different Node runtime entirely might not hit the same bug. Re-check before trusting the `--webpack` workaround is still necessary here.

`unitprep-ui`'s WSL environment (Ubuntu-22.04) has **no Linux-native Node.js on PATH** — `which node` returns nothing. `npm`/`npx` resolve to the Windows install via WSL's cross-boundary interop, which breaks (a bare cmd.exe "UNC paths are not supported" error) when invoked with a WSL-side working directory from a non-interactive `wsl.exe -d Ubuntu-22.04 -- bash -lc "..."` call (as opposed to a real interactive WSL terminal).

**A real Linux node binary does exist**, bundled by the VS Code Remote-WSL extension: `~/.vscode-server/bin/*/node` (resolve the `*` at runtime — it's a build-id hash that changes). This is what actually runs `unitprep-ui`'s `next dev` in normal (interactive VS Code) use.

## The node symlink fix

**Applied 2026-07-17**: created a symlink at `/mnt/c/Users/bmaksimov/bin/node` (that directory is already on PATH via `/mnt/c/Users/bmaksimov/bin`, and is user-writable — no `/usr/local/bin` access without a sudo password, which isn't available non-interactively) pointing at the real vscode-server node binary. `which node` / plain `node ...` now resolves correctly from any non-interactive shell.

**This symlink goes stale on its own — expect to recreate it.** Hit 2026-07-23: `which node` returned nothing and `setsid node ...` failed with "No such file or directory", even though the symlink file was still there — it pointed at a `~/.vscode-server/bin/<old-hash>/node` path that no longer existed (VS Code Remote-WSL had updated its server build in between sessions, changing the hash). Fix is one line, safe to just re-run whenever this happens rather than debugging further:

```bash
mkdir -p /mnt/c/Users/bmaksimov/bin
ln -sf ~/.vscode-server/bin/*/node /mnt/c/Users/bmaksimov/bin/node
```

(the glob resolves to whatever build-hash directory is currently installed). Verify with `node --version` before relying on it for a `next dev`/`next build` launch.

## Known-unresolved: Turbopack worker-spawn failure

Even with `node` resolvable, **Turbopack's dev-mode worker-pool spawn is still broken** in this environment — `next dev` (Turbopack, the default) fails every route compile with:

```
FATAL: An unexpected Turbopack error occurred.
Failed to write app endpoint /<route>/page
Caused by: ... creating new process, spawning node pooled process,
No such file or directory (os error 2)
```

This reproduces 100% of the time on a *freshly started* `next dev`, regardless of the node PATH fix above — it's internal to Turbopack's own Rust-native binary, not a plain PATH-resolution problem at the Node.js JS layer.

**Workaround: pass `--webpack`** (`next dev --webpack`) to fall back to webpack instead of Turbopack — this compiles and serves routes correctly. Not yet root-caused *why* Turbopack specifically fails here; only the workaround is confirmed. A long-lived `next dev` process that happened to already be running (started before this investigation, possibly from a real interactive terminal) DID serve `/dedup` correctly earlier the same day — so this may be specific to a *fresh* Turbopack process's first-compile worker spawn, not a permanent block on Turbopack ever working here.

**Confirmed real 2026-07-17, same day**: this is not just an artifact of non-interactive `wsl.exe` invocation quirks. Boris hit the *exact* same panic (`spawning node pooled process — No such file or directory (os error 2)`, same `evaluate_webpack_loader`/`parse_css` call chain processing `app/globals.css`) running plain `npm run dev` in his own real, normal, interactive VS Code Remote-WSL terminal. This is a genuine environment bug that will bite any dev on this machine/setup, not a one-off.

### Root-cause investigation — started, inconclusive, left unfinished

Resume here rather than re-deriving from scratch:

- Read the actual panic log at `/tmp/next-panic-*.log` (there are several; `ls -lat` to find the newest) — confirms the failure is specifically Turbopack's `evaluate_webpack_loader` step (running Tailwind's PostCSS plugin against `app/globals.css`) trying to spawn a pooled Node.js worker process, and that spawn hitting a bare ENOENT.
- Web search confirms this is a known Turbopack failure mode in general ("spawning node pooled process" + ENOENT = Turbopack can't find a `node` binary to spawn for JS-based loader evaluation) — but didn't pin down *which* Node.js path-resolution mechanism Turbopack's Rust-native binary actually uses (it does NOT appear to be a simple inherited-PATH search, since `node` was already resolvable via PATH — the symlink fix above — and Turbopack still failed identically afterward).
- **One theory ruled out**: checked whether `~/Documents` (where this whole repo lives) is secretly a symlink/mount into the Windows side filesystem (`/mnt/c/...`, a 9p mount with known quirks under heavy Rust-native syscall use) — confirmed NOT the case. `readlink -f ~/Documents` resolves to itself (not a symlink) and `stat -f` reports `ext2/ext3` (genuinely native WSL2 filesystem), not 9p. So this is not a cross-filesystem-boundary issue.
- **Leading unconfirmed theory**: Turbopack's pooled-process spawner likely resolves the Node binary via something more specific than a plain PATH search — possibly an npm-set env var like `npm_node_execpath`/`npm_execpath` (which npm normally sets to the exact Node binary that invoked it, for child processes to reuse consistently) that may be stale or unset in this VS Code Remote-WSL setup. VS Code's bundled node lives under a build-hash-versioned directory (`~/.vscode-server/bin/<hash>/node`) that changes on every VS Code Remote-WSL server update — exactly the kind of thing that would leave a *cached* path reference broken after an update while a fresh PATH-based lookup still resolves fine. **Not confirmed** — was mid-investigation (checking `npm run env` for `npm_node_execpath`/`npm_execpath`/`NODE`) when this got interrupted; the check itself returned nothing useful (exit code 1, empty), never re-attempted with a corrected approach.
- **Next step when resumed**: try running `next dev` (Turbopack) with `RUST_LOG=trace` or check for a Turbopack-specific trace/debug env var to get the literal path/command it attempts to spawn, rather than inferring from the high-level panic log. Also worth directly inspecting `npm_node_execpath`/`npm_execpath`/`process.execPath` from *inside* a real `next dev` process (e.g. a one-off script) rather than via `npm run env`, which may not reflect what a nested Turbopack child process actually inherits.

**Pragmatic fix offered, not yet applied**: since this hits any dev on this setup via plain `npm run dev`, offered to update `package.json`'s `dev` script to default to `next dev --webpack` (still fully supported, stable — not a downgrade) so nobody has to discover the `--webpack` flag manually. Boris asked to understand *why* first rather than just patch around it — the investigation above is the result; the actual `package.json` change is still pending his go-ahead once the root-cause question is settled (or he decides to apply the workaround anyway despite the open question).

### Second real incident, 2026-07-23

A long-lived `next dev` (Turbopack) process — running since the prior day, having absorbed many hot-reloads across an extended session's file edits — eventually stopped serving the app's very first page load (`http://localhost:3000` → `/clients`) entirely, not just one route's compile. No `/tmp/next-panic-*.log` was left behind this time (different failure mode than the documented worker-spawn ENOENT above, or the panic went to the interactive terminal's own stdout instead of a file — wasn't captured either way). Boris restarted the process himself and it immediately worked again (verified: `/clients` served 200 OK with real content in 69ms right after restart).

Diagnostic groundwork before this: a separate "discovery took 7-10 seconds" complaint was fully ruled out as server/network-side first — `curl`-from-WSL2 round trip 1-4ms, a cold Windows→WSL2 request via PowerShell ~114ms then 3-6ms warm — so a multi-second delay has to be browser/dev-server-side, and this hang is the same category of thing.

**Offered again to switch to `--webpack` given the recurrence — Boris said no, leave it on Turbopack for now.** Not a rejection of the diagnosis, just choosing to keep restarting around it rather than switch bundlers yet. Don't re-propose this unprompted; the standing per-incident move is: confirm current state (is it still stuck, or did the user already restart it), test with curl/PowerShell to see if it's actually the server or something environmental, and restart if needed — the fix-in-hand remains `next dev --webpack` if Boris ever wants it applied.

## Practical recipe: starting the dev server non-interactively

```bash
wsl.exe -d Ubuntu-22.04 -- bash -lc "cd ~/Documents/unitprep-ui && setsid node node_modules/.bin/next dev --webpack > /tmp/unitprep-ui-dev.log 2>&1 < /dev/null &
sleep 2
echo launched"
```

Use `setsid`, not just `nohup ... &` + `disown` — plain nohup/disown was observed to NOT reliably survive the invoking `wsl.exe` process exiting for `next dev` specifically (it did work fine for the Rust backend's `cargo run --release`), while `setsid` reliably detached it.

**Don't combine `pkill -f 'next dev'` with launching a new `next dev` in the same compound command** — the pattern `'next dev'` matches the *launching* command's own argv too (since it also contains the literal substring "next dev"), causing `pkill` to kill its own parent shell before the new process finishes detaching. Run the kill and the launch as fully separate tool calls, or match on a more specific token (e.g. `node_modules/.bin/next` or `next-server`) via `ps`/`pgrep` instead of a generic `pkill -f` pattern.

## tsc/eslint verification recipe

Works fine, no Turbopack involved:

```powershell
Set-Location "\\wsl.localhost\Ubuntu-22.04\home\bmaksimov\Documents\unitprep-ui"
node .\node_modules\typescript\bin\tsc --noEmit -p tsconfig.json
node .\node_modules\eslint\bin\eslint.js <files>
```

Via PowerShell against the UNC path (cmd.exe-based tools like `npx`/`npm` break on UNC paths; plain `node <script>` invocations don't). If `tsc` reports a parse error inside `.next/dev/types/*.ts`, that's a stale/corrupted auto-generated Next.js type-checking helper, not a real source error — `rm -rf .next` (safe, it's a build cache) and re-run.

See [[Python Environment]] for a similar prior environment gap (that one about Python) — same pattern of "the tool exists but isn't on PATH the way you'd expect" recurring in this dev setup.

## Never run `next build` while `next dev` is live

Hit this twice in one session (2026-07-24) before the pattern registered: running a production build (as a verification step, e.g. after a round of edits) deletes/repopulates `.next/dev/*` out from under the still-running dev server, which then fails every request with `ENOENT ... .next/dev/routes-manifest.json` (or `.next/dev/server/app/.../page.js`) and no other error — "Internal Server Error" in the browser, nothing informative in the dev server's own log beyond the ENOENT stack. First occurrence looked like a mystery regression; second occurrence (same session, same mistake) confirmed the cause immediately.

**Fix and going-forward rule**: if a `next build` verification is genuinely needed, immediately kill and restart the `next dev` process afterward (`rm -rf .next` first, then relaunch via the recipe above) — treat every `next build` call as something that requires a dev-server restart right after, no exceptions, don't wait for Boris to report a 500 first.

## Never run npm install/audit fix from Windows against the UNC path

Hit 2026-07-27: `npm audit fix` (no `--dry-run`) crashed outright with `EISDIR`/`EPERM` errors trying to delete `node_modules/.bin` symlinks over the WSL UNC boundary (same class of npm-over-UNC breakage as the `npx`/`tsc` issue above, just on a write path instead of a read path) — package.json/package-lock.json were left untouched (confirmed via `git status`), so no real damage, but the `--dry-run` output revealed something worse than the crash itself: applying the fix would have **removed `@next/swc-linux-x64-gnu`, `@img/sharp-linux-x64`, `@tailwindcss/oxide-linux-x64-gnu`, and `@unrs/resolver-binding-linux-x64-gnu`, replacing them with the `-win32-x64-msvc`/`-win32-x64` equivalents** — because npm resolves these platform-specific optional dependencies for whatever OS it's actually running on, and from this Windows session that's Windows, not the WSL Linux environment `next dev` actually runs in. Doing this for real would silently break `next dev` the next time someone runs it from the real interactive WSL terminal.

**The safe pattern**: `npm audit` (read-only, just reports) is fine to run from here; anything that actually installs/removes packages (`npm install`, `npm audit fix`, `npm update`) needs to happen from an actual WSL terminal instead, or be handed to Boris to run himself — don't try to work around this by force or by hand-editing `package-lock.json`.

## Stray NUL byte from a normal Edit call

A stray NUL byte can silently end up inside `ScanResultsPage.tsx` from a normal `Edit` call over the UNC path — hit 2026-07-24: an edit that should have inserted a plain `" "` string literal instead wrote a literal `\x00` byte at that exact spot (confirmed via `cat -A` over `wsl.exe`; `file` reported the whole file as generic `data` instead of text because of it). This silently broke later `Edit` tool calls targeting that region (the old_string, containing a real space, no longer matched the actual on-disk bytes) with a generic "String not found" error that gives no hint the file itself is corrupted.

**If an `Edit` call fails against text you just read successfully with `Read` and visually matches, don't assume you mistyped**; check for stray NUL bytes first (`grep -naP '\x00' <file>` inside WSL, or `file <file>` and look for anything other than an ASCII/UTF-8/Unicode text classification) before re-deriving the edit. Fix is a one-line `sed -i 's/\x00/ /g' <file>` (safe — the WSL Edit machinery had already made all *other* edits in that session land correctly; this was a one-spot artifact, not systemic corruption) run directly against the WSL path, then retry the failed `Edit` normally. Root cause not identified (not reproduced deliberately) — worth rechecking for NUL bytes early if an `Edit` mysteriously fails to match obviously-present text again, rather than re-deriving the whole edit from scratch.

## Related

- [[Python Environment]]
- [[UnitPrep File Locations]]
- [[WSL Execution Technique]]
- [[UnitPrep Architecture Overview]]
