---
date: 2026-08-27
description: "A prior memory (Proactively recommend syncing a parked non-dev database branch when the pending migration count starts accumulating — do not wait to…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-27T21:02:57.996Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# unitprep-api's Neon "prod" branch is NOT an empty/unused scaffold — it holds real data

A prior memory (Proactively recommend syncing a parked non-dev database branch when the pending migration count starts accumulating — do not wait to be asked) and this repo's own `.env.local` comments both describe the Neon `prod` branch as "provisioned but unused, no deployment exists" -- Boris directly corrected this 2026-08-27: prod is NOT empty, and he has never personally run a dev-to-prod migration sync himself (a prior Claude session apparently did this for him, which is why he doesn't know the procedure and isn't comfortable doing it unsupervised).

Verified directly via a read-only query against NEON_PROD_DATABASE_URL_DIRECT: `auth.users` = 1 row, `auth.user_invites` = 2 rows, `client_ops.qms_tag` = 120 rows. So prod carries at least one real user account and a full, real tag catalog -- not zero rows across the board the way a truly throwaway/scaffold branch would be.

What this means going forward: do NOT treat unitprep-api's prod Neon branch as safely resettable/discardable (a "Neon branch reset from dev" suggestion is actively dangerous here, not just unnecessary) and do NOT assume a migration is risk-free there just because it's already been safely applied to dev -- any migration that DELETEs or UPDATEs existing rows (as opposed to pure CREATE TABLE / ADD COLUMN / INSERT-only additions) needs its actual effect on prod's real, possibly-diverged data checked before running, not just assumed identical to dev's outcome. Treat prod exactly like a real customer-facing production database when reasoning about risk, even though no CI/CD pipeline or deployment config currently points at it (confirmed: no fly.toml/render.yaml/Dockerfile/GitHub Actions workflow/systemd unit references NEON_PROD anywhere in the repo) -- something is clearly writing to and relying on it outside of what's visible in the codebase.

Before running any prod migration in the future: read every pending migration's actual SQL first (not just its filename), separate schema-only changes (ADD COLUMN, CREATE TABLE, pure INSERT of new rows) from ones that DELETE/UPDATE existing rows, and verify the latter's actual precondition (e.g. "is this specific row present") against prod directly before running -- don't extrapolate from dev's data shape.

## How this is known

Ran `SELECT count(*)` against auth.users, auth.sessions, auth.webauthn_credentials, auth.user_invites, auth.auth_audit_logs, client_ops.qms_tag, and client_ops.audit_log directly on NEON_PROD_DATABASE_URL_DIRECT: 1, 0, 0, 2, 0, 120, 0 respectively.
