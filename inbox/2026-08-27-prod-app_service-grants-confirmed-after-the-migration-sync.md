---
date: 2026-08-27
description: "Closes the one open item from the prod DB sync: Boris ran scripts/setup_app_service_role.sql against NEON_PROD_DATABASE_URL_DIRECT himself and it comp"
tags:
  - project-note
source_repo: development
---

# Prod app_service grants confirmed after the migration sync

Closes the one open item from the prod DB sync: Boris ran scripts/setup_app_service_role.sql against NEON_PROD_DATABASE_URL_DIRECT himself and it completed cleanly (GRANT, GRANT, ALTER DEFAULT PRIVILEGES, then 7 guarded DO blocks, no errors) -- app_service now explicitly has grants on client_ops.vendor_format, the table created by the migration sync.






## Related

- Synced prod DB (5 migrations) and shipped the left-nav name display feature _(no note yet)_


_Recorded 2026-08-27T22:11:37.970Z from `development` via the om MCP server (routing: fallback)._
