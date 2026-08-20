---
date: 2026-08-11
description: "If an application stores any kind of session/ceremony/workflow state purely in server process memory (an in-memory HashMap-backed store, not the…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-11T17:44:20.731Z"
scope: general
projects: []
confidence: verified
---

# Restarting a shared dev server silently discards in-memory session state, with no error, no warning, and no way to recover it

If an application stores any kind of session/ceremony/workflow state purely in server process memory (an in-memory HashMap-backed store, not the database), restarting that server process for any reason -- testing an unrelated change, applying a code fix, verifying a build -- destroys every one of those sessions instantly and silently. There is no error at restart time and no error when the now-orphaned session ID is used again; the next request against it either 404s or behaves as if the session never existed. This reads to the user as a mysterious bug in whatever feature they were using, not as "the environment got reset out from under you."

This is a real risk specifically when working live in the same dev environment a user is actively using: restarting a backend server to verify your own change can invisibly destroy the user's unrelated, in-progress work in a completely different feature. The two events (your restart, their broken session) can be minutes apart and have no visible causal link unless someone thinks to check.

Practical implications: (1) before restarting a shared dev server for your own verification purposes, consider whether the user might have live state riding on it (an open session, an in-progress multi-step flow) and say so if restarting anyway; (2) when a user reports a sudden, unexplained 404/expired-session-shaped bug against a feature nobody touched, check whether any server process was restarted recently (by anyone) before assuming it's a real code defect -- read the actual session-storage code (is it in-memory or persisted?) rather than guessing; (3) this generalizes to any app with in-memory session/ceremony stores, not just one project -- the same failure mode applies to auth ceremony state, multi-step wizards, WebSocket-adjacent connection state, or any other server-memory-resident workflow.

## How this is known

Confirmed by reading the actual AppState struct in unitprep-api's main.rs: dedup_sessions is an Arc<InMemorySessionStore<DedupSession>>, never persisted to Postgres. Directly correlated to a real incident: restarted the backend twice in one session to test unrelated frontend changes, and the user reported a 404 on an in-progress dedup session shortly after -- confirmed as cause, not coincidence, by reading the session-store code rather than assuming.
