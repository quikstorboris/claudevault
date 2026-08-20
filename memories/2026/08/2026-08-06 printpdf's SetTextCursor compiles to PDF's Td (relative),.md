---
date: 2026-08-06
description: "When manually building a PDF page as a flat `Vec<Op>` (printpdf 0.12's `Op`-based API, not the higher-level HTML/layout path), `Op::SetTextCursor {…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-06T15:27:24.232Z"
scope: general
projects: []
confidence: verified
---

# printpdf's SetTextCursor compiles to PDF's Td (relative), not an absolute position -- use SetTextMatrix/Tm for grid layouts

When manually building a PDF page as a flat `Vec<Op>` (printpdf 0.12's `Op`-based API, not the higher-level HTML/layout path), `Op::SetTextCursor { pos }` looks like it sets an absolute page position -- the field is literally named `pos: Point` -- but printpdf's own serializer (`serialize.rs`) compiles it straight to the PDF `Td` operator: `content.push(LoOp::new("Td", vec![pos.x.0.into(), pos.y.0.into()]))`. Per the PDF spec, `Td tx ty` moves the text line matrix *relative to the start of the current line*, not to an absolute page position. Calling it more than once inside one `BT...ET` text section -- exactly what a grid/table layout needs, one call per cell -- makes every position accumulate on top of the one before it. The visible symptom is severe and easy to misdiagnose: only the very first piece of text in the section lands where intended: everything after it drifts progressively further off-page and is invisible, so a multi-column table renders as a title plus one lone header cell and nothing else, looking like the whole render pipeline is broken rather than one wrong operator choice.

The fix is `Op::SetTextMatrix { matrix: TextMatrix::Translate(x, y) }`, which compiles to the PDF `Tm` operator -- `Tm` *replaces* the text matrix outright per the spec (printpdf's own doc comment on `TextMatrix` says this explicitly: "unlike CurTransMat, TextMatrix uses the Tm operator which COMPLETELY REPLACES the current text matrix"). Each call is genuinely absolute regardless of how many text draws came before it in the same section. `TextMatrix::Translate` takes `Pt`, not `Mm` -- build the point via `Point::new(Mm(x), Mm(y))` (which converts through `Into<Pt>`) and pass its `.x`/`.y` fields into `Translate`, rather than hand-rolling the mm-to-pt conversion.

Generalizes beyond this one crate: any PDF-generation library that exposes a raw `Td`-equivalent operator as a "positioning" primitive has this exact trap, because `Td`'s relative semantics are the actual PDF-spec behavior underneath most such abstractions, and naming/API design frequently makes it look absolute. When a from-scratch PDF render produces almost nothing visible except the very first text draw, check whether the positioning call is spec'd as relative-to-current-line before assuming the renderer, the font, or the page setup is broken.

## How this is known

Reproduced directly on unitprep-api: a real rendered PDF (read back and visually inspected) showed only the title and the word "Time" repeated on every page, matching the predicted symptom exactly. Switching every text-placement call from Op::SetTextCursor to Op::SetTextMatrix{TextMatrix::Translate} fixed it immediately -- the same render then showed the full 6-column table across all rows and pages. Added a regression test asserting two consecutive calls each produce their own absolute SetTextMatrix value, independent of each other.
