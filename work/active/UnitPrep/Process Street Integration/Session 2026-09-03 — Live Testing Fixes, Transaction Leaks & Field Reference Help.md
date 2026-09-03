---
date: 2026-09-03
description: "Live-usage bug hunt on the just-shipped Client record UI: a missing encryption key, a NUMERIC/f64 decode bug, a real credentials_added_to_qms mapping bug, two transaction-leak incidents (root-caused live via pg_stat_activity, both fixed), PartyCard formatting/SSN masking, and a new Field Reference help table built from a full 163-field PS audit."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-03 — Live Testing Fixes, Transaction Leaks & Field Reference Help

Direct continuation of [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]] -- that note covers what got *built*; this one covers what broke once Boris actually used it against Prairie Enterprises' real data, and the Elavon tab (Phase 4 item 5) getting built along the way. See [[Implementation Plan]] for current phase status.

## Elavon tab shipped (Phase 4 item 5)

Built in direct response to the Elavon-data-missing bug below: a Facility page tab showing whichever is true -- a linked Merchant Account run's summary + owner/signer parties, or (if unlinked) an auto-suggested candidate via the same title-correlation logic search already used, shown with a link to the real PS run and a "Confirm this link" action (deliberate friction -- never auto-accepted). When correlation is genuinely ambiguous (a real duplicate PS submission, confirmed for Carpentersville: two Merchant Account runs both named for it), every candidate is listed as a clickable option instead of forcing pure manual entry. Falls back to a manual run-ID paste field when nothing matched at all.

New backend module `api::clients_elavon` (`GET`/`POST .../elavon`, `.../elavon/link`), gated on `client_ops.perform` for the write. This is also the general, repeatable fix for what created Prairie's own Elavon gap in the first place -- a facility whose Merchant Account run was never correlated (or correlation simply found nothing) previously had no path to get linked at all short of a one-off DB backfill.

## Real bugs found from live usage, all fixed

### 1. `CLIENT_PII_ENCRYPTION_KEY` was never actually set on the real server

The Elavon tab's first real "link" attempt panicked: `NotConfigured("CLIENT_PII_ENCRYPTION_KEY is not set")`. Confirmed via `.env.local` -- the key genuinely didn't exist, even though the code has required it since Phase 1 (2026-08-28). Nothing had ever actually exercised the ingest path against the real running server before this, since Prairie's original creation never had a resolved Merchant Account run id to ingest. Generated a real key (`openssl rand -hex 32`, matching `TOTP_ENCRYPTION_KEY`'s own format) and added it. Also fixed the underlying robustness gap this exposed: `ingest_merchant_account_run`/`insert_party` used to `.expect()` a missing key into a request-handler panic; now returns a typed `IngestMerchantAccountError` that surfaces as a clean `503 encryption_not_configured` instead.

### 2. `ownership_percent` NUMERIC vs. Rust `f64` -- a real decode bug, only surfaced once real data existed

