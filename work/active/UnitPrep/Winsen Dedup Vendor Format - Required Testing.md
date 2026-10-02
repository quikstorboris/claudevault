---
date: 2026-10-02
description: "Checklist of what must be tested when Winsen/Sentinel tenant exports are registered for dedup (CustID tenant-ID grouping); blocked on a sample file."
tags: [work-note, dedup, winsen]
status: active
quarter: Q4-2026
---

# Winsen Dedup Vendor Format - Required Testing

Status as of 2026-10-02: **sample found and analyzed (Highway 20 Self Storage, Prairie Enterprises LLC, `Preliminary Data/1st Pull`); build not started, awaiting Boris's go-ahead.** Earlier this note said blocked on a sample. No Winsen tenant export has been seen yet, so no registry row exists. Boris is waiting on real data. This list is drafted from how SiteLink and QuikStor Cloud were onboarded (see [[SiteLink Tenants Vendor Format (Dedup)]], [[QuikStor Cloud Tenants Vendor Format (Dedup)]], [[Dedup Tenant-ID Grouping and Duplicate Customer Records]]); the Winsen-specific items are inferred (TBC) until a file arrives. The only Winsen file seen so far is a *unit list* (`Pyott_Road_Winsen_unit_list_Boris.csv`, a Group Prep case, not dedup).

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

## Findings from the Highway 20 pull (2026-10-02, headers/counts only)

The files are Winsen **printed reports saved as `.xls`**, not flat exports: title rows, a "Page 1" cell, a facility/date/time row, a two-line header (e.g. `Cust` over `ID`), blank rows between records, the header **repeated on every page** (11 times in the contact report), and data in sparse columns (merged-cell layout). Column positions differ per report, so cells must be found by header label, not index.

| File (report) | Gives | Rows | Key |
|---|---|---|---|
| `xref.xls` Tenant Cross Reference | name, address 1/2, city, state, zip, residence + business phone | 540 unit rows | Unit + Customer Name |
| `email.xls` Tenant Email Address Report | email, email-notices flag | 490 | Unit + Customer Name |
| `rentroll.xls` Rent Roll Report | **Cust ID** (the tenant identifier, header `Cust`/`ID`) with unit and name | 482 | Unit + Customer Name |
| `multiple.xls` Tenants with Multiple Units | `Name:` + `CustID:` followed by their unit list | 58 tenants | CustID |
| `tenant.xls` Tenant Status Report | unit status, balances; every unit incl. vacant | 540 | Unit |
| `passcode.xls` | "Other Parties with Access" (possible alternate contacts, TBC) | 1263 | Unit |
| others | billing, deposit, notes, past due, unit list, insurance, monthly tax, autobill | - | not needed for dedup |

Measured: unit + name is a safe join (no duplicate keys in the contact report; 0 mismatches where both files have the unit). 474 of 540 contact rows get a Cust ID; the other 66 are units absent from the rent roll (non-rental or vacant rows, TBC), 490 get an email. 370 distinct Cust IDs over 482 rent-roll rows, 51 of them on several units. The earlier `Duplicate Check/Highway20_duplicate_check_1st_pull.csv` was built from a hand-merged table with the unit number standing in for the customer number (no real Cust ID), so it could not detect one person under two Cust IDs.

## What the build needs (proposal)

1. **Printed-report reader** for `.xls`: find the header row by registered label signature, flatten the two-line header, drop title/page/blank/repeated-header rows, read cells by header position. New generic capability, also useful for other report-style exports.
2. **Multi-file join** (deferred earlier; this is the second case after Freeland): primary contact report plus email and rent roll joined on unit + normalized name, then one normal dedup run. Needs registry roles (primary / supporting join sources), the "Files required" panel text, and run history for several source files (`tool_runs` is single-source today).
3. Registry rows for the three formats with `TenantId <- Cust ID`; tests per the list above using the real headers.
4. Decisions needed: treat units absent from the rent roll as tenants without an id (name grouping) or skip them; use `multiple.xls` only as a cross-check; whether `passcode.xls` Other Parties map to alternate contacts.
