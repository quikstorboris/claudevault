---
date: 2026-10-07
description: "ClickUp Copy: copy key comments between a client's facility ClickUp lists. Every design decision (with Boris's answers), Phase 1 as built (parent designation, no-ClickUp waiver), the remaining phases, and open items."
tags: [work-note, unitprep, clickup, design, integration]
status: active
quarter: Q4-2026
project: unitprep
---

# ClickUp Copy — Design and Phase 1

Part of the [[ClickUp Integration — Design Log]]. A client with several facilities has one ClickUp list per facility, and onboarding managers track the redundant ("corporate-level") tasks in each by hand. ClickUp Copy copies a comment from a source task to its counterpart task in other facilities' lists.

> [!note] Status (as of 2026-10-07)
> **Phase 1 shipped** (api v1.9.92, ui v1.6.64, both pushed and tagged). Migration `20261007130000` is applied to local test-db **and Neon dev**; prod is Boris-only.
> **Phase 2a built and tested, not committed** (see "Phase 2a" below): the facility dialog and its three endpoints. **Not yet exercised against live ClickUp** — only against a mock. Phases 2b–5 not started.

## Decisions (Boris, 2026-10-07)

- **Where it lives.** Facility level: a dialog. Client level: a **bulk tab** (between General and Onboarding Summary). Single facility per dialog; the target is always the facility you're on, whose own list is attached to it.
- **Dialog layout.** Source task | target task | editable comment (focused on open, prefilled with the source's latest comment) | Confirm. Two collapsible groups, **Set Up** and **Migration**. Where a mid-level task has subtasks, show **only the mid-level tasks, collapsed**.
- **Groups.** Come from the list template, as the *Onboarding Phase* custom field. A *Corp/Fac* custom field (Corporate / Facility) exists too; use it as a **filter** for corporate vs facility-specific tasks. Both come back as option **indexes**, not names; map through the list's field definitions and match on stable option ids (emoji in names come back garbled).
- **Matching.** Auto-match by name + group, with manual override per row and a "no match" state. Reuse `clickup::task_matching` normalization (verbs, numbering, emoji, plurals).
- **Direction.** Any source task to its counterpart target, **not only parent → secondary**. The dialog gets a source-facility selector that defaults to the parent.
- **No per-task state in our DB.** ClickUp is the record. Double-posting is acceptable. Instead, detect an already-copied comment by matching the standard wording; later add a marker like "Auto-added by OO". **Every place that matches on wording must be commented `MARKER-TODO:`** (one constant, one grep).
- **Comments.** Plain text, no attachments. Mentions pass through untouched. Posted as the **clicking user** (per-user token); show an "access denied" message per row on 403.
- **Pointer comment.** Whenever a comment is copied, also post a separate generic comment on the target task: *"Main task list for this client is {parent facility's list}"*, the list name linked. **Once per target task**: skipped if that task already has it (wording match, `MARKER-TODO`). Alternative not chosen: a single list-level comment per target list.
- **Throttling.** ClickUp allows ~100 requests/min per token. Estimate API calls (reads + writes). Over budget, switch to a background queue and "We will notify you when copying is complete", with a browser notification and a fallback banner. The only new DB state: a minimal job record for the queue, plus a small sync log feeding "Last Synced Project".
- **Linking.** Enforced at client creation: a ClickUp link, or the "Create without ClickUp project" checkbox. Tool runs (Dedup first) get "Add comment to ClickUp" via the same category-based task lookup, so a comment can be posted later if ClickUp was unavailable. Parent changes are recorded; each facility's Copy Comments section shows a scrollable chronological **Last Synced Project** log.
- **Bulk tab.** Pick the source task, tick destination facilities (select all/none, all selected by default), write one comment applied to all targets.

## Phase 1 as built

- **API.** Migration `20261007130000`: `clients.companies.clickup_parent_facility_id`, `clickup_waived_at`/`clickup_waived_by`, and the append-only `clients.company_clickup_parent_history` (name snapshots, so history survives a rename or delete). `PUT /clients/{id}/clickup-parent` (parent must belong to the company *and* have a linked list; idempotent), `PUT`/`DELETE /clients/{id}/clickup-waiver`, `clickup_waived` on `POST /clients`. Gated `client_ops.perform`; audited. Module `api/clients_clickup_parent.rs`; 10 DB tests.
- **UI.** Review & Create gets a ClickUp card with the checkbox. Unticked, a user with ClickUp access lands on the new client with the Link ClickUp dialog open (`?linkClickUp=1`); ticked, the waiver is recorded. The company's ClickUp section gets a Parent facility dropdown (only facilities with a linked list) with a scrollable history, plus waiver/amber states.
- **Chosen without being asked:** the link step happens *after* Create (facilities don't exist before it), and a user without `integrations.clickup` isn't blocked.
- Verified: clippy clean, 812 unit tests, 10 new DB tests, tsc/eslint clean, 209 UI tests. Boris confirmed the parent dropdown works on Neon dev.

## Phase 2a as built (uncommitted)

- **API** (`src/clickup/` + `src/api/clickup_copy.rs`). Tasks now carry resolved dropdown custom fields (`TaskDropdown`; the value is the option's *orderindex*, an option id string is also accepted). `comments.rs` reads a task's comments (paged, newest first). `copy_pairing.rs` pairs tasks: same phase only, score = 0.7 × name + 0.3 × parent-name (Dice over `task_matching` tokens), min 0.5, greedy one-to-one, `Corp/Fac` as a filter. `copy_text.rs` holds the pointer wording and the wording-match checks (**`MARKER-TODO`** tagged). Endpoints on the target facility: `copy-pairs`, `copy-comments` (per row, lazy), `copy` (≤30 rows/request, 4 at a time, rows independent). Audit event `facility_clickup_comments_copied`.
- **Constants for now**: field names "Onboarding Phase" / "Corp/Fac" and phases "Set Up" / "Migration" live in `copy_pairing.rs` (compared by letters/digits only, so "Set Up" = "Setup"). Move to data like `clickup_task_steps` if the template changes.
- **UI** (`components/clickup/copy/`). `Copy comments…` button on the facility ClickUp section (needs another facility with a linked list; source defaults to the parent). Dialog: phase groups (collapsible), top-level tasks only with subtasks collapsed, target dropdown with suggestions, editable comment prefilled, cursor in the first box, per-row Confirm and outcome. Comment lookups only for visible rows, 3 at a time.
- **Pointer**: posted once per target task after a successful copy; skipped on the parent's own tasks and when no parent is designated.
- Verified: clippy clean; 837 unit + 43 DB tests (10 new copy DB tests against a mock ClickUp with two lists, custom fields and comment state); UI tsc/eslint clean, 903 tests (19 new).

## Phase 5 (partly) — Update ClickUp from Onboarding Work (uncommitted, 2026-10-07)

- Each recorded **duplicate check** run in Onboarding Work has an **Update ClickUp** button (users with `integrations.clickup`), opening the existing `ClickUpDuplicateCheckPanel` inline for that run. The API's dedup ClickUp endpoints now accept the run's row id as well as its session id (the feed lists runs by row id), resolved to the canonical session id inside `prepare`.
- **Unit Groups and Template Tagger: not done, and deliberately parked (Boris, 2026-10-07).** Each will eventually get its own ClickUp task update from Onboarding Work, plus an activity-log entry. Nothing in the vault or code yet says which ClickUp task they update or what the comment says. To add one: a step row in `integrations.clickup_task_steps` (key, label, ordinal, task-name phrases), the comment wording, an endpoint pair like `clickup_duplicate_check`, and the tool in `canUpdateClickUp` (`components/facility/RunClickUpAction.tsx`). **Need from Boris:** the ClickUp task name(s) for each and what the comment should say (and whether to assign/complete).

## Phases 3 and 4 as built (uncommitted, 2026-10-07)

- **Shipped before this:** Phase 1 (api v1.9.92 / ui v1.6.64) and Phase 2a plus Update ClickUp on dedup runs (api v1.9.93 / ui v1.6.65).
- **Bulk tab** (`ClickUp Copy`, between General and Onboarding Summary, users with `integrations.clickup`). Choose a source task, tick destination facilities (all ticked, select all/none, per-facility target override, no-match stays unticked), one shared comment prefilled from the source, Confirm. Endpoints under `/clients/{id}/clickup/`: `bulk-tasks`, `bulk-pairs`, `bulk-comment`, `bulk-copy`, `copy-jobs`, `copy-jobs/{id}`.
- **Rate limit** (`clickup::rate_limit`): sliding 60 s window, 80 calls per user (ClickUp allows ~100/min per token), shared by everything that user runs; calls wait, they don't fail. Every ClickUp call a copy makes takes a slot (`clickup_copy::exec`).
- **Inline vs job.** Estimated ClickUp calls = destinations × 3 (comment, read for pointer, post pointer; worst case). ≤ 50 → inside the request; more → job (the "50 in a minute" rule from Boris). `POST bulk-copy` answers 200 `inline` or 202 `job`.
- **Job state** is the one thing ClickUp Copy stores: `client_ops.clickup_copy_jobs` (migration `20261007140000`; owner-only RLS; progress and per-facility results as JSON). A job `running` but silent for 5 min is reported `interrupted` on read (no startup sweep -- that would need to read other users' rows). The job runs as a `tokio::spawn` task in the API process, so a restart cuts it; "Recent copies" says so.
- **Notifications:** the UI polls running jobs every 3 s and raises a browser Notification on running → finished; permission is requested in the click that starts a big copy (browsers only allow it from a gesture). Only a job seen *running* in this session notifies; one already finished at page load doesn't.
- `clickup_copy.rs` (≈700 lines) was split into a module (`lists`, `pairs`, `comments`, `copy`, `exec`, `bulk`, `jobs`), following the standing split-mixed-concern-files rule.
- Verified: clippy clean; 844 unit + 52 ClickUp/parent/copy/bulk DB tests (incl. a real 17-facility background job); UI tsc/eslint clean, 936 tests.
- **Applied to Neon dev 2026-10-07**: migration `20261007140000`, together with `20261007150000` (the QuikStor Cloud street-header format seed from another session). After applying: all 53 ClickUp/parent/copy/bulk/registry DB tests pass; 3 copy tests failed once (first-step status checks) under heavy concurrent CPU load and did not recur in 8 later runs. Still not exercised against live ClickUp.

## Remaining

2b. Live check against real lists (confirm the Onboarding Phase / Corp/Fac option names and the `GET /task/{id}/comment` paging/ordering assumptions).
4b. Facility > Copy Comments "Last Synced Project" log (needs a small sync log -- not built; the jobs table only covers background copies).
5. Onboarding Work: "Add comment to ClickUp" for Unit Groups and Template Tagger (see above).
6. A durable job queue if restart-resilience is ever needed (today a restart interrupts a running job).

## Open items

- Exact option names of *Onboarding Phase* / *Corp/Fac* are unconfirmed (no live probe: Boris's `curl` had an unset `$CU_TOKEN`). Plan: make the phase names an editable setting, default "Set Up" / "Migration", match loosely.
- Pre-existing, unrelated: ignored test `refresh_matching_facility_updates_unprotected_fields_and_skips_protected_ones` needs a real imported Highway 20 row plus live Process Street, so it fails on a fresh test-db.

## Operational gotchas learned

- `docker compose exec api-dev cargo run` reads **Neon dev** (`DATABASE_URL`); only `--ignored` tests use the local test-db (`TEST_DATABASE_URL`). A migration applied only to the test-db makes the running app 500 on the new column.
- `DATABASE_URL` is the restricted `app_service` role and **cannot run DDL**. Run sqlx against `NEON_DEV_DATABASE_URL_DIRECT` (unpooled owner); never use the PROD variables. Pull it with `grep`, never `source` the file.
- DB tests: a caller whose user id isn't a real `auth.users` row hits the new `waived_by`/`changed_by` foreign keys and gets a 500. Use `create_user` from `clickup_db_tests`.

## After the first live test (AffStor, 2026-10-07) — uncommitted

Boris's feedback: (1) the Copy tab copied to every other facility by default; he wants to pick and choose, as a dropdown with checkboxes. (2) Every copied comment should end with a link to the main list's source task: `Main tracker task - {text/link}` at the bottom, with 3 line breaks after the original comment.
- **Picker.** `FacilityMultiSelect` (dropdown of checkboxes, Select all / none, closes on Escape / outside click). **Nothing is selected to begin with.** A task row appears only for each picked facility; a picked facility with no counterpart must have a task chosen (or be unpicked) before Confirm enables; a facility whose list could not be read cannot be picked and Select all skips it. The per-facility `checked` no longer implies a target exists (`DestinationState.blocked` added).
- **Footer**, server-side so the facility dialog, bulk copy and background jobs all get it: body + `"\n\n\nMain tracker task - "` + the source task's name as a link to its URL (`clickup::copy_text::comment_parts`, `exec::SourceLink`). `source_task_id` is new on `POST .../clickup/copy` items and `POST .../bulk-copy`; the task is looked up in the *source* facility's list (so the URL is ClickUp's own) and anything outside it is refused (`task_not_in_source_list`) before any write. It is optional on the wire for older clients, but both UIs always send it. `looks_already_copied` strips the footer before comparing.
- **Decision not asked for:** the separate once-per-task "Main task list for this client is ..." pointer comment is **unchanged**, so a target task can now carry both that note and the footer link. If the footer replaces it, delete `pointer_*` (`copy_text`, `exec::copy_one`, UI `pointerNote`) and `calls_per_row` drops from 3 to 1, which raises the inline budget from about 16 to about 50 facilities.
- Verified: API 847 unit + 56 DB tests, clippy clean; UI 939 tests, tsc and eslint clean. Not yet seen in live ClickUp: that a leading `\n\n\n` text block renders as three line breaks.


## Complete-the-task option (2026-10-07, after the first release; uncommitted code)

Boris: copying must be able to *just* copy/create comments without completing the task, and optionally complete it. (Copy never completed anything before this; only the duplicate-check update does.) Built as an opt-in, **default off**: `complete_tasks` on `POST .../clickup/copy` and `POST .../clickup/bulk-copy`; UI checkbox "Also mark each task complete" on the Copy tab and in the facility dialog. After a comment is posted the destination list's own statuses are read and the task set to its complete status (`complete`/`completed`, else `closed` class, else `done`); a list without one reports `This list has no complete status.` and the comment still stands; a refused comment is never completed. Two extra ClickUp calls a destination (inline budget about 10 facilities with pointer + completing, about 16 without completing; larger copies are background jobs). Verified: API 849 unit + 61 DB tests, clippy and fmt clean; UI 941 tests, tsc and eslint clean. Not yet seen in live ClickUp.
Also this round: Boris reported not seeing the destination picker and the footer note: the running UI bundle already contained both, so it was a stale browser tab (hard refresh). The footer itself is appended by the API when posting, so it is not part of the editable comment text; the note under the comment box says so.
