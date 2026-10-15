---
date: 2026-10-14
description: "Standing rule: every real document that exposes behavior is captured as a fixture plus an exhaustive vault record, with expected output. Written for Claude, to give total recall from day one."
tags:
  - brain
  - rule
  - testing
status: active
---

# Real Documents Are the Spec

**Rule, set by Boris on 2026-10-14, applies to every future addition to this vault and to the UnitPrep repos:**

> Every real document (or file, export, payload, screenshot) that teaches us how a tool behaves is captured twice: as a **fixture with its expected output** in the repo's test corpus, and as an **exhaustive record** in this vault. Nothing is summarized away to save space. Nothing is recorded only as prose about a session.

Boris's words, so they are not paraphrased away: *"capture whatever you would work best with. prose, poetry, tech heavy docs? I don't care as long as you have exhaustive information and total recall from day 1 of the vault. no need to save on space there. everything must be recorded. real document for everything."*

## Why this exists

On 2026-10-14 the Template Tagger passed every unit test (1,046 UI, ~970 backend) while returning 2 wrong hits on a real lease (Longview Self Storage / T.C.'s RV). Tests written from imagined documents encode the author's assumptions. What found the gaps was running the actual file and reading its XML. The platform got better that day, but only in session prose; nothing made it *provably* better, and nothing would stop the next change from quietly undoing it. A corpus of real documents with expected output does both. See [[Test Audit 2026-10-14]].

## What "real document for everything" means in practice

- A bug found on a real file: the file becomes a fixture **before** the fix, fails, then passes.
- A new vendor format (dedup exports, SiteLink pulls, QuikStor Cloud, Syrasoft, Easy Storage Solutions): a real sample (redacted) becomes a fixture with the expected recognition result.
- A new template (leases, notices, emails): the real template plus the expected tag set.
- An API response that surprised us (ClickUp, Process Street, Dropbox, QMS): the real payload, redacted, recorded as a fixture a mock server can replay.
- A screen that was wrong in the browser: the real data that produced it and the expected render.

## The two halves

### 1. Fixture in the repo (machine-checkable)

Lives next to the code that consumes it, under a `corpus/` directory (Rust: `<crate>/tests/corpus/<kind>/<name>/`). Each case is a folder:

- `input.*` — the document. **Redacted if it holds personal data** (see PII boundary).
- `expected.json` — the expected output, exact enough to fail on regression: for the tagger, every candidate as `{tag_key, tier, region, context}` plus the list of tags that must appear in the applied output and which text must stay byte-identical.
- `patterns.json` (tagger) or the equivalent configuration the case depends on, so the test does not need a database.
- `README.md` — one screen: where the file came from, what is unusual about it, what is deliberately *not* tagged and why.

A test walks the corpus and runs every case. Adding a case is adding a folder, never editing a test.

### 2. Record in the vault (exhaustive, for total recall)

One note per real document, created from [[Real Document Record]] (template) under the project's `work/active/` cluster. It is written **for Claude**, so it favors exactness over narrative. It always contains:

1. **Provenance**: original path (Dropbox / email / URL), date obtained, who sent it, SHA-256, size, what system produced it, whether the repo fixture is the original or a redacted copy and what was redacted.
2. **Structure facts**, measured not remembered: file format internals that matter (for a .docx: counts of text boxes, tables, underlined tabs, underscore runs, groups, Fallback copies, section/page geometry; for a CSV: header row verbatim, delimiter, encoding, row count, sample rows).
3. **Field-by-field table**: every field or column in the document, with its location, what it means, the tag or mapping chosen, the tier, and **why**. Include the fields deliberately left alone.
4. **Decisions and who made them**, in Boris's words where he gave them, with the reasoning and the alternatives rejected.
5. **Expected output**, or a pointer to `expected.json`, plus the exact command that reproduces it.
6. **Open questions and known gaps**, each with the concrete thing that would resolve it.
7. **Raw excerpts**: the smallest XML/CSV/JSON fragments that explain a surprising behavior, verbatim. Excerpts are cheap; reconstructing them is not.
8. **Links**: the commit(s) and version(s) that handled it, the work note for the session, and the fixture path.

Long is fine. Tables, code blocks, raw excerpts and hashes are all welcome. The only wrong format is a short summary that a future session cannot act on without re-deriving.

## PII boundary (the one limit on "record everything")

Real tenant and customer data must not land in a git repository or an artifact.

- **Blank forms and templates** (no personal data): commit as-is.
- **Filled documents and exports** (tenant names, addresses, phone numbers, emails, DOBs, license numbers, account or card data): the repo fixture is a **redacted copy** with values replaced by realistic fakes that keep the same shape (length, character classes, formatting). The vault record states exactly what was redacted. The original stays in Dropbox; its path and SHA-256 go in the record so it can be re-fetched.
- **Credentials, tokens, keys**: never recorded anywhere, redacted or not.
- The vault is private to Boris, so exhaustive description of a document's *structure* is always fine; the restriction is on committing raw personal data to the repos.

## Backfill

The rule starts today and is retroactive where it is cheap. The first record is [[Real Document Record - Longview Self Storage Rental Agreement]]. Existing vendor-format work (Davidson Road QuikStor Cloud, Syrasoft, Westpark/Rowley cross-checks, Easy Storage Solutions) should be converted to records and fixtures the next time each is touched; the audit lists them.

## Related

- [[Test Audit 2026-10-14]] — the audit that motivated this and the plan to build the corpus
- [[Real Document Record]] — template
- [[Dev Principles]], [[Collaboration Style]], [[Gotchas]]
