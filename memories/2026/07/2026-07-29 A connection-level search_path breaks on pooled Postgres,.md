---
date: 2026-07-29
description: "Setting `search_path` as a **connection option** works on a direct Postgres connection and fails outright through a PgBouncer-style pooler (Neon's…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-29T22:21:43.456Z"
scope: general
projects: []
confidence: verified
---

# A connection-level search_path breaks on pooled Postgres, and per-session SET is not the fix — schema-qualify instead

Setting `search_path` as a **connection option** works on a direct Postgres connection and fails outright through a PgBouncer-style pooler (Neon's pooled endpoint, Supabase's, RDS Proxy in some configs):

```
unsupported startup parameter in options: search_path
```

The reason is that connection options travel in the Postgres **startup packet**, and a pooler multiplexes many clients over shared server connections, so it can only honour startup parameters it knows how to replay. Every query fails, including a bare health check — so it reads as "the database is down", not "one setting is unsupported".

With sqlx this is `PgConnectOptions::options([("search_path", "...")])`. Equivalents exist in every driver.

**Why moving it to a per-connection `SET` is a trap, not a fix.** The obvious next move is an `after_connect` hook running `SET search_path = ...`. Do not: a pooler in **transaction mode** hands a different server connection to the next transaction, so a session-level `SET` is not reliably bound to the client that issued it. It appears to work under light load — one client, one connection — and starts vanishing or leaking across clients under concurrency. That is strictly worse than failing, because the failure now depends on load.

`SET LOCAL` inside an explicit transaction *is* safe under transaction pooling (it dies with the transaction), which is why per-request GUCs set that way are fine while a session-level `search_path` is not. But that only helps if every query runs inside a transaction you control.

**The form that is correct everywhere: schema-qualify.** `auth.users`, `auth.resolve_session(...)`, and so on in every application query, with no `search_path` set at all. Correct on direct connections, pooled connections, and under any pooling mode. The cost is that an unqualified name added later fails at runtime rather than compile time, so it is worth a grep in review.

**Two things that make this specific bug hide unusually well:**

1. Unit tests that use a lazy, never-actually-connected pool execute no SQL, so they pass regardless. The bug is invisible until something runs the real binary against the real database.
2. Identical code works or fails purely on **which endpoint the connection string names** — direct vs pooled hostnames often differ by one substring (`-pooler`). So "it worked yesterday" and "it fails now" can both be true with no code change at all, which sends you looking in the wrong place.

Corollary worth internalising: after switching a connection string, verify against a **freshly started** process. A health check that passes against a still-running old process — which loaded the previous value at boot, since dotenv-style loading reads env once — is indistinguishable from a real pass and will manufacture false confidence.

Expect to end up with several distinct `search_path` regimes coexisting deliberately: none for the application, an explicit pin inside each `SECURITY DEFINER` function, and the migration role's own default. They are not redundant and should not be unified.

## How this is known

Hit on unitprep-api 2026-07-29. With `options([("search_path", "auth,public")])` in db.rs and DATABASE_URL on Neon's pooled host, every request failed with the quoted error, including GET /health/db. After removing the option and schema-qualifying all seven SQL sites, the same binary against the same pooled URL returned {"status":"ok","connected_as":"app_service"}, issued a real WebAuthn registration challenge, and wrote audit rows. Also confirmed the hiding mechanisms first-hand: the 350-test suite passed throughout (unreachable lazy pool, no SQL executed), and an earlier "confirmed working" health check had come from a process still running the direct URL, which is what delayed finding this by several hours.

## Related

- [[RLS Implementation]]
- [[Database Schema]]
- [[Phase 2 Progress]]
