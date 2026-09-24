---
description: "Architectural and workflow decisions worth recalling across sessions — each links to its source work note"
tags:
  - brain
---

# Key Decisions

Architectural or workflow decisions worth recalling. Link to the full [[Decision Record]] when one exists.

## UnitPrep auth architecture (2026-07-20, final)

Self-hosted WebAuthn/TOTP for identity, opaque session-token cookies (not JWT, not DPoP), Postgres via Neon with row-level security, a single Admin role for v1 (deliberately narrowed down from a four-role/Groups design once it was clear that would be built ahead of actual need). Full detail and rationale in [[Architecture]] (`work/active/UnitPrep/Auth & Persistence/`). Database schema (7 tables, RLS pass) built and verified on Neon dev as of 2026-07-21; Rust wiring still pending. See [[Collaboration Style]] for how this decision got made — Boris supplied several of the deciding factors himself.

## UnitPrep git branch policy (2026-07-23)

`main` only on `unitprep-api` and `unitprep-ui` — no incidental branches without an explicit ask, reinforced as a hard rule after a stray unattributed branch caused a review to miss two days of real work. Full rule in [[Patterns]], incident in [[Gotchas]].

## UnitPrep no-auth-by-design (standing, revisit trigger fired 2026-07-20)

Both UnitPrep repos ship with no authentication, an accepted and deliberate gap for single-operator internal use — not to be raised as a surprise finding. The stated revisit trigger (scope going client-facing / needing admin roles) fired 2026-07-20, which is what started the auth architecture work above. See [[Gotchas]] for the full reasoning.

## UnitPrep patch-version philosophy: one bump per real release boundary, not one per fix

When a batch of bug fixes/hygiene/test work accumulates with no new functionality, it gets **one** patch version bump (1.1.0 → 1.1.1 → 1.1.2) covering the whole batch — not a separate patch version per individual commit or fix. Versions mark real release boundaries; since nothing was actually released in between individual fixes within a single work session, manufacturing several consecutive patch numbers for them would be inventing history that didn't happen. Half-built, not-yet-wired features (e.g. the in-progress auth work) stay under CHANGELOG's `Unreleased` section rather than being folded into a patch bump, even if some of their scaffolding landed in the same session — a version bump should reflect what's actually shippable, not everything that happened to get touched.

## UnitPrep session-cleanup lock scope and `cancel_session` race — revisited and fixed 2026-07-28

Both had been judged "disproportionate to fix given single-operator scale/risk" as of the third hardening pass. Boris asked to fix them anyway as part of fully closing out the refactor before a code-quality review, ahead of resuming auth — not because the original risk assessment was wrong, but because finishing the refactor took priority. Full technical detail in [[Fourth Pass - File Splits, Concurrency Fixes, Dead Code Removal]].

## UnitPrep auth: four decisions taken together (2026-07-30)

All Boris's calls, made while reviewing task 8.

**1. Admin approval of new users — considered and dropped.** Boris proposed a step where an invited user registers, lands in a `pending_approval` state, and an admin manually approves. Dropped after weighing: the invite is already single-use and expiring, so the leak window it defends is narrow; it adds permanent manual work per user forever; and without email it becomes a *polling* problem — someone enrolling Friday evening waits until Monday. It also creates a new stuck state (enrolled but cannot sign in) needing its own UI. **Two cheaper substitutes adopted instead**: shorter invite lifetime (below), and *notify rather than gate* — an audit event now, an email later saying "X just enrolled", with revoke as the response. **Worth revisiting when the four roles exist**: approving someone into an *admin* role is genuinely different from a view-only one, so gating privileged roles only would get most of the benefit at a fraction of the friction.

**2. Invite lifetime 24 hours**, down from 7 days. The real risk with a setup link isn't guessing (256 bits of random) but *lingering* — in a Teams log, an email, a terminal's scrollback, long after the recipient enrolled. `--reissue-invite` makes expiry a non-event.

