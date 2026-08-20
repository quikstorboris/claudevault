---
date: 2026-08-03
description: "Boris asked to be reminded of this specifically once the auth frontend work is ready for a wrap-up/QA pass, with concrete test steps provided at that…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-03T21:23:42.354Z"
scope: project
projects: ["unitprep-ui"]
confidence: verified
---

# unitprep-ui manual QA pending: invite-redemption 'already signed in' guard needs a real click-through before the auth frontend is considered done

Boris asked to be reminded of this specifically once the auth frontend work is ready for a wrap-up/QA pass, with concrete test steps provided at that time (not before). Recording the steps now, while the implementation is fresh, rather than reconstructing them later from a decayed context.

What needs testing: app/invites/[token]/page.tsx's guard against the stale-session-hijacks-ceremony gotcha (see Testing a WebAuthn invite/registration flow: a stale session cookie silently hijacks the ceremony, and incognito hides password-manager passkeys). The code path is verified by reading only -- the automated browser tool used throughout this build cannot complete a real WebAuthn ceremony, and it runs as a separate, unauthenticated context from Boris's own browser, so only the signed-out flow has actually been exercised live.

Draft test steps for when this is raised:
1. In a REAL browser (not the Claude Code browser pane), sign in normally via /login with a real passkey.
2. Generate a fresh invite token for a DIFFERENT account -- via `unitprep bootstrap-admin --reissue-invite <email>` (or the admin invites endpoint once that UI exists), for an account that is not the one currently signed in.
3. While still signed in as the first account, navigate to /invites/<token> for the second account.
4. Confirm the page shows the warning ("You're already signed in on this browser... sign out first") and the 'Sign out and continue' button -- NOT the 'Create your passkey' form. This is the specific thing that was previously silently wrong (see the linked gotcha): getting this right is the actual point of the test.
5. Click 'Sign out and continue'. Confirm the UI transitions to the normal passkey-creation form.
6. Complete the ceremony. Confirm it was applied to the SECOND (invited) account, not the first -- check via signing back in afterward and comparing /health/whoami's user_id, or by querying auth.webauthn_credentials directly for which user_id gained a new row.

This note should be treated as the first entry in what will likely become a small running list of 'needs a human, not automation' QA items for this frontend build (TOTP enrollment's QR-code-scan-with-a-real-phone step is a near-certain second one) -- check for sibling notes with a similar title pattern when this is eventually raised, so nothing gets tested in isolation and forgotten.

## How this is known

Boris's explicit request in conversation on 2026-08-03 to remember this and be reminded later with test steps prepared in advance.
