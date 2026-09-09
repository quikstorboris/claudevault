---
date: 2026-08-28
description: "Shipped in unitprep-api, following the plan in Orchestrator's Dropbox integration: Full Dropbox scope, env-configurable root path, planned QMS…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T15:07:31.409Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# Orchestrator's Dropbox client (Phase 1 foundation) is built and verified against the real API

Shipped in unitprep-api, following the plan in Orchestrator's Dropbox integration: Full Dropbox scope, env-configurable root path, planned QMS Onboarding quick-access button and Orchestrator's Dropbox refresh-token credential is live in unitprep-api/.env.local:

- New top-level module `src/dropbox/` (sibling to `client_ops/`): `config.rs` (`DropboxConfig::from_env()`, one struct grouping all 5 DROPBOX_* vars since they're only ever used together — a deliberate deviation from this codebase's usual one-var-one-function env convention), `client.rs` (`DropboxClient` with a `tokio::sync::Mutex`-cached access token refreshed lazily via the refresh_token grant, plus `list_folder`/`download`/`upload`; `DropboxError` via `thiserror`, matching the `AuthError` precedent).
- `reqwest` moved from dev-dependency-only (previously used solely to HTTP-test this app's own router over plain loopback HTTP) to a real `[dependencies]` entry — this is the first genuine outbound HTTP client in the codebase. Needed `features = ["json", "rustls-tls"]` explicitly: default-features=false means no TLS backend at all otherwise, and unlike the existing dev-dependency (localhost-only, plain HTTP), this one talks to real HTTPS endpoints.
- `AppState` (`src/api/state.rs`) gained one field: `dropbox: Arc<DropboxClient>` (concrete type, not `Arc<dyn Trait>` — no swap point exists). Wired in `main.rs` next to the other fallible-setup blocks (near `db_pool`).
- Verified two ways, no mocking (matching this repo's real-credential-test convention — see `auth::authenticated_user`'s and `auth::roles`'s `#[ignore]`d DB tests): (1) a new `#[ignore]`d real-network test in `src/dropbox/client.rs` that loads `.env.local` and asserts the real QMS Onboarding folder has >200 entries including "Papa Ducks" — passes via `cargo test --bin unitprep dropbox -- --ignored` (note: this is a binary-only crate, no lib target, so `--bin unitprep` is required, not `--lib`); (2) the full existing suite (`cargo test`) still passes at 334 passed / 4 ignored, no regressions. All test-fixture `AppState` constructors (`src/api/test_support.rs`, `dedup_test_support.rs`, `tagger_test_support.rs`) needed a `dropbox:` field added — done via a shared `test_dropbox_client()` fixture (fake, never-dialed config) in `test_support.rs`, reused by the other two via `crate::api::test_support::test_dropbox_client()`.

Deliberately NOT done (see the linked plan note): no wiring into Group Prep/Dedup/Tagger's upload or export handlers, no customer-to-folder matching logic, no new HTTP route. That's separate, not-yet-scoped follow-up work — the recorded recommendation is an explicit staff-picked folder (sourced live from `list_folder`) rather than fuzzy name-matching, given none of the three tools currently carry any customer/facility identity to match against.

## How this is known

cargo build/check clean; cargo test --bin unitprep dropbox -- --ignored passed against the real Dropbox API; full cargo test suite passed 334/0 failed/4 ignored with no regressions.
