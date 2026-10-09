---
date: 2026-10-09
description: "Facility Map: a new facility-level tool tab (beside Dedup) for picking map/plan files from Dropbox, rendering them side by side, and linking or creating the matching ClickUp task. Every decision with Boris's answers. NOT BUILT; spec only."
tags: [work-note, unitprep, facility-map, clickup, dropbox, design]
status: active
quarter: Q4-2026
project: unitprep
---

# Facility Map — Design and Requirements

> [!warning] Status (2026-10-09): spec only, nothing built
> Boris asked for the design to be written down first because a heavy session was running in parallel on the repos. Do not start building until that session has shipped; re-check the current code before implementing (it may have moved). Related: [[ClickUp Integration — Design Log]], [[ClickUp Copy — Design and Phase 1]], [[Onboarding Work Tabs and Run Recording]].

## What it is

Facility map/plan files are an onboarding step and, at the very least, a ClickUp task. New **Facility Map** tool tab on the facility level, in the top row where Dedup lives. It records into the Onboarding Work tab like Dedup does.

## Files

- Source is the **existing Dropbox integration**, same folder structure as everywhere else. Maps are usually in the root of the company/facility folder.
- **Manual selection only.** Never auto-search for map/plan files.
- **Multiple files** allowed. Types: images, PDFs, possibly XLSX, others depending on the third-party vendor.
- The Dropbox **facility root folder link** is stored and reused.
- **Decision: no file bytes in Neon (conserve Neon).** Store per file: Dropbox file ID (survives moves/renames), path, name, size, type, revision, linked to the facility. Files render and download through short-lived Dropbox temporary links (about 4 hours), requested by the API after a permission check.
- If the file was permanently deleted/moved out of reach in Dropbox, show a message such as **"This file might no longer exist."** Do not fail the whole tab.
- May change later (storing a copy). Not now.
- **OO deletes nothing at this point**: no delete or replace of files; records are append-only.

## Rendering

- Images and PDFs render inline at **medium size, side by side, at most 2 per row**, wrapping into more rows (2 / 2 / 2 ...). XLSX and other types show as cards with download.
- Each preview can be **expanded** to a larger area wide enough that **the whole document fits by width** (for review), and **collapsed** again.
- The section's **horizontal width changes dynamically** with a **smooth momentary transition**, not an abrupt jump.
- Open point: a single file (half-width in the grid vs full row) not answered; suggested half-width plus the expand option.

## ClickUp task

- Search is limited to the facility's **linked onboarding list**, narrowed by keywords like "map", "plan", "layout" (and similar). Linking ClickUp is encouraged, not 100% enforced.
- **Link existing task:** pick a match, or **skip and link/edit later** (must be supported). Existing comments are shown; new ones can be added.
- **No task exists:** create one with subject, comments, **assignee and due date** (due date blank by default).
- Assignee and due date are also selectable when **linking** an existing task.
- On file selection, **one comment is posted** listing the **file names** and the **Dropbox folder link to the facility root**. **No new comments afterwards** (ClickUp logs attachment and other actions itself). **No attachments** uploaded to ClickUp (links only; revisit only if file bytes are ever stored).
- Created map task: status **"Ready for You"**, assignee = the facility's **default VA**, no other assignees unless explicitly specified. Verify "Ready for You" exists in the onboarding list's statuses (statuses are per list); fallback behavior still undecided.

## Default VA and Default Tasks (Facility General tab)

- The **ClickUp section of the Facility General tab** gets an optional **Default VA** picker, from the ClickUp assignee dropdown. The VA is a human (has a ClickUp user record), despite the name. Stored per facility.
- A **Default Tasks** button (in the ClickUp table) opens a selection: the most common tasks on top, **pre-selected**, and all other ClickUp tasks below for additional selection. Initial pre-selected list:
  1. The facility **MAP** task
  2. **CONFIGURE Company DNS Records**
  3. **ADD USERS to QMS Demo & QS Learn**
- Selected tasks are assigned to the default VA **when created only, never when updated**.

## Permissions

Same roles as other onboarding tools: **onboarding and department managers** only (use the existing role names; check how they are named in the code).

## Later (separate item)

A **big, prominent notice during company creation** that Onboarding functionality is significantly reduced without a linked ClickUp.

## Open points

- Single-file layout (see Rendering).
- "Ready for You" fallback if a list lacks the status.
- Confirm the exact existing role names for permissions.

## Related

- [[ClickUp Integration — Design Log]], [[ClickUp Integration — Build Log]], [[Onboarding Work Tabs and Run Recording]], [[Orchestrator Feature Backlog]]

