---
date: 2026-08-28
description: "Follow-up to the backend logging sweep (see 2026-08-28 logging/observability sweep: 8 gaps found and fixed across unitprep-api)."
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T16:52:14.598Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# Frontend logging gaps closed + DB query-latency logging enabled (2026-08-28)

Follow-up to the backend logging sweep (see 2026-08-28 logging/observability sweep: 8 gaps found and fixed across unitprep-api). Two more pieces landed same day:

**unitprep-ui frontend fixes** (all 4 candidates from the prior audit):
1. `lib/useAuditLogFilterData.ts` no longer silently swallows a failed event-types/users fetch -- added `filterDataError: string | null` to its return, set on either fetch's failure, rendered in both consuming pages (`app/(app)/admin/audit-logs/page.tsx`, `.../export/page.tsx`) using their existing `role="alert"` error-banner style.
2. Added `app/error.tsx` and `app/global-error.tsx` (Next.js App Router error boundaries) -- previously a render-time throw anywhere fell through to Next's default blank error page with zero record anywhere. Each logs via `console.error` (including Next's `error.digest` when present) and shows a "Try again" reset button.
3. Added `components/GlobalErrorListeners.tsx` (mounted in `app/layout.tsx`), registering `window.onerror`/`window.onunhandledrejection` -- a safety net for whatever doesn't go through the established non-throwing `{kind, message}` Result pattern.
4. `lib/api.ts`'s `errorMessageFrom` (the single shared choke point every domain's fetch-error path already funnels through) now appends the backend's `x-request-id` response header to the returned message when present -- `"<message> (request: <id>)"` -- so a user hitting an error can hand over one exact correlator. Had to guard with optional chaining (`response.headers?.get?.(...)`) rather than assuming a real `Response` shape: several existing tests (e.g. `FormatConfirmationSection.test.tsx`) mock a bare `{ok, status, text}` object with no `headers` at all, and the unguarded version threw and broke that test. Verified: `npx tsc --noEmit`, `npx eslint .`, `npx vitest run` (336/336) all clean.

**unitprep-api: DB query-latency logging** -- corrected an earlier wrong assessment (originally called this "an architectural change, not a quick add" before actually reading sqlx's source; it wasn't). sqlx-core 0.8.6 already emits a `tracing::event!` for every query via its internal `QueryLogger` (`sqlx-core-0.8.6/src/logger.rs`, verified by reading the actual installed crate source, not docs/memory) -- target `sqlx::query`, fields `elapsed`/`elapsed_secs`/`rows_affected`/`rows_returned`/the SQL summary, DEBUG by default and WARN once over a slow-statement threshold (sqlx's own default: 1s). Two tiny config changes turned this on rather than building anything: `main.rs`'s default `EnvFilter` widened to `"unitprep=info,sqlx=warn"` (previously the `sqlx` target wasn't mentioned at all, so even WARN-level slow queries were filtered out entirely), and `db.rs`'s `connect_options` now calls `.log_slow_statements(log::LevelFilter::Warn, Duration::from_millis(200))` (tightened from sqlx's 1s default). Needed adding `log = "0.4"` as a direct dependency purely for the `LevelFilter` type sqlx's API takes (sqlx's actual emission still goes through `tracing`, confirmed in source). Verified live against the real dev Neon branch two ways: with `RUST_LOG=sqlx=debug` forced on, every query fired correctly (real observed baseline: ~40-90ms per round trip to Neon, confirming 200ms is a sensible non-twitchy threshold above that baseline) and a query made inside a real HTTP request correctly showed the request's `request_id`/`method`/`path` as span context on the `sqlx::query` event -- confirming this correlates with the same request-id system for free, no extra wiring. With the real default filter, no WARN fired (expected -- nothing was actually slow in this quick check).

The residual gap this doesn't cover (pool-acquisition wait time, not query execution time) is recorded separately as its own diagnostic-trigger note: DB slow-query logging only covers query execution time, not.

## How this is known

Frontend: npx tsc --noEmit clean, npx eslint . clean, npx vitest run 336/336 passed (one test initially broke on the unguarded headers.get call, fixed with optional chaining, then passed). Backend: cargo build --all-targets zero warnings, cargo test 335/0/4 no regressions, and live verification against the real dev Neon branch with RUST_LOG=sqlx=debug showing real per-query timings and correct request_id span correlation.
