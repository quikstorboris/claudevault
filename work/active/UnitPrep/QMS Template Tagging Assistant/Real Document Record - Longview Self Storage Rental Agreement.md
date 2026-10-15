---
date: 2026-10-14
description: "Exhaustive record of the Longview Self Storage / T.C.'s RV rental agreement (PDF-converted .docx): its structure, every field and the tag chosen, decisions, expected output, gaps. First record under the real-document rule."
project: UnitPrep
status: active
quarter: Q4-2026
tags:
  - real-document
  - fixture
  - template-tagger
---

# Real Document Record - Longview Self Storage Rental Agreement

Written for Claude: exact over narrative, long over short. Rule: [[Real Documents Are the Spec]]. Session narrative: [[2026-10-14-underlined-tab-blanks-and-empty-cell-initials]].

## 1. Provenance

- **Original path:** `C:\Users\bmaksimov\KoBre Dropbox\QS Fileserver\Shared\QMS Onboarding\Longview Self Storage\longview_self_storage_99987_rental_agreement-3-1.docx`. The same file (same hash) also sat in `...\QMS Onboarding\TC's RV & Mini Storage\TC's RV & Mini Storage\` and a PDF twin `longview_self_storage_99987_rental_agreement-3-1.pdf` (364,049 bytes) sits beside the .docx.
- **Obtained:** 2026-10-14, supplied by Boris while onboarding Longview Self Storage / T.C.'s RV & Mini Storage. Facility-side file number `99987`; form revision printed on the page: `REV. 7/10/26`.
- **Produced by:** a PDF-to-Word conversion (shapes named `Textbox N`, `Graphic N`, `docshape N`; text boxes with zero insets; every paragraph carried as many tiny runs).
- **Size / SHA-256:** 49,265 bytes; `cb5fe60a32ff61b54320a23ba983f74de76c400c1298adca8c1e387a7a515284`.
- **Repo fixture:** `unitprep-api/tagger-pipeline/tests/corpus/longview-self-storage-rental-agreement/` (`input.docx`, `patterns.json`, `expected.json`, `README.md`).
- **Fixture is:** the original, byte for byte. It is a blank template with no personal data (business names, addresses, phone numbers of the facilities are public).
- **Tagged outputs Boris produced while we iterated** (in `...\Longview Self Storage\Tagged Templates\`): `tagged_2026-10-14_1455.docx` (0 tags: "Download Without Changes" with both candidates unchecked), `_1536` (7 tags), `_1608` (25), `_1615` (25, still missing the 2 grouped initials). Each is an output of a specific code state, so they are evidence, not fixtures.

## 2. Structure facts (measured with a script over `word/document.xml`, 690,297 bytes)

| Fact | Value |
|---|---|
| Zip parts | 13: `word/document.xml`, `settings.xml`, `styles.xml`, `fontTable.xml`, `numbering.xml`, `theme/theme1.xml`, `_rels/document.xml.rels`, `media/image1.png`, `docProps/{app,core,custom}.xml`, `[Content_Types].xml`, `_rels/.rels` |
| Page | `w:pgSz w:w="12240" w:h="20160"` (8.5 x 14 in, legal); `w:pgMar top=20 bottom=0 left=360 right=360` (right margin 360 twips = 18 pt, so the page's content right edge is 594 pt) |
| Paragraphs / runs / `w:t` | 232 / 4,975 / 4,866 |
| Tables / cells | 2 / 8 |
| `mc:AlternateContent` | 63; each has one `mc:Choice` and one `mc:Fallback` (63/63) |
| `w:txbxContent` | 96 total = 48 in `mc:Choice` + 48 in `mc:Fallback` (every text box is stored twice) |
| `wpg:wgp` group shapes | 12 |
| `wp:anchor` / `wp:inline` | 58 / 6 |
| Real `<w:tab/>` | 49 |
| Tab-stop definitions `<w:tab w:val=... w:pos=.../>` | 74 (these are NOT tab characters; the old reader flattened them as `\t`) |
| Literal underscore runs (>= 3 `_`) in `w:t` | 5 |
| Underlined `<w:tab/>` runs | 28 (flat-text offsets of the underlined tabs are recorded in `FlatText.underlined_tabs`) |
| Text boxes readable after skipping Fallback | 48 (41 free-standing with geometry, 7 in groups without) |

How each number was obtained: regexes over the unzipped `document.xml` (see the session note for the one-off scripts); the Rust reader's own view is `docx-surgeon::read_docx` -> `FlatDocument { body, table_cells, textboxes, page }`.

## 3. Field-by-field table

"Blank kind" is how the form draws the place where a value goes; it decides which recognizer finds it.

| Section | Label (as in the file) | Blank kind | Tag | Tier | Why |
|---|---|---|---|---|---|
| Lease info | `DATE OF LEASE:` | underlined tab | `m.indate` | Auto | Same slot Stowaway and Rest Stop tag `m.indate`; this lease says "entered into ... as of the date set forth above" and "Term ... shall commence as of the date set forth in Section 1.A". `d.now` would be wrong (that is today's date). |
| Lease info | `B. STORAGE SPACE LVSS <blank> TC'S <blank>` | underlined tab after `LVSS` | `u.num` | Auto | One unit blank per facility; this is the Longview Self Storage copy. Boris: "LVSS blank only - company unit maybe?" (meaning of "company unit" unresolved). |
| Lease info | `C. APPROX. UNIT SIZE:` | underlined tab | `u.dim` | Auto | Existing pattern label `SIZE`. |
| Lease info | `D. Access Code:` | underlined tab | `e.keycodes` | Auto | QMS tag "Access/Gate Codes". |
| Lease info | `F. Rental Rate Per Month: $` | underlined tab after `$` | `m.effrate` | Auto | Boris approved for this move-in lease. Tag lands right after the `$`. |
| Lease info | `E. Administration Fee: $15.00` | literal amount | (none) | - | Fixed text, not a blank. |
| Occupant | `Occupant Name - First:` | text box | `e.fname` | Auto | Box grows to the next box on its row. |
| Occupant | `Last:` | text box | `e.lname` | Auto | Anchored on "Occupant Name - First:". |
| Occupant | `_Phone:` | text box | `e.phone` | Auto | The leading underscore is in the converted file's own text. |
| Occupant | `Zip:`, `State:`, `City:` | text boxes | `e.post`, `e.state`, `e.city` | Auto | Anchored on the occupant name label. |
| Occupant | `Address:` | text box | `e.address` | Auto | Pre-existing anchored pattern (`OCCUPANT NAME` within 120). |
| Occupant | `Email:` | text box | `e.email` | Auto | Anchored on the occupant name label. |
| Occupant | `Cell:` | text box | `e.phone` | Auto | Boris: map Cell to `e.phone` always when there is no more specific alternative (e.g. a home-phone tag). QMS has none. |
| Occupant | `Employer:`, employer `Phone:` | text boxes | (none) | - | Boris: NOT `e.comp`; `e.comp` is for a tenant that is a business. |
| Occupant | `Active Military:` Yes/No | text box | (none) | - | Checkbox style, no tag. |
| Alternate contact | `Name:` | underlined tab (body text) | `e.a.name` | Auto | Anchored on "ANOTHER PERSON". |
| Alternate contact | `Phone:` | text box | `e.a.phone` | Auto | Anchored on the end of the header sentence "...MAY BE SENT." within 100 chars. |
| Alternate contact | `City:`, `Address:`, `State:`, `Zip:` | text boxes | `e.a.city`, `e.a.address`, `e.a.state`, `e.a.post` | Auto | Same anchor. |
| Alternate contact | `Email:` | underlined tab (body text) | `e.a.email` | Auto | Anchored on "ANOTHER PERSON" within 700. |
| Lienholder | `Address:`, `City:`, `Phone:`, `State:`, `Zip:`, `Lienholder or Secured Party:` | text boxes | (none) | - | Boris: "leave lienholder block alone"; no lienholder tag in the QMS list. Its `City:` is the one Needs Review row (the generic Sumas `CITY` pattern repeats in the document, so it is only a suggestion). |
| ID | `D.O.B.` | text box | `e.dob` | Auto | |
| ID | `Driver's License:` (curly apostrophe U+2019) | text box | `e.dlnum` | Auto | |
| Initials | `By placing his/her initials here,` x2 | empty table cell (cells 1 and 5) | `e.init` | Auto | Label cell ends with the label; next cell is empty. |
| Initials | `By placing his/her initials here,` x2 | square inside a group shape | `e.init` | Auto | The square is a drawn shape with no text; the tag is written into it as a text shape. |
| Credit card | `CARD NUMBER:`, `Expires:`, `Name on Credit Card:` | underlined tabs | (none) | - | No tags for payment data. |
| Credit card | 4 `___________` underscore text boxes | underscores in separate boxes | (none) | - | Their "initials" label lives in a different (grouped) shape, so they cannot be linked by text. |
| Late fees | `Late rent charge ... of $20.00` etc. | literal amounts | (none) | - | Fixed fee schedule. |
| Signature | `Please sign here "Occupant"` | | (none) | - | Signing happens later; not known at generation. |

