---
date: 2026-10-19
description: "What Claude can and cannot reach in Sentry and Grafana from the desktop Code-tab session, and by which route (connectors, Sentry CLI, logcli, Grafana MCP script, Chrome); the Sentry token-type question (organization token rejected; personal token or internal integration instead) with Sentry's own documentation; what was tested and what was not."
project: UnitPrep
quarter: Q4-2026
status: active
tags:
  - work-note
---

# Sentry and Grafana access for Claude

Part of [[Server Logging and Grafana - Index]]. Grafana-side tooling: [[Reading Logs - Tools and Recipes]]. Sentry's own setup: [[Session 2026-10-16 (Part 2) — Sentry Setup, Log Correlation, Tools Dashboard]]. Results of using both: [[Check-in 2026-10-19 - Weekend Quiet, Pool Warning, Sentry Empty]].

**Rule that applies throughout**: tokens are described by type and scope only; never paste a token into chat or the vault. Everything below was used **read-only**.

## The questions and what was answered

1. *(after the first Sentry events)* Boris tried to connect Sentry: "created an org key. it's not working in claude - sentry rejected your key. is org key the right type for this?"
   **No.** Sentry's documentation page on auth tokens (read on 2026-10-16/17 at https://docs.sentry.io/account/auth-tokens/) lists three kinds:
   - **Organization tokens**: bound to one organization, all its projects; meant for **CI and the Sentry CLI**; **permissions are fixed** (set for CI-style tasks). The page does not list exact scope names for them. Anyone can create one; only owners and managers can revoke. The full token is shown once. Reading issues through the API is not what they are for, which is the most likely reason the connection refused it.
   - **Internal integrations**: bound to an organization, customizable and editable permissions; the docs point to them "for cases where organization tokens lack sufficient access".
   - **Personal tokens**: bound to a user (any org/project that user can reach), permissions chosen at creation and **not editable afterwards**, not recommended for CI (they stop working if the user leaves the org); the docs' example of use is fetching a user's issues.
   The page says nothing about AI assistants. It also recommends a separate token per use case.
2. *"tell me what to do in Sentry to create a personal key to be used here"*: steps given (sentry.io, user menu, User settings, Personal Tokens at `/settings/account/api/auth-tokens/` or `de.sentry.io` if EU; Create New Token; name `claude-read`; scopes read-only for Organization, Project and Issue & Event, **nothing Write or Admin**; copy once; paste into `unitprep-api/.env.local` as `SENTRY_READ_TOKEN=...`, a **different name from `SENTRY_AUTH_TOKEN`**, which the other session's plan reserves for the UI build's source-map upload). Scope labels were recalled from memory, not checked. Whether Boris created it is not recorded; **it turned out not to be needed** (see the CLI below).
3. *"i have linked sentry and grafana in 'On-Call' mode of claude desktop. i also added sentry plug in and CLI. can you now fully access both?"*
   Answer after testing: **partly, and not through the connectors**.

## Test results (about 2026-10-17; the CLI reported "4 weeks and 1 day remaining" on its login)

| Route | Result |
|---|---|
| Connectors visible to this Code-tab session (`session_connectors_status`) | Claude Docs (8 tools), Intercom (15), HubSpot (29), visualize (2), ClickUp (61), filesystem (desktop, 14), scheduled-tasks (6). **No Sentry and no Grafana.** `ToolSearch` for "sentry" and "grafana" found no deferred tools either. So the "On-Call" mode links and any Sentry plugin do **not** appear in this session; what On-Call can do was not examined. To add connectors to a session, enable them in its connector list or type `/mcp` there (only the user can sign in). |
| **Sentry CLI** `~/.local/bin/sentry` 0.47.0 in WSL | **Works.** `sentry auth status`: authenticated as Boris M (bmaksimov@quikstor.com), config `~/.config/sentry/cli.db`, access token expires **2026-11-15 13:31:09 PT** (auto-refresh is on per the Part 2 note; check it worked near that date). `sentry issue list quikstor-wf/orchestrator --limit 5` returned a real issue (`ORCHESTRATOR-1`). This login was created by the Part 2 session (OAuth), not by a pasted token. On 2026-10-19 both projects were read this way. |
| **Grafana** via `scripts/logcli.sh`, the `scripts/grafana-mcp.sh` MCP server and Chrome | **Works** (re-tested 2026-10-16 16:19 PT, and `logcli` again on 2026-10-19). |

## How Claude should reach each, now

- **Sentry**: the CLI from a terminal session, e.g. `sentry issue list quikstor-wf/orchestrator`, `sentry issue view <ID>`, `sentry api <path>`. Org `quikstor-wf`, projects `orchestrator` (Rust API) and `orchestrator-ui` (Next.js). Useful flags: `--query "is:resolved"` (the **default list is unresolved only**), `--fresh` (skip the cache), `--json` with `--fields`, `--period` (default 90 days). A pasted personal token is not required.
- **Grafana**: files first, then `scripts/logcli.sh`, then the MCP server in a session started in `unitprep-api`, then Chrome (ordering and recipes in [[Reading Logs - Tools and Recipes]]).

## Using it proactively (decided 2026-10-19)

Having this access means Claude should **check Sentry and the logs without being asked**, and a scheduled routine now does so twice a day. The rules, the lookup order and the routine's guardrails are in [[Routine Monitoring and Troubleshooting Playbook]]; the same instruction is in both repos' `CLAUDE.md`.

## Not tested

- Whether the CLI's OAuth login can **write** (resolve, assign, delete); it would not be used for that without asking Boris.
- Opening a single issue in full (stack trace, tags) and the request-ID cross-link between a Sentry event and Grafana logs (the Part 2 note records that the `request_id` tag was not yet seen live).
- The "On-Call" mode connections and the Sentry plugin (not present in this session).
- A real Sentry issue from the running API (none has occurred; see the check-in note).

## Related

[[Server Logging and Grafana - Index]] · [[Observability Plan and Open Tasks (Sentry + Grafana)]] · [[Grafana Cloud Setup and Objects]]
