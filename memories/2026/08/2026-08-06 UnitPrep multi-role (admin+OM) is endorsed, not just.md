---
date: 2026-08-06
description: "When a design note documents \"role stays a single column since role is one-per-user in this design,\" that's a decision scoped to the assumptions true…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-06T17:13:27.953Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: unverified
---

# UnitPrep: multi-role (admin+OM) is endorsed, not just tolerated — user_roles join table is the right model

When a design note documents "role stays a single column since role is one-per-user in this design," that's a decision scoped to the assumptions true *at the time it was written* (v1 had exactly one role), not a standing constraint to defend once those assumptions change. The tell that it's expired: a real person needs two job functions on one account (here: Boris is both the admin building UnitPrep and an OM using it) — at that point a single-role column is actively wrong, not just limiting.

The fix is the standard RBAC shape: a `user_roles` many-to-many join table, effective permissions = union of all held roles' capabilities. This isn't a compromise or a risk to accept reluctantly — it's the correct model once "role = job function" (an existing principle) is taken seriously, since two different job functions on one person is exactly what that principle already anticipates, not an edge case it strains against.

**Why it doesn't worsen an existing segregation-of-duties gap, and how to reason about that class of question in general:** if a system already has a documented, accepted single-point-of-trust gap (here: one admin can act and review their own actions, unresolved until a second admin exists), granting that same account an *additional, orthogonal* capability (OM's client-data visibility) doesn't deepen the original gap — it doesn't touch the audit trail or the admin's own oversight powers. It's a new instance of the same already-accepted exception ("we only have one person, so trust concentration is real"), not a new category of risk. The thing worth stating explicitly rather than leaving implicit: since there's only one admin, that person can grant themselves any additional role including the one being discussed, unchecked. Name that plainly next to the existing single-admin gap rather than treating it as a fresh problem — it's the same fact viewed from a different angle.

General lesson: when asked "should I do the thing that breaks an old assumption," check whether the assumption's own stated justification still holds before treating the old decision as binding. If the justification was scoped ("...since X is true right now") and X stopped being true, the old decision doesn't need to be defended — it needs to be updated, deliberately and on the record, same weight as making it the first time.

## Related

- [[Roles & Permissions — Design Discussion]]
- [[Database Schema]]
- [[Compliance & Process Readiness]]
