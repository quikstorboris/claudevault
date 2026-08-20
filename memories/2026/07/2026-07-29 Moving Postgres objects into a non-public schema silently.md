---
date: 2026-07-29
description: "A migration that relocates tables/functions into a dedicated schema (`ALTER TABLE ..."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-29T20:27:15.631Z"
scope: general
projects: []
confidence: verified
---

# Moving Postgres objects into a non-public schema silently breaks later migrations, because the migration connection's search_path is not the application's

A migration that relocates tables/functions into a dedicated schema (`ALTER TABLE ... SET SCHEMA auth`) will keep the *application* working while breaking every *later* migration that uses unqualified names — because the two connections have different `search_path` values and nothing warns you about the divergence.

The application side is usually configured explicitly, e.g. with sqlx:

```rust
let opts: PgConnectOptions = url.parse()?;
let opts = opts.options([("search_path", "auth,public")]);
```

so unqualified names in application queries (`users`, `resolve_session`) keep resolving fine. But the migration/owner connection (sqlx-cli, or plain `psql`) uses the role's default, typically `"$user", public` — which does **not** include the new schema. Verify with `SHOW search_path;`, not by assuming.

Consequences:

1. **Pre-move migrations in git history are unqualified and still pass**, because the objects were in `public` when those migrations ran. This makes the unqualified style look sanctioned. Any NEW migration copying that style fails.
2. **The failure mode for functions is at CREATE time, not call time**: `CREATE FUNCTION ... AS $$ SELECT ... FROM users $$` with `LANGUAGE sql` validates its body when created, so an unqualified reference errors immediately. That is the good case — a `plpgsql` body defers resolution to call time, so the same mistake ships silently and fails in production.
3. **`SET search_path` pins on existing SECURITY DEFINER functions must be re-pointed too.** A function hardened with `SET search_path = public` stops finding its own tables the moment they move; the relocating migration has to `ALTER FUNCTION ... SET search_path = <new>, public` for each one.
4. **Table-level grants survive a schema move; schema-level `USAGE` does not.** A non-owner application role needs `GRANT USAGE ON SCHEMA <new>` re-granted, plus `ALTER DEFAULT PRIVILEGES ... IN SCHEMA <new>` so future tables inherit access. If that role's grants live in a manually-run script rather than tracked migrations (common, since `CREATE ROLE` is cluster-level), the script must be re-run against every environment — easy to do on dev and forget on prod.

Practical rule: in any migration written after such a move, **fully schema-qualify every reference** (`auth.users`, not `users`) rather than relying on `search_path`. Qualification is correct under both connections; `search_path` reliance is correct under only one.

## How this is known

Hit directly in unitprep-api on 2026-07-29 while adding a migration after its earlier auth-schema move: `psql "$OWNER_URL" -c "SHOW search_path;"` returned `"$user", public`, and `SELECT count(*) FROM users` on that same connection returned "relation \"users\" does not exist" while the running app queried the identical tables successfully via its own `search_path=auth,public`. The new fully-qualified `LANGUAGE sql` function then created and ran cleanly. Points 3 and 4 read off that repo's own relocating migration and its `setup_app_service_role.sql`, which had both fixes applied at move time.

## Related

- [[Database Schema]]
- [[RLS Implementation]]
- [[Phase 2 Progress]]
