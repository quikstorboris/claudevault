---
date: 2026-08-07
description: "Entry point for the QMS (KoBre) Public Gateway WebApi v2 OpenAPI spec — 92 endpoints, 307 schemas, read end-to-end 2026-08-07 ahead of Orchestrator's QMS API integration step."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS API Index

Read in full 2026-08-07 per the [[Platform Vision (Onboarding Orchestrator)]] gate
("read the real OpenAPI doc first; don't design against assumed capabilities").
This is the actual prerequisite for Orchestrator's QMS API integration step —
see [[Auth & Persistence Index]]'s current-status line: *"Next: QMS API
integration — that's the actual reason this whole auth effort exists."*

**Spec file**: ![[QMS API - OpenAPI Spec (v2, as of 2026-08-07).json]] — the
verbatim spec, kept in the vault so this is never "go re-read the OneDrive
file" again. [[UnitPrep File Locations]] still tracks the live OneDrive
source path (`api-1.json`) for whenever a newer version needs re-pulling; this
copy is the point-in-time reference this whole note set is built from. If the
API changes, re-copy and re-date the filename rather than editing this one in
place, then diff before rewriting the domain notes.

**Title**: "Public Gateway WebApi", **version**: `v2`. The name itself
("Gateway", "for Integrators" — see `LeaseForIntegrators` in the Leases
schema) confirms this is QMS's actual third-party-integration surface, not an
internal API incidentally exposed.

## Notes in this set

- [[QMS API - Endpoint Catalog]] — all 92 endpoints, grouped by the 25 tags
  the spec itself uses (Companies, Facilities, Units, UnitGroups, EndUsers,
  Leases, Leads, Payments, Reservations, Specials, Coupons, Reports, etc.)
- [[QMS API - Domain Model & PII]] — the shape of Company → Facility → Unit /
  UnitGroup / Lease / EndUser (tenant), the common Address/Phone objects, key
  enums, and a corrected PII inventory against what
  [[Compliance & Process Readiness]] assumed
- [[QMS API - Tool Opportunities]] — Boris's ask, 2026-08-07: "as you review
  the API try to identify any opportunities for onboarding tools... feel free
  to get creative." Ideas grounded in specific endpoints, not built.
- [[QMS Template Tags — Catalog & Editor Design]] — the template-tagging
  tool, grounded in a real client document and QMS's own Standard Templates
  library.
- [[QMS Template Tags — Open Questions & Mismatches]] — running log of
  unresolved tag questions and real mismatches found along the way.

## Auth — confirmed shape

- **Login**: `POST /api/v2/login`, body `{grantType, clientId, clientSecret}`
  where `grantType` is `Client_Credentials` or `Refresh_Token` (the latter
  taking `refreshToken` instead). Response: `{token, tokenType, expiresIn,
  refreshToken}`.
- Two security schemes are declared at the spec level (`Bearer` — JWT, and
  `Basic` — base64 `ClientId:ClientSecret`), but the only concrete flow shown
  anywhere in the spec is the `/login` client-credentials exchange above.
  Whether Basic is used to *call* protected endpoints directly, or only to
  bootstrap the login call, isn't stated — worth confirming with Boris's
  colleague alongside the base-URL question below, not assumed either way.
- This is a **per-client-company OAuth2-client-credentials-style setup**:
  each Orchestrator-managed client would need its own `clientId`/`clientSecret`
  issued against their QMS company, matching the Platform Vision's "credential
  entry screen for that client's QMS API" step exactly.

## Scope correction, 2026-08-07: not an onboarding-intake channel

Boris corrected the working assumption behind [[QMS API - Tool
Opportunities]]'s first pass: this API is **the escape hatch, not the front
door** — built for a live client to export their data (e.g. if they leave
for a competitor) and for day-to-day operations on facilities already on
QMS. **Net-new client onboarding does not go through this API.** A separate
team imports a new client's data into QMS through its own internal process;
Orchestrator's tools (dedup, Group Prep) only prepare data beforehand and
were never going to be the thing pushing it in either way.

This matches the API's own shape, independent of being told: **there is no
create endpoint anywhere for Units or UnitGroups** — every operation under
both tags is `GET` (read) or a rate/class `PUT`/`PATCH` (update an
*existing* row). If onboarding intake were this API's job, unit/unit-group
creation would be the first thing it needed, and it's exactly what's
missing. Confirms Boris's own read: "very limited when it comes to writing."

**What this means going forward**: treat this API as a **verification/audit
surface over data someone else already imported**, not a data-entry channel.
See [[QMS API - Tool Opportunities]]'s Go-Live Readiness Auditor for the
idea this reframing actually supports well.

