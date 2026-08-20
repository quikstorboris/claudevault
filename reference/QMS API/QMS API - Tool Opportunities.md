---
date: 2026-08-07
description: "Onboarding-tool ideas grounded in real QMS API endpoints. Revised same day after Boris corrected the API's actual role: read-heavy operations/export surface for already-live facilities, not an onboarding data-intake channel."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS API — Tool Opportunities

Boris's ask, 2026-08-07: having read the real API, identify onboarding-tool
ideas it could support. First pass (below, in the superseded section) assumed
the API could be used to push onboarding data into QMS. Boris corrected that
same day — see **What this API is actually for**, which changes which ideas
survive.

## What this API is actually for (corrected 2026-08-07)

Boris's own framing: think of this API as **the escape hatch, not the front
door** — it exists so a live client can export their data if they leave for
a competitor, and to support day-to-day operations (leads, payments,
reservations, reports) once a facility is already on QMS. **Net-new client
onboarding does not go through this API at all.** A new client's data gets
imported into QMS by a *different team*, through a separate (internal,
non-gateway) process — the checklist below calls them out doing lease
imports and leaving notes in ClickUp. Orchestrator's own tools (dedup, Group
Prep) only *prepare* the data beforehand; they don't push it in, and per this
correction, this API isn't the thing that would do that pushing either.

This is corroborated independently by the API's own shape, not just Boris's
statement: **there is no create endpoint anywhere for Units or UnitGroups** —
checked across every operation under both tags. Units and UnitGroups support
only `GET` (read) and rate/class `PUT`/`PATCH` (update-existing). If this API
were meant for onboarding intake, unit/unit-group creation would be the first
thing it needed and it's the one thing conspicuously absent. Matches Boris's
own read: "very limited when it comes to writing."

**What this reframes:**
- The API's relevance to Orchestrator is **verification/audit of data that
  already made it into QMS** (via the other team's import), not moving data
  there itself. The Go-Live Readiness Auditor below is the shape that fits.
- The "API path" step in [[Platform Vision (Onboarding Orchestrator)]]'s
  original entry flow (credential screen → "look up data in the DB" as an
  alternative to file upload, during onboarding prep) is now in tension with
  this — a genuinely **new** client isn't in QMS yet at prep time, so there's
  nothing to look up. Not resolved here; flagged in that note for whenever
  it's revisited. It may still make sense for a narrower case (an existing
  multi-facility client onboarding one more facility, where the company
  record already exists) — worth asking Boris rather than assuming.

## Superseded ideas (kept for the record, not deleted)

~~**Rate Loader** — push Group Prep's output straight into QMS via the bulk
rate endpoints.~~ Doesn't work for its intended onboarding use case: those
endpoints update rates on units/groups that **already exist**, and a net-new
client's units don't exist in QMS until the other team's import runs. Might
still be useful for *existing* live clients correcting rates post-go-live,
but that's a different (live-ops) use case than onboarding prep, and not
Orchestrator's stated scope.

~~**Client-picker via the company/facility list**~~ — the list is real
(`GET /companies/{code}/facilities`), but it lists clients **already on
QMS**. A net-new onboarding's whole point is that the client isn't there
yet, so this doesn't serve the "pick an existing client" step for the
typical onboarding case it was proposed for.

## The idea worth building: Go-Live Readiness Auditor

Boris confirmed this is genuinely interesting: there's a real, currently
**entirely manual** pre-go-live/go-live-day checklist (below), and a one-click
checker against it would meaningfully speed up the process. This fits the
API's real shape exactly — it's a **read-only verification pass over data
someone else already imported**, which is precisely what this
read-heavy/write-limited API is good for. This also folds in and replaces
what were separate "post-migration cutover check" and "baseline report"
ideas from the first pass — same read-only-verification shape, one tool.

### Checklist mapping (against the manual checklist Boris supplied, 2026-08-07)

Legend: ✅ direct API match · 🟡 partial/indirect match, needs judgement or
extra logic · ❌ not exposed by this API at all.

