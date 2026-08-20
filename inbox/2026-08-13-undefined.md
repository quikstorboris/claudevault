---
date: 2026-08-13
description: "Pivoted the QMS Template Tagging Assistant's 'Replace' (remove-underscores) style away from the color-hiding approach shipped earlier this session, to"
tags:
  - project-note
source_repo: bmaksimov
---

# 

Pivoted the QMS Template Tagging Assistant's "Replace" (remove-underscores) style away from the color-hiding approach shipped earlier this session, to underline-based blanks -- the user's own idea, developed further via a research request I ran mid-session. Root cause chain: (1) counting characters when padding a removed blank doesn't preserve visual width, since glyphs differ in rendered width (fixed via keep-characters-hide-with-color); (2) but even with hiding fixed, the TAG TEXT ITSELF (e.g. "{{d.now}}") still occupies a different width than the underscores it directly replaces in the center of the blank, since curly-brace/letter glyphs render narrower than underscores -- confirmed with real Times New Roman AFM-style metrics (~2.5mm narrower per field at 10pt, compounding on lines with multiple fields); (3) crucially, this whole pursuit was aimed at the wrong target: QMS's own eventual real-value merge will insert a value of yet another unrelated length in the same spot, so exact width-matching for an intermediate {{tag_key}} placeholder was never going to survive to the final document anyway. The user proposed underlining the tag instead (matching a convention this corpus's own templates already use -- Northwest Heated Mini Storage: 192 blanks, zero literal underscores, purely underline-formatted) since an underline extends under whatever text is there regardless of length, elegantly handling both the intermediate proofing copy AND (assuming QMS preserves run formatting on merge, which is how virtually every template engine including this codebase's own substitution model works) the final real-value merge too. Implementation: docx-surgeon's HiddenBlankEdit/color machinery (added same-session, only briefly shipped) was deleted outright rather than kept as a dead alternative; UnderlineEdit replaces it, reusing the same run-splitting-to-protect-label-formatting approach but writing <w:u w:val="single"/> instead of <w:color>, and needs no padding/centering math at all since underline has no "too short to fit" degrade case. User also proposed tab-stops to stabilize same-line field alignment (UNIT # not shifting when OCCUPANT NAME's blank content changes length) -- deliberately deferred as a follow-up, not built yet, pending seeing whether underline alone resolves enough of the visual drift. Verified against the real Sumas document via a throwaway example (same pattern as prior verifications) before shipping: no panics, well-formed XML, tags land directly after labels with zero leftover underscore characters. Shipped as commit 79f8ce8, pushed to origin/main. Also noteworthy: mid-session, an unrelated OTHER Claude session running concurrently on this same machine left dedup/src/relatedness.rs in a broken (non-compiling) mid-refactor state, which blocked `cargo test -p unitprep` until the user's other session resolved it -- confirms multiple concurrent sessions on this repo do share the same working tree and can transiently break each other's builds; worth checking `git status` for unfamiliar uncommitted changes before assuming a compile failure is self-inflicted.







_Recorded 2026-08-13T17:07:14.282Z from `bmaksimov` via the om MCP server (routing: fallback)._
