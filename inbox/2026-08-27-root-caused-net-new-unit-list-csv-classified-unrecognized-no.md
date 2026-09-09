---
date: 2026-08-27
description: "Investigated why a validly-named unit-list CSV (Pyott_Road_Winsen_unit_list_Boris.csv) for a net-new facility got 0 unit files found / unrecognized_fi"
tags:
  - project-note
source_repo: development
---

# Root-caused: net-new unit-list CSV classified unrecognized (no filename fallback in vendor detection)

Investigated why a validly-named unit-list CSV (Pyott_Road_Winsen_unit_list_Boris.csv) for a net-new facility got 0 unit files found / unrecognized_files=1 in discovery. Also located both session-duration configs (upload/discovery in-memory session vs. login/passkey session) ahead of a planned timeout change (4h / 8h). Investigation only, no code changed.



## Learned

- Unit-file classification (unitprep-api/src/api/discover/selection.rs reconcile_unit_file_selection, calling unitprep_core::vendor_format::detect_vendor) is PURELY header-signature based -- it never looks at the filename at all. A document becomes a unit-file candidate only if ALL of a registered client_ops.vendor_format row's signature_headers are present (case/separator-insensitive via CsvDocument::header_index); otherwise it falls through to is_group_document's Name/Description/Active(+ optional Assigned To/Status/Last Updated) check, and if that also fails it's counted unrecognized_files.
- As of the 20260818120000_create_vendor_format_registry migration, content_type='units' has exactly 3 seeded vendor rows: QSX (signature UnitGroup+Number+Category), Storage Commander (UnitGroup+Number+Category+Locality), DoorSwap (Unit+'Unit Type'+Status+Customer). A hand-authored/manually-built unit list for a brand-new facility (no PMS export) will not match any of these header sets and is guaranteed to classify as unrecognized -- there is no lenient/fallback path for the 'net new facility, no master group file' mode on the UNIT-file side. (There IS an equivalent leniency already implemented for the master GROUP file: resolve_group_file_readiness in the same selection.rs explicitly treats zero group-file candidates as a legitimate ready state for a net-new client. No such treatment exists for zero unit-file candidates -- that gap is the actual bug/gap to close, either by adding more permissive/generic unit-file detection for net-new mode or by letting the user manually designate an unrecognized file as the unit file the same way group-file selection already allows.)
- Frontend message 'No unit files found -- check your folder selection' (unitprep-ui/components/DiscoveryPage.tsx ~line 400-405) is the LAST branch of the status ternary, reached only after: not ready, !requires_unit_file_selection, !requires_format_resolution, and the group-file-related branches are all false (satisfied in net-new mode once netNewAcknowledged=true) -- so in net-new mode this message fires purely off discovery.unit_files_found === 0, which is unit_file_candidates.len() from the backend, i.e. zero vendor-signature matches.
- Session-duration config: (1) upload/discovery in-memory session timeout (InMemorySessionStore -- also shared by dedup and tagger session stores) is read from env var SESSION_TIMEOUT_SECS in unitprep-api/src/main.rs lines 75-82, default 600s (10 min) if unset/unparseable -- matches the observed age_ms=626487 expiry. Changing this one env var affects all three tools' session stores identically (by explicit design/comment). (2) Login/passkey session has TWO independent knobs: absolute lifetime via SESSION_LIFETIME_HOURS env var (unitprep-api/src/auth/session_cookie.rs session_lifetime_hours(), default 12h, floor-checked >0) which sets both the cookie Max-Age and auth.sessions.expires_at in both auth_login.rs (~line 404-405, 480) and auth_register.rs (~line 685, 717); and idle timeout via SESSION_IDLE_TIMEOUT_MINUTES (unitprep-api/src/auth/authenticated_user.rs session_idle_timeout_minutes(), default 30 min, floor-checked >0), enforced inside auth.resolve_session/auth.check_session_expired independent of the absolute expiry. A request for '8-hour login session' needs to decide whether that's the absolute SESSION_LIFETIME_HOURS (default 12, would be lowered to 8) or something about the idle timeout (default 30 min, a different axis entirely) -- flagged to the user rather than assumed.



## Open

- Task 1 fix not yet decided/implemented: options discussed were (a) add a generic/lenient 'single CSV with plausible unit-ish columns' fallback path specifically for net-new mode, or (b) extend the existing manual group-file-style selection override to let a user designate an unrecognized file as the unit file. No decision made yet -- this was investigation only per explicit instruction not to change code.
- Task 2 not yet implemented: user still needs to decide exactly which login-session knob(s) to change to reach '8 hours' (absolute SESSION_LIFETIME_HOURS vs idle SESSION_IDLE_TIMEOUT_MINUTES) before editing; SESSION_TIMEOUT_SECS=14400 covers the 4-hour discovery/upload session ask directly but also changes dedup/tagger session timeouts as a side effect.



_Recorded 2026-08-27T19:12:48.999Z from `development` via the om MCP server (routing: fallback)._
