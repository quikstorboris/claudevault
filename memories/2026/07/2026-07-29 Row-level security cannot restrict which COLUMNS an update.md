---
date: 2026-07-29
description: "A typical owner-or-admin RLS policy is row-scoped only: ```sql CREATE POLICY users_update_own_or_admin ON users FOR UPDATE USING (id =…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-29T21:06:38.029Z"
scope: general
projects: []
confidence: verified
---

# Row-level security cannot restrict which COLUMNS an update touches — that needs column-level privileges, and a blanket table GRANT silently re-opens the hole

A typical owner-or-admin RLS policy is row-scoped only:

```sql
CREATE POLICY users_update_own_or_admin ON users FOR UPDATE
  USING (id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
         OR current_setting('app.current_user_role', true) = 'admin');
```

That correctly permits a caller to update *their own row* — and places no constraint whatsoever on **which columns** the update sets. If the application role also holds table-level `UPDATE`, a self-service "edit my profile" request can legally include `SET role = 'admin'`. RLS has no column dimension; there is no policy form that expresses "this row, but not this column".

The fix is column-level privileges, which are enforced *in addition to* RLS:

```sql
REVOKE UPDATE ON users FROM app_role;
GRANT UPDATE (first_name, last_name, job_title) ON users TO app_role;
```

Everything withheld then becomes an administrative act that must go through a `SECURITY DEFINER` function which checks the caller is an admin. Prefer this over relying on the application never accepting a `role` field — app discipline is one refactor away from being wrong, and the database constraint costs nothing.

Three non-obvious details:

1. **A blanket grant silently undoes it.** Any later `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA x TO app_role` re-grants *table-level* UPDATE, which re-opens the gap with no error and no output. Role-setup scripts that do exactly this are common and are usually documented as "safe to re-run" — so re-running one becomes a silent security regression. Either narrow the blanket grant or have the script re-assert the column restriction at the end.

2. **Triggers need no grant on the columns they write.** Column-level UPDATE privilege is checked against the columns named in the statement's `SET` list, not against columns a `BEFORE UPDATE` trigger modifies on `NEW`. So an `updated_at` auto-touch trigger keeps working without `UPDATE (updated_at)` being granted, even when the trigger function is `SECURITY INVOKER`.

3. **A mixed statement is refused whole, not partially applied.** `SET first_name = 'x', role = 'admin'` errors rather than applying the permitted half — so there is no partial-write hazard to defend against separately.

**Testing caveat that produces false confidence**: verifying this with `SET ROLE app_role` from the owning role can fail with `permission denied to set role` when the owner is not a member of that role (the default on managed Postgres such as Neon, where the owner is not a superuser). Every statement in the transaction then errors for that reason instead, which reads exactly like the denial being tested for. Connect with the application role's own credentials rather than assuming `SET ROLE` is available.

## How this is known

Closed this gap on unitprep-api 2026-07-29 (migration 20260729210000). Verified by connecting as the real app_service role on the dev branch: role, status, deleted_at and email updates each returned "permission denied for table users"; a combined first_name + role update was refused outright; a job_title-only update returned UPDATE 1 and the users_set_updated_at trigger still advanced updated_at (19:18:50 -> 21:04:15) with no grant on that column. An initial attempt to test via SET ROLE app_service from neondb_owner failed with "permission denied to set role" on every statement -- the false-positive case described above, caught only because the expected-success test failed identically to the expected-failure ones. The blanket-grant interaction was found by reading the role-setup script after writing the migration.

## Related

- [[RLS Implementation]]
- [[Database Schema]]
