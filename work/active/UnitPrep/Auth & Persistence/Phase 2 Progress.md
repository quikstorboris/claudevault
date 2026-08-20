---
date: 2026-07-27
description: "Phase 2 (Core identity & sessions) implementation progress: 11-task plan, dropped axum-login, webauthn-rs API specifics. Tasks 1-10 of 11 done as of 2026-07-30; only the audit-coverage check remains."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — Phase 2 Progress

Phase 1 (schema + RLS + sqlx wiring) is complete — see [[Database Schema]] and [[RLS Implementation]]. This tracks Phase 2 ("Core identity & sessions" in [[Build Plan & Infra Checklist]]), started 2026-07-21, working through an 11-task ordered list one commit-sized chunk at a time.

**Status as of 2026-07-30: tasks 1-10 of 11 done. Only task 11 remains** (audit-event coverage verification, a closing check rather than new implementation).

The invitation flow is now complete end to end — an admin issues, an invitee
redeems — and both halves were verified interoperating against the dev DB
branch.

`AUTH_BOOTSTRAP_ENABLED` **no longer exists** — task 6 deleted it along with
its `auth.resolve_bootstrap_registration` lookup. There is no
env-var-gated unauthenticated path left anywhere in the codebase.

## The 11-task order

1. Auth module skeleton (webauthn-rs + trait) — **done**
2. Session cookie plumbing — **done**
3. Session verification middleware (`resolve_session` + `SET LOCAL` GUCs) — **done**
4. WebAuthn registration ceremony (HTTP endpoints) — **done 2026-07-29**
5. WebAuthn login ceremony (HTTP endpoints) — **done 2026-07-29**
6. Invite acceptance — **done 2026-07-30**. Folded into
   `POST /auth/register/begin` as a third authorization path rather than a
   separate endpoint, so there is one WebAuthn code path. The invite is
   consumed at `/finish` after the credential verifies, **in the same
   transaction as the credential insert** — see the constraint below on why
   any other arrangement is unrecoverable. Retired
   `AUTH_BOOTSTRAP_ENABLED` and dropped
   `auth.resolve_bootstrap_registration`.

   **Verified end to end with a real authenticator 2026-07-30**, not only in
   tests: an invited account enrolled its first passkey through the harness and
   came out `active` with the invite consumed, one credential, and an audit row
   reading `{"invite": true, "device_bound": false}`. The used invite is then
   refused for reuse. Deactivating that account afterwards destroyed its
   credential by trigger while its history survived — so
   "restore requires re-enrolment" is now demonstrated rather than assumed.
7. Invite creation endpoint (admin-only) — **done 2026-07-30**.
   `POST /auth/invites`. **No new database objects were needed** —
   `users_insert_admin_only` and `user_invites_admin_only` already permit
   both writes under an admin identity, so the database enforces admin-ness
   independently of the handler's check, and `user_invites.created_by`
   populates itself from the identity GUC. Reissues for an account that has
   not enrolled, retiring any outstanding invite first — which is what
   **settles the "one outstanding invite per user" question** (see below).
   Accepts no `role` field. Verified against the dev DB branch with a real
   admin session, including a token minted here resolving through task 6's
   own lookup.
8. First-Admin bootstrap path — **done 2026-07-29** (moved ahead of 6 and 7, see below)
9. TOTP fallback enrollment + verification — **done 2026-07-30**.
   Two-step enrolment (`confirmed_at` stays NULL until a real code verifies),
   removal, and an unauthenticated `POST /auth/login/totp`. **The deferred
   encryption-at-rest decision was made here**: ChaCha20-Poly1305 with a
   32-byte key from `TOTP_ENCRYPTION_KEY`, ciphertext bound to its `user_id`
   through the AEAD's additional data, and a version byte for future
   rotation. Explicitly an app-level stopgap — a dump *plus* the key is as
   good as plaintext; real KMS stays trigger-gated. Sign-in is rate-limited
   (5 failures, 15-minute lock), which is affordable **only because TOTP is
   the fallback** — see the constraint below.
10. Logout / sign-out-everywhere — **done 2026-07-30**. Two token-keyed
    `SECURITY DEFINER` functions, so they can only act on the account whose
    live token the caller holds. Also fixed a real bug: the session cookie
    was never actually cleared in a browser (no `Path` on the deletion
    header). **Original constraint, which held:** must be a `SECURITY DEFINER` function that only ever sets `revoked_at = now()`, never clears it — `app_service` no longer has `UPDATE` on `auth.sessions` at all, and re-granting even `UPDATE (revoked_at)` would reintroduce the un-revoke hole. See [[RLS Implementation]].
