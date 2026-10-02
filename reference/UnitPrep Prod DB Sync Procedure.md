---
date: 2026-10-02
description: "How the Neon prod DB branch is brought level with dev: a manual, read-first procedure run from Boris's laptop (not CI), plus the app_service password step."
tags: [reference, unitprep, neon]
---

# UnitPrep Prod DB Sync Procedure

Status as of 2026-10-02. Everything runs on Boris's laptop; GitHub Actions only tests against a throwaway Postgres and never touches Neon. Syncing the prod DB branch is **manual and on request** ("sync prod"), not automatic. Prod holds real data (users, invites, the tag catalog; see [[Auth & Persistence Index]]); dev holds real QS clients that are deliberately **not** copied to prod. Last sync: 2026-10-02 -- 32 migrations to `20261001150000`, then 2 more (SiteLink Group Prep row, `source_encrypted`) to `20261002130000`; dev and prod DB branches both at 92 migrations, schema-identical.

## Steps (all in WSL, from `~/Development/unitprep-api`)

1. **Look:** `bash scripts/prod_db_status.sh` (read-only) prints prod's latest applied migration and the local ones it lacks.
2. **Read every pending migration's SQL** before running. Separate additive changes from anything that DELETEs, UPDATEs or drops existing rows, and check those against prod's actual data (do not assume dev's outcome).
3. **Apply:** `bash scripts/prod_db_sync.sh` shows before counts, asks you to type `apply prod`, runs `sqlx migrate run` (each migration in its own transaction), re-runs `scripts/setup_app_service_role.sql` for new tables and schemas, and verifies `app_service` privileges and counts.
4. A migration for code that is not yet released should wait: the running code and the schema should move together.

Both scripts read `NEON_PROD_DATABASE_URL_DIRECT` from `.env.local` by extracting that one line (never `source` the file). The auto-mode classifier blocks Claude from reading prod, so Boris runs them and pastes the output.

## The `app_service` password on the prod branch

Set 2026-10-02 (random 48-hex-char password, written only into `NEON_PROD_DATABASE_URL_APP` in `.env.local`, never printed; login verified as `app_service`; the previous file is kept as `.env.local.pre-prod-app-pw`, gitignored). Nothing reads it yet. To rotate: connect with the direct (owner) URL, run `password app_service`, update the same `.env.local` line. Roles are per Neon branch, so this is independent of dev.
