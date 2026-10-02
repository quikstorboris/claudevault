---
date: "2026-10-01"
description: "Copy-paste commands for starting, stopping, restarting and watching logs for the UnitPrep API and UI dev containers (Docker Phases 1-3)."
tags:
  - reference
  - unitprep
  - docker
---

# UnitPrep Docker Cheat Sheet

Day-to-day commands for the dev containers described in [[UnitPrep Docker Standards]] and built as Phases 1-3 of [[UnitPrep CI-CD Framework]]. Run everything in WSL. `~/Development/unitprep-api` for API commands, `~/Development/unitprep-ui` for UI commands. Use a separate terminal for anything marked "stays open".

Everything is gated behind the `dev` compose profile, so a bare `docker compose up` does nothing by accident.

## Start everything

**1. API containers** (`test-db` and `api-dev`):
```bash
cd ~/Development/unitprep-api && docker compose --profile dev up -d
```

**2. API server** (stays open -- the server runs in this terminal):
```bash
cd ~/Development/unitprep-api && docker compose exec api-dev cargo run
```

**3. UI:**
```bash
cd ~/Development/unitprep-ui && docker compose --profile dev up -d
```

UI at http://localhost:3001 (not 3000 -- a native `next dev` may already hold that port; the API's CORS and WebAuthn settings are set for 3001). API at http://localhost:8080 once step 2 is running. The UI's first start runs `npm ci` and Next's first compile, so allow a minute.

## Restart the API after a code change

`api-dev`'s main process is a test-watch loop, not the server, so `cargo run` does **not** reload on save. Ctrl-C in the terminal running step 2, then run step 2 again.

If it reports port 8080 already in use, an old `cargo run` is still alive inside the container, where host tools can't see it:
```bash
cd ~/Development/unitprep-api && docker compose up -d --force-recreate api-dev
```
then run step 2 again. Recreating wipes anything started by hand, which is why step 2 has to be repeated. The slim image has **no `pkill`** -- don't try to kill the process by name.

## Stop everything

```bash
cd ~/Development/unitprep-ui && docker compose --profile dev down
```
```bash
cd ~/Development/unitprep-api && docker compose --profile dev down
```
`down` removes the containers but keeps the named volumes (`node_modules`, `.next`, cargo registry/git/rustup, `target/`), so the next start is fast. `stop` instead of `down` pauses without removing.

A WSL or Docker restart stops all of this on its own (confirmed 2026-10-01: after an overnight restart `docker ps` was empty and nothing listened on 3000/3001/8080).

## Live logs

UI -- Next.js compiling on every save:
```bash
cd ~/Development/unitprep-ui && docker compose logs -f ui-dev
```

API -- the test-watch loop, which reruns the whole workspace suite on every Rust save:
```bash
cd ~/Development/unitprep-api && docker compose logs -f api-dev
```

Ctrl-C stops watching, not the container. `--tail 50` starts from the last 50 lines. The API *server's* own request log prints in the terminal running step 2, not in `api-dev`'s logs.

## Status and extras

| Need | Command |
|---|---|
| What's running | `docker ps` (empty = nothing; `-a` includes stopped) |
| Shell in the API container | `cd ~/Development/unitprep-api && docker compose exec api-dev bash` |
| Shell in the UI container | `cd ~/Development/unitprep-ui && docker compose exec ui-dev bash` |
| Real-DB `#[ignore]`d test against the throwaway DB | `docker compose exec api-dev cargo test -- --ignored <name>` (run `./scripts/bootstrap_test_db.sh` first on a fresh `test-db`) |

## Gotchas

- **Which database does `cargo run` hit?** The compose file only sets `TEST_DATABASE_URL` (the throwaway `test-db`, used by the test loop). The server very likely reads `.env.local` through the bind mount and so talks to the real Neon dev branch -- (unverified as of 2026-10-01). Check before assuming the containerised app touches only throwaway data.
- **Docker itself costs almost nothing; the dev server is a debug build.** `docker compose exec api-dev cargo run` builds without `--release`, which is roughly 10x slower on allocation-heavy loops (a dedup check measured 8.7 s natively in debug vs 0.84 s in release, with Docker adding ~0.4 s on top of that; see [[Gotchas]]). Port forwarding and Next file watching are small by comparison. (Bind mounts are not the cause: `~/Development` is on WSL's own filesystem.) For a fast API run use `cargo run --release` natively in WSL.
- **`pkill` doesn't exist in the image, and PowerShell commands don't run in the WSL shell** -- both cost a round trip on 2026-09-30.

## Related

- [[UnitPrep Docker Standards]] -- the rules behind every container artifact
- [[UnitPrep CI-CD Framework]] -- the phased plan (Docker Phases 1-5)
