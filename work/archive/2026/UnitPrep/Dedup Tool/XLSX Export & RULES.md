---
date: 2026-07-27
description: "The xlsx export path (clickable cell refs, cluster background colors) built alongside CSV via a shared export-plan module, plus dedup/RULES.md"
tags: [work-note, unitprep, dedup]
status: completed
quarter: Q3-2026
project: unitprep
---

# XLSX Export & RULES

Part of [[Dedup Tool Index]]. Implemented 2026-07-17, alongside CSV rather than replacing it — reversing the earlier "CSV only, no xlsx needed" call (see [[Core Engine Implementation]]).

## Ask and design conversation

Boris's ask: dedup specifically needs real `.xlsx` output (Group Prep explicitly does not, per his own scoping). Same layout as the CSV (his own reasoning: xlsx's main practical edge is auto-fit columns — no more manually dragging CSV's condensed columns open in Excel). Both formats available side by side with the UI prompting for a choice (including "both at once"). After a follow-up design conversation: correction notes that cite a specific cell should become **clickable** (jump to that cell), and each group/candidate cluster should get its own **background color** so adjacent findings are easy to isolate visually.

**Real technical constraint surfaced and agreed on before writing code**: a single xlsx cell can only carry one hyperlink, but a note often cites several fields/cells. Resolved (Boris: "one link to one field is fine, since usually all other referenced fields will be in the same cluster") — the note cell links to the *first* cited cell only; the rest of the citations stay as plain text in the same note. Not a real loss in practice since every cited cell for a given note always belongs to that same small cluster of rows.

## Architecture

Rather than writing xlsx as an independent copy of the CSV exporter's row/column logic (real risk of the two silently drifting apart — exactly the kind of duplicated-logic bug class this project has been bitten by before), extracted a new shared module, `src/infrastructure/dedup_export_plan.rs`, that both `dedup_csv_export.rs` and the new `dedup_xlsx_export.rs` consume. It owns `COLUMNS`, a `PlannedRow` enum (`Data { record, note, cluster, hyperlink_target }` / `Blank` / `Marker`), and `build_export_plan(report, all_records)` — the exact same row-ordering/note/cell-ref logic that used to live directly in the CSV writer, now serialization-agnostic. The `cell_refs` submodule (col-letter math, the `FieldName`→column-name map, `note_with_cell_refs`) moved from CSV-specific to living under this shared plan module, plus gained `first_cell_ref` for the xlsx hyperlink target (see [[Cell References]] for the fuller cell-ref history).

**Real lifetime issue hit and fixed along the way**: `PlannedRow` initially tried to *borrow* `TenantRecord`s, but the typo-variant/related-tenant sections re-derive their groups from a fresh `group_records` call (owned data with no lifetime tying it back to the original `all_records` slice) — fixed by having `PlannedRow` *own* its `TenantRecord` (boxed, per a clippy `large_enum_variant` catch, since `Blank`/`Marker` are tiny by comparison) rather than borrow it. Cloning cost is a non-issue at real facility data volumes, same as several other places this crate already clones records freely.

## Dependencies

New dependency: `rust_xlsxwriter` (0.96 — no existing dependency covers writing; `calamine`, already a dependency, is read-only, used only for parsing uploaded files). Also added `calamine` as a **dev-dependency** of the binary specifically to read the xlsx exporter's own output back in its tests — real verification (header row, cell values, note text) instead of "some bytes came out."

## API and frontend

`/dedup/export` gained a `format: "csv" | "xlsx" | "both"` field (`#[serde(default)]` → `Csv`, so an existing caller sending no format at all keeps today's behavior unchanged). `"both"` reuses Group Prep's own `csv_export::build_zip` helper directly — one ZIP, one download, no new zip-building logic. Frontend: `DedupResultsPage.tsx` gained a radio-button format picker (mirroring `DiscoveryPage`'s own existing radio-button convention for the master-group-file choice, not a new UI pattern) feeding into `useDedupExport`'s `handleExport(format)` (format is now a call-time argument, not fixed at hook-creation time).

## Verified, in layers

1. Unit tests: `dedup_export_plan_tests.rs` (cluster indices increase correctly, only a cluster's first row carries the note/hyperlink target, related-tenant rows never get a hyperlink target), the moved `cell_refs_tests.rs` (plus new `first_cell_ref` tests), `dedup_xlsx_export_tests.rs` (reads its own output back via `calamine` — header row, flagged-group notes with cell references, the related-tenants section), updated `dedup_csv_export_tests.rs` and `dedup_tests.rs` (new xlsx/both-format handler tests, including a default-format test proving an omitted field still means CSV).
2. Full workspace suite: 136 tests passing, `cargo clippy --workspace --all-targets -- -D warnings` clean (two real strict-mode catches fixed along the way: the `large_enum_variant` above, and an `explicit_counter_loop` in the xlsx writer's row-advance logic, switched to `(1u32..).zip(plan.iter())`).
3. Live verification against the real running server: generated a real xlsx from a real flagged-group session, then **unzipped it and inspected the raw XML directly** (xlsx is itself a zip of XML) since `calamine` only reads cell values, not formatting — confirmed a genuine `<hyperlink ref="C2" location="'Duplicate Tenant Check'!T2" .../>` entry and a genuine `<fgColor rgb="FFDDEBF7"/>` fill in `styles.xml`, i.e. both the clickable-link and color-coding requirements are structurally present in the real output, not just asserted by code review. Also verified CSV, xlsx, and `"both"` (a real 2-file ZIP) all work end-to-end via the live server, and that omitting `format` entirely still defaults to CSV.

**Flagged, not yet split**: `src/api/dedup.rs` grew to 277 lines (was ~200) after adding the format-branching response helpers (`build_csv_response`/`build_xlsx_response`/`build_zip_response`/`file_response`) — past the 250-line alarm threshold. Borderline whether these helpers are their own separable concern or just part of the export handler's own logic; left as-is and flagged rather than split speculatively.

## Committed, pushed to origin/main

Three separate thematic commits: `unitprep-api` `8be2e4e` (the `dedup_export_plan` extraction, pure refactor, no behavior change — deliberately split out first so it's independently reviewable/bisectable from the feature that needed it) and `f337ea3` (the actual xlsx writer + API format field + new dependencies), `unitprep-ui` `303dd3b` (the format picker UI). The `mod.rs` module declaration for each new module was temporarily hand-split across the two backend commits (edited out, committed, edited back in) specifically so each commit's own file set matches what it actually needs.

## dedup/RULES.md

Written the same session (2026-07-17) as the resolution to a side-discussion about whether dedup's rules should move into one centralized module or an external config file — see [[Core Engine Implementation]] for the full reasoning (config file rejected in favor of the existing one-module-per-kind-of-rule architecture). `RULES.md` itself: plain-English, one section per rule with a pointer to its implementing module, an explicit "update this file in the same change" instruction, and a documented "how to add a new rule" section at the end. Meant to be useful to both a human and a future AI session picking this crate back up.

## Related

- [[Dedup Tool Index]]
- [[Cell References]]
- [[Core Engine Implementation]]
- [[Related-Tenant Detection]]
- [[Patterns#UnitPrep: flag modules approaching ~250 lines]]
