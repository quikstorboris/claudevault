---
date: 2026-10-01
description: "Reference-only map of what data in the LG Squared SiteLink pull can migrate to QMS: files, join keys, coverage, gaps, control totals, quirks."
tags: [work-note, sitelink, qms-migration, reference]
status: active
quarter: Q4-2026
project: lg2-migration
---

# SiteLink migratable data - LG Squared (pull 2026-10-01)

Source: `LG2 LLC / LG Squared RV & Ministorage / Preliminary Data / 1st Pull / ... Receipt Details/` - 36 xlsx reports, 1 facility (SiteID 12), 308 units, 240 active ledgers. Counts below are rows with real data, not header counts. Reusable method: the `sitelink-migration-analysis` skill. Dedup: SiteLink tenants format, see [[SiteLink Tenants Vendor Format (Dedup)]].

## 1. Join keys

| Key | Meaning | Carried by | Distinct |
|---|---|---|---|
| LedgerID | one lease of one tenant on one unit (primary join) | Directory, Rent Roll, Walk Thru, Past Due, All Unpaid Charges, Unpaid Charges, Aged Receivables, Payment Activity, Prepaid Rent Liab., Refund Summary, Gate Access, Calls and Notes | 240 active; 402 / 257 / 244 / 2062 in all-time reports |
| TenantID | one contact record; several ledgers can share it | Directory, Rent Roll, Walk Thru, Past Due, Receipts, Gate Access | 193 active tenants, 31 hold 78 units |
| UnitID / sUnitName | unit (name is unique) | Rent Roll, Directory, Gate Access / all unit reports | 308 |
| ChargeID | one charge line | All Unpaid Charges, Receipt Details | 1346 / 88 |
| CreditCardID | card on file | Credit Card Roll, Directory, Rent Roll | 117 / 137 |
| AccessID | one gate access record | Directory, Gate Access | 240 / 2062 |
| iUnitTypeID / UnitTypeID | unit type | Price List, Vacant Units, Directory | 7 types |
| iReceiptNum | receipt | Receipt Details, Receipts | 75 |

Names are not keys: some reports truncate (`Dalpes, G`), others carry the full name.

## 2. File catalog

| Report | Grain | Rows | Areas |
|---|---|---|---|
| Directory | active ledger, 409 cols (183 populated) | 240 | A6 A8 A11 A17 A18 A19 |
| Rent Roll | unit, 374 cols (154 populated); 68 vacant rows have blank LedgerID | 308 | A3 A6 A8 A11 A17 A18 A19 |
| Custom Unit Report | unit | 308 | A3 |
| Unit Status | unit | 308 | A3 A4 |
| Walk Thru | unit (balance, paid-thru, zone) | 308 | A3 A8 |
| Vacant Units | vacant unit, rates, days vacant | 67 | A2 A4 |
| Complimentary Units | free units | 3 | A4 |
| Unit Notes | unit note | 4 | A5 |
| Unit History | past tenancies, unit A01 only | 8 | A7 |
| Price List | type x size | 27 | A2 |
| Occupied Units | occupied ledger, rent vs std | 240 | A8 A10 |
| Rent Change History | ledger, latest rate change | 254 | A9 |
| Past Due Balances | past-due ledger | 120 | A14 A18 A20 |
| Balances Due | past-due ledger by category | 120 | A14 |
| All Unpaid Charges | unpaid charge, current ledgers | 1346 (120 ledgers) | A14 |
| Unpaid Charges | ledger, 8 aging buckets, 137 moved-out | 257 | A14 A7 |
| Aged Receivables | ledger, 7 aging buckets, 161 moved-out | 402 | A14 A7 |
| Prepaid Rent Liabilities | ledger prepaid balance | 37 | A15 |
| Prepaid Rent | forward-month prepaid receipts | 45 | A15 |
| Refund Summary | ledger refund balance | 47 | A15 A7 |
| Payment Activity | ledger payment totals, 2026 YTD, rent only | 244 | A16 |
| Daily Payments | day by tender, facility total, 2026-01-01..10-01 | 124 | A16 control |
| Receipt Details | receipt line, 2026-10-01 only | 88 | A16 |
| Receipts | receipt by tender + TenantID, 2026-10-01 only | 88 | A16 |
| Credit Card Roll | card on file | 117 | A17 |
| Gate Access | access record, all-time, `Current` flags 240 | 2062 | A19 A7 |
| Calls and Notes | event log, 2026-10-01 only (88 autobill, 13 card adds) | 101 | A20 A17 |
| Financial Summary | charge catalog (13) + payment groups | 13 | A11 A23 |
| General Journal Entries | GL lines for 2026-10-01 | 31 | A23 |
| Income Analysis, Management Summary, Management History, Occupancy Statistics, Occupied History, Rental Activity, Rate Management History | aggregates | - | control totals only |

