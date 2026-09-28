# UnitPrep — response to your 2026-09-24 review, requesting a follow-up pass

This responds to your champion-grade review of `unitprep-api` (then `v1.9.38`) and `unitprep-ui` (then `v1.6.39`). Every finding below was independently re-verified against the live repos before acting on it — a few turned out to be wrong or already resolved at review time, which is called out explicitly rather than silently corrected. Current versions: `unitprep-api v1.9.40`, `unitprep-ui v1.6.40`.

## Two corrections to the original review

Worth flagging before anything else, since they may affect how you calibrate this pass:

1. **"`docx-surgeon`... not yet wired into the template-tagging pipeline or any HTTP endpoint" was false at the time you wrote it.** `src/api/tagger.rs` already imported and called `docx_surgeon::{edit_docx_all, read_docx, ...}` directly, wired to live routes (`/tagger/check`, `/tagger/apply`, etc.). No action was needed here.
2. **"Types mirrored 1:1 (`types/api.ts` + ts-rs generation path)" overclaimed the scope.** `types/generated/README.md` already correctly scoped ts-rs codegen to 4 response families (`UploadResponse`/`DiscoverResponse`/`ValidateResponse`/`AnalyzeResponse`); the rest of `types/api.ts` (dedup, tagger) is still intentionally hand-mirrored. Unchanged, and correctly documented as such — not a gap.

Also: your test counts (556 API-side, 414 UI) were already stale at review time — actual counts then were 685/633; current counts are higher still (see below).

## P1 findings — addressed

**1. Tool sessions (Group Prep/Dedup/Tagger) purely in-memory, lost on restart/crash.**
Fixed in `unitprep-api v1.9.39`. Built `DurableSessionStore<S>` (`core/src/durable_session_store.rs`) — a write-through wrapper around the existing `InMemorySessionStore<S>`: `get_handle` still returns the same shared `Arc<RwLock<S>>` for in-process concurrent callers (a naive "deserialize fresh from Postgres every call" design would have let concurrent handles silently diverge), `save()` writes through to a new `auth.durable_sessions` Postgres table (bincode payload, one shared kind-discriminated table for every session type), and a `get_handle` miss cold-hydrates from that table before falling back to normal in-memory behavior. Applied to all three tool session types after making each serializable through its full type graph (`Session`/`SessionData` for Group Prep was the hardest — `Arc<Vec<CsvDocument>>`/`Arc<AnalysisResults>` needed serde's `rc` feature; Dedup and Tagger's session types were already plain, easily-serializable data). Four real-DB integration tests prove actual restart survival (save → drop store → build fresh store against same pool → confirm rehydration), each run for real against the live dev DB, not just asserted to compile.

Residual, by design: still single-instance only (the in-memory layer is per-process — two instances behind a load balancer without sticky sessions could observe a session inconsistently). Fixing that would mean every read going through Postgres, which we deliberately didn't do since it's not today's actual deployment model. Documented in the new `RUNBOOK.md` (below), not hidden.

**2. WebAuthn ceremony state in-memory, 5-min TTL.**
Fixed the same way, same commit range (`v1.9.39`) — `RegistrationCeremony`/`AuthenticationCeremony` moved onto `DurableSessionStore` first, before the three tool sessions, as the smallest validation of the pattern. TTL is still a fixed 5 minutes (unchanged, deliberately — a WebAuthn ceremony is one browser round trip, not a tunable operational parameter), but it now survives a restart within that window.

**3. UI README vs. API timeout language / doc drift.**
Fixed. The specific numbers were actually already internally consistent (10-min tool-session timeout, 30-min auth idle timeout, 12h auth absolute lifetime — two genuinely distinct mechanisms, not conflicting claims about one). The real issue was that "session" is heavily overloaded in this codebase with no disambiguation — added a clarifying clause to `unitprep-ui/README.md` distinguishing the two. Also fixed genuinely stale test counts in both READMEs (958 API-side / 633 UI-side as of the fix date; see current counts below for further growth since).

**4. Process Street/Dropbox "saved but not reloaded" clarity.**
Not changed behaviorally (a config change still takes effect on the next restart, not live) — but now explicitly documented in `RUNBOOK.md`: "A saved change on either Integrations settings page takes effect on the next server restart — nothing re-reads it mid-run." Judged a reasonable, cheap-to-document limitation rather than something worth building hot-reload for, given the low frequency of these particular settings changing.

## P2 findings

**Migration volume (168+ files).** Not yet started. Explicitly next in the work queue after the `client_ops` schema work below — deliberately sequenced, not forgotten.

**Vendor-format/person-index cache failure-mode observability.** Not looked at this round.

**CI enforcement of `generate-types` staleness.** Deliberately not implemented — solo developer, no CI infrastructure at all currently, and building CI machinery for a one-person team was judged not worth it right now. Tracked instead in a new running backlog (`brain/CI Backlog.md` in our internal notes) specifically so it isn't lost, to build if/when this project gets a second developer or real CI/CD infrastructure. Happy to reconsider if you think the actual drift risk is higher than we're weighing it.

**`docx-surgeon` "unwired."** Already covered above — was never actually true.

## P3 findings — addressed

**Repository URL in `Cargo.toml`.** Fixed (`unitPrep.git` → `unitprep-api.git`, confirmed against the real `git remote`).

**Shared session-store trait, if a second durable implementation is ever added.** Effectively addressed as a side effect of the P1 fix — `DurableSessionStore<S>` is one generic implementation shared across all four durable session types (2 WebAuthn ceremony types + 3 tool session types), not four near-identical ones.

**UI dependency surface.** No action needed — already genuinely minimal (5 runtime deps), confirmed accurate.

