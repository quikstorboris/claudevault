---
date: 2026-08-07
description: "Running log of unresolved questions, ambiguities, and real mismatches found while working with QMS's template tag system. Living doc — append new entries, don't let them get lost in conversation."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS Template Tags — Open Questions & Mismatches

Started 2026-08-07, per Boris's request: a dedicated place to accumulate
questions and discovered inconsistencies about QMS's tag system as we
actually work with more documents, rather than letting them live only in
conversation and get lost. Add to this list as new documents turn up new
cases — don't resolve items here without evidence; move a resolved item to
[[QMS Template Tags — Catalog & Editor Design]] once it's actually answered,
and mark it resolved here with a pointer.

## Open

**Signature convention: `/s/{{e.name}}` vs. `{{sig}}` — narrowed, not
resolved.** A real template use of `{{esign}}` ("Open and sign the document
here: {{esign}}") clarified that `{{esign}}` belongs to notification
messages (email/SMS) linking to a signing flow, not to the document being
signed itself — see [[QMS Template Tags — New Families & Label Glossary]].
Still open: which of `/s/{{e.name}}` (Stowaway/Rest Stop/Sumas) or `{{sig}}`
(QMS's own Default Lease) is the one that actually functions **inside** a
document body for a given e-signature setup. Found 2026-08-07, narrowed
2026-08-08.

**Does the template system support conditional logic?** Three tags resolve
to true/false rather than a display value (`{{e.alt}}` "Is Alternate
Contact Present", `{{e.mil}}` "Is Military Profile Present", `{{l.excldel}}`
"Is Excluded From Delinquency") — found via QMS's own tag-picker labels,
see [[QMS Template Tags — New Families & Label Glossary]]. Are these
literal Yes/No display tags, or can a template show/hide a block based on
one? Matters for the "no tag exists for this field" cases already logged —
some might actually be expressible via a conditional plus manual text.
Found 2026-08-08.

**What does "QSX2" refer to?** Found in a real tagged document (Rest Stop
Storage): a human tagger left `[NO QSX2 TAG – Customer Provided Overall
Length]` on a field with no QMS equivalent. Is "QSX2" a formal name for this
tag/template system, distinct from how "QMS" has been used in this whole
note set so far, or informal shorthand from whoever wrote it? Doesn't block
anything today, but worth knowing before assuming "QMS" and "QSX2" are
interchangeable. Found 2026-08-08.

**Owner-signature-line name: tagged or literal?** QMS's own `Lien Notice -
Tenant.docx` and the Sumas agreement both tag it (`{{f.name}}`); Rest
Stop's leaves it as literal company name. Real inconsistency across
currently-in-use documents — which is actually correct? Found 2026-08-08.

**"Date agreement is executed": `d.now`/`d.nowlong` or `m.indate`?**
Stowaway and Rest Stop use `{{m.indate}}` for "AGREEMENT is entered into
on..."; Sumas uses `{{d.nowlong}}` for the equivalent "THIS LEASE is
executed this..." phrase, while separately using `m.indate` for its
distinct term-commencement sentence. May be a genuine, deliberate
distinction (signing date vs. commencement date can differ) rather than an
error — needs confirming, not guessing. Found 2026-08-08.

**Date-offset arithmetic (`{{tag±N}}`) — how far does it extend?** Confirmed
real usage: `{{l.ptd+1}}`, `{{d.now+15}}` (see [[QMS Template Tags —
Evidence from Real Documents]]). Unconfirmed: which tags support this (any
date tag, or only some), whether negative offsets work, and whether units
besides days exist. Not in `tags.txt` at all — only found by reading real
documents. Found 2026-08-08.

**`f.ow.*` (Facility owner) tags have no corresponding field anywhere in the
QMS API schema.** Either this is genuinely QMS-UI-only data (never exposed
via the gateway API) or it maps to something in the API under a name that
wasn't recognized as "the facility owner." Low priority — nothing currently
needs this confirmed — but worth resolving before building anything that
assumes API/tag parity. Found 2026-08-07.

**Which real client templates actually need `m.*`/`l.*`/`d.*` disambiguation, and does it correspond to a rule we can infer, or only to genuinely knowing the document's QMS category?** Surfaced 2026-08-14 building `recognize_filled_values` (see [[2026-08-14-filled-document-field-detection-shipped|Filled-document field detection]]) — `template-tagger`'s own scope lock (dated 2026-08-10) excludes these tag families until a real disambiguation mechanism exists, and this note's own catalog entry already names the pairs:

| Concept | Move-in / signing context | Lease / post-move-in context (delinquency, statements) |
|---|---|---|
| Security deposit | `m.secdep` | `l.secdep` |
| Effective rate | `m.effrate` | `l.effrate` |
| Move-in date | `m.indate` | `l.indate` |
| Excluded delinquency | `m.excldel` | `l.excldel` |
| Date/Time vs. Delinquency (`d.*`) | `d.now`/`d.nowlong` (most contexts) | `d.trledg`, `d.earliest.auction.closing.date` (delinquency-adjacent contexts) |

Boris: this needs real research against actual templates before it can be
resolved either way — not yet known which of the currently-tagged client
templates (Stowaway, Rest Stop, Sumas, or others reviewed in
[[QMS Template Tags — Evidence from Real Documents]]) actually exercise
both sides of any given pair, or whether a document's own content/structure
would let a rule infer its QMS category without being told. Tracking table
below, to be filled in as documents get checked:

| Template | Document appears to be | `m.*` tags seen | `l.*` tags seen | `d.*` usage | Notes |
|---|---|---|---|---|---|
| *(unfilled)* | | | | | |

Found 2026-08-14.

## To check directly in QMS (not questions for QuikStor's developers)

These don't need a developer — they need another look at a page we already
know how to reach (QMS → Templates → Tag List, per the screenshot Boris
shared 2026-08-08 — see [[QMS Template Tags — Catalog & Editor Design]]'s
"real UI structure" section for the five category URLs).

**Which of the five categories do the six new families actually live
under?** Transfer, Move-Out, Manual Payment, Reservation, Login Link,
Move-In Link (see [[QMS Template Tags — New Families & Label Glossary]])
were found in a second pasted dump without clear section boundaries.
Reasonable guesses (Transfer/Move-Out under Lease Tags, Manual Payment
under Manual Tags) — not confirmed.

## Opportunity: bulk-capture every tooltip via the browser, not by hand

Boris found 2026-08-08 that hovering a tag in QMS's Tag List page shows a
tooltip with its plain-English label. Investigated live via Claude in
Chrome the same day, connected to Boris's actual logged-in session on
`app.trial.quikstor.com` — findings:

- **The tooltip text is not a static DOM attribute.** Inspecting a tag
  chip's HTML directly showed no `title`/`aria-label`/`data-*` holding it.
- **It's mounted into the DOM only on real hover**, as a
  `div.bg-black.text-white.rounded-lg` containing the label text — findable
  and readable via a script once hovered.
- **A synthetic, script-dispatched hover (`MouseEvent('mouseover')` etc.)
  did not reliably trigger a fresh tooltip** — a test loop dispatching
  synthetic events across several tags got stuck showing the *first* tag's
  label for every subsequent one. **A real hover (via the browser
  extension's actual cursor movement, not a dispatched event) did work
  correctly** every time it was tried, confirmed by both a screenshot and a
  script reading the tooltip element immediately after.
- **Net result: no single-pass script can harvest this.** It needs one real
  hover per tag, each followed by a short pause and a read — mechanical and
  fully scriptable as a loop, just not a one-shot console script. Given
  ~300+ tags across five categories, that's a real but bounded amount of
  automated work, not a blocker — paused pending Boris's call on whether to
  run the full sweep now.

## Status 2026-08-08 — paused

Boris found something that may be further useful regarding tags and asked
to pause before starting any implementation (Template Tagging Assistant
Phase 1/2 was about to start as a new `template-tagger` crate in
`unitprep-api`, with a DB migration for the tag catalog). Nothing built
yet — waiting on what he shares next before resuming.

## Resolved

**The Trigger Tags category's actual contents, confirmed live 2026-08-08.**
Visited `/template-tags/trigger` directly via Claude in Chrome, connected
to Boris's real logged-in QMS session. It contains exactly three
sub-contexts: **Company User Send Registration Email** (Company Tags, User
Tags `cu.*`, Send Registration Tags `sr.link`), **Company User Reset
Password**, and **Schedule Reports** — matching content already known from
`tags.txt`, just now correctly attributed to the Trigger Tags category
rather than guessed as sitting under Delinquency Tags. The "Corporate /
Facility" scope value logged elsewhere does **not** appear to belong here —
still unaccounted for.

**Mass Document Send genuinely has fewer tags than similar contexts —
confirmed, not a cut-short transcription.** `tags.txt` is Boris's own
hand-typed copy of what he saw in QMS's UI, not a system export — so
"looked truncated" here meant "looked like his copying stopped partway
through" (every other context with Tenant/Facility tags also has Lease and
Unit tags following; this one just stopped after Facility Tags). Boris
checked directly against QMS's live UI 2026-08-08: that's the real,
complete list — Company, Date/Time, Tenant, Facility only, no Lease or Unit
tags. Detail moved to [[QMS Template Tags — Catalog & Editor Design]].

## Questions to take to QMS/QuikStor developers

Compiled 2026-08-08, extended 2026-08-08. Full text lives in its own
standalone note — [[QMS Tag System — Questions for QuikStor]] — written
with zero reference to Orchestrator, this vault, or any internal process,
so it can be copied or forwarded to someone at QuikStor exactly as written.
Eleven questions, covering (in order): whether an authoritative tag spec
exists at all, the date-offset arithmetic syntax found in real templates,
how fees are represented (if at all), the two signature-placeholder
conventions found in use, the two same-concept-different-tag
inconsistencies found across real templates, whether QMS validates
templates before they go live, whether the tag-category-per-document-type
grouping is enforced or just a UI convenience, what "QSX2" refers to,
whether facility-owner tag data is backed by a real system of record, what
happens when a tag has no value for a given tenant, and (added 2026-08-08)
whether the template system supports conditional logic on boolean-valued
tags. Keep that note as the single copy of the actual question text —
update it there, not here, if any question changes.

## Confirmed mismatches (real errors found in real documents — worth acting on, not just noting)

**A broken tag already exists in the "Standard Templates" library.**
`! Standard Templates\DOCUMENTS\Courtesy Notice.docx` (the canonical/default
version, not a one-off client copy) contains `{f.add2}}` — missing its
opening brace — in the sign-off block (return address, second line). QMS's
merge engine almost certainly can't resolve this and would print it
literally in every generated courtesy-reminder letter that uses this
template or a copy of it. **This is a live production bug, not a
hypothetical design case** — worth telling whoever maintains this template
library directly, independent of anything Orchestrator builds. Found
2026-08-07, not yet reported to QMS/template owner as of this writing.

## Related

- [[QMS Template Tags — Catalog & Editor Design]] — where resolved answers
  and the stable catalog live
- [[QMS Template Tags — New Families & Label Glossary]] — the six tag
  families and label clarifications several items above draw on
- [[QMS API Index]], [[QMS API - Domain Model & PII]] — the API-side
  counterpart these questions get checked against
- [[2026-08-14-filled-document-field-detection-shipped|Filled-document field detection]] —
  the code-side scope lock that surfaced the `m.*`/`l.*`/`d.*` research item
  above
