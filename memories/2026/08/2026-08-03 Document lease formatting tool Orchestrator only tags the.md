---
date: 2026-08-03
description: "Correction to an earlier, imprecise framing of this planned tool (next after auth)."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-03T19:33:16.596Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# Document/lease formatting tool: Orchestrator only tags the sample document, never stores or matches PII — QMS is the system of record

Correction to an earlier, imprecise framing of this planned tool (next after auth). The actual data flow, per Boris directly:

1. A client-supplied sample lease document (Word) contains live or generic PII (names, phones, unit numbers, amounts, etc.) mixed in with QMS's own `{{placeholder}}` tag syntax.
2. Orchestrator detects which values in that document correspond to which QMS tags and replaces them with the correct `{{tag}}` in place — a transient, in-flight transformation of the uploaded document.
3. The tagged document is then uploaded TO QMS. All actual matching/hydration (pulling real tenant data into those tags to generate a real notice email) happens inside QMS, not Orchestrator.

So Orchestrator never stores the PII it processes, and never performs the tag-to-real-data matching itself — it only produces a genericized, tagged document. QMS remains the sole system of record for tenant PII throughout. This matters for future data-handling/compliance scoping of this tool: the surface area needing protection in Orchestrator for this feature is much smaller than "a system that holds tenant PII" would imply — it's closer to "a system that transiently reads a document, writes a differently-shaped document, and stores neither the input's real values nor a copy of QMS's data."

Still genuinely unscoped/undesigned otherwise (extraction mechanism, how confident matching needs to be, human review step, etc.) — this note only fixes the PII-storage misconception, not the design.

## How this is known

Boris's direct correction in conversation on 2026-08-03, describing the actual intended data flow precisely.

## Related

- [[Platform Vision (Onboarding Orchestrator)]]
