---
date: 2026-08-07
description: "Full 92-endpoint catalog of the QMS Public Gateway WebApi v2, grouped by the spec's own 25 tags. Companion to QMS API Index."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS API — Endpoint Catalog

All paths are relative to the (currently unknown — see [[QMS API Index]])
gateway host and share the prefix `/api/v2/companies/{companyCode}/...`
(company-scoped) or `/api/v2/companies/{companyCode}/facilities/{facilityCode}/...`
(facility-scoped within a company). `companyCode` and `facilityCode` are
short codes, not the internal `id` uuids — confirmed from the path parameter
types across every operation.

## Companies & Facilities

| Method | Path (from `/api/v2`) | What |
|---|---|---|
| GET | `/companies/{companyCode}` | Read one company |
| GET | `/companies/{companyCode}/facilities` | List facilities for a company (paginated) |
| GET | `/companies/{companyCode}/facilities/{facilityCode}` | Read one facility |
| GET | `/companies/{companyCode}/facilities/{facilityCode}/field-settings` | Per-facility move-in/move-out field requirements |
| GET | `/companies/{companyCode}/facilities/{facilityCode}/billing-calendars` | Facility billing calendar |

## Units & UnitGroups

| Method | Path | What |
|---|---|---|
| GET | `/facilities/{facilityCode}/units` | List units (filter: Search, IsActive, IsDamaged, IsRentable, IsDelinquent, Status) |
| GET | `/facilities/{facilityCode}/units/{unitNumber}` | Read one unit — includes nested `tenant` + `lease` summary if occupied |
| PUT | `/facilities/{facilityCode}/units/{unitNumber}/rates` | Update one unit's rates |
| PUT | `/facilities/{facilityCode}/units/rates` | **Bulk** update unit rates |
| PUT | `/facilities/{facilityCode}/units/{unitNumber}/street-rate` | Update one unit's street rate |
| PUT | `/facilities/{facilityCode}/units/street-rates` | **Bulk** update unit street rates |
| PUT | `/facilities/{facilityCode}/units/class` | **Bulk** update unit classes |
| PATCH | `/facilities/{facilityCode}/units/{unitNumber}/isRentable` | Toggle rentability |
| GET / PATCH | `/facilities/{facilityCode}/units/{unitNumber}/desirability-rank` | Read/update desirability rank (search-result ordering) |
| GET | `/facilities/{facilityCode}/unit-groups` | List unit groups (= unit types, e.g. "10x10") |
| GET | `/facilities/{facilityCode}/unit-groups/statistics` | Occupancy %, vacant/occupied/rentable counts, rate stats **per unit group** |
| PATCH | `/facilities/{facilityCode}/unit-group/{unitTypeId}/rates` | Update rates for a unit group |
| PATCH | `/facilities/{facilityCode}/unit-group/{unitTypeId}/street-rates` | Update street rate for a unit group |
| PUT | `/facilities/{facilityCode}/unit-groups/rates` | **Bulk** update unit group rates |
| PUT | `/facilities/{facilityCode}/unit-groups/street-rates` | **Bulk** update unit group street rates |
| GET | `/facilities/{facilityCode}/unit-groups/{unitTypeId}/move-in-url` | Tenant-portal move-in URL for a unit group |
| GET | `/facilities/{facilityCode}/unit-groups/{unitTypeId}/reserve-url` | Tenant-portal reservation URL for a unit group |

## EndUsers (tenants/prospects — see [[QMS API - Domain Model & PII]] for full field list)

| Method | Path | What |
|---|---|---|
| POST | `/facilities/{facilityCode}/end-users` | Create end user |
| GET | `/facilities/{facilityCode}/end-users/search` | Search (Search, Status, Page, Size) |
| GET / PUT | `/facilities/{facilityCode}/end-users/{endUserId}` | Read/update one end user |
| PUT | `/facilities/{facilityCode}/end-users/{endUserId}/alternate-contacts` | Replace alternate contacts |
| PUT | `/facilities/{facilityCode}/end-users/{endUserId}/military-profile` | Replace military profile (SCRA-related fields) |
| GET | `/facilities/{facilityCode}/end-users/{endUserId}/keycodes` | Access-control keycodes issued to the tenant |
| GET / POST | `/facilities/{facilityCode}/end-users/{endUserId}/notes` | List/add notes |
| GET | `/facilities/{facilityCode}/end-users/{endUserId}/notes/{noteId}` | Read one note |
| POST | `/facilities/{facilityCode}/end-users/send-reset-password-email` | Tenant-portal password reset |

## Leases & Lease actions

| Method | Path | What |
|---|---|---|
| GET | `/facilities/{facilityCode}/leases` | List leases (rich filter: TenantId, move-in/out/paid-through/created date ranges, Status) |
| GET | `/facilities/{facilityCode}/leases/{leaseId}` | Read one lease — `tenantId`, dates, `document` (signed-URL only), `leaseOrigin`, `leaseType` |
| PUT | `/facilities/{facilityCode}/leases/{leaseId}/additional-information` | Update additional info |
| PATCH | `/facilities/{facilityCode}/leases/{leaseId}/expected-move-out-date` | Set expected move-out date |
| GET / PATCH / DELETE | `.../leases/{leaseId}/next-effective-rate` | Scheduled future rate change |
| GET | `.../leases/{leaseId}/effective-rates` | Current effective rate |
| GET | `/end-users/{endUserId}/leases/{leaseId}/auto-billing` | Auto-billing methods on file |
| GET | `/end-users/{endUserId}/leases/{leaseId}/future-charges` | Calculate future charges |
| GET | `/end-users/{endUserId}/leases/{leaseId}/payment-history` | Payment history |
| POST | `/end-users/{endUserId}/leases/{leaseId}/payment` | Process a lease payment |
| GET | `.../end-users/{endUserId}/balance-due` / `.../leases/{leaseId}/balance-due` | Balance due, tenant- or lease-scoped |
| GET | `.../units/{unitNumber}/delinquency-overview` | Active delinquency process for a unit |
| POST | `/end-users/{endUserId}/leases/{leaseId}/move-out` | Initiate move-out |
| GET | `.../units/{unitNumber}/overlock-overview`, `.../leases/{leaseId}/overlock-overview`, `.../access-control/overlock-overview` | Overlock status: unit-, lease-, and facility-wide |

