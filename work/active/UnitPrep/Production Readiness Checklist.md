# Production Readiness Checklist

Running list of decisions we deliberately deferred during development, that need a real answer before UnitPrep/Onboarding Orchestrator goes live for real users. Add to this any time we consciously say "fine for now, revisit before shipping" — don't let those decisions evaporate into scrollback.

## Open items

### Activity Logs retention (added 2026-09-02)
**Decision deferred**: Activity Logs (`client_ops.audit_log`, surfaced at `/admin/activity-logs`) currently retain everything forever, no pruning/archival policy — same as today's Security Logs (`auth.audit_log`). Shipped 2026-09-02, see [[Session 2026-09-02–03 — Confirmation Screen, Re-sync, Activity Logs & Client Record UI]].

**Why this needs a real answer before shipping**: Activity Logs will be far higher-volume than Security Logs — every dedup run, every Unit Group run, every sync tick (soon hourly-configurable), every client/facility creation all write a row. Unbounded retention on a fast-growing table has real costs (storage, query/PDF-export performance, backup size) that security audit logs never had at the same scale.

**What to decide when we get there**: a retention window (e.g. keep N months, archive/export older rows), or confirm unlimited retention is actually fine at expected scale and this can be closed out.

## Format for future entries

```
### <short title> (added <date>)
**Decision deferred**: what we're doing now, and why it's provisional.
**Why this needs a real answer before shipping**: the actual risk/cost of leaving it as-is in production.
**What to decide when we get there**: the concrete options, if known.
```
