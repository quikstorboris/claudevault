---
date: 2026-08-06
description: "The internal UnitPrep staff role abbreviated \"DM\" throughout the roles/permissions design discussion (approves QMS API credential changes, oversees…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-06T20:15:45.189Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# UnitPrep internal DM role is "Department Manager" — "District Manager" collides with real client-side facility-manager terminology

The internal UnitPrep staff role abbreviated "DM" throughout the roles/permissions design discussion (approves QMS API credential changes, oversees onboarding managers, elevated client-ops privileges over OM) is named **Department Manager**, not District Manager. "District Manager" was the initial name used when the role was first built (2026-08-06, migration 20260806120000) and immediately corrected same-day (migration 20260806140000) once Boris caught that "district manager" is already real self-storage-industry nomenclature for a client-side facility manager — a completely different concept from this internal staff role. Renamed both the DB key (district_manager -> department_manager) and the label, not just the display label, specifically so no trace of the confusing term survives anywhere a developer, admin, or client-facing conversation might encounter it.

Generalizes beyond this one rename: when naming an internal role/concept for a system whose users also work inside a client's own business domain (here: self-storage facility management), check the name against that domain's existing vocabulary before it ships, not after. A name that reads as perfectly sensible in isolation ("District Manager" is a completely normal-sounding management-hierarchy title) can still collide badly if the industry the software serves already uses it to mean something else -- the failure mode is confusing internal staff conversations with client-facing ones, or someone building client-facing copy that accidentally uses a term with two live meanings in the same company.

## Related

- [[Roles & Permissions — Design Discussion]]
