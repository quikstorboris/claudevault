---
date: 2026-10-13
description: "Clients page filters were empty: Implementation Manager was never assigned (staff resolution never built) and Previous PMS read '3rd Party PMS' for every third-party facility. Fixed from the Intake answers; api 1.9.121 / ui 1.6.95."
tags: [work-note, unitprep, process-street, clients, session]
status: active
quarter: Q4-2026
project: unitprep
---

# Implementation Manager from the Intake conductor, and the specific Previous PMS (2026-10-13)

Boris, on the Clients list page: (1) the Implementation Manager dropdown had no options, and the manager should appear on the company page ("Implementation manager: John Doe", under the title row, above Company Information); (2) Previous PMS had almost no options (LG Squared is on SiteLink, selected in PS Intake, but it did not show).

## Root causes
1. **Never finished.** The Clients filter lists users *assigned* as manager. Nothing ever assigned one: `clients_filter_options.rs`'s own header said staff resolution was "a follow-up" and the planned `staff_resolution` module "was never built and has been removed". The pieces it needed existed (`implementation_manager_user_id` on `clients.companies`, `clients.staff_identity_alias`, `auth.staff_directory()`), unused. It was not a "no other users" problem.
2. **Wrong PS field.** Previous PMS was read from "What Property Management Software is this facility currently using?", whose answer for any third-party system is just `3rd Party PMS`. The product is in the follow-up "Which 3rd Party Software are they using?" (pick list: e.g. `Sitelink Web Edition`, or `Other`), with "What is the name of the 3rd Party Software they are using?" as the typed name for Other. The filter list is the distinct values in use, so there was nothing real to list.

## What was built
- `clients::staff_resolution`: the Intake step "Who is the Conductor" answers with `Conductor_Email_Address:`; that email is matched to the OO user (case-insensitive), `staff_identity_alias` first (the sanctioned redirect for a former employee: `imasse@quikstor.com` already maps to Boris), then the user directory. At client creation only, and never over a manager already set. No match = unassigned, never a guess.
- `intake_mapping::previous_pms`: the follow-up answer replaces the umbrella one; "Other" uses the typed name; an "Other" with no name falls back to "3rd Party PMS". The value is kept as PS spells it, so a new product shows up in the filter the first time a client uses it ("added to our OO list whenever a client is created" is this: the list has no table of its own).
- Company detail returns `implementation_manager` and the page shows it ("Not assigned" when none).
- Migration `20261013120000` backfills both from each row's stored `raw_ps_snapshot` (a hand-edited previous PMS is left alone). Neon dev result: 16 of 20 companies assigned (all to Boris, who is the only real conductor with an OO account); LG Squared now reads `Sitelink Web Edition`.

## Known limits and follow-ups
- **A conductor with no OO account is unassigned** (dev: `nsanchez`, `msanchez`, `opal` @quikstor.com; 4 companies). Creating the account does not retro-assign; run the migration's first UPDATE again, or add an alias row, or use the future reassign feature. The nightly sync does **not** re-resolve the manager (refresh works on `MappedCompany`, which does not carry the conductor); a conductor changed in PS afterwards is not picked up. Deliberate: a person may have reassigned it.
- **Sales Rep** (PS "Fill in Rep Only fields", a *name*, not an email) is still not assigned. Same mechanism would work with a name match against the alias table; not done.
- **Typed-name inconsistency in PS data:** the same product appears as `Sentinel Winsen` (2) and `Winsen Sentinel` (1). They are separate filter options until someone normalizes the PS answers (or a small alias/normalization table is added; not built).
- Prod needs `scripts/prod_db_status.sh` then `prod_db_sync.sh` (Boris): migrations `20261009120000` (ClickUp steps) and `20261013120000`.

Related: [[Process Street Integration — Kickoff & Findings]], [[Client & Facility Schema (Process Street-Sourced)]].
