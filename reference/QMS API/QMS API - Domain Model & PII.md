---
date: 2026-08-07
description: "QMS's actual object shapes — Company/Facility/Unit/UnitGroup/Lease/EndUser — read from the OpenAPI schemas, plus a corrected PII inventory against Compliance & Process Readiness's assumptions."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS API — Domain Model & PII

Field lists below are read directly off the OpenAPI `components.schemas`
definitions in ![[QMS API - OpenAPI Spec (v2, as of 2026-08-07).json]], not
inferred — every field named here is one QMS's own schema declares.

## The hierarchy

```
Company (companyCode)
  └─ Facility (facilityCode)        — one physical storage location
       ├─ Unit (unitNumber)          — a physical storage unit
       │    ├─ UnitType / UnitGroup  — the "10x10", "5x5", etc. category
       │    └─ current tenant + lease summary, nested inline when occupied
       ├─ Lease (leaseId)            — the time-bounded occupancy record
       │    └─ tenantId (FK to EndUser, not embedded)
       └─ EndUser (endUserId)        — a person: prospect, tenant, or former tenant
```

**This confirms the occupancy-as-link-table default already banked in
[[response-to-groks-tenant-piigdpr-implementation-suggestions|the Grok
response]]** — QMS itself doesn't denormalize tenant PII onto every historical
record. A `Lease` carries only `tenantId` (a bare FK) plus dates; the *current*
occupant's name is denormalized onto the live `Unit` read as a convenience
(`tenant: {id, firstName, lastName, fullName}` — name only, no PII beyond
that), but the authoritative person record lives solely on `EndUser`. Good
external validation that the link-table pattern isn't an invention — it's how
the system Orchestrator integrates with already works.

**`EEndUserStatus` is `Prospect | CurrentTenant | FormerTenant | Temporary`.**
Worth noting for whenever a tenant/EndUser mirror table gets designed: this is
QMS's own tri/quad-state model for "how real is this record," a reasonable
starting point rather than inventing a status enum from scratch.

## Company & Facility

Both have near-identical shapes: `id` (uuid), `code`, `name`, `isActive`,
`location` (`lat`, `lng`, `timeZoneId`), `createdAt`/`updatedAt` (date only,
no time), `phoneNumbers[]`, `addresses[]`. Company additionally has `email`
and `facilityCount`; Facility additionally has `tenantPortalUrl` (nullable).

