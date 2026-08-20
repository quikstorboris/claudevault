---
date: 2026-08-04
description: "The Users tab's \"Recover account\" action (unitprep-ui, shipped 2026-08-04 as part of Phase I item 8) already lets any admin revoke-and-reissue an…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-04T17:06:26.455Z"
scope: project
projects: ["unitprep-ui", "unitprep-api"]
confidence: verified
---

# Pending: test admin-recovers-fellow-admin with a real second admin account, once Boris creates one

The Users tab's "Recover account" action (unitprep-ui, shipped 2026-08-04 as part of Phase I item 8) already lets any admin revoke-and-reissue an invite for any other `active` user -- which, since `Role` has exactly one variant (`admin`) in v1, already means "one admin unlocks a fellow admin who lost their passkey." It has been built and live-tested end-to-end against the real dev database, but only using a synthetic test-fixture account (`invite-test@quikstor.com`) as the "fellow admin" being recovered -- never with a second real person.

**Trigger**: the next time Boris mentions creating another real user/admin account (rolling out the platform to more people, inviting a colleague, anything of that shape), that is the moment to surface this and offer to walk through/confirm the recovery flow works for a real second admin, not just the test fixture. He said explicitly he'll test it himself at that point and asked for this reminder rather than pre-building anything further now.

**Distinct from, and does not close, Phase I item 9** ("confirm the single-admin break-glass path") -- that is specifically the *no other admin exists* case, which this multi-admin recovery feature cannot help with by definition. Item 9 remains open and untouched; see the Auth hardening two-phase plan note.

##### Related

- [[Phase 2 Progress]]

## How this is known

Boris's own message 2026-08-04: confirmed the Users tab's recovery action is the multi-admin capability he meant, agreed it should stay as-is, and explicitly asked for a vault reminder tied to the future trigger of creating other real users, rather than further work now.
