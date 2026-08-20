---
date: 2026-08-07
description: "QMS's own merge-field/placeholder-tag catalog (221 tags across 14 document contexts), pulled from the QMS UI, not the API. Revives the template-editor idea the API itself can't back, plus a DB-vs-hardcode design recommendation."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS Template Tags — Catalog & Editor Design

[[QMS API Index]] found that the QMS **API** exposes no template/placeholder
content at all. This is the other half of that story: QMS's own **template
editor UI** clearly has a full merge-tag system — Boris read the tag list
directly off that UI page and typed/copy-pasted it into a text file by
hand, one tag at a time. **This is not a QMS export feature of any kind** —
there is no built-in export for this list as far as we know; the source
file is purely a manual transcription, which is exactly why it turned out
to be incomplete (see below) rather than a sign QMS's own data is
incomplete. The tags themselves are real, stable, and used by QMS's own
templates — enough to build an Orchestrator-side template editor against
**without** needing API support for it. Source file: ![[QMS Template Tags
(as of 2026-08-07).txt]] (verbatim copy of Boris's hand-typed list).

## Known-incomplete: this catalog undercounts the real system

**Update 2026-08-08**: a second, larger batch of real tag pickers, again
copied by hand from QMS's UI, turned up six entire tag families never
captured in the original `tags.txt` file — Transfer, Move-Out, Manual
Payment, Reservation, Login Link, Move-In Link. This is a direct
consequence of the source being a manual transcription rather than a
system export (see above) — nobody missed anything QMS documented, the
first pass just didn't happen to copy everything visible in the UI. See
[[QMS Template Tags — New Families & Label Glossary]] for all of them, plus
authoritative plain-English labels for tags that were previously just
abbreviations. Treat "221 tags / 14 contexts" below as a documented floor
from that first pass, not the actual total — don't cite it as complete.

## The real UI structure: a two-level hierarchy, confirmed by screenshot

Corrected 2026-08-08 — Boris shared a screenshot of the actual page this
was all copied from, and it changes the mental model. This lives in QMS at
**Templates → Tag List**, a real, dedicated reference page (not the
template editor itself) with a copy-to-clipboard icon on every tag — QMS's
own version of exactly the "tag palette" tool sketched in this note's
Phase 1. There are exactly **five top-level template categories**, each its
own page:

- Lease Tags — `/template-tags/lease`
- Delinquency Tags — `/template-tags/delinquency`
- Trigger Tags — `/template-tags/trigger`
- Manual Tags — `/template-tags/manual`
- Mass Document Tags — `/template-tags/mass-document`

**Each category page contains one or more collapsible document-type
sub-sections** — the screenshot shows the Lease Tags page with "Move-In
Document Signing" (collapsed) and "Coverage Plan Sold" (expanded) both
sitting under it. This means the "contexts" table below (Move-In Document
Signing, Coverage Plan Sold, Send To Print Center, etc.) was never a flat
list of 14 peers — they're **sub-contexts nested inside the five
categories above**, and `tags.txt`'s own top-level headers ("Lease Tags,"
"Delinquency Tags," "Manual Tags," "Mass Document Tags" — one per copy-paste
pass Boris did, page by page) were the category boundaries all along, not
just more tag-category labels like "Company Tags" or "Tenant Tags." Worth
re-reading `tags.txt` with this in mind if anything below seems oddly
grouped.

