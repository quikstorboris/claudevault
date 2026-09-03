---
date: 2026-09-03
description: "Phases 3-5 of the PS integration shipped: the Add-to-OO confirmation screen (Company/Facility redesigned as always-separate), two-phase hybrid re-sync with a new Activity Logs feature, and Phase 4's read-only Client record UI (Company page, facility rail, Facility Policies) — plus a real Elavon-data bug fix and a page-blink performance fix found afterward."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI

Continues [[Implementation Plan]] (Phases 3-5) and [[Process Street Integration — Kickoff & Findings]]. This note carries the detail; the Implementation Plan's phase headers just link back here per this vault's single-source-status convention.

## Company vs. Facility — the either/or design was wrong, reversed 2026-09-02

The Implementation Plan (written 2026-08-31) specified Company/Facility as mutually-exclusive per-row buttons — a row is either the one Company or a Facility, never both. Boris corrected this directly against his own real Prairie Enterprises case: **"what i sent you earlier are all facilities. the company as you well know is Prairie. that needs to have its own section on the review page and that needs to be set as a company for subsequent creation."**

**The real model**: Company is its own section, not a role a facility switches into. Every selected PS run becomes its own `clients.facilities` row — including Highway 20, which also happens to carry the corporate data that seeds the Company section. `pickCompanySourceRun` picks whichever selected run has the fullest resolved company data (preferring one with a real Legal Name from Merchant Account correlation) purely to decide which run's fields seed `clients.companies`; it does not exclude that run from also becoming a facility. Nothing at the schema or handler level required the exclusion — it was a frontend-only rule, and a wrong one.

## Phase 3 — confirmation screen: shipped

- `unitprep-ui`'s `/clients/new` page: Company section + one section per selected facility, pencil-edit-in-place per field, Create button posts to `POST /clients`.
- **Merchant Account correlation carried through to Create** (see the 2026-09-03 Elavon bug below) — `PreviewedRun.merchant_account_run_id` flows from preview through the edited-fields state to `CreateFacilitySelection.merchant_account_run_id`.
- **Create latency fix**: an early real run took ~18s, traced to sequential PS API calls during Create — including one genuinely duplicate fetch of the same run. Fixed by batching every run id (Intake + correlated Merchant Account) into one deduped `HashSet` and fetching concurrently via `futures::future::join_all`, confirmed PS doesn't serialize concurrent requests (measured directly, not assumed).
- Regression test: `app/(app)/clients/new/page.test.tsx`'s `"forwards each run's resolved Merchant Account run id to createClient"`.

## Phase 5 — Re-sync & scheduled sync: shipped, with a hybrid conflict-resolution design

Design aligned with Boris before coding (his own framing): re-doing the 18s PS fetch on every Create was excessive risk-for-cost, but PS data drifting between when a client is first added and when someone reopens the record days later is real and needs handling. Agreed shape:

1. **A background scheduled sync**, config on the Process Street integration page — `sync_interval_hours` (1-168, replacing an earlier fixed-daily-time design that was simplified away). Runs delta refreshes nobody has to trigger manually.
2. **A manual Re-sync button** on the Company page, for "I need this fresh right now."
3. **Hybrid conflict resolution** (Boris's call, catching a real risk in the original plan): once a field has been manually edited in OO, a naive re-sync could silently clobber that correction. Fields are tracked in a new `manually_edited_fields` (`TEXT[]`) column. Re-sync is two-phase — `preview_resync` classifies each changed field as a safe auto-apply or a conflict (touches a manually-edited field), `apply_resync` takes the caller's per-field resolution (overwrite from PS vs. keep the OO edit) for each flagged conflict. Implemented in `api::clients_resync` (`classify_company_diff`/`classify_facility_diff`/`effective_protected_fields`) and `clients::sync` (`apply_company_refresh`/`apply_facility_refresh`/`refreshed_field`).
4. `sync.rs`'s `refresh_matching_facility` has a real live test against actual Highway 20 data in the Neon dev branch — confirmed protected fields are actually skipped, not just asserted by code review.
5. **Known, accepted gap**: `apply_resync`'s SQL itself was never live-tested (unlike the scheduler's own refresh path) — it commits internally with no caller-supplied transaction to roll back, so a live test would permanently mutate the real shared dev DB. Deliberate decision, not an oversight.

