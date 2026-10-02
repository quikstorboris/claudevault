---
date: 2026-10-01
description: "Dedup now groups tenants by the vendor's own tenant id when the format has one and reports one person under several ids as a duplicate-customer-record finding, separate from flagged groups."
tags: [work-note, unitprep, dedup, design]
status: active
quarter: Q4-2026
project: unitprep
---

# Dedup Tenant-ID Grouping and Duplicate Customer Records

Status as of 2026-10-01: **committed and pushed** as `unitprep-api` `v1.9.55` and `unitprep-ui` `v1.6.53`. Migration `20261001150000` (the `TenantId` mappings) **applied to the Neon dev DB**; prod DB branch synced 2026-10-02. Restart the API to pick it up.

## The change

- `TenantRecord.tenant_id` (blank when the format has none). Registry mapping target `TenantId`: SiteLink `TenantID`, QuikStor Cloud `LegacyTenantId`. QSX and Easy Storage Solutions only have a per-unit `CustNumb`, so they keep grouping by name. A format with a real id (Winsen / Sentinel `CustID`, etc.) is just one more mapping entry; none is registered yet because no sample headers exist.
- `grouping::group_records_by_tenant` keys by tenant id, falling back to the name key. It drives `unique_tenants`, `multi_unit_tenants` and the contact-mismatch comparison (flagged groups). `group_records` (name-keyed) is unchanged and still feeds **typo-variant and related-tenant detection**, whose logic was deliberately left alone: a person split across ids still reads as one name there, so it never reports "two different names sharing an address", and the placeholder filter that suppressed the XXXX street address is untouched.
- New finding `duplicate_customer_records` (`dedup/src/duplicate_records.rs`): group the id-keyed tenants by normalized name; any name held by 2+ distinct ids is reported with each id's units, the contact categories that differ across the records (empty when identical), and a plain-English note. Reported separately from flagged groups. Units that merely repeat the id (QuikStor Cloud maps the id into the unit slot) are left out of the note.
- Carried through: report view JSON, CSV/XLSX export (its own marked section after the flagged groups), the run-summary audit JSON, and a UI results section ("Possible duplicate customer records", hidden when empty), also shown in the Onboarding Work tab for saved runs and counted in the summary stats.

## Validated on real data

| File | Tenants / multi-unit / flagged / duplicate records / related |
|---|---|
| LG Squared SiteLink Directory (240 rows) | 193 / 31 / 0 / **1** (Frank Flores: ID 186417 on B18, ID 182866 on B26, contact identical) / 5 |
| LG Squared SiteLink Rent Roll | identical to the Directory |
| Freeland QuikStor Cloud Tenants.csv (126 rows) | 105 / 17 / 0 / **7** / 0 |

Before: LG Squared was 192 / 32 / 0 and never showed Flores. Freeland's six flagged groups (Barrett, Roehnelt, Elsbree, Sheppard, Grant, Campbell) now appear as duplicate-record findings that carry their contact differences with them, and Shane Ross (3 ids, identical contact) surfaces for the first time.

## Behavior to know about

- A name held by several ids with *differing* contact details used to be a flagged group; it is now a duplicate-record finding that lists the differences. Nothing is lost, but the count moves from "flagged" to "duplicate records".
- `TenantRecord` and `DedupReport` gained fields, which changes their persisted (bincode) shape: a dedup session saved before this deploys will not reload (sessions are short-lived). Older cached reports in the browser lack the new field; the UI treats it as empty.

## Related

- [[Dedup Folder Scan and File Requirements]]
- [[SiteLink Tenants Vendor Format (Dedup)]]
- [[QuikStor Cloud Tenants Vendor Format (Dedup)]]
- [[Dedup Tool Index]]