Non-data files: 3 site-map PNGs (SiteLink, Goodlew Earth, survey), rental agreement `.doc` (marked WILL CHANGE - DO NOT USE), Go-Live recording.

## 3. Data areas

| # | Area | Primary | Combine with | Key | Coverage / gap |
|---|---|---|---|---|---|
| A1 | Site profile | last sheet of any workbook | - | SiteID | 1 row: name, PO box address, phone, email, QuickBooks, accrual |
| A2 | Unit types + rate card | Price List | Custom Unit Report, Vacant Units | iUnitTypeID | 7 types, 27 type x size rows; std, weekly, web, 28-day rate; push rate all 0; tax flags per type are in Rent Roll `bChargeTax1/2` (false) |
| A3 | Unit inventory + attributes | Custom Unit Report | Rent Roll (UnitID, desc, push rate, map top/left), Walk Thru (zone/row/aisle) | sUnitName | 308 units; power 82; climate/inside/alarm 0; floor 1 (300) / 0 (8); entry Exterior 91; roll-up door 75; 5 "Virtual Unit"; no height |
| A4 | Unit status / flags | Unit Status | Rent Roll, Vacant Units, Complimentary Units | sUnitName | rented 240 / vacant 67 / unrentable 1; gate-locked 80; overlocked 0; auction 0; complimentary 3 (one tenant) |
| A5 | Unit notes | Unit Notes | Rent Roll `sUnitNote`/`dUnitNote` | sUnitName | 4 notes |
| A6 | Tenant contacts | Directory | Rent Roll, Past Due (mobile/email), Refund Summary | TenantID | 240 rows: phone 240, mobile 94, email 237, company 24, alt contact ~50, business 12, additional 4, tenant note 33 |
| A7 | Former tenants | Gate Access | Aged Receivables, Unpaid Charges, Refund Summary, Unit History | LedgerID | 1822 historic ledgers (names, unit, code); contact only for 47 refund ledgers |
| A8 | Active leases | Directory | Rent Roll, Occupied Units, Walk Thru | LedgerID | lease #, lease date, move-in, anniversary, billing freq (all Monthly), rent, std rate, paid-through (120 past today / 120 before), tax-on-rent flag (226 yes / 14 no), invoice prefs, 21 ledgers with past-due suspended, 25 transfers |
| A9 | Rate change history | Rent Change History | Occupied Units, Rent Roll `dcSchedRent` | LedgerID | 254 rows, only 20 with an old rate; no scheduled changes pending |
| A10 | Concessions | Occupied Units (Variance, Discount) | Rent Roll `dcRent` vs `dcStdRate` | LedgerID | 67 ledgers below std rate; plan names empty; plan definitions absent |
| A11 | Fees + recurring charges | Directory | Financial Summary (charge catalog) | LedgerID, ChargeDescID | per ledger: cut-lock 50, NSF 30 (8 ledgers 0), admin 0 (1 ledger 50), late fees 10 / 10 / 20 flat starting 2008-07-01; recurring charges 1-13 all 0 (client does not use them - expected); charge catalog: Lock Rental, Prox Card, Rent, Damages, Admin Adjustment, Golf Cart - Electricity, Rent - Misc, Insufficient Notice Fee, Late Fee #4/#5, 3 refund-dismissed |
| A12 | Insurance | Directory | - | LedgerID | none - client does not offer insurance (expected, not a gap) |
| A13 | Security deposits | Directory | Custom Unit Report | LedgerID | none - client takes no deposits (expected, not a gap) |
| A14 | Opening AR | All Unpaid Charges | Past Due, Balances Due, Aged Receivables, Unpaid Charges | LedgerID, ChargeID | 1346 rent charges on 120 ledgers, 2015-11 to 2026-10, no tax; moved-out balances only as aging buckets |
| A15 | Credits, prepaids, refunds | Prepaid Rent Liabilities | Prepaid Rent, Refund Summary | LedgerID | 37 prepaid ledgers; 47 refund ledgers; prepaid receipts run to 2030-07 |
| A16 | Payment history | Receipt Details | Receipts, Payment Activity, Daily Payments, Directory `dPmtLast` | iReceiptNum, LedgerID | **partial**: 88 receipts for one day; YTD totals per ledger (rent only); daily facility totals; last payment date/amount per ledger (232) |
| A17 | Autopay + payment methods | Credit Card Roll | Directory/Rent Roll, Calls and Notes | CreditCardID | 117 cards (Visa 92, Mastercard 25), tokens 105, autobill on 117 ledgers, ACH none (client does not offer ACH - expected); sensitive |
| A18 | Delinquency state | Past Due Balances | Directory, Aged Receivables | LedgerID | 120 ledgers, days late up to 3987, last 3 notes each (templated "Account Status"); no auction; process config absent |
| A19 | Access control | Gate Access | Directory `sAccessCode`, Walk Thru | LedgerID | 2062 codes; one keypad zone ("All Keypads") and one time zone ("24 Hour Access"); never-lockout 1; sensitive |
| A20 | Notes + comms | Directory `sTenNote` | Past Due notes, Calls and Notes | LedgerID | 33 tenant notes; call log is one day |
| A21 | Vehicles | Directory | - | LedgerID | description on 3 ledgers, driver license on 13 |
| A22 | Marketing | Directory `Mktg*` | - | TenantID | 4 rows |
| A23 | GL + controls | General Journal Entries | Financial Summary | AcctCode | 23 accounts (assets 1000-1202, liabilities 2020-2082, income 4000-4900, COGS 5000-5002) |