**Resolved 2026-08-08**: `/template-tags/trigger` was visited directly (via
Claude in Chrome, connected to Boris's real logged-in QMS session). It
contains exactly three sub-contexts — Company User Send Registration
Email, Company User Reset Password, Schedule Reports — matching content
already known from `tags.txt`, just now correctly attributed to this
category rather than guessed as sitting under Delinquency Tags. The
"Corporate / Facility" scope value logged elsewhere does **not** appear to
belong to Trigger Tags after all — still unaccounted for. Detail in [[QMS
Template Tags — Open Questions & Mismatches]].

**Also unconfirmed**: which of the five categories the six new families in
[[QMS Template Tags — New Families & Label Glossary]] (Transfer, Move-Out,
Manual Payment, Reservation, Login Link, Move-In Link) actually live under.
Reasonable guesses — Transfer/Move-Out under Lease Tags, Manual Payment
under Manual Tags — but guesses, not confirmed.

## Shape: 221 tags across 14 sub-contexts (not 14 top-level categories — see above)

Each **sub-context** is a distinct QMS document/notification type, and each
one exposes only a subset of tag **categories** — not every tag is valid
everywhere. This context-scoping is the one thing a flat tag list would lose,
and it's the main reason a real editor needs more structure than "here are
221 strings."

| Context | Tag categories available |
|---|---|
| Move-In Document Signing | Company, Date/Time, Tenant, Facility, Move-In, Unit, Signature |
| Coverage Plan Sold | Company, Date/Time, Tenant, Facility, Move-In, Unit, Signature |
| Send To Print Center | Company, Date/Time, Delinquency, Tenant, Facility, **Lease**, Unit |
| Send Email | Company, Date/Time, Delinquency, Tenant, Facility, Lease, Unit, + a Trigger scope value (Corporate / Facility — not a merge tag, a setting) |
| Send SMS | Company, Date/Time, Tenant, Facility, Lease, Unit *(no Delinquency)* |
| Recurring Apply Fee Notice | Company, Date/Time, Delinquency, Tenant, Facility, Lease, Unit |
| Company User Send Registration Email | Company, User (`cu.*`), Send Registration link |
| Company User Reset Password | Company, User (`cu.*`), Reset Password link |
| Schedule Reports | Company, Date/Time, Schedule Reports links |
| Manual Email Send | Company, Date/Time, Tenant, Facility, Lease, Unit |
| Manual SMS Send | Company, Date/Time, Tenant, Facility, Lease, Unit |
| Manual Email Signature Request | Manual Email Send's set + Signature Request |
| Manual Sms Signature Request | Manual SMS Send's set + Signature Request |
| Mass Document Send | Company, Date/Time, Tenant, Facility — **no Lease or Unit tags** |

**Confirmed 2026-08-08, directly against the QMS UI**: Mass Document Send
genuinely has fewer tag categories than the visually similar Manual Email
Send / Send Email contexts — this isn't a copy-paste artifact of Boris's
hand-typed source file (the file itself just happens to end exactly where
this context's list ends, which made it look like the transcription had
been cut short; it hadn't). Boris confirmed by reading the live tag picker
directly. Plausible reason, **inferred, not
confirmed**: a mass send can target many tenants across many units/leases
at once, so there's no single lease or unit to bind a `{{l.*}}`/`{{u.*}}`
tag to — worth asking QMS directly if the reasoning ever matters, but not
blocking anything today.

## Tag family legend (prefix → source)

| Prefix | Family | Maps to (see [[QMS API - Domain Model & PII]]) |
|---|---|---|
| `c.*` | Company | `Company` object |
| `f.*`, `f.ow.*` | Facility, Facility owner | `Facility` object (`f.ow.*` isn't in the API schema — facility "owner" contact appears to be QMS-UI-only data) |
| `e.*` | Tenant (EndUser) | `EndUser` basic fields |
| `e.a.*` | Tenant's alternate contact | `EndUser.alternateContacts[]` |
| `e.m.*` | Tenant's military profile | `EndUser.militaryProfile` — **`e.m.l4ssn` = the same `lastFourSsnDigits` field** flagged in the PII correction to [[Compliance & Process Readiness]] |
| `e.m.a.*` | Military profile's agent | `militaryProfile.agent*` fields |
| `u.*` | Unit | `Unit` + `UnitAttributes` |
| `l.*` | Lease (post-move-in context: delinquency notices, statements, etc.) | `Lease` object |
| `m.*` | Move-in (move-in-time context: the signing document itself) | Overlaps `Lease`/`AdditionalInformationGatewayResponse`/`VehicleInformationGatewayResponse` fields, but under a **different prefix** than the same concept has once it's on an existing lease (`m.secdep`/`m.effrate`/`m.indate`/`m.excldel` at move-in vs. `l.secdep`/`l.effrate`/`l.indate`/`l.excldel` afterward) |
| `d.*` | **Overloaded** — Date/Time (`d.now`, `d.nowlong`) in most contexts, but **Delinquency** (`d.trledg`, `d.earliest.auction.closing.date`) in delinquency-adjacent contexts | Context-dependent — a tag catalog must key on `(context, tag)`, not `tag` alone, or `d.*` collides |
| `cu.*` | Company user (staff account) | Not in the API at all — matches [[QMS API - Tool Opportunities]]'s finding that Users/staff accounts have zero API surface |
| `sr.*`, `rp.*`, `reportlist.*` | Registration link, reset-password link, scheduled-report links | Action-specific, single-tag categories |
| `sig`, `esign` | Signature placeholder | — |

**The `m.*`/`l.*` duality is the one real design trap**: several concepts
(security deposit, effective rate, move-in date, excluded delinquency)
exist under **two different tag names** depending on which document context
they're used in. A tag catalog keyed only by semantic meaning ("security
deposit") would need to know which prefix applies per context — this isn't
optional cleanup, it's how QMS's own system actually works.

**Independent confirmation of the PII correction**: `e.m.l4ssn`,
`e.dlnum`/`e.dlstate`/`e.dlexp` (driver's license), and the full `e.a.*`/
`e.m.a.*` third-party contact fields all show up here too, from a completely
different source (QMS's own document-editor UI) than the API schema that
first surfaced them. Two independent sources agreeing is worth noting — this
isn't a schema quirk, it's really how much PII QMS's tenant record carries.

## Evidence from real documents

Split out 2026-08-08 once it grew past a single note's worth — see
[[QMS Template Tags — Evidence from Real Documents]] for: three full
before/after client pairs read in detail (Stowaway Storage, Rest Stop
Storage, Sumas Mini Storage), several of QMS's own canonical `! Standard
Templates`, a newly-discovered tag-syntax feature (`{{tag±N}}` date-offset
arithmetic — not in `tags.txt` at all, only found by reading real
documents), and every confirmed pattern or open mismatch those documents
turned up. Read that note before assuming a design point here is untested —
most of what follows was shaped directly by it.

## Editor design question: hardcode vs. DB-stored

Boris's own framing: leaning DB-stored with add/edit capability, in case QMS
changes the catalog. **Agreed — DB-stored is the right call**, for reasons
beyond "just in case":

1. **The context-scoping and the `d.*` collision both need real structure**
   a hardcoded list can't cheaply express — a `(context, tag_key)` composite
   key falls out naturally from a normalized schema, and awkwardly from a
   flat constant.
2. **QMS-side additions are the likely failure mode, not wholesale changes.**
   A new document context or a handful of new tags (e.g. if QMS adds a new
   notification type) is far more probable than the whole taxonomy being
   restructured — and "add a row" beats "ship a code change" for that.
3. **Never hard-delete a tag that goes stale.** If Orchestrator-authored
   templates already reference a tag QMS later removes, the tag needs to
   stay resolvable (or at least visible as "deprecated") rather than vanish
   out from under existing templates — the same soft-delete-not-hard-delete
   instinct already used for `auth.users` in this codebase applies here.

**Suggested shape** (not built, just sketched):

```
qms_template_context (id, name, created_at)
qms_merge_tag (id, tag_key, category, label, description, is_active, source_verified_at)
qms_template_context_tag (context_id, tag_id)  -- many-to-many
```

- `is_active` (not a hard delete) handles QMS removing a tag later.
- `source_verified_at` gives a per-tag staleness marker — worth it given the
  catalog is hand-copied from QMS's UI today, not fed by an API (there is no
  API to feed it from — see [[QMS API Index]]). Re-verifying periodically
  (or when a client's document renders wrong) is the only staleness check
  available; there's no live source to diff against automatically.
- Admin-only add/edit UI, per Boris's own framing — this is exactly the
  "cheap to keep current" mechanism the DB-backed choice buys, versus a
  hardcoded list needing a code deploy for every QMS-side change.

## What the tool actually is, clarified 2026-08-07

Resolves the "composer vs. independent document management" question this
note originally left open — the confusion was on my (Claude's) side, not a
real fork in the design. Boris's explanation, grounded against a real
example (see below): **QMS is always the system that generates the actual
document.** A "template" is a client's own legal document (their lease
form, their move-in packet) with the tenant/unit/date/etc. wording replaced
by QMS tags, uploaded into QMS, which then auto-populates and generates the
real document per tenant. There is no scenario where Orchestrator generates
or manages documents independently — that was never on the table. The only
question was ever how much of the *tagging* work (replacing literal wording
with the matching tag) the tool does for the OM, which is now well-defined:

**The tool's job: given a client's raw legal document, find the spots that
should become QMS tags, and produce a real `.docx` with those tags placed —
not just a review screen.** Corrected 2026-08-07: the deliverable is an
actual Word document, tags inserted in place of the literal wording, ready
for the OM to review and then upload into QMS's own template system (still
the only path — the API has no template-write endpoint). Anything the tool
notices but can't or shouldn't fix on its own (a typo, a broken tag, an
encoding artifact — see the confirmed-mismatch example below) gets
**highlighted directly in that same output document** — Word's own
highlight/comment mechanism, not a silent fix and not a separate report the
OM has to cross-reference against the document. The OM reviews the one
file, sees the tags in place and the flags inline, and decides what to do
with each.

## Hard rule: these are legal documents — propose, never modify

Boris, 2026-08-07: **replacing literal tenant/unit/date wording with the
matching QMS tag does not change the document's material legal content**
(that's the whole point — the tag resolves to the same value QMS would have
put there anyway), **so that substitution is safe for the tool to do.**
**Everything else is not the tool's call to make.** Even something as
small as a typo or the mangled-apostrophe encoding issue found above must be
**flagged, never auto-corrected** — the fix goes back to the client to make
themselves, since it's their legal document and their call, not an
implementation detail Orchestrator gets to decide silently on their behalf.

Concretely, this means every candidate spot in the output document ends up
in exactly one of three states, never a silent edit:
1. **Substituted** — literal text replaced with the matching tag, directly
   in the output `.docx`.
2. **Highlighted, not corrected** — something looks off (a typo, a broken
   tag, an encoding artifact) but the tool doesn't touch it — marked
   in-document (highlight color and/or a Word comment explaining what was
   noticed) so the OM sees it in context and can decide whether to send it
   back to the client.
3. **Left alone** — no match, no issue; nothing happens to that text.

**A real example of exactly what category 2 is for**: QMS's own canonical
`Courtesy Notice.docx` template contains a literally broken tag QMS's merge
engine can't resolve — see [[QMS Template Tags — Evidence from Real
Documents]] for the detail, and [[QMS Template Tags — Open Questions &
Mismatches]] for tracking it. Worth reporting to whoever maintains that
template library independent of anything Orchestrator builds, since it's a
live production issue today, not a hypothetical.

## Phased build plan (not scoped for effort/timeline, just sequenced by what each phase needs)

1. **Tag reference/composer** — browse, search, and copy tags from the
   DB-stored catalog above, scoped to the document context being worked on.
   No document parsing at all yet; pure lookup tool. Buildable now.
2. **Rule-based candidate detection for the easy cases** — given a document
   and (separately supplied) real values for a sample tenant/unit/lease, find
   literal string matches (a name, an address, a phone number, a unit
   number) and propose the matching tag. Straightforward pattern matching,
   no AI needed. The Stowaway example's easy fields (name, address, phone,
   email, DL#, unit number/size, access code) are exactly this tier.
3. **Judgement-requiring cases** — the `m.*`/`l.*`/`d.now`/blank
   disambiguation, and recognizing "no tag exists for this, even though it
   looks matchable" (Admin Fee, Alternate Mailing Information). This is
   where the dormant AI integration point becomes a real candidate — see
   below — but isn't required to ship phase 2 first.

**On the "unused AI crate" Boris mentioned**: verified directly in
`unitprep-api` — `src/ai/interface.rs` is a genuine stub (`AiDecisionContext`
struct, a `describe_ai_ready_contract()` function returning a placeholder
string, both `#[allow(dead_code)]`), declared as a module in `main.rs` but
called from **zero** other places in the codebase. It's an intentional
placeholder marking future intent, not a partially-built integration —
accurate to describe it as "not started" rather than "in progress."

## Where the tool's output lives (storage, resolved 2026-08-07)

Boris: storing OM-produced output (formatted templates, dedup/unit-group
CSVs) in the DB is appealing but shouldn't wait on a real storage solution
(S3 or similar) to exist first. **For now: write output back to the same
locally-synced Dropbox folder the client's source documents already live
in** — e.g. this very template would be written back into
`Stowaway Storage - Kingsburg California\`, alongside the original. No new
infrastructure needed: this is the same "user-initiated folder access, no
Dropbox API integration required" mechanism [[Platform Vision (Onboarding
Orchestrator)]] already established for *reading* client folders — writing
a finished file back into a folder the user already granted access to is the
same capability, not a new one. S3/DB-backed storage is deferred, consistent
with Grok's already-rejected "Postgres blob as a v1 stopgap" — go straight
to real object storage **later, if and when a concrete need forces it**,
per [[response-to-groks-tenant-piigdpr-implementation-suggestions|that
decision record]]; the Dropbox-folder approach avoids needing either option
today.

## Related

- [[QMS Template Tags — New Families & Label Glossary]] — six tag families
  missing from this note's original catalog, plus authoritative labels
- [[QMS Template Tags — Evidence from Real Documents]] — every real
  document read so far and what it confirmed or complicated
- [[QMS Template Tags — Open Questions & Mismatches]] — the running log for
  new ambiguities and mismatches as more documents get reviewed; don't let
  new findings pile up only in conversation
- [[QMS API Index]] — the placeholder-tag-via-API finding this note answers
  from the other direction (via the UI instead)
- [[QMS API - Domain Model & PII]] — the API-schema fields these tags
  correspond to, and the PII inventory this independently confirms
- [[QMS API - Tool Opportunities]] — where this fits among other QMS-API-
  adjacent feature ideas
- [[Compliance & Process Readiness]] — the PII correction this note
  reinforces from a second, independent source
