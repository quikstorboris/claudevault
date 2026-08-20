---
date: 2026-08-08
description: "Standalone question list for QuikStor/QMS developers about how the document-template tag/variable system actually works. Self-contained — meant to be sent externally as-is."
tags: [reference, unitprep, qms-api]
project: unitprep
---
                           
# QMS Tag System — Questions for QuikStor

We're building tooling around QMS's document-template tag/variable system
(the `{{...}}` placeholders used in lease agreements, notices, and other
generated documents) and have run into some gaps working it out from
examples alone. The questions below would help close those gaps. The first
one could make several of the others unnecessary.

1. **Is there an authoritative, versioned specification for the tag/
   variable system used in QMS document templates** — every tag, its exact
   syntax, and which document types accept it? The list we're working from
   was typed up by hand from the template editor's UI (there doesn't appear
   to be a built-in export for it), and we've since found real syntax it
   doesn't cover (question 2) plus six entire tag groups it left out
   entirely (transfers, move-outs, manual payments, reservations, and two
   link tags) that only turned up by manually collecting more examples. A
   canonical reference would let us check our work against it instead of
   continuing to piece it together example by example.

2. We found real templates using **date-offset arithmetic inside a tag** —
   for example `{{l.ptd+1}}` (a paid-through-date tag, plus one day) and
   `{{d.now+15}}` (today's date tag, plus fifteen days). This wasn't in the
   tag list we were given. Is this officially supported syntax? Which tags
   support an offset? Do negative offsets work (e.g. `{{d.now-5}}`)? Are
   units other than days supported (weeks, months)?

3. **Fees** (admin fees, lock fees, setup fees, security deposits, etc.)
   appear to be configured individually per facility inside QMS rather than
   exposed as tags. Is there any way to reference a facility's configured
   fee schedule dynamically inside a document template — similar to how a
   tag can embed a dynamic table of unpaid charges — or does every fee
   amount have to be typed as plain static text in the template, with no
   tag at all? If a facility later changes a fee amount, does that require
   manually editing every template that mentions it?

4. We've worked out that a tag called `{{esign}}` is meant for a
   notification message (an email or SMS) that links out to a separate
   signing flow, based on real usage like "Open and sign the document here:
   {{esign}}." What we still can't tell is what belongs **inside the actual
   document being signed**: we've seen two different conventions used there
   in real, currently-active templates — literal text like
   `/s/{{TenantFullName}}` (a typed name at the signature line) and a
   dedicated tag called `{{sig}}`. Which of these two actually functions
   correctly with your e-signature process for the in-document signature
   block? Would using the wrong one break the signing flow?

5. We found **two cases where the same real-world concept is represented
   differently across different currently-active templates**, and want to
   know whether there's a documented standard, or whether both are
   legitimate depending on the situation:
   - The name of the facility/owner on the signature line of the agreement:
     in some templates this is a tag that auto-fills the facility's name;
     in other templates it's typed as fixed text that never changes.
   - The date the rental agreement is "entered into" or "executed": in some
     templates this is tagged as the date the tenant's lease/move-in
     officially begins; in other templates it's tagged as the date the
     document itself is generated, which is not necessarily the same day.
     Is a lease agreement ever generated on a different day than its
     official start date? If so, are these actually two different, correct
     concepts rather than an inconsistency?

6. **Does QMS validate a document template for broken or unrecognized tags
   before it goes live** — rejecting it or warning whoever uploads it? We
   found a template already in use with a tag missing one of its two
   opening curly braces (broken syntax), and don't know whether QMS would
   catch that automatically or whether it would simply print literally,
   broken, in every document generated from it.

7. Templates are grouped by document type (lease, late notice, email, SMS,
   etc.), and each type appears to expose only a specific subset of tags as
   valid options — for example, one bulk-send document type genuinely
   offers no lease- or unit-related tags at all, only company/tenant/
   facility ones, which we confirmed directly in your editor. **Is that
   restriction technically enforced** — would a tag from an unlisted
   category actually fail to resolve or get rejected if typed in manually —
   **or is it just a suggested grouping in the editor's UI** with no real
   restriction underneath?

8. In a real template, whoever built it left a note in place of a value
   they couldn't find a tag for, referencing something called **"QSX2"**
   (something like: "no QSX2 tag available for this field"). Is "QSX2" a
   specific system or version name distinct from "QMS," or likely just
   informal shorthand from whoever wrote the note?

9. Some tags exist for a facility's **"owner" contact information** (name,
   email, phone, address, company name) as distinct from the facility's own
   general contact information. Is that owner-contact data backed by a
   real, structured field elsewhere in the system, or is it something only
   ever entered directly when the document template itself is created,
   with no other system of record?

10. When a template contains a tag for something a specific tenant simply
    doesn't have on file — for example, a tag for an "alternate contact"
    when none was ever provided, or a tag tied to a military-service
    profile when the tenant has none — **what happens when the actual
    document is generated?** Does it render as a blank space, does the
    whole line or section get omitted automatically, or something else?

11. Some tags appear to resolve to a true/false value rather than a display
    value — for example, one tag whose label is "Is Alternate Contact
    Present" and another labeled "Is Excluded From Delinquency." **Does the
    template system support any conditional logic** (show a block of text
    only if a given tag is true/false), or are tags like these meant to be
    displayed as literal "Yes"/"No" text in the generated document?

## Related

- [[QMS Template Tags — Open Questions & Mismatches]] — the internal
  tracking log this list was drawn from, with links back to the specific
  documents/evidence behind each question
- [[QMS Template Tags — New Families & Label Glossary]] — the evidence
  behind the sharpened questions 1, 4, 7, and 11 above