## Move-ins

| Method | Path | What |
|---|---|---|
| POST | `/facilities/{facilityCode}/move-ins` | Start move-in (`endUserId` + `unitNumber` → `leaseId`) |
| GET | `/facilities/{facilityCode}/units/{unitId}/move-in-charges` | Charges preview (accepts `coverageId`/`specialId`/`couponCode`) |
| POST | `.../move-ins/{leaseId}/invoices` / `.../invoices/{invoiceId}` | Create / submit move-in invoice |
| GET | `.../move-ins/{leaseId}/invoices` | Read move-in invoice |
| POST | `.../move-ins/{leaseId}/complete` | Complete move-in with payment |

## Leads

| Method | Path | What |
|---|---|---|
| GET | `/facilities/{facilityCode}/leads` | List leads in facility (Search, Statuses, paginated) |
| GET | `/end-users/{endUserId}/leads` | Leads for a specific end user |
| GET / POST | `/facilities/{facilityCode}/leads` / `/leads/{leadId}` | Read/add lead |
| PATCH | `/leads/{leadId}/interests`, `/leads/{leadId}/status` | Update interests / status |
| POST | `/leads/{leadId}/follow-ups` | Add follow-up |
| PUT | `/leads/{leadId}/notes` | Add note |
| GET / POST | `/companies/{companyCode}/lead-sources`, `/facilities/{facilityCode}/lead-sources` | List/create lead sources, company- or facility-scoped |
| GET | `.../lead-sources/{leadSourceId}` | Read one lead source |

## Reservations

| Method | Path | What |
|---|---|---|
| GET | `/facilities/{facilityCode}/reservations` | List (Statuses, paginated) |
| GET | `/facilities/{facilityCode}/reservations/settings` | Facility reservation settings/defaults |
| GET | `/reservations/{reservationId}` | Read one |
| PATCH | `/reservations/{reservationId}/expiration-date` | Update expiration |
| GET / POST | `/units/{unitNumber}/reservation` | Read/create reservation for a specific unit |
| PATCH | `/units/{unitNumber}/reservations/{reservationId}/status/canceled` | Cancel |
| POST | `/unit-groups/{unitGroupId}/reservation` | Reserve **any** unit from a group (idempotency-key header supported) |

## Payments & Payment Methods

| Method | Path | What |
|---|---|---|
| POST | `/end-users/{endUserId}/payment` | Process a tenant-level payment |
| POST | `/end-users/{endUserId}/leases/{leaseId}/payment` | Process a lease-level payment |
| POST | `/end-users/{endUserId}/payment-methods/ach-eft` | Create ACH/EFT method on file |
| POST | `/end-users/{endUserId}/payment-methods/credit-card-lightbox` | Create card method via **Lightbox** (hosted/tokenized — PCI stays off this API, see [[QMS API - Domain Model & PII]]) |
| POST | `/payments/lightbox-sessions` | Start a Lightbox payment session |
| POST | `/payments/lightbox-sessions/method-on-file` | Start a Lightbox method-on-file session |

## Coverage Plans, Specials & Coupons

| Method | Path | What |
|---|---|---|
| GET | `/companies/{companyCode}/coverages/{coverageId}` | Coverage plan by id |
| GET | `/facilities/{facilityCode}/coverages` | Coverage plans for facility |
| GET | `/units/{unitNumber}/coverages` | Coverage plans available to a unit |
| GET | `/companies/{companyCode}/specials`, `/specials/{specialId}` | Company-level specials |
| GET | `/facilities/{facilityCode}/specials`, `/specials/{specialId}` | Facility-level specials |
| GET | `/units/{unitNumber}/specials` | Specials for a unit |
| PATCH | `/facilities/{facilityCode}/specials/{specialId}` | Assign/unassign a special to a unit or unit group |
| GET | `/companies/{companyCode}/specials/{specialId}/coupons`, `/facilities/{facilityCode}/coupons` | Coupons for a special / for a facility |

## Reports

| Method | Path | What |
|---|---|---|
| GET/POST | `/facilities/{facilityCode}/reports/coverage-activity` | Coverage activity report |
| GET/POST | `/companies/{companyCode}/reports/journal-entries`, `/facilities/{facilityCode}/reports/journal-entries` | Journal entries, company- or facility-scoped |
| POST | `/facilities/{facilityCode}/reports/movement-analysis` | Movement analysis report |
| POST | `/facilities/{facilityCode}/reports/in-place-rates-by-unit` | In-place rates by unit |

## Auth

| Method | Path | What |
|---|---|---|
| POST | `/login` | Client-credentials or refresh-token exchange → Bearer JWT |

## Related

- [[QMS API Index]] — auth shape, base-URL gap, placeholder-tag answer
- [[QMS API - Domain Model & PII]] — the actual field-level shape of Company/
  Facility/EndUser/Lease/Unit/UnitGroup
- [[QMS API - Tool Opportunities]] — ideas mapped to specific rows in this
  table
