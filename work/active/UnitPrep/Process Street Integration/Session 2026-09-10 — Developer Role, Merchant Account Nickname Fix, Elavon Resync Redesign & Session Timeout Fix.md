---
date: 2026-09-10
description: "Four independent pieces shipped the same day: a new developer system role (full client-ops + integrations access, no admin), a real Merchant Account correlation bug fix (a short parenthetical nickname false-matched an unrelated client), the Elavon tab's credentials-only resync redesigned into one full-tab resync, and a real production bug found and fixed — a 30-minute idle timeout silently overriding an intentionally-set 8-hour session length."
tags: [work-note, unitprep, process-street, auth, rls]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-10 — Developer Role, Merchant Account Nickname Fix, Elavon Resync Redesign & Session Timeout Fix

## Developer role: full client-ops + integrations access, no admin

Boris's spec, verbatim: "like admin, this role will have full access to both integration configs, and logs. No access to security configs/logs unless admin role is assigned along side developer. They will also have full access to everything that onboarding manager has."

**The real work was the RLS layer, not the permission catalog.** This codebase's RLS policies do NOT check permissions — every `clients.*`/`client_ops.*` table's own INSERT/UPDATE/DELETE policy hardcodes `auth.current_user_has_role('onboarding_manager') OR auth.current_user_has_role('department_manager')` directly, across 69 policies on 23 tables (confirmed by querying `pg_policies` directly, not reconstructed from migration history by hand). Simply granting `developer` the `client_ops.perform`/`client_ops.manage_tags` permissions in the catalog would have passed every app-layer check and then silently failed at the database — the same class of bug `20260909150000_admin_only_integrations_settings` had already fixed once for Process Street's own settings table.

**Fix**: one shared function, `auth.current_user_is_client_ops_role()`, and every one of those 69 policies repointed at it. Adding a role to this club going forward is now a one-line change to the function, not another 69-policy sweep. The 3 integrations-settings policies (admin-only before `developer` existed) got the same treatment, inlined since there were only three.

**Real gap found and closed live**: a follow-up migration was needed within minutes of applying the first — the permission grant had been built off `onboarding_manager_user()`'s test fixture, which turned out to be stale. The real `onboarding_manager` role (seeded 2026-08-18 by `create_vendor_format_registry`) also holds `client_ops.manage_vendor_formats`, confirmed live on `/admin/roles` right after applying the first migration. "Full access to everything onboarding manager has" means the real role, not the fixture — backfilled the same gap into the `admin`/`onboarding_manager`/`department_manager` test fixtures too while fixing it.

Both migrations applied and verified directly against the live Neon dev database (`_sqlx_migrations` confirms both `success: t`); Boris's own account was granted the role via the same sanctioned bootstrap-migration route his original admin+onboarding_manager dual-hat used (RLS structurally refuses anyone, including admin, from granting/revoking their own roles through the normal app path).

Shipped `unitprep-api` `v1.9.26` (`382656a`).

## Merchant Account correlation: a short parenthetical nickname false-matched an unrelated client

Real bug, found live: Dubuqueland Mini Storage's own "Main" facility gave a Merchant Account run titled `"...(Main)"`. `"main"` is a plain substring of an entirely unrelated new client's own Intake title, `"Main Street Storage - QMS Onboarding"`. `correlate_by_title` matched them as `Unambiguous` (nothing else competed for the slot), silently seeding Dubuqueland's own legal name onto Main Street Storage's confirmation screen.

A word-boundary check would **not** have caught this — "Main" is a genuine whole word in both titles. The actual problem: a short, single-word nickname isn't a specific enough discriminator to trust unattended. Fix: `is_specific_enough(keyword)` — a parenthetical nickname must be either multi-word (`"Pyott Rd"`) or 6+ characters (`"Carpentersville"`) to be trusted as a candidate at all; anything shorter is excluded entirely, same treatment as no parenthetical existing. It can still surface as `Correlation::Ambiguous` if some *other*, more specific nickname also matches — this only kills the false `Unambiguous` case, not correlation generally. Proven against the exact real case (Dubuqueland/Main vs. Main Street Storage) plus a regression test confirming a genuinely specific nickname (Highway 20) still correlates normally alongside a screened-out generic one in the same run.