## 4. Control totals (use to validate loads)

| Item | Value | Source |
|---|---|---|
| Units total / occupied / vacant / unrentable | 308 / 240 / 67 / 1 | Occupancy Statistics |
| Complimentary units | 3 | Occupancy Statistics, Complimentary Units |
| Total area | 82,830 sf | Occupancy Statistics |
| Gross potential / actual occupied rent | 20,620 / 19,612 | Occupancy Statistics |
| Past-due total (current ledgers) | 96,117.37 | All Unpaid Charges |
| Aged Receivables total (incl. moved-out) | 164,551.23 | Aged Receivables (sum of dcTotal) |
| Unpaid Charges rent total (incl. moved-out) | 170,005.67 | Unpaid Charges sheet 2 |
| Prepaid rent liability, ending | 8,132.88 | Prepaid Rent Liabilities |
| Refund balances, beginning | 3,694.86 | Refund Summary |
| 2026 YTD receipts | 155,812.27 | Daily Payments = Payment Activity = Management Summary |
| Single-day receipts 2026-10-01 | 88 receipts, card only | Receipt Details |

## 5. Gaps - re-pull or ask the client

**The one report that needs complete history: Receipts** (the pull's `Receipts` / `Receipt Details` reports). Re-run it with the date range from the facility's first transaction (earliest move-in in the data is 2006-07-01) through today. It is the only source of transaction-level payments per tenant; every other payment file is a total or a single day. Include both layouts if the pull offers both: Receipt Details has charge description, check/card reference and authorization code per line; Receipts has tender columns plus `TenantID`.

Optional, only if the history is being migrated:

| Area | Missing | Action |
|---|---|---|
| A20 | call and letter history (the pull has one day) | Calls and Notes, same wide date range as Receipts |
| A16 | per-ledger charge history (what was billed, not just what was paid) | per-ledger charge/payment history report (name TBC) |
| A10 | special / concession / discount plan definitions | export the discount plan setup (report name TBC) |
| A18 | notice schedule, late-fee automation, lien/auction steps ("Past Due Events" disabled on some ledgers) | screenshots or setup export |
| - | merchandise item list (GL 1200s/4060/5000s exist) | export merchandise setup |
| - | tax rates (only a per-ledger tax-exempt flag) | confirm with client |
| - | reservations / waiting list, tenant documents, e-signed leases | not in pull; ask |

**Expected empty, not gaps (client confirmed 2026-10-01):** insurance (A12), security deposits (A13), recurring charges (A11), ACH (A17).

## 6. Quirks

- Sentinels: `-999` (no value), `1900-01-0x` and `2000-01-01` (placeholder dates), `System.Byte[]` in `uTS` (drop).
- Directory names carry trailing spaces; `TenantName` is "Last, First"; Balances Due and Payment Activity truncate to "Last, F".
- `sReasonComplimentary` is used as a proration note: "ROM" (rest of month) on 131 ledgers, not a complimentary reason.
- Custom Unit Report flags are `X` or blank-space strings. Walk Thru has a unit named `!E04`.
- Sensitive, do not copy into tickets: `sCreditCardNum` (ciphertext), `sToken`/`TokenID`, `sAccessCode`/`GateCode`, `sSSN` (1), `sLicense` (13).
- Dedup on this pull: 240 records, 192 unique tenants, 0 flagged mismatches, 5 related-tenant candidates (shared address, phone or email).

## Related

- [[SiteLink Tenants Vendor Format (Dedup)]]
- [[Dedup Tool Index]]
