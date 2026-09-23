---
date: 2026-09-23
description: "New Onboarding Summary tab on the Company page (Elavon status capped at 'Add Credentials to QMS', with a reminder note); a delete action for a mistaken Onboarding Work tool run; cut a redundant Process Street re-fetch out of resync apply; Dedup tab now auto-selects the current facility. unitprep-api v1.9.36, unitprep-ui v1.6.38, both pushed."
tags: [work-note, unitprep, process-street]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-23 — Onboarding Summary Tab, Tool Run Delete, Resync Perf Fix & Dedup Facility Auto-Select

First half of a long session — see [[Session 2026-09-23 — Milton Mix-Up, Manual Link Action & EIN-Address Disambiguation]] for the second half (a real data-quality incident that grew into a Manual Link feature and correlation-disambiguation work).

## New: Onboarding Summary tab

The Company page previously had no tab bar at all — business/owner/Dropbox info just rendered directly. Split into **General** (the existing content, unchanged) and a new **Onboarding Summary** tab: one row per facility, two columns.

**Elavon Status** — the next outstanding step in that facility's Merchant Account Process Street workflow. Walks `clients.ps_task_status` in `id ASC` order (the only ordering signal available at all — PS's own task API carries no position field; `id` is a `BIGSERIAL` assigned the first time a task is ever seen, stable across resyncs since `ON CONFLICT DO UPDATE` never reassigns it).

**Revised mid-session, against real data**: the first version walked the *entire* task list. Checked live against Affordable Storage Katy-Flewellen's own real Merchant Account run — 27 tasks deep, with a long tail after QMS credentials get added ("Twilio Information", "Step for Trojan"/"Step for Absolute"/"Step for Menards", "Add Credentials to YouTrack Card", "Request IP Whitelisting", "Update UDF in Zoho CRM", ...) that are PS-internal/per-vendor follow-ups, not things an onboarding coordinator tracks through this tab. The walk now stops at **"Add Credentials to QMS"** — everything after it is ignored for this column's purposes. Once that step (and everything before it) is done, the cell shows **Complete**; otherwise it shows the first still-incomplete step's name. A boolean flag (`elavon_awaiting_credentials`) marks when "Add Credentials to QMS" itself is the current step, and — per Boris's own follow-up correction — the same reminder note ("Be sure to add credentials to QMS.") now shows under **both** the pending step *and* under Complete, since "Complete" here only means PS's own checklist says the step is checked off, not that OO has independently verified someone actually did it in QMS.

**Duplicate Checks** — count of `client_ops.tool_runs` rows (`tool = 'dedup'`) for that facility, linking straight to its own Onboarding Work tab.

New `GET /clients/{company_id}/onboarding-summary` endpoint; new `CompanyTabs` nav component (General / Onboarding Summary), shown only when no facility is selected — mirrors how `ClientTabs` already handles the facility-scoped tool tabs.

## New: delete a mistaken Onboarding Work tool run

Real trigger: Boris ran a Dedup check on Affordable Storage FM 529 using another facility's uploaded data by mistake. `client_ops.tool_runs` shipped deliberately append-only (`20260910120000_create_client_ops_tool_runs`'s own migration comment: "no DELETE policy — same append-only posture as `client_ops.audit_log`") — there was no way to clear it.

New `DELETE /clients/{company_id}/facilities/{facility_id}/tool-runs/{run_id}`, gated by a new `tool_runs_delete_client_ops_roles` RLS policy (reusing `auth.current_user_is_client_ops_role()`, the shared function `20260909170000_add_developer_role` introduced specifically so a new role-gated policy doesn't need its own fresh OR-chain) plus the existing `client_ops.perform` permission check. Writes a `tool_run_deleted` audit log entry. Frontend: a Delete button on each Onboarding Work run card, same click-to-confirm pattern the Elavon tab's own Unlink button already uses.

## Performance: cut a redundant Process Street fetch out of resync apply

Boris's own observation: confirming a resync — even choosing "keep OO's version" for every conflicting field — took as long as the preview itself, and he suspected `apply` was needlessly re-fetching from PS.

Confirmed by reading the code: `preview_resync` and `apply_resync` each independently called `load_comparisons`, which fetches every linked run's fields *and* tasks live from Process Street, for the company plus every one of its facilities. Preview did that fetch once (~9s in Boris's own log); Confirm did the *entire same fetch again* (~10-14s) before writing anything.

Fix: `preview_resync` now stashes its own already-fetched snapshot in a new `AppState.resync_preview_cache` (keyed by company, 5-minute TTL, `parking_lot::RwLock<HashMap<...>>>` — same pattern `SyncProgressHandle` already uses for shared server-side state). `apply_resync` drains that entry (single-use) when it's still fresh, and only falls back to a live fetch when there's nothing usable — a missing/stale cache entry is always a safe fallback to the old behavior, never a correctness risk. Cuts both the wait and the Process Street API cost roughly in half for the common path.

## Dedup tab now auto-selects the current facility

Separate, smaller fix: the Dedup tab's "Which facility?" dropdown (for importing from Dropbox) previously defaulted to blank every time, requiring a manual pick before every check — the exact kind of manual, error-prone step that caused [[Session 2026-09-23 — Milton Mix-Up, Manual Link Action & EIN-Address Disambiguation|the same day's Milton mix-up]] on the Elavon-linking side. `DedupUploadPage.tsx` now resolves the facility the tab is already scoped to (via `CompanyDetailContext`, already available with no extra fetch) and pre-fills the picker and its Dropbox folder on load. The picker still allows a manual override; it just no longer defaults to nothing.

## Shipped

Organized into 5 feature commits per repo plus a version bump, both pushed to `origin/main`:

- `unitprep-api` **v1.9.36**: `489c0e9` (Onboarding Summary), `30ee8cf` (tool run delete), `2c646c9` (resync cache), plus the two commits covered in [[Session 2026-09-23 — Milton Mix-Up, Manual Link Action & EIN-Address Disambiguation|the Milton session note]], then `d3291ab` (version bump).
- `unitprep-ui` **v1.6.38**: `5326963` (Onboarding Summary), `f99c8f9` (tool run delete), `8aa212b` (Dedup auto-select), plus the two commits covered in the Milton session note, then `79d10b4` (version bump).

644 backend tests / 442 frontend tests, clippy/tsc/eslint all clean.

## Related

[[Session 2026-09-23 — Milton Mix-Up, Manual Link Action & EIN-Address Disambiguation]] — same day, second half.
[[Session 2026-09-11 — Onboarding Work Tab (Durable Tool-Run History)]] — the tool_runs table and Onboarding Work tab this session extends with a delete action.
[[Session 2026-09-09 — Security & Activity Logs Page Split (DRY Pagination Refactor)]] — the shared `useInfiniteLogFeed` hook the Onboarding Work tab already reuses.
[[Process Street Integration — Kickoff & Findings]]
