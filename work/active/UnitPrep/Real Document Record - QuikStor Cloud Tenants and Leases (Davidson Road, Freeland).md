---
date: "2026-10-30"
description: "Real QuikStor Cloud Tenants.csv + Leases.csv pairs from the Davidson Road (1st prelim) and Freeland (final 2026-10-27) pulls: exact headers, row/lease shapes, how Leases gives dedup real unit numbers, redacted repo fixtures and expected output."
project: unitprep
status: active
quarter: Q4-2026
tags:
  - real-document
  - fixture
  - work-note
---

# Real Document Record - QuikStor Cloud Tenants and Leases (Davidson Road, Freeland)

Written for Claude: exact over narrative, long over short. Rule: [[Real Documents Are the Spec]]. Work it supports: [[QuikStor Cloud Tenants Vendor Format (Dedup)]] (the "Update 2026-10-30" section), shipped as `unitprep-api` 1.9.138.

## 1. Provenance
- Original paths (company Dropbox, `KoBre Dropbox/QS Fileserver/Shared/QMS Onboarding/`):
  - Davidson: `Davidson Road Self Storage/Davidson Road Self Storage/Preliminary Data/1st Prelim Data/{Tenants,Leases}.csv`
  - Freeland: `Freeland Warehousing & Storage/Freeland Warehousing & Storage/Final Data/Freeland Warehousing & Storage 2026-10-27/Freeland Warehousing & Storage 2026-10-27/{Tenants,Leases}.csv`
- Obtained: pulled by the onboarding team from each facility's QuikStor Cloud (the vendor's own export of its cloud product); read in place 2026-10-30, nothing copied out except the redacted fixtures below.
- Sizes / SHA-256 (first 16 hex): Davidson Tenants 52,219 B `29481787487b0c11`; Davidson Leases 64,570 B `6a2f6eec819c56c5`; Freeland Tenants 23,798 B `023cca2eeb914ce8`; Freeland Leases 24,871 B `dc68d821973a0498`. All UTF-8, no BOM, LF line endings.
- Repo fixtures: `unitprep-api/dedup/tests/fixtures/quikstor_cloud/{davidson,freeland}/{Tenants,Leases}.csv`
- Fixtures are **redacted copies**. Replaced by stable placeholders that preserve "which rows share a value" (same normalized value gets the same placeholder): first/last/company names (`FirstN`/`LastN`/`CompanyN`), email (`userN@example.test`), street (`N Test St`), city (`CityN`), postal code, every phone number (`555NNNNNNN`). Blanked: middle name, other email, address line 2, special tenant note, driver's license, date of birth, unit name/phone, commanding officer, ETS date. In `Leases.csv` everything except `LegacyLeaseId`, `LegacyTenantId`, `LegacyUnitId`, `UnitNumber` and `LeaseStart` is blanked (balances, rents, specials). Tenant IDs, unit numbers and structure are the real ones. The generator was a throwaway script (not kept); the fixtures are the artifact.

## 2. Structure facts (measured 2026-10-30 by a Python csv profile of the real files)
| | Davidson Road | Freeland |
|---|---|---|
| Tenants.csv rows | 291 | 129 |
| distinct `LegacyTenantId` | 291 | 107 |
| Tenants rows per id | 1 for all 291 | 1 (88 ids), 2 (16), 3 (3), identical rows |
| Leases.csv rows | 344 | 129 |
| leases per tenant | 1 (249), 2 (31), 3 (11) | 1 (88), 2 (16), 3 (3) |
| ids only in one file | 0 / 0 | 0 / 0 |
| blank `UnitNumber` in Leases | 0 | 0 |
| repeated Tenants ids whose rows differ | 0 | 0 |

**The two pulls differ in how Tenants.csv already repeats people** (Freeland: once per lease, identical; Davidson: once per tenant). Same export family, different export version. One rule covers both: one record per lease row, carrying the tenant's details.

Davidson `Tenants.csv` header (33): `Email,FirstName,MiddleName,LastName,CompanyName,AccountType,Gender,CellPhoneNumberPrefix,CellPhoneNumber,HomePhoneNumberPrefix,HomePhoneNumber,WorkPhoneNumberPrefix,WorkPhoneNumber,LegacyTenantId,OtherEmail,AddressStreet1,AddressStreet2,AddressCity,AddressState,AddressPostalCode,AddressCountry,SpecialTenantNote,DriversLicense,DriversLicenseState,DateOfBirth,Source,Language,MilesFromSite,NSFCounter,ETSDate,UnitName,UnitPhoneNumber,CommandingOfficer`

Freeland `Tenants.csv` header (32): same but no `Gender`, and `AddressLine,AddressLineOptional,City,State,PostalCode,Country` instead of `AddressStreet1,AddressStreet2,AddressCity,AddressState,AddressPostalCode,AddressCountry`.

Davidson `Leases.csv` header (26): `LegacyLeaseId,LegacyTenantId,LegacyUnitId,UnitNumber,SecurityDepositPaid,ConversionBalance,PTD,InvoicesCreatedUntil,LeaseStart,LeaseStartDate,LeaseEnd,InvoiceForXMonths,DelinquencyOption,ExpectedMoveOutDate,LastPaymentDate,LinkedLeasesIds,Insurance,DueMonthly,Rent,Balance,LastRentRaiseDate,LastRentRaiseAmount,NextRentRaiseDate,NextRentRaiseAmount,HasActiveSpecial,Specials`. Freeland's is the same minus `LeaseStartDate` (25).