11. Audit-event coverage verification (closing check, not new implementation) — pending

Explicitly NOT in Phase 2's scope: step-up re-auth (Phase 4) and the Admin UI (Phase 3).

## How each completed task went

The per-task write-ups — decisions, verification, and the mistakes made and
corrected along the way — live in **[[Phase 2 Progress — Task Log]]**. Split out
2026-07-30 when this note crossed the vault's 25KB threshold; content moved
verbatim, nothing trimmed.

- Task 1 — auth module skeleton, and why `axum-login` was dropped
- Task 2 — session cookie plumbing
- Task 3 — session verification middleware
- Task 4 — WebAuthn registration endpoints, plus the bootstrap sequencing problem
- Task 5 — WebAuthn login endpoints, the real browser ceremony, and the pooler bug it uncovered
- Task 8 — first-admin bootstrap, `--reissue-invite`, and the undeletable-user discovery

Also there: the verified webauthn-rs 0.5.5 API specifics (checked against
docs.rs rather than assumed).

## Constraints that bind future work

Collected here because each was discovered mid-task and applies to tasks not yet
written. Ignoring one silently reintroduces something already closed.

- **Task 10 (logout)** must be a `SECURITY DEFINER` function that only ever
  *sets* `revoked_at = now()`. `app_service` has no `UPDATE` on `auth.sessions`
  at all, and re-granting even `UPDATE (revoked_at)` would restore the
  self-un-revoke hole, because a column grant permits writing `NULL` just as
  readily as a timestamp.
- **The TOTP lockout is only affordable while TOTP is a FALLBACK.** Five failed
  codes lock it for 15 minutes, which is safe to expose because the passkey path
  consults none of it — so locking the fallback inconveniences the owner rather
  than denying them their account. **If TOTP ever becomes primary or mandatory,
  that reasoning collapses and the same lockout becomes an account-denial
  primitive.** Stated in the migration too, because whoever makes that change
  will not think to look here.
- **`TOTP_ENCRYPTION_KEY` cannot be rotated without re-enrolment.** Every stored
  secret is encrypted under it, and there is no rotation path yet — the blob
  carries a version byte precisely so one can be added without guessing which
  ciphertexts are which. Changing the key today means every TOTP user re-enrols.
- **Any administrative change to a user** (`role`, `status`, `company`, `email`,
  `deleted_at`, `deletion_reason`) needs a `SECURITY DEFINER` function that
  checks the caller. `app_service` holds `UPDATE` on only `first_name`,
  `last_name` and `job_title`. This is *why* deactivation cannot be a plain
  handler.
- **Never use `INSERT ... RETURNING` on `auth_audit_logs`.** `RETURNING` is
  evaluated against the admin-only SELECT policy, so it fails precisely on the
  no-identity-context events the trail exists for — failed logins. Use
  `auth::audit_log::record`, which already gets this right.
- **All application SQL must be schema-qualified** (`auth.users`, not `users`).
  No `search_path` is set on the connection, deliberately — see
  [[RLS Implementation]] for why a per-connection `SET` would be worse.
- **Never edit a migration that has been applied anywhere**, not even a comment.
  sqlx checksums the whole file and refuses to run afterwards.
- **Enrolled factors are removed on deactivation/soft-delete** by trigger, so
  restoring an account requires re-enrolment. History survives; the credential
  does not.
- ~~**`AUTH_BOOTSTRAP_ENABLED` must be deleted, not just unset, once task 6
  lands.**~~ **Done 2026-07-30**, along with its database lookup. A test now
  asserts the variable is inert, because "delete the gate" is easy to do
  incompletely and a surviving read in one branch would restore an
  unauthenticated path that no test named.
- **Anything that consumes an invite must do so in the same transaction as
  the work the invite authorizes.** `consume_invite` both marks the invite
  used and flips the user to `active`, and `--reissue-invite` refuses an
  account that is not `invited` *as well as* one that already holds a
  credential — so a non-atomic pairing strands the account whichever order
  is chosen, and both stranded states are unrecoverable with current
  tooling:

  | if this failed | leaves | `--reissue-invite` |
  |---|---|---|
  | insert, after consume | `active`, no credential | refuses: not `invited` |
  | consume, after insert | `invited`, has credential | refuses: has a credential |

  This will apply again to task 9 (TOTP enrolment) if TOTP ever becomes a
  thing an invite can authorize.

## See also

- [[Database Schema]] / [[RLS Implementation]] — the tables and functions this code calls.
- [[Architecture]] — original architecture this build implements (note: axum-login was dropped, see above).
- [[Build Plan & Infra Checklist]] — where Phase 2 sits in the overall sequence.
