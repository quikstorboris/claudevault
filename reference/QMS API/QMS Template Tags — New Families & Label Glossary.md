---
date: 2026-08-08
description: "Six tag families QMS's own tag picker exposes that weren't in Boris's original hand-copied tags.txt list (Transfer, Move-Out, Manual Payment, Reservation, Login Link, Move-In Link), plus authoritative plain-English labels for tags that were previously just abbreviations, and a few resolved/clarified ambiguities."
tags: [reference, unitprep, qms-api]
project: unitprep
---

# QMS Template Tags — New Families & Label Glossary

Boris pasted a large, messy multi-template dump 2026-08-08 — tag pickers
copied from several different QMS template contexts, with real body text
from a few live templates mixed in. **`tags.txt` (the original source) is
Boris's own hand-typed transcription of what he saw on QMS's UI page — not
a system export of any kind**, and QMS has no built-in export feature for
this list as far as we know. That's exactly why it undercounted the
system: **six entire tag families never appeared in it at all**, not
because QMS hides them, but because a manual, one-pass copy job missed
them. This note captures what's new; [[QMS Template Tags — Catalog &
Editor Design]]'s "221 tags / 14 contexts" framing is now known to be a
floor, not the whole picture — treat that count as stale until a fuller
re-copy happens.

**Where these actually live is unconfirmed** — see [[QMS Template Tags —
Catalog & Editor Design]]'s "real UI structure" section: QMS's Tag List
page has five top-level categories (Lease, Delinquency, Trigger, Manual,
Mass Document Tags), each containing multiple sub-contexts, and it's not
yet confirmed which category each family below sits under.

## Update 2026-08-08 (second batch): tooltips exist, and context-exclusivity confirmed with real names

Boris found that **hovering a tag in QMS's Tag List page shows a tooltip
with its plain-English description** — the same labels captured in the
first batch above, but confirmed to be sourced from the live UI itself
(not just a separately-pasted table), and raising a real capture-automation
question (see [[QMS Template Tags — Open Questions & Mismatches]]).

He also confirmed, with two named real examples, the exact design
assumption already baked into this note set — **tags overlap across
sub-contexts, but each sub-context also has tags exclusive to it**:

- **"Auto Pay Success"** (a sub-context, category unconfirmed — plausibly
  under Trigger Tags, given the name reads as a system-triggered
  notification) has its own exclusive **Auto Payment Tags** category
  containing `{{ap.trledg}}` = "Auto Payment Transaction Ledger." This is a
  **new top-level prefix, `ap.*`**, distinct from `l.apmeth`/`l.apadd1`/etc.
  (which are autopay-*method* fields nested under the Lease family) — `ap.*`
  is its own family, parallel to `mp.*` (Manual Payment). Only one `ap.*`
  tag confirmed so far; unknown whether an `{{ap.total}}` counterpart to
  `{{mp.total}}` exists.
- **"Move-Out Completion"** (full, precise name — more specific than the
  plain "Move-Out" label used earlier in this note) confirmed with its
  exclusive **Move-Out Tags** category (`mo.*`) sitting alongside the
  standard Company/Date-Time/Tenant/Facility/Lease/Unit categories, exactly
  as expected.

**Three more real Unit tags confirmed**, none previously verified:
`{{u.webrate}}` ("web rate" — matches `Unit.webRate` in [[QMS API - Domain
Model & PII]] exactly, not seen in any tag list before this), and
`{{u.mnt}}` / `{{u.smlock}}` (previously only inferred from
`UnitAttributes.monitoringEnabled`/`smartLockEnabled` in the API schema,
now confirmed as real, selectable tags in the picker).

## Six new tag families

**`ll.*` — Login Link** (its own one-tag context): `{{ll.link}}` = "Login
Link." Presumably used in an email/SMS inviting someone to log into the
tenant portal.

**`mil.*` — Move-In Link** (its own one-tag context): `{{mil.link}}` =
"Move-In Link." Distinct from the `m.*` Move-In Tags family entirely — this
is a single link, likely to a move-in flow/portal, not lease field data.