## Auth, continued: per-operation permission scoping

Missed on the first pass (only `summary` fields were extracted, not the
richer `description` field each operation carries). Re-checked: **91 of 105
operations declare an explicit required permission** in their description,
e.g. `Facility: ApiReadEndUsers`, `Facility: ApiCreatePaymentMethod`,
`Facility: ApiUpdateLease`. This means QMS's own client-credential model is
almost certainly **scoped per operation per facility**, not just
authenticated-or-not. Relevant for whenever Orchestrator's own QMS
credentials get provisioned: worth asking whether a client-credential pair
can be scoped to read-only / specific-operation access (which would fit a
verification-only tool much more safely than a broad grant), rather than
assuming it's all-or-nothing.

## Open blocker: no base URL

The spec's `servers` array is **empty** — confirmed by parsing the JSON, not
just eyeballing it. Every path is relative (`/api/v2/companies/{companyCode}/...`)
with nothing to resolve it against. Boris is checking with a colleague as of
2026-08-07; **this blocks any real Postman/integration test**, not just
Orchestrator code. Update this note once the base URL (per-environment? one
global gateway host?) is known — it changes whether "the QMS API" is one
constant or something Orchestrator's per-client config needs to store per
company.

## The placeholder-tag question — answered, confirmed absent

Boris's idea for a next Orchestrator module: a **template editor using
placeholder tags** (merge-field-style, e.g. `{{TenantName}}`) for
customizing document templates. Checked exhaustively against the full spec
text, not just the tag list:

- `grep`-equivalent full-text search across the entire 602KB spec for
  `placeholder`, `template`, `merge field`, `macro`, `token`: **zero** hits
  for "placeholder", "merge field", or "macro" anywhere in the document.
- The only "template" hits are unrelated: `isDelinquencyTemplateAssigned` /
  `isMoveInTemplateAssigned` — two booleans on the **Unit** object saying
  *whether* a delinquency-letter or move-in-document template has been
  assigned to that unit, with no visibility into the template's content, and
  a `templateId` (uuid, opaque) on the active delinquency process. QMS
  clearly has templates internally; the API exposes only "is one assigned"
  and "which id", never the template body or any tag/field list.
- The lease document endpoint (`GET .../leases/{leaseId}` → `document` field,
  schema `ReadLeaseDocumentGatewayResponse`) returns exactly two fields:
  `isDocumentSigned` and `signedDocumentUrls` (an array of URL strings). The
  document itself is generated and signed **entirely server-side on QMS's
  end** — the API hands back a link to the finished PDF, never the source
  template, its fields, or anything a client-side editor could hook into.

**Conclusion: confirmed, not just "appears to be."** There is no
template/placeholder/merge-field capability anywhere in this API surface —
not partially, not under different terminology I can find. If QMS's own UI
has a template editor, it isn't reachable through this gateway at all. This
matches Boris's own read. If there's vendor terminology for this that
wouldn't show up under any of the strings checked, worth a direct question to
the colleague who owns the base-URL answer rather than more spec-mining —
the spec itself has nothing further to search for.

**Revived 2026-08-07, from the other direction**: the API can't back this,
but QMS's own template-editor **UI** has a full, stable merge-tag catalog —
Boris pulled it directly (221 tags, 14 document contexts). That's enough to
build the editor against, without any API support, by treating the tag
catalog as its own known-and-maintained dataset rather than something
Orchestrator would discover live. See [[QMS Template Tags — Catalog & Editor
Design]] for the full catalog, the context-scoping structure it needs, and a
DB-vs-hardcode design recommendation.

## Standing rule adopted 2026-08-07

Boris: **"as a general rule, when new features are discussed, quietly check
the API and see if we can leverage it for anything."** Applies from here
forward to every Orchestrator feature conversation, not just this session —
recorded as a durable rule (see `remember` call this session) so it survives
context resets, not just written here.

## Related

- [[Platform Vision (Onboarding Orchestrator)]] — the QSX vs. QMS
  distinction, the gradual-build sequencing that gates API integration behind
  auth, and the original instruction to read this doc before designing
  anything QMS-related
- [[UnitPrep File Locations]] — where the live/updatable copy of the spec
  lives outside the vault
- [[Auth & Persistence Index]] — QMS API integration is the named next step
  after auth
- [[Roles & Permissions — Design Discussion]] — the onboarding_manager
  tool-access-granularity question this session also addressed
- [[Compliance & Process Readiness]] — the PII/data-profile assessment
  [[QMS API - Domain Model & PII]] corrects against real schema fields