`FacilityFieldSettings` (`GET .../field-settings`) is **not** a document
template system (see [[QMS API Index]]'s placeholder-tag section) — it's a
per-facility toggle set for which End User fields are required/shown during
move-in (`endUserBasic`, `endUserAlternateContact`, `endUserMilitaryInfo`,
`endUserMiscInfo`, `lienProperty`, `vehicleInfo` groups) and move-out
(`basic` + a `categoryOptions` string array — move-out reason categories,
configurable per facility).

## Unit

Key fields beyond the obvious (`number`, `isActive`, `isDamaged`,
`isRentable`, `streetRate`, `webRate`): `availabilityStatus` (enum:
`Vacant | Occupied | Reserved | Unavailable | Company`), `unitType` +
`globalUnitTypes[]`, `isDelinquencyTemplateAssigned` /
`isMoveInTemplateAssigned` (booleans only — see placeholder-tag finding),
`hasUnitInsuranceSettings`, nullable `lease` (id, paidThroughDate,
effectiveRate, isDelinquent) and nullable `tenant` (id, name only) when
occupied.

`UnitAttributes` is a rich physical-characteristics object: `width`,
`length`, `height`, `area`, `doorWidth`/`doorHeight`, `doorType`,
`insideOutside`, `floor`, `covered`, `climateControlled`, `nearElevator`,
`driveUpAccess`, `bottleCapacity`, `furnished`, `power`, `lighting`, `alarm`,
`class`, `doorCount`, `conversionType`, `smartLockEnabled`,
`monitoringEnabled` — all nullable, i.e. all optional at the QMS end. See
[[QMS API - Tool Opportunities]] for the completeness-check idea this
suggests.

## UnitGroup (unit type)

`ReadUnitGroupGatewayResponse`: `id`, `label`, `streetRate`, `webRate`,
`availableSpecial`/`availableWebSpecial` (nested special summary),
`availableTotal`, `availableAtThisPrice`, `availableAtThisWebPrice`,
`totalInGroup`, `reservedTotal`. The separate `GET .../unit-groups/statistics`
endpoint adds `numberOfRentableUnits`, `numberOfVacantUnits`,
`numberOfOccupiedUnits`, `percentageOfOccupiedUnits`, plus
`classStreetRates`/`classWebRates`/`squareFootage` breakdowns.

## Lease

`ReadLeaseGatewayResponse`: `id`, `balanceDue`, `expectedMoveOutDate`,
`paidThroughDate`, `moveInDate`, `moveOutDate`, `moveOutReason`,
`moveOutDescription`, `tenantId` (bare FK), `document` (see below),
`nextEffectiveRate`, `special`, `leadSource`, `leaseOrigin` (enum:
`Quikstor | TenantPortal | Integration`), `leaseType` (enum: `MoveIn |
Transfer | Migration` — **QMS has a native "Migration" lease type**, worth
knowing if Orchestrator's dedup/migration output ever needs to distinguish
migrated-in leases from organically-created ones), `propertyInformation`,
`vehicleInformation`, `additionalInformation`.

**`document` (`ReadLeaseDocumentGatewayResponse`) is exactly two fields:
`isDocumentSigned` (bool) and `signedDocumentUrls` (string[])** — this is the
entirety of what the API exposes about the actual lease document. No content,
no field list, no template reference. Confirms the placeholder-tag finding in
[[QMS API Index]] from a second angle: even the one place a "document" shows
up in the API, it's a finished, opaque, already-rendered artifact.

## EndUser (the tenant/prospect person record) — full PII surface

This is QMS's tenant record and the single most PII-dense object in the API.
Reading the actual schema **corrects an assumption** in
[[Compliance & Process Readiness]], which characterized UnitPrep's tenant PII
profile as "name, address, phone, email... no SSNs." The real `EndUser`
schema (`ReadEndUserGatewayResponse`, `CreateEndUserGateway.Request`,
`UpdateEndUserGateway.Request`) carries more than that assumption covered:

- **Basic**: `firstName`, `lastName`, `fullName`, `email`, `companyName`,
  `gender`, `dateOfBirth`, `accountType` (`Individual | Company`),
  `phoneNumber` (single primary), `address`, `profileImageUrl`.
- **Driver's license**: `number`, `state`, `expirationDate` — a government-ID
  number, not previously accounted for.
- **Alternate contacts[]**: each with its own `firstName`, `lastName`,
  `email`, `relationship`, `address`, `phoneNumber` — i.e. **third parties'**
  PII collected under the tenant's record, not just the tenant's own.
  Anonymizing a tenant without also handling their alternate contacts would
  leave third-party PII behind.
- **Military profile** (`MilitaryProfileResponse`) — collected for SCRA
  (Servicemembers Civil Relief Act) purposes, and genuinely sensitive:
  `branchOfService`, `rank`, `isRetired`, `placeOfBirth`, `militaryUnit`,
  `squadron`, `militaryEmail`, **`lastFourSsnDigits`**, `division`,
  `typeOfService`, `currentDutyLocation` (address), `dateEnteredService`,
  `endOfActiveServiceDate`, `militaryId`, plus a **commanding officer's**
  name/phone and an **agent's** name/email/phone/address — again, third
  parties' contact info nested under the tenant.
- **Delivery options[]**: `deliveryType` (`Sms | Email | Mail`) preferences.
- Read-only counters: `numberOfNotes`, `numberOfDocuments`.
- **Notes** (separate `GET/POST .../end-users/{id}/notes`): free-text,
  potentially containing anything a staff member typed.
- **Keycodes** (`GET .../end-users/{id}/keycodes`): access-control codes
  issued to the tenant.

**Correction to log against [[Compliance & Process Readiness]]**: the
"no SSNs" line needs qualifying — there is no *full* SSN anywhere in this
API, but `lastFourSsnDigits` is a real partial-SSN field, and driver's
license numbers are a government ID the original assessment didn't count.
Neither changes the CCPA/breach-notification conclusions on its own (partial
SSN and a DL number are both still short of what most state breach laws
key on), but the *next* time that compliance assessment gets revisited, it
should be against this field list, not the earlier "name, address, phone,
email" shorthand. Not fixing the other note in place — flagging here per the
correction-sweep convention so whoever next touches
[[Compliance & Process Readiness]] does it with the full picture.

## Common building blocks

- **Address** (request/response pair): `street1` (required), `street2`,
  `city`, `postalCode`, `state`, `country` — response version has everything
  nullable, request version requires `street1`/`city`/`postalCode`/`state`/
  `country`.
- **PhoneNumber**: `countryCode` (pattern `^\+([0-9]){1,4}$`), `number`
  (pattern `^([0-9]){4,14}$`), `isPrimary`.
- **Payment methods**: `PaymentGatewayRequest` is a discriminated union —
  `paymentType` enum selects between `paymentAch`, `paymentCreditCardLightbox`,
  or `paymentOnFile`. **Card payments only ever go through "Lightbox"**
  (QMS's own hosted/tokenized payment flow — `credit-card-lightbox` payment
  methods, `lightbox-sessions` endpoints) — Orchestrator would never handle
  raw card numbers even if it called these endpoints directly, which is a
  clean confirmation of [[Compliance & Process Readiness]]'s existing
  PCI-DSS "does not apply" conclusion, now backed by the actual API shape
  rather than just the product description.

## Related

- [[QMS API Index]] — auth, base URL gap, placeholder-tag finding
- [[QMS API - Endpoint Catalog]] — every operation these schemas back
- [[QMS API - Tool Opportunities]] — ideas this domain model suggests
- [[Compliance & Process Readiness]] — the PII assessment corrected above
- [[response-to-groks-tenant-piigdpr-implementation-suggestions|Response to
  Grok's tenant-PII/GDPR implementation suggestions]] — the occupancy-link-
  table default this note's hierarchy section validates
