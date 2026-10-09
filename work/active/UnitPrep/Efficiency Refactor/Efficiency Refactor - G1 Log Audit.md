---
date: 2026-10-08
description: "G1 log-event audit for the efficiency refactor: what both audit trails and the tracing logs hold, the gaps found against recent work, what shipped (api 1.9.111-1.9.112), what was consciously not done."
tags: [work-note, unitprep, efficiency, refactor, observability, audit]
status: active
quarter: Q4-2026
project: unitprep
---

# Efficiency Refactor - G1 Log Audit

Phase G1 of [[Efficiency Refactor - Master Plan and Progress]]: audit the backend's log events after the rest of the refactor, and add the ones recent work warrants. Chronology is in [[Efficiency Refactor - Session Log]]; the standing design is [[Logging & Observability]].

## What shipped (all pushed 2026-10-08)

| Release | Change |
|---|---|
| api **1.9.111** + ui 1.6.86 | New security-trail event `integration_settings_updated`: admin edits of the Dropbox settings, Process Street settings and Process Street task-role mappings (before: no audit row at all). Records the integration, what was set, the caller's IP, and ONLY that a secret was replaced. New client-ops event `activity_log_exported` (the counterpart of the security trail's `audit_log_exported`). 6 real-DB tests, mutation-checked; secrets proven absent from the rows. |
| api **1.9.112** | `bootstrap-admin` (create / `--reissue-invite`) writes an `invite_created` row (no actor, `via: bootstrap_cli`), smoke-tested with the real binary against a scratch DB. `database connection pool exhausted` is its own log line (pool size + idle). Retry give-ups log once (`integrations::http`). `warn_if_slow` wired into 7 more handlers (dedup export x2, tagger check/apply, unit-group validate/analyze/export). `Debug` redacted on the 4 secret-bearing input structs. |

## Method

1. **Route cross-reference.** A script parsed every `gated_route` in `router/routes/*.rs` (107 mutating routes) and checked whether the handler (or its module) emits an audit event. Heuristic: `module-only` mostly means a helper audits. Of the 38 `NONE`, nearly all are session-scoped tool plumbing (upload, validate, correct, tagger steps, cancel) that mutate an in-memory session, not stored data - deliberately unaudited. The real gaps were the integration-settings writers and the activity-log export.
2. **Backlog walk.** Every G1 backlog line recorded during the refactor was decided (below).
3. **PII / secret scan of the `tracing` calls.** No log call prints a request body, headers or a credential value; upstream response bodies are truncated to 512 B (A2). One latent risk found (secret-bearing request structs derived `Debug`) and closed.

## Decisions