**Showstoppers**

| Checklist item | Verdict | How |
|---|---|---|
| Company & Facility exist in QMS | ✅ | `GET /companies/{code}`, `GET .../facilities/{code}` — 404 or `isActive:false` = fail |
| Facility DNS configured | ❌ | No DNS/Communications surface in this API at all |
| Facility email assigned | ❌ | Not exposed — `Company.email` exists but is company-level, not the facility DNS/branding email the checklist means |
| Duplicate tenant corrections complete | ❌ (not needed here) | Corrected 2026-08-07: dedup runs on **source** client data *before* migration, not on QMS's copy — by the time records are in QMS they're already clean. Re-checking for dupes against live QMS data would be solving a problem that shouldn't exist at that point; not part of this tool |
| Elavon account activated / credit card integration configured | 🟡 | No direct "is Elavon enabled" read, but see "Test Credit Card Payment" below — same probe answers both |
| Payment settings configured | 🟡 | Partial, via billing calendar (see Final Settings Check below) |

**Verify Setup**

| Checklist item | Verdict | How |
|---|---|---|
| Users (Owner/staff accounts, user groups) | ❌ | No Users/staff-account surface anywhere in the API — 0 hits for "Users" across the whole spec |
| Fees, security deposits, taxes | 🟡 | No facility-level "list configured fees" read, but `GET .../units/{unitId}/move-in-charges` returns `securityDeposit`, `oneTimeFees[]` (named), and `rents[].recurringFees[]` (named) for a specific unit — call per unit/unit-type to confirm expected line items actually come back non-zero |
| Trigger (delinquency) templates assigned | 🟡 | `Unit.isDelinquencyTemplateAssigned` (bool, per unit) — sweep all units, flag `false`. Can't preview the *content* of the process on a non-delinquent unit, only presence/absence of an assignment |
| Lease templates (correct tags, assigned) | ❌ | `isMoveInTemplateAssigned` confirms *a* template is assigned, never its content — this is the same gap as [[QMS API Index]]'s placeholder-tag finding, and it's exactly why this checklist step has to stay manual |
| Delinquency process assigned & configured | 🟡 | Same `isDelinquencyTemplateAssigned` flag; process detail only readable via `delinquency-overview` and only once a unit is actually delinquent |
| Coverage setup | ✅ | `GET .../coverages` (facility-level plans) + `GET .../units/{unitNumber}/coverages` (per-unit) + move-in-charges' `coverage` field — three corroborating reads |
| Specials created & assigned | ✅ | `GET .../specials` (facility) + `GET .../units/{unitNumber}/specials` (per-unit assignment) — direct match |
| Retail items configured | ❌ (pre-go-live) | No facility-level items list; `InvoiceRetailItemGatewayResponse` only appears on an already-generated invoice, i.e. after the fact, not as a pre-launch config check |
| Units present in QMS | ✅ | `GET .../units` (paginated list) — count check |
| Unit-level Delinquency Policy / Security Deposit / Recurring Fees / Move-In Admin Fee / Transfer Fee | ✅ | **Strongest match in the whole checklist** — `GET .../units/{unitId}/move-in-charges` returns all of these by name in one call: `securityDeposit`, `oneTimeFees[]` (Admin Fee, Transfer Fee show up here by name), `rents[].recurringFees[]` (rent tax, tech fee, etc.) |
| Unit-level Coverages | ✅ | Same move-in-charges call, `coverage` field, plus `GET .../units/{unitNumber}/coverages` |
| Lease & move-in documents + document order | ❌ | Never exposed — consistent with the placeholder-tag finding |
| Site Access / Lockout settings (Requires Manual Overlock Y/N) | ❌ (config) / 🟡 (behavior) | No settings read; but `shouldLockoutCauseOverlocking` / `hasLockoutReason` / `currentlyOverlocked` on the Overlock endpoints are *live derived state* per unit — spot-checking a sample unit's behavior is an indirect proxy, not a full settings sweep |
| Overlock task configuration & user assignment | ❌ | No Users/task API |

