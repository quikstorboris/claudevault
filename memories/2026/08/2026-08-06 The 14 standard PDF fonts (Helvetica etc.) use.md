---
date: 2026-08-06
description: "A PDF built on printpdf's (or any PDF library's) built-in/standard-14 fonts -- Helvetica, Times, Courier, no embedded TTF -- renders text through…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-06T15:27:35.735Z"
scope: general
projects: []
confidence: verified
---

# The 14 standard PDF fonts (Helvetica etc.) use WinAnsiEncoding, which has no arrow glyph (→) -- Unicode text needs an ASCII-safe stand-in or it silently becomes "?"

A PDF built on printpdf's (or any PDF library's) built-in/standard-14 fonts -- Helvetica, Times, Courier, no embedded TTF -- renders text through WinAnsiEncoding (essentially Windows-1252/CP1252), not full Unicode. Most "smart punctuation" survives fine because CP1252 happens to include it: em dash (—, U+2014) is CP1252 0x97, horizontal ellipsis (…, U+2026) is CP1252 0x85. But common arrow characters are not in CP1252 at all -- U+2192 (→) has no slot -- so any glyph outside the encoding's ~256-character set silently renders as a fallback character (typically "?") with no error, warning, or panic anywhere in the pipeline. This is easy to miss in code review because the string looks completely reasonable ("status: active → deactivated") and only fails at the rendering step, on a real render, for that one specific character.

Before shipping user-facing or generated text through a standard-14-font PDF path, check every non-ASCII character used against CP1252's actual character set rather than assuming "it's just punctuation, it'll be fine" -- em dash and ellipsis happen to work, arrows and most other Unicode symbols (checkmarks, bullets beyond •, most typographic arrows) do not. When in doubt, prefer an ASCII-safe equivalent (e.g. "->" instead of "→") -- it is unambiguous, always renders correctly regardless of font/encoding, and for a plain-text-style report is arguably more appropriate anyway than a typographic character that depends on the exact rendering path.

Generalizes beyond printpdf: this is a property of WinAnsiEncoding/CP1252 and the standard-14 PDF fonts themselves, so it applies to any PDF-generation approach (any language, any library) that renders through the base fonts rather than an embedded Unicode-complete TTF. The moment a project embeds a real font file instead, this constraint disappears entirely (an embedded font can carry a much larger, even full-Unicode, glyph set).

## How this is known

Reproduced directly on unitprep-api: a rendered audit-log PDF with a before/after diff summary containing "→" showed a literal "?" character in place of the arrow in the actual PDF (visually confirmed by reading the generated file back). Replacing "→" with "->" in the source string and re-rendering produced the correct, fully readable text with no other changes needed -- confirming the encoding gap was the entire cause, not a font-selection or layout issue.
