---
date: 2026-08-28
description: "Design decisions made while scoping Orchestrator's (formerly unitPrep) Dropbox integration, as of 2026-08-21: - Access model: single-user,…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T14:43:30.709Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# Orchestrator's Dropbox integration: Full Dropbox scope, env-configurable root path, planned QMS Onboarding quick-access button

Design decisions made while scoping Orchestrator's (formerly unitPrep) Dropbox integration, as of 2026-08-21:

- Access model: single-user, token-based (no per-end-user OAuth consent flow) — Orchestrator's backend holds one Dropbox credential for the whole app.
- Access type: Full Dropbox (not App-folder), because the target folder (`/QS Fileserver/Shared/QMS Onboarding`, a Dropbox Business Team-Space folder, namespace root id 13656904209) already exists and is heavily relied on by other people — it cannot be moved/renamed into an App-folder sandbox (`/Apps/<name>/`) the way App-folder access would require. Consequence: Dropbox enforces no folder boundary on this token — it can reach anything the authorizing user (bmaksimov@quikstor.com, on the "KoBre" Dropbox Business team) can see. The QMS-Onboarding-only scoping is enforced entirely in Orchestrator's own application code, not by Dropbox.
- The app ("Onboarding Orchestrator" in Dropbox's App Console, app id 8175635) needed these scopes explicitly enabled on the Permissions tab and submitted before any token gained them: files.metadata.write (implies .read), files.content.write, files.content.read, sharing.write (implies .read), account_info.read. A token generated before submitting scope changes does NOT retroactively gain new scopes — must regenerate after submit.
- No Dropbox Business admin approval was required to authorize this app as a regular (non-admin) team member — the OAuth/token flow went through cleanly. (Team's third-party-app policy was not locked down; this could differ for other Dropbox Business teams.)
- The QMS Onboarding root folder path is meant to be configurable via env var (e.g. `.env.local`, not hardcoded), so it can change without a code deploy. Explicitly decided NOT to build an admin UI/settings screen for this — Boris judged that overkill for a small, dev-managed, single-folder, single-tenant concept app at this stage; revisit only if Orchestrator grows to multi-tenant/multi-folder needs.
- Forward-looking UX idea (not yet implemented, "a bit ahead of myself" per Boris): wherever Dropbox integration appears in the Orchestrator UI, add a dedicated "QMS Onboarding" button next to the general Dropbox button that opens that specific folder directly.
- Credential handling: moved from Dropbox's short-lived "Generate access token" (Settings tab, ~4hr expiry, fine only for manual smoke testing) to a real OAuth2 authorization-code flow with `token_access_type=offline` to mint a non-expiring refresh_token, stored in env config alongside the app key/secret — never hardcoded or committed.

## How this is known

Verified live against the real Dropbox API during this session: tested get_current_account, list_folder at multiple paths (including the exact QMS Onboarding path), and the scope-enforcement error message, using real tokens generated in the Dropbox App Console for this app.
