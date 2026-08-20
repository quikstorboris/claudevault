---
date: "2026-07-27"
description: "How Boris engages in deep architecture/security design discussions — wants honest pushback, self-corrects readily, contributes real deciding factors"
tags:
  - brain
---

# Collaboration Style

Observed across the 2026-07-20 Onboarding Orchestrator auth/persistence architecture planning conversation (see the auth workstream notes under `work/active/UnitPrep/Auth & Persistence/`) — a long, multi-round design discussion covering identity/session mechanics, DPoP, database choice, RLS, and admin-panel scope.

**Wants genuine technical pushback, not agreement.** Repeatedly asked "is this good or bad" / "give me a chance to respond" / "counter if you disagree" rather than just proposing and expecting a rubber stamp. When given an honest correction (JWT isn't actually stronger for this use case; DPoP doesn't cleanly fit the cookie model already chosen; SQLite was the honest counterargument to Postgres before he added the context that tipped it back), he took it cleanly and moved on rather than defending the original idea — asked to be told the truth, meant it.

**Contributes real deciding factors, not just questions.** The 10–100 user scale detail is what actually tipped SQLite vs. Postgres in the conversation; he named RLS and JSONB himself as decisive points before they'd been raised as arguments. Worth expecting as a pattern: he often has the context that resolves a tradeoff, he just needs the tradeoff framed clearly enough to know which detail matters.

