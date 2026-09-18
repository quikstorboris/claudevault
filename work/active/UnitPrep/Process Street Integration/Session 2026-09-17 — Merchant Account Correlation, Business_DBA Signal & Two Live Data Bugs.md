---
date: 2026-09-17
description: "Investigated a real 'completed Elavon application not showing in OO' report down to two distinct root causes, then added Business_DBA as a second correlation signal alongside the run-title parenthetical. Found a live data-integrity bug along the way: Main Street Storage's facility_merchant_accounts row still points at Dubuqueland's own run, a leftover from the pre-fix false-positive incident, never corrected."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-17 — Merchant Account Correlation, Business_DBA Signal & Two Live Data Bugs

## Starting point: "Milton Self Storage" Elavon application not captured in OO

Boris reported a completed PS Elavon application for "Milton Self Storage" not showing up in OO. Investigation traced to the facility already existing in OO under its **legal name**, "Knapp's Self Stor of Milton Freewater" (`ps_intake_run_id` matched exactly) -- "Milton Self Storage" is just the `Business_DBA` on the Merchant Account application. Not a missing-client problem at all; the real cause was that `correlate_by_title` never even considered this run as a candidate, because its title (`"Milton Self Storage - New Elavon Account"`) has no `(parenthetical)` at all -- `parenthetical()` returns `None` immediately, the run is skipped before any comparison happens.

## Why: the parenthetical convention isn't universal

`merchant_account_correlation.rs`'s whole matching mechanism was reverse-engineered from Prairie Enterprises' own real titling (`"Prairie Enterprises (Highway 20)"`). Real PS data shows a second, plain naming convention exists too: `"<name> - New Elavon Account"`, with no parens anywhere. Confirmed this isn't a one-off: **Main Street Storage's own real, completed application** (`ij83agH69Jmz6qEyzkBDyg`) has the same plain-titled shape and was *also* never correlated by title.

## Real data bug found while checking that: Main Street Storage is linked to the wrong run

Main Street Storage's `facility_merchant_accounts` row points at `swSvLUdhV9zhe9sAludIHw` -- **Dubuqueland Mini Storage's own `(Main)` run**, the exact run from [[Session 2026-09-10 — Developer Role, Merchant Account Nickname Fix, Elavon Resync Redesign & Session Timeout Fix|last week's "Main" false-positive fix]] (`a0058ab`). That fix stops the false match from happening *again*; it never corrected the bad link this same bug had already created before the fix shipped. Right now, Main Street Storage's Elavon tab is showing **Dubuqueland's real rate/parties/EIN/bank/credentials** as its own. **Not yet fixed** -- needs an unlink (Main Street Storage / Dubuqueland's run) and a relink (Main Street Storage / its own real run `ij83agH69Jmz6qEyzkBDyg`), both pending Boris's go-ahead.

## The fix: `Business_DBA` as a second, additive correlation signal

Boris's own framing: the run's title is a lossy, human-typed proxy for information the Merchant Account form already captures cleanly in `Business_DBA`. Checked this against real data:

| Facility | `Business_DBA` | Intake `Facility_Name` | Match? |
|---|---|---|---|
| Highway 20 (Prairie) | "Highway 20 self storage" | "Highway 20 Self Storage" | ✅ |
| Main Street Storage | "Main Street Storage" | "Main Street Storage" | ✅ |
| Milton | "Milton Self Storage" | "Knapp's Self Stor of Milton Freewater" | ❌ |

Two of three real cases resolve cleanly on `Business_DBA` alone, without ever touching a parenthetical. Milton doesn't -- see [[Gotchas#Absolute Storage Management is not a representative client -- don't use it as a design reference|the Absolute gotcha]] for why that specific miss isn't expected to generalize.

**Shipped** -- committed and pushed 2026-09-18 as `unitprep-api` `v1.9.32` (`7f099aa`), see [[Session 2026-09-18 — Force Sync Mode Shipped, Business_DBA Backfill Deferred]]:
- Migration `20260917140000_add_business_dba_to_ps_sync_state`: nullable `business_dba` column on `clients.ps_sync_state`.
- `sync::orchestrator::sync_one_run` now extracts `Business_DBA` (falling back to the key-drift variants `Facility_Name_in_CRM`/`Facility_Name_in_Zoho`, confirmed both exist in real data for the same concept) from the same `fields` fetch it already makes for `ps_person_index` -- **zero extra PS API calls**.
- `merchant_account_correlation.rs`: `MerchantAccountRunInfo` carries `business_dba`; a new `candidate_keywords()` collects both the parenthetical nickname and the DBA (each independently gated by the existing `is_specific_enough` threshold) so either signal alone makes a run a candidate. Additive, not a replacement -- the original title-parenthetical path is untouched.
- 5 new tests, including one proving the real Main Street Storage case now resolves. Live-schema test (`sync_one_run_persists_a_real_business_dba_for_a_merchant_account_run`) confirmed against Highway 20's own real run. 605 total tests green, clippy clean.

## A real limitation found while writing the tests, not silently patched

Writing a "disagreement between signals" test surfaced a **pre-existing** blind spot: a single Merchant Account run whose two signals point at *different* Intake runs currently resolves to `Unambiguous` for **both**, independently -- because each Intake run only ever sees its own candidate count, with no way to know the same `ma.run_id` was also claimed elsewhere. This isn't new; the same thing happens today if one run's parenthetical alone happened to substring-match two different Intake titles. Adding a second signal just doubled the odds of hitting it. **Not fixed this pass** -- would need a post-pass step that demotes any `ma.run_id` claimed `Unambiguous` by more than one Intake run to `Ambiguous` for all of them. Flagged in the code's own test doc comment (`disagreement_between_the_two_signals_independently_unambiguous_for_both_today`), not guessed at silently.

## Open items

1. ~~**Backfill**: the new `business_dba` column is `NULL` for every already-indexed `ps_sync_state` merchant_account row...~~ **Decided 2026-09-18: not running it.** A force-sync mode to do this was built anyway (see [[Session 2026-09-18 — Force Sync Mode Shipped, Business_DBA Backfill Deferred]]), but Boris chose not to spend the PS API budget on it right now -- OO is properly organized as-is, and there's no need to revisit until the missing-signal issue actually resurfaces on a real client.
2. **The cross-run-disagreement gap** above -- a real design question, not urgent.
3. **Main Street Storage's wrong link** -- needs the unlink/relink described above.
4. Owner phone/address as a third corroborating signal (Boris's original proposal) -- not yet built. Only useful for non-Absolute, interactively-filled applications; deferred pending Boris's steer on whether the DBA signal alone is enough for now.

## Related

[[Session 2026-09-18 — Force Sync Mode Shipped, Business_DBA Backfill Deferred]] -- this session's own shipping + the backfill decision.
[[Session 2026-09-10 — Developer Role, Merchant Account Nickname Fix, Elavon Resync Redesign & Session Timeout Fix]] -- the original "Main" false-positive fix this session's own data bug traces back to.
[[Session 2026-09-09 — Elavon QMS & Pinpad Credentials Section]] -- the Elavon tab work this correlation logic ultimately feeds.
[[Gotchas#Absolute Storage Management is not a representative client -- don't use it as a design reference|Absolute-not-representative gotcha]].
