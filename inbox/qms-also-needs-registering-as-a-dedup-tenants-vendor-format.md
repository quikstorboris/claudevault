---
date: 2026-08-27
description: "Boris confirmed the QMS registration I made ('unit group', i.e. Group Prep / content_type='units') was what he meant by 'dedup vendor list' — a termin"
tags:
  - decision
source_repo: development
---

# QMS also needs registering as a dedup (tenants) vendor format — deferred

Boris confirmed the QMS registration I made ("unit group", i.e. Group Prep / content_type='units') was what he meant by "dedup vendor list" — a terminology slip, not a correction. He also confirmed separately that QMS should eventually be registered for the actual dedup tool (content_type='tenants') too, but explicitly said not to scrap the units work and to park the tenants side for later.


## Decisions

- Keep the existing units-registration migration (20260827200000) as-is -- Active stays unmapped from UnitStatus; Boris confirmed he doesn't care about that field, so there's no code/data change to make there.
- Do NOT register a QMS row for content_type='tenants' yet -- no QMS tenant/customer export (the shape dedup's vendor_format signatures actually need: contact/name/address columns, not unit records) has been provided. This is a real confirmed to-do, not a maybe -- just blocked on Boris supplying that file's header shape.




## Open

- When Boris provides a QMS tenant/customer list export (or its header row), add a matching client_ops.vendor_format row with content_type='tenants', following the same pattern as migration 20260827200000 (units) and the original QSX/Easy Storage Solutions tenants rows in 20260818120000.


## Related

- Registered QMS as a recognized units vendor format _(no note yet)_
- Net-new facility unit files stuck as "unrecognized" — added manual unit-file upload _(no note yet)_


_Recorded 2026-08-27T19:47:50.057Z from `development` via the om MCP server (routing: fallback)._
