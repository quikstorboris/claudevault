---
date: 2026-08-28
description: "Phased build order for the OO x Process Street integration: schema/RLS, a fixture-tested PS ingestion pipeline, a two-tier sync (cheap search index vs. expensive full import), the client record UI, re-sync, dedup, and permissions."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Process Street Integration — Implementation Plan

High-level build order for [[Process Street Integration — Kickoff & Findings]] and [[Client & Facility Schema (Process Street-Sourced)]]. Nothing built yet — this sequences the work, following the same "validate each layer before generalizing" discipline already established for Onboarding Orchestrator in [[Platform Vision (Onboarding Orchestrator)]].

## Two things this plan surfaces that weren't decided yet

**1. Search needs its own cheap sync tier, separate from the full import.** PS's API can list workflow-runs by name, but it cannot search *inside* form-field values — finding a facility by an owner/manager's name means fetching `/form-fields` for every candidate run, which is too expensive to do live per keystroke. So "search the Clients page for a PS facility by owner/DM/manager name" needs a lightweight background sync that pulls just names/emails/ids from every run across all three workflows into a small lookup table, refreshed periodically — independent from and much cheaper than the full per-field import in Phase 2. Corporate/facility-name search doesn't have this problem (workflow-run names ARE searchable directly), only person-name search does.

**2. Re-sync can clobber OO-side manual edits, symmetric to the "Same for each facility" risk already designed for.** Once Delinquency (and possibly other tabs) become OO-editable per Boris's stated intent, a naive "re-sync from PS" has the same destructive-overwrite shape as the copy action — needs the same warn-and-confirm treatment, or a smarter merge (only overwrite fields that haven't been touched in OO). Not resolved here, flagged for whichever phase implements re-sync.

## Phase 0-2 — Foundations, Ingestion Pipeline & Search — **shipped 2026-08-28 through 2026-08-31**

Schema/RLS, the field-mapping/encryption/repository ingestion pipeline (including Contract Order mapping), and facility-name search. Full build detail moved to [[Phase 0-2 — Foundations, Ingestion Pipeline & Search]] once this note crossed the vault's organization-size threshold. Person-name search (Phase 2's other half) is still not built.

## Phase 3 — "Add to OO" flow — **shipped 2026-09-02** (backend foundation 2026-08-31, confirmation screen + Create-latency fix 2026-09-02)

Full design conversation, not just the stub below — captured here since this is where Phase 3 actually gets built from. Live-build detail (the confirmation screen itself, the Create-latency fix) is in [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]].

> [!warning] Correction, 2026-09-02 — Company vs. Facility is NOT an either/or
> The "Company vs. Facility is a real either/or per row" design below (agreed 2026-08-31) was wrong and has been reversed. **Company is its own section, and every selected run also becomes its own Facility record** — a run can seed the Company section's data AND be a real facility at the same time (Highway 20 is both, for Prairie Enterprises). See the correction writeup for the full reasoning.

**Shipped** (`unitprep-api` `v1.8.21`, 5 commits `731c4cd..1bce4c8`, committed, not yet pushed to `origin/main`): facility search narrowed to Intake runs only, `already_imported` flagging per match, `clients::company_naming::resolve_company_name`, `clients::repository` split into reusable `insert_company`/`insert_facility`/`insert_facility_policies_and_people` building blocks, and `clients::create::create_company_and_facilities` — the real trigger, `POST /clients`, gated on `client_ops.perform`. Proven against the real live API and Postgres: creating a company with zero facilities, and refusing to recreate an already-imported run, both rolled back. 401 tests passing, clippy clean.

