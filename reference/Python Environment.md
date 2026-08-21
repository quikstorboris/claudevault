---
date: 2026-07-27
description: Python 3.14.6 and pip are properly installed and on PATH on this Windows machine, replacing earlier Store-alias failures.
tags: [reference, environment, python]
---

# Python Environment

As of 2026-07-09, a real Python 3.14.6 install is on PATH and resolves correctly from both the Bash tool and PowerShell (`python`, `python3`, and `py` all work). This replaced an earlier state where `python`/`python3` only resolved to Windows Store alias stubs that failed with "Python was not found."

`pip` (26.1.2) also works, so third-party packages can be installed on demand (e.g. `pandas`, `openpyxl`, `python-docx` for the xlsx/docx skills) without needing to pre-install anything.

Verified working end-to-end by running the actual `duplicate_tenant_check.py` script (see [[Dedup Tool Index|Dedup Tool]]) against a real sample file — output matched a known-good prior result byte-for-byte.

**No special setup needed going forward** for Python scripts on this machine — just invoke `python <script>` via Bash or PowerShell directly.

**Re-confirmed 2026-08-21 on the new laptop (`QSLP14`, see [[New Laptop Migration — QSLP14]])**: same shape, `python`/`python3` resolve (this time via the WindowsApps alias path specifically, forwarding to a real install at `AppData\Local\Python\pythoncore-3.14-64` — not the old broken Store-stub behavior this note originally replaced), `pip` 26.2.1, a basic script runs. Just a newer patch version (3.14.7 vs. 3.14.6) — this is evidently per-machine state, not something that carries over with a laptop swap, so it's worth a quick re-check like this on any future migration too.

## Related

- [[UnitPrep File Locations]]
- [[Dedup Tool Index|Dedup Tool]]
