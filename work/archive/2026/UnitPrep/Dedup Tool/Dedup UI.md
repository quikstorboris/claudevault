---
date: 2026-07-27
description: "The unitprep-ui dedup frontend: mockup, build against existing conventions, live verification, and the WSL/Node environment quirks hit along the way"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# Dedup UI

Part of [[Dedup Tool Index]]. `unitprep-ui` originally covered only Group Prep; dedup had no frontend until this work.

## Design ideas discussed 2026-07-16, nothing built yet

A mockup was shown (artifact-style, not committed anywhere) proposing:

- A left-nav shell with the tool as one entry (superseded by the Client Prep concept — see [[Platform Vision (Onboarding Orchestrator)]] — but the *screen itself*, independent of what nav wraps it, still the right next build).
- Flow: upload (one QMS End Users CSV) → results → export, tied to the existing `session_id` so a page refresh re-fetches via `POST /dedup/report` instead of losing state.
- Results screen: summary stat tiles (total rows, unique tenants, multi-unit tenants, flagged-group count, typo-variant count), then two sections — flagged groups (note shown directly, a collapsed-by-default "what differs" detail using the real `FieldValueMismatch` values) and possible name/typo variants (both tenants + units + note, with a **qualitative badge** — "Contact info matches"/"differs" — instead of the raw similarity percentage, since a bare "86.67% similar" number invites false precision the ratio was never meant to carry).
- No interactive confirm/dismiss anywhere — matches the MVP scope (list only, corrections happen outside the platform — see [[Session, API & Scope Decisions]]).
- Real facilities so far had 0–3 flagged items total, not hundreds — deliberately not over-building for scale that hasn't shown up yet.
- States still to design: a genuine "no issues found" success state (the *common* case, not the exception), upload-error states reusing `unitprep-ui`'s existing `errorMessageFrom()` pattern, and a session-expired state matching Group Prep's existing one.
- **Open at the time**: a lightweight client-side-only "reviewed" checkbox per item (pure UI convenience, nothing saved server-side) vs. keeping the report purely read-only for v1.
- Before building, `unitprep-ui`'s actual codebase hadn't been explored yet this round — the mockup was informed by the backend contract only, not the frontend's real components/routing/styling conventions.

## Built and verified 2026-07-16

Explored `unitprep-ui`'s actual conventions first (App Router, `app/*/page.tsx` thin wrappers delegating to `components/*Page.tsx`, no component library, raw Tailwind utility classes, `<details>`/`<summary>` for collapsibles, inline `fetch` + `errorMessageFrom` per call site, no shared Button/Badge/StatTile components but a consistent hand-rolled shape for each) and matched it exactly rather than inventing a parallel style.

Built: `app/dedup/page.tsx` + `app/dedup/[sessionId]/page.tsx` (thin route wrappers), `components/DedupUploadPage.tsx` (single-file `<input type="file" accept=".csv">` mirroring `DiscoveryPage`'s hidden-input + styled-label pattern, minus `webkitdirectory`/`multiple`), `components/DedupResultsPage.tsx` (mirrors `ExportCompletePage`'s shape: loading/error/session-expired states, stats, findings, export button/download-complete state), plus `components/dedup/`: `useDedupReport.ts`/`useDedupExport.ts` (mirror `useAnalysis`/`useExportDownload` exactly, including the Strict-Mode double-fetch ref guard), `DedupSummaryStats.tsx` (config-array stat-tile grid like `SummaryStats.tsx`), `FlaggedGroupsSection.tsx` (per-group card with a nested collapsed "what differs" detail rendering real `FieldValueMismatch` values, not raw JSON), `TypoVariantsSection.tsx` (table with the qualitative badge instead of the raw ratio). Added matching TS types to `types/api.ts` (`DedupReport` and everything it nests), hand-checked field-for-field against the real Rust structs (`dedup/src/report.rs`, `types.rs`, `types/fields.rs`) rather than guessed.

**Open design points from the mockup resolved:**

- **"Reviewed" checkbox — settled 2026-07-17, closed, not revisited.** Asked Boris directly once, got no response; proceeded with the recommended default (skip it, stay purely read-only for v1, matching the already-agreed MVP scope). Re-confirmed as final while working through the post-launch tightening punch list. Not an open item anymore.
- Empty/success state: a green banner ("No duplicate tenants or name variants found across N unique tenants") when both `flagged_groups` and `typo_variant_candidates` are empty — treated as the expected common case.
- Session-expired and error states: reused `SessionExpiredPage` as-is and the existing `errorMessageFrom` idiom verbatim — no new components needed.

**Verified three ways, same discipline as the backend build**:
1. `node node_modules/typescript/bin/tsc --noEmit` — zero errors.
2. `node node_modules/eslint/bin/eslint.js` against every new file — zero warnings.
3. A live end-to-end run: rebuilt and restarted `unitprep-api` fresh (killed several stale `target/debug`/`target/release` processes left running from earlier sessions first — one from "Jul15" predated dedup's routes entirely, confirmed by a bare empty-body 404 instead of the app's structured error), confirmed `/health` now reports a `dedup_sessions` block, then uploaded a small hand-built synthetic CSV (deliberately constructed to trigger one flagged group — same name, different email — and one typo-variant candidate — "MARYJONES"/"MARYJOHNES", ~95% ratio, matching contact info) via curl to `/dedup/check`, and confirmed `/dedup/report` and `/dedup/export` both returned exactly the shape the new TS types and components expect. Real facility fixtures (No Ka Oi/New Castle) weren't used for this pass — they live in a KoBre Dropbox path this session didn't relocate quickly, and a synthetic fixture was faster and gave deliberate control over exercising both code paths.

## Environment notes

**WSL/Node quirk**: `unitprep-ui`'s WSL environment has no Linux-native Node.js on PATH — `npm`/`npx` resolve to the Windows install via WSL's interop, which breaks (a bare cmd.exe "UNC paths are not supported" error) when invoked with a WSL-side working directory from outside a real WSL terminal. The actual usable Linux node lives at `~/.vscode-server/bin/*/node` (bundled by the VS Code Remote-WSL extension) — that's what actually runs the already-live `next dev` process (confirmed running continuously since "Jul15", picked up the new dedup files via hot reload with no restart needed). Use that binary path for any future direct/scripted frontend build/test invocation from outside an interactive WSL session. (See also [[UnitPrep UI Dev Environment]] for the broader `--webpack` workaround and the never-run-`next build`-while-`next dev`-is-live rule.)

**Could not visually verify in a real browser this session**: the sandboxed Browser pane can't reach the WSL-hosted `localhost:3000`/`localhost:8080`, and Claude-in-Chrome had no connected browser (`list_connected_browsers` returned empty — extension not set up). Confirmed via PowerShell from the Windows host that both `localhost:3000/dedup` and `localhost:8080/health` are reachable, so Boris could open `http://localhost:3000/dedup` in his own browser directly — both servers left running intentionally for exactly that.

## Sequencing note

This UI build completed step 1 of the platform-vision gradual-build sequencing (see [[Platform Vision (Onboarding Orchestrator)]]) — nothing blocking remained before the "Client Prep" wrapper step at the time. Small follow-ups noted as worth a look later, not urgent: a real yes/no from Boris on the reviewed-checkbox default (later settled, see above), and the real KoBre Dropbox fixtures could replace the synthetic smoke test if a from-real-data regression check is ever wanted.

## Related

- [[Dedup Tool Index]]
- [[Session, API & Scope Decisions]]
- [[Note Enrichment & Copy Redesign]]
- [[UnitPrep UI Dev Environment]]
- [[Platform Vision (Onboarding Orchestrator)]]