**The company-naming rule, exactly**: New Merchant Account's Facility Information (Pre-App) step has three real fields now mapped — `Legal_Name_2` (real value seen: `"Prairie Enterprises LLC"`), `Business_DBA` (real value: `"Highway 20 self storage"`), `Ownership_Type` (real value seen so far: just `"LLC"` — matched case-insensitively against "sole prop" since the real sole-proprietor enum value hasn't been observed yet). Preference order: `Legal_Name_2` when a Merchant Account run exists at all (it asks more carefully than Intake does) → Intake's own legal name when no Merchant Account run exists → for a sole proprietor specifically, **`"<Owner's First Last> DBA <Business_DBA>"`** instead of `Legal_Name_2` (Boris, 2026-08-31: small/sole-prop clients often don't have a distinct company legal name from PS's own perspective, so this constructs one worth showing). **Not yet wired to real Merchant Account data anywhere** — the matching flow below (finding the right Merchant Account run for a facility) doesn't exist yet, so every real call site currently passes `merchant_account: None` and gets Intake's legal name, same as before this rule existed.

**Not yet built**: the confirmation-screen frontend itself (pencil-edit fields, the Company/Facility toggle UI, greyed-out already-imported rows, inline add-more search), and the Merchant Account matching+confirm-link flow described below.

**Search scope narrowed**: facility-name search now only searches **Intake** runs (Boris, 2026-08-31) — Merchant Account existing or not is a fact about the facility, not something reliable to search by (not every client uses Elavon).

**Confirmation screen, not a direct write**: selecting facility matches and hitting "Add"/"Next" lands on a review screen before anything is written to Postgres.
- Every field shown starts as read-only text with a pencil icon; clicking it turns that one field into an editable input. Applies broadly (see the global edit-button convention below), not just to legal name/facility name (the two examples Boris gave first).
- **Company is its own section, not a role a row switches into (corrected 2026-09-02, superseding the original either/or design)**: Company gets one section on the confirmation screen, seeded from whichever selected run has the fullest resolved company data (`pickCompanySourceRun`). Every selected run — including the one that seeds Company — also becomes its own real `clients.facilities` row. Nothing at the schema or handler level requires excluding a company's source run from also being a facility; Boris's own real Prairie Enterprises case needs it this way (Highway 20 carries the corporate data *and* is itself a real, separate facility). At most one run seeds the Company section per batch.
- **One company per Add action** — a batch spanning more than one real company is considered unlikely (real client folders in Dropbox are usually organized this way) and out of scope for v1.
- **Adding a facility to a company that already exists in OO** (not part of this batch): run another search and pull it in that way — no separate "attach to existing company" picker planned for v1.
- **Greyed-out already-imported facilities**: search results should flag (and grey out) any Intake run whose `ps_intake_run_id` already has a `clients.facilities` row, so a manager searching to add more facilities to an existing company can see at a glance which ones are already in OO. Nice-to-have, not a hard blocker if it turns out to be awkward to implement.
- **"Add more facilities" inline on the confirmation screen**: another company/facility-name search, embedded in the same screen, appending to the current batch rather than starting over. Considered unlikely to be needed often, but nice to have.
- **Duplicate-add protection**: check `ps_intake_run_id` uniqueness before the real write, block/warn instead of silently creating a duplicate facility. Confirmed: build this.
- **Land on the Company page** after a successful create, not a facility page — Company is the new main page (see Phase 4 below).

**Elavon (New Merchant Account) matching — the hard part, designed 2026-08-31**: PS has *no* programmatic link between an Intake run and a Merchant Account run for the same real facility — confirmed, not assumed; the only earlier signal (two very differently-worded titles for the same real Highway 20) was purely a human reading two titles side by side. Name-only fuzzy matching isn't good enough on its own (Boris's explicit call). Planned approach:
1. Once a facility is confirmed/created from its Intake data, score candidate Merchant Account runs against that facility's now-known data — shared owner email (already parsed as structured people via `people::parse_people_block`, not just free text), shared facility address/phone, name similarity, etc. No new capture needed — Intake mapping already has all of these fields.
2. If a strong candidate surfaces, show it as **"New Merchant Account Flow Found: `<Flow Name>`"** where the flow name is a real, clickable link (to the underlying PS run) — the user must click through and look at it before the "confirm this link" action becomes available. Deliberate friction: never let an algorithmic match get silently accepted.
3. No candidate found (or user declines) → facility just has no Merchant Account attached yet; can be linked manually later from the Facility page's own Elavon tab.
- **Contract Order is out of scope for this phase entirely** — lowest priority, picked up only once Intake/company-facility creation and the Merchant Account matching flow are both built and working.

