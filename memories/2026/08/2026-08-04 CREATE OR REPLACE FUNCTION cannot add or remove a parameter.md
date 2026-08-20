---
date: 2026-08-04
description: "PostgreSQL resolves functions by (schema, name, argument types) as a unit, not by name alone."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-04T18:43:28.711Z"
scope: general
projects: []
confidence: verified
---

# CREATE OR REPLACE FUNCTION cannot add or remove a parameter -- it silently creates a second overload with default PUBLIC privileges instead of replacing

PostgreSQL resolves functions by (schema, name, argument types) as a unit, not by name alone. `CREATE OR REPLACE FUNCTION foo(a INT, b INT)` only replaces an existing `foo` whose argument *types* are exactly `(INT, INT)`. If the existing function is `foo(a INT)` and you write `CREATE OR REPLACE FUNCTION foo(a INT, b INT DEFAULT 0)` intending to "add an optional parameter", Postgres does not error and does not replace anything -- it creates a second, distinct, overloaded function. The original `foo(INT)` keeps existing and keeps working exactly as before, invisible to a caller who only looked at the new definition.

This matters most in a SECURITY DEFINER / locked-down-privileges schema: the original function's `REVOKE ALL FROM PUBLIC; GRANT EXECUTE TO some_role` does not carry over to the new overload. A freshly created Postgres function grants EXECUTE to PUBLIC by default. So "adding an optional argument" via CREATE OR REPLACE can silently reopen a SECURITY DEFINER function to every role that can connect, while looking, on read, like a routine signature extension. Nothing about the migration errors or warns -- the new overload simply exists with looser privileges than every other function in the schema, and only a privilege audit (`\df+` cross-checked against expected grants, or querying `information_schema.routine_privileges`) surfaces it.

The only way to actually replace a function whose signature is changing (parameter added, removed, or reordered) is `DROP FUNCTION foo(<old exact arg types>); CREATE FUNCTION foo(<new arg types>) ...;` followed by fresh, explicit `REVOKE EXECUTE ... FROM PUBLIC` and `GRANT EXECUTE ... TO <role>` statements for the new signature -- privileges are never inherited from a dropped function by a differently-signed replacement.

CREATE OR REPLACE is genuinely safe and does what it looks like it does when the argument list (names may change, but types/order/count must not) is identical and only the function body changes -- that's the one case where privileges and dependents survive intact.

Generalizes beyond any one project: this is Postgres's own function-overloading and privilege-default behavior, not something specific to a particular schema or ORM. Any migration that changes a function's parameter list needs a signature check first (`\df schema.function_name` or `SELECT pg_get_function_arguments(oid) FROM pg_proc WHERE proname = '...'`) before deciding whether CREATE OR REPLACE is sufficient.
