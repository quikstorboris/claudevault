---
date: "2026-09-28"
description: "Follow-up to the durable-session-store work (v1.9.39): moved dropbox_configuration/process_street_settings out of client_ops into a new integrations schema, added RUNBOOK.md, ran a cheap live-DB FK-index audit, and started brain/CI Backlog.md"
tags: [work-note, unitprep, infra]
status: active
quarter: Q3-2026
project: unitprep
---

# Session 2026-09-28 — client_ops Schema Split, Runbook, Live-DB Audit & CI Backlog

Continuation of the [[Session 2026-09-24 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation|Grok review]] follow-through, after `v1.9.39`'s durable session store work shipped. Boris's priority order: `client_ops` schema modularity first, migration squash next, CI work deferred to a backlog note, live-DB EXPLAIN only if cheap, demo runbook if cheap.

## `client_ops` schema modularity — smaller than it looked

Grok's review (and an earlier doc-accuracy pass) had characterized `client_ops` as having accreted "7+ concerns" — sounded like it needed a big reorganization. Investigation showed otherwise: `src/client_ops/mod.rs`'s own doc comment already defines the domain precisely ("tooling an Onboarding Manager uses day to day"), and 5 of the 7 tables (`audit_log`, `tool_runs`, `vendor_format`, `qms_tag`, `tag_pattern`) genuinely belong there by that definition — not drift, intentional design. The real mismatch was narrow: `dropbox_configuration` and `process_street_settings` have been gated by the `integrations.manage` permission (not `client_ops.perform`) since [[Session 2026-09-09 — Admin-Only Integrations Nav, integrations.manage Permission, and Editable Dropbox Settings]], but their schema namespace never followed — the migration from that session literally documents the permission move in a comment without moving the table.

**Fix shipped as `v1.9.40`**: `ALTER TABLE ... SET SCHEMA` moved both tables into a new `integrations` schema (preserves RLS/triggers/indexes/FKs unchanged), ~21 Rust SQL-string references updated across 7 files, and `scripts/setup_app_service_role.sql` got a new guarded grant block — schema-level `USAGE` does **not** survive a table's `SET SCHEMA` the way table-level grants do, caught by testing the moved tables' real queries against the dev DB as `app_service` (not just checking the migration applied cleanly). Verified: data intact with original timestamps (not recreated), full workspace suite green, clippy clean.

**Next**: migration squash (168+ files) — Boris's explicit next-in-line item, not started this session.

## `RUNBOOK.md` added

One page: required config, the four distinct session lifetimes and which are durable as of `v1.9.39`, the single-instance deployment assumption, stuck-deploy recovery steps. Cheap, Boris approved directly.

## Live-DB FK-index audit — cheap, done

Grok's suggested "index/RLS/orphan audit" was gated on Neon compute cost — checked via the Claude browser extension (already logged into the Neon console): **93.52 of 100 free-tier compute-hours used since Sep 1** (93.5%, confirming Boris's "above 90%" concern was real). A single lightweight catalog query (57ms) found 13 foreign keys without a covering index, mostly "who touched this" audit columns (`created_by`/`updated_by`/`actor_user_id`) pointing at `auth.users`. A second query (245ms) showed the largest table in the whole database has **1,879 rows**. Verdict: real gaps, but not urgent — a sequential scan on <2000 rows is microseconds. Documented, not fixed, matching this project's own "don't over-engineer for load that doesn't exist yet" principle (see [[Dev Principles]] #7). Total live-DB cost: ~300ms.

## `neonctl` CLI auth broken in this WSL session

`neonctl projects list` failed with a keyring error (`Could not read the OS keyring item for profile "DEFAULT"`) — non-interactive WSL session can't complete the interactive browser auth flow it wants. Worked around by using the Claude browser extension directly against `console.neon.tech` (Boris had it already logged in) instead. Worth trying `neon auth --profile DEFAULT` interactively next time this is needed from a real terminal, or just defaulting to the browser-extension path.

## `brain/CI Backlog.md` started

New note for CI-shaped ideas identified during normal development but not implemented (solo developer, no CI infra yet) — distinct from [[Compliance & Process Readiness]]'s broader "CI/CD is deliberately deferred" governance decision. First entry: enforcing `unitprep-ui`'s generated types stay in sync with their Rust source (from the same Grok review). Standing rule: add future CI ideas here instead of building them, unless Boris explicitly asks.

## Related

- [[Compliance & Process Readiness]] — the broader CI/CD deferral decision
- [[CI Backlog]] — the new backlog note itself
- [[Dev Principles]] — "don't over-engineer for load that doesn't exist yet," applied to the FK-index findings
- [[Session 2026-09-09 — Admin-Only Integrations Nav, integrations.manage Permission, and Editable Dropbox Settings]] — where the permission moved without the schema
