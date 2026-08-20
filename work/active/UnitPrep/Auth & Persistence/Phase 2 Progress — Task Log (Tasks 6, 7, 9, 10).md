---
date: 2026-08-10
description: "Event-log satellite filling the tasks 6/7/9/10 gap in Phase 2 Progress — Task Log; also folds in the logging-roadmap closure, a backend security assessment, a passkey-only readiness review, and a tool-session-ownership note found loose."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — Phase 2 Progress — Task Log (Tasks 6, 7, 9, 10)

[[Phase 2 Progress — Task Log]]'s own "Decisions made during task 1" /
"Task 1 complete" / "Task 2 complete" / "Task 3 complete" sections (continued
in [[Phase 2 Progress — Task Log 2026-07-29]] for tasks 4, 5, 8) give
per-task detail for tasks **1, 2, 3, 4, 5, 8** — but [[Phase 2 Progress]]'s
"How each completed task went" section, which points to both Task Log notes,
lists exactly those six tasks and conspicuously omits **6, 7, 9, and 10**,
even though the core note's own "11-task order" section carries a one-paragraph
inline summary for each of them. This note fills that gap: it holds the
first-hand, verbatim session write-ups for tasks 6, 7, 9 and 10, which existed
all along but had drifted into `inbox/` and the bare `work/active/UnitPrep/`
root under auto-generated filenames, never linked from anything.

While assembling this, four more first-hand notes turned up in the same
drifted state, covering closely related work from the same and following
days. Two are squarely part of this workstream (the logging-roadmap closure
that immediately preceded task 6, and a backend-only security assessment
performed the same evening as tasks 9/10) and are included as full entries.
Two are adjacent but not literally about tasks 6/7/9/10: a passkey-only
enforcement readiness assessment (auth-adjacent, done the next day), and a
tool-session-ownership revisit for the Onboarding Orchestrator's advisory
tooling (**not** part of the WebAuthn/TOTP auth build at all — it concerns
`InMemorySessionStore` attribution for `unit-group`/`dedup` tool calls).
Both are included here as additional dated entries rather than split into
two more one-off notes, per the instruction to consolidate drifted
single-session write-ups rather than fragment them further. Read the intro
line of each entry below before assuming it's about Phase 2.

All entries are in chronological order by each source note's own trailing
`_Recorded ...Z_` timestamp. Content is moved verbatim — nothing trimmed,
nothing paraphrased away — reorganized only under short bold labels mirroring
each source's own section headings.

---

## 2026-07-30 19:57 UTC — Logging roadmap closed out, and two om bugs fixed

Closed all three "do with the next touch" items from the approved logging
roadmap in unitprep-api (commit 86f9a6a). The headline item was a genuine
bug: a refused passkey registration was recorded nowhere at all, while a
failed login wrote an audit row, so probing registration across an address
list was untraceable. Also correlated both halves of a WebAuthn ceremony and
captured `device_bound` at enrolment. Separately fixed two bugs in the om MCP
server itself, and established this laptop's hard resource limits the hard
way. (The om-MCP-server and laptop-resource-limit material below is *not*
UnitPrep auth work — it's included verbatim because it was recorded in the
same session note, not because it belongs to this workstream.)

**What changed:**

- `src/auth/audit_log.rs` - added `event::REGISTRATION_FAILED`, the registration-side counterpart of `LOGIN_FAILED`
- `src/api/auth_register.rs` - new `reject_bootstrap()` logs a warn and writes the audit row before returning the unchanged opaque 403; all three refusal paths route through it so a fourth reason cannot be silently unrecorded. `register_begin` gained a `HeaderMap` for `user_agent`; `register_finish` writes `credential_rejected` on failed verification and threads `correlation_id` through all four log lines
- `src/auth/registration_ceremony.rs` + `authentication_ceremony.rs` - added `correlation_id: Uuid` generated in `new()`, with tests that it differs from the ceremony (cookie) id and is unique per ceremony
- `src/api/auth_login.rs` - `correlation_id` on every log line and in the metadata of `login_succeeded`, `login_failed` and the credentials-removed-mid-ceremony row
- vault `lib/mcp-qmd-client.ts` - pass `rerank: false` to qmd's query tool
- vault `lib/mcp-capture.ts` - root check now matches the whole declared root instead of only the first path segment, plus a regression test using multi-segment roots
- vault `brain/Gotchas.md` and `brain/Skills.md` - the rerank diagnosis, the corrected retry advice, and the machine's resource limits
- unitprep-api - annotated tags v1.1.1 through v1.1.5 created retroactively, local only, each verified against `Cargo.toml` at that commit

**Decisions:**

- Did NOT log the ceremony id despite the roadmap asking for it: that id IS the ceremony cookie's value, so logging it would put a live bearer token into ops output and contradict the same note's own "never log tokens" rule. Added a separate server-only `correlation_id` instead. Supersedes roadmap item 2 as written.
- One event type (`registration_failed`) with a reason in metadata for both the refused `/begin` and the failed `/finish`, mirroring how `login_failed` already carries distinct reasons. The join an operator wants is "all registration failures".
- Every refusal routes through a single `reject_bootstrap()` rather than leaving `bootstrap_rejected()` directly callable - the bug being fixed was "a path that refuses without recording", so the structure should make that unrepresentable.
- Attempted email recorded in audit metadata but never in the tracing line: the audit table is admin-only and an unmatched address is data about an attempt, whereas ops logs ship somewhere with weaker access control.
- Rejected raising om's `CALL_TIMEOUT_MS`, at Boris's direction - it converts a failure into a two-minute block and hides that the cost is per-candidate and grows with the vault. Disabled reranking instead, which is what qmd's own docs recommend for CPU-only machines.
- Tagged v1.1.1-v1.1.5 but deliberately not v1.2.0, since 1.2.0 is still the working version and tagging it now would understate the release.

