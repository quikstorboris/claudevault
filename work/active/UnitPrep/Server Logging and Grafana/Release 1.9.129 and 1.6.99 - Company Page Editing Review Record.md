---
date: 2026-10-16
description: "Record of how unitprep-api 1.9.129 and unitprep-ui 1.6.99 were shipped on 2026-10-16: the push of the outstanding API commits, the discovery that the front end's uncommitted work depended on uncommitted backend code, the stranger's-PR review of that backend work, the commits, version bumps, tags and pushes, with the gaps found."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Release record: api 1.9.129 and ui 1.6.99 (company page editing)

Part of [[Server Logging and Grafana - Index]]. Applies the standing habit in [[Patterns]] of reviewing a previous session's uncommitted work like a stranger's PR before shipping it. Later the same day Part 2 shipped api 1.9.130/1.9.131 and ui 1.6.100 (Sentry); that is recorded in [[Session 2026-10-16 (Part 2) — Sentry Setup, Log Correlation, Tools Dashboard]].

## Step 1: push the outstanding API commits (Boris: "push all outstanding api commits coherently")

- Unpushed on `unitprep-api` main at that point (oldest first): `c6c1fe1` dashboard JSON, `3cc7918` extended dashboard, `3b9c01e` ClickUp logging (made by the ClickUp logging session), `6556023` idle-ping `SELECT 1` (made by the database-fix session), `0999d9a` logcli/MCP wrapper scripts and `docs/LOGS.md`.
- "Coherently" was read as: document the unreleased work first. Added `46cbb19` ("Changelog: record the unreleased logging, ClickUp logging and pool-ping changes") under `## [Unreleased]`, **without** bumping the version or tagging (Boris had only said push). The preflight's version/tag advisory ("N commits since v1.9.128 but Cargo.toml still 1.9.128") is advisory and was left for the release step.
- Push: the pre-push hook runs `scripts/preflight.sh` (cargo fmt --check, clippy -D warnings, the fast test suite, cargo audit, gitleaks, version/tag advisory, secret-pattern scan, workflow secret guard, ts-rs drift check, SCHEMA.sql freshness). It passed; `origin/main` went to `46cbb19`.
- Earlier the same day an earlier push had been **aborted by that hook**: `cargo fmt --check` failed on `src/process_street/client.rs` (two line-wrap differences in code committed earlier, not part of the logging change). Fixed with `rustfmt --edition 2021` on that one file (not `cargo fmt`, which would have touched other sessions' uncommitted files) as `543466b`. Clippy, tests, audit and secret scans had all passed on that run.

## Step 2: look at the front end (Boris: "look at what's outstanding for the front end. commit coherently, tag and push")

- `unitprep-ui` had no unpushed commits but **uncommitted work**: modified `app/(app)/clients/[clientId]/info/page.tsx`, `components/clients/ImplementationManagerLine.tsx` (+ its test), `lib/clientsCompanies.ts`, `types/generated/index.ts`; new `components/clients/CompanyInfoForm.tsx` (+ test) and generated types `CompanyInfoFields`, `SetImplementationManagerRequest`, `StaffListResponse`. 5 files changed, 409 insertions, 56 deletions, plus the new files.
- It is one feature, **company page editing**, left uncommitted by an earlier, idle session ("Company page editing and facility management", `local_75ed7d9f-5c78-4f3e-899b-af3d1e3d6367`, last activity 10:42 PT; file times 10:36-10:41 PT; **no vault note and no handoff existed**).
- **It called three endpoints that existed only in uncommitted backend code**: `PUT /clients/{id}/info`, `PUT /clients/{id}/implementation-manager`, `GET /clients/staff`. The backend half was likewise uncommitted: new `src/api/clients_company_edit.rs` (436 lines) and `clients_company_edit_db_tests.rs` (172 lines), plus edits to `src/api/mod.rs`, `src/api/router/routes/clients.rs`, `src/api/router/permission_gate_tests.rs` (+43) and `src/client_ops/audit_log.rs` (+9).
- Shipping the UI alone would have released a UI that 404s against the pushed API. Boris was asked and chose **"Yes: review the uncommitted backend company-edit work, commit it coherently, then commit the front end coherently, bump both versions with changelog entries, tag both, and push both."**
- Before asking, the front end's checks were run on the uncommitted work: `scripts/preflight.sh` passed (tsc, eslint, **vitest 134 files / 1053 tests**, npm audit, gitleaks, version advisory, secret scan, workflow guard, and the check that the generated types match the API, 103 files). The API's own preflight had already run over the working tree (including these files) during the earlier push.

## Step 3: review of the backend half (stranger's-PR style)

What the code does (`clients_company_edit.rs`):
- `PUT /clients/{company_id}/info` saves 14 editable fields (`legal_name`, `corporate_email`, `corporate_phone`, `corporate_address_street/city/state/zip`, `subdomain`, `website_url`, `accepted_payment_methods`, `accounting_basis`, `payment_scheme`, `offers_tenant_insurance_raw`, `insurance_provider`). Values are trimmed and blanks become NULL; a blank legal name is a 400. Only fields that actually changed are written, each is added (DISTINCT) to `manually_edited_fields` so `clients::sync::apply_company_refresh` leaves it alone on the next Process Street sync; a no-op request returns 204 without writing.
- `PUT /clients/{company_id}/implementation-manager` takes `{user_id: Uuid | null}`; the id is validated against `auth.staff_directory()`; `null` clears it and hands it back to sync (sync only fills an empty manager); audited only when the value changes.
- `GET /clients/staff` lists active staff (`auth.staff_directory()`), any authenticated caller, "same reasoning as filter-options".
- Audit: `client_info_updated` (before/after of only the changed fields) and `client_implementation_manager_changed`, recorded **after** the commit.

Checked and found sound:
- **Permissions twice**: the route gate (`RouteAccess::Permission { keys: ["client_ops.perform"], action: ... }` for both PUTs, `Authenticated` for the list) **and** `user.require_permission(...)` inside each handler. `permission_gate_tests.rs` includes both new gated routes (the standing verification-gap tests).
- **Row-level security** through `begin_for` -> `begin_rls_transaction`; the company row is locked `SELECT ... FOR UPDATE` before the write.
- **No SQL injection surface**: the dynamic `UPDATE` uses `QueryBuilder` with column names taken only from the fixed `pairs()` list and `push_bind` for values.
- **No migration needed**: audit `event_type` is a plain `TEXT NOT NULL` column (migrations `20260721194830...` and `20260808130000...`), no CHECK or enum listing event names; the two new names were added to the `event::ALL` list in `audit_log.rs`.
- **Real-DB tests** run on the local `test-db` (`TEST_DATABASE_URL=postgres://app_service:app_service@127.0.0.1:5433/unitprep_test cargo test --bin unitprep -- --ignored company_edit_db`): **3 passed** (`..._saves_and_protects_changed_fields_only`, `..._rejects_a_blank_name_and_an_unknown_company`, `..._rejects_an_unknown_implementation_manager`, which also checks that clearing an unassigned manager is a harmless 204). Plus 3 unit tests (`normalized_trims_and_blanks_become_none`, `changed_fields_lists_only_differences`, `unchanged_input_yields_no_changes`).

Gaps found, **not blocking, not fixed**:
1. No DB test assigns a **real** staff member (needs seeded staff in the test DB).
2. The audit rows carry before/after **values including emails and phone numbers** (PII in the audit table, admin-viewed). Consistent with other audit usage but worth remembering for the PII/retention review.
3. No explicit length limits on the free-text fields beyond the global request-body limit.

Front-end review:
- `ImplementationManagerLine` gains a Change control: loads staff on first use (`GET /clients/staff`), a `select` with a "Not assigned" option, Save/Cancel, inline `role="alert"` error, calls `onChanged` to refetch. `CompanyInfoForm` edits the 14 fields, refuses a blank legal name client-side, shows API errors inline. The info page has an Edit button toggling the form.
- **Buttons not hidden for users without `client_ops.perform`**: elsewhere in the UI some controls are (`ClickUpCompanySection`, `RunActions`, `DedupRunDetails` use `hasPermission(user, "client_ops.perform")`), but the sibling controls on this same page (`ImplementationCompletedToggle`, `ResyncButton`), which also need that permission, are not either. So the new buttons follow this page's own convention (the API refuses and the UI shows the error); **left as is**. Note for later: admin never holds `client_ops.perform`.
- `lib/clientsCompanies.ts` mixes formatter line re-wraps of existing functions with the feature (noted in the commit message).

## Step 4: commits, versions, tags, pushes

API (`unitprep-api`):
- `930dc4d` (13:57 PT) "Let people edit a company's info and Implementation Manager by hand": the six backend files above (module, DB tests, router wiring, permission-gate tests, audit constants).
- `b23af77` (13:58) "Release 1.9.129": `CHANGELOG.md` (the `[Unreleased]` logging entry became `## [1.9.129] - 2026-10-16` plus the company-edit bullet), `Cargo.toml` version 1.9.128 -> 1.9.129, `Cargo.lock` (refreshed by `cargo check`). Tag **`v1.9.129`**, **lightweight** like earlier tags (`git cat-file -t v1.9.128` is `commit`).
- Pushed with `git push origin main v1.9.129` (hook ran preflight, passed; "SCHEMA.sql matches the 117 migrations"): `46cbb19..b23af77`, new tag `v1.9.129`.

UI (`unitprep-ui`):
- `771f90d` (13:58) "Company page: edit the company info and change the Implementation Manager": all front-end files and the three generated types (from api 1.9.129).
- `5fff10c` (13:58) "Release 1.6.99": `CHANGELOG.md` (notes that it needs api 1.9.129 or later), `package.json` line 3 and `package-lock.json` lines 3 and 9 from 1.6.98 to 1.6.99. Tag **`v1.6.99`** (lightweight).
- Pushed API first, then UI: `292a702..5fff10c`, new tag `v1.6.99`; preflight passed including "103 generated type file(s) match".
- Both pushes verified on GitHub (`git ls-remote --tags`), zero unpushed commits afterwards. Tag pushes start the GitHub Actions test runs (Tier-1 CI, as before); **their results were not looked at** by this session.

Afterwards:
- `3db7be1` (14:20) "Docs: record the Grafana alert definitions (error and panic) in LOGS.md" was pushed **without** a version bump or tag (documentation only; the preflight itself says a docs-only push is expected to look unreleased). Boris asked "commit tag push everything"; the no-tag choice was stated and a `v1.9.130` offer made. Boris did not take it up; `v1.9.130` was later cut by Part 2 for Sentry instead.
- Vault commits that day: `088ffb0`, `c7bc330`, `aef9f43`, `28b01cd` (made by the database-fix session), `2cd8f15`, `767222a`. The first vault push attempt was **blocked by the Auto Mode classifier** ("Out-of-Place Publication"); after Boris said it should not be a safety issue and asked to retry, it went through (`dcf51d8..088ffb0`).

## Related

[[Server Logging and Grafana - Index]] · [[Build Timeline 2026-10-16 (Part 1)]] · [[UnitPrep CI-CD Framework]] · [[Production Readiness Checklist]]
