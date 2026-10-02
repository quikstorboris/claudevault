---
date: 2026-10-01
description: "SiteLink registered as a dedup tenants vendor format: which reports are the tenant file, how they are recognized, the derive transform, and what dedup can and cannot find on SiteLink data."
tags: [work-note, unitprep, dedup, vendor-format, sitelink]
status: active
quarter: Q4-2026
project: unitprep
---

# SiteLink Tenants Vendor Format (Dedup)

Status as of 2026-10-01: code, migration and tests **committed and pushed** in `unitprep-api` `v1.9.54` (`3ddb33f`). Migration **applied to the Neon dev DB 2026-10-01** (with the QuikStor Cloud one; prod DB branch synced 2026-10-02). The running API reads the vendor registry into a cache, so restart it (or wait for the refresh) before SiteLink files are recognized. First client: LG Squared (see [[SiteLink Migratable Data - LG2 (pull 2026-10-01)]]).

## Which SiteLink files are dedup inputs

Only two of the 36 reports carry name + address + phone + email + unit + ledger on one row:

- **Directory** - 240 rows, one per active ledger. Preferred.
- **Rent Roll** - 308 rows, one per unit; the 68 vacant units have a blank `LedgerID` and no tenant.

Both reduce to the same 240 records. Every other report lacks the address/email columns (Past Due Balances has phone/email but only for delinquent ledgers).

## What was added

- Migration `20261001130000_seed_sitelink_tenants_vendor_format.{up,down}.sql`: vendor `SiteLink` (**since split by `20261001140000` into `SiteLink Directory` and `SiteLink Rent Roll`**, see [[Dedup Folder Scan and File Requirements]]), signature `sUnitName, LedgerID, TenantID, sFName, sLName, sAddr1, sEmail` (present in both reports), transform `derive_sitelink_tenant_fields`.
- Mapping (data only): `LedgerID`->CustNumb, `sUnitName`->UnitNumber, name/company/address/email from the `s*` columns, alt contact from the `*Alt` columns. `TenantID` is not mapped (dedup has no field for it).
- Transform `core/src/vendor_format/transforms/sitelink.rs`: `FirtLast` = first + last (company fallback); `PhoneNumber` = `sPhone`, else `sMobile`; drops rows with no `LedgerID` (Rent Roll vacant units).
- Refactor: `transforms.rs` split into `transforms/{mod,ess,quikstor_cloud,sitelink}.rs` with shared helpers; ingest tests moved to `dedup/src/ingest_tests.rs`. No behavior change; all earlier tests kept.
- Tests: 4 transform tests, 2 ingest tests (recognition + vacant-row drop; a split tenant under two TenantIDs is flagged with real unit numbers). Workspace `clippy -D warnings` and `cargo test` green.

## What dedup finds on SiteLink

Run on the real LG2 files (identical for both reports), **after tenant-ID grouping** ([[Dedup Tenant-ID Grouping and Duplicate Customer Records]]): 240 records, 193 tenants, 31 multi-unit, **0 flagged**, **1 duplicate customer record (Frank Flores)**, 0 typo variants, **5 related-tenant candidates** (Warden household, Thorburn household, a shared phone, Lucero shared email + address, a shared email with a typo domain).

Zero flagged is expected, not a failure: SiteLink keeps contact on the tenant record (`TenantID`), so the 31 tenants holding 78 units share one contact record and cannot disagree. The real SiteLink problem is the inverse, one person entered under two `TenantID`s; LG2 has exactly one (Frank Flores, 2 IDs, identical contact), now reported as a duplicate customer record. The related-tenant and typo checks are the other value.

## Open

- **Group Prep (units) built 2026-10-02** (committed in `unitprep-api`, not yet released; registry row needs migration `20261002120000` applied to the dev DB branch, and an API restart for the 4 h cache). Boris decided **unit group = Type + UnitSize** ("both"), e.g. `Self Storage 10x20`: source is Custom Unit Report; transform `derive_sitelink_unit_group` appends `UnitGroup`; mapped `Number<-UnitName`, `UnitGroup`, `StandardRate`, `Width`, `Length`; the `X`/blank flag columns (Power, Climate, Inside, ...) are deliberately unmapped. On LG2 that gives 20 groups over 308 units (the 27 in the Price List is its type x size rows, not units). Sessions apply a detected vendor's transform at discovery (`Session::apply_vendor_transforms`, idempotent).
- Alternate-contact comparison works (mapped from `*Alt`); business (`*Bus`) and additional (`*Add`) contact blocks are not compared (almost empty).

## Related

- [[QuikStor Cloud Tenants Vendor Format (Dedup)]]
- [[Dedup Folder Scan and File Requirements]]
- [[Shared Vendor-Format Registry (Easy Storage Solutions)]]
- [[Dedup Tool Index]]
