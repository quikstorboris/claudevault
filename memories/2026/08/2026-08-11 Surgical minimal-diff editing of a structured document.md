---
date: 2026-08-11
description: "When you need to change a small, known part of a structured document format (docx/xlsx/pptx-style zip-of-XML, or any other format with a \"container…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-11T17:44:36.892Z"
scope: general
projects: []
confidence: verified
---

# Surgical minimal-diff editing of a structured document format: never deserialize the whole thing, splice into the original bytes, and never slice raw text mid-entity

When you need to change a small, known part of a structured document format (docx/xlsx/pptx-style zip-of-XML, or any other format with a "container of typed parts" shape) without disturbing anything else in the file, the obvious approach -- parse the whole document into an object model, mutate it, serialize it back out -- carries real, hard-to-detect fidelity risk. Any detail the model doesn't fully capture (an obscure run property, a content control, a comment anchor, an unusual namespace) can be silently dropped or altered on the round trip, even in parts of the document nobody meant to touch. This is the standard approach taken by most general-purpose "edit this document" libraries, and it is the wrong tool for a narrow "change exactly this span, touch nothing else" job.

The safer alternative: never deserialize the whole document into a model that claims to represent it. Instead, (1) walk the raw XML with a streaming parser just far enough to flatten the plain text into one string, while recording -- for each addressable unit of text (a run, a cell, whatever the format's smallest text-bearing element is) -- the exact byte range in the *original, untouched* raw XML where that unit's content lives; (2) let the caller decide what to change against that flat text; (3) splice each change directly into the original raw bytes at exactly that recorded range, copying every other byte through completely unchanged. Every byte outside a targeted unit is untouched by construction, not by care -- there is nothing else in the file the edit code is even capable of altering.

The one correctness trap this approach must handle deliberately: a text unit's *encoded* form (an XML entity like `&amp;`) and its *decoded* form (`&`) have different byte lengths. Never slice the raw encoded bytes at a byte-offset computed against decoded text -- if the unit contains an entity, the offsets no longer agree and the slice lands mid-entity, corrupting the file the moment that unit contains one. Fix: always replace a touched unit's *entire* raw content wholesale, via a decode -> splice-in-decoded-space -> re-encode round trip, even when the edit only touches part of that unit's text. This makes entity corruption structurally impossible rather than merely avoided by careful offset math.

A second, related discipline: refuse (don't guess at) an edit whose target span crosses two separate text units, rather than trying to splice across an element boundary -- that's a materially harder, riskier problem with a much smaller payoff than the single-unit case, and guessing wrong there is exactly the kind of silent corruption this whole approach exists to prevent.

This generalizes beyond one project or one file format: any time the actual need is "change this one exact thing, prove nothing else moved" rather than "understand and faithfully re-author this whole document," reach for surgical byte-range splicing over full deserialize-mutate-reserialize, and design the very first integration test to prove the byte-identical-elsewhere claim against a real file from the format, not a synthetic one -- that's the test that actually earns trust in the approach.

## How this is known

Built as docx-surgeon (Rust, in unitprep-api), verified two ways: (1) an integration test diffing every zip entry and every byte of document.xml outside the one edited run's text content between an original and an edited real sample .docx, confirming byte-for-byte identity everywhere except the intended change; (2) opening the edited output in real Microsoft Word via COM automation and confirming it opens cleanly with no repair/corruption prompt and the substitution renders correctly.