Result: 28 candidates, 27 Auto (applied), 1 Needs Review. The 27 tags in document order are in `expected.json`.

## 4. Decisions (Boris's words where he gave them)

- "include move-in date {{m.indate}} but verify." Verified: in QMS's official tag list (`reference/QMS API/QMS Template Tags (as of 2026-08-07).txt`), used by Stowaway/Rest Stop for the signing document's date.
- "textbox fields have a line where initials will go. {{e.init}} tag should be used for that." (Turned out to be empty cells and group squares, not text boxes.)
- "Cell -> e.phone - always if there are no other specific alternatives (e.g. home phone)."
- "Employer -> e.comp - no this is a situation where tenant is a business (tag), so not necessarily an employer."
- "leave lienholder block alone."
- "tagger should find those consistently, reliably and accurately. careful with formatting too. underscores have proven to be tricky. when replacing underscores with tags, tags need to be underlined." Replace and PreserveBlank both underline the tag; a test covers a blank split across runs.
- "if i want to ignore the 2 tags that needed review, i want the file to be updated with everything else that i WAS able to find." Apply/Save work with any subset checked, including none.
- Rejected: tagging the "TC'S" unit blank in this copy (would print the unit number twice); widening nothing and appending the tag to a label-sized box (clipped); matching text boxes by page geometry alone.

