---
date: 2026-10-14
description: "Template Tagger now recognizes underlined-tab blanks and empty-cell initials boxes (Longview/T.C.'s lease went from 2 wrong hits to 7 correct tags); apply/save no longer requires a checked row"
tags:
  - project-note
quarter: Q4-2026
source_repo: bmaksimov
---

# Template Tagger: underlined-tab blanks, empty-cell initials, and "ignore" that still saves

Trigger: Boris ran the Longview Self Storage / T.C.'s RV rental agreement (`longview_self_storage_99987_rental_agreement-3-1.docx`, a PDF-converted form) through the tagger and got only two hits, both wrong or unwanted (`u.num` proposing the word "SIZE", `d.now` proposing a stray ")"), then "Download Without Changes" produced a copy with zero tags. The real gap: the form draws every fill-in line as an **underlined tab** (no `_` anywhere) or leaves an **empty table cell** (initials), and the library only knew underscore blanks and already-filled values.

## What changed (api, uncommitted as of this note)

- `docx-surgeon/read.rs` — `FlatText` now carries `underlined_tabs` (flat offsets of `<w:tab/>` inside underlined runs) and `empty_paragraph` (insertion point for a table cell with no text). **Bug fixed in passing:** tab-stop *definitions* (`<w:tabs><w:tab w:val=.. w:pos=../>`) were being flattened as real `\t` characters.
- `docx-surgeon/edit` — a zero-width edit into an empty cell writes a new run into its empty paragraph (both `<w:p></w:p>` and self-closing `<w:p/>`); two zero-width edits at the same point now conflict.
- `template-tagger::recognize_tab_blanks` (+ `find_label_ends`) — first underlined tab after a label, reached through only spaces / `:` / `$` / `#` within `max_gap_chars`. A plain tab is a separator, never a blank.
- `tagger-pipeline` — tab blanks are exact (Auto tier); `to_edit` inserts the tag *before* the tab and leaves the tab (the drawn line); an empty cell directly after a cell that *ends with* a label (`initials here,`) is that label's blank.
- `recognize_filled_values` — no longer proposes a "value" that is itself another label, or that has no letters/digits (this is what produced the two bad hits).
- `views.rs` — a tab-blank candidate's own tab shows as `⇥`; an empty-cell candidate's snippet is the label cell + `[empty cell]`.
- Migration `20261014160000_seed_underlined_tab_and_initials_cell_patterns` — `m.indate` ("DATE OF LEASE"), `e.keycodes` ("Access Code"), `e.init` ("initials here"), anchored `e.a.name` ("Name:") / `e.a.email` ("Email:") after "ANOTHER PERSON". **Applied to the Neon dev DB only; prod not yet.**
- unitprep-ui — Apply/Save no longer disabled with nothing checked ("Download Without Changes"); rows say Apply/Ignore; sections explain unchecked = left alone.

## Result on the real lease

7 Auto tags, 0 Needs Review noise: `m.indate`, `u.dim` (existing "SIZE" pattern), `e.keycodes`, `e.a.name`, `e.a.email`, `e.init` x2. Output docx well-formed; every other zip part byte-identical.

## Verified: `m.indate` is right for "DATE OF LEASE"

In QMS's official tag list; Stowaway and Rest Stop use it for "AGREEMENT is entered into on ..."; this lease says "entered into ... as of the date set forth above" and "Term ... shall commence as of the date set forth in Section 1.A". `d.now` is only right next to the owner's signature (see [[QMS Template Tags — Evidence from Real Documents]]).

## Not covered / decisions left open

