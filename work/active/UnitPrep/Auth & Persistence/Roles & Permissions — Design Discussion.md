---
date: 2026-08-04
description: "Ongoing design effort for UnitPrep's role/permission model, started once a second role (onboarding_manager) made it a real question rather than a hypothetical. Accumulates gradually."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Roles & Permissions — Design Discussion

This is the "right moment" the [[Auth & Persistence Index]] flagged back on
2026-07-30 ("least privilege as the role model grows — raise at the right
moment rather than pre-emptively"). It arrived: `onboarding_manager` exists
in the schema now (see [[Architecture]]'s Roles section, [[Database
Schema]]), and Boris wants this treated as its own **ongoing effort**,
added to gradually, not a one-shot decision to close out. This note is
where that accumulates.

## Current state, as of 2026-08-08 (corrected — see below)

> [!important] The 2026-08-04 snapshot below was superseded 2026-08-06/07 in a session that never recorded it here
> Caught 2026-08-08 while doing unrelated `client_ops` work and reading the
> real migrations directly, not from any vault note. Real current state:
>
> - **Four roles**, real data in `auth.roles`/`auth.user_roles`, not a
>   single enum column (that column is gone — see [[Database Schema]]):
>   `admin`, `onboarding_manager`, **`department_manager`** (everything
>   onboarding_manager can do, plus approving pending QMS
>   credential changes — briefly seeded as `district_manager`, renamed
>   same-day since that term already means a client-side facility manager
>   in self-storage), and **`sales`** (read-only client-record access,
>   capabilities still undefined). A user can hold more than one role.
> - **Permissions are real, checked data too**: `auth.permissions`,
>   `auth.role_permissions`, resolved into every session as
>   `permission_keys`. `AuthenticatedUser::require_permission` replaced the
>   old hardcoded `match role { ... }` block at every gated endpoint.
> - **The umbrella-permission question below is answered and shipped**:
>   `client_ops.perform` is exactly the "one capability, not per-tool
>   grants" recommendation, granted to `onboarding_manager` and
>   `department_manager`. Not granted to `admin` — see the next point.
> - **2026-08-08, this session**: `client_ops.manage_tags` — a second,
>   narrower permission, granted to all three of `admin`,
>   `onboarding_manager`, and `department_manager` alike, for maintaining
>   the QMS template-tag catalog specifically (see the vault's `QMS
>   Template Tags` note set). Deliberately *not* the same permission as
>   `client_ops.perform`: admin still never performs a client operation,
>   but keeping a reference catalog of tag names current reads as system
>   configuration, not client-ops work, so it gets its own permission all
>   three can hold without blurring that line. First real precedent for
>   "some client-ops-adjacent actions are administrative enough for admin
>   to share, most aren't" — worth remembering as a pattern if a similar
>   question comes up again, rather than re-deriving it from scratch.
>
> Source of truth: `unitprep-api`'s `CHANGELOG.md` v1.6.0 and migrations
> `add_roles_permissions_tables`,
> `rename_district_manager_to_department_manager`, and
> `add_qms_tag_manage_permission_and_widen_rls`. The 2026-08-04 snapshot
> below is kept for its reasoning, not its facts.

- ~~Two roles: `admin` (full capability) and `onboarding_manager`
  (schema-only — every admin-gated action refuses it with a 403 and an
  `authorization_failure` audit row). Any admin may assign either role, at
  invite time or after.~~
- `unitprep-ui`'s admin nav/routes are being restricted so
  `onboarding_manager` doesn't see Users/Audit Logs at all (in progress,
  same session this note was created).
- ~~No finer-grained policy exists yet than "admin can do everything,
  everyone else can do nothing admin-shaped."~~

## Principles established so far

**Least privilege means "role = job function," not "role = trust level."**
The instinct to arrange roles on one ladder (`onboarding_manager` <
`admin` < future-more-powerful-role) is the wrong mental model. The right
question for a new capability isn't "how trusted is this role" but "does
*this job function* need *this data or action* to do its job." Two
capabilities can both be "trusted" and still have no reason to see each
other's data.

**Corollary: separate "who can administer the system" from "who can see
business data."** These got collapsed into one `Role` axis because the
project is small (one person does both jobs today). Worth remembering
before a third role gets named: `admin` (system/user administration) and
something like a future `finance_viewer` (business data visibility) are
independent axes, not two rungs of the same ladder. Don't assume every
future role slots into a single hierarchy.

**An audit log and a personal-activity feed are different tools for
different audiences.** The audit log (`GET /auth/audit-logs`) is an
*oversight* tool — who's watching the watchers — and stays admin-only.
"What happened to my own account" (my logins, my sessions, an admin
changed my role) is a different, legitimate need, and belongs on a
personal profile page, not the audit viewer. See the Profile page idea
below.

## Open questions log

Grey areas raised 2026-08-04, not yet resolved — logging them rather than
guessing, per Boris's own framing ("this is another area I don't know the
best practice for").

- **Should `admin` see financial data** (once financial data — tenant
  payment history, facility revenue summaries, unit rates — actually
  flows through this system)? Leaning no, per the least-privilege
  principle above: system administration and financial visibility are
  different job functions that happen to be done by the same person
  today. Not resolved — revisit once there's a concrete financial-data
  feature to hang the decision on, rather than deciding in the abstract.
- **Should `onboarding_manager` see its own `authorization_failure`
  rows?** Leaning **no** — decided 2026-08-04, tentatively. An audit log
  showing someone their own blocked attempts doesn't serve them
  functionally and mostly just tells a compromised account what got
  blocked. If the real need is "let me see what happened on my account,"
  that's the personal-activity-feed idea below, not exposure to the
  admin audit log.
- **What should `onboarding_manager` actually be able to do?** ~~Still
  completely open~~ — **answered and shipped 2026-08-06/07**:
  `client_ops.perform` (see the correction callout above). What it
  actually gates in practice (which endpoints check it) still grows over
  time, but the umbrella-vs-per-tool shape question below is settled, not
  hypothetical.

  **The umbrella-vs-per-tool question, raised 2026-08-07, recommendation
  confirmed by what shipped**: Boris's framing — `onboarding_manager` is
  "the one who can access all 'Client' tools and run them e2e (dedup, unit
  group)," with more tools joining that set over time. Question: per-tool
  grants, or one sweeping "Client tools" permission? **Recommended one
  umbrella capability, not per-tool grants** — gate on "is this route under
  the Client Prep/tool-suite umbrella," structurally, rather than
  enumerating tool names in an authorization check. Reasoning, applying the
  "role = job function" principle above: the job function *is* "run the
  onboarding tool suite for a client" — there is no stated case for an
  onboarding manager who should see dedup but not unit group, or vice
  versa, so a per-tool split would be modeling a distinction nobody has
  asked for. Per-tool grants also mean every new tool (and the
  [[Platform Vision (Onboarding Orchestrator)]] roadmap plans on adding
  several — a lease document processor, at minimum) needs its own
  authorization wiring added by hand, which is exactly the kind of
  enumeration cost the existing "define `role` as an extensible enum from
  day one" pattern ([[Architecture]]) was chosen to avoid elsewhere. **This
  is exactly the shape `client_ops.perform` shipped in** — one permission,
  checked once, not enumerated per tool.

## Ideas captured, not yet built

**Profile page** (personal information, a personal-activity-log tab,
avatars, etc.) — Boris's own framing, "just a thought for now." The
activity-log tab is the natural home for "what happened to my account"
separate from the admin audit trail (see principle above). Not scoped,
not scheduled — flagged here so it isn't lost, to be designed
deliberately when it's actually time, same as the admin panel was.

**A "Manager" role with dual-approval for admin role changes** — distinct
from the `department_manager` role that actually shipped 2026-08-06/07
(see the correction callout above), which approves pending *QMS
credential* changes, not admin role changes. Don't conflate the two — this
idea remains unbuilt and is about a different kind of approval entirely.
Boris asked for a brief opinion, to vault rather than build. Opinion: **dual
control (four-eyes) on privileged role changes is a real, standard
control** (this is exactly what SOX/SOC 2 reviewers look for under "who
can grant admin"), not overengineering as a general practice. But it only
functions with a genuine second approver — with effectively one active
admin today, an approval workflow would just be the same person
approving their own request through an extra click, which is theater,
not control. **Recommendation: don't build until a second admin
genuinely exists to make it real** — trigger-gated the same way the
last-remaining-admin guard is. Cheap interim compensating control instead
of a full workflow: make `role_changed` (and `user_deactivated`)
prominent wherever the dormant-account/activity indicators land on the
admin Users page, so a role change is hard to miss even without a formal
approval gate — detective now, preventive later once the org is big
enough for preventive to mean something.

Self-role-edit is already refused structurally (`POST
/auth/users/{id}/role` and `/deactivate` both refuse the caller's own
`user_id`) — that part shipped 2026-08-04, independent of whether a
Manager-approval role is ever built.

## Related

- [[Roles & Permissions — Design Finalization Log]], [[Roles & Permissions —
  Backend Build Log]], [[Roles & Permissions — Frontend Build & Ship Log]] —
  first-hand detail (closing design rounds, schema, authorization core,
  frontend) behind the "Current state, as of 2026-08-08" correction above,
  2026-08-06/07, split across three notes
- [[Auth & Persistence Index]] — where this was first flagged as "raise
  at the right moment"
- [[Architecture]] — the Roles and authorization design as originally shipped (v1, single-role — see [[Database Schema]]'s correction callout for what superseded it)
- [[Database Schema]] — the real current shape: `auth.roles`/`auth.permissions`/`auth.role_permissions`/`auth.user_roles`, not `auth_role`/`users.role` (dropped)
- [[Orchestrator Feature Backlog]] — where this note's shipped-vs-open items are tracked for planning purposes
- `THREAT_MODEL.md` (unitprep-api repo) — check directly for current known gaps rather than trusting this note's older restatement
- [[Compliance & Process Readiness]] — the SOX/SOC2/CCPA framework
  assessment that prompted this session's roles conversation