**Learned:**

- om's `record_work` could not target any multi-segment exposed root. `resolveDestination` compared only the FIRST path segment against each full root string, so `folder: 'work/active'` was refused verbatim while `'work/active'` was listed as allowed, and the error blamed "work". Nine of eleven roots were unreachable and calls fell through to caller-identity routing or the inbox. It survived because every root in the test fixture happened to be a single segment - the one shape the broken comparison handles.
- qmd caches query-expansion output and rerank scores per query, so a hard latency ceiling masquerades as flakiness: re-running a failed query returns in seconds, which makes "just retry it" look like a remedy while the real per-candidate cost stays invisible. Any timing measurement must use a genuinely NOVEL query - an early "structured queries are fast (16s)" reading here was contaminated by a warm rerank cache and would have produced the wrong fix.
- Reranking costs roughly 2 seconds PER CANDIDATE with no discrete GPU, at a default candidate limit of 40. That is the entire reason om search never worked, and it is hardware-bound rather than tunable.
- A stale server binary produced a convincing false negative for the second time: "zero audit rows, no log lines" looked like the fix failing, but `cargo run` had failed to bind port 8080 because a pre-fix binary from that morning was still serving. The health check passed and proved nothing. The bind error was sitting in the log tail - read that before believing a negative.
- Backgrounding a process inside `wsl -e bash -lc '... &'` does not survive the invocation; it needs `setsid nohup ... < /dev/null &`. Without it the next call sees connection-refused with no server and no error.

**Verification:**

"unitprep-api: 371 workspace tests passing (366 baseline plus 5 new), cargo fmt clean, clippy unchanged at its 2-warning baseline. Live against the dev Neon branch with a confirmed-fresh binary: audit rows 8 -> 11; all three refusal reasons wrote a row carrying the probed address while returning byte-identical 403 bodies; a real two-request login ceremony logged one correlation_id across both halves and into the audit row, with the ceremony cookie's value (1e932acb...) confirmed different from the logged id (c63573a8...) and absent from the logs; no email appears anywhere in tracing output. Vault: om search returns a novel query immediately with a 91% on-topic top hit; mcp-capture tests 31/31 and mcp-qmd-client 34/34; both fixes mirrored byte-identically into `.shardmind/templates/`. Caveat stated honestly: the full vault suite showed varying numbers of failures across runs in the load-sensitive subprocess groups, and that instability is a symptom of the machine being out of memory, not of these changes - none of the failures were in the files touched."

**Open:**

- Task 6, invite acceptance, is NOT started. It remains the next build step and still retires `AUTH_BOOTSTRAP_ENABLED`.
- `credential_rejected` and `device_bound` in `passkey_registered` metadata are covered by unit tests and the identical code path but NOT by a live run: both need a real authenticator plus a bootstrap-eligible user, and dev has one user who already holds two credentials. Creating a temp user would leave a permanently undeletable row, so it was not done unilaterally.
- v1.1.1-v1.1.5 tags are local only, not pushed.
- Ollama autostart is disabled and its processes stopped, but 3.68GB of models remain on disk and the app is still installed; removing them is Boris's call. The `ocx-llama3-2-latest` agent definition becomes dead weight if ollama goes.
- The vault's git repo has zero commits. Boris has decided deliberately not to version the vault - do not raise it again.
- Roadmap items 4 (request ids) and 5 (ceremony duration) remain trigger-gated as agreed.

**Related (original links):** [[Phase 2 Progress]], "Logging and Observability" (no note yet at the time — now [[Logging & Observability]]), [[Gotchas]]

---

## 2026-07-30 20:24 UTC — Task 6 shipped: invite acceptance, and the bootstrap path deleted

Phase 2 task 6 landed as commit fa764e6. An invited user now enrols their
first passkey by presenting their invitation token to `POST
/auth/register/begin`, finishing signed in. `AUTH_BOOTSTRAP_ENABLED` and
`auth.resolve_bootstrap_registration` are both deleted outright, so no
env-var-gated unauthenticated path remains anywhere. Phase 2 is now tasks 1-6
and 8 of 11 done; task 7 (invite creation) is next.

**What changed:**