- **Unit number**: the form prints one blank per facility ("LVSS ⇥ TC'S ⇥"); which is `u.num` depends on whose copy of the template it is. Not seeded.
- **Monthly rate** (`m.effrate`): locked with the other m.*/l.*/d.* tags until the disambiguation mechanism exists; Boris only asked for `m.indate`.
- **~25 text-box fields** (occupant name/address/phone/..., DOB, driver's license, lienholder): floating label boxes over drawn lines; pairing needs page geometry. Not attempted.
- **Initials drawn as grouped shapes** (paragraphs 8, 9 and similar) have no text container at all — only the table-cell kind is handled.
- Pattern rows live in the DB: prod needs the migration applied via `scripts/prod_db_sync.sh`.

## Related

- [[2026-08-14-filled-document-field-detection-shipped|Filled-document field detection]] — the `recognize_filled_values` this session tightened
- [[QMS Template Tags — Open Questions & Mismatches]]
- [[QMS Template Tags — Catalog & Editor Design]]

## Part 2 (same day, later): floating text-box labels — the core name/contact fields

Boris re-ran the lease and the core fields (names, phone, address, email, DOB, license) were still untagged. They are **floating text boxes** (one per label, sized to the label, laid over a drawn field bar — no text container for the value). Tag goes at the end of the label's own box, and the box must grow or the value is clipped.

- `docx-surgeon/textbox.rs` (new) — reads each box's page position/size (`wp:anchor`, `wp:extent`, the shape's `a:ext`), page width + right margin from `w:sectPr`, and computes `room_to_right`: up to 2pt short of the next box on the same row (same anchor paragraph, `v` within 4pt), else the page's right content edge. Boxes in a group shape have no usable geometry and are never touched.
- `docx-surgeon/read.rs` — **`mc:Fallback` copies are no longer read at all** (each floating shape is stored twice; every text box label was being found/edited twice). A box's text now ends with a line break so it can't glue onto the next body text ("ANOTHER PERSON" + "IN ADDITION" had read as "PERSONIN" and broke every anchor).
- `docx-surgeon/edit/textbox_growth.rs` — an edit appended at a box's end also rewrites both widths (`wp:extent` and `a:ext`), together; the legacy Fallback copy is untouched.
- `template-tagger::recognize_textbox_blanks` — a label that is the *whole end* of a box (only `: , . # $` and spaces after it) → zero-width candidate at the box end. Only boxes with room to grow are offered.
- `tagger-pipeline` — new `Origin` (Exact / Guess / AmbiguousLabel). An **unanchored** pattern whose label repeats in the document (Sumas' generic `CITY` vs the occupant's, alternate contact's and lienholder's "City:") is only a suggestion (NeedsReview), and yields to an anchored exact candidate on the same span. Exact duplicates are still *not* collapsed (existing test `reports_candidates_from_both_matchers_without_deduplicating` is a deliberate rule).
- Migration `20261014180000_seed_text_box_label_patterns` — occupant (`e.fname/lname/phone/post/state/city/email`, anchored on "Occupant Name - First:"), `e.dob`, `e.dlnum`, alternate contact (`e.a.phone/city/address/state/post`, anchored on "MAY BE SENT." within 100 chars — the lienholder's "Address:" is ~134 chars past it, which is what keeps it out). **Dev DB only.**

Result on the real lease, using the dev DB's actual 39 pattern rows: **22 Auto tags, 1 NeedsReview** (the lienholder "City:", which has no QMS tag). 15 text boxes widened; document.xml well-formed; every other zip part and every Fallback copy byte-identical.

Underscore blanks: the existing tests already cover Replace and PreserveBlank underlining the tag; added a case for a blank split across two runs (tag appears once, underlined, original bold kept). The 4 underscore blanks left in this lease are separate underscore text boxes whose "initials" label lives in a different (grouped) shape — not linkable by text.

Still not covered: lienholder block, "Cell:" (QMS has only `e.phone`), "Employer:", initials boxes drawn as group shapes, unit number (one blank per facility), `m.effrate`.

## Part 3: Boris's calls on the remaining fields (migration `20261014200000`, dev DB only)

- **Cell → `e.phone`**: rule from Boris — map "Cell" to `e.phone` whenever there is no more specific alternative (e.g. a home-phone tag); QMS has none.
- **Employer → `e.comp`: NO.** `e.comp` is the tenant's company name for a business tenant, not an employer. Employer stays untagged.
- **Lienholder block: leave alone.**
- **Rental rate → `m.effrate`**: approved for this move-in lease (the m.* lock in the crate docs still applies to everything else).
- **Unit number**: `u.num` on the **LVSS** blank only (Boris: "company unit maybe?" — unresolved what that means for the T.C.'S blank; left untagged).

Real lease via the dev DB's 42 pattern rows: **25 Auto tags, 1 NeedsReview** (lienholder "City:").

## Part 4: grouped initials boxes + Dropbox-first save (api migrations `20261014200000`, `20261014220000`; dev DB only)

- **Initials inside group shapes** (the two "By placing his/her initials here, [square], Occupant acknowledges..." boxes): the square is a drawn shape with no text. `TextBoxTracker` now reads each group child's position/size, and for a label box finds the text-less shape that starts just after it on the same row (`GroupBlank`: byte offset of the square's `<wps:bodyPr`, plus the label's own `<w:rPr>`). Applying writes a `<wps:txbx>` with a centered run into the square, in the label's font; the label's own text is untouched. The group's outer border (starts at the left edge) is excluded by position.
- **`repeats` flag on a pattern** (`LabelProximityPattern.repeats`, JSON key `"repeats"`): a label that legitimately recurs for the *same* tag ("initials here" under each paragraph) is not the section ambiguity of an unanchored "City:". The `e.init`/"initials here" row is marked `repeats: true` (migration `20261014220000`).
- Real lease via the dev DB's 42 pattern rows: **27 Auto tags, 1 NeedsReview** (lienholder "City:"); all four initials boxes (2 empty table cells, 2 grouped) are Auto.
- **UI (unitprep-ui)**: Dropbox is the main action. With a facility folder, "Save to Facility Folder" is first and primary, and the local download is a quiet secondary button ("Download a copy (N substitutions)"), only on demand. With no folder, the download is the primary button. Nothing fires automatically.

## Shipped

`unitprep-api` **v1.9.124** (`01404a6` engine, `fba139a` pattern seeds + SCHEMA.sql, `33c85c5` version/changelog) and `unitprep-ui` **v1.6.97** (`d375bc0`, `7d6e770`), both pushed with tags, preflight green. **Prod migrations NOT yet applied** (the auto-mode classifier blocked the agent from running `scripts/prod_db_sync.sh` against prod; by design that script is run by Boris interactively): pending on prod = `20261014120000` (Syrasoft, from 1.9.122) + `20261014160000`, `20261014180000`, `20261014200000`, `20261014220000` (this work). Run `scripts/prod_db_sync.sh`, then deploy.
