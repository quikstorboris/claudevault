---
date: 2026-08-28
description: "Follow-up sweep to [[Logging & Observability]] (the 2026-07-30 roadmap), done at Boris's request (\"let's look at the code and identify good…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T16:17:22.317Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# 2026-08-28 logging/observability sweep: 8 gaps found and fixed across unitprep-api

Follow-up sweep to [[Logging & Observability]] (the 2026-07-30 roadmap), done at Boris's request ("let's look at the code and identify good candidates... audit trail for user actions, system events, troubleshooting, telemetry"). Judged ops-telemetry and audit-trail separately per that note's own framing, and checked the 2026-07-30 roadmap's status against current code rather than trusting the note's dates -- it was PARTLY stale: items 1-3 (registration-failure audit row, ceremony correlation_id, device_bound) are correctly DONE; the "no rate limiting" flag from a companion 2026-07-30 security assessment turned out to be ALREADY FIXED (tower_governor rejections are audited via RATE_LIMIT_REJECTED, contradicting that stale note); items 4 (request ids) and 5 (ceremony duration) were correctly still open.

**Found and fixed, all verified (cargo build zero warnings, cargo test 335/0/4 no regressions throughout, several also verified live against a real running server):**

1. **`client_ops_qms_tags.rs` rejection asymmetry** -- permission-denials were audited, but blank-field validation, duplicate-tag-key 409, not-found 404, and already-in-that-state 409 rejections wrote nothing at all. Added `tracing::warn!` (user_id + tag_key + reason) at each of the ~6 rejection sites. Same asymmetry shape the original roadmap's "one bug" (rejected registration) was.

2. **`session_not_found()`/`stage_conflict()` (`src/api/mod.rs`) had no logging inside them**, despite being the shared response helper for ~20+2 call sites across Group Prep/Dedup/Tagger (`respond()` too, 3 more call sites). Centralized `tracing::warn!` inside all three (session_id, and required/current stage for stage_conflict), changing their signatures to take `session_id: &str` -- updated every call site across ~17 files. Deliberately accepted some duplicate logging at sites that already warn with richer local context (e.g. export.rs's pre-existing stage-check warn) rather than removing that context; better to over-log than reopen the gap if someone forgets next time.

3. **`try_authenticated_user()` (`src/auth/authenticated_user.rs`) swallowed DB errors via `.ok()`** -- a DB outage on this path looked identical to "not signed in," while the *mandatory* auth extractor's near-identical query correctly logs the same failure. Rewrote as an explicit match so the Err branch logs before collapsing to None (the None-collapsing behavior itself, documented in the function's own doc comment, is unchanged).

4. **Group Prep's `/export` completion log was missing `owner_id`** that Dedup's and Tagger's equivalent logs both carry -- three near-identical business events, one inconsistent. Added.

5. **Startup panics bypassed `tracing` entirely** -- no `std::panic::set_hook`, so a crashed `db_pool`/`dropbox_client`/`auth_backend` at boot printed only to raw stderr via Rust's default hook. Installed a wrapping panic hook in `main.rs` (logs via `tracing::error!`, then calls the original hook so the familiar stderr backtrace is preserved too). Verified live with a deliberate temporary `panic!()`: the ERROR line fired correctly alongside the normal stderr output.

6. **No graceful shutdown, no final log line on exit** -- the process had zero signal handling at all; Ctrl+C/SIGTERM killed it immediately mid-request with nothing recorded. Added `shutdown_signal()` (Ctrl+C or, on Unix, SIGTERM via `tokio::signal::unix`) wired through `axum::serve(...).with_graceful_shutdown(...)`, logging which signal fired and a final "UnitPrep API stopped" line. Verified live: sent real SIGTERM to a running server, saw both log lines fire in order.

7. **The rate-limit-bucket cleanup background loop (`router.rs`, a 60s `tokio::spawn` loop calling `retain_recent()`) had zero tracing**, and its own doc comment's claim that it "must keep running even if one iteration panics" was actually FALSE -- nothing enforced that; a real panic would have killed the task silently and permanently, quietly resuming the exact memory leak it exists to prevent. Wrapped the tick body in `std::panic::catch_unwind` (`AssertUnwindSafe`, since `retain_recent()` is synchronous) and log `tracing::error!` with the extracted panic message on failure, so the comment's claim is now actually true.

8. **No request-id/correlation-id spanning a whole HTTP request** (only WebAuthn-ceremony-scoped ids existed) -- the roadmap's item 4, deferred 2026-07-30 with the stated trigger "the first time a support question cannot be answered from the logs." Revisited now given more people (product/dev team) are about to start using Orchestrator. Added `tower-http`'s `trace`+`request-id` features: `SetRequestIdLayer` (outermost of the whole router, so every request gets an id before anything else -- cors, body-limit, catch-panic -- touches it) mints a UUID via `MakeRequestUuid`; `TraceLayer::new_for_http()` creates a per-request span carrying `method`/`path`/`request_id` (so every `tracing::` call made anywhere while handling that request inherits those fields automatically) and logs a `request completed` line with `status`+`latency_ms`; `PropagateRequestIdLayer` echoes the id back as an `x-request-id` response header. Getting the three tower-http layers' relative order right needed care: axum's `Router::layer` makes the LAST-applied `.layer()` call the OUTERMOST (confirmed against this file's own pre-existing "Outermost layer" comment on `CatchPanicLayer`) -- the OPPOSITE of how `tower::ServiceBuilder`'s docs/examples order the same three layers (first-listed = outermost there). Verified live end-to-end: curl showed a unique `x-request-id` response header per request (including a 401), and the server log's completion line for each request carried the exact same id as the header the client received.

**Deliberately not done, and why:** a shared query-instrumentation layer (`#[tracing::instrument]`/DB latency tracking everywhere) is a real gap too, but treated the same trigger-gated way as item 8's predecessor rather than built speculatively. Boris asked what a good trigger would be; answered: the first time a slow request or a DB-related incident can't actually be diagnosed from the existing (now request-id-correlated) logs -- mirroring item 8's own now-fired trigger, but for latency/performance rather than "what happened for this user" -- plus, secondarily, the point Orchestrator gets a real production deployment against a network-separated Postgres (Neon), since local dev's DB latency characteristics don't resemble a real deployment's (this project has already hit real Neon-pooler-specific gotchas, so that transition is a concrete, known moment to revisit this rather than a vague someday).

## How this is known

cargo build --all-targets: zero warnings throughout all 8 fixes. cargo test: 335 passed / 0 failed / 4 ignored, no regressions, checked after each major change. Items 5, 6, and 8 additionally verified live against a real running `cargo run` server: a deliberate temporary panic confirmed the panic hook logs via tracing before delegating to the default hook; a real SIGTERM confirmed both graceful-shutdown log lines fire in order; curl against several real endpoints (including a 401) confirmed a unique x-request-id response header per request, matching the request_id field in that request's server-side completion log line exactly.

## Related

- [[Logging & Observability]]
