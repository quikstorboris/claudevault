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

## Related

- [[UnitPrep File Locations]]
- [[Dedup Tool Index|Dedup Tool]]
