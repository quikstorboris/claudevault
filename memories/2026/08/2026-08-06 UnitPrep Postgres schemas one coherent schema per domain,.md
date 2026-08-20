---
date: 2026-08-06
description: "Boris's explicit standing rule (2026-08-06), generalizing what auth already does by example: every distinct business/technical domain in the UnitPrep…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-06T19:39:53.925Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# UnitPrep Postgres schemas: one coherent schema per domain, not a flat public namespace

Boris's explicit standing rule (2026-08-06), generalizing what auth already does by example: every distinct business/technical domain in the UnitPrep database gets its own named Postgres schema, following the precedent already set by `auth` (users, sessions, credentials, invites, audit logs, and now roles/permissions/authorization all live together there because they're one coherent domain). `public` is reserved for cross-cutting infrastructure only (today: just `_sqlx_migrations`).

The test for "does this belong in an existing schema or does it need a new one": is the new table part of the SAME domain as something already there, or a genuinely different business concern? Roles/permissions/user_roles/role_permissions went into `auth` (not a new schema) because they're the authorization half of identity -- same request lifecycle as session resolution, tight FK coupling to auth.users, not a separate concern. By contrast, the still-unbuilt Client/Facility/Contacts schema (UnitPrep's "Onboarding Orchestrator" persistence work, step 2 of the agreed build order) is a genuinely different domain from auth and should get its own schema (likely `clients`), not be bolted onto `auth` or dumped into `public` just because it's convenient at the time.

Apply this test before adding any new table going forward: name the schema decision explicitly rather than defaulting to `public`, the same way the auth-schema move (migration 20260723150000_move_auth_objects_to_auth_schema) had to happen after-the-fact once tables had already accumulated in `public` -- cheaper to decide up front than to migrate later.

## Related

- [[Database Schema]]
- [[Architecture]]
