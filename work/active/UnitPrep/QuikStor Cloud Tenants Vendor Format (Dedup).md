---
date: 2026-10-01
description: "Registered QuikStor Cloud's Tenants.csv as a recognized dedup (tenants) vendor format via a new derive transform plus a data-only registry row; verified on the real Freeland file."
tags: [work-note, unitprep, dedup, vendor-format]
status: active
quarter: Q4-2026
project: unitprep
---

# QuikStor Cloud Tenants Vendor Format (Dedup)

Status: code + migration **committed and pushed** in `unitprep-api` `v1.9.54` (`3ddb33f`); migration **applied to the Neon dev DB 2026-10-01** (prod DB branch synced 2026-10-02). The API caches the registry, so restart it for the row to be recognized.

Closes the parked to-do in [[qms-also-needs-registering-as-a-dedup-tenants-vendor-format]] (the QMS tenants side), using a real preliminary pull from Freeland Warehousing & Storage (`1st Prelim Pull/Tenants.csv`, 126 rows).

## Is it the right dedup file? Yes

- One row per tenant record, repeated per lease (126 rows / 105 distinct `LegacyTenantId`), same shape QSX has per unit.
- Seven people appear under 2-3 different tenant IDs (e.g. Tom Barrett x3 IDs with a mistyped phone) — exactly what dedup flags.
- Sibling files in the pull are *not* dedup inputs: `Units.csv` (no tenant link), `AlternateTenants.csv` (same headers plus `Relationship`/`LegacyAlternateTenantId`, keyed by `LegacyTenantId`).

## What was added

- `migrations/20261001120000_seed_quikstor_cloud_tenants_vendor_format.{up,down}.sql` — name `QuikStor Cloud`, `content_type='tenants'`, signature `LegacyTenantId, AccountType, FirstName, LastName, AddressLine, CellPhoneNumber`, `transform_key='derive_quikstor_cloud_tenant_fields'`. `LegacyTenantId` maps to **both** `CustNumb` and `UnitNumber` (pure data) so notes name records by tenant ID instead of printing blank units.
- `core/src/vendor_format/transforms/quikstor_cloud.rs` — `transforms` moved out of the 470-line `vendor_format.rs` (later split further into one file per vendor, see [[SiteLink Tenants Vendor Format (Dedup)]]), then the new transform: derives `FirtLast` (`First Last`, whitespace-collapsed, middle name ignored, `CompanyName` fallback), `PhoneNumber`/prefix (first non-blank of Cell → Home → Work), and blanks the `#NoEmail` / `notprovided@non.com` Email sentinels.
- Tests: 5 transform unit tests, 2 `dedup/src/ingest.rs` tests (recognition + normalization; full pipeline flags a phone mismatch). Full `cargo test --workspace` and `clippy -D warnings` clean.

## Verified on the real file

Run through the exact registry definition (throwaway test, deleted): 126 records → 96 unique tenants, 22 multi-record, **6 flagged groups**, 0 typo-variant, 0 related. Flags were real (phone/address mismatches across IDs for Barrett, Roehnelt, Elsbree, Sheppard, Grant, Campbell).

## Known limits

- Freeland is QuikStor Cloud, so **unit numbers need a join**: Tenants.csv has no unit link and the pull has no leases file. `AlternateTenants.csv` is now registered as a *supporting* format (never pre-selected, refused as a lone file) via [[Dedup Folder Scan and File Requirements]].

- **Alternate contacts are not compared** — they live in `AlternateTenants.csv`; dedup takes one file and does not join. Mapping omits every `AlternateContact*` field.
- Notes say "unit 1034223" where this vendor means a tenant ID (the composer hardcodes "unit").
- Identical repeated rows for one ID count as separate records (assumed one per lease) — can show as "units 87122, 87122".
- `AlternateTenants.csv` also satisfies this signature (superset of headers); recognition is presence-only.
- `Units.csv` from this export family (`Number, LegacyUnitId, UnitType, ...`) matches **no** registered units vendor (QMS units row uses `UnitNumber/SizeCode/...`) — Group Prep would need its own row.
- Row is named "QuikStor Cloud", while the existing units row is "QMS"; assumed the same product family but worth confirming.

## Update 2026-10-01: tenant-ID grouping

`LegacyTenantId` is now also mapped to dedup's canonical `TenantId`, so Tenants.csv groups by tenant id: 105 tenants / 17 multi-unit / 0 flagged / 7 duplicate customer records (Barrett x3 ids, Ross x3, Roehnelt, Elsbree, Sheppard, Grant, Campbell). See [[Dedup Tenant-ID Grouping and Duplicate Customer Records]].

## Related

- [[Shared Vendor-Format Registry (Easy Storage Solutions)]] — the registry and the transform precedent this follows.
- [[Dedup Tool Index]]

## Update 2026-10-07: second header variant (Davidson Road) + Leases.csv

Davidson Road Self Storage's "1st Prelim Data" is the same QuikStor Cloud export family, but `Tenants.csv` / `AlternateTenants.csv` name the address columns `AddressStreet1/2`, `AddressCity`, `AddressState`, `AddressPostalCode` (plus a `Gender` column) instead of `AddressLine`/`City`/`State`/`PostalCode`. The first row's signature requires `AddressLine`, so **no file in the pull was recognized** and dedup refused to run on a manual selection. Fix (migration `20261007150000`, **written and tested; applied to Neon dev 2026-10-07 (together with `20261007140000`); NOT yet committed** while another session had uncommitted ClickUp Copy work in the same repo; `sqlx` applies pending migrations in order, so both were applied together). The running API caches the vendor registry for 4 h: restart it to recognize Davidson files: three additional registry rows, leaving the originals untouched. `QuikStor Cloud Alternate Tenants (street address headers)` (supporting, inserted first because it is a header superset), `QuikStor Cloud (street address headers)` (primary, same derive transform, identity address mapping, `LegacyTenantId` -> `TenantId`) and `QuikStor Cloud Leases` (supporting; `LegacyLeaseId, LegacyTenantId, LegacyUnitId, UnitNumber`; the tenant-to-unit link Freeland lacked, recognized but not joined). The original row's guidance no longer says leases are unsupported. Tests: 2 ingest tests + the real-migration-chain `the_seeded_registry_classifies_real_export_headers` extended with Davidson's headers. Real file through the real pipeline (throwaway test, removed): 291 records, 291 tenants, 0 flagged, 4 duplicate customer records (Johns, Husak, Auth, Demos), 2 typo variants, 5 related candidates. Still open: using `Leases.csv` (needs the join step), and a Group Prep row for this family's `Units.csv`.