**`r.*` — Reservation**: `r.startdate` = "Reservation Start Date",
`r.enddate` = "Reservation End Date", `r.leadsrc` = "Reservation Lead
Source." Small family, matches the Reservations area of the QMS API (see
[[QMS API - Endpoint Catalog]]).

**`mp.*` — Manual Payment**: `mp.trledg` = "Manual Payment Transaction
Ledger", `mp.total` = "Manual Payment Total." Confirmed in real use — see
Evidence section below.

**`mo.*` — Move-Out**: mirrors several `m.*` (Move-In) fields for the
move-out event instead: `mo.trledg` ("Transaction Ledger" — not present on
`m.*` at all), `mo.indate`, `mo.outdate`, `mo.leadsrc`, `mo.estval`,
`mo.descgood`, `mo.ins`, `mo.insprice`, `mo.secdep`. Notably missing
relative to `m.*`: no `mo.promo.name`, no `mo.opi.*`/`mo.vi.*`, no
`mo.maxrp`/`maxra`/`maxrdate` — a move-out document apparently doesn't need
promotion, lienholder/vehicle, or rent-cap fields.

**`t.*` — Transfer** (a tenant moving from one unit/lease to another — this
is the document family for `ELeaseType: Transfer`, the enum value already
seen in [[QMS API - Domain Model & PII]] but not previously connected to a
template family): by far the largest new family, ~112 tags.
- `t.date` = "Transfer Date", `t.table` = "Transfer Table"
- `t.nl.*` ("New Lease") mirrors a *subset* of `l.*`: `ptd`, `effrate`,
  `ins`, `insprice`, `secdep`, `nxtdate`, `nxtamt`, `baldue`, `leadsrc`,
  `estval`, `descgood`, `opi.*`, `vi.*`. Missing relative to full `l.*`:
  `indate`/`outdate`, all `ap*` autopay fields, `lpmamt`/`lpmdate`,
  `rectrans`/`unpaidtable`, `excldel`, `maxrp`/`maxra`/`maxrdate` — makes
  sense, a lease that's only just been created by the transfer has no
  payment history, no delinquency status, and no rent-cap yet.
- `t.ol.*` ("Old Lease") mirrors the exact same field subset as `t.nl.*`.
- `t.ufrom.*` / `t.uto.*` ("Unit From" / "Unit To") each mirror the full
  `u.*` family (number, standard rate, type, dimensions, every
  `UnitAttributes` field) — the unit being vacated and the unit being moved
  into.

## Boolean/presence-flag tags — a new question, not just a new fact

Three tags resolve to true/false, not a display value:
- `{{e.alt}}` = "Is Alternate Contact Present"
- `{{e.mil}}` = "Is Military Profile Present"
- `{{l.excldel}}` = "Is Excluded From Delinquency"

