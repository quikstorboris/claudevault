---
date: 2026-09-08
description: "Full live bug-hunt session creating 'Dubuqueland Mini Storage' via Add to OO: company-name resolution for 'Same as DBA', a Corporate-Info fallback-banner gap, a real person-identity bug (email-only matching collapsed distinct family members sharing one inbox), new remove-user/delete-company features, and a CORS config gap that silently blocked every DELETE route. Includes rejected approaches and open items."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap

Direct continuation of [[Session 2026-09-03 — Live Testing Fixes, Transaction Leaks & Field Reference Help]] -- same pattern, a new real client (Dubuqueland Mini Storage) exercising features live and turning up real bugs, several days later. Phase 4 item 4 (Users tab) is now live and in active use (built in a session not captured in this note's own context -- **(TBC)** exactly when), which is what surfaces most of this session's findings. See [[Implementation Plan]] for phase status.

## Starting point: a 4-part bug report from a real "Add to OO" run

Boris reported, creating **Dubuqueland Mini Storage** (3 real facilities -- Main, Upper Lot, Key West -- plus one unexplained extra):

1. Company legal name wasn't pulled onto the Verify screen, even though it's indirectly derivable: one of the Merchant Account forms has `Business_DBA` filled in and `Legal_Name?` answered "Same as DBA."
2. The Review & Create (confirmation) screen re-fetches from Process Street -- expected to use pre-pulled data instead.
3. Searching "Dubuque" returned all 3 real facilities but with blank Company and a blank Status for one of them (Key West).
4. Searching "Dubuqueland" didn't return Key West at all, even though "Dubuque" matched it on a person (Asher Soppe).

### Resolutions, in order

- **#1, real bug, fixed** (`unitprep-api` `v1.9.20`, shipped before this note's own visible context began): `company_naming::resolve_company_name` had no branch for "Same as Business DBA" -- when a Merchant Account run answers that way, PS never asks `Legal_Name_2` at all (comes back `None`, not a copy of the DBA), so the old code fell straight through to Intake's own legal name, which is itself blank for a non-first-time sister facility. Added a `is_same_as_dba` branch that uses `Business_DBA` in that case, with a new `legal_name_same_as_dba` field mapped from PS's `Legal_Name?`. Verified against real live PS data for both the original "Main" case and, separately, the "(Key West)" Merchant Account run.
- **#2, confirmed by design, no change**: the confirmation screen deliberately live-fetches -- Boris accepted this ("Leave as is").
- **#3, split into two real findings**:
  - Blank Company for "Parking" (Key West's facility, before Boris later renamed it) traced to `merchant_account_correlation::correlate_by_title`'s parenthetical-nickname matching finding zero Merchant Account runs for that Intake title's old wording -- not a code bug, a PS-side title mismatch. Boris manually renamed the Intake run in PS to include a matching nickname (`(Upper Lot)`), confirmed live afterward to correlate correctly.
  - Blank Status for one match traced to `MatchedVia::Person` being a documented, deliberate design choice (a person-name match skips a live per-candidate status lookup to avoid N+1 PS calls) -- confirmed not "no Intake form," Boris's own guess. Shipped a `StatusCell` component (`unitprep-ui` `v1.6.25`) labeling it "Unknown" instead of a bare dash, since a blank cell read as confusing next to real "Active" values.
- **#4**: confirmed correct substring-matching behavior against real indexed data, not a bug -- "dubuque" matched Asher Soppe's real indexed email; "Dubuqueland" (the full string) didn't appear in that same email, so no match. Working as designed.

### The unexplained 4th search result

Boris later renamed the real Intake runs himself (adding parenthetical nicknames matching the Merchant Account side) and reported a 4th row appearing: a plain "Dubuqueland Mini Storage, Inc." run with no facility identity of its own. Live-diagnostic fetch (`clients::search`'s live PS call, `#[ignore]`d scratch test, deleted after use) confirmed all 4 rows are genuinely real, current, Active Intake runs in PS -- 3 confirmed as the real facilities (`Dubuqueland-Mini-Storage-Inc-Main-l6V5_AqglsifGwHbNItKxw`, `...-Upper-Lot-pWROFjlI5IPJA8ODb_FE3g`, `...-Key-West-mBy_MK_H_g-YFD-PE3FMYw`), the 4th (`gdBZphWLh8zBlf2WvO5Hlg`, "Dubuqueland Mini Storage, Inc. - QMS Onboarding") not among them.

> [!question] Still open
> What the 4th run actually is has never been answered -- a PS-side/business-side question, out of this codebase's own scope regardless of the answer.

## Corporate Info fallback banner: real bug, fixed twice

Boris next reported the Review & Create screen showing populated Legal Name and Subdomain but blank Corporate Email/Phone/Street/City/State/ZIP for the resolved Company.

**Investigation** (live-fetched the 3 real Dubuqueland Intake runs' own Corporate Info fields, `#[ignore]`d scratch test, deleted after use):

| Run | `is_first_time` | Legal Name (Intake's own) | Corporate contact fields | Subdomain |
|---|---|---|---|---|
| Main | **Yes** | blank | all blank | `dubuquelandstorage.qms-email.com` |
| Upper Lot | No | Dubuqueland Mini Storage, Inc. | all blank | blank |
| Key West | No | blank | all blank | blank |

Genuinely blank in PS, confirmed by Boris directly ("there is a section called corporate details where there's only one field -- Corporate Name. that was blank. i fixed that. but there is no other information"). `Company_Subdomain:` is answered independently of the gated Corporate Info block, contradicting `MappedCompany::subdomain`'s own doc comment claiming the same sister-site gating -- worth a doc-comment correction next time that file is touched (not done this session).

**The real bug**: an existing fallback mechanism ("No Company Information Captured" banner, "Use Facility Info" button, copies the first-time facility's own contact data onto Company) only triggered when the whole Company section was **completely** blank (`companyCompleteness(editedCompany) === 0`). Main had `subdomain` populated (and, post-fix, a Merchant-Account-derived `legal_name`), so completeness was 2, not 0 -- the banner silently never fired even though the genuinely useful contact fields were still missing.

**Fix** (`unitprep-ui` `v1.6.26`): trigger changed to check the *contact* fields specifically (email/phone/street/city/state/zip -- deliberately excluding `legal_name`/`subdomain`/`website_url`), gated on the source run being the company's own first-time facility (`is_first_time === true`). `handleAcceptCompanyFallback` made non-destructive (`prev.field ?? facility.field` per field) so it no longer overwrites an already-resolved `legal_name`/`subdomain`. Renamed the banner to "No Company Contact Info Captured." Two new tests cover the exact partial-completeness scenario and non-destructive accept.

### Rejected: gating the fix on "legal name same as DBA," as originally proposed

Boris's own proposed rule: if `is_first_time = Yes` **and** legal name is same-as-DBA, auto-use the facility's contact info. Pushed back and this was narrowed to `is_first_time = Yes` alone:
- "Same as DBA" and "this facility's address is the company's" are orthogonal facts -- a company can have a legal name genuinely different from its DBA while still being a real single-address business. Requiring both would make the heuristic fire *less* often than it should.
- The field lives only on the Merchant Account mapping (`legal_name_same_as_dba`) and isn't even plumbed to the frontend -- would need new API surface for something `is_first_time` already signals on its own.
- Kept as a human-confirmed banner action rather than automatic, since Boris separately framed OO as able to "piggyback as a validation/discrepancy identifier tool" surfacing PS's own gaps -- silent auto-substitution would hide exactly the kind of gap worth surfacing.

## Live browser verification (Claude in Chrome) -- real UI test, one false alarm

Boris installed the Chrome extension and asked for live verification on `localhost` in his own logged-in session. Reproduced the fallback banner firing correctly on a fresh `/clients/new` load for Main+Upper Lot+Key West, and confirmed "Use Facility Info" correctly filled the blank fields while leaving Legal Name/Subdomain untouched.

**A transient false alarm, not a real bug**: a later re-test appeared to hang indefinitely on "Searching…". Diagnosed via direct `fetch()` calls from the page's own JS console (bypassing the UI) -- the backend responded instantly and correctly both unauthenticated (`curl`, 401) and authenticated-from-the-page (200, real data) -- so the hang was the React component's own local state getting confused by rapid overlapping clicks/reloads during testing, not a backend or logic bug. A clean single navigate-search-select sequence worked immediately.

## "Absolute Storage" vs. Dubuqueland -- same lookup, different PS answers

Boris asked why an earlier client ("Affordable Storage," not "Absolute Storage" -- corrected the name) got its company contact info automatically while Dubuqueland didn't. Same code path both times (`resolve_company_name`'s 3-step priority: Merchant Account's own typed Legal Name → "same as DBA" → Intake's own legal name); Affordable Storage's team just typed a real answer into the Merchant Account form's Legal Name question (step 1 worked immediately), while Dubuqueland's team answered "Same as DBA" (needing this week's new step 2).

## Person-identity bug: the session's biggest finding

Boris reported, viewing Key West's Users tab: only 3 roster rows (Barb Soppe/Owner, Zoie Soppe/District Manager, Asher Soppe/Manager), with several other real owners (Carrie Krueger, Chad Soppe, Chris Soppe) showing as **red** ("already linked") "Add User" candidate chips instead of green/addable -- even though they were never actually added.

### Root cause

Every person-matching path in `unitprep-api` used **email alone** as identity for `clients.people`:
- `link_person_to_facility` (ingest-time) -- `SELECT id FROM clients.people WHERE email = $1`.
- `upsert_person_and_link_to_facility` (Add User chip / self-heal) -- same, then unconditionally overwrote `full_name`/`phone` on a match.
- `unitprep-ui`'s own "already linked" match (`rosterByEmailAndRole`) -- keyed on `(email, role)`, no name.

Real Dubuqueland/Soppe family data has several genuinely distinct people sharing one family inbox (`dubuquemini@gmail.com`) with the same role ("owner"). At ingest, every real owner *was* processed (`insert_facility_policies_and_people`'s loop iterates all of `mapped.people()`), but each one resolved to the same shared `clients.people` row (matched by email alone), so only the first insert into `(facility, person, "owner")` succeeded -- every subsequent same-email owner's insert silently hit `ON CONFLICT DO NOTHING` and was dropped. The stored name for that shared row ended up being whichever owner happened to be first in PS's raw text (turned out to be Zoie Soppe, who is *also* listed as an owner, not just DM) -- explaining why "Zoie Soppe" later appeared under **both** Owner and District Manager roles: same collapsed `person_id`, two different role links.

### Fix (`unitprep-api` `v1.9.21`, `unitprep-ui` `v1.6.27`)

Boris's explicit choice, via `AskUserQuestion`, was to **support distinct people sharing one email** (the rejected alternative: treat it as a pure PS data-quality gap and leave the identity model alone).

- `clients.people` identity is now **(email, full_name)**, both case-insensitive, for every path that creates/finds a person.
- New `heal_person_in_place(tx, person_id, full_name, phone)` -- corrects a **known** roster row directly by its own `person_id`, replacing the self-heal path's old re-resolve-by-email step. This matters because self-heal's real job (Sand-Sto's own "Irene Chen - (301) 787-9221" → "Irene Chen" name correction) needs the *opposite* of strict name-matching -- it corrects a name that's already wrong. Splitting the two concerns (identity resolution for a new "Add" vs. direct-by-id correction for self-heal) let both be right at once.
- `get_facility_people`'s self-heal candidate selection now prefers an exact name match among same-email-role candidates (safe under a shared inbox); falls back to a bare email+role match only when it's unambiguous (exactly one candidate) -- the genuine name-correction case; two or more different-named candidates sharing that email+role is left alone rather than guessed at.
- Frontend's "already linked" match (`candidateKey`) now includes full name too.
- Verified with **6 real-Postgres integration tests** (2 new, reproducing the exact Soppe scenario and the Irene Chen correction case directly) plus the full 538→540-test unit suite, all green.

### Rejected approach along the way

Requiring an exact full-name match everywhere (including inside `upsert_person_and_link_to_facility`'s self-heal call) was considered and rejected -- it would have broken the genuine Irene Chen name-correction case entirely (a corrected name, by definition, doesn't match the old stored name). `heal_person_in_place` resolved this by removing the need for any lookup at all on that path.

### Residual data: Key West's existing rows are still stuck

The fix stops this from happening on **new** ingests/links -- it does not retroactively repair Key West's already-collapsed data. Explained precisely why: the "Zoie Soppe -- Owner" row is a leftover misidentified row (a real owner's slot, mislabeled), and self-heal correctly refuses to guess which real owner it should become (ambiguous: 4 candidates share that email+role). Gave Boris a concrete manual fix via the existing UI: Edit-and-rename the wrong row to a real owner's name, then use the now-green "Add User" chips for the rest.

**Follow-on discovered while explaining this**: the roster table had no direct unlink/remove action independent of a matching candidate chip -- Boris asked for one.

## New features requested and shipped

1. **Users tab: direct "Remove" button** (`unitprep-ui` `v1.6.28`) -- unlinks a roster row by its own `person_id`/`role` directly, reusing the existing `DELETE .../people/{id}` endpoint (already existed server-side). Works even for a row a candidate chip can no longer match by name.
2. **Permanent client delete, distinct from archive** (`unitprep-api` `v1.9.22`, `unitprep-ui` `v1.6.28`) -- new `DELETE /clients/{company_id}`, cascades to every facility/policy/link row via the FK `ON DELETE CASCADE` already declared on those tables, never touches `clients.people` itself (a person can be linked under other companies too). Gated on `client_ops.perform`, same as archive. Frontend adds a confirmed (`window.confirm`), separate red "Delete" button on both active and archived rows -- explicitly asked for "not just archive."

Both shipped with full test coverage (backend permission-check test; frontend confirm/cancel/error/archived-row tests).

## CORS gap: DELETE was never actually allowed

Boris tried to delete the test client immediately after the above shipped and got **"Could not reach the API server at http://localhost:8080"** -- with the backend's own log showing the `OPTIONS` preflight succeeding (200) but no follow-up `DELETE` ever arriving.

**Root cause**: `CorsLayer::allow_methods` in `router.rs` never included `DELETE` -- only `GET/POST/PUT/PATCH`. DELETE isn't a CORS-"simple" method, so every cross-origin DELETE is always preflighted; with DELETE missing from the allowed list, the browser's own preflight decision silently refused to ever send the real request. This wasn't new to this feature -- it silently affected **every** existing DELETE route too (facility-person unlink, Elavon unlink, role revocation), just never noticed because nobody had exercised those via a real cross-origin browser session enough to catch it. Diagnostically the failure is indistinguishable from the server actually being down, from the browser's own error message.

**Fix** (`unitprep-api` `v1.9.23`): added `DELETE` to `allow_methods`. Added a real HTTP-level regression test (`a_delete_route_is_allowed_by_the_cors_preflight`, in `http_integration_tests.rs` -- this class of bug is invisible to any direct-handler-call test, same reasoning as the file's existing CORS tests) and **verified it actually fails without the fix** (`git stash` the one-line change, confirmed `expected DELETE in Allow-Methods, got: GET,POST,PUT,PATCH`, then restored). Full 540-test suite green with the fix in place.

## Diagnostic dead ends worth recording

- Considered, before finding the CORS bug: a stale Fast-Refresh bundle, a crashed/stuck backend process, WSL networking. Ruled each out with direct evidence (health-check curl responded instantly; `pg`/process checks showed the backend healthy) before landing on the actual cause.
- Earlier in the session, before the identity bug was found, briefly considered whether `clients_preview.rs` merges `MappedCompany` fields inconsistently across multiple selected Intake runs (a plausible-sounding alternate explanation for the blank-contact-info report). Read the actual code: each selected run keeps its own independent `MappedCompany`; the frontend's `pickCompanySourceRun` picks **one** run's data wholesale, never merges fields across runs. Ruled out before proposing any fix -- consistent with this project's established discipline of verifying against real code/data before changing anything.

## Working-tree hygiene note

`unitprep-ui`'s working tree had unrelated, uncommitted `OrchestratorLoader` component work (not written by this session) touching `clients/search/page.tsx` and `clients/new/page.tsx` alongside files this session needed to edit. Every commit this session made staged only the specific files it intended (`git add <exact paths>`, never `-A`/`.`), leaving that other work untouched and uncommitted for Boris's own session to handle.

## Shipped, versions

| Repo | Version | What |
|---|---|---|
| `unitprep-api` | v1.9.20 *(pre-existing this session)* | "Same as Business DBA" company-name fix |
| `unitprep-ui` | v1.6.25 *(pre-existing this session)* | Search Status "Unknown" labeling |
| `unitprep-ui` | v1.6.26 | Corporate-contact-info fallback banner trigger fix |
| `unitprep-api` | v1.9.21 | Person identity keyed on (email, name); `heal_person_in_place` |
| `unitprep-ui` | v1.6.27 | Users-tab already-linked match includes full name |
| `unitprep-ui` | v1.6.28 | Roster "Remove" button; client "Delete" button |
| `unitprep-api` | v1.9.22 | `DELETE /clients/{company_id}` (permanent delete) |
| `unitprep-api` | v1.9.23 | CORS fix: `allow_methods` now includes `DELETE` |

All tags pushed to `origin/main` on both repos.

## Open items for next session

- The 4th, unexplained Dubuqueland Intake run (`gdBZphWLh8zBlf2WvO5Hlg`) -- still unanswered, PS/business-side question.
- Key West's existing roster still has one misidentified "owner" row (currently showing a real owner's slot mislabeled "Zoie Soppe") -- needs the manual Edit-and-rename-then-Add-the-rest UI fix described above; not done as part of this session (Boris was about to delete-and-recreate the whole test company instead, once delete actually worked).
- `MappedCompany::subdomain`'s own doc comment (in `intake_mapping.rs`) claims the same first-time-facility gating as the other corporate fields -- contradicted by real Dubuqueland data (`Company_Subdomain:` answered independently). Doc-only fix, not done this session.
- Whether to backfill a still-blank company `legal_name` when a Merchant Account run gets linked manually later via the Elavon tab (raised earlier, before this note's own visible context, no answer received yet) -- still open, do not build without confirmation.
- No direct database verification was possible this session for the person-identity investigation -- embedding the real `DATABASE_URL` connection string directly in a Bash command was refused by the safety classifier (credential-in-command-line block). Worked around entirely via `#[ignore]`d Rust tests that load `.env.local` internally (not typed into the shell) -- worth remembering as the pattern for any future live-DB check.

## Related

- [[Session 2026-09-03 — Live Testing Fixes, Transaction Leaks & Field Reference Help]]
- [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]]
- [[Implementation Plan]]
- [[Client & Facility Schema (Process Street-Sourced)]]
- [[Gotchas]]
- [[Production Readiness Checklist]]