**3. Enrolled factors expire on deactivation/soft-delete.** Passkeys (and TOTP later) are removed when a user is deactivated or soft-deleted, so restoring the account requires re-enrolling. Boris: "cheap UX cost — better security." The account's *history* is untouched — audit rows survive, so restoring restores access to prior work, which remains an explicit goal. What doesn't survive is the means of authenticating. Enforced by a `SECURITY DEFINER` trigger rather than application code, because nothing deactivates a user yet and there will eventually be several paths (admin action, offboarding routine, break-glass, bulk operation, manual SQL) — a trigger covers the ones nobody remembers to write.

**4. Least privilege as roles arrive.** Boris asked to note this and raise it at the right moment: as the four-role model gets built, keep pushing capabilities down to the narrowest role that needs them. Already demonstrated by `app_service` holding `UPDATE` on only `first_name`/`last_name`/`job_title` — which, usefully, is *why* it cannot deactivate a user, forcing that path through a checked `SECURITY DEFINER` function.

## UnitPrep: device-bound passkeys are NOT required — requirement dropped (2026-07-29)

The 2026-07-20 architecture said device-bound (non-syncable) passkeys "should be required specifically for accounts that will hold QMS/Dropbox credentials". **Reversed by Boris 2026-07-29**: not required, synced passkeys explicitly acceptable, for any account.

Two concrete reasons rather than theoretical ones. Boris **works remotely on occasion**, and a credential that cannot leave one machine means lockout whenever that machine isn't to hand — where the only recovery is the heavily-logged break-glass path this design treats as an exception, not a routine. And when the first real ceremony ran, **both Windows Hello and Proton Pass produced synced credentials by default** — so enforcing device-bound would reject the ordinary path on ordinary tooling, to protect QMS/Dropbox credentials that don't exist yet.

`webauthn_credentials.device_bound` survives as **information only** (and was fixed the same day — it had been defaulting to `true` for every row regardless of truth). If revisited, the honest shape is *per-action* rather than per-account: require a fresh device-bound factor at the moment someone views a stored third-party credential, i.e. fold it into step-up re-auth (Phase 4), rather than blocking enrolment. Full reasoning in [[Architecture]].

## UnitPrep multi-role expansion raised, then declined — the no-Groups decision still stands (2026-07-29)

While resuming Phase 2 auth work, Boris asked about a `user_roles` table with 5 roles (Super Admin, Admin, Implementation, Sales, Developer) — this is exactly the trigger condition the 2026-07-20 decision named ("until a real second role/department need shows up"). Flagged against [[Gotchas]]'s no-Groups-by-design entry before building anything; Boris then clarified this was not an intentional reversal ("sorry for confusion") and the single-Admin-role, no-Groups-table decision stands unchanged. No schema change made. Recorded here specifically so a future session doesn't mistake "it was asked about" for "it was decided" — the revisit trigger has now been raised once without firing.

## UnitPrep test coverage tooling: `cargo-llvm-cov` primary, `cargo-tarpaulin` as an occasional cross-check only

Both are installed (`cargo cov` / `cargo cov-tarpaulin` aliases in `unitprep-api/.cargo/config.toml`), but they measure the same thing — running both routinely is redundant maintenance for no real extra signal. `cargo-llvm-cov` is the default for regular use (LLVM source-based, fast, accurate branch coverage). Reach for `cargo-tarpaulin` only if `llvm-cov`'s numbers ever look suspicious and an independently-implemented second opinion is worth the extra run. Baseline as of 2026-07-28: 84% (llvm-cov) / 81% (tarpaulin) — consistent, no discrepancy investigated. Frontend equivalent is `@vitest/coverage-v8` (`npm run test:coverage` in `unitprep-ui`), baseline ~9% since only 3 files have tests so far.

## UnitPrep: no `is_test` column on `auth.users` — test accounts are identified by email convention (2026-07-30)

Boris proposed a `test` / `dev test` column so throwaway accounts could be isolated later, flagging himself that he wasn't sure it was a good idea, and explicitly left the call open. **Declined, and he agreed.** The reasoning is worth keeping because the instinct behind it was reasonable and will recur.

