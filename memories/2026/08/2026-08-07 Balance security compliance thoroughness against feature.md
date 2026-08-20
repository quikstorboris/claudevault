---
date: 2026-08-07
description: "Boris's explicit standing instruction on UnitPrep (2026-08-06), stated while reviewing a security/compliance architecture proposal: proactively…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-07T15:17:35.674Z"
scope: project
projects: ["unitprep-api", "unitprep-ui"]
confidence: verified
---

# Balance security/compliance thoroughness against feature velocity — don't front-load controls before their trigger arrives

Boris's explicit standing instruction on UnitPrep (2026-08-06), stated while reviewing a security/compliance architecture proposal: proactively surfacing security and compliance considerations is wanted and valued, but building them preemptively is not. His words: "this is all in the name of security, but i don't want to get bogged down locking down the fort at the cost of slow feature development. need a good balance here."

How to apply this: when a new security/compliance idea comes up (from a review, an external tool's suggestion, or your own analysis), the default action is to NAME it, record it with a concrete trigger condition (a specific future event, not a vague "later"), and defer building it until that trigger actually fires -- not to implement it immediately just because it's correct in principle. This is the same discipline this project already applies elsewhere (KMS deferred until a real secret exists to encrypt, ZTNA deferred until a hosting decision makes it near-zero-cost, Groups deferred until a real multi-client-visibility need exists, the last-remaining-admin guard deferred until rollout is real) -- the instruction here is to keep applying that same discipline deliberately to PII/compliance work specifically, rather than let "PII and compliance" as a topic feel like it demands a different, more front-loaded standard than everything else in the project.

The failure mode this guards against: treating every theoretically-correct control (encryption, exhaustive access logging, formal DSR tooling, self-service portals) as something to build now because it's defensible in isolation, which collectively slows feature work without a concrete need pulling any single piece forward yet. The test before building a security/compliance control: is there a real, present trigger for it (real data of that sensitivity exists, a real second person needs the oversight, a real regulatory ask has landed), or is it still hypothetical? If hypothetical, record it with its trigger and move on.

## Related

- [[Compliance & Process Readiness]]
