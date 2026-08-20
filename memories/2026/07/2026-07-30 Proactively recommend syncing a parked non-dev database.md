---
date: 2026-07-30
description: "When a project keeps a provisioned-but-unused second database branch (a `prod` branch with no deployment, a staging branch nobody hits), the working…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-30T15:23:27.250Z"
scope: general
projects: []
confidence: verified
---

# Proactively recommend syncing a parked non-dev database branch when the pending migration count starts accumulating — do not wait to be asked

When a project keeps a provisioned-but-unused second database branch (a `prod` branch with no deployment, a staging branch nobody hits), the working default is **dev-only**: don't apply each migration to both, because doing so turns every schema change into a two-destination chore for no present benefit.

But the failure mode of "dev-only" is silent accumulation. Drift is cheap at 1-2 migrations and expensive at 20, because by then nobody remembers which ones carried data assumptions, which needed a manual script re-run alongside them, or whether they still apply in order against a branch that has diverged.

**So: periodically surface it as a recommendation rather than waiting to be asked.** Good moments to raise it — a version bump or release boundary, the end of a coherent feature, a migration that changes grants or roles (those often pair with a manual setup script that also needs re-running), or simply when the pending count crosses a handful. Report the actual number pending rather than a vague "we should sync sometime".

Keep it a recommendation, not an action: applying migrations to a branch named `prod` is the user's call even when that branch is empty and unused, and an agent that syncs it unprompted has widened scope on the most consequential-sounding target available.

Two things that make the sync safe to defer at all, and are worth confirming still hold before relying on this: migration tooling that **fails loudly on drift** rather than half-applying (sqlx refuses to run when a recorded checksum no longer matches the file), and a role/grant setup script that is **order-independent and idempotent**, so a long-parked branch can be brought up in one pass rather than needing archaeology.

## How this is known

Boris's explicit instruction 2026-07-29 on unitprep-api, after I had provisioned the prod Neon branch unprompted and then immediately let dev run ahead of it: "i would not mind if you occasionally stop and recommend DB sync when you think it's appropriate and which would keep us from accumulating the sync volume over time." The two safety properties named above were both established in that same session and verified against the live branches.

## Related

- [[RLS Implementation]]
- [[Build Plan & Infra Checklist]]
