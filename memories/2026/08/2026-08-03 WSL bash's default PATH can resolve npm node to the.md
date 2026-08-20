---
date: 2026-08-03
description: "On a machine with Node installed both on the Windows side (reachable from WSL via `/mnt/c/...`, e.g."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-03T21:47:14.509Z"
scope: general
projects: []
confidence: verified
---

# WSL bash's default PATH can resolve npm/node to the Windows-side install, which corrupts node_modules against a WSL-native project

On a machine with Node installed both on the Windows side (reachable from WSL via `/mnt/c/...`, e.g. `/mnt/c/Program Files/nodejs/npm`) and natively inside WSL (e.g. under `~/.nvm/versions/node/<version>/bin`), a typical WSL bash PATH built from Windows PATH import puts the Windows-side entries first. Running `npm install` from WSL bash against a project that lives on the WSL filesystem (`~/Documents/...`, not `/mnt/c/...`) then invokes the *Windows* npm binary against a *Linux* filesystem path, which npm reaches through the `\\wsl.localhost\...` UNC bridge. That bridge does not implement full POSIX filesystem semantics (symlinks, some rmdir/lstat cases), so npm's own cleanup/reinstall logic throws `EISDIR`/`EPERM` on existing packages it isn't even trying to touch (seen: `next/dist/next-devtools/dev-overlay`, `@bramus/specificity`, `node_modules/.bin/acorn`), and the install aborts without ever reaching the packages actually being added.

Worse: if a dev server (`next dev` watching `node_modules`) is running at the time, this partial file mutation can crash it outright -- the process disappears with no error in its own log, because the corruption happens to files Node's watcher/module resolution touches, not to anything the server itself logged.

Fix: **run npm/node from WSL against a WSL-native path using the native WSL Node**, not whatever resolves first on PATH. Reorder PATH for that invocation, e.g. `export PATH=$HOME/.nvm/versions/node/<version>/bin:$PATH`, or `command -v node`/`which node` first to confirm which one will actually run. The same install that failed via the Windows-side npm (`EISDIR`, hung for minutes) completed via the native one in ~4 seconds.

Distinct from Node npm npx WSL interop-style gotchas about `.cmd` wrappers shelling through `cmd.exe`: this one is about *which Node build answers* `node`/`npm` on WSL's own PATH, not about invocation syntax. Both can appear in the same session and look like the same class of problem, but the fix differs (PATH reordering vs. invoking `node` directly against a JS entry point).

##### How this is known

Hit directly on unitprep-ui 2026-08-03. `which npm` in the WSL bash tool resolved to `/mnt/c/Program Files/nodejs/npm`; `npm install qrcode @types/qrcode` from that shell failed with a wall of `EISDIR`/`EPERM` cleanup errors on unrelated existing packages and never wrote the new dependency to package.json. The already-running `next dev` process (alive since earlier in the session) was confirmed gone immediately after, with no crash message in its own log. Reordering PATH to `~/.nvm/versions/node/v24.18.0/bin` first and re-running the identical install command succeeded in 4s with a clean `package.json` diff.

##### Related

- Node npm npx WSL interop

## How this is known

Reproduced the failure with the Windows-side npm resolved first on PATH, then fixed it by prepending the native WSL nvm bin directory to PATH and re-running the identical command, which succeeded cleanly.
