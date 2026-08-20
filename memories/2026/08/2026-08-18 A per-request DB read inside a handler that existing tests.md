---
date: 2026-08-18
description: "When adding a new DB-backed lookup (e.g. a lookup table, a feature registry) to logic that HTTP handler tests call directly against a fake/lazy…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-18T21:29:52.739Z"
scope: general
projects: []
confidence: verified
---

# A per-request DB read inside a handler that existing tests call directly can silently turn a fast unit-test suite into 50ms-timeout failures

When adding a new DB-backed lookup (e.g. a lookup table, a feature registry) to logic that HTTP handler tests call directly against a fake/lazy connection pool (a pool that never actually connects, built specifically so tests never touch a real database), don't put the DB read inside the handler's request path at all. Load it once at startup and cache it in shared app state (refreshed on a timer if it needs to stay current), and have the handler read the cache synchronously. If the DB read stays inline, every test that calls that handler directly starts hitting the fake pool's connection-timeout path — which doesn't error loudly, it just makes each affected test take however long the pool's acquire_timeout is (seconds, if nothing tightened it), turning a millisecond test suite into a mysteriously slow one, or an outright failure if the handler treats the timeout as "not found" rather than "DB unreachable."

Why this is easy to miss: the failure mode looks identical to the feature just not working ("no vendor detected," "empty results") rather than "this call is wired to touch infrastructure it shouldn't." It only surfaces when you actually run the existing test suite after the change, not from reading the diff.

Related, same root cause: if the new data lives behind row-level-security that checks a per-request-set context value (e.g. current_setting('app.current_user_id')), a background/startup read with no real request context needs an explicit placeholder value for that setting - a nil/sentinel ID is enough if the policy only checks "is this set," not "is this a real user." Skipping that makes the query silently return zero rows instead of erroring, which again looks exactly like "nothing matched" rather than "this call forgot to open the RLS context."

## How this is known

Discovered by running cargo test after wiring vendor-format lookups into Group Prep's discovery handlers in unitprep-api: ~190 existing tests called discover()/select_unit_file()/etc. directly against test_support::test_db_pool() (a connect_lazy pool with a deliberately tightened 50ms acquire_timeout specifically to catch this class of bug fast rather than silently). Fixed by caching the registry in AppState (loaded at startup, refreshed every 5 minutes) instead of querying per request; full suite passed once no request path touched the DB.

## Related

- [[Multi-Vendor Unit-File Discovery]]
- [[UnitPrep Architecture Overview]]
