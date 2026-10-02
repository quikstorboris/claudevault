---
date: 2026-10-02
description: "Onboarding Work now records Unit Group and Template Tagger runs and shows each activity on its own newest-first tab; Group Prep names the unit file in use."
tags: [work-note, onboarding-work]
status: active
quarter: Q4-2026
---

# Onboarding Work: tabs per activity and run recording

Status as of 2026-10-02: **committed** in `unitprep-api` (`b31c35c`) and `unitprep-ui` (`97cf3ba`), **not released**. Migration `20261002170000` is applied to the dev DB branch, not prod. The API in Docker needs a restart.

## What changed

- **Unit Groups and Template Tagger runs are recorded** next to Dedup, in `client_ops.tool_runs` (`tool` is now `dedup` | `unit_group` | `tagger`). They are recorded only when the run came from a facility's own page, because the facility id is what ties a run to a facility (`analyze` and `tagger/check`/`import-dropbox` take an optional `facility_id`).
  - **Unit Groups:** recorded at the analysis step (the first point with a result). Re-analysis after a correction updates the same row (`record_run` upserts by session). The summary is the analysis response plus the unit files and master group file it read. The export (download or Dropbox) is attached as the run's output (a ZIP).
  - **Template Tagger:** recorded when the template is checked (template name, places found, how many needed review, tags found); applying merges in how many tags were applied and attaches the tagged `.docx`.
  - No source file is stored for these two tools, so the "Download Source File" button does not appear for them. Output downloads still need `client_ops.perform`.
- **Onboarding Work page:** tabs Duplicate Check / Unit Groups / Template Tagger. Each tab is its own feed, **newest first** (ids are UUIDv7, the list orders by id descending), and only the open tab loads.
- **UI split by concern** (standing rule): `OnboardingWorkTab` (tabs), `ToolRunFeed`, `RunCard`, `RunActions`, `toolRunLabels`, and one details view per tool. `ToolRunSummary` is a union on `tool`.
- **Group Prep:** the Confirm Unit File Format section (and the confirmed summary) says which unit file(s) will be used.

## Limits

- Runs made before this release, and runs started outside a facility's page, are not recorded.
- Unit Groups runs are recorded at analysis, so a run that never reaches the analysis step leaves no record.

Related: [[Dedup Folder Scan and File Requirements]], [[Winsen Dedup Vendor Format - Required Testing]], [[Session 2026-09-11 — Onboarding Work Tab (Durable Tool-Run History)]].
