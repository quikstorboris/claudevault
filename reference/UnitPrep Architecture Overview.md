---
date: 2026-07-27
description: What UnitPrep is, its current architecture post workspace-split (Cargo workspace + Next.js frontend), pipeline, and design principles.
tags: [reference, unitprep, architecture]
---

# UnitPrep Architecture Overview

> [!note] Staleness
> Ported from a memory note last updated as of the end of the 2026-07-17 session. Treat specifics (file paths, line counts, "as of" dates) as point-in-time — verify against actual code before relying on them.

UnitPrep is an internal Quikstor tool that prepares self-storage facility unit inventory exports for migration/import. It is a growing **platform of tools** — as of 2026-07-16 this is real, not just envisioned: the original group-analysis tool (now called **"Group Prep"** in conversation) plus a second tool, duplicate tenant check (see [[Dedup Tool Index|Dedup Tool]]), both fully built and mounted.

## Naming note (2026-07-16)

Boris now refers to the original tool as **"Group Prep"** rather than "UnitGroup," and "UnitPrep" is becoming the platform-level name (itself expected to be renamed later once the platform covers more than groups). The codebase still says `unit-group`/`UnitGroup` throughout — the actual code rename is a distinct, not-yet-scheduled task. Use "Group Prep" in conversation; don't assume the code has caught up.

`unitprep-api`'s own README was reframed around this same platform-vs-tool distinction 2026-07-17 (commit `1264842`) — its intro used to describe the whole API as if it were just Group Prep even though it already documented dedup further down; now opens with "UnitPrep is a platform... two tools today" and has a `## Platform vision` section (Client Prep nav, QMS vs. QSX, the auth trigger, persistence — all explicitly marked not-yet-built). `unitprep-ui`'s own README was not touched and may still need the same treatment.

## QSX vs. QMS

QSX is QuikStor's legacy, desktop-only, being-sunset PMS (no real API); QMS is the modern cloud/API-capable PMS platform UnitPrep actually targets — see [[UnitPrep File Locations]] for the real QMS OpenAPI spec's location. Sample data used so far (No Ka Oi, New Castle) is QSX-era — legacy shape, not necessarily representative of QMS's own export format.

Full platform vision (Client Prep navigation, QMS API integration, auth, persistence — none built yet as of this writing) is in [[Platform Vision (Onboarding Orchestrator)]].

## Two repos, versioned independently

### `unitprep-api` — Rust/Axum/Tokio backend

As of 2026-07-15, a Cargo workspace, not a single crate; as of 2026-07-16, fully multi-tool:

