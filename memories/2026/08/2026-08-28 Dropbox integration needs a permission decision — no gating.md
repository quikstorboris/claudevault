---
date: 2026-08-28
description: "Boris asked to note that Dropbox integration needs permissions added, assuming the top-level Clients menu in Orchestrator is \"probably already…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T17:53:55.821Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# Dropbox integration needs a permission decision — no gating exists today, and the Clients menu isn't restricted either (correcting an assumption)

Boris asked to note that Dropbox integration needs permissions added, assuming the top-level Clients menu in Orchestrator is "probably already restricted" and that if a more granular Dropbox-specific permission gets added, it should be granted to every role that currently exists. Checked both assumptions directly rather than trusting them:

**Correction: the Clients menu is NOT currently restricted at all.** `unitprep-ui/components/nav/LeftNav.tsx` defines it as a plain top-level link (`{label: "Clients", href: "/clients"}`) with no `RequirePermission` wrapper, and neither `app/(app)/clients/page.tsx` nor the client info page have any permission check either -- any authenticated user, any role, can reach the whole Clients section today. `RequirePermission` exists and is used elsewhere (admin/audit-logs, admin/roles, admin/users, admin/client-ops/qms-tags, admin/security-policies) but was never applied to Clients.

**Dropbox's own two endpoints (`GET /dropbox/list`, `GET /dropbox/search`, both in `unitprep-api/src/api/dropbox_browse.rs`) currently require only `AuthenticatedUser` -- no permission gate at all**, deliberately mirroring `client_ops_qms_tags::list_qms_tags`'s "catalog data, nothing sensitive" reasoning (folder *names* only, no file contents). So today: any signed-in user of any role can browse/search the Dropbox folder structure, same as any signed-in user can reach the Clients menu that exposes it.

**The actual current role list** (`auth.roles`, seeded in `migrations/20260806120000_add_roles_permissions_tables.up.sql`): `admin`, `onboarding_manager`, `district_manager`, `sales`. (Note: a code comment elsewhere in the repo says "department_manager" -- that name does not exist in the seeded roles table; either stale or an earlier working name for `district_manager`. Worth a quick grep-and-fix pass if noticed again, not urgent.)

**Decision needed, not yet made**: whether Dropbox access should get its own dedicated permission (e.g. `client_ops.dropbox` or similar) separate from general Clients-menu access, or whether gating the Clients menu itself (currently ungated) is the more relevant fix. Boris's instruction: IF a Dropbox-specific permission is added, grant it to all roles that exist AT THE TIME it's added -- don't use it to restrict anyone today, since nothing is restricted today and narrowing access wasn't the ask.

**Standing trigger, to be raised proactively**: the next time a new role is added to `auth.roles` (currently 4: admin/onboarding_manager/district_manager/sales), check whether it should also be granted Dropbox access (whatever form that gating ends up taking) before that role ships. Don't let a new role silently miss whatever Dropbox permission exists by then.

## How this is known

Read unitprep-ui's LeftNav.tsx and the clients page/layout directly (no RequirePermission usage found); read unitprep-api's dropbox_browse.rs handlers directly (AuthenticatedUser only, no permission check); read the actual auth.roles seed migration for the current 4-role list.
