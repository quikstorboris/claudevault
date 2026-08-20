---
date: 2026-08-07
description: "Accumulating findings from reading real QMS templates (client before/after pairs, QMS's own Standard Templates library) — confirmed tag-usage patterns, a newly-discovered syntax feature, and evidence behind the editor design's rules. Split out of the main design note to keep it from growing unbounded."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS Template Tags — Evidence from Real Documents

Split out of [[QMS Template Tags — Catalog & Editor Design]] 2026-08-08 once
this section outgrew the main note — this is where evidence accumulates as
more real documents get reviewed; the main note stays the stable
catalog/design reference. Add new findings here as new documents turn up.

## Tag syntax discovery: date-offset arithmetic, `{{tag±N}}`

Not in `tags.txt` at all — found by reading real documents from QMS's own
`! Standard Templates\DOCUMENTS\` library (2026-08-08):

- `Late Notice.docx`: `{{l.ptd+1}}` — paid-through-date, plus one day (the
  actual due date), and `{{l.baldue}}`/`{{l.unpaidtable}}` used normally.
- `Lien Notice - Tenant.docx`: `{{d.now+15}}` — today, plus fifteen days
  (the lien-sale deadline).

**This means the tag catalog isn't just a list of keys — the tag language
itself supports inline day-offset arithmetic on at least some date tags.**
A catalog lookup that only exact-matches `tag_key` against the 221 known
strings would silently fail on `l.ptd+1` (which isn't itself one of the 221).
Any detector or validator needs to parse a `base_tag(+|-)N` grammar, not
just do a literal string match. **Open, not yet confirmed**: which tags
support this (any date-typed tag, or only some?), whether negative offsets
work, and whether units other than days are supported — logged in
[[QMS Template Tags — Open Questions & Mismatches]].

## Confirmed from real documents, 2026-08-08

Read three full before/after client pairs (Stowaway Storage/Kingsburg CA,
Rest Stop Storage/Greeley CO, Sumas Mini Storage/Sumas WA) plus several of
QMS's own canonical `! Standard Templates` (the Default Lease, Late Notice,
Lien Notice - Tenant). Findings that sharpen or confirm the design:

**Three-for-three: facility-specific one-time fees with no catalog tag stay
as static literal text, never blanked, never guessed at.** Stowaway's Admin
Fee/Lock Fee, Sumas's Setup Fee ($15, left as a literal dollar amount) and
Refundable Lock Deposit (left as an untagged blank) all confirm the same
pattern independently, across three unrelated clients in three different
states. High-confidence rule now, not just a hypothesis from one example.

**Status 2026-08-08**: Boris confirmed fees are configured individually per
facility in QMS and is checking directly with QMS whether any tag mechanism
applies to them at all — see question 3 in [[QMS Template Tags — Open
Questions & Mismatches]]. Don't re-derive this from more documents in the
meantime; wait for his answer rather than guessing further from pattern-
matching alone.

**A third blank category, not just "tagged" vs. "no tag exists."**
`Lien Notice - Tenant.docx`'s "Declaration in Opposition to Lien Sale"
section — address, phone, signature, date lines for the **tenant** to fill
out **by hand** when disputing the lien — is entirely blank, correctly.
This isn't a missing tag; it was never a QMS-populated field to begin with.
The candidate classifier needs three buckets, not two: (1) substitute a
tag, (2) no tag exists for a QMS-tracked concept — flag it, (3) not a QMS
field at all, a human-fill-in-later blank — leave alone, don't even flag.

**Vehicle lienholder vs. general lienholder are genuinely different tags,
confirmed by real contrast.** Rest Stop's vehicle stored-property row uses
`{{m.vi.lhfn}}`/`{{m.vi.lha}}` (vehicle-specific lienholder); Sumas's
general "Name and Address of Lienholder(s)" field (not vehicle-specific in
that document) uses `{{m.opi.lhfn}}`/`{{m.opi.lha}}` instead. `opi` = "other
property information," matching `PropertyInformationGatewayResponse` in
[[QMS API - Domain Model & PII]] — resolved, not just suspected.

**"Declared value," even inside a vehicle-info row, is the general
`{{m.estval}}` tag, not a `m.vi.*` one.** Rest Stop's vehicle row uses
`m.vi.make`/`m.vi.model`/`m.vi.pn` for vehicle-specific fields but
`{{m.estval}}` (a top-level Move-In tag) for the dollar value — confirms a
value can look like it belongs to a sub-family by table position while
actually being the general-purpose tag. Position in the document is not a
reliable signal for which prefix applies.

**A blank/placeholder sample value in the source document is not itself a
signal to skip tagging.** Rest Stop's raw document had "Lienholder Name and
Address: N/A" (this particular tenant had none) — still correctly tagged as
`{{m.vi.lhfn}}, {{m.vi.lha}}` in the formatted version, because the *field*
is always populatable even though *this sample* happened to be empty. Judge
whether the concept maps to a tag, not whether the sample data was present.

**A real, human-authored "no tag exists" annotation convention is already
in active use.** Rest Stop's raw/formatted pair left one field as literal
text: `"Customer's Provided Exact Overall Length: [NO QSX2 TAG – Customer
Provided Overall Length]"` — a bracketed note, evidently written by whoever
tagged this document, marking a field they confirmed has no QMS equivalent.
**Open question, not resolved**: what "QSX2" refers to precisely (a formal
name for this tag/version system distinct from how "QMS" has been used so
far, or an informal shorthand) — logged in [[QMS Template Tags — Open
Questions & Mismatches]]. Regardless of the answer, this is worth adopting
directly: if OMs already write `[NO <SYSTEM> TAG – <description>]` by hand,
the tool's own "no tag exists" flag should probably render in the same
convention rather than inventing a different one.