Shipped `unitprep-api` `v1.9.27` (`a0058ab`).

## Elavon tab: credentials-only resync redesigned into one full-tab resync

Follow-up to [[Session 2026-09-09 — Elavon QMS & Pinpad Credentials Section]]. Boris reported `credentials_added_to_qms` stuck showing "No" after actually completing the "Add Credentials to QMS" PS checklist step post-link. Root cause: that field is only ever set **once**, at link time, from `get_run_tasks` — the dedicated "Resync Credentials" button shipped the day before deliberately never called `get_run_tasks` at all (by design, scoped to just 4 credential fields), so there was no path to refresh it short of a destructive unlink/relink that also wipes party rows.

**Decision, and why**: rather than adding a second, broader button alongside the narrow one, replaced it entirely. Unlike Intake's own resync (which has real manually-edited-field protection to navigate), nothing in Merchant Account data has a manual-edit UI in OO — it's pure read-through from PS — so a full silent overwrite from a fresh `get_run_form_fields` + `get_run_tasks` pull is exactly as safe as the narrow version was. One "Resync Elavon Data" button now refreshes rate, status, `credentials_added_to_qms`, financials, credentials, and parties together; `repository::resync_merchant_account_run` UPDATEs the existing row and replaces party rows (delete + re-insert) instead of the INSERT-only path `ingest_merchant_account_run` uses at link time.

Shipped `unitprep-api` `v1.9.25` (`c3f15d2`) and `unitprep-ui` `v1.6.30` (`c90c66f`).

## Real production bug: a 30-minute idle timeout was silently overriding an intentional 8-hour session length

Boris asked to "bump login session length to 8 hours" — turned out dev's `.env.local` already had `SESSION_LIFETIME_HOURS=8` (set 2026-08-27). The actual complaint ("booted after what feels like 30-60 minutes") didn't match either the 8h or the code's 12h fallback default at all.

**Root cause**: a *separate* idle timeout (`SESSION_IDLE_TIMEOUT_MINUTES`), enforced server-side in `auth.resolve_session` independent of the absolute session lifetime, had never been set — silently falling back to the code's 30-minute default. Any gap of 30+ minutes without an authenticated request killed the session outright, no matter how much of the 8-hour ceiling remained. The `.env.local` comment from 2026-08-27 (when the session length was deliberately lowered from 12h to 8h) explicitly called the idle timeout "a separate, unrelated knob" and left it alone — that assumption was the actual bug. At the 30-minute default, idle timeout was the binding constraint the entire time, not session length.

**Fix**: `SESSION_IDLE_TIMEOUT_MINUTES=480` in dev's `.env.local`, matching the 8-hour session length so idle timeout stops being a separate, tighter ceiling in practice. Comment corrected to document what actually happened. No code change — both values were already env-var driven; `.env.local` is gitignored, so nothing to commit. Dev backend restarted to pick up the change (it only reads `.env.local` at startup). **Open item**: if production has its own `SESSION_IDLE_TIMEOUT_MINUTES` (or lack thereof) set somewhere outside this repo, the same fix applies there — not verified, no deployment config exists in-repo to check.

## Related

[[Session 2026-09-09 — Elavon QMS & Pinpad Credentials Section]] — the Elavon credentials work this session's resync redesign follows up on.
[[Gotchas#STRICT RULE (2026-09-09)_ `unitprep-api`/`unitprep-ui` exist ONLY in WSL — never a Windows/Dropbox/OneDrive clone|Gotchas' WSL-only rule]] — the incident immediately preceding this session, same day's broader work.
