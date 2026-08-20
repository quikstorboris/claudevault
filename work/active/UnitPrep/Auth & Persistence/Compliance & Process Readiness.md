---
date: 2026-08-04
description: "Deferred, low-priority-for-now bucket for auditor/compliance-facing gaps: SOX ITGC posture, other regulatory frameworks assessed against UnitPrep's actual data profile, CI/CD, and availability/recovery. Preemptive framework, not active work."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Compliance & Process Readiness

Boris's framing, 2026-08-04: this is **preemptive and defensive, not a
current priority** — "establishing framework to tighten controls,
policies and practices with relative ease as opposed to having to stand
everything up from scratch." Nothing here should be read as blocking or
urgent. It exists so that when the time comes (a real customer security
review, a SOX scoping conversation, an actual EU user), the answer is
"already mapped, here's the punch list" rather than starting cold.

## SOX ITGC — assessed 2026-08-04, gaps are process, not engineering

Full assessment given in-conversation; summary here for durability.
**Important scoping caveat, Boris's own to raise internally**: whether
UnitPrep is even *in scope* for SOX at all is a determination that
belongs to Quikstor's SOX program / external auditors (does this system's
data feed financial statements?), not something derivable from the code.
Everything below assumes it might be asked, or that SOC 2-adjacent rigor
is wanted regardless.

- **Strong**: authentication/session security, audit-trail integrity
  (append-only, now with `ip_address` + before/after diffing), access
  provisioning/deprovisioning (invite-based, real deactivation action).
- **The real gap: segregation of duties.** One role (`admin`) can act
  *and* review its own actions (create users, assign roles, read the
  audit trail that would catch abuse of the first two). This is the
  single most likely finding if anyone actually looks — see [[Roles &
  Permissions — Design Discussion]] for what would actually fix it (a
  second admin, eventually a Manager-approval role) and why it isn't
  buildable yet with one active admin.
- **Missing**: evidence the documented quarterly review (see
  `AUDIT_RETENTION.md`) is actually being executed, not just that the
  policy exists. An access-review CSV export (queued as a near-term
  polish item) is the cheap first step toward this.
- **Not assessed this session, unknown either way**: change-management
  evidence (PR review requirements, deploy approval). Worth a dedicated
  look before assuming readiness either way, whenever this becomes
  relevant.
- **Named, accepted gap**: `TOTP_ENCRYPTION_KEY` in a plain env var, no
  rotation. Already documented as deferred in `AUTHENTICATION.md`.

## Other frameworks, given UnitPrep's actual data profile

Boris's own scoping: the only PII is storage-tenant (the facility's
*own* tenants, i.e. the customer's customer) contact information —
name, address, phone, email. No CC numbers, no SSNs. Some financial data
(tenant payment history, facility revenue summaries, unit street rates)
but nothing more elaborate. Assessed against that profile, not
speculatively:

> [!warning] Correction, 2026-08-07 — the profile above is incomplete
> Reading QMS's actual `EndUser` API schema (see
> [[QMS API - Domain Model & PII]]) surfaced fields this scoping didn't
> account for: a **driver's license number** (government ID), and a
> **`lastFourSsnDigits`** field on the military profile (a genuine partial
> SSN, collected for SCRA purposes) — plus full contact PII for **alternate
> contacts** and a **military profile's commanding officer/agent**, i.e.
> third parties' data nested under the tenant record, not just the tenant's
> own. Doesn't overturn the conclusions below on its own (partial SSN + a DL
> number still fall short of most state breach-notification triggers), but
> the next time this assessment gets revisited, do it against the real field
> list in [[QMS API - Domain Model & PII]], not this paragraph's shorthand.

- **CCPA/CPRA (California)** — plausible, not certain. Storage tenants
  are often individual consumers, and name+contact info is personal
  information under CCPA's definition. Complicating factor: UnitPrep is
  closer to a data *processor* acting on the storage facility operator's
  behalf (via QMS exports) than the system of record for those tenants —
  right-to-know/right-to-delete requests would likely flow through the
  primary QMS system, not this tool directly. Worth a real determination
  once UnitPrep's actual data-retention footprint (does it persist tenant
  PII, or only process it transiently during dedup?) is nailed down.
- **GDPR** — deferred, no EU users today. Already tracked in [[Auth &
  Persistence Index]]'s "Trigger-gated, no trigger yet" section (the
  erasure/anonymize path) — not duplicating that entry here, just
  cross-referencing it as the same underlying gap CCPA would also want
  closed.
