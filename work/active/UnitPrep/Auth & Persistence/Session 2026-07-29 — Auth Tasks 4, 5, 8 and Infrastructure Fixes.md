---
date: 2026-07-30
description: "Handoff record for the 2026-07-29/30 session: Phase 2 tasks 4, 5, 8 shipped as v1.2.0+, three real security fixes, the Neon pooler bug, qmd search repair, and every outstanding item."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-07-29/30 — Auth tasks 4, 5, 8 and infrastructure fixes

Handoff note, written at Boris's request before migrating to a new session. The
per-task technical detail lives in [[Phase 2 Progress — Task Log 2026-07-29]];
this is the narrative, the decisions, and — most importantly — **what is still
open**.

## Where things stand

`unitprep-api` at **v1.2.0**, 16 commits on `origin/main` since v1.1.5, working
tree clean apart from Boris's own untracked `README.sample.md` / `assets/`.
**366 tests passing**, clippy at a 2-warning baseline (both awaiting task 10),
fmt clean. Dev and prod Neon branches both at **23 migrations**, checksums clean
on both, 48 structural facts diffed identical.

Phase 2: **tasks 1-5 and 8 of 11 done.** Passkey registration and sign-in work
end to end, verified through a real browser with three different authenticators
(Windows Hello, Proton Pass, and a second Windows Hello credential).

## What shipped

**Task 4** — `POST /auth/register/begin` + `/finish`. Two paths: an
authenticated caller adds a passkey for themselves, or an env-gated bootstrap
path for a first enrolment. **Task 5** — `POST /auth/login/begin` + `/finish`,
plus audit-event recording wired in from the start. **Task 8** —
`unitprep bootstrap-admin`, a CLI subcommand that creates the first
administrator and mints the first invite.

Task 8 was **deliberately reordered ahead of 6 and 7**: an invite is created by
an admin, and until one exists nobody can create one, so bootstrap is the
dependency — and it mints the first token, which is what makes acceptance
testable. An earlier suggestion in-session to do 7 before 6 was wrong for the
same reason and is superseded. Correct order is **8 → 6 → 7**.

## Three genuine security fixes

Worth separating from the correctness work, because these were live holes in
reachable code paths rather than tidiness:

1. **Privilege escalation via `auth.users`.** `app_service` held table-level
   `UPDATE`, and `users_update_own_or_admin` is row-scoped, so a caller could
   have run `SET role = 'admin'` on their own row. Not reachable *today* only
   because every existing user is already admin — it would have gone live the
   moment a second role existed. Now column-scoped to `first_name`, `last_name`,
   `job_title`.