## 5. Expected output

- `expected.json` path: `unitprep-api/tagger-pipeline/tests/corpus/longview-self-storage-rental-agreement/expected.json`
- Reproduce: `cd ~/Development/unitprep-api && cargo test -p unitprep-tagger-pipeline --test corpus` (re-bless after an intended change: `UPDATE_CORPUS=1 ...`, then review the diff).
- Applied-output checks the test enforces for every corpus case: edited `document.xml` is well-formed; all 12 other zip parts byte-identical; all 63 `mc:Fallback` copies byte-identical; each Auto candidate applied exactly once. Measured on the real file (2026-10-14): 15 free-standing text boxes widened, e.g. `Occupant Name - First:` 78 pt -> 171 pt (stops 2 pt before `Last:` at 220 pt), `Zip:` 13 pt -> 79 pt, `D.O.B.` 22 pt -> 405 pt (no right neighbor, so to the 594 pt content edge).

## 6. Open questions and known gaps

- "company unit maybe?" (Boris, on the LVSS blank): what it means for the TC'S blank is unresolved. Resolving it: ask Boris which template copy each facility uses.
- The Word layout of widened boxes and initials squares is unverified in Word (no renderer available in the session). Resolve: open `tagged_*.docx` in Word and look.
- Four underscore text boxes remain unlinked (see table). Resolve: a text-order-independent way to pair a group's label with a separate underscore box, or accept manual tagging.
- Lienholder tags: need QMS tag names for lienholder name/address/phone, if Boris ever wants them.
- `m.effrate`: the `m.*` lock in the `template-tagger` crate docs is bypassed here by an explicit per-pattern decision. Revisit when a real move-in vs lease disambiguation mechanism exists.

## 7. Raw excerpts

Underlined tab blank (label run, then a run holding only an underlined tab):

```xml
<w:r><w:t>LEASE: </w:t></w:r><w:r><w:rPr><w:u w:val="single"/></w:rPr><w:tab/></w:r>
```

Free-standing text box (Choice side; the Fallback copy has the same text in a `v:shape`). Width lives in two places that must change together:

```xml
<wp:anchor><wp:positionH relativeFrom="page"><wp:posOffset>597395</wp:posOffset></wp:positionH>
<wp:positionV relativeFrom="paragraph"><wp:posOffset>3419</wp:posOffset></wp:positionV>
<wp:extent cx="985520" cy="106680"/> ... <a:ext cx="985520" cy="106680"/> ...
<w:txbxContent><w:p><w:r><w:t>Occupant</w:t></w:r><w:r><w:t> </w:t></w:r>...<w:r><w:t>First:</w:t></w:r></w:p></w:txbxContent>
```

Group shape with an initials square (child offsets in EMU, group scale 1:1):

```
Graphic 85  off=(0,0)          ext=3352165x224790  border, no text
Graphic 86  off=1198880,17157  ext=537210x114300   the initials square, no text   <- tag goes here
Textbox 87  off=75438,20561    ext=1136650x91440   "By placing his/her initials here,"
Textbox 88  off=1728911,20561  ext=1557020x91440   ", Occupant acknowledges that he/she has"
```

Empty initials cell (cells 1 and 5): `<w:tc>...<w:p></w:p></w:tc>` between a cell ending `initials here,` and a cell starting `, Occupant acknowledges`.

Flat text the matchers see (excerpt; `\t` underlined-tab or plain tab, `\n` paragraph or text-box end):

```
...F. Rental Rate Per Month: $\t\n\n\nOccupant Name - First:\n\nLast:\n\n_Phone:\n\nZip:\n\nState:\n\nCity:\n\nAddress:\n\nEmail:\n\nBy providing an email address...\n\nCell:\n\n...
PROVIDE THE NAME AND ADDRESS OF ANOTHER PERSON\nIN ADDITION TO YOURSELF ... MAY BE SENT.\n\n\nPhone:\nName: \t\t(\t) \t\n\nCity:\n\nAddress:\n\nState:\n\nZip:\nEmail: \t\n\nWHO HAVE AN INTEREST ...
```

The anchor `MAY BE SENT.` within 100 chars reaches the alternate contact's labels (Zip: is ~50 chars past it) but not the lienholder's `Address:` (~134 chars past it).

## 8. Links

- Commits: api `01404a6` (engine), `fba139a` (pattern seeds), `33c85c5` (v1.9.124); ui `d375bc0`, `7d6e770` (v1.6.97). The corpus harness is added after v1.9.124 (see the audit note).
- Session work note: [[2026-10-14-underlined-tab-blanks-and-empty-cell-initials]].
- Audit that created the corpus: [[Test Audit 2026-10-14]].
- Related: [[QMS Template Tags — Evidence from Real Documents]], [[QMS Template Tags — Catalog & Editor Design]].