**A data-quality reality to design for, not solve yet**: some real clients don't understand or maintain the company/business vs. facility/location distinction at all — to them, everything is one location, and Intake forms get filled out accordingly ("half-assed" per Boris). The business/location separation should still exist in every case (see the global edit-button convention below for how a manager cleans this up after the fact), but expect friction here specifically for single-facility companies where the two names end up identical or the corporate fields are sparse/wrong. Not a blocker for building the rest of Phase 3 — just something to keep in mind rather than assume clean data.

## Phase 4 — Client record UI — **items 1-3, 4, 5 shipped (Company page, facility rail + General tab, Facility Policies tab, Users tab, Elavon tab), read-only pass except Users; items 6, 7 (DropBox connection flow, ps_task_status indicators) not yet built**

Build-order and live-build detail are in [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]] (items 1-3, shipped 2026-09-02) and [[Session 2026-09-03 — Live Testing Fixes, Transaction Leaks & Field Reference Help]] (item 5/Elavon tab, real bugs found from live usage, plus a new Field Reference help table not in the original plan at all -- a searchable "which PS field does this OO field come from" reference, both shipped 2026-09-03).

> [!note] Item 4 (Users tab) build session not captured in this plan
> First observed live and in active use 2026-09-08 — **(TBC)** exactly which session built it, since that isn't in this note's own tracked history. That session's own real bugs (a person-identity model that silently collapsed distinct people sharing one email, plus a roster-remove action added) are in [[Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap]].

**Company page is the main page — no tabs.** Sections/boxes instead:
- **Company Information**: address, phone, email.
- **Financial Information**: Elavon yes/no (does a Merchant Account exist for this company at all), Ownership Type (enum, from New Merchant Account > Pre-App > Ownership Type), accounting basis, payment scheme, accepted payment methods, insurance offered.
- **Owner(s) information** (contact, percent ownership, unmasked SSN, unmasked DOB) — Company-page-only, sourced from whichever one of the company's facilities has `facility_merchant_account_parties` data (only one usually does), never repeated per facility. No new schema needed for this — a read-time query across the company's facilities, not a new company-level table.
- Company name preference: New Merchant Account > Facility Information (Pre-App) > Legal Name when it exists; falls back to Intake > Corporate/Facility Info > Facility Name when there's no Elavon application at all.
- Between these sections and the left nav: a facility-selector rail (buttons, one per facility) plus one button above them all to return to Company View — same rail pattern already designed for Facility Policies, just extended to the whole company/facility page structure.

