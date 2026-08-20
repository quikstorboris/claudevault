---
date: 2026-08-07
description: "Boris's standing instruction, 2026-08-07: \"as a general rule, when new features are discussed, quietly check the API and see if we can leverage it…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-07T18:24:16.492Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# When new Orchestrator features are discussed, check the QMS API for leverage before assuming new backend work is needed

Boris's standing instruction, 2026-08-07: "as a general rule, when new features are discussed, quietly check the API and see if we can leverage it for anything." Applies to every future Orchestrator/UnitPrep feature conversation, not just the session it was said in.

Mechanism: the QMS Public Gateway WebApi v2 (92 endpoints, 307 schemas) was read in full 2026-08-07 and recorded in the vault at reference/QMS API/ (QMS API Index, Endpoint Catalog, Domain Model & PII, Tool Opportunities — start with the Index). Before proposing a new tool, a new data field, or a new piece of Orchestrator functionality, check whether QMS's API already exposes the capability, the data, or a close analogue — quietly, i.e. as part of normal design thinking, not as a separate ceremony Boris has to ask for each time.

Concretely this already caught one real thing: Boris's idea for a template/placeholder-tag editor turned out to have no backing capability in the API at all (confirmed by full-text search across the spec for placeholder/template/merge-field/macro — the only "template" fields are two opaque assignment booleans, and the lease-document endpoint returns only a signed PDF URL, never template content). Surfacing that before any scaffold got built is the payoff this rule is for — cheaper to find via the API doc than via building toward a capability that doesn't exist yet.

If the API spec changes (a newer version gets pulled), re-derive the domain notes rather than assuming the cached read still holds — the vault notes are dated 2026-08-07 and should be treated as being of that vintage.

## How this is known

Confirmed by full-text search across the entire 602KB OpenAPI spec (api-1.json) for 'placeholder', 'template', 'merge field', 'macro', 'token' — zero hits for placeholder/merge-field/macro; the only template-related fields are two boolean assignment flags on Unit and an opaque templateId on delinquency processes.

## Related

- [[QMS API Index]]
- [[Platform Vision (Onboarding Orchestrator)]]
