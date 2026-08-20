---
date: 2026-07-29
description: "Postgres roles live in the cluster catalog, which on Neon is part of a branch's own copy-on-write data."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-29T21:06:07.613Z"
scope: general
projects: []
confidence: verified
---

# Neon roles are per-branch state, so a role created on one branch silently does not exist on its siblings

Postgres roles live in the cluster catalog, which on Neon is part of a branch's own copy-on-write data. So a role is **branch-scoped**, not project-scoped: creating one on a dev branch does not create it on the parent/production branch, and a branch only inherits roles that already existed at the moment it was taken.

This is easy to get wrong because the Neon console presents roles in a project-level UI, which reads as if they were global.

The failure mode is delayed and quiet. Everything works on the branch where the role was created, sometimes for weeks, and the gap only surfaces at go-live on another branch — as `role "<name>" does not exist` from whatever runs first there.

It also interacts badly with schema migrations that reference the role. If any migration contains `GRANT ... TO <app_role>` (common for `SECURITY DEFINER` bootstrap functions, or any grant applied as part of enabling RLS), then on a fresh branch:

- the role must exist **before** `migrate run`, or that migration aborts partway through, and
- the role's own grants can only be applied **after** `migrate run`, because the schema/tables it grants on do not exist yet.

Those two constraints point in opposite directions, so a single role-setup script cannot satisfy both on an empty branch. Make the setup script idempotent and order-independent — guard each schema/table-dependent statement on the object existing (`GRANT` has no `IF EXISTS`, so use a `DO` block with a `pg_namespace`/`pg_tables` check) — then the procedure is: run it, migrate, run it again. It converges either way, and a single run still suffices on an already-migrated branch.

Verify per branch rather than trusting one check: `SELECT rolname FROM pg_roles WHERE rolname = '<role>';` against each branch's own connection string.

## How this is known

Hit directly on unitprep-api's Neon project 2026-07-29. `app_service` had existed on the dev branch since 2026-07-21; querying pg_roles on the prod branch returned nothing, and prod had no schemas or tables at all. Running `sqlx migrate run` against prod then failed at migration 20260721202617 with `role "app_service" does not exist` after applying 10 of 17 migrations (no dirty row left behind, so it resumed cleanly once the role was created). Re-running the guarded setup script before and after the migrations produced a prod branch that diffed byte-identical to dev across 43 structural facts (role attributes, schema USAGE, per-table RLS flags and privileges, all policies, all functions with secdef/execute, enums, triggers, default ACLs).

## Related

- [[RLS Implementation]]
- [[Build Plan & Infra Checklist]]