**QuikStor's own Default Lease document independently confirms the
"don't touch wording" rule** — in QuikStor's own words, not just Boris's
internal caution: *"QuikStor cannot, and will not, be able to offer any
legal advice/consultation for your rental agreement nor make any changes to
the formatting or wording."* This is the vendor's stated policy, and this
tool inherits the same constraint for the same reason.

**QuikStor calls them "variables," not "tags," in client-facing material**
— worth knowing as alternate terminology when talking to anyone on the QMS
side. The Default Lease document also gives an explicit **priority list of
the most common ones**: First Name, Last Name, Address, City, State, Zip,
Tenant Phone, Tenant Email, Tenant Driver License, Tenant DL State, Unit
Number, Paid Through Date, Monthly Rent. Good candidate ordering for phase 2
of the editor's build plan (see [[QMS Template Tags — Catalog & Editor
Design]]) — these are the fields QMS itself considers highest-value to get
right first.

**The owner-signature-line name is tagged inconsistently across real,
currently-in-use documents.** QMS's own `Lien Notice - Tenant.docx` and the
Sumas agreement both tag it (`By: {{f.name}}`, `FOR {{f.name}}`); Rest
Stop's leaves it as literal text (`By: /s/Rest Stop Storage`). Logged as an
open mismatch, not resolved — see [[QMS Template Tags — Open Questions &
Mismatches]].

**The "date this agreement is executed" phrase maps to different tags in
different real documents.** Stowaway and Rest Stop use `{{m.indate}}`
("AGREEMENT is entered into on {{m.indate}}"); Sumas uses `{{d.nowlong}}`
("THIS LEASE is executed this {{d.nowlong}}") for what reads as the same
semantic slot — though Sumas *separately* uses `{{m.indate}}` for its
distinct "Term... shall commence on" sentence a few lines later, so this
may be a real, deliberate distinction (signing date vs. term-commencement
date can genuinely differ) rather than a plain inconsistency. Logged
unresolved either way.

## Grounded in a real example: Stowaway Storage (Kingsburg, CA)

Read the actual finished template Boris referenced:
`Stowaway Storage Rental Agreement Formmated .docx`, in the client's own
Dropbox onboarding folder. This is real, already-tagged output — evidence
of what a human OM actually produces today, not a hypothetical. Findings
that should shape the tool's design directly:

