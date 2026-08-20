---
date: 2026-07-30
description: "Assessment of unitprep-api's auth logging and audit trail as of v1.2.0, what is already right, the one gap that is a bug, and a ranked roadmap Boris approved."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Logging & Observability

Assessment made 2026-07-30 after reviewing the server output from a real
end-to-end passkey session, at Boris's request. **He approved everything below,
including the "later" items**, and asked that log-improvement opportunities be
raised proactively when they fit the work in hand rather than saved up.

## The framing that makes gaps visible

There are **two records**, doing different jobs, and judging them together is
how holes hide:

| | purpose | lifetime |
|---|---|---|
| `tracing` output | ops telemetry — *what is happening now* | ephemeral |
| `auth.auth_audit_logs` | the durable record — *what happened, for forensics and compliance* | permanent, append-only |

A thing can be adequately logged and still be a hole in the audit trail. That is
exactly the case below.

## What is already right — do not regress these

- **Fields are structured**, not interpolated into prose: `user_id=…`,
  `session_id=…`, `is_bootstrap=false`. Already queryable if the logs ever reach
  something that indexes them.
- **`user_id` is a UUID, not an email.** The logs do not accumulate PII. Keep it
  that way.
- **Severity is meaningful** rather than everything-at-info. A failed ceremony is
  `warn` — an ordinary client outcome, a cancelled prompt or wrong device. A
  database failure is `error` — a server fault. That distinction is worth real
  money during an incident.
- **Both halves of a ceremony log**, so one that starts and never completes is
  visible.
- **Audit recording is infallible to callers by design** — a logging failure must
  not be able to deny a login. See `auth::audit_log`.

## The one item that is a bug, not an enhancement — FIXED 2026-07-30

> [!success] Fixed in `unitprep-api` commit `86f9a6a`, along with roadmap items 2 and 3.
> Refusals now write a `registration_failed` audit row naming the reason
> (`bootstrap_disabled`, `missing_email`, `not_eligible`) plus the attempted
> address, and log a `warn`. A registration whose credential fails verification
> writes one too (`credential_rejected`), matching login's `assertion_rejected`.
> Verified on the dev branch against a freshly started binary: audit rows went
> 8 → 11 while all three refusals returned byte-identical 403 bodies.
> The original problem statement is kept below, unedited, because the reasoning
> is what generalises.

**A rejected registration attempt is recorded nowhere.** Verified 2026-07-30: a
`403 registration_not_available` produced no tracing line *and* no audit row
(`0 rows` matching). Meanwhile a failed *login* writes `login_failed`. So probing
registration across a list of addresses is entirely untraceable, while identical
probing against login is recorded — an asymmetry with no principled basis.

It costs nothing security-wise to fix: the HTTP response stays indistinguishable
to the caller (that is deliberate, and protects against user enumeration).
Recording it server-side leaks nothing; it just means the operator can see what
the attacker cannot.

Treat as a small bug. "An audit trail with a silent path in it" is the kind of
thing discovered at the worst possible moment.

## Ranked roadmap

### Do with the next touch of that surface — all three DONE 2026-07-30

1. ~~**Audit row for rejected registration attempts**~~ — the bug above. **Done.**
2. ~~**`ceremony_id` on both halves of a ceremony.**~~ **Done, but deliberately
   NOT as specified.** The instruction said to log the ceremony id because it
   "already exists in the code (it is generated and put in the cookie)" — and
   that parenthesis is exactly the reason not to. The ceremony id *is* the
   cookie's value, the thing a client presents to `/finish`, so logging it
   writes a live bearer value into ops output that gets shipped somewhere less
   protected than the database. It would also have contradicted this note's own
   "never log tokens" rule two sections down.

   Instead each ceremony now carries a second `correlation_id`, generated at
   construction, never sent to the client, logged on both halves and recorded in
   the audit metadata so a permanent row joins to the ephemeral log lines. A
   test in each ceremony type asserts the two ids differ, because collapsing
   them back into one would read as a tidy-up in review. Verified live: the
   cookie held `1e932acb…` while the logs carried `c63573a8…`.

   **Confirmed on a real successful ceremony 2026-07-30** — a Windows Hello
   sign-in through `dev-tools/run-auth-harness.sh`, not curl. Both log lines
   *and* the permanent `login_succeeded` audit row carried
   `correlation_id=ff5f43a3…`, with `session_id` matching across log and row. So
   the intended join actually works: an audit row leads to the ops lines for
   that specific ceremony, which is exactly what `user_id` alone could not do.
3. ~~**`device_bound` in `passkey_registered` metadata.**~~ **Done, and observed
   on real enrolments 2026-07-30** — two of them through the harness, one
   authenticated (`{"invite": false, "device_bound": false}`) and one via invite
   (`{"invite": true, "device_bound": false}`), each carrying the ceremony's
   correlation id. Worth noting what the value says: **every credential enrolled
   on this project so far is `device_bound: false`** — they are synced passkeys
   living in Proton Pass, not Windows Hello platform credentials. That is the
   evidence behind dropping the device-bound requirement, now visible in the
   audit trail rather than inferred from one ceremony.

### Worth having, not yet

4. **Request ids.** At one operator, timestamps are enough correlation. At ~50
   users, answering "what happened for this person at 3pm" gets painful.
   `tower-http`'s `TraceLayer` gives it cheaply. Trigger: the first time a
   support question cannot be answered from the logs.
5. **Ceremony duration.** A user fumbling with Windows Hello and a genuinely
   broken authenticator currently look identical.

### Deliberately not doing

- **No emails in logs.** UUIDs only. (Note the *audit* table does store an
  attempted address in `metadata` for a failed login — correct, because an
  unmatched address is data about the attempt rather than an identity, and that
  table is access-controlled.)
- **No turning normal-operation logging up.** This project already dialled DEBUG
  back after every discovery run emitted hundreds of per-file lines; see
  `main.rs`'s `EnvFilter` default of `unitprep=info`.
- **Never log challenges, tokens, or `passkey_data`.**

## Standing instruction

Boris: *"I love me a good log."* Raise logging improvements when they fit the
work in hand — while already editing that handler, adding that endpoint — rather
than as a separate project or a saved-up list. Judge against best practice
(structured fields, meaningful severity, no PII, correlation ids, one record of
truth) rather than volume.

## Related

- [[Phase 2 Progress]] — the audit events wired so far live under task 5
- [[Session 2026-07-29 — Auth Tasks 4, 5, 8 and Infrastructure Fixes]]
- [[Database Schema]] — `auth_audit_logs` columns and why `event_type` is text
- [[RLS Implementation]] — the admin-only SELECT policy that makes
  `INSERT ... RETURNING` fail on this table
- [[Admin Panel & Audit Logs Polish — Session Log]] — first-hand build detail
  for audit-log steps 2-5 (cosmetics, lazy-load, CSV export, PDF export
  polish), 2026-08-05/06