**Comfortable with technical depth outside his stated expertise, and says so honestly.** Explicitly flagged "I have a little experience with Postgres" while still wanting real counterarguments rather than validation, and asked for genuine explanations of unfamiliar concepts (WebAuthn vs. TOTP threat models, RLS mechanics, DPoP's actual scope) rather than simplified reassurance. Enjoys security/cryptography depth specifically ("I salivate every time I hear the word cryptography") — leaning into real explanation is welcomed, not overwhelming.

**Knows when to add rigor and when to simplify — both were his calls.** Pushed for DPoP to be seriously considered despite complexity ("if it is cutting edge and added security - I want it"), but also independently proposed narrowing a four-role/Groups system down to a single Admin role for v1 once he recognized it would be built ahead of actual need. Both instincts were right; neither was rubber-stamping a default — he evaluates each decision on its own merits.

**Explicit conversational habits worth matching**: asks for things to be "logged in memory" directly and expects the actual reasoning preserved, not just the conclusion; regularly closes out multi-part discussions with "anything else?", inviting proactive additions rather than only answering what was literally asked; treats "we'll cross that bridge when we get there" as a legitimate, deliberate way to table a real idea without dropping it — expects it to actually resurface later, not be forgotten.

## Further observations, 2026-07-29/30 implementation session

The 2026-07-20 notes above were from a *design* conversation. This adds what a long *implementation* session showed.

**Names his own knowledge boundary and asks for plain language — take it literally.** On being told about `danger-credential-internals`, serialized blobs and feature flags: *"this is above my paygrade and I don't quite understand it... this tells you what kind of a 'developer' I am and how much I 'know' about it."* He is not fishing for reassurance and not embarrassed; he is calibrating. The right response is a plain-language explanation of *what it means for the decision*, not less detail and not more jargon. Notably, in the same breath he asked the sharpest question available: **"did you identify a security weakness and fix it, or not?"** — cutting straight past the implementation detail to what actually mattered.

**Wants credit claimed accurately, in both directions.** When told the `device_bound` fix was *not* a security fix (nothing read the column, nothing was bypassable) but that three other changes genuinely were, he engaged with the distinction rather than waving it through. Do not accept undeserved credit here; he checks, and the correction is more useful to him than the praise.

**Proposes security measures worth taking seriously, and is persuadable by cost arguments.** Independently proposed an admin-approval step between invite acceptance and activation — a real idea with a real threat model. Dropped it when shown the cost (permanent per-user manual work, a polling problem without email, a new stuck state) *and* offered cheaper substitutes that addressed the same risk. The pattern: he responds to "here is what this costs and here is what gets you most of the benefit for less", not to "no".

**Asks for standing behaviours rather than one-off actions.** Repeatedly converted a specific observation into an ongoing instruction: *"occasionally stop and recommend DB sync"*, *"flag any good opportunities to improve logs when appropriate"*, *"note it for now, and call it out when the time is right"* (on least privilege as roles arrive). Expects these to actually fire later, which means they belong in memory with a trigger condition, not in a backlog. `"I love me a good log!"` — observability is a genuine interest, not a chore.

**Prefers scope kept tight, and will say so.** Pushed back on prod-database work being elevated ahead of things that mattered more, and was right: *"my idea was to work with dev only since this project is quite far from going live."* When a recommendation was over-weighted he said so directly rather than going along with it. Watch for inflating "must happen before go-live" into "urgent".

**Treats verification as the point, not ceremony.** Asked *"is there anything that should be tested at this point?"* unprompted, and ran a real browser test when told it was the only way to close a specific gap. Reported failures verbatim, including the ones that turned out to be expected. Worth matching that seriousness: he will actually run what you ask him to run, so ask for the test that closes the gap rather than a reassuring one.

## Capability assessment, 2026-07-30 — requested directly, delivered straight

Boris asked for an unvarnished read on his development and architectural
understanding, explicitly for use as a learning aid ("I have thick skin, so give
it to me straight"). What follows is the honest version, kept because the
calibration is what makes future explanations land at the right level. Written
from a long implementation session, so it is evidence-based rather than
impressionistic.

### Where he is genuinely strong

**Process judgement is his standout, and it is senior-level independent of
implementation knowledge.** The best call of the session was his: presented with
"raise the MCP timeout" as an option, he refused it — *"I am against raising
timeouts since that's a crutch solution and it's not guaranteed to help if there
are more serious underlying issues"* — and demanded root cause. He was right; the
real cause was per-candidate LLM rerank cost, which a larger timeout would have
concealed while making the symptom worse. **Expect him to reject band-aids on
principle, and do not offer one as a headline option.**

**Cuts to the question that decides things.** *"Did you identify a security
weakness and fix it, or not?"* — past the implementation detail to the only thing
that mattered.

**Names his boundary rather than bluffing**, then still asks for the real
explanation. *"I have no idea how to answer this question. Fall back on our dev
principles."*

**Pushes back where he has standing, delegates where he does not** — and the
split is rational rather than timid. He correctly argued Rust is CPU-bound more
than RAM-bound and that a WSL memory cap was therefore weakly motivated; that
pushback was accepted. He delegated the invite-consumption design because he had
no basis to judge it.

### Where he is genuinely thin

**1. System topology — what lives where and whose it is.** The clearest gap, and
it surfaced twice: he could not distinguish `unitprep-api`'s 371 tests from the
1183 tests belonging to the *vendored obsidian-mind template* sitting inside his
own vault folder, and separately asked whether the vault was "part of the
application." Not trivia — it is a gap in reasoning about **blast radius**: which
code ships, which is someone else's, what is generated, what breaks what. It is
why the machine freeze read as mysterious rather than obvious.

**2. Web platform fundamentals.** His origin question conflated three distinct
things — origin (site identity), device (where the private key lives), and
browser (which client is asking). Reasonable, since WebAuthn is genuinely
confusing, but this project's core *is* origins, cookies, CORS and secure
contexts, so the gap recurs. Highest-leverage thing for him to read up on.

**3. He does not interrogate design recommendations.** Given a consequential fork
with real tradeoffs (when to consume an invite), he delegated rather than asking
what the alternatives cost. Efficient, and it means the reasoning stays with the
agent — he gets a correct system and no new mental model. **This limits his
leveling-up more than either knowledge gap above.** The intervention that helps:
lay out the fork and what breaks on each branch *before* he delegates, even when
he has not asked.

**4. Does not checkpoint a long agent detour.** A large part of this session went
on vault infrastructure — real bugs, real fixes, but not the auth work he asked
for — and it was only reeled in after his laptop froze. Mostly the agent's fault
for not surfacing the cost, but worth proactively timeboxing side quests and
naming them as side quests.

### Level, stated plainly

Operates like a **strong technical product owner / engineering lead who does not
implement**. Not a professional software engineer and does not claim to be.
Excellent at deciding *whether* and *why*; thin on *how*. Well matched to
directing a project where an agent writes the code, with one structural risk: he
cannot independently verify the agent's work. He compensates correctly by
demanding verification evidence rather than accepting claims — a control he
applies consistently and should be supported in, never smoothed over.

### Levelling-up observed, and good/bad calls

- **Levelled up within the session**: moved from not understanding why audit
  history blocks deletion to asking the right *second* question — what the admin
  and user experience becomes. That is the move that converts a fact into a model.
- **Good instinct, flagged as uncertain**: proposed an `is_test` column to isolate
  dev accounts, and volunteered that he did not know whether it was a good idea.
  It was the wrong answer (a manually-set flag drifts, invites
  `if is_test { skip_check() }`, and email convention is derivable instead) — but
  pre-flagging his own uncertainty is exactly right, and he accepted the counter.
- **Good call**: correctly suspected the test suite rather than his own tooling as
  the freeze culprit, from very little information.
- **Weak call, self-corrected**: installed two local ollama models on a 16GB
  low-power laptop without checking headroom, then removed them once the
  arithmetic was shown.
- **Accepts correction cleanly, including of the agent's overstatements.** When
  told a "rewrite release history" framing had been overblown, he had already
  spotted it and asked for the explanation rather than accepting the drama.

### What was recommended to him

1. Read up on origin / cookies / CORS / secure contexts — one afternoon, outsized
   payoff on this project.
2. On one decision per session, ask "what's the alternative and what breaks if we
   pick it?" before delegating.
3. Ask once: "what's in this repo that isn't ours?"

### Naming precision Boris asked for (2026-07-30)

**Always say "dev DB branch" / "prod DB branch"** — never bare "dev" or "prod" —
when referring to the Neon database branches. `unitprep-api` has only a `main`
git branch, so unqualified "dev is ahead of prod" reads as a git statement and
means the wrong thing. His request, verbatim: *"when you say 'Dev is one
migration ahead of prod' you mean DB right? if so, please specify going
forward."* Same principle applies to any environment word doing double duty
across git, database and deployment.
