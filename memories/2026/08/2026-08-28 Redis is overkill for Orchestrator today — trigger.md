---
date: 2026-08-28
description: "Came up 2026-08-28 while discussing whether a Dropbox facility-search feature needed a background tree-cache."
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T17:34:51.041Z"
scope: project
projects: ["unitprep-api"]
confidence: unverified
---

# Redis is overkill for Orchestrator today — trigger conditions for when to reconsider it

Came up 2026-08-28 while discussing whether a Dropbox facility-search feature needed a background tree-cache. Decision: no Redis, and more generally, no external cache/state store belongs in Orchestrator (unitprep-api) until a real trigger fires -- keep using the in-process cache pattern already established (`client_ops::vendor_format::VendorFormatCache`: loaded once, refreshed on a timer, read synchronously, no per-request fetch).

**Why Redis is overkill right now**: every piece of shared state in this codebase is deliberately in-process, not externalized -- session stores (unit_group/dedup/tagger, all `InMemorySessionStore`), WebAuthn ceremony state, rate-limit buckets. This is a single backend instance with no horizontal scaling anywhere in the architecture. Redis earns its keep for two reasons, neither of which applies today: (1) cache/session state needs to be SHARED ACROSS MULTIPLE BACKEND INSTANCES (horizontal scaling), or (2) state needs to SURVIVE A PROCESS RESTART. Introducing Redis now would mean provisioning and operating a new piece of infrastructure to solve a problem the existing in-process pattern already handles, which cuts against this project's own established preference for self-hosted/minimal-infrastructure solutions over new services (see the TOTP-not-KMS, printpdf-not-hosted-service precedents).

**Concrete triggers to actually revisit this** (raise proactively if one fires, per Boris's standing "raise proactively" instruction -- don't wait to be asked):
1. **Orchestrator gets deployed as more than one running backend instance** (real horizontal scaling, e.g. behind a load balancer for actual concurrent-user capacity) -- at that point in-memory session stores AND any in-process cache both stop working correctly (a session created on instance A is invisible to instance B), and that's a much bigger migration than "add Redis for one cache" -- it would mean moving session storage externally too, which Redis (or Postgres) would need to solve as a package, not cache alone.
2. **A cache genuinely needs to survive a restart** -- e.g. something expensive enough to rebuild that a deploy-triggered restart causing a cold cache becomes a real, noticed problem (not yet true for anything in this app; the vendor_format cache and any future Dropbox-tree cache are both cheap enough to rebuild from scratch on every process start).
3. **State needs to be shared with a process OTHER than this one Rust binary** -- e.g. a separate worker process, a scheduled job runner, or a second service -- that Postgres alone is a poor fit for (high-frequency reads/writes, pub/sub, rate-limiting primitives across processes).

If Boris says any of these three has actually happened, that's the moment to bring Redis back into the conversation as a real option -- not before.

## How this is known

Reasoned from this session's own review of unitprep-api's existing state-management code (session stores, vendor_format cache, rate limiter) -- not independently verified against a live multi-instance deployment scenario, since none exists yet.
