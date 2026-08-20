---
date: 2026-07-27
description: "Priority-ordered build plan for OO auth (phases 1-4), trigger-gated deferred initiatives (Cloudflare Access, KMS, ESP), and Neon/infra setup status as of 2026-07-20."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — Build Plan & Infra Checklist

Companion to [[Architecture]] — the sequencing and infra side of the same 2026-07-20 planning conversation.

## Priority order — sequenced by dependency, not just importance

1. **Foundation** — Provision Postgres/Neon; design the users schema with an extensible-but-currently-single-value `role` column (Admin only for v1). Still worth deliberately deciding the DB connection/role strategy up front (the RLS caveat in [[Architecture]]) even for v1's simpler single-role case. Wire up `sqlx` from `unitprep-api`. *(Done — see [[Database Schema]].)*
2. **Core identity & sessions** — Self-hosted auth (`webauthn-rs` + TOTP fallback) behind a swappable interface; opaque session token + httpOnly cookie; mandatory first-login enrollment folded into the same login flow.
   - **User invitation for v1, confirmed**: an Admin creates a user record and generates a one-time "first login" setup link, shared manually via internal comms (Teams) — no ESP involved. Automated email delivery is a later enhancement once an ESP is chosen.
   - **Bootstrap gap**: no Admin exists yet to generate the very first invite, so this phase needs an explicit one-time bootstrap path (setup script or first-run flow gated behind an env var/local-only check).
   - Basic audit-event capture wired in from day one, so there's no gap in the record from turning logging on after the fact.
   - *(In progress — see [[Phase 2 Progress]].)*
3. **Admin UI** — `Admin` > `Security` tabs (Authentication Policy, Users, Groups, Audit Logs), built once there's real backend data behind each tab. *(Not started.)*
4. **Step-up auth** — The general re-authentication mechanism can be built once phase 2 exists; specific gated actions depend on the deferred bucket below — nothing sensitive to gate yet since QMS/Dropbox credential fields are still placeholders. *(Not started.)*

## Trigger-gated, not fixed-position (revised 2026-07-20)

Boris initially asked for Cloudflare Access (ZTNA) to be pinned as a fixed "phase 3." On reflection, agreed to keep it out of the fixed numbered sequence instead: its start date is gated by a hosting decision that doesn't exist yet, so numbering it alongside work with no external blocker would misrepresent how decided the sequence actually is. It stays tracked as its own **named** initiative, just without a fixed slot. Same logic applies to the rest of this bucket:

- **Cloudflare Access (ZTNA)** — once a hosting decision is made. Boris trusts Cloudflare specifically (QMS itself is Cloudflare-hosted) but wants it folded into a broader "third-party involvement in general" conversation, not decided as a one-off.
- **KMS/secrets-at-rest** — once real QMS/Dropbox credentials exist to protect.
- **Real ESP integration** — once SendGrid-vs-SES is resolved and something actually needs to send beyond the admin-invite-link workaround in phase 2.

## Neon setup status (2026-07-20) — no secrets stored here, by design

Region confirmed: **Oregon (us-west-2)** — closest to Boris (California); branches inherit the parent project's region, so this applies to both dev and prod branches. **Neon Auth (the bundled identity add-on) was explicitly declined** — it would provision its own user/session schema, directly competing with the self-hosted plan.

Two Neon-specific operational facts worth remembering:
- **Branch auto-delete/expiration is a fixed calendar countdown from creation, not an inactivity timer** — deletes N days after creation regardless of activity. The primary `dev` branch must have this set to "never"/no expiration.
- **The "how to copy data" choice when branching is currently moot** (production is empty) but stops being moot once production holds real client data: any future dev/test branch created off populated production should use **"Branch & anonymize data"** (or schema-only) — never raw data-and-schema — to keep real client PII out of lower-security dev environments. Flag again when the first such branch is created post-launch.
- **Dev and prod branches currently share the same DB role/credentials** (`neondb_owner`, same password) — normal Neon default, not a mistake, but no credential-level separation between environments today. Revisit before real production go-live / before production holds real client data: whether dev and prod should have genuinely distinct passwords/roles.

**Connection string handling** — deliberately not stored in any memory file. `unitprep-api/.env.local` (confirmed git-ignored) holds four named parameters Boris fills in manually: `NEON_DEV_DATABASE_URL` (pooled), `NEON_DEV_DATABASE_URL_DIRECT` (direct, migrations), `NEON_PROD_DATABASE_URL` / `NEON_PROD_DATABASE_URL_DIRECT` (same split, prod branch, not yet used by anything). `.env.local` also holds a pre-existing, seemingly-stray `NEXT_PUBLIC_API_URL` line — left alone, not understood/touched.

**Status: fully done, 2026-07-20.** `dev` branch created (auto-delete set to "never"), all four `NEON_DEV_*`/`NEON_PROD_*` values filled in and verified (one typo caught and fixed), `psql` installed and tested against both branches, `sqlx-cli` confirmed installed (v0.9.0). Only remaining wiring: a dotenv-loading mechanism for Rust (e.g. `dotenvy`) in `main.rs` — genuine Phase 1 implementation work, not infra setup.

## Infra/tooling checklist to actually start development (2026-07-20)

**Needed now, blocks phase 1 — ALL DONE as of 2026-07-20**:
- **Neon** — project created (Oregon/us-west-2), `dev` + default/prod branches live, connection strings captured and verified in `.env.local`.
- **`sqlx-cli`** — installed (v0.9.0).
- **`psql`** — installed, live connections tested against both branches.

**Explicitly NOT needed yet — correcting an assumption Boris was about to act on**:
- **Cloudflare** — no account needed now; Phase 1/2 is 100% local dev with no edge-network layer, and Access itself is trigger-gated on an undecided hosting decision.
- **Vercel** — not needed; development happens locally, hosting is a separate still-undecided question.

No new WebAuthn-specific setup needed — `localhost` is a recognized secure context for WebAuthn, Windows Hello already works against it in Chrome/Edge with zero extra installation. All new Rust dependencies (`webauthn-rs`, `totp-rs`, `sqlx`) are plain `Cargo.toml` additions.

## See also

- [[Architecture]] — the design decisions this plan implements.
- [[Database Schema]] — Phase 1 output.
- [[Phase 2 Progress]] — current status against step 2 above.