**Not every similar-sounding field has a matching tag — a real trap already
present in this document.** The form has two visually similar sections:
"ALTERNATE MAILING INFORMATION" (a secondary mailing address for the tenant
*themselves*) and "ALTERNATE CONTACT" (a different person, for lien-notice
purposes). Only the second maps to QMS tags (`e.a.name`, `e.a.add1`, etc.) —
`EndUser` has exactly one `address` field and one `alternateContacts[]`
array (see [[QMS API - Domain Model & PII]]), so "Alternate Mailing
Information" has **no tag to map to at all** and correctly stays blank/manual
in the finished template. A naive "these two sections look similar, tag them
the same way" heuristic would get this wrong. Any automated candidate-finder
needs to fail closed here (propose nothing) rather than guess.

**Date tags require real judgement, confirmed against a real resolved case.**
The document uses three different treatments for what looks like "a date"
on the surface:
- Dates that are terms of the agreement itself (lease start, the date
  referenced in "AGREEMENT is entered into on ___") → `{{m.indate}}`
- The date the document itself was generated, next to the Owner's signature
  line → `{{d.now}}`
- The date the *Occupant* actually signs → left as a blank underscore,
  **not** tagged at all, because it isn't known until the real, later,
  in-person or e-signed moment — generation time isn't signing time.

This is exactly the `d.now` vs. `m.indate` ambiguity Boris flagged as hard
before any real example existed — now there's a resolved, correct instance
of it to test candidate-detection logic against.

**Some concepts that clearly exist in QMS's data model still don't get
tagged, on purpose.** The Admin Fee and Lock Fee lines, and both fee-schedule
tables (late charges, lien processing fees, dishonored-check fee, etc.), are
left as blank underscores or static dollar amounts — even though move-in
charges data exists in the API ([[QMS API - Domain Model & PII]]'s
`oneTimeFees[]`) and these are clearly per-facility-configurable amounts.
There's simply no tag for them in the 221-tag catalog. Confirms: "a plausible
match exists in QMS's data" is not the same test as "a tag exists for it" —
the tool must check against the actual tag catalog, never infer a tag ought
to exist.

**The signature convention doesn't match the tag catalog exactly.** The
document uses literal `/s/{{e.name}}` (a typed-name placeholder) at
signature lines, not the catalog's `{{sig}}`/`{{esign}}` tags. QMS's own
Default Lease document, by contrast, uses `{{sig}}` directly ("Electronic
Signature Sample: {{sig}}"). So both conventions are real and in active use
somewhere — worth confirming with whoever actually operates QMS's template
system which is actually expected/functional for a given e-signature setup,
rather than assuming either generalizes. Logged in [[QMS Template Tags —
Open Questions & Mismatches]].

**Real, visible document-quality issues already exist in this exact
finished template** — repeated mangled apostrophes (`Occupant's` rendering
as `Occupant�s` throughout, an encoding artifact) and a stray `?` character
in the fee-schedule table. Neither is a tagging issue; both are exactly the
"typo/quality flag, never silently fix" case Boris named. Good concrete
evidence the flagging half of this tool has value even independent of the
tagging half.

## A broken tag already in QMS's own Standard Templates library

`! Standard Templates\DOCUMENTS\Courtesy Notice.docx` — the canonical
default template, not a one-off client copy — contains a literally broken
tag, `{f.add2}}` (missing its opening brace), in its sign-off block. QMS's
merge engine can't resolve that; it would print the broken tag literally in
every generated letter using this template or a copy of it. Real, live
evidence for exactly the "highlight, don't silently fix" rule in
[[QMS Template Tags — Catalog & Editor Design]] — and worth reporting to
whoever maintains this template library independent of anything
Orchestrator builds, since it's a production issue today, not a
hypothetical.

## Related

- [[QMS Template Tags — New Families & Label Glossary]] — a second batch of
  real-document evidence (2026-08-08) confirming `{{esign}}`'s actual role,
  `{{mp.total}}`/`{{mp.trledg}}`, and `{{l.rectrans}}` in live use, plus six
  tag families this note's three-document sample never encountered
- [[QMS Template Tags — Catalog & Editor Design]] — the stable catalog and
  design this evidence feeds into
- [[QMS Template Tags — Open Questions & Mismatches]] — unresolved
  questions raised by this evidence
- [[QMS API - Domain Model & PII]] — the API-schema fields several findings
  above cross-reference
