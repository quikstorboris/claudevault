---
date: 2026-08-28
description: "OO's client/facility creation redesigned to source from Process Street instead of manual entry: confirmed read-only API access to Intake/Progress, New Merchant Account, and Contract Order workflows, and the 'sister site' data-sharing mechanism across multi-facility companies."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Process Street Integration — Kickoff & Findings

New effort as of 2026-08-28, superseding the "manual-entry-first" plan for Company/Facility/Contact data described in [[Platform Vision (Onboarding Orchestrator)]]'s Step 2. That note's own config-template list flagged Process.st as "optional, ultra-low-priority... unconfirmed, unexplored" — it is now confirmed, working, and the primary intended source for this data. Continues the build order agreed in [[Onboarding Orchestrator Kickoff — Session Log]] (Step 2: Client/Facility/Contacts schema).

## Why this changed the plan

Boris already has a real Process Street (PS) API key. The onboarding team's actual client/facility data — corporate info, facility details, fees/tax/DLQ/coverage config, owner/manager contacts, and Elavon merchant account status — already lives there, entered through three workflows the onboarding team runs for every client. Sourcing OO's client records from PS directly, instead of the current placeholder manual form, also lets OO drive "add client" off real structured data instead of ad hoc entry.

## Access confirmed (read-only)

**PS access must stay read-only** — GET only, no writes, standing constraint until Boris says otherwise. This is a live ops system the onboarding team depends on daily; there must be no risk of mutating PS data while OO is being built out.

- Base: `https://public-api.process.st/api/v1.1`, `X-API-KEY` header auth.
- `/workflows`, `/workflow-runs?workflowId=...` — both paginate via a `links[].name=="next"` cursor, not an offset; the `limit` query param is accepted but appears to be ignored on `/workflow-runs/{id}/tasks` and `/workflow-runs/{id}/form-fields` (always ~20/page regardless), so those two always need the cursor-following loop.
- `/workflow-runs/{id}/tasks` → step name + `status` (`Completed`/`NotCompleted`) — the "is this step done in PS" signal for OO's UI.
- `/workflow-runs/{id}/form-fields` → `label`/`key`/`value`/`fieldType` per field, tied to `taskId`. Unanswered fields return `data: null` — must be handled defensively, not assumed present.

## The three workflows

1. **🚂 Intake / Progress** (`tRh93HgRC5OLom3UxhJD3w`) — one run per facility. Corporate info, facility details, fees/tax/DLQ/coverage, subdomain/email setup, Dropbox folder link, and the Owner/District-Manager/Manager contact fields all live here.
2. **💳 New Merchant Account** (`rhUaJ-KRu0ejEOYQ-jxGMA`) — one run per facility. **Confirmed always 1:1 with a facility** (Boris). Rate provided, credit card application review/status, QMS credential status.
3. **✅ Contract Order** (`j_idx2uXcI0_6gs4XvZGBA`) — ignore the duplicate old template `Contract Order (OLD WAY 01/29/25)`. **Confirmed by Boris: its absence for a given facility is inconsistent sales-territory/process behavior, not a data gap to chase.** When it does exist, the field that matters is which legacy system the client is migrating off of onto QMS — that's the whole reason this workflow is worth having in OO at all. **Mapping shipped 2026-08-31** using real data Boris pointed at directly (Tri County Mini Storage, Dubuqueland Mini Storage) — finding it surfaced a real bug: `GET /workflow-runs` defaults to `status=Active` only, and Contract Order runs are marked `Completed` once processed, so the original search found neither client until `status=Completed`/`Archived` were queried explicitly. Fixed in `ProcessStreetClient::list_workflow_runs`; see [[Gotchas#Process Street's `GET /workflow-runs` defaults to `status=Active` only — silently hides most real data|the vault Gotchas entry]].

## Critical finding: the "sister site" sharing mechanism

