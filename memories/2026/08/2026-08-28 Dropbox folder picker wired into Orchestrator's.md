---
date: 2026-08-28
description: "Built on top of the Dropbox client foundation (see Orchestrator's Dropbox client (Phase 1 foundation) is built and verified against the real API): a…"
tags: [memory]
source: mcp-capture
origin: "development"
session: "2026-08-28T15:31:10.201Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# Dropbox folder picker wired into Orchestrator's client-creation and client-info flows

Built on top of the Dropbox client foundation (see Orchestrator's Dropbox client (Phase 1 foundation) is built and verified against the real API): a real folder browser now backs `Client.dropboxPath`, replacing the free-text input that was previously labeled "manual reference only, for now" (`unitprep-ui/app/(app)/clients/[clientId]/info/page.tsx`) -- that placeholder was Boris's own earlier forward-looking design, not left by anyone else on the project.

Key discovery this round: the real QMS Onboarding folder structure is Client (top-level company folder, e.g. "Prairie Enterprises LLC") -> one or more Facility folders (inconsistent naming -- status-tag suffixes like "(Cloud)"/"(NewVACANT)"/"(QSX)", leading underscores, template/admin folders like "Coverage Docs" or "Menards TEMPLATES" mixed in alongside real facilities) -> the 5 standard per-facility subfolders (Final Data, Preliminary Data with dated "N-th Pull" subfolders, Tenants & Leases Migration, Units Migration, Validation). This inconsistency is why Boris explicitly rejected automatic/fuzzy folder matching in favor of an explicit human-driven picker, and specified the picker must default to landing at the client-root level (top of QMS Onboarding, where company folders live) on the client-creation step specifically -- not pre-guess or descend into any facility -- to reduce selection ambiguity up front. The folder is picked once at client-creation time and remains editable afterward on the same client's info page.

Implementation:
- Backend: new `GET /dropbox/list` route (`unitprep-api/src/api/dropbox_browse.rs`), any-authenticated-caller (same reasoning as `client_ops_qms_tags::list_qms_tags` -- folder names only, nothing sensitive), no DB transaction. The one real piece of logic: every requested `path` must equal or start with `state.dropbox.root_path()` (a new accessor added to `DropboxClient`) or the request is rejected with 400 `path_outside_dropbox_root` -- this is the actual enforcement point for the "Dropbox itself enforces no folder boundary" caveat recorded in the earlier Dropbox-client memory. Covered by a fast, hermetic handler test (no network) asserting that rejection; the network-touching success path is left to the already-`#[ignore]`d real-credential test on `DropboxClient::list_folder` itself, deliberately not duplicated here to avoid installing network flakiness into the default `cargo test` run.
- Frontend: `unitprep-ui/lib/dropbox.ts` (mirrors `lib/clientOps.ts`'s per-domain fetch-helper shape) and a reusable `components/clients/DropboxFolderPicker.tsx` (inline browse: current path, Up, click a folder to descend, "Select this folder" to commit) used in both `app/(app)/clients/page.tsx` (client creation -- picker always starts at the configured root, satisfying the "land in client root" requirement since `value` starts empty there) and the client's `/info` page (editing -- picker starts browsing wherever `client.dropboxPath` currently points, for convenient re-selection).

Verified: `cargo test` (335 passed, 0 failed, 4 ignored, no regressions), `npx tsc --noEmit` clean, `npx eslint` clean on the new/changed files, `npx vitest run` (336 passed, no regressions), and manual curl checks against a real running `cargo run` server confirming `/dropbox/list` returns 401 with no/invalid session cookie in every case (including a path-outside-root request, so the boundary check never leaks anything to an unauthenticated caller). NOT verified: an actual logged-in browser click-through of the picker UI -- blocked by this app's real WebAuthn/passkey + TOTP login requirement, which can't be scripted headlessly. Boris should click through it himself before relying on it, especially given his OO demo may happen on short notice (see the demo-timeline memory).

## How this is known

cargo test 335/0/4 no regressions; npx tsc --noEmit clean; npx eslint clean; npx vitest run 336/0 no regressions; live curl checks against a running cargo run server confirmed 401 auth-gating on all unauthenticated variants including the outside-root path. Real browser click-through with a logged-in session was not performed (blocked by WebAuthn/TOTP, not scriptable).
