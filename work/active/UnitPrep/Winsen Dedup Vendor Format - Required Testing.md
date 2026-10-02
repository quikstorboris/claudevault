---
date: 2026-10-02
description: "Checklist of what must be tested when Winsen/Sentinel tenant exports are registered for dedup (CustID tenant-ID grouping); blocked on a sample file."
tags: [work-note, dedup, winsen]
status: active
quarter: Q4-2026
---

# Winsen Dedup Vendor Format - Required Testing

Status as of 2026-10-02: **blocked on a real sample.** No Winsen tenant export has been seen yet, so no registry row exists. Boris is waiting on real data. This list is drafted from how SiteLink and QuikStor Cloud were onboarded (see [[SiteLink Tenants Vendor Format (Dedup)]], [[QuikStor Cloud Tenants Vendor Format (Dedup)]], [[Dedup Tenant-ID Grouping and Duplicate Customer Records]]); the Winsen-specific items are inferred (TBC) until a file arrives. The only Winsen file seen so far is a *unit list* (`Pyott_Road_Winsen_unit_list_Boris.csv`, a Group Prep case, not dedup).

## What is needed first

- A Winsen/Sentinel **tenant export with headers** (one facility is enough), and the name of the report that produced it.
- Confirmation that the tenant identifier column is `CustID` (TBC) and whether it is one id per person or per lease.
- Whether unit numbers are in the same file (QuikStor Cloud's Tenants file had none).

## Tests to run once the sample exists

1. **Recognition by headers:** a registry migration row (signature headers, field mapping, `TenantId <- CustID`, file metadata: `pms`, `report_name`, `file_role`, `selection_priority`, `guidance`). Order it before any format whose headers are a subset of Winsen's. A DB test classifies the real headers (`the_seeded_registry_classifies_real_export_headers`).
2. **Normalization:** a unit test built from the real header row (names, phone fallbacks, email sentinels, vacant/blank rows) in `dedup/src/ingest_tests.rs`; a transform only if the export cannot be handled by renames.
3. **Tenant-ID grouping:** one `CustID` on several units counts as one tenant (multi-unit, not flagged); the same person under two `CustID`s appears once in "Possible duplicate customer records"; blank ids fall back to name grouping.
4. **Known pitfalls:** placeholder values, phone-prefix rules, sister-site sharing (see [[Gotchas]]).
5. **Realistic size:** run the real file; check the check time stays well under the 2 s slow-operation warning (debug build) and that findings are plausible against a manual look.
6. **Folder scan and requirements panel:** the file is classified with the right badge, pre-selected, and the "Files required" panel describes it.
7. **Browser click-through** of the whole dedup page with the real folder (never done for any vendor yet).
8. **Prod DB branch:** the new migration is applied to the dev DB branch first, then synced to the prod DB branch by hand (`scripts/prod_db_sync.sh`).
