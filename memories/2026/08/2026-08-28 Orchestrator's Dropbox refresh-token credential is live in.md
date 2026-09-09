---
date: 2026-08-28
description: "As of 2026-08-28, the Dropbox OAuth2 refresh-token flow described in Orchestrator's Dropbox integration: Full Dropbox scope, env-configurable root…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T14:47:14.806Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# Orchestrator's Dropbox refresh-token credential is live in unitprep-api/.env.local

As of 2026-08-28, the Dropbox OAuth2 refresh-token flow described in Orchestrator's Dropbox integration: Full Dropbox scope, env-configurable root path, planned QMS Onboarding quick-access button is done, not just planned: DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN, DROPBOX_ROOT_NAMESPACE_ID, and DROPBOX_ROOT_PATH are all set in unitprep-api/.env.local (gitignored, not committed). The refresh token was minted via the OAuth2 authorization-code flow with token_access_type=offline and verified end-to-end: exchanged for a fresh short-lived access_token via grant_type=refresh_token, and that access token successfully listed the real QMS Onboarding folder contents. All throwaway manual test tokens generated earlier in this process (via the App Console's "Generate access token" button) were revoked via POST /2/auth/token/revoke once superseded. No Rust code has been written yet to actually consume these env vars in unitprep-api -- that (the thin Dropbox HTTP client, token refresh helper, and file operations) is the next real implementation step, not this credential-provisioning one.

## How this is known

Performed and verified live in this session: OAuth code exchange, refresh-token exchange, and a real files/list_folder call against the QMS Onboarding path all returned successful (HTTP 200) responses.