- **`unitprep-core`** — tool-agnostic shared engine: file ingestion/parsing (`core/src/parsing/{mod,csv,excel,spreadsheetml}.rs`, split by format; tolerates a trailing unnamed column beyond the header, a real QMS-export quirk), `CsvDocument`/`UploadedFile` (source-agnostic document models), and the generic session engine (`SessionMetadata`, `HasSessionMetadata` trait, `SessionStore`/`InMemorySessionStore` generic over any tool's own session type — `parking_lot::RwLock`, no poisoning, upgradable-read throttled last-accessed bumping, configurable idle timeout via `with_timeout`/`SESSION_TIMEOUT_SECS`).
- **`unit-group`** (crate name `unitprep-unit-group`) — Group Prep's domain logic, extracted 2026-07-16 (was an empty stub before this). Discovery-result/validation-result data, per-facility batch building, the fingerprint-matching engine, validation rules, manual-correction overlays. Depends only on `unitprep-core`; no session state, HTTP, or export format — those stayed in the binary. See [[Code Review Watchlist]] for the full extraction story (two phases, same session).
- **`dedup`** (crate name `unitprep-dedup`) — the duplicate-tenant-check tool's domain logic (grouping by exact `FirtLast` match, contact-info comparison, typo/name-variant detection, a pluggable `NoteComposer` for human-facing message text). Same boundary as `unit-group`: depends only on `unitprep-core`, no session/HTTP/export concerns. See [[Dedup Tool Index|Dedup Tool]] for the full build history.
- **`unitprep`** (the binary, at repo root) — HTTP layer (`src/api/`), session orchestration for both tools (`src/application/`: `unit_group_session.rs` + `session_service.rs` for Group Prep, `dedup_session_service.rs` for dedup), export artifact generation (`src/infrastructure/`: `csv_export.rs` + `dedup_csv_export.rs`). `src/domain/` no longer exists — fully absorbed into the split above. `AppState` holds `unit_group_sessions: Arc<dyn SessionStore<Session>>` (renamed from `session_store` 2026-07-15, deliberately, so a second tool's store would be additive later, not a rename cascade — proven right when `dedup_sessions` was added exactly that way 2026-07-16).

### `unitprep-ui` — Next.js 16 / React 19 / TypeScript 5 / Tailwind 4 frontend

Explicitly "thin" — no business logic, just drives the browser upload and renders API responses. `lib/api.ts` holds the API base URL and `errorMessageFrom()` (parses the backend's `{error, message}` error body, added 2026-07-15). `types/api.ts` mirrors the Rust request/response structs 1:1 by design so a backend field rename becomes a TS compile error, not a silent mismatch.

**Covers both tools as of 2026-07-16**: dedup's own standalone screens (`app/dedup/page.tsx` + `app/dedup/[sessionId]/page.tsx`, `components/DedupUploadPage.tsx`/`DedupResultsPage.tsx`, plus `components/dedup/*`) were built matching Group Prep's existing conventions exactly — see [[Dedup Tool Index|Dedup Tool]] for the full build/verification writeup. No shared nav yet (that's the still-pending "Client Prep" wrapper step, see [[Platform Vision (Onboarding Orchestrator)]]) — each tool is reached at its own top-level route today (`/` for Group Prep, `/dedup` for dedup).

See [[UnitPrep UI Dev Environment]] for how to actually run this frontend's dev server in the real WSL setup.

## Pipeline (sequential, session-scoped)

upload → discover → (group-file/select if ambiguous) → validate → (correct / exempt-dimensions loop) → analyze → export

- Existence of a UnitGroup is decided by **exact name match only**. Fuzzy (fingerprint + normalized Levenshtein) similarity is advisory-only and never determines net-new status — this was a deliberate fix after fuzzy-match false positives were found between unrelated groups.
- Export is blocked while unresolved `Severity::Error` validation issues exist, unless the caller explicitly passes `acknowledge_errors: true` (logged when used, never silent).
- **Every error response across the API shares one shape** (as of 2026-07-15): `ApiErrorBody { error: &'static str, message: String }`. `session_not_found()` → 404, `stage_conflict()` → 409 (session exists, wrong workflow stage — replaced a fake all-zero 200 that used to be indistinguishable from a real empty-but-successful result), `internal_error()` → 500. Frontend already updated to surface `message`, not just the status code.
- Parses `.csv`, `.xlsx`, and `.xls`, including Excel 2003 SpreadsheetML XML mislabeled with a `.xls` extension (content-sniffed, not extension-based). All header-name lookups go through `CsvDocument::header_index` (normalizes case AND strips spaces/underscores) — a real bug class (independent ad hoc normalizers silently disagreeing) has been found and fixed **three times** now (`discover.rs`'s classifier, `analysis::reference`'s Name lookup, and `analysis::batch`'s UnitGroup-column lookup, 2026-07-16 — the last one caught by an external review pass, verified before fixing). If a *fourth* ad hoc header comparison turns up anywhere, it's the same bug again — worth a proactive grep at that point.

## Business/design principles

See the UnitPrep_*.json docs in [[UnitPrep File Locations]]: data integrity over convenience, deterministic results, business-rule correctness over clever algorithms, parse-once/use-many-times, thin frontend + domain-driven backend, no temporary/technical-debt-by-design solutions, security and observability designed in from the start rather than retrofitted.

**Prefer data over hardcoding** (added 2026-08-18): a fact that can change without a deploy — vendor/PMS export formats, lookup tables, anything a non-engineer might reasonably need to add — belongs in the database, not a Rust/TS constant. Hardcoding stays reserved for genuinely algorithmic code (parsing/transform logic, validation rules, a pipeline's own required-fields list). Concrete precedent: vendor-format recognition, previously hardcoded per-tool consts (`unit-group::format::{QSX, STORAGE_COMMANDER, DOOR_SWAP}`), moved to one shared `client_ops.vendor_format` registry read through `core::vendor_format` by both Group Prep and dedup — see [[Multi-Vendor Unit-File Discovery]] for the original per-tool version this replaced, and [[Dedup Tool Index|Dedup Tool]] for dedup's own Easy Storage Solutions onboarding that prompted the generalization.

## Project history

Started as a CLI utility for comparing CSV exports, evolved into this web app; CLI code has since been fully removed. Session handling uses `Arc<RwLock<Session>>` handle-based access (`with_session()`/`with_session_mut()`, now via `SessionStoreExt` in `unitprep-core`) to avoid deep cloning.

**2026-07-15: major architecture session** — converted the single-crate backend into the workspace described above, ran two independent external-review passes (see [[Code Review Watchlist]] for the full list of findings and what was fixed vs. deliberately deferred), and split several oversized files into per-concern modules. `v1.0.0` tag still points at the original commit; none of this session's work bumped the version (internal architecture work, not a user-facing release) except one `[Unreleased]` CHANGELOG entry for the one real API-contract change (stage violations: 200 → 409).

## Development workflow

Established 2026-07-15, held steady through 2026-07-16's larger session: don't commit until a step is genuinely complete and tested; one commit per logically-distinct change, not batched; dry technical commit messages, never naming which review tool flagged something; flag any source file approaching ~250 lines and ask about splitting rather than doing it silently (250 is explicitly not a strict cap — split only when it genuinely improves modularity, leave a legitimately cohesive large file alone). These commit-cadence, commit-style, and 250-line-alarm conventions are tracked as standing personal working-style preferences rather than project facts, separate from this note.

Boris explicitly treats external AI review (Grok, used across both sessions) as **a collaborator to verify against, not an authority to trust blindly** — every Grok finding gets checked against the actual code before acting on it; the same standard applies to AI-generated suggestions generally.

**Verification habit that emerged 2026-07-16**: for structural changes (new session/API layers, crate extractions), don't stop at `cargo build`/`cargo test` passing — also run `cargo clippy --workspace --all-targets -- -D warnings` (strict mode catches real things regular test/build don't), and do at least one live run against the actual server (start it, hit real endpoints with curl, inspect real response bytes) rather than trusting unit tests alone for anything touching a whole pipeline's wiring.

## Status as of end of 2026-07-17 session, and what's next

The 2026-07-17 session (see [[Code Review Watchlist]] for the architecture punch-list closed out, and [[Dedup Tool Index|Dedup Tool]] for the full backend feature work — correction-note enrichment, cell references, related-tenant detection, xlsx export) left both tools' **backend logic caught up to everything discovered so far** — nothing known is sitting unimplemented on the backend side, and the UI has been kept in lockstep with every backend change (not a lagging "remaining task").

Boris's explicit direction for that next session: **move on to arranging and polishing the UI** — this reads as visual/UX refinement of the existing Group Prep + dedup screens, distinct from the still-on-hold "Client Prep" navigation wrapper (see [[Platform Vision (Onboarding Orchestrator)]], deliberately parked until the UI-polish pass is done) and distinct from the bigger "Onboarding Orchestrator" vision (same note — real, but explicitly for-awareness only at that point, no trigger yet).

Also still open at that point, not yet resumed: the Turbopack dev-server root-cause investigation (see [[UnitPrep UI Dev Environment]] — confirmed to affect Boris's own real terminal, not just scripted invocation; root cause still unconfirmed, a `package.json` `--webpack` default was proposed but not yet applied pending that).

> [!note] Later developments not covered here
> Subsequent work — the auth/persistence build-out, multi-vendor unit-file discovery, the validation/warnings redesign, and further review-and-refactor passes — is tracked in its own notes under `work/`, not folded into this architecture overview. See [[Platform Vision (Onboarding Orchestrator)]] and [[Post-Refactor Audit]] for the most current state.

## Related

- [[UnitPrep File Locations]]
- [[Dedup Tool Index|Dedup Tool]]
- [[Platform Vision (Onboarding Orchestrator)]]
- [[Code Review Watchlist]]
- [[UnitPrep UI Dev Environment]]
- [[UnitPrep Context Skill]]
