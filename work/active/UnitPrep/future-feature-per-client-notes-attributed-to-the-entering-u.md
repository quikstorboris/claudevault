---
date: 2026-08-04
description: "Boris asked to log a future feature idea, unrelated to current Phase II auth work: once client records exist in the DB, each client should have a 'not"
tags:
  - decision
source_repo: bmaksimov
---

# Future feature: per-client notes, attributed to the entering user

Boris asked to log a future feature idea, unrelated to current Phase II auth work: once client records exist in the DB, each client should have a "notes" section where onboarding staff (or anyone else with access) can leave freeform notes. Notes must be attributed to the user who entered them. Explicitly not scoped or designed yet -- requirements to be refined when the team actually gets to building it.


## Decisions

- Per-client notes feature, deferred: each client record (not yet built -- client records themselves are still future work per [[Platform Vision (Onboarding Orchestrator)]]) gets a notes section. Any user with access to the client (onboarding staff named explicitly, 'or anyone else' left open) can leave a note. Notes are attributed to the entering user -- an actor/author field is a hard requirement, not optional, mirroring the same attribution discipline already used in unitprep-api's audit trail (actor_user_id, never anonymous for an authenticated action).




## Open

- No schema, no UI, no access-control model decided yet -- explicitly deferred until the team is ready to build it. Open questions for that point: are notes editable/deletable after the fact (and if so, does that need its own audit trail, the same tension AUDIT_RETENTION.md already names for the auth audit log)? Are notes visible to every user with client access, or role/permission-scoped? Do notes support anything beyond plain text (mentions, attachments, timestps beyond created_at)?
- Depends on client records existing at all, which is itself still future work -- this feature has no timeline and no trigger beyond 'when we get to this.'


## Related

- [[Platform Vision (Onboarding Orchestrator)]]


_Recorded 2026-08-04T19:55:15.652Z from `bmaksimov` via the om MCP server (routing: caller)._
