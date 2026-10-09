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

> [!note] Status (as of 2026-10-09)
> **Everything planned is shipped except the live check.** Phases 1, 2a, 3, 4 (api v1.9.92 to v1.9.94, ui v1.6.64 to v1.6.66), the complete-the-task option (v1.9.95 / v1.6.67), every Onboarding Phase (v1.9.117 / v1.6.92), and on 2026-10-09 the **Last Synced Project log (4b)** and **Unit Groups / Template Tagger ClickUp updates (5)** (api v1.9.118 / ui v1.6.93, migration `20261009120000`). **Still not exercised against live ClickUp** (mock only; phase 2b). Phase 6 (a durable job queue) is **dropped**, see below. Part of the [[ClickUp Integration — Build Log]] story; speed work in [[ClickUp Duplicate Check — Speed Work and Share-Link Capture]].

## Every phase, not just Set Up and Migration (2026-10-08, released 2026-10-09 as api v1.9.117 / ui v1.6.92)

Boris: the Copy tab (and the facility dialog) must offer all the groups on the ClickUp list pages -- Scheduling, Show Stoppers and the rest -- not only Set Up and Migration. Done by removing the hard-coded `COPY_PHASES` in `clickup::copy_pairing`: **any task with an Onboarding Phase is offered and paired within its own phase**; a task with *no* phase is still not offered (assumption: "groups" = the Onboarding Phase field's options, as in the 2026-10-02 exploration -- not yet seen on a real list, so confirm the names). The phases are whatever options the list's field defines, so a new template phase needs no code. Each row/task now carries `phase_order` (the option's `orderindex`, kept as `TaskDropdown.option_order`) and both UIs sort groups by it, replacing a hard-coded Set Up/Migration ordering. Verified: clippy clean, 897 unit + 60 ClickUp DB tests, UI 1,025 tests. The earlier statements below that say "Set Up / Migration" describe the original scope.

## Release history

| When | api | ui | What |
|---|---|---|---|
| 2026-10-07 | v1.9.92 | v1.6.64 | Phase 1: parent facility, no-ClickUp waiver, required at Create |
| 2026-10-07 | v1.9.93 | v1.6.65 | Phase 2a: facility Copy dialog and endpoints, pointer comment; Update ClickUp on dedup runs |
| 2026-10-07 | v1.9.94 | v1.6.66 | Phases 3+4: client ClickUp Copy tab, rate limit, background jobs, facility picker, `Main tracker task` footer |
| 2026-10-07 | v1.9.95 | v1.6.67 | Opt-in "Also mark each task complete" (`complete_tasks`, default off); api also carries the passkey-registration characterization tests and the `auth_register` module split (refactor D4g). No migration. |
| 2026-10-09 | v1.9.117 | v1.6.92 | Every Onboarding Phase offered, in the list's own order |
| 2026-10-09 | v1.9.118 | v1.6.93 | Last Synced Project log (facility); Update ClickUp for Unit Groups and Template Tagger runs; task phrases and comment wording moved to data. **Migration `20261009120000`** |

Migrations on Neon dev (applied 2026-10-07): `20261007130000` (parent + waiver), `20261007140000` (copy jobs). **Prod has neither** — `scripts/prod_db_status.sh` then `prod_db_sync.sh`, by Boris only, before the matching api release goes to prod. Phases 3+4 and the footer/picker work were committed together by a second session working in the same tree (`cadc230` api, `1916197` ui).

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

## Phase 2a as built (shipped: api v1.9.93, ui v1.6.65)

- **API** (`src/clickup/` + `src/api/clickup_copy.rs`). Tasks now carry resolved dropdown custom fields (`TaskDropdown`; the value is the option's *orderindex*, an option id string is also accepted). `comments.rs` reads a task's comments (paged, newest first). `copy_pairing.rs` pairs tasks: same phase only, score = 0.7 × name + 0.3 × parent-name (Dice over `task_matching` tokens), min 0.5, greedy one-to-one, `Corp/Fac` as a filter. `copy_text.rs` holds the pointer wording and the wording-match checks (**`MARKER-TODO`** tagged). Endpoints on the target facility: `copy-pairs`, `copy-comments` (per row, lazy), `copy` (≤30 rows/request, 4 at a time, rows independent). Audit event `facility_clickup_comments_copied`.
- **Constants for now**: field names "Onboarding Phase" / "Corp/Fac" and phases "Set Up" / "Migration" live in `copy_pairing.rs` (compared by letters/digits only, so "Set Up" = "Setup"). Move to data like `clickup_task_steps` if the template changes.
- **UI** (`components/clickup/copy/`). `Copy comments…` button on the facility ClickUp section (needs another facility with a linked list; source defaults to the parent). Dialog: phase groups (collapsible), top-level tasks only with subtasks collapsed, target dropdown with suggestions, editable comment prefilled, cursor in the first box, per-row Confirm and outcome. Comment lookups only for visible rows, 3 at a time.
- **Pointer**: posted once per target task after a successful copy; skipped on the parent's own tasks and when no parent is designated.
- Verified: clippy clean; 837 unit + 43 DB tests (10 new copy DB tests against a mock ClickUp with two lists, custom fields and comment state); UI tsc/eslint clean, 903 tests (19 new).

## Phase 5 — Update ClickUp from Onboarding Work (duplicate check 2026-10-07; Unit Groups and Template Tagger 2026-10-09)

- Each recorded run in Onboarding Work has an **Update ClickUp** button (users with `integrations.clickup`), opening the shared panel inline for that run. The endpoints accept the run's row id as well as its session id (the feed lists runs by row id), resolved to the canonical session id inside `prepare`.
- **2026-10-09: now every tool, and the task names are data.** Boris named the tasks: **Unit Groups = "CONFIGURE Unit Setup"**, **Template Tagger = "APPLY TAGS to Lease"**. They are rows in `integrations.clickup_task_steps` (`unit_groups`, `template_tagger`), not code. The migration added `tool`, `comment_lead`, `comment_link_text`, `comment_without_link`, `comment_only_from_sequence` and `UNIQUE (tool, ordinal)`, and moved the duplicate-check wording out of Rust constants into its two rows. A run is matched to the step with the highest `ordinal` not above its position among the facility's runs of that tool (a 3rd duplicate check uses the 2nd's step). Same flow as a duplicate check: the person confirms the task, the comment links the saved file, the actor is added as assignee, the task is set complete; a later run of a one-step tool only comments.
- Module and routes renamed: `clickup_duplicate_check` -> `clickup_run_update`, `clickup/duplicate-check-tasks|results` -> `clickup/run-tasks|run-results`; UI `ClickUpRunUpdatePanel`, `lib/clickupRunUpdate.ts`. Non-dedup runs are audited as `facility_clickup_run_posted` (dedup keeps its older event type so the history reads as one).
- **Decided without asking (flip any):** Unit Groups and Template Tagger *also assign and complete* the task, exactly like a duplicate check, and say "Unit group results are here" / "Template tagger results are here" (no-file fallbacks "Unit groups complete." / "Template tagger complete."). They are data: change the row, not the code.
- **To be configurable later (Boris, 2026-10-09):** the task-name phrases ("keywords for case look-up") and the comment wording should eventually be editable in a settings screen. Today they are database rows an admin/developer can `UPDATE` (RLS already allows it), with no UI. Do not hard-code any of it. Tracked in [[Orchestrator Feature Backlog]].

## 4b — "Last Synced Project" log (shipped 2026-10-09)

- **No new table.** Every copy already writes a `facility_clickup_comments_copied` row in `client_ops.audit_log` (the Activity Logs trail) against the *target* facility, for single, bulk and background copies alike. `GET .../facilities/{id}/clickup/sync-log` (`clickup_copy::sync_log`) reads those rows (source facility name looked up live, who, when, copied/failed/completed, dialog vs bulk), newest first, keyset-paged. The facility's ClickUp section shows the latest source on top and a scrollable history below (`CopySyncLog`), reloaded when the Copy dialog closes.
- **Why the Activity Logs trail and not a log of its own** (Boris asked for an opinion on "the backend log"): the data already exists and is already written in the one place every operations event goes, so a second table would be a second copy that can disagree with the first, and it is indexed already (`entity_type, entity_id`). The cost is that these rows are only as retentive as the Activity Log itself, which is what we want. Known limits: it records counts per copy, not per-task detail (the per-row outcome is in the response and in ClickUp itself); the actor name comes from `auth.users`, which RLS limits to the caller and admins, so a non-admin may see rows with no name; and a deleted source facility reads "A removed facility". The Activity Logs page already shows the same events with every other one.

## Phases 3 and 4 as built (shipped: api v1.9.94, ui v1.6.66)

- **Shipped before this:** Phase 1 (api v1.9.92 / ui v1.6.64) and Phase 2a plus Update ClickUp on dedup runs (api v1.9.93 / ui v1.6.65).
- **Multi-instance caveat (Fly.io is the design target, see [[Key Decisions]]):** the rate limiter, the task cache and the background job *runner* are all in-process. With several machines each would have its own 80-calls/min window against ClickUp's one ~100/min per-token limit, and a job lives on whichever machine accepted the request. The jobs *table* is shared and correct; the limiter and runner are the parts that need the planned Redis (or a shared queue) before running more than one instance.
- **Bulk tab** (`ClickUp Copy`, between General and Onboarding Summary, users with `integrations.clickup`). Choose a source task, tick destination facilities (all ticked, select all/none, per-facility target override, no-match stays unticked), one shared comment prefilled from the source, Confirm. Endpoints under `/clients/{id}/clickup/`: `bulk-tasks`, `bulk-pairs`, `bulk-comment`, `bulk-copy`, `copy-jobs`, `copy-jobs/{id}`.
- **Rate limit** (`clickup::rate_limit`): sliding 60 s window, 80 calls per user (ClickUp allows ~100/min per token), shared by everything that user runs; calls wait, they don't fail. Every ClickUp call a copy makes takes a slot (`clickup_copy::exec`).
- **Inline vs job.** Estimated ClickUp calls = destinations × 3 (comment, read for pointer, post pointer; worst case). ≤ 50 → inside the request; more → job (the "50 in a minute" rule from Boris). `POST bulk-copy` answers 200 `inline` or 202 `job`.
- **Job state** is the one thing ClickUp Copy stores: `client_ops.clickup_copy_jobs` (migration `20261007140000`; owner-only RLS; progress and per-facility results as JSON). A job `running` but silent for 5 min is reported `interrupted` on read (no startup sweep -- that would need to read other users' rows). The job runs as a `tokio::spawn` task in the API process, so a restart cuts it; "Recent copies" says so.
- **Notifications:** the UI polls running jobs every 3 s and raises a browser Notification on running → finished; permission is requested in the click that starts a big copy (browsers only allow it from a gesture). Only a job seen *running* in this session notifies; one already finished at page load doesn't.
- `clickup_copy.rs` (≈700 lines) was split into a module (`lists`, `pairs`, `comments`, `copy`, `exec`, `bulk`, `jobs`), following the standing split-mixed-concern-files rule.
- Verified: clippy clean; 844 unit + 52 ClickUp/parent/copy/bulk DB tests (incl. a real 17-facility background job); UI tsc/eslint clean, 936 tests.
- **Applied to Neon dev 2026-10-07**: migration `20261007140000`, together with `20261007150000` (the QuikStor Cloud street-header format seed from another session). After applying: all 53 ClickUp/parent/copy/bulk/registry DB tests pass; 3 copy tests failed once (first-step status checks) under heavy concurrent CPU load and did not recur in 8 later runs. Still not exercised against live ClickUp.

## Remaining

2b. Live check against real lists (confirm the Onboarding Phase / Corp/Fac option names and the `GET /task/{id}/comment` paging/ordering assumptions), and now also: that the **CONFIGURE Unit Setup** and **APPLY TAGS to Lease** phrases match real tasks.
- A settings screen for `clickup_task_steps` (phrases and comment wording). Data-driven already; no UI.
- **Dropped 2026-10-09 (Boris): no durable job queue.** A background copy still runs as an in-process task and a server restart cuts it ("Recent copies" says so). Do not build a queue unless that changes.

## Open items

- **Footer vs pointer (asked 2026-10-09, still undecided).** Every copied comment now ends with `Main tracker task - {source task link}`. The older separate "Main task list for this client is {parent list}" comment is still posted once per target task, so a task can carry both. If the footer is judged enough, delete `pointer_*` (`copy_text`, `exec::copy_one`, UI `pointerNote`): each destination then costs 1 ClickUp call (the comment) instead of 3 (comment, read to see whether the pointer is there, post the pointer), so the inline limit (about 50 calls) rises from about 16 to about 50 facilities. The trade is losing the list-level pointer (the footer names a *task*, the pointer names the *list*).
- **Rate limiter, task cache and job runner are per-process. Trigger: starting work on cloud deployment (e.g. Fly.io).** With more than one machine each has its own 80-calls/min window against ClickUp's single ~100/min per-token limit. Fix before running more than one instance: a shared limiter (Redis). Also in [[Gotchas]] and [[Key Decisions]].
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