- `migrations/20260730120000_invite_registration_lookup.{up,down}.sql` - adds `auth.resolve_invite_registration(BYTEA)` returning `user_id`/`email`/`first_name`/`last_name`, guarded on invite unused + unexpired + user still `'invited'` + zero credentials; drops `auth.resolve_bootstrap_registration(citext)`. The down migration recreates the dropped function verbatim so a down/up cycle lands on the same definition rather than a paraphrase.
- `src/api/auth_register.rs` - the unauthenticated branch now takes `invite_token` instead of `email`; the `email` field is gone from `RegisterBeginRequest` entirely. `bootstrap_enabled()` deleted. `bootstrap_rejected`/`reject_bootstrap` renamed `registration_unavailable`/`reject_registration`, and the latter now takes `actor_user_id` so post-resolution failures can name the user. `insert_credential` became `enrol_credential`, which wraps the credential insert and `consume_invite` in ONE transaction and returns `Ok(false)` when the invite is no longer consumable.
- `src/auth/registration_ceremony.rs` - `is_bootstrap: bool` became `invite_token_hash: Option<Vec<u8>>`, carrying the hash finish needs to consume rather than merely asserting a path. Only ever the hash, never the raw token.
- `src/bootstrap.rs` + `README.md` - doc corrections; the README now documents redeeming the printed token against `/auth/register/begin` and carries a Removed note for `AUTH_BOOTSTRAP_ENABLED`.
- `CHANGELOG.md` - Added/Removed entries under Unreleased.

**Decisions:**