> [!danger] High-importance — do not lose this before Phase II
> Full writeup in [[Gotchas#Process Street's "sister site" sharing has no definitive link between facilities — do not assume the "first-time" facility is always resolvable]]. Deferred to Phase II per Boris, but the open question there (a "No" facility overriding just one category) must be resolved before the sharing model in [[Client & Facility Schema (Process Street-Sourced)]] is trusted as complete.

Confirmed via Prairie Enterprises' 3 real facilities (Highway 20, Carpentersville, Pyott Road): a field `"Is this their first time filling out this form?"` gates whether Corporate Info / Sales+Rent Tax / DLQ+Late-Fee schedule / Lien fees / Commission % / Coverage tiers are filled in **on that facility's own PS run at all**. Highway 20 answered "Yes" and has full real data in all those categories; Carpentersville and Pyott Road both answered "No" and have `null` in every one of those same fields on their own runs — **PS does not duplicate this data onto the "No" facilities**, and stores no field linking a "No" facility to its actual sister. It's tribal knowledge only a human onboarding rep holds.

**Exception, confirmed independently**: the "Owner Level Users" / "District Manager Level Users" / "Manager Level Users" free-text fields (format: `Name, email, phone` per line) ARE copy-pasted verbatim onto every facility's own run regardless of the first-time flag (byte-identical text confirmed across 2 Beau Ryan facilities). This makes sense — different people can manage different facilities under one company, so this data doesn't have a single "sister" source the way fees/tax/DLQ/coverage do. Needs regex parsing (not a clean structured multi-value field), and should be deduped by email across facilities — see [[Client & Facility Schema (Process Street-Sourced)]]'s People section. Worth noting: deduping these person records across facilities/workflows is the same shape of problem [[Dedup Tool Index|UnitPrep's own dedup tool]] already solves for tenant contacts.

## Design decisions agreed with Boris (2026-08-28)

- **Persistence**: cache PS data into OO's own DB on import (`last_synced_at` + manual/scheduled re-sync), not live-query PS on every page load — needed so OO's own dedup tooling and any OO-side annotations survive a re-sync.
- **Grain**: model Facilities/Fees/Tax/DLQ/Coverage at the facility level, matching PS's native structure. No shared-vs-local toggle in the UI — see [[Client & Facility Schema (Process Street-Sourced)]] for how the sister-site sharing is modeled as one shared row instead.
- **People**: modeled at the facility-assignment grain (matches how PS actually captures it — no artificial company-level table needed), deduped by email across the Intake Form's Owner/DM/Manager fields AND the Merchant Account signer fields.
- **Elavon tab**: always 1:1 with facility (confirmed by Boris) — lives directly on the facility record, no separate linking table.
- **Owner vs. Signer roles**: kept as distinct role tags, not merged — a person can hold both via two rows (same person, two roles) when they really are both; a bookkeeper who is signer-only with no ownership stake just gets the one role.
- **Dedicated `clients` schema, confirmed** — briefly reconsidered mid-implementation (almost folded into the existing `client_ops` schema, which turned out to be the wrong call for real reasons: that schema is tool-support/reference data, not the clients themselves, and would need carving apart later once "Groups" client-scoped visibility ever gets built). Migration + RLS shipped 2026-08-28, see [[Client & Facility Schema (Process Street-Sourced)]].
- Target OO client record UI: tabs for **Corporate | Facilities | Users | DropBox (customizable link) | Elavon | Facility Policies** (Fees/Delinquency/Commission/Coverage sub-tabs — see [[Client & Facility Schema (Process Street-Sourced)]] for the naming discussion).
- Planned entry point: a search interface on the Clients page — search by corporate name, facility name, or a person's name (owner/DM/manager/signer) — then "add" to create the OO record from the matched PS data.

## Related

- [[Platform Vision (Onboarding Orchestrator)]]
- [[Onboarding Orchestrator Kickoff — Session Log]]
- [[Client & Facility Schema (Process Street-Sourced)]]
- [[Implementation Plan]]
- [[Auth & RLS Security Audit — 2026-08-28]]
- [[Orchestrator Feature Backlog]]
- [[Dedup Tool Index]]