**This raises a genuinely new question, added to [[QMS Tag System —
Questions for QuikStor]]: does the template system support any conditional
logic (show this block only if a boolean tag is true), or are these three
tags meant to be displayed as literal "Yes"/"No" text?** If conditional
blocks exist, that changes the answer to an earlier open question — a field
with "no matching tag" (like Stowaway's Admin Fee) might still be
expressible today via a conditional block plus manual text, rather than
being a flat "not possible" case. Not assumed either way; needs confirming.

## Signature representation — clarified, not fully resolved

A real template snippet Boris shared uses `{{esign}}` for the first time in
a way that clarifies its role: *"Open and sign the document here:
{{esign}}"* — inside what reads as an email or SMS notification, not inside
the lease document itself. This lines up with `tags.txt`'s own grouping:
`{{esign}}` lives under the "Signature Request" category, specifically for
the **Manual Email Signature Request** / **Manual Sms Signature Request**
contexts — i.e. a *notification telling someone to go sign*, not the
signature block inside the document being signed.

That leaves the picture as three distinct things, not one ambiguous one:
- `/s/{{e.name}}` (literal typed-name text) — used **inside** the lease
  document itself, at the actual signature line (Stowaway, Rest Stop,
  Sumas all do this).
- `{{sig}}` — shown in QMS's own generic Default Lease document as an
  "Electronic Signature Sample," inside the document.
- `{{esign}}` — used in a **separate notification message** (email/SMS)
  that links out to the signing flow, not inside the document being signed.

Still open, now more precisely stated: **is `/s/{{tag}}` or `{{sig}}` the
one QMS's e-signature integration actually recognizes inside a document
body?** Both are real, in different documents, and we still don't know
which (if either, or both) functions correctly. Question already logged in
[[QMS Tag System — Questions for QuikStor]] — not restated here, just
sharpened.

## New real-usage evidence

- **`{{mp.total}}` / `{{mp.trledg}}` confirmed in a real payment-receipt
  email**: *"Thank you for your payment of {{mp.total}} on {{d.now}} at
  {{f.name}}. Below is a transcript of the payment. {{mp.trledg}}"*
- **`{{l.rectrans}}` confirmed in real use**, labeled inline by whoever
  wrote the template: *"These are the recurring transactions: (Monthly
  Rent) {{l.rectrans}}"* — confirms it embeds a dynamic list/table, the
  same shape as `{{l.unpaidtable}}`.
- **A payment-confirmation SMS-style message** uses only already-known
  tags correctly together: `{{u.num}}`, `{{f.name}}`, `{{l.lpmamt}}` — no
  new information, but a fourth real document independently reusing the
  same tags consistently.

## A few label clarifications worth calling out

QMS's own tag picker gives every tag a plain-English label — most just
confirm what was already inferred from context, but a few resolve real
prior ambiguity:
- `{{l.baldue}}` is labeled **"Balance Value,"** not "balance due" as
  assumed by name alone — same concept, just noting the exact vendor
  wording in case it matters for anyone searching their own docs for it.
- `{{l.apmeth}}`/`{{l.apadd1}}`/`{{l.appost}}`/`{{l.aplast4}}`/`{{l.apexp}}`
  — the `ap` prefix is **"Autopayment"**: method, billing address, billing
  postal code, card's last four digits, card expiration. Not something the
  abbreviations alone made obvious.
- `{{l.maxrp}}` / `{{l.maxra}}` / `{{l.maxrdate}}` = **Max Rent Increase**
  Percentage / Amount / Valid Date — a rent-increase cap, not something
  guessable from the abbreviation alone.
- `{{m.ptd}}` is fully labeled **"Paid Through Date"** while `{{l.ptd}}` is
  only labeled **"Ptd"** — the same underlying concept, labeled more fully
  on the move-in side. Consistent with the already-documented `m.*`/`l.*`
  duality (the same lease, described at two different points in its life),
  not a new inconsistency.

## QMS's own labels contain real typos — don't mistake these for OM error

Found directly in the vendor's own tag-picker text, appearing identically
across every copy pasted: **"Vehicke Information"** (should be "Vehicle,"
appears dozens of times, always spelled the same wrong way — baked into the
system, not a one-off typo), **"Lightning"** for the unit attribute that
means **"Lighting"** (`{{u.light}}`), and **"Resert Password Link"** for
`{{rp.link}}`. Worth remembering generally: an odd label or spelling found
while reviewing a template is not automatically evidence of human tagging
error — check whether QMS's own system already says it that way before
concluding someone made a mistake.

## Related

- [[QMS Template Tags — Catalog & Editor Design]] — the stable catalog this
  note extends; its tag/context counts are now known-incomplete
- [[QMS Template Tags — Evidence from Real Documents]] — prior real-document
  findings this note adds to
- [[QMS Tag System — Questions for QuikStor]] — updated with the new
  conditional-logic question this note raised
- [[QMS API - Domain Model & PII]] — `ELeaseType: Transfer` connects
  directly to the new `t.*` family found here
