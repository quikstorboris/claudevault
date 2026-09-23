---
date: 2026-09-23
description: "Knapp's Self Stor of Milton Freewater found linked to a different real business's Merchant Account run purely on a fuzzy title match. Root-caused via live PS API queries, fixed via a new Manual Link action, and hardened search results with EIN/address disambiguation and a near-miss name-collision warning. unitprep-api v1.9.36, unitprep-ui v1.6.38, both pushed. Milton's own link deliberately left broken as a live test case."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-23 — Milton Mix-Up, Manual Link Action & EIN/Address Disambiguation

Second half of a long session — see [[Session 2026-09-23 — Onboarding Summary Tab, Tool Run Delete, Resync Perf Fix & Dedup Facility Auto-Select|the first half]] for the Onboarding Summary tab this investigation started from.

## The bug: two different real businesses, both named "Milton" something

Checking the new Onboarding Summary tab against real data, Boris flagged **Knapp's Self Stor of Milton Freewater**'s Elavon Status as "What Rate was provided to the customer" — a step he'd already completed in PS, with a direct link to the task in question.

First pass looked like a resync-not-catching-up issue. It wasn't. Queried the live dev DB directly (`psql` against `NEON_DEV_DATABASE_URL_DIRECT`, bypassing RLS as the table owner) and found the facility's `facility_merchant_accounts.ps_new_merchant_run_id` pointed at run `h_CH_HP9sv2FxY_3c3FPXw` — titled **"Milton Self Storage - New Elavon Account"**, created 2026-09-11. Boris's own URL pointed at a *different* run, `v58kmTeAFkYdSETk6fRJ6A`, titled **"Knapp's Self Stor of Milton Freewater"**, created 2026-08-20 — the one he'd actually been filling out since August (task-completion history in that run shows Boris himself completing the early steps on 2026-08-20).

Pulled both runs' full form fields directly from the PS API (`GET /workflow-runs/{id}/form-fields`, paginated):

| | Knapp's real run (`v58km...`) | Wrong run (`h_CH_H...`) |
|---|---|---|
| Business_DBA | "Knapp's Self Stor of Milton Freewater" | "Milton Self Storage" |
| Legal owner | Rosetta M Knapp | *(blank)* |
| Business_Contact | Rosie Knapp | Shane Carlson |
| Business_Address | 84097 Hwy 11, Milton Freewater, OR 97862 | *(blank)* |
| EIN | 537586661 | *(blank)* |
| Contact_Us_Email | Selfstor_2@msn.com — **exact match** to the real Intake run's own contact email | *(blank)* |
| Conductor (staff) | bmaksimov@quikstor.com | alee@quikstor.com |

Different owner, different contact, a real filled address/EIN on one and nothing on the other, despite several of the wrong run's own tasks being marked "Completed" with no underlying data ever entered. Checked PS's Intake workflow directly for any second Intake run matching "Milton" — none exists; "Milton Self Storage" never got as far as its own Intake.