- Folded acceptance into `POST /auth/register/begin` as a third authorization path rather than adding `POST /auth/invite/accept`. Registration already modelled "who is this ceremony for" as one resolved decision with variants, so the whole WebAuthn orchestration is shared; a separate endpoint would have meant a second place that starts registration ceremonies. Boris delegated this call with the criteria "best practices, elegance, high security, efficiency".
- The invite is consumed at `/finish` AFTER the credential verifies and IN THE SAME TRANSACTION as the credential insert. This was chosen against specific failure modes, not for tidiness: consume-then-insert strands the account `active` with no credential, insert-then-consume strands it `invited` with a credential, and `--reissue-invite` refuses BOTH of those states, so each non-atomic ordering is an unrecoverable lockout. One transaction leaves only "enrolled and active" or "untouched and retryable", which is why cancelling a Windows Hello prompt now costs the user nothing.
- Dropped `auth.resolve_bootstrap_registration` rather than leaving it orphaned (Boris's explicit choice of the fullest cleanup option). Left in place it would have been a callable SECURITY DEFINER function matching any active credential-less user by email alone, with its only guard - the env var - removed in the same change.
- The new lookup returns the account's real email so the address WebAuthn shows in the authenticator prompt cannot be influenced by the client. The caller supplies only a token.
- Nothing derived from the invite token is ever logged or audited - not the raw value, not the hash. An audit trail holding live tokens is a credential store under another name. The deliberate consequence is that a refusal with an unrecognised token identifies no user, because there is none to identify.
- Replaced the two tests asserting the env gate held shut with one asserting the variable is now inert, plus one asserting a refusal never echoes the submitted token. "Delete the gate" is easy to do incompletely, and a surviving read in one branch would restore an unauthenticated path that no test named.

**Learned:**

- `consume_invite` returning NULL is a normal, reachable outcome rather than an error: the invite expired mid-ceremony or a concurrent attempt won. It maps to a rollback plus the same opaque 403 as any other refusal, with reason `invite_consumed_elsewhere`. Treating it as an error would have produced a 500 for an ordinary race.
- Verifying database-layer guards inside a `BEGIN ... ROLLBACK` block is the right tool when a project's own data model makes test rows hard to remove - here a user acquires audit history and then cannot be hard-deleted by anyone. Ten guard clauses were exercised against real rows with zero residue.
- A successful `/auth/register/begin` writes no audit row, only a tracing line, which is what made it safe to create a committed probe user for the HTTP happy-path check and then hard-delete it afterwards. Worth knowing before creating test accounts on any branch.
- psql treats "double quotes" as identifiers, so a shell-nested query using them fails with 'column ... does not exist' rather than a syntax error - which reads like a schema problem. Pass SQL via `-f` from a file instead of fighting quote layers through `wsl -lc`.

**Verification:**

"372 workspace tests pass (198 in the binary, up 1 net: two env-gate tests removed, three added), cargo fmt clean, clippy unchanged at its 2-warning baseline. Database layer verified against the real dev branch inside a transaction that rolled back, leaving no residue: a live invite resolves with the right email and name; unknown, expired, already-used, no-longer-invited and already-has-a-credential each resolve to zero rows; consume_invite returns the user id and flips status to active while marking the invite used; a second consume of the same invite returns NULL; the invite no longer resolves afterwards; and after ROLLBACK the probe user does not exist. Over HTTP against a freshly started binary: a missing token, a garbage token, and the retired `email` field all return byte-identical 403s and write audit rows carrying only a reason. A real token returned a genuine WebAuthn challenge with is_invite=true and a correlation id, and the invite was confirmed STILL unconsumed with the user still 'invited' afterwards - the central design property. The probe account was then hard-deleted and dev holds one user again; the dev server was stopped and port 8080 confirmed closed."

**Open:**

- The `/finish` half is NOT verified end to end: it needs a real authenticator. The consume-in-transaction path is covered by unit tests plus SQL-level checks of resolve/consume, not by a real ceremony. Next real browser enrolment should confirm it, and would also finally observe `device_bound` landing in `passkey_registered` metadata.
- Dev is now ONE migration ahead of the parked prod branch (dev 24, prod 23) - the gap being `20260730120000_invite_registration_lookup`. Not yet worth a sync; this is the counter to watch.
- Task 7 (invite creation, admin-only) is next. Until it exists, invites can be redeemed but only minted by the bootstrap-admin CLI.
- The prod bootstrap invite expired unused as predicted; `--reissue-invite` mints a fresh one when prod is actually needed.
- `app_service` still has no password on the prod branch - Boris's own credential to add, not needed until a deployment exists.

**Related (original links):** [[Phase 2 Progress]], "Auth and Persistence Index" (no note yet at the time — now [[Auth & Persistence Index]]), [[Database Schema]], [[RLS Implementation]]

---

## 2026-07-30 22:01 UTC — Task 7 shipped: admin invite creation, completing the invitation flow

Phase 2 task 7 landed as commit a887afe. `POST /auth/invites` lets an
administrator issue an invitation, completing the flow task 6 started — an
admin issues, an invitee redeems, and both halves were verified interoperating
against the dev DB branch. Phase 2 is now tasks 1-8 of 11 done; the admin
panel's agreed trigger has fired.

**What changed:**

- `src/api/auth_invites.rs` (new) - `POST /auth/invites`. Creates the account as `'invited'` or reissues for one that has not enrolled, retiring outstanding invites first. Validates email/name/company before opening a transaction, reusing bootstrap's `VALID_COMPANIES` so the two tools cannot disagree. Returns the raw token once.
- `src/auth/audit_log.rs` - added `event::INVITE_CREATED` and a named `Subjects` value (`anonymous` / `by(actor)` / `.about(target)`) replacing the bare actor parameter; the INSERT now writes `target_user_id` too.
- `src/api/auth_register.rs` + `auth_login.rs` - all eight audit call sites converted to `Subjects`.
- `src/api/mod.rs` - route wired, with a comment that authorization is the extractor plus the RLS policies rather than any middleware layer.
- `src/bootstrap.rs` - `VALID_COMPANIES` and `invite_hours()` made `pub` so the endpoint shares one definition of "valid company" and "how long is an invite valid".
- `CHANGELOG.md` - Added entries for the endpoint and for `target_user_id`, including the deletion consequence.

**Decisions:**

- No new database objects, verified rather than assumed: `users_insert_admin_only` and `user_invites_admin_only` already permit both writes under an admin identity, so the handler runs inside `begin_rls_transaction(.., Role::Admin)` and the DATABASE enforces admin-ness independently of the handler's own check. Both kept deliberately - the handler gives a clean 403, the policy holds if a refactor drops it.
- `user_invites.created_by` left to its column default, which reads `app.current_user_id` and so records the issuing admin by itself. Binding it explicitly would duplicate the schema's own answer.
- Retiring outstanding invites on every issue SETTLES the previously-undecided "one outstanding invite per user" question with no partial-unique constraint. The invariant is maintained by every path that issues rather than enforced against paths that would break it. The argument rests on there being no third issuing path, so revisit if one appears.
- No `role` field accepted. Only `'admin'` exists, so accepting one would add a client-controlled path to choosing a new account's privilege level for zero capability gained. The handler's role check is a `match` rather than an `if`, so a second variant becomes a compile error instead of a silently permissive endpoint.
- Admin-facing refusals say WHY (409 naming the passkey count or the wrong status), unlike the opaque 403s on the unauthenticated endpoints. Anti-enumeration reasoning applies to anonymous callers; applying it to an admin who can already list users protects nothing and makes the tool worse.
- Actor and target are passed as a named `Subjects` value rather than two adjacent `Option<Uuid>` parameters. A transposition there would misattribute an administrative act to the person it was performed on, compile cleanly, and leave a row with nothing visibly wrong. Making it unrepresentable beat documenting it.
- Recording `target_user_id` accepted despite making invited accounts permanently un-hard-deletable (both audit FKs are RESTRICT, the table is append-only). An invitation is a real act about a real person and an admin issuing many is exactly what an audit trail should surface. The cost is that a mistyped address leaves a permanently soft-deletable-only row.

**Learned:**

- Issuing an invitation now makes that account permanently un-hard-deletable, where previously only DOING something had that effect. Verified by attempting the delete: it fails on `auth_audit_logs_target_user_id_fkey`. Worth knowing before creating test accounts through the API - use RFC 2606 addresses (`@example.com`) and expect to soft-delete rather than remove.
- A soft-deleted user keeps its outstanding invite row with `used_at` still NULL, so a naive "live invites" query counts it. Not a hole - `resolve_invite_registration` checks both status and `deleted_at`, and the token was confirmed unredeemable - but the deactivation trigger retires enrolled factors and does NOT retire pending invites. Minor consistency item rather than a bug.
- `auth.user_deletion_reason` has exactly two values, `'offboarding'` and `'emergency'`. There is no generic "other", so a test cleanup has to pick one of the two real reasons.
- An admin session can be minted directly with `auth.create_session` (the same function login calls) plus a sha256 of a random token as the cookie value. That makes authenticated endpoints testable over HTTP with no authenticator and no browser - far cheaper than driving the harness, and genuine rather than mocked.

**Verification:**

"375 workspace tests pass (201 in the binary, up 3), cargo fmt clean, clippy unchanged at its 2-warning baseline. Live against the dev DB branch with a real admin session minted via auth.create_session: unauthenticated refused 401; unknown company refused 400 naming the valid options with no account created; valid call returned 201 and its token's hash resolved through auth.resolve_invite_registration, the first interoperation of both halves of the flow; created_by came back equal to the acting admin without being bound; 'QuikStor' normalised to the enum value and job_title landed; reissue returned reissued:true for the same user id leaving exactly one live and one retired invite, with the first token confirmed dead rather than merely superseded; inviting an account holding passkeys returned 409 naming the count; both audit rows carried actor=admin, target=invitee and the correct reissued flag. The permanence consequence was verified by attempting the hard delete and reading the FK refusal. Test account soft-deleted, server stopped, port 8080 confirmed closed."

**Open:**

- FLAGGED FOR BORIS, not yet decided: whether recording `target_user_id` is worth invited accounts becoming permanent. The alternative is putting the invitee id in metadata, which keeps them deletable but loses the queryable actor-vs-target distinction and the FK's referential guarantee. Recommended keeping as-is; it is a cheap change if he disagrees.
- The admin panel's agreed trigger (after tasks 6-8) has now fired. Scope was pre-agreed as Users + Authentication Policy, with Audit Logs a separate effort and Groups deferred.
- Remaining Phase 2: task 9 (TOTP), 10 (sign-out, which must be a SECURITY DEFINER function that only ever SETS `revoked_at`), 11 (audit-coverage check). No dependency between them and the admin panel, so ordering is open.
- No email is sent - the admin must deliver the token manually until an ESP exists. Notify-on-enrolment also waits on that.
- Deactivation not retiring pending invites (see above) - decide whether the trigger should extend to invites.
- Dev DB branch remains exactly ONE migration ahead of the parked prod DB branch; task 7 added none.

**Related (original links):** [[Phase 2 Progress]], [[RLS Implementation]], [[Database Schema]]

---

## 2026-07-30 22:55 UTC — Tasks 9 and 10 shipped: TOTP fallback and sign-out — Phase 2 is one closing check from done

Phase 2 tasks 10 (sign-out) and 9 (TOTP) landed as commits 1431576, 3c5967e
and 73b9966. Sessions can now be revoked, and TOTP works as a fallback factor
for a device with no passkey. Only task 11 remains, which is an
audit-coverage verification rather than new implementation. Three real bugs
were found along the way, one of them mine.

**What changed:**

- `migrations/20260730140000_revoke_sessions` - `auth.revoke_session` and `auth.revoke_all_sessions_for_token`, both SECURITY DEFINER and both keyed on a TOKEN HASH rather than a user id
- `src/api/auth_logout.rs` (new) - `POST /auth/logout` and `/auth/logout/everywhere`, deliberately not behind the `AuthenticatedUser` extractor
- `src/auth/session_cookie.rs` - fixed the deletion header carrying no Path, switched from `remove()` to adding an expired cookie, and added tests that assert the emitted wire attributes
- `migrations/20260730150000_revoke_sessions_on_deactivation` - the deactivation trigger now revokes sessions too, plus a backfill
- `src/auth/totp.rs` (new) - secret generation, ChaCha20-Poly1305 encryption at rest bound to `user_id` via AEAD additional data, RFC 6238 verification, 10 unit tests including the RFC's own vector
- `src/api/auth_totp.rs` (new) - enroll/begin, enroll/confirm, disable, and `POST /auth/login/totp`
- `migrations/20260730160000_totp_login_support` - `failed_attempts`/`locked_until` columns plus `resolve_totp_candidate`, `record_totp_failure`, `record_totp_success`
- `src/auth/audit_log.rs` - `SESSION_REVOKED` plus four TOTP event types
- `Cargo.toml` - totp-rs (default-features off, to avoid pulling qrcode/image), chacha20poly1305, hex
- `dev-tools/auth-test.html` - TOTP controls and sign-out buttons; secret display built with DOM calls rather than innerHTML
- `.env.local` - `TOTP_ENCRYPTION_KEY` generated (gitignored)

**Decisions:**

- Both session-revocation functions take a TOKEN HASH, never a user id, which makes them self-authorizing: they derive the user from the presented session, so "sign this other user out of everything" is not a request that can be expressed rather than one guarded by every handler passing the right id. The admin-facing user-id form belongs with the admin panel, checking the caller.
- Sign-out-everywhere requires the presented session to be currently valid; plain sign-out does not. Ending an already-dead session is harmless, but a leaked expired cookie must not be usable to sign someone out of every device.
- Neither logout endpoint sits behind the auth extractor. Logging out must succeed with a stale or absent cookie, or the moment a user most needs the cookie gone is the moment it 401s.
- TOTP encryption at rest (the decision the schema deferred to task 9): ChaCha20-Poly1305, 32-byte key from `TOTP_ENCRYPTION_KEY`, ciphertext bound to its `user_id` through the AEAD's additional data so a secret grafted onto another row fails to decrypt, and a version byte so key rotation is possible later without guessing which ciphertexts are which. Labelled an app-level stopgap: a dump plus the key is as good as plaintext, and real KMS stays trigger-gated.
- TOTP enrolment is two steps with `confirmed_at` NULL until a real code verifies. Otherwise a user believes they have a working fallback while having mis-scanned the secret, and finds out when they need it and have nothing else.
- TOTP sign-in is rate-limited at 5 failures then a 15-minute lock, which is only affordable BECAUSE TOTP is the fallback - the passkey path consults none of it, so locking inconveniences rather than denies. Recorded as a constraint: if TOTP ever becomes primary or mandatory, the same lockout becomes an account-denial primitive.
- Deactivation now revokes sessions, completing what the trigger was already named after. The UPDATE is inline rather than calling the task 10 functions, because those are token-keyed by design and adding a user-id-keyed variant would create the exact denial-of-service primitive they avoid.

**Learned:**

- THE SESSION COOKIE WAS NEVER ACTUALLY CLEARED IN A BROWSER. `clear_session_cookie` emitted a Set-Cookie with no Path, and per RFC 6265 that defaults to the requesting URI's DIRECTORY rather than everywhere - so clearing from `/auth/logout` produced a deletion scoped to `/auth`, which never matched the real cookie's `Path=/`. Nothing was exposed since the session is revoked server-side, but the browser kept presenting a dead token and every later request 401'd with a cookie attached. It survived because the existing test asserted "no longer reads back" against an in-memory jar, which models NO path semantics and passes either way.
- `cookie::CookieJar::remove()` only emits a deletion in the delta if a cookie of that name was an ORIGINAL parsed from the request. Remove something merely added, or absent, and nothing is emitted at all - so "logout always clears" was false exactly when the jar had not parsed the cookie. Adding an already-expired cookie instead makes it unconditional. Consequence: after clearing, reading the jar yields `Some("")` rather than `None`, so the token must be read BEFORE clearing.
- My own bug, caught by the new tests: the first draft of `sign_out` cleared the cookie before reading the token, so sign-out cleared the browser's cookie and never revoked the session server-side - invisible from the client because the response is identical either way.
- STALE BINARY, THIRD OCCURRENCE. `cargo test` builds the test harness, NOT `target/debug/unitprep`. A verification run reported `revoked_count 0` and no clearing header purely because the running binary predated the fix. The check that settles it: `find src -name '*.rs' -newer target/debug/unitprep` must print nothing before trusting any live run.
- `pkill -f 'target/debug/unitprep'` matches its own shell command line and kills the invoking shell (exit 15) as well as the server. Use `pkill -x unitprep`, or resolve the PID from the port with `ss -ltnp`, which is also how to kill one instance while leaving another running.
- Verifying TOTP against an INDEPENDENT implementation is worth the effort: computing RFC 6238 codes in Python (hmac-sha1, 20 lines) and checking the Rust server accepts them proves interoperability, whereas asking the server to verify its own generated code only proves self-consistency. It also makes the whole flow testable with no authenticator app and no browser.

**Verification:**

"395 workspace tests, fmt clean, clippy clean, and ZERO build warnings for the first time (the old two-warning baseline was `clear_session_cookie` and `SESSION_COOKIE_NAME`, both waiting on task 10). Sign-out: eight SQL properties inside a rolled-back transaction including that re-revoking does not move the timestamp and that `app_service` still has neither table- nor column-level UPDATE on `auth.sessions`; then end to end - one session revoked and the others left alone, a dead token revoking nothing and unable to trigger sign-out-everywhere, no-cookie still returning 200 with the clearing header, and a live token signing the account out of all 8 sessions. TOTP: 10 unit tests including RFC 6238's published vector, then 16 scenarios end to end with codes computed by an independent Python implementation - 24 assertions, all passing - covering unconfirmed-credential refusal, plaintext absence from the stored column, clock skew accepted at -1 step and refused at -50, the five-failure lock, the correct code refused while locked, a locked attempt not extending the lock, the passkey path still working during a TOTP lockout, and unknown-address versus wrong-code responses identical byte for byte."

**Open:**

- Task 11 is all that remains in Phase 2: audit-event coverage verification, a closing check rather than implementation. Then the admin panel, whose trigger fired at task 8.
- Dev DB branch is now FIVE migrations ahead of the parked prod DB branch (28 vs 23). This has crossed from "not worth it" into the range where a sync is worth recommending.
- `TOTP_ENCRYPTION_KEY` has no rotation path. Every secret is encrypted under it, so changing it today means every TOTP user re-enrols. The blob's version byte exists so rotation can be added without guessing which ciphertexts are which.
- Three commits are unpushed as of this note (1431576, 3c5967e, 73b9966).
- The harness page still needs a QR renderer if scanning is ever preferred to typing the base32 secret; it ships no libraries deliberately.
- TOTP was verified with scripted codes, not with a real authenticator app - Boris was going to exercise it through the harness.

**Related (original links):** [[Phase 2 Progress]], [[Architecture]], [[Database Schema]], [[RLS Implementation]]

---

## 2026-07-30 23:29 UTC — Auth security assessment (backend-only, 2026-07-30)

Reviewed unitprep-api authentication end-to-end (handlers, ceremonies,
sessions, WebAuthn, TOTP, invites, RLS, SECURITY DEFINER functions, audit
trail) against the live Neon schema export. Overall: strong,
defense-in-depth design for a passkey-first backend; not yet fully
audit-ready for production without rate limiting, session/IP hardening, and
tool-route auth gating. *(This file was found sitting in a stray
`work/active/UnitPrep/Auth-Persistence/` folder — no ampersand, no space —
almost certainly an accidental duplicate of this real `Auth & Persistence`
folder. Its content is folded in here verbatim; the stray folder has been
deleted, see this vault-hygiene pass's final report.)*

**What changed** *(this was a review, not an implementation session — "what changed" here means what was read/checked)*:

- Read auth modules and HTTP handlers under `src/auth` and `src/api/auth_*.rs`
- Cross-checked Neon schema dump for RLS policies, grants patterns, and SECURITY DEFINER functions
- Compared findings against vault notes on RLS column privileges, audit asymmetry, and invite registration gotchas

**Decisions:**

- Assessment is evaluative only — no code changes. Primary question was security quality of the auth model, not bug hunting.
- TOTP-as-fallback-first-factor is treated as an intentional product decision already documented in code, not a defect, while still called out as the weakest factor for auditors.

**Learned:**

- Tool endpoints remain unauthenticated; auth exists but does not yet gate the product surface.
- No application-level rate limiting on unauthenticated auth endpoints.
- Ceremony state is process-local (in-memory), which is correct for security of challenge state but constrains multi-instance deployment.

**Verification:**

Code and migration review only; no live exploit tests or penetration exercise. Schema cross-check against Neon export 2026-07-30.

**Open:**

- Rate limiting / abuse controls on login, TOTP, register, invite redeem
- Whether tool routes should require `AuthenticatedUser` before frontend ships
- TOTP used-code replay window, KMS for TOTP key, session idle/absolute policies, `SameSite=Strict` evaluation
- Formal threat model / control matrix for external audit

**Related (original links):** "Testing a WebAuthn invite/registration flow: a stale session cookie silently hijacks the ceremony, and incognito hides password-manager passkeys" (no note yet), "Raise logging improvements while already touching that code — and judge the audit trail separately from the ops log, because a gap hides between them" (no note yet — now covered by [[Logging & Observability]]), "Row-level security cannot restrict which COLUMNS an update touches — that needs column-level privileges, and a blanket table GRANT silently re-opens the hole" (no note yet — now covered by [[RLS Implementation]])

*Note on attribution: this source file's frontmatter read `source_repo: unknown` and its trailing timestamp read `from `unknown``, unlike every other source folded into this satellite (which read `bmaksimov`). Preserved as found; not corrected, since it isn't independently verifiable which session recorded it.*

---

## 2026-07-31 15:34 UTC — Passkey-only enforcement readiness assessment: recovery-path gap, QR codes, frontend scope

Reviewed vault and live code state to answer Boris's questions about going
passkey-only (no passwords, TOTP demoted to fallback) and enforcing logins.
Confirmed via direct repo inspection that unitprep-ui has zero auth code
today, and that unitprep-api already emits the `otpauth://` URI needed for
TOTP QR codes even though no QR renderer exists yet. Cross-checked GitHub
Copilot-style LLM review feedback against the vault's own 2026-07-30 security
assessment and found strong overlap on rate limiting.

**Decisions:**

- TOTP QR codes: recommended as a frontend-only addition, not a backend change. The original totp-rs default-features-off choice (avoiding qrcode/image Rust crates) does not block a lightweight client-side JS QR renderer, since `auth_totp.rs`'s `EnrollBeginResponse` already returns the `otpauth://` URI needed.
- Rate limiting on auth endpoints is the single GitHub-LLM-suggested improvement that best fits the existing framework: it was independently flagged in the vault's own 2026-07-30 security assessment (no application-level rate limiting on login/register/invite-redeem), so it has two independent confirmations and is a concrete, scoped engineering task rather than a process/organizational one.
- Enforcing logins broadly is not yet recommended: backend tool routes are not gated behind `AuthenticatedUser` (per the 2026-07-30 assessment), Phase 2 task 11 (audit-coverage verification) is still open, no rate limiting exists, and the frontend has zero auth integration to enforce against.
- Account-recovery / break-glass for an already-enrolled user who loses their only device is an unbuilt gap, not merely an unimplemented nice-to-have: `--reissue-invite` explicitly refuses an account that already holds a credential, so there is currently no path back in for that user short of manual DB intervention. This becomes materially more urgent once passwords are fully off the table as a fallback and logins are enforced.

**Learned:**

- unitprep-ui has no auth code whatsoever as of 2026-07-31: no `middleware.ts`, no login/invite/TOTP pages, no WebAuthn client library in `package.json`, and the only `app/api` route is a health-check proxy. Frontend auth work is fully greenfield, not an extension of partial work.
- The QR-code gap is purely presentational: the backend was already designed to hand the frontend an `otpauth://` URI specifically so it could be "normally rendered as a QR code" (per the doc comment in `EnrollBeginResponse`) - the dependency-minimization decision on the Rust side never actually required skipping QR support end-to-end, only skipping it in Rust.

**Verification:**

Read unitprep-api `src/api/auth_totp.rs` directly (`EnrollBeginResponse` doc comment confirms `otpauth://` URI already returned). Grepped unitprep-ui repo directly via WSL: no `middleware.ts`, no login/auth pages found, no webauthn/auth packages in `package.json`, only `app/api/health/route.ts` exists as a Next.js API route.

**Open:**

- Lost-device / break-glass recovery flow for an active user with an existing credential is undesigned in code (only sketched in Architecture.md) and should likely be prioritized before enforcing logins broadly, given no password fallback exists.
- Single-admin lockout risk: only one Admin (Boris) exists; whether the first-admin bootstrap CLI is safely re-runnable as an admin-only break-glass path if he loses his own device is unconfirmed.
- Rate limiting implementation approach (e.g. tower-governor or similar) not yet chosen.
- Frontend build scope for enforcing logins: WebAuthn client library choice, Next.js API relay routes for each backend auth endpoint, `middleware.ts` route-gating strategy, session/user context provider, TOTP enrollment + login-fallback UI, invite redemption page, and Admin>Security>Users UI - all still to be scoped into concrete tasks.

**Related (original links):** [[Architecture]], [[Build Plan & Infra Checklist]], [[Phase 2 Progress]], "UnitPrep Auth & Persistence — Index" (no note yet at the time — now [[Auth & Persistence Index]]), "Auth security assessment (backend-only, 2026-07-30)" (no note yet at the time — folded into this satellite immediately above)

---

## 2026-08-03 19:12 UTC — Revisited tool-session ownership (item 4) with the Onboarding Orchestrator vision in view

**This entry is not part of the WebAuthn/TOTP auth build.** It's included
here per instruction to consolidate drifted single-session notes rather than
create another one-off file for it, but it concerns a different Phase I
item (Onboarding Orchestrator tool-session infrastructure — `unit-group`/
`dedup` advisory tool sessions), not Auth Phase 2 tasks 6/7/9/10 or the
Auth-hardening Phase I/II. Cross-reference [[Platform Vision (Onboarding Orchestrator)]] rather than [[Phase 2 Progress]] for this one.

Boris asked to revisit the tool-session `owner_id` decision (Phase I item 4)
after clarifying what it's actually for: not primarily access control, but
attribution feeding a long-term vision (task tracking, completion
percentage, eventual 3rd-party task sync to systems like ClickUp/HubSpot)
plus a possible future usage/activity log visible to non-admin users. He also
described the next planned tool after auth (document/lease formatting —
extracting QMS `{{placeholder}}` tags via API, feeding a sample lease
document, replacing live/generic PII with the correct tag for notice-email
generation) as a candidate for needing longer-lived, shareable sessions,
unlike today's tools.

**Decisions:**

- Recommended (pending Boris's confirmation) capturing `owner_id` on tool-session creation now, without enforcing owner-only access control - decoupling "who ran this" (attribution, wanted now, cheap) from "who may access this" (real access control, not needed today given 10-minute session TTL and trivially-repeatable current tool steps, per Boris's own reasoning).
- Surfaced an honest limitation Boris should know before treating this as progress toward the Orchestrator vision: unit_group/dedup sessions live only in the in-memory `InMemorySessionStore` with a ~10-minute TTL. Stamping `owner_id` on that in-memory record only matters for the session's own short lifetime - it does NOT by itself enable any durable history, completion tracking, or 3rd-party task sync, since the record vanishes on expiry regardless of what fields it carries. The actual prerequisite for that vision is a persistence layer that outlives the session (writing session outcomes to Postgres, not just holding them in memory) - which is the "persistence" pillar the vault's own Platform Vision note already names alongside auth as a real requirement, not yet built. Item 4 is a small, cheap, forward-compatible step toward that, not a substitute for it.
- Distinguished the "usage audit log visible to non-admin users" idea from `auth.auth_audit_logs` explicitly: the existing audit log is auth-events-only (login/registration/TOTP/invites/recovery), lives in the `auth` schema, and is admin-only by RLS policy (`auth_audit_logs_select_admin_only`). A tool-usage/activity history feature would need its own separate table and its own visibility rules, not a relaxation of the auth audit log's admin-only policy - flagged as a distinct future feature, not building now.

**Open:**

- Document/lease formatting tool (extract QMS placeholder tags via API, detect and tag live/generic PII in a sample lease document for notice-email generation) is the next planned tool after auth is buttoned up - not yet scoped or designed. Good candidate for eventually needing longer-lived/shareable/resumable sessions given the multi-step, review-and-correct nature described, unlike today's quick advisory tools.
- Whether/when to build a persistence layer for tool sessions (durable storage surviving the in-memory TTL) is a separate, larger decision than item 4 - not yet raised as its own roadmap item.
- Whether/when to build a user-visible tool-usage activity log is a separate future feature, not yet scoped.

**Related (original links):** [[Platform Vision (Onboarding Orchestrator)]]

---

## Related

- [[Phase 2 Progress]] — the current-status note whose "How each completed task went" section has the gap this note fills.
- [[Phase 2 Progress — Task Log]] — the sibling note holding tasks 1, 2, 3 (and pointing to [[Phase 2 Progress — Task Log 2026-07-29]] for 4, 5, 8); this note is task-log-shaped in the same way, for tasks 6, 7, 9, 10 plus the related follow-ups above.
- [[Phase 2 Progress — Task Log 2026-07-29]] — tasks 4, 5, 8.
- [[Auth & Persistence Index]] — top-level index for the whole workstream.
- [[Logging & Observability]] — the roadmap the first entry above closes out.
- [[RLS Implementation]] — SECURITY DEFINER functions and column grants referenced throughout (task 6, 7, 9, 10 decisions all lean on this).
- [[Database Schema]] — tables (`auth.user_invites`, `auth.totp_credentials`, `auth.sessions`) these tasks built against.
- [[Architecture]] — original v1 design tasks 9/10 implement against.
- [[Platform Vision (Onboarding Orchestrator)]] — the actual home for the final entry above (tool-session ownership), not this auth workstream.