## Activity Logs — new feature, not in the original plan

Introduced this session as a natural extension of an existing ask: OO already had Security Logs (`auth.auth_audit_logs`, login/auth events); Boris wanted a separate trail for *user actions* — including every sync run, which needed somewhere to log to anyway once scheduled sync existed.

- Existing Audit Logs renamed to **Security Logs** (`/admin/security-logs`, was `/admin/audit-logs`) to disambiguate from the new trail.
- New **Activity Logs** (`client_ops.audit_log`, `/admin/activity-logs`) — new nav item under Administration, gated on its own `activity_logs.read` permission (separate from `audit_logs.read`). Exportable to PDF and searchable, matching Security Logs' existing UX exactly.
- Captures sync outcomes (including PS API errors — sync failure is a real, handled case, not just the happy path) via `RunSyncOutcome` and `SYSTEM_USER_ID`/`SYSTEM_ROLE` constants for system-triggered (non-human) log rows.
- **Retention decision deliberately deferred** — flagged in [[Production Readiness Checklist]] since Activity Logs will be far higher-volume than Security Logs ever was.
- Test gap found and fixed during the later full-codebase pass: `client_ops::audit_log` had zero direct tests before this; added.

## Phase 4 items 1-3 — Client record UI (read-only pass)

Built after Boris asked to "revisit everything that's planned and put it in the order of execution" once the Tools tab existed but no actual client data did. Agreed order: (1) Company page sections, (2) facility rail + a facility's General tab, (3) Facility Policies tab — approved as a batch ("let's proceed with 1-3").

- **Backend**: `api::clients_detail` (new module) — `get_company_detail`, `get_facility_detail`, `get_facility_policies`. Any-authenticated-caller gate, same as search/preview; the genuinely sensitive parts (Elavon activity, owner PII) are protected by RLS itself (`facility_merchant_accounts`/`facility_merchant_account_parties` stay `onboarding_manager`/`department_manager`-only at the database level), so a lower-privileged caller just gets those fields back empty rather than needing a duplicated permission check.
- **Company page** (`/clients/[clientId]/info`): Company Information, Financial Information, Owner(s) Information (decrypted per-party PII, gracefully degrading per-row on a decrypt failure rather than failing the whole page), Re-sync button.
- **Facility page** (`/clients/[clientId]/facilities/[facilityId]`): General | Users | DropBox | Elavon | Facility Policies tabs — only General and Facility Policies actually built this pass; the other three are visible placeholders so the tab structure exists rather than being added piecemeal later.
- **Two known display gaps flagged at the time, one since fixed**: `ownership_type` and Elavon's own richer financial fields still aren't shown on the Company page (no persisted company→Merchant-Account-run link exists to read them from — real future work); separately, the 5 "Financial Information" fields (accepted payment methods, accounting basis, payment scheme, tenant-insurance offered + provider) were discovered to actually live on the **Intake** form, not Merchant Account as first assumed — corrected via `values_for()`, a new helper for PS's MultiChoice field type (`data.values`, plural array) that `value_for()` doesn't handle.
- **Full-codebase test-gap pass** (explicit ask: "check both front end and back end entire code base, identify gaps in auto-tests"): found and fixed real gaps beyond Activity Logs above — the new sync-refresh SQL was unverified (added the live Highway-20 test), `classify_company_diff`/`classify_facility_diff` had no direct tests, `ResyncButton.tsx` had zero tests (added 6, covering the hybrid conflict UI). Frontend went from no coverage on this surface to a real regression suite.

## 2026-09-03 — three follow-up fixes from real usage

Reported together after Boris actually used the built pages: Elavon data missing from the Company page, a page-blink on facility switching, and an ugly Dropbox link.

### 1. Elavon data was never being written — real bug, root-caused and fixed