Three reasons, in order of weight:

1. **It is a test backdoor waiting to be written.** A boolean named `is_test` on the users table invites `if user.is_test { skip_check() }` later — plausible-looking code that is exactly how test bypasses reach production. The column does not do that by itself; it makes it easy and unremarkable in review.
2. **A manually-set, UI-invisible flag will be wrong.** The proposal was for developers to set it by hand, with no UI surface. Nobody remembers. The result is a column that cannot be trusted while *looking* like a filter — worse than having none, because it invites reliance.
3. **The discriminator already exists for free.** `invite-test@quikstor.com` is filterable today with no schema change. Systematising it is a naming convention, not a migration: reserved domains like `@example.com` (RFC 2606, can never be a real address) make "is this a test account" **derivable** rather than **stored**, so it cannot drift out of sync with reality.

Generalises as: **don't put a dev-workflow concept into the production schema.** The domain has no notion of a fake user; the database shouldn't either.

**What would legitimately earn a column**: needing to *enforce* different behaviour, e.g. test accounts can never be granted access to real facility data. That is a domain rule. Filtering a list is not.

Practically moot as well — `status = 'deactivated'` already keeps the one existing test account out of any sensible active-user view. See [[Phase 2 Progress]] for how that account came to exist.

## UnitPrep: `onboarding_manager` role added schema-only, and permissions/roles work is now its own standing effort (2026-08-05)

The second role from the original four-role architecture design landed —
but deliberately with **zero permissions**: every admin-gated action refuses
it via a shared `insufficient_role()` 403 plus an `authorization_failure`
audit row. Adding the role and deciding what it can do are treated as two
separate decisions on purpose — the role existing early (with a safe
default-deny) is what makes it safe to defer the second question rather
than rushing it.

**Boris's explicit framing**: permissions/roles design is genuinely
ongoing and not something to close out in one pass — "add to it gradually
... it is crucial to get right, so discussion, pushback, education... are
welcome and necessary." This is now tracked in its own note,
[[Roles & Permissions — Design Discussion]] (`work/active/UnitPrep/Auth &
Persistence/`), not folded into routine feature work or closed-out
decision records. Treat any future roles/permissions question as
belonging there first.

**Two principles established in that first pass, worth internalizing
generally, not just for UnitPrep**: (1) least privilege means "role = job
function," not "role = trust level" — the instinct to arrange roles on one
trust ladder is the wrong model; ask what a job needs, not how trusted it
is. (2) "who can administer the system" and "who can see business data"
are independent axes that happen to be collapsed into one `Role` today
because the team is one person — don't assume every future role slots
into a single hierarchy.

**A "Manager" role with dual-approval for admin role changes — opinion
given, not built.** Dual control on privileged role changes is a real,
standard control (this is exactly what SOX/SOC 2 reviewers look for), not
overengineering in general — but it only functions with a genuine second
approver. With effectively one active admin, it would be theater. **Don't
build until a second admin actually exists** to make it real — same
trigger-gating logic as the last-remaining-admin guard below. Self-role-
edit is already refused structurally regardless (shipped 2026-08-05,
independent of whether this ever gets built).

## UnitPrep: a last-remaining-admin guard only needs to cover what a single request can cause (2026-08-05)

`change_user_role` and `deactivate_user` both refuse if the specific
change requested would leave zero active admins (counts remaining active
admins excluding the target). Deliberately **not** a general guarantee:
two admins alternately demoting/deactivating each other down to one, then
that one hitting the pre-existing self-target refusal, is still a
multi-request path to "one admin left" that this doesn't prevent — judged
acceptable because it needs a second admin to even attempt, at which
point the dual-control conversation above becomes the relevant next
step, not a bigger single-request guard.

## UnitPrep: an "alert" with no ESP/notification service is an in-app indicator, not a push notification — say so explicitly (2026-08-05)