- **State breach-notification laws** (all 50 US states, various
  thresholds) — a baseline legal duty regardless of any formal audit.
  Worth knowing: plain contact info alone (name + email/phone, no
  SSN/financial account/CC) does **not** trigger notification under most
  state definitions — this is a lower-stakes data profile than it might
  sound, not a reason to be careless about it.
- **GLBA (Gramm-Leach-Bliley)** — almost certainly **does not apply**.
  This is a financial-institution privacy framework; Quikstor is
  self-storage software, and tenant payment history is a storage
  operator's business record, not "nonpublic personal financial
  information collected by a financial institution." Named here to rule
  it out explicitly rather than leave it unconsidered.
- **PCI-DSS** — **does not apply to UnitPrep specifically** — no
  cardholder data is stored or processed here. (The underlying
  billing/POS system elsewhere in Quikstor's stack may well be in PCI
  scope; that is a different system's problem.)
- **SOC 2 (Type II) — the more likely practical near-term ask.** Unlike
  SOX (which needs a specific financial-reporting trigger) or a specific
  privacy law (which needs specific data-residency facts), SOC 2 is
  *voluntary* but is very commonly the **first** audit-shaped thing a
  growing B2B software vendor gets asked for — by a customer's
  procurement/security team during vendor due diligence, not by a
  regulator. It maps almost 1:1 onto the same controls already discussed
  (access control, logging, change management, availability). If
  Quikstor's storage-software product (UnitPrep or the broader platform)
  is ever sold/licensed externally, this is the realistic first ask,
  probably well before SOX becomes relevant at all.

**Not legal advice** — this is engineering input to a compliance
conversation. The actual scoping call belongs with whoever owns
Quikstor's compliance/legal function, when the time comes.

## Availability & Recovery — explained, not yet assessed

Boris asked what this actually means, in plain terms:

- **Availability** = can people use the system when they need to (uptime).
- **Recovery** = if something destroys or corrupts data — a bad deploy, an
  accidental `DELETE`, a disk failure, ransomware, a data-center outage —
  can you get back to a known-good state, and how much would you lose in
  the process. Two numbers usually asked for: **RTO** (Recovery Time
  Objective — how long until back up) and **RPO** (Recovery Point
  Objective — how much recent data, if any, is lost — e.g. "up to the
  last 5 minutes of writes").
- **Backups vs. disaster recovery are different tiers of the same
  question.** Backups/point-in-time-restore (can I undo a mistake or
  restore after a crash) is the cheap, usually-already-included tier —
  Neon (the Postgres host) almost certainly provides this as part of its
  managed service already; **worth a 10-minute check of Neon's actual
  PITR/backup settings**, not a project. True disaster recovery
  (automatic failover to a *different data center* if one goes down
  entirely) is the expensive, advanced tier Boris was actually picturing
  — and correctly guessed it's closely related to the CI/CD/DevOps
  question below: low priority at this stage, likely someone else's
  problem eventually.

**Status: not assessed this session.** The cheap check (confirm Neon's
backup/PITR settings) is worth doing whenever convenient; true
multi-region DR is explicitly deferred, same tier as CI/CD below.

## CI/CD & DevOps — explicitly deferred, Boris's call

Not necessary at this stage: the product isn't at POC yet, the team
doesn't know it well, and this will likely be delegated to whichever team
already handles CI/CD/DevOps for Quikstor's main software, to stay in
sync with existing process rather than inventing a parallel one.
Revisit once the product has real users and a team hand-off is actually
happening — not before.

## Process documentation & periodic-review bureaucracy — flagged, not urgent

Same treatment as CI/CD: real, will matter eventually (see the SOX
segregation-of-duties gap above, which is partly a "nobody's proven the
review is happening" problem), but not worth investing in at pre-POC
stage. Flagged here so future-Claude/future-Boris doesn't have to
rediscover that this was already considered and deliberately deprioritized
— not forgotten.

## Related

- [[Onboarding Orchestrator Kickoff — Session Log]] — the 2026-08-07
  PII/compliance architecture backlog review (9 trigger-gated items) that
  cross-references this note's data-profile assessment
- [[Roles & Permissions — Design Discussion]] — the segregation-of-duties
  gap named above is really a roles problem; that's where the actual fix
  lives
- [[Auth & Persistence Index]] — erasure/anonymize path (the GDPR/CCPA
  shared gap), trigger-gated items
- [[Architecture]], [[Database Schema]] — what the SOC 2/SOX controls
  above are actually assessed against
