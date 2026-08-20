---
date: 2026-07-30
description: "**Trigger: raise this when any of these first happens — an EU-based user is added, an enterprise security review is scheduled, or a customer asks for…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-30T22:23:01.254Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# UnitPrep has no personal-data erasure path, deliberately — raise the anonymize design at the first EU user, enterprise security review, or customer DPA

**Trigger: raise this when any of these first happens — an EU-based user is added, an enterprise security review is scheduled, or a customer asks for a DPA.** Not before; Boris deferred it consciously on 2026-07-30 and the deferral is sound.

**The state.** `auth.users` supports only soft delete (`deleted_at` + `deletion_reason`), which leaves `email`, `first_name` and `last_name` in place indefinitely. Hard deletion is impossible for any account with audit history, because `auth_audit_logs.actor_user_id` and `.target_user_id` are `ON DELETE RESTRICT` and the table is append-only by trigger — no role can delete either the audit row or the user, including the owner. So there is **no way to erase a person's personal data at all**.

**Why this is not the criticism it looks like.** An append-only audit trail with non-deletable actors is *expected* in SOC 2 / PCI / HIPAA / SOX contexts; a reviewer would treat it as a control, not a smell. It is also a non-repudiation property rather than a security one — it stops history being unwritten, which is a different guarantee from preventing unauthorized action, and worth naming precisely when defending it.

**What a competent reviewer will actually raise: right to erasure** (GDPR Art. 17, CCPA/CPRA analogues). Audit logs normally survive an erasure request under legitimate-interest or legal-obligation grounds, but the standard expectation is that PII can be **anonymized or pseudonymized while the trail's integrity is preserved**. That capability does not exist here.

**The chosen remedy, decided in advance so it is not re-litigated under pressure: the hybrid.** Keep the foreign keys; add an anonymize path that tombstones name and email on the user row, or encrypts PII under a per-user key and destroys the key (crypto-shredding). Audit rows keep pointing at a real id, the person stops being identifiable. This is what regulated shops typically land on.

**Explicitly rejected**: dropping the FKs in favour of storing denormalized identity snapshots (email/name as text at event time) in each audit row. It does make users deletable and keeps the trail readable — it is a common and defensible pattern — but it trades a referential guarantee for PII scattered through the log, which is the wrong direction when the motivation is data protection.

**Why deferring is safe rather than lazy**: the hybrid is purely *additive*. Adding an anonymize function later changes no existing table, constraint or query, so nothing is being locked in. That is the specific fact that justifies waiting, and it is worth re-checking before relying on it — if a future change makes PII load-bearing somewhere else (denormalized into another table, cached, exported), the additive property stops holding and the cost of deferral goes up.

**Generalises as**: "we cannot delete a user" is defensible; "we cannot make a user unidentifiable" is the part that fails a data-protection review. Check which of the two a system actually has before claiming compliance readiness.

## How this is known

Schema facts verified against the dev DB branch 2026-07-30: pg_constraint shows confdeltype='r' (RESTRICT) on both auth_audit_logs_actor_user_id_fkey and auth_audit_logs_target_user_id_fkey; an attempted DELETE of an invited user returned 'violates RESTRICT setting of foreign key constraint auth_audit_logs_target_user_id_fkey'; auth.users has deleted_at/deletion_reason (enum: offboarding, emergency) and no anonymize or scrub mechanism of any kind. The deferral and the choice of the hybrid remedy are Boris's explicit decisions, recorded the same day: 'this is my favorite option ... but you're right, now's not the time to worry about it.'

## Related

- [[Database Schema]]
- [[Phase 2 Progress]]