Boris asked for a "dormant account alert." No email/webhook/notification
service exists anywhere in this system (a standing, deliberate deferral —
see [[Architecture]]). Built the honest interim instead of quietly
under-delivering on the word "alert": a "Last active" column + a 90-day
inactivity flag directly on the admin Users table, costing no new
infrastructure. **Named the gap explicitly rather than silently building
the smaller thing and calling it done** — real push alerting is blocked on
the same deferred ESP/webhook decision as everything else that would
need one, and should be designed once, not solved piecemeal per feature.

## UnitPrep: GatedRouter as the structural replacement for the lost `Role`-enum compiler backstop (2026-09-23)

`THREAT_MODEL.md` named a real, specific gap: roles/permissions moving from a closed Rust `Role` enum to data-driven tables (2026-08-06) removed a genuine compiler backstop (a new role forced every `match admin.role` to grow an arm or fail to build), and nothing replaced it — a new handler can simply forget to call `require_permission` and nothing catches it. `unitprep-api`'s `GatedRouter` (`src/api/route_access.rs`) closes this at two levels: it never re-exposes `axum::Router::route`, so a route cannot be registered without declaring a `RouteAccess` at that call site (compile-time half), and a `permission_gate_tests` module calls the real handler behind every `Permission`-classified route with a zero-permission caller and asserts 403 (runtime half — catches a handler that declares the right classification but forgets the actual check). Full detail in [[Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation]].

**Worth noting for future "should we build compile-time enforcement or a runtime test" decisions**: neither half alone would have been enough — the compile-time half only forces a classification to exist, not that it's true, and the runtime half alone (without the compile-time forcing function) would still let a new route slip through unclassified entirely.

## UnitPrep: generate frontend types from Rust structs (ts-rs) rather than diffing a hand-written mirror against a schema (2026-09-23)

Considered three approaches to `unitprep-ui`'s `types/api.ts` hand-mirroring Rust response structs with nothing enforcing it stayed accurate (it had already drifted once — the `output_path` field removal broke at runtime): (A) generate a JSON schema from Rust, commit it, and diff a hand-written TS type against it; (B) a same-repo Rust-only "tripwire" snapshot test that only reminds a developer something changed; (C) generate the actual `.ts` file from the Rust struct via `ts-rs`, replacing the hand-written mirror entirely.

**(A) was rejected on inspection, not just cost** — there is no way to mechanically compare a JSON schema against a hand-written TypeScript type at runtime (TS types are erased at compile time), so "diffing" would need either a second hand-maintained field-name manifest (the same drift risk, moved one level down) or codegen anyway. Chose (C): it needs more upfront setup than (B), but it's the only one of the three that's still correct once CI eventually exists (regenerate, then `git diff --exit-code` on the generated file — no new mechanism needed at that point), and it eliminates the hand-mirror for the covered types entirely rather than just detecting when it goes wrong. Scoped deliberately to the four response families `types/api.ts`'s own header already named, not the whole file. Full detail and the real `ts-rs` `export_to` gotcha hit along the way in [[Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation]] and [[Gotchas]].

## UnitPrep: modularity/file-size checks apply after finishing a task, not only before starting one (2026-09-24)

Refines the existing [[Patterns#UnitPrep: flag modules approaching ~250 lines|~250-line flag rule]] and its 2026-08-14 generalization to unprompted architectural-drift flagging, after both failed to fire on `unitprep-api`'s own `router.rs` growing from 842 to 1909 lines in one session (the GatedRouter work above) without being flagged in the moment. The rule was applied to the *substance* of that session's work but never re-checked against the resulting file's own size once the work was done. **Fix**: the check now lives directly in both repos' own `CLAUDE.md` as a standing law (not just the vault, reachable only via `recall`/`search` on non-trivial *design* decisions — a routine multi-edit task that grows a file doesn't reliably re-trigger that path), stated explicitly as "check after finishing, not just when starting." Full incident writeup in [[Patterns]]; the fix itself in [[Session 2026-09-24 — Modularity Standing Law, Router Split, Refresh Parity Tests & Policy-Handler DRY Refactor]].