**Root cause, confirmed by Boris directly**: not a correlation-algorithm bug (`Business_DBA` "Milton Self Storage" doesn't even substring-match "Knapp's Self Stor of Milton Freewater" — the existing `correlate_by_title` signal would never have suggested this pairing). The wrong run's id was copied by hand from the standalone Merchant Account search results (a list matched purely on title text, with zero disambiguating info) and manually linked via the Elavon tab.

## Fix direction, from Boris

1. **Incorporate EIN** as a disambiguation signal.
2. **Address as a secondary, fuzzy measure** — tolerant of formatting noise ("Av." vs. "Ave." vs. "Avenue"), not exact-string.
3. **No hand-holding for missing data** — explicitly declined an automatic "this run looks suspiciously empty" warning.
4. **A confirmation screen during client creation** when multiple similarly-named candidates exist and can't be definitively resolved (both Intake and Merchant Account) — scoped as a larger follow-up, not built this session; the search-results-page enhancements below are the piece that actually shipped.
5. **A new "Manual Link" button** on the Company page (next to Field Reference/Re-sync) to fix a wrong link in place, "to avoid having to remove/recreate client records" — with a worked example showing the run id bolded/red in an example PS URL.
6. **Deliberately did not fix Milton's own link** — Boris's own call, so the new Manual Link button would be a real test case once built. (Confirmed working: "manual link worked like a charm and elavon status is correct now.")

## Shipped: Manual Link action

New `POST /clients/{company_id}/manual-link` (`clients_manual_link.rs`), exposed as a **Manual Link** button/dialog on the Company page. Covers both workflows and — unlike the Elavon tab's own "Link Manually," which explicitly deferred this — relinking *over* an already-linked run:

- **Merchant Account**: clears the old link's rows first (the same three deletes `unlink_facility_elavon` uses: parties, `ps_task_status`, `facility_merchant_accounts`) before ingesting the new run.
- **Intake**: no separate linked/unlinked state to begin with, so it's always a straight overwrite of the facility's own core fields (name/address/phone/etc.) plus `ps_person_index` for the newly-linked run. Deliberately scoped to just the facility row, not `facility_policies`/fees/taxes/coverage/specials or company-level fields — same scope `apply_resync`'s own facility refresh already has.

Always a full overwrite, no `manually_edited_fields` protection — an explicit correction, not routine sync. New `facility_intake_relinked` audit event for the Intake side; Merchant Account reuses the existing `MERCHANT_ACCOUNT_UNLINKED`/`MERCHANT_ACCOUNT_LINKED` pair (fires both, since that's literally what happens to the data).

## Shipped: EIN/address disambiguation + near-miss detection on search

Rather than touch `correlate_by_title` itself (well-tested, incident-history-laden — Milton's own case doesn't even trigger it), the fix landed on the search results page, where the wrong run id actually got copied from:

- `MappedMerchantAccount` gained `ein_last_4` (masked via the existing `mask_bank_number` — the real EIN only ever exists inside encrypted secrets, never in this field) and `business_address` (combined `Business_Address`/`City`/`State`/`Zip`), neither previously captured outside encrypted storage or mapped at all.
- A new `normalize_address`/`addresses_fuzzy_match` pair canonicalizes street-type words (`av`/`ave`/`avenue` → `ave`, etc.) — the literal "Av. vs. Ave. vs. Avenue" case Boris named.
- "Potential Duplicates" candidates (search page) and standalone Merchant Account search results now show each candidate's EIN/address. Potential Duplicates groups also get a per-group `addresses_agree` note: addresses that agree across candidates look like a genuine duplicate submission (the real Carpentersville case); addresses that disagree look like two different real businesses (the real Milton case).
- A new `shares_a_significant_word` check (stopword-filtered word overlap, extending the same reasoning `is_specific_enough` already applies to a single short nickname) flags a standalone Merchant Account match whose title shares real vocabulary with a facility match in the same search without being an outright substring match either way — the actual Milton shape. Surfaced as a "⚠ Similar name to..." warning under the match.

All of it decision-support only — nothing auto-resolves a correlation; Boris's own "no hand-holding" instruction was honored by keeping this to *information*, not automated warnings/gates.

**Not built this session** (Boris: "I'll test the creation piece if/when it comes up... hard to recreate without knowing exactly who might have this issue"): the creation-flow confirmation screen for ambiguous Intake candidates. Deferred until a real case surfaces.

## Shipped versions

Same release as [[Session 2026-09-23 — Onboarding Summary Tab, Tool Run Delete, Resync Perf Fix & Dedup Facility Auto-Select|the first half of this session]] — `unitprep-api` **v1.9.36** (`ad57658` Manual Link, `de641b4` EIN/address/near-miss), `unitprep-ui` **v1.6.38** (`2aa531f` Manual Link, `d7a53ea` EIN/address/near-miss). Both repos' full commit sequences, test counts, and push confirmation are in that note.

## Confirmed working live

Boris used the new Manual Link button to relink Milton's own facility to the correct run (`v58kmTeAFkYdSETk6fRJ6A`) — Elavon Status now correctly shows Complete.

## Related

[[Session 2026-09-23 — Onboarding Summary Tab, Tool Run Delete, Resync Perf Fix & Dedup Facility Auto-Select]] — same day, first half; the Onboarding Summary tab this investigation started from.
[[Session 2026-09-17 — Merchant Account Correlation, Business_DBA Signal & Two Live Data Bugs]] — the same correlation code's own known "cross-run-disagreement" blind spot, a related but distinct gap not touched this session.
[[Session 2026-09-10 — Developer Role, Merchant Account Nickname Fix, Elavon Resync Redesign & Session Timeout Fix]] — the earlier "short nickname false-matches an unrelated client" incident (Dubuqueland's "(Main)" vs. Main Street Storage) this session's `shares_a_significant_word` check is philosophically continuous with.
[[Gotchas]] — see the new entry on Process Street task ids being shared across every run of the same workflow template, discovered while investigating this.