**Validate Conversion (Go-Live Day)**

| Checklist item | Verdict | How |
|---|---|---|
| Unit count (Management Report totals/vacant) | ✅ **strong** | `GET .../unit-groups/statistics`, summed across every unit group in the facility, gives exact `numberOfRentableUnits`/`numberOfVacantUnits`/`numberOfOccupiedUnits` — better than anything in the Reports tag, which has no occupancy-count report at all |
| Tenant Contact List anomaly scan | ❌ (not needed here) | Same correction as above — formatting/anomaly cleanup is dedup's job on the source data pre-migration, not something to re-run against QMS's already-clean copy |
| Test Credit Card Payment | ✅ **strong, zero-risk** | `POST .../payments/lightbox-sessions/method-on-file` performs, per its own operation description, "a $0 account verification... no money is moved," and its documented precondition is exactly "the facility must have Elavon or Elavon Canada enabled." Success vs. error is a faithful automated stand-in for "does the Lightbox modal appear" — and answers the Showstoppers' Elavon/credit-card items too, for free |
| Verify Facility Email | ❌ | Not exposed |
| Payment scheme (Anniversary / 1st of Month + pro-rate days) | ✅ **confirmed exact match** | `GET .../billing-calendars` → `billingCalendarValue` enum is literally `Anniversary \| FirstOfTheMonth`, plus `maxCalendarDayForProRateOnlyAppMoveIn` / `...OnlineMoveIn` for the pro-rate-days setting |
| Reservation Days | ✅ | `GET .../reservations/settings` → `reservationMaximumDaysAhead` |
| Activate Tenant Portal | 🟡 unverified | `Facility.tenantPortalUrl` (nullable) is the only related field found — plausible that null means "not yet activated," but this is inferred, not documented as an activation flag anywhere in the spec. Confirm before relying on it. |

### What this means for scoping the tool

Roughly a third of the manual checklist (Coverage, Specials, unit count,
credit-card/Elavon test, payment scheme, reservation days, and — the biggest
win — the whole Security Deposit/Recurring Fees/Admin Fee/Transfer Fee
cluster) is a **clean, confident, one-click API check**. A smaller chunk
(delinquency-template presence, lockout behavior) is buildable but needs
judgement calls rather than a bare pass/fail. A real chunk (Users, DNS,
facility email, retail items, lease/move-in document content and order,
task assignment, and — corrected 2026-08-07 — duplicate-tenant/contact-list
checks, which are dedup's job upstream on source data, not this tool's)
**cannot or should not** be checked via this API, and stays out of scope —
worth being upfront about that split rather than promising a checker that
covers the whole list. Not scoped further than this — a real design pass
would need to decide how ❌ items get surfaced (still require the human
step, vs. silently omitted from the checker's report).

## Revived 2026-08-07: template editor, via a self-maintained tag catalog

Not ruled out after all — see [[QMS Template Tags — Catalog & Editor
Design]]. The **API** still has nothing to build against (confirmed,
unchanged), but QMS's own template-editor **UI** has a stable 221-tag
catalog across 14 document contexts, which Boris pulled directly. Enough to
build the editor against as a DB-stored, admin-editable dataset — doesn't
need the API at all. Open question that note flags: whether the editor's
output is text a human pastes into QMS's own editor, or something rendered
independently — the API's lack of a template-write endpoint makes the
former the only option today unless QMS confirms otherwise.

## Related

- [[QMS API Index]] — auth, base URL, placeholder-tag finding, and the
  write-limited/scope correction this note builds on
- [[QMS API - Endpoint Catalog]] — every endpoint cited above
- [[QMS API - Domain Model & PII]] — full field shapes behind the ✅/🟡 calls
- [[QMS Template Tags — Catalog & Editor Design]] — the revived template-
  editor idea, sourced from QMS's UI rather than its API
- [[Platform Vision (Onboarding Orchestrator)]] — the "API path" tension
  flagged above, and the existing tool suite this auditor would join
