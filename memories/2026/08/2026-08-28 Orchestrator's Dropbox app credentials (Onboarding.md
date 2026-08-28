---
date: 2026-08-28
description: "Live credentials for the \"Onboarding Orchestrator\" Dropbox app, currently stored in `unitprep-api/.env.local` (gitignored, not committed) and used by…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T17:34:47.273Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# Orchestrator's Dropbox app credentials (Onboarding Orchestrator app, App Console app id 8175635)

Live credentials for the "Onboarding Orchestrator" Dropbox app, currently stored in `unitprep-api/.env.local` (gitignored, not committed) and used by `src/dropbox::DropboxClient`. Recorded here as a personal reference in case the .env.local copy is ever lost, not as a substitute for it.

```
DROPBOX_APP_KEY="9uohq103tadfku1"
DROPBOX_APP_SECRET="65rvmkp3oqeunuh"
DROPBOX_REFRESH_TOKEN="HKj8b9yY8lsAAAAAAAAAARQVtVbt7NGwzOxx2SV6sS0UM4hDjBxJNUtbvJmAXnAn"
DROPBOX_ROOT_NAMESPACE_ID="13656904209"
DROPBOX_ROOT_PATH="/QS Fileserver/Shared/QMS Onboarding"
```

Field meanings: APP_KEY/APP_SECRET identify the Dropbox app itself (App Console, Full Dropbox scope -- see Orchestrator's Dropbox integration: Full Dropbox scope, env-configurable root path, planned QMS Onboarding quick-access button for why App-folder scope wasn't usable). REFRESH_TOKEN was minted once via the OAuth2 authorization-code flow (token_access_type=offline) and does not expire on its own -- it's what the running app actually holds and exchanges for short-lived access tokens on every call. ROOT_NAMESPACE_ID is the Dropbox Business Team Space namespace id the QMS Onboarding folder lives under (must be sent as the `Dropbox-API-Path-Root` header on every API call, or paths silently resolve against the wrong namespace). ROOT_PATH is the app-level convention boundary -- Dropbox's Full Dropbox scope enforces nothing narrower than "this account," so this path is enforced only by Orchestrator's own code (`api::dropbox_browse`'s root check).

**Security note, since this is a plaintext note in a vault rather than a permission-scoped secret store**: APP_SECRET and REFRESH_TOKEN are live bearer credentials -- anyone with either can act as this Dropbox app/account. Treat this note with the same care as the .env.local it mirrors. If the vault is ever exported, synced somewhere less trusted, or shared, rotate both (revoke the refresh token via a fresh OAuth flow; the app secret can be rolled from the App Console) rather than assuming exposure is fine because "it's just notes."

## How this is known

Read directly from the live unitprep-api/.env.local file on 2026-08-28; these are the exact values the running application uses today.