Right after the first successful link (Kyle Lindley et al. really did land in Postgres), both `get_company_detail` and the new Elavon tab started 500ing on every subsequent load -- **including one that made the Company page "unreachable even after logout/login"**, since it wasn't an auth problem at all: `ownership_percent` is `NUMERIC` in Postgres, but the Rust row struct declared `Option<f64>`, and sqlx has no built-in NUMERIC→f64 decode. This had existed since the Company page was first built but never fired, because no facility had a real party row to decode until this session's first real link. Fixed by casting to `float8` in both SQL queries; verified directly against real data (Kyle Lindley's 30% decodes correctly now).

### 3. "Add Credentials to QMS" showing No for a step Boris had actually completed in PS

Root cause: **it isn't a form field at all** -- it's a checklist *task* ("Add Credentials to QMS"), confirmed live against the real API (`GET /workflow-runs/{id}/tasks`). Nothing had ever ingested task status for the Merchant Account workflow (`clients::ingest::ingest_facility`, the original Phase 1 trigger, already did -- but the live-used `clients::create`/`api::clients_elavon` paths didn't), so the column just sat at its schema default (`false`) forever. Now derived from real task completion (`merchant_account_mapping::credentials_added_to_qms_from_tasks`) in every ingestion path, with a live-verified regression test. Existing already-linked rows (Highway 20, Pyott Road) needed a one-time backfill against their real PS task status -- Carpentersville's own `false` was double-checked and is genuinely correct (that step really isn't done there).

### 4. Two transaction-leak incidents -- the session's biggest finding

Both `api::clients_elavon`'s "link" action and the original `api::clients_create` "Add to OO" flow opened their database transaction *before* fetching from Process Street's live API, holding it open across that network round trip. One of Boris's own repeated link attempts left a Postgres backend `idle in transaction` for 3+ minutes, blocking `GET /clients`' session-resolution query behind its lock -- diagnosed live via `pg_stat_activity`, not inferred (confirmed `wait_event_type = 'Lock'` on the stuck query). Killed the stuck backend to unblock immediately, then restructured **both** endpoints into three phases: a short DB-only pre-check, the live PS fetch with no transaction open at all, then a fresh short transaction for the write. `clients::create::create_company_and_facilities` (the old combined function) still exists but is now `#[cfg(test)]`-only, kept purely so the module's own live tests can still wrap a whole create-and-rollback cycle in one transaction without leaving real rows in the shared dev database. Full writeup, including the general lesson, in [[Gotchas#Never hold a database transaction open across a live external API call]].

### 5. The pool-size fix from the prior session wasn't enough on its own

Same incident review surfaced that the earlier `max_connections` bump (5→20, see the prior session note) was necessary but the *real* floor on latency was fixed by items 4 above, not pool size alone. See [[Gotchas#The application's own Postgres connection pool can be the bottleneck, not Neon or its pooler]] for the standalone lesson.

## PartyCard: shared formatting + masking fix

Boris asked for phone as `xxx-xxx-xxxx`, DOB as `mm-dd-yyyy` with no time, and SSN masked behind a Show/Hide toggle -- previously shown in full plaintext everywhere. Extracted a shared `PartyCard` component (`unitprep-ui`) used by both the Company page's Owner(s) Information and the Facility page's Elavon tab, so the fix applies in both places from one source. New `lib/format.ts` helpers: `formatPhone` (strips non-digits, formats a real 10-digit number, passes anything else through unchanged) and `formatDateOnly` (reads the literal `YYYY-MM-DD` prefix off an ISO string rather than parsing through `Date` -- PS's own DOB values carry an inconsistent, seemingly arbitrary time-of-day component, e.g. `13:00:00.000Z` on one real record and `16:00:00.000Z` on another for the same form, so converting through `Date`'s local/UTC getters risked shifting the calendar date by a day depending on the reader's timezone).

## Field Reference help table (new, not in the original plan)

Boris asked for a searchable reference -- same UX as the QMS Tag Catalog admin page (`admin/client-ops/qms-tags`) -- explaining which PS run/step/field every OO field on the Company/Facility pages comes from. Built as `lib/fieldProvenance.ts` (a static, hand-maintained array -- no backend endpoint, since this is documentation about the mapping code itself, not live data) rendered by a new `FieldReferenceHelp` modal, wired onto both pages via a header button.

**Compiled from a real 163-field live audit** of Highway 20's actual Pre-App run (`GET /workflow-runs/{id}/form-fields`, following pagination), cross-referenced against real task names (`GET .../tasks`) to get accurate step names -- not guessed. Every currently-mapped OO field is listed with its real PS field key/label and step; every field PS captures that OO doesn't show yet is listed too (`status: not_yet_mapped`), including: Legal Name/Business DBA/Ownership Type (computed in code for company naming but never persisted or shown), revenue and credit-card/ACH volume fields, Year/Months Established, Legal Address override, Business Contact name, processor/conversion meta fields, CRM link, and -- notably -- EIN/Bank Routing+Account Number/the QMS credential bundle, all of which are **already captured and encrypted** in `facility_merchant_accounts.encrypted_secrets` but have no read/decrypt endpoint yet (same shape as the party PII decrypt path, just not built for the facility-level secrets bundle).

## Open items for next session

- **The encrypted facility-level secrets (EIN, bank routing/account, QMS credentials) have no read path** -- `decrypt_party_pii` exists for party PII; nothing analogous exists for `FacilitySecrets`. Real production question: should bank account/EIN ever render in the UI even masked, or is "captured, never displayed, exportable only via a deliberate separate flow" the right call? Not decided yet.
- **The Financial Information / Elavon field-audit gap list** (see the Field Reference table's own `not_yet_mapped` rows) is now a real backlog, not just a chat message -- prioritize with Boris which of these actually matter for OO's own workflows before mapping more fields for their own sake.
- **`create_company_and_facilities`'s live tests** (`clients::create::live_tests`) currently fail against the real dev DB -- not a regression, they assume Highway 20's Intake run isn't already imported, and it now genuinely is (Prairie is real, committed data). Needs either different real test-fixture run ids or an acceptance that these need `#[ignore]`d-and-run-manually judgment about current DB state before trusting a red result.
- Phase 4 items 4, 6, 7 (Users tab, DropBox tab/connection flow, `ps_task_status` "done in PS" indicators) still not started.

## Related

- [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]]
- [[Implementation Plan]]
- [[Client & Facility Schema (Process Street-Sourced)]]
- [[Gotchas]]
- [[Production Readiness Checklist]]