## 3. Field-by-field (what dedup reads from Leases)
| Location | Column | Meaning | Mapping | Why |
|---|---|---|---|---|
| Leases.csv | `LegacyTenantId` | the tenant who holds the lease | canonical `TenantId` | the join key to Tenants.csv (which maps the same column to `TenantId` and `CustNumb`) |
| Leases.csv | `UnitNumber` | the unit's visible number (e.g. `A28`) | canonical `UnitNumber` | replaces the placeholder unit (the tenant ID) on the tenant's records |
| Leases.csv | `LegacyLeaseId`, `LegacyUnitId` | internal ids | signature only | recognition (the 4-header signature `LegacyLeaseId, LegacyTenantId, LegacyUnitId, UnitNumber` identifies the file) |

Deliberately left alone: balances, dates, rents, specials, insurance, `LinkedLeasesIds` (not dedup inputs); `AlternateTenants.csv` (alternate contacts: still supporting, not compared); `Units.csv` (no tenant link).

## 4. Decisions
- Boris, 2026-10-30: "Leases join" (the open item "using `Leases.csv`, needs the join step").
- A leases file is a **unit link**, not an ordinary join: it has a tenant ID and a unit but no customer name, so the existing name-and-unit join cannot match it. New module `dedup/src/unit_link.rs`; `join::merge_joined` applies unit links first. (Rejected: teaching the ordinary join to match on tenant ID too, which would blur two different shapes; rejected: a new `file_role` value, since `join` already exists and needed no schema change.)
- Identical repeated tenant rows are **collapsed** before the tenant is spread over their units (Freeland). A tenant with **different** rows that do not match the unit count is **refused** (error), never guessed. A tenant with no lease keeps its row. A lease for an unknown tenant is ignored. A repeated (tenant, unit) pair counts once. Blank lease units are skipped.
- Records keep `CustNumb` = tenant ID; `UnitNumber` = real unit. Findings and the duplicate-customer entries now list real units.

## 5. Expected output
- Redacted fixtures (run on every `cargo test`): `dedup/tests/quikstor_cloud_leases_fixtures.rs`, tests `redacted_davidson_road_leases_give_one_record_per_lease` and `redacted_freeland_leases_give_one_record_per_lease`.
- Davidson: **344 records, 291 unique tenants, 42 multi-unit tenants, 0 flagged groups, 4 duplicate-customer records.** Freeland: **129 records, 107 unique tenants, 19 multi-unit, 0 flagged, 7 duplicate-customer records.** The real files give identical numbers (ignored tests `davidson_road_leases_give_one_record_per_lease` and `freeland_leases_give_one_record_per_lease`, with `UNITPREP_DEDUP_QC_DAVIDSON_DIR` and `UNITPREP_DEDUP_QC_FREELAND_DIR` pointing at the real folders). The duplicate-customer counts equal the earlier runs without leases (4 and 7), so joining units changed nothing about what is flagged, only what the findings call the records.
- Reproduce: `cargo test -p unitprep-dedup --test quikstor_cloud_leases_fixtures` (add `-- --ignored --nocapture` with the two env vars for the real files).
- Registry check (real migration chain): `cargo test -- --ignored the_seeded_registry_classifies_real_export_headers` in `api-dev`: `Davidson Leases.csv` classifies as `QuikStor Cloud Leases` with role `join`.

## 6. Open questions and known gaps
- The redaction keeps equality (same normalized value, same placeholder) but destroys *similarity*: the typo-variant (2) and related-tenant (5) counts recorded for Davidson on 2026-10-07 are **not** reproduced by the fixture, and are not asserted. To pin them, a fixture would need near-miss placeholders.
- `AlternateTenants.csv` alternate contacts remain uncompared; a join keyed by `LegacyTenantId` would be the same shape of work.
- Group Prep still has no row for this family's `Units.csv`.
- A tenant whose Tenants rows differ *and* do not match their lease count would stop a whole run (clear error). None in the two real pulls; if one turns up, decide per case whether to degrade instead of refusing.
- Freeland's 2026-10-27 final pull is a later pull than the preliminary one the first QuikStor Cloud row was built from (126 tenant rows then, 129 now): not the same file.

## 7. Raw excerpts (redacted fixture, Davidson)
`Tenants.csv` row 1: `user1@example.test,First1,,Last1,,Individual,M,+1,5550000001,+1,5550000001,,,168311,,1 Test St,,City1,Pennsylvania,00001,United States,,,,,Yellow Pages,English,0,0,,,,`

`Leases.csv` rows 1-2: `122095,168311,29791,A3,,,,,07/09/2012 04:00:00,,,...` and `122098,168314,29675,A28,,,,,05/26/2012 04:00:00,,,...`

## 8. Links
- Commits / versions: `unitprep-api` 1.9.138, migration `20261030120000_use_quikstor_cloud_leases_for_units`.
- Session work note: [[QuikStor Cloud Tenants Vendor Format (Dedup)]]
- Related records: [[Real Documents Are the Spec]]