Company page showed no Elavon data at all, for a client (Prairie/Highway 20) known to have real Merchant Account data. Root cause, confirmed by a direct `psql` query showing **0 rows** in both `facility_merchant_accounts` and `facility_merchant_account_parties` for Highway 20's facility id: the Merchant Account run id gets correlated during `preview_clients` (`clients_preview.rs`), but that correlation was silently dropped before `POST /clients` — `create_company_and_facilities` never received it, so `ingest_merchant_account_run`/`insert_party` (which already existed from Phase 1, just never had a real caller) were never invoked for anything created through the confirmation screen.

**Fix**: `PreviewedRun.merchant_account_run_id` and `CreateFacilitySelection.merchant_account_run_id` now carry the correlated run id end to end; `create_company_and_facilities` takes `facility_selections: &[(String, EditableFacilityFields, Option<String>)]` and, when a Merchant Account run id is present, fetches and ingests it in the same transaction as the facility itself. Migration `20260903120000_add_company_financial_info_fields` also landed the 5 Financial Information columns discovered to be missing from `clients.companies` during this same investigation.

### 2. Page "blink" on facility switching — real backend + frontend causes, both fixed

Boris: *"when switching from company to facility and then other facilities, the page 'blinks' while 'loading...'. Is there any way to smooth that out and speed it up? is this a DB call issue?"* — yes to both parts.

- **Backend**: `get_company_detail` was doing 4 sequential DB round trips inside one shared transaction (company row, facility list, Elavon-active check, owner parties), and `get_facility_policies` up to 7 (existence check + fees/taxes/delinquency/coverage/commission/specials). Against the real remote Neon Postgres (not local), each round trip is real latency, additive. Fixed by splitting each into its own short-lived RLS transaction and running them concurrently via `tokio::join!` — sqlx transactions can't be shared across concurrent queries, so each query now opens/commits its own. Existence checks that used to gate the later queries no longer do (a nonexistent id just makes every other query return empty, discarded on the 404 path anyway).
- **Frontend**: `/facilities/[facilityId]/page.tsx` was independently re-fetching `getCompanyDetail(clientId)` on every facility click, even though company/rail data doesn't change between facilities in the same company. New `CompanyDetailContext` (`components/clients/CompanyDetailContext.tsx`) fetches company detail once per `companyId` and is provided from the shared `[clientId]/layout.tsx`, consumed by both the Company page and the Facility page. The facility page's own loading state was also narrowed to just the tab content area (rail + chrome now stay mounted across a facility switch, rather than the whole page blanking to "Loading…").
- New test coverage: `components/clients/CompanyDetailContext.test.tsx` (5 tests — fetches once per companyId, doesn't refetch on an unrelated re-render, does refetch on a companyId change, surfaces a failed fetch, throws outside a provider).

### 3. Dropbox link → "Go to DropBox" button

Boris asked for two buttons: one to open a local Explorer window, one to open the Dropbox web folder in a new tab. Investigated and reported back before building: `dropbox_folder_url` is sourced from PS as a Dropbox **web** share link (`Facility_Onboarding_folder_URL:` on Intake), not a local filesystem path — there is no local path in this data for a browser to hand to Explorer, and no browser API can launch a desktop file manager from a webpage regardless (security sandboxing). Boris agreed to drop the Explorer button rather than ship a fragile best-effort guess. Shipped: a single "Go to DropBox" button using the existing `DropboxLogo` icon component (already built for the dedup tool's Source Files UI), opening `dropbox_folder_url` in a new tab, replacing the plain-text field that didn't wrap well.

## Verification, this session

Backend: `cargo build`, `cargo test` (475 passed), `cargo clippy --all-targets` (clean — the only warnings present are pre-existing, in unrelated `dropbox_browse.rs`, not touched here), `cargo build --release` (binary rebuilt, **needs a restart by Boris to pick up**).
Frontend: `tsc --noEmit`, `npm run lint` (clean), `vitest run` (364 passed), `npm run build` (production build succeeds).

## Related

- [[Implementation Plan]]
- [[Process Street Integration — Kickoff & Findings]]
- [[Client & Facility Schema (Process Street-Sourced)]]
- [[Production Readiness Checklist]]
- [[Gotchas]]