| Item | Decision |
|---|---|
| Integration settings writers unaudited | **Added** `integration_settings_updated` (security trail: credentials/config are security-relevant). |
| Activity-log export unaudited | **Added** `activity_log_exported` (client-ops trail). The export *preview* is not audited (same as the security log's). |
| Bootstrap CLI leaves no record | **Added** as `invite_created` with `via: bootstrap_cli` rather than a new event: it IS an invite, and the metadata distinguishes it. |
| Pool exhaustion | **Added** a distinct `error` line; no durable event (it is a capacity signal, not an action). |
| Retries exhausted | **Added** one `warn` per give-up. No audit event: ordinary scheduled-sync failures already write `sync_failed`. |
| Slow handlers | **Wired** where the handler already timed itself; not wired where it would need new timing. |
| Secrets in `Debug` | **Redacted** for the 4 request-input structs. Not done for response structs that return decrypted secrets to an admin on purpose (`DropboxSettingsResponse`, `ProcessStreetSettingsResponse`, `EnrollBeginResponse`, `CreateInviteResponse`): they are outputs, and nothing logs them. |
| Blocking-task failure | Already logs `error` "blocking task failed" with `operation` + `panicked`; no durable event. |
| Tool-run rematch / unidentified-mode changes | **Not audited** (they re-derive a stored output of the user's own run; the run itself is audited). Revisit if a reviewer wants it. |
| Vendor-format registry | No admin endpoints exist; changes are migrations, which are versioned. Nothing to audit. |
| Unclean shutdown record (D3b) | Not done; revisit when hosting is decided. |
| Session-persistence coalescing (B5) | N/A - B5 was skipped. |
| Per-run sync failures (B3) | Already non-fatal and recorded in the sync's own `sync_failed`/`sync_completed` audit rows; no new event. |

## Known limitations

- The route cross-reference is heuristic (a handler that audits through a helper under another name reads as `NONE`/`module-only`); re-run it by reading `router/routes/*.rs` after adding routes.
- `integration_settings_updated` does not record the previous values (a `Change`): the secrets can't be, and the non-secret fields (Dropbox root path, PS schedule) are recorded as the new value only.
- A pre-existing failing real-DB test, `clients::sync::orchestrator::live_tests::refresh_matching_facility_updates_unprotected_fields_and_skips_protected_ones`, fails on the untouched baseline too (found 2026-10-08, not investigated; unrelated to G1).

## Audit-event inventory (generated from the code, 2026-10-08)

**Security trail** (`auth.auth_audit_logs`, `auth::audit_log::event`): 30 event types.

| Event | What it records | Emitted from |
|---|---|---|
| `registration_failed` | The registration-side counterpart of `LOGIN_FAILED`, covering both a refused `/register/begin` and a `/register/finish` whose credential did not verif | `finish.rs, responses.rs` |
| `invite_created` | An administrator issued an invitation. | `bootstrap.rs, invite.rs` |
| `session_revoked` | One or more sessions were revoked. | `auth_logout.rs` |
| `totp_enrolment_started` | A user began TOTP enrolment: a secret was written but not yet proven. | `auth_totp.rs` |
| `totp_enrolment_failed` | A confirmation code was rejected during enrolment. | `auth_totp.rs` |
| `totp_enrolled` | TOTP is confirmed and usable as a step-up factor for sensitive in-session actions (see TOTP_STEP_UP_SUCCEEDED) -- not a way to log in; see auth_totp.r | `auth_totp.rs` |
| `invite_refused` | An administrator attempted to issue an invitation to an account that was not eligible -- already credentialed, or not in `invited` status. | `invite.rs, recovery.rs` |
| `account_recovery_initiated` | An administrator initiated account recovery: every existing access path on the target account (passkeys, TOTP, live sessions, any outstanding invite)  | `recovery.rs` |
| `totp_step_up_succeeded` | An already-signed-in caller proved a fresh TOTP code, elevating their own session for a short window (auth.record_step_up) so a sensitive action (addi | `auth_totp.rs` |
| `totp_step_up_failed` | A step-up code was rejected. | `auth_totp.rs` |
| `passkey_reverify_succeeded` | An already-signed-in caller proved a fresh passkey assertion, elevating their own session for a short window (auth.record_passkey_reverify) so a sensi | `auth_passkey_reverify.rs` |
| `passkey_reverify_failed` | A passkey re-verification assertion failed or was abandoned. | `auth_passkey_reverify.rs` |
| `login_anomaly_detected` | A successful login came from an IP address or user_agent never seen before for an account that has prior session history (Phase II anomaly signal, see | `auth_login.rs` |
| `session_expired_access_attempt` | A request presented a session cookie that resolved to a real, non-revoked session row, but one that had already crossed its idle or absolute expiry. | `authenticated_user.rs` |
| `rate_limit_rejected` | `tower_governor` refused a request for exceeding its bucket. | `mod.rs` |
| `authorization_failure` | An authenticated caller reached an admin-gated action without the role it requires. | `authenticated_user.rs` |
| `user_deactivated` | An administrator deactivated another user's account through the standalone disable-user action -- distinct from `ACCOUNT_RECOVERY_INITIATED`, which al | `auth_user_status.rs` |
| `role_granted` | An administrator granted an already-enrolled user an additional role. | `auth_user_role.rs` |
| `role_revoked` | `ROLE_GRANTED`'s counterpart -- an administrator revoked a role from an already-enrolled user. | `auth_user_role.rs` |
| `user_reactivated` | An administrator reactivated a deactivated user's account, issuing a fresh invite in its place. | `auth_user_status.rs` |
| `audit_log_exported` | An administrator exported the audit log as a PDF. | `auth_audit_logs_export.rs` |
| `auth_configuration_updated` | An administrator edited org-wide auth policy (`auth.auth_configuration` -- currently just `step_up_actions`). | `auth_configuration.rs` |
| `permission_granted` | An authorized user granted an already-enrolled user an individually-grantable permission such as a personal integration (`auth.user_permissions`). | `auth_user_permissions.rs` |
| `permission_revoked` | `PERMISSION_GRANTED`'s counterpart. | `auth_user_permissions.rs` |
| `integration_connected` | A user saved a valid personal credential for a third-party integration (`metadata.integration` names which one). | `clickup_connection.rs` |
| `integration_disconnected` | A user removed their own credential for a third-party integration. | `clickup_connection.rs` |
| `integration_settings_updated` | An administrator changed an org-wide integration setting (`api::dropbox_settings`, `api::process_street_settings`, `api::process_street_task_roles`) - | `integration_settings_audit.rs` |
| `login_succeeded` |  | `auth_login.rs` |
| `login_failed` |  | `auth_login.rs` |
| `passkey_registered` |  | `finish.rs` |

**Client-ops activity trail** (`client_ops.audit_log`, `client_ops::audit_log::event`): 35 event types.

| Event | What it records | Emitted from |
|---|---|---|
| `client_created` | A client + its facilities were imported from Process Street via the "Add to OO" confirmation screen (`api::clients_create`). | `clients_create.rs` |
| `dedup_completed` | A dedup-tool run was exported (`api::dedup::export`/`export_to_dropbox`). | `export.rs, export_dropbox.rs` |
| `unit_group_completed` | A Unit Group run was exported (`api::export::export`). | `export.rs` |
| `sync_completed` | A Process Street sync (scheduled or the manual "Sync Now"/scoped Re-sync trigger) finished successfully -- see `clients::sync`. | `apply.rs, mod.rs` |
| `sync_failed` | A Process Street sync failed partway through -- e.g. | `mod.rs` |
| `merchant_account_linked` | A facility's Merchant Account run was manually linked via the Elavon tab's "link" action (`api::clients_elavon`) -- distinct from `CLIENT_CREATED`'s o | `clients_manual_link.rs, link.rs` |
| `merchant_account_unlinked` | A facility's Merchant Account link was manually removed via the Elavon tab's "Unlink" action (`api::clients_elavon`) -- e.g. | `clients_manual_link.rs, unlink.rs` |
| `elavon_data_resynced` | The Elavon tab's "Resync Elavon Data" action refreshed a linked facility's whole Merchant Account picture from Process Street (`api::clients_elavon::r | `resync.rs` |
| `facility_dropbox_folder_changed` | A facility's linked Dropbox folder was manually changed via the DropBox tab (`api::clients_dropbox_folder`) -- a rare, deliberate action (the wrong fa | `clients_dropbox_folder.rs` |
| `facility_clickup_linked` | A facility was linked to (or re-pointed at) a ClickUp list -- `api::clients_clickup_links`. | `clients_clickup_links.rs` |
| `facility_clickup_unlinked` | A facility's ClickUp link was removed (one facility, or every facility of a company via "Unlink All Facilities"). | `clients_clickup_links.rs` |
| `facility_clickup_duplicate_check_posted` | A duplicate check's results were posted to the facility's ClickUp task (`api::clickup_duplicate_check`): a comment linking the saved file, the actor a | `clickup_duplicate_check.rs` |
| `facility_clickup_comments_copied` | Comments were copied from another facility's ClickUp list onto this facility's tasks (`api::clickup_copy`). | `bulk.rs, copy.rs` |
| `facility_person_added` | A person was added to a facility's Users tab roster (`api::clients_facility_people::add_facility_person`) -- either an "Add User" chip click for a Pro | `add.rs` |
| `facility_person_updated` | A roster person's own name/email/phone/role was edited (`api::clients_facility_people::edit_facility_person`). | `edit.rs` |
| `facility_person_unlinked` | A person was removed from a facility's Users tab roster (`api::clients_facility_people::unlink_facility_person`) -- the gap this event closes: this ac | `unlink.rs` |
| `facility_fees_updated` | A facility's fee policy was edited (`api::clients_facility_policies_edit::update_fees`). | `fees.rs` |
| `facility_taxes_updated` | A facility's tax policy was edited (`api::clients_facility_policies_edit::update_taxes`). | `taxes.rs` |
| `facility_delinquency_updated` | A facility's delinquency policy was edited (`api::clients_facility_policies_edit::update_delinquency`). | `delinquency.rs` |
| `facility_coverage_updated` | A facility's coverage/insurance policy was edited (`api::clients_facility_policies_edit::update_coverage`). | `coverage.rs` |
| `facility_specials_updated` | A facility's specials/promo policy was edited (`api::clients_facility_policies_edit::update_specials`). | `specials.rs` |
| `client_archived` | A client company was archived (`api::clients_companies::archive_company`). | `clients_companies.rs` |
| `client_unarchived` | A client company was unarchived (`api::clients_companies::unarchive_company`). | `clients_companies.rs` |
| `client_implementation_completed` | A client company's implementation was marked completed (`api::clients_implementation_status::mark_implementation_completed`). | `clients_implementation_status.rs` |
| `client_implementation_reopened` | A completed implementation was reopened (`api::clients_implementation_status::reopen_implementation`). | `clients_implementation_status.rs` |
| `client_deleted` | A client company was **permanently** deleted, cascading its facilities/policies/people-links/Elavon data (`api::clients_companies::delete_company`) -- | `clients_companies.rs` |
| `tool_run_deleted` | A facility's tool run (Onboarding Work tab -- Dedup, so far) was deleted (`api::tool_runs::delete_tool_run`) -- the "clear a mistaken run" action, 202 | `tool_runs.rs` |
| `facility_intake_relinked` | A facility's linked Intake run was manually repointed at a different run id (`api::clients_manual_link::manual_link`) -- the Company page's "Manual Li | `clients_manual_link.rs` |
| `client_clickup_parent_changed` | A company's parent ClickUp facility (the source its comments are copied from) was designated or changed (`api::clients_clickup_parent::set_clickup_par | `clients_clickup_parent.rs` |
| `client_clickup_waiver_changed` | A company was marked "no ClickUp project" or that waiver was cleared (`api::clients_clickup_parent::set_clickup_waiver`, or the Create screen's checkb | `clients_clickup_parent.rs, clients_create.rs` |
| `activity_log_exported` | Someone exported the activity log as a PDF (`api::client_ops_activity_logs_export::export_activity_logs`) -- the counterpart of `auth::audit_log::even | `client_ops_activity_logs_export.rs` |
| `qms_tag_created` |  | `client_ops_qms_tags.rs` |
| `qms_tag_updated` |  | `client_ops_qms_tags.rs` |
| `qms_tag_deactivated` |  | `client_ops_qms_tags.rs` |
| `qms_tag_reactivated` |  | `client_ops_qms_tags.rs` |

## `tracing` inventory (non-test call sites, 2026-10-08)

error 465 / warn 112 / info 110 / debug 5.

