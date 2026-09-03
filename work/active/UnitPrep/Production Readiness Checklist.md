# Production Readiness Checklist

Running list of decisions we deliberately deferred during development, that need a real answer before UnitPrep/Onboarding Orchestrator goes live for real users. Add to this any time we consciously say "fine for now, revisit before shipping" — don't let those decisions evaporate into scrollback.

## Open items

### Activity Logs retention (added 2026-09-02)
**Decision deferred**: Activity Logs (`client_ops.audit_log`, surfaced at `/admin/activity-logs`) currently retain everything forever, no pruning/archival policy — same as today's Security Logs (`auth.audit_log`). Shipped 2026-09-02, see [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]].

**Why this needs a real answer before shipping**: Activity Logs will be far higher-volume than Security Logs — every dedup run, every Unit Group run, every sync tick (soon hourly-configurable), every client/facility creation all write a row. Unbounded retention on a fast-growing table has real costs (storage, query/PDF-export performance, backup size) that security audit logs never had at the same scale.

**What to decide when we get there**: a retention window (e.g. keep N months, archive/export older rows), or confirm unlimited retention is actually fine at expected scale and this can be closed out.

### Encrypted Merchant Account facility-level secrets have no read path (added 2026-09-03)
**Decision deferred**: EIN, Bank Routing/Account Number, and the QMS credential bundle (QUIKSTOR Password, QSS Web PIN, Pinpad User ID, QSS API Pin, MID, Account ID) are already captured and encrypted (`facility_merchant_accounts.encrypted_secrets`) whenever a Merchant Account run is ingested — but nothing decrypts or displays them anywhere. `decrypt_party_pii` exists for owner/signer PII; no equivalent exists for this bundle. See [[Session 2026-09-03 — Live Testing Fixes, Transaction Leaks & Field Reference Help]] and the Field Reference help table's own `not_yet_mapped` rows.

**Why this needs a real answer before shipping**: this is exactly the kind of data (bank account, EIN, live system credentials) the 2026-08-07 PII/compliance review anticipated — it's real and already stored, just not surfaced yet. Once a UI is built to show it, the masking/reveal treatment and who's allowed to see it (RLS already gates this table to `onboarding_manager`/`department_manager`, but a UI-level "who can click Show" decision is separate) both need to be deliberate, not an afterthought bolted onto an existing DetailSection.

**What to decide when we get there**: whether bank account/EIN should ever render in the UI at all (even masked), or whether "captured, never displayed in OO, exportable only via a deliberate separate flow" is the right posture for this specific data class.

## Format for future entries

```
### <short title> (added <date>)
**Decision deferred**: what we're doing now, and why it's provisional.
**Why this needs a real answer before shipping**: the actual risk/cost of leaving it as-is in production.
**What to decide when we get there**: the concrete options, if known.
```