**Facility page tabs**: **General | Users | DropBox | Elavon | Facility Policies** (Corporate dropped — that's now Company-page-only).
- **General**: facility contact info (address/phone/email/units/subdomain) plus, per the Dropbox redesign below, the facility's own Dropbox subfolder picker.
- **Elavon**: per-facility, since real Elavon applications and eventual API credentials are genuinely per-facility (`facility_merchant_accounts.encrypted_secrets` already models this — QMS password, QSS web PIN, pinpad user id, QSS API pin, MID, account id — schema already shipped, just needs a UI). Elavon credentials are the one thing that stays **non-editable** — see the global edit convention below.
- **Facility Policies**: unchanged from the original design — Fees | Taxes | Delinquency | Coverage | Specials sub-tabs, the facility-selector rail, the per-tab "Same for each facility" copy action.

**Dropbox, redesigned 2026-08-31**: no longer picked at client-creation time (removed from the quick-create form, `unitprep-ui` `v1.5.10`). Connected once on the Company page; each facility then picks its own subfolder from that root on its own General tab. Real client folders vary a lot in cleanliness (Prairie's should be obvious; something like Absolute Management's likely won't be) — so facility folder selection must default to starting inside the company's root, but still allow picking any folder manually, not just an auto-suggested match.

**Global edit convention, applies to every page/tab built from here on**: everything is editable **except Elavon credentials** — but nothing renders as an input field by default. Each main section (below the tabs, one per company/facility page) shows read-only text with an "Edit" button top-right of that section; clicking it reveals the actual input fields for that section only. This exists because re-synced PS data won't always be clean (see the data-quality note above) and a manager needs a real way to fix it without every page looking like a giant form by default.

- Copy-to-clipboard button on every raw-text value (unchanged from original design).
- `ps_task_status` surfaced as "done in PS" indicators against the step lists in [[Process Street Integration — Kickoff & Findings]] (unchanged).

## Phase 5 — Re-sync & maintenance — **shipped 2026-09-02, hybrid conflict resolution**

- Manual "re-sync from PS" per client/facility, plus a configurable background scheduled sync (`sync_interval_hours`, 1-168) — both shipped. The clobber-risk question above is resolved via a two-phase preview/apply flow with per-field conflict resolution when a manually-edited OO field would be overwritten; a new `manually_edited_fields` column tracks which fields to protect. Full design and implementation detail in [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]].
- **New, not originally planned**: shipped alongside re-sync, an Activity Logs feature (`client_ops.audit_log`, `/admin/activity-logs`) captures every sync run plus other user actions — separate from and renamed apart from the existing Security Logs. See the same session note.
- `ps_task_status` still not on its own lighter sync cadence — still Phase 4 item 7, not yet built.

## Phase 6 — People dedup

- Wire `facility_people` ingestion to reuse/adapt [[Dedup Tool Index|the existing dedup tool's]] matching logic — email-first, name+phone fallback triage — rather than building a second, parallel dedup approach for the same shape of problem.

## Phase 7 — Permissions

- Decide who can trigger import, re-sync, and especially the destructive "Same for each facility" action against the existing `admin`/`onboarding_manager` roles rather than inventing a new one ad hoc.
- **Integrations nav/settings access (Process Street + Dropbox) — decided and shipped 2026-09-09**: a new `integrations.manage` permission, admin-only. See [[Session 2026-09-09 — Admin-Only Integrations Nav, integrations.manage Permission, and Editable Dropbox Settings]] for the full reasoning, including the real behavior change (onboarding_manager/department_manager lose the Process Street settings access they had before).

## Testing expectations, carried over from this codebase's existing standards

- Backend: fixture-based PS client tests (no live calls in CI), migration tests, RLS tests matching the `auth` schema's existing test pattern.
- Frontend: component tests for the tab/facility-selector interaction, and specifically for the "Same for each facility" confirm-dialog flow — destructive, overwrite-everything actions have historically been where this codebase's real bugs hide (see [[Gotchas]]), so this deserves real coverage, not just a happy-path click-through.
- Manual verification: Prairie Enterprises / Highway 20 end-to-end is the natural golden-path walkthrough, since its data is already fully known from this session.

## Related

- [[Process Street Integration — Kickoff & Findings]]
- [[Client & Facility Schema (Process Street-Sourced)]]
- [[Onboarding Orchestrator Kickoff — Session Log]]
- [[Session 2026-09-09 — Admin-Only Integrations Nav, integrations.manage Permission, and Editable Dropbox Settings]]
- [[Phase 0-2 — Foundations, Ingestion Pipeline & Search]]
- [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]]
- [[Session 2026-09-03 — Live Testing Fixes, Transaction Leaks & Field Reference Help]]
- [[Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap]]
- [[Production Readiness Checklist]]
- [[Dedup Tool Index]]
