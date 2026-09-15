---
date: 2026-09-08
description: "Reconstructed from commit history (session not live-captured): Taxes/Delinquency moved from free-text to structured data, the Users tab got source tracking/manual-add/full editing, the DropBox tab was built for real, and the facility page was widened. Precedes and sets up the same-day Dubuqueland bug hunt."
tags: [work-note, unitprep, process-street, reconstructed]
status: active
quarter: Q3-2026
project: unitprep
---

> [!note] Reconstructed, not live-captured
> This note was written 2026-09-15 from `unitprep-api`/`unitprep-ui` commit history (`b8df8f8`/`54a7cf1`, `1bfb00f`/`bd59dc9`, `e413ae2`/`559db58`, `955e8c9`) — no session transcript exists for this block of work. Content below is what the commits themselves document; treat anything not directly attributable to a commit message as **(inferred)**. [[Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap|The same day's afternoon session]] explicitly flagged this gap: "Phase 4 item 4 (Users tab) is now live... built in a session not captured in this note's own context."

## Structured Taxes/Delinquency (`b8df8f8` / `54a7cf1`)

Both tabs moved off free-text onto real structured tables:

- **Taxes** (`clients.policy_tax_entries`) — one row per tax: name (Sales/Rental), description, flat dollar amount, attribute payable percent, recurring flag. Only `tax_type = "fixed"` has real fields wired up; `marginal`/`percentage` are accepted by the schema's own CHECK constraint but deliberately deferred (Boris's own call, 2026-09-08).
- **Delinquency** (`clients.policy_delinquency_entries`) — a required dollar amount (0 allowed), an optional days-after count, and a real trigger: either the facility's own Paid Through Date, or another entry on the same schedule referenced by **category** (not row id — a schedule can't reasonably have two Pre-Lien rows, and category survives reordering a row id wouldn't). Covers "everything up to Lien keys off PTD, Lien itself keys off Pre-Lien" directly. A CHECK constraint enforces `trigger_category` is set iff `trigger_type = step_category`.
- **Old tables not dropped or auto-migrated** — Highway 20 Self Storage has real historical data in both (1 tax row, 9 delinquency rows, one of which names two separate fees in the same free-text value) and turning that prose into structured fields needs a human's judgment call, not a parser. Both old tables still come back from `get_facility_policies` as read-only history, and both tabs show that legacy data alongside the new structured entries when a facility has it.
- Frontend: Taxes edit row later resized the same day (`955e8c9`) — Description gets `flex-[3]` with a real minimum width (it's a name like "Parking Space County Tax", not a code), Flat Price/Attribute Payable shrink to `w-24` since they're just numbers.

## Users tab rebuild: source tracking, manual add, full editing (`1bfb00f` / `bd59dc9`)

`clients.facility_people` gained a `source` column (`process_street` | `manual`). A manually-added person is **permanently exempt** from the Users tab's own self-heal pass — this is the "add a user that will never be overwritten by re-sync" capability Boris asked for the same day. Every roster row became directly editable (name/email/phone/role); editing a `process_street`-sourced person shows a `protect_from_resync` checkbox that flips their `source` to `manual` when checked, so the edit survives the next self-heal instead of silently reverting.

New `repository::edit_person_and_facility_link` handles the name/role change plus the source decision together — proven against real Postgres both directions (protected vs. unprotected edit). Frontend: new "+ Add Person Manually" form, an Edit button per row, a Source column (Process Street / Manual, excluded from Copy All).

**Same-day follow-up gotcha this fed into**: the Users-tab candidate-matching logic this rebuild depends on was still email+role-only at this point — [[Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap]]'s person-identity bug (two distinct family members sharing one inbox collapsing into one row) was found and fixed later the same afternoon, directly downstream of this morning's work going live.

## DropBox tab built for real (`e413ae2` / `559db58`)

Replaced the placeholder. `PUT /clients/{company_id}/facilities/{facility_id}/dropbox-folder` lets a manager relink a facility to a different Dropbox folder (or clear it) — audit-logged (`facility_dropbox_folder_changed`), same treatment as a Merchant Account relink. Marks `dropbox_folder_url` into `manually_edited_fields` so the existing scalar-field re-sync protection (`clients::sync::apply_facility_refresh`) already covers it, no new protection mechanism needed. Frontend shows "Go to DropBox" + Change Folder when linked, "Link a Folder" as the primary action when not — reuses the same `DropboxFolderPicker` every other Dropbox-import flow already uses; the Company page's own launchpad links are untouched.

## Also same morning (`955e8c9`)

Facility page content area widened `max-w-5xl` → `max-w-6xl` (the whole tab area was cramped), and Copy All on the Users tab started grouping the roster under Owner(s)/District Manager(s)/Manager(s) headings (skipping any role the facility has none of) instead of one flat list.

## Related

[[Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap]] — same-day continuation, live bug hunt against the Users tab this session shipped.
[[Implementation Plan]] — phase tracking this work counts against.