**Extend session-expired-style discipline to long-running tool UIs (progress, cancel, partial failure).** Fixed in `unitprep-ui v1.6.40`. New shared `useAbortableOperation` (elapsed-time ticking + `AbortController`, since none of these endpoints stream a real percentage back — an honest indeterminate-progress affordance, not a fake bar) and `useFileUploadAction` (switched real uploads from `fetch` to `XMLHttpRequest` specifically to get genuine `upload.onprogress` events, which `fetch` has no equivalent for). Wired into `useSessionAction`/`useSessionPost` and rippling into roughly 20 call sites app-wide. `UploadResponse`'s `files_uploaded`/`files_failed`/`multipart_errors` counters — previously computed by the backend but never surfaced distinctly in the UI — are now shown explicitly as a partial-failure state, separate from both success and total failure. Cancel + elapsed-time UI added to Dedup, Template Tagger, and the full Group Prep upload→discover→validate→export pipeline.

## Work done that you didn't flag, found via our own follow-up audit

**`client_ops` schema modularity — narrower than we initially assumed.** We went in expecting to need a broad reorganization ("7+ concerns crammed into one schema," per our own earlier internal audit). Investigation showed the codebase's own module doc comment (`src/client_ops/mod.rs`) already defines that domain precisely — "tooling an Onboarding Manager uses day to day" — and 5 of the 7 tables (`audit_log`, `tool_runs`, `vendor_format`, `qms_tag`, `tag_pattern`) genuinely belong there by that definition; not drift, intentional design. The real mismatch was 2 tables: `dropbox_configuration`/`process_street_settings` have been gated by a different permission (`integrations.manage`, not `client_ops.perform`) since a mid-September migration, but their schema namespace never followed — that migration's own comment documents the permission move without moving the table. Fixed in `unitprep-api v1.9.40`: moved both to a new `integrations` schema (`ALTER TABLE ... SET SCHEMA`, which preserves RLS/triggers/indexes/FKs unchanged), updated ~21 Rust SQL-string references, and caught + fixed a real gap along the way — schema-level `USAGE` does not survive a table's `SET SCHEMA` the way table-level grants do, so `scripts/setup_app_service_role.sql` needed a new grant block, found by testing the moved tables' real queries against the dev DB as the app's actual runtime role, not just confirming the migration applied.

**CHANGELOG backfill.** `unitprep-api`'s `CHANGELOG.md` had stopped at `1.8.0` while the repo had shipped to `1.9.38` (48 tags / 213 commits undocumented); `unitprep-ui`'s had stopped at `1.4.0` against actual `1.6.39` (148 commits). Backfilled 60 and 51 entries respectively, sourced primarily from our own internal session notes with git log as the fallback for anything not otherwise documented.

**5 oversized `unitprep-ui` files split** (`clients/new/page.tsx` 656→169, `clients/search/page.tsx` 586→162, `facility/UsersTab.tsx` 579→137, `DiscoveryPage.tsx` 523→132, `ScanResultsPage.tsx` 535→257 lines) per this project's own ~250-line file-size convention. Pure reorganization, no behavior change, each verified independently in isolation (not just as part of the combined diff) before being committed as its own change.

**Cheap live-DB check, budget-constrained.** Ran a lightweight FK-index-coverage audit against the real dev DB (a single ~57ms catalog query, not a bulk audit — Neon free-tier compute was at ~93.5% of its monthly allowance at the time, so we deliberately kept this minimal). Found 13 foreign keys without a covering index, mostly "who touched this" audit columns (`created_by`/`updated_by`/`actor_user_id`) pointing at `auth.users`. Also checked real row counts: the largest table in the entire database has 1,879 rows. Verdict: real gaps, not urgent — documented rather than fixed, since adding indexes for a load that doesn't exist yet would be the premature optimization this project's own conventions specifically warn against. A fuller `EXPLAIN ANALYZE`/RLS/orphan pass, as you originally suggested, is still deferred until compute budget allows more headroom.

**`RUNBOOK.md` added** — required configuration, the four distinct session lifetimes (auth idle/absolute, WebAuthn ceremony, tool session) and which are now durable across a restart, the single-instance deployment assumption stated explicitly, basic stuck-deploy recovery steps.

## Current state, for your reference

- `unitprep-api`: `v1.9.40` (was `v1.9.38` at your review). Test counts as of the durability work: 654 unit/integration tests passing + 35 real-DB integration tests (`#[ignore]`d by default, including 4 proving session durability across a simulated restart), clippy clean except 3 pre-existing, unrelated failures we independently confirmed predate all of this work (`src/api/dropbox_browse.rs` ×2, `src/clients/repository.rs` ×1 — not fixed, out of scope, but not new either).
- `unitprep-ui`: `v1.6.40` (was `v1.6.39` at your review). 86 test files / 669 tests passing, `tsc`/`eslint` clean.
- Every commit in both repos across this whole follow-through was verified independently (build/test/lint) at its own point in history, not just at the final combined state — including reconstructing true intermediate states via `git stash` where two pieces of work landed on the same files back to back, specifically so the commit history stays bisectable rather than just plausible-looking.

## What we'd like from this pass

Given the above, we'd appreciate:
1. Verification that the P1 fixes actually close the gaps you identified, not just that they exist.
2. A fresh look at anything that's grown or changed shape since your last pass that we might not have caught ourselves — the codebase has moved by 2 versions on the API side and 1 on the UI side since you last looked, including the two corrections noted at the top (worth double-checking those aren't hiding a different real issue we haven't found).
3. Whether the deferred items (migration squash, cache observability, CI enforcement, full EXPLAIN/RLS/orphan audit) still look right to leave deferred, or whether anything there has become more urgent than we're currently treating it.