2. **Session self-rescue via `auth.sessions`.** Same row-scoped policy would
   have let a caller clear their own `revoked_at` (undoing "sign out
   everywhere") or extend `expires_at` indefinitely — defeating the entire
   reason an opaque token was chosen over a JWT. `UPDATE` revoked outright.
3. **The setup script silently re-opening #1.** Its blanket
   `GRANT ... ON ALL TABLES IN SCHEMA auth` re-granted table-level `UPDATE`, so
   running a script documented as *"safe to re-run"* reopened the escalation
   vector with no error and no output.

Plus `auth_audit_logs` `UPDATE`/`DELETE` revoked as a third barrier (RLS
default-deny and the append-only triggers already blocked both).

## Decisions taken

Recorded in full in [[Key Decisions]]. Summary:

- **Device-bound passkeys not required** — requirement dropped, not deferred.
  Boris works remotely, and Windows Hello and password managers both produce
  synced credentials by default, so enforcing it would reject the ordinary path
  to protect secrets that do not exist yet.
- **Admin approval of new users — considered and dropped.** Substitutes adopted:
  24-hour invite lifetime (down from 7 days), and *notify rather than gate* when
  email lands. Worth revisiting when four roles exist, gating **admin**-role
  enrolment only.
- **Enrolled factors expire on deactivation/soft-delete**, by trigger. History
  survives, the credential does not, so restore requires re-enrolment.
- **Multi-role expansion raised, then declined** — the single-Admin, no-Groups
  decision stands.
- **Prod is "provisioned but parked"** — dev-only by default, with drift flagged
  proactively rather than synced per change.

## Infrastructure fixed along the way

- **The Neon pooler bug.** `db.rs` sent `search_path` as a connection option,
  which the pooler rejects, so *every* query failed including `/health/db`. All
  application SQL is now schema-qualified. **This corrected an earlier wrong
  conclusion in this same session** — see the warning callout in
  [[RLS Implementation]]; a "confirmed working" health check had come from a
  process still running the direct URL.
- **Prod branch provisioned and synced.** Also uncovered that the role-setup
  script could not bootstrap a fresh branch in *any* order, and that Neon roles
  are per-branch rather than project-wide.
- **qmd semantic search repaired.** It was never installed; and separately, the
  `om` server's path-matching silently withheld any note whose path contained
  punctuation — including this entire folder. See [[Gotchas]].
- **Vault test suite green** (1183/1183) after restoring missing `AGENTS.md`,
  `GEMINI.md`, `.codex/`, `.gemini/`.

## Outstanding items

### Next up

> [!note] Done 2026-07-30 — task 6 landed; next is task 7.
> This section is left as written because it is the handoff it was. For current
> status go to [[Phase 2 Progress]]. In short: acceptance shipped folded into
> `POST /auth/register/begin`, `AUTH_BOOTSTRAP_ENABLED` and
> `auth.resolve_bootstrap_registration` are deleted, and the prod bootstrap
> invite below did expire unused as predicted — `--reissue-invite` mints a fresh
> one when prod is actually needed.

- **Task 6, invite acceptance.** Retires `AUTH_BOOTSTRAP_ENABLED`, which should
  then be **deleted, not merely unset**. There is a live 24-hour invite on the
  prod branch to test against. Ordering detail: `create_session` and
  `resolve_bootstrap_registration` both require `status = 'active'`, so the
  invite must be consumed *before* the passkey ceremony can complete.
- Then task 7 (invite creation), then the admin panel — see below.

### Approved, not yet built

- **Logging improvements** — full assessment and roadmap in
  [[Logging & Observability]]. One item is a small bug rather than an
  enhancement: a rejected registration attempt is recorded **nowhere**, while a
  failed login writes an audit row.
- **Notify-on-enrolment** when an ESP is chosen: audit event now, "X just
  enrolled" email later, revoke as the response.
- **Admin panel (Phase 3)** — agreed trigger is *after* tasks 6-8, when a Users
  tab has real backend behind it. Scope: Users + Authentication Policy. Audit
  Logs excluded by Boris as a separate effort; Groups still deferred.
- **Least privilege as roles arrive** — Boris asked for this to be raised at the
  right moment rather than pre-emptively.

### Unresolved questions

- **`app_service` password on prod is unset.** Boris's to do, not needed until a
  deployment exists: connect with `NEON_PROD_DATABASE_URL_DIRECT` and run
  `\password app_service`, then replace the placeholder in `.env.local`. Nothing
  reads it yet.
- **Prod's bootstrap invite will expire unused** (24h from 2026-07-30 16:06 UTC)
  since nothing can consume it until task 6. Harmless —
  `--reissue-invite` mints a fresh one.
- **Sessions accumulate** — 4 on dev, none revocable until task 10.
- **`totp_credentials.secret_encrypted` encryption at rest** — still undecided,
  deferred to task 9.
- **Two audit-log FK actions were made honest** (`SET NULL` → `RESTRICT`); the
  equivalent question was *not* raised for `user_invites.created_by` or
  `auth_configuration.updated_by`, which are legitimately `SET NULL` because
  those tables have no append-only trigger.

### Deliberately not done

- `user_invites` partial-unique "one outstanding invite per user" constraint —
  still undecided. Note `--reissue-invite` now retires outstanding invites
  itself, which achieves the practical effect for the bootstrap path.
- Per-developer database roles — needs a second developer.
- `sessions` DELETE policy — needs a cleanup-sweep job to exist.
- Frontend npm audit (12 high-severity, no non-breaking fix) — unchanged.

## Mistakes made this session, and what they teach

Kept because each one nearly shipped, and the pattern matters more than the
instance.

1. **A stale binary reported plausible-but-wrong output** — printed "valid for 7
   day(s)" after the value was changed to 24 hours. Caught only by checking the
   *database*, not the tool's printout. **After changing a value a CLI reports,
   verify the stored result.**
2. **A verification that passed by returning nothing** — a parity probe reported
   "IDENTICAL across 0 structural facts" because the query errored on both sides
   and it diffed two empty files. **A pass with a zero count is not a pass.**
3. **A tautological test** — the first `device_bound` test restated the
   inversion locally, so dropping the `!` in production would have left it
   green. Rewritten to call the production function.
4. **Editing already-applied migrations** (comment-only), which broke sqlx's
   checksums and blocked all further migrations.
5. **A 30-second stall hidden as a passing test** — the lazy test pool meant an
   unintended query waited out sqlx's 30s default and *then* errored, so the
   test still passed and only the suite got slower. Now 50ms.
6. **Advice that was conditionally true** — the bootstrap tool first printed
   "delete the user row and start over", which works immediately after bootstrap
   and is impossible thereafter. Worse than plainly wrong.

## One thing left red, deliberately

The **vault's own** test suite ends this session at **1182/1183**, not green.
`qmd-refresh.integration.test.ts` fails under full-suite parallelism while
passing 13/13 in isolation — a load-sensitive integration test, not a content
error. It was green twice earlier the same day; the vault grew from ~80 to 88
notes in between, and that test does real qmd work whose duration scales with
vault size. Triage guidance and the honest fix options are in [[Gotchas]].

Flagged rather than fixed because Boris called a stop to implementation. **Do not
try to fix it by editing notes** — nothing about the content is wrong.
`unitprep-api`'s own suite is fully green at 366/366.

## Related

- [[Phase 2 Progress]] — status and the constraints binding future work
- [[Phase 2 Progress — Task Log 2026-07-29]] — per-task detail
- [[Logging & Observability]] — the logging roadmap
- [[RLS Implementation]] / [[Database Schema]] / [[Architecture]]
- [[Key Decisions]] / [[Gotchas]] / [[Patterns]]
