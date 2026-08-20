---
date: 2026-07-27
description: "Boris's long-term vision for UnitPrep as \"Onboarding Orchestrator\": client records, config templates (QMS/Dropbox/ClickUp), tool-suite nav, progress tracking. None built yet."
tags: [work-note, unitprep]
status: active
quarter: Q3-2026
project: unitprep
---

# Platform Vision (Onboarding Orchestrator)

Captured 2026-07-16, after both backend tools (Group Prep, dedup) were built and working, then substantially evolved 2026-07-17. This is Boris's own stated vision for where the platform goes next — shared explicitly so future work adjusts toward it, **not because any of it is being built yet**. Treat everything below as forward-looking roadmap, not a shipped feature or even a committed spec.

## QSX vs. QMS — a real, important distinction

- **QSX**: QuikStor's original, archaic, desktop-based (Windows 95-era UI) software. Local database, local interface, no true internet access, rarely talks to a centralized company server. **Being aggressively sunset.** The sample data used to verify the dedup tool's domain logic is QSX-era — legacy data, not representative of the target platform going forward.
- **QMS**: the modern evolution — cloud/web-based, API-capable. This is the actual PMS platform UnitPrep is building toward. Group Prep's output files (net-new/similar groups, etc.) get imported back into QMS today. The real OpenAPI spec for QMS lives at `C:\Users\bmaksimov\OneDrive - Kobre Holdings, LLC\Documents\api-1.json` — read this before designing anything QMS-API-related; don't assume capabilities without checking it first. As of 2026-07-16, Boris's own understanding of the API is shallow — the only capability either of us could name concretely is pulling the master unit-group list. Treat any other assumed capability as unverified until the doc is actually read.

## The long-term vision (Boris's words, lightly organized)

Not a committed spec — a mental model to build toward gradually, adjusting as reality (and the actual QMS API doc) informs specifics.

**1. Client Prep — the real top-level navigation concept.** Rather than a flat left-nav listing each tool as a peer ("Group Prep", "Deduplication"), the better mental model is **"I'm working on this client/facility"** — a single "Client Prep" entry point containing every tool as a horizontal tab collection underneath. This matches how an implementation manager actually thinks about their work — by client, not by tool — since both existing tools (and presumably future ones) get run for every client as part of onboarding.

**2. Entry flow into Client Prep:**
1. Log in (see auth, below).
2. Click "Client Prep".
3. System asks: raw source files, or connect to the client's QMS database? (Exact wording TBD once the API's real shape is known.)
   - **Files path** (today's model, unchanged): proceed to the tabbed module page.
   - **API path**: present a credential-entry screen for that client's QMS API. Once authenticated, the *same* discovery/analysis UI applies, but each tool gains an added option ("look up data in the DB") alongside file/folder selection — a mix of sourcing methods per client, not an exclusive either/or.
4. Inside the tabbed page, tools are run **in any order**, are **all optional**, and switching between them or returning to a previous tool's step for revisions is always allowed. A "do you want to do $TOOL now?" prompt is a suggestion, never a permanent lock for that session.
5. Dedup is **file-only, permanently** — QSX data is what's being migrated *from*, so there's no QMS-side source to query for it. Only applies to tools whose source data actually lives in QMS.

**3. File/folder selection UX**: let the user point at **one all-inclusive folder** containing everything for that client — group files, unit list files, tenant list files for dedup, etc. (matches the real-world `Preliminary Data`/`Units Migration` folder structure already seen in sample facility data). UnitPrep would auto-identify which files are relevant to which tool (extending the header-based sniffing classification logic `discover.rs` already does for Group Prep, not filename guessing), and present a **confirmation step** showing what it found, with the ability to correct misidentified files before proceeding. Per-tool manual file/folder selection (today's model) stays available as an explicit alternative even after this exists — additive, not a replacement.

**Technical note for whoever builds this**: a browser can't freely browse an arbitrary filesystem, but a user-initiated folder picker (native OS folder dialog, or drag-and-drop of a folder) *can* read every file inside a chosen folder, non-recursively, with one-time user permission — no Dropbox API integration needed as long as the folder is locally synced (which today's KoBre Dropbox setup already is). Real Dropbox API integration would only become relevant if the web app needed to reach into an account that *isn't* locally synced to the machine running the browser — a distinctly bigger, different feature than "let the user pick a folder."

**4. Authentication — deliberately not built yet, but the target shape is set.** When it does get built: strong-by-default, low-friction — 2FA via OTP and/or passkey as the primary mechanism, leaning on Next.js's own auth capabilities. Boris is also open to something like a locally-held file/hash-signature or HMAC-style mechanism for extra assurance, but doesn't yet know enough to commit to it — flagged as "figure out what's actually sound here," not a firm requirement. Explicit design goal: "Fort Knox, but not burdensome" — accept some one-time setup friction (enrolling a passkey, etc.), never ongoing friction beyond that. **Trigger for building this**: QMS API credential storage — that's the point the current no-auth internal posture stops being acceptable, since the tool would then hold a real secret for a real production system, not just this tool's own session data. (Note: as of this writing, actual auth design/build work — self-hosted WebAuthn/TOTP, Postgres/Neon+RLS — is underway separately; see the Auth & Persistence workstream.)

**5. Persistence / database** — needed for storing each client's analysis results so a future run can compare against a past one. This is the *same* underlying need as dedup's already-tabled "re-check two pulls over time" feature, tabled explicitly until a real database conversation happens — Boris independently arrived at the same need from the Group Prep/Client Prep side, which confirms that whenever persistence does get designed, it should be **one shared capability serving every tool's "compare to last time" need**, not built bespoke per tool. Also relevant: whether a global company/client-list API exists in QMS (letting "Client Prep" start from "pick an existing client" instead of manually establishing client identity each time) — worth checking once the API doc is actually reviewed. Boris's own words: "too far out to architect now" — agreed; revisit only once there's a concrete trigger.

## The gradual-build sequencing — agreed 2026-07-16

Explicit principle: **validate each layer before generalizing it; don't let an early layer's design quietly assume there's only one way of doing something later.** Concretely, the agreed order (each step usable on its own, none blocking the next, nothing built before the step before it has actually been used):

1. Standalone per-tool screens, file upload only, no auth. Group Prep's UI already does this; dedup's equivalent was next.
2. Once both tools are working and have been used a bit: wrap them in the "Client Prep" left-nav + tabs, as **pure navigation** — same two independent per-tool uploads underneath, just organized under one roof. No backend change required.
3. Only if repeated real use shows "uploading the same files twice for two tools" is an actual recurring pain point: build the shared all-inclusive-folder selection + auto-identification + confirmation UI. This is the first step that needs real new backend thinking (a "client" concept spanning multiple tool sessions) — wait for the proven need, don't guess at it.
4. Auth, built properly, right before QMS API integration needs it — not before, not speculatively.
5. QMS API integration — its own project, gated behind auth. Read the real OpenAPI doc first; don't design against assumed capabilities.
6. Persistence/DB — last, and only once a concrete feature actually needs it (dedup's re-check-over-time, and/or Client Prep's cross-run comparison, whichever lands first).

**Explicit scope discipline as of 2026-07-16**: none of steps 3-6 were being built at the time. The immediate next real step was finishing standalone per-tool UI (step 1).

**Status 2026-07-17**: Boris asked to hold off on step 2 (the Client Prep nav wrapper) until the post-launch tightening punch list was fully closed out first — not abandoned, just sequenced after loose ends rather than started early. Separately, the vision itself evolved substantially — see below. Treat that section as superseding the scope of "Client Prep" described above, not contradicting it: the tabbed-navigation idea is still real, it's just now understood as one piece of a considerably bigger picture.

## Vision evolution 2026-07-17: "Onboarding Orchestrator"

Captured verbatim-in-spirit from Boris, explicitly **for awareness and future shaping — no immediate action required**, not a spec to start building. Recorded in full because it changes *why* several previously-deferred items (auth, persistence, centralized file storage) exist, which should inform how those get designed whenever their own trigger arrives, even though nothing here was being built yet as of this capture.

**The reframe**: UnitPrep isn't just a data-processing tool — it's becoming a **task checklist / executor for the whole client onboarding process**. Boris's own words: it's "time we rename it to **Onboarding Orchestrator**" to reflect that expanded scope. Same relationship as the earlier "UnitPrep → Group Prep" rename — a **product-facing** naming evolution, not a code change; the repos/code still say `unitprep-*` throughout, and an actual rename is its own distinct, not-yet-scheduled task, same as the still-pending `unit-group`/`UnitGroup` code rename. Scoped (not started) 2026-08-07 — see [[UnitPrep to Orchestrator Rename]].

**The envisioned flow**:
1. A new onboarding starts. The implementation manager (Boris) selects or creates a **client** — manually, or eventually via an API + Dropbox integration.
2. The tool creates a **client record** and a **config template** where the user connects, per client:
   - API credentials for the client's QMS instance.
   - A Dropbox folder connection (their onboarding files live there today — this generalizes the "one all-inclusive folder" idea above into a persistent per-client connection rather than a one-off picker).
   - A ClickUp task list / client dashboard connection.
   - *(optional, ultra-low-priority)* Process.st, if it turns out to have a usable API — unconfirmed, unexplored.
   - *(optional, ultra-low-priority)* Zoho.
   - Possibly more integrations over time — the config template is meant to be extensible, not a closed list.
3. Once configured, a navigation screen shows the **tool suite** for that client: Group Prep, dedup, and — named for the first time here — a **lease document processor** (no further detail given yet; a real future tool candidate, not just a placeholder), plus whatever else joins later.
4. The implementation manager completes these in **any order they choose** — onboarding deliverables genuinely don't arrive in a fixed order or on the same timeline, so the tool must not impose one.
5. Each deliverable/process/analysis/output can be marked **complete**, which rolls up into an overall **onboarding progress** indicator — Boris's own words: "a separate feature, low priority until we have a meaningful tool set." Not being designed now.

**Why this matters for architecture decisions going forward** (Boris's own framing): this is *the* reason auth, centralized file-storage access, and persistence all eventually need to exist — they stop being abstract "someday" items and become concrete requirements of a real product shape:
- **Persistence** — a client record, its config (credentials, integration connections), its tool-suite completion state, and overall progress all need to be stored somewhere real, not in-memory-per-session. This is a considerably bigger persistence need than the earlier-scoped "compare this run to a past run" capability — it's now core state, not an optional comparison feature.
- **Authentication** — once the tool holds real per-client QMS API credentials *and* Dropbox/ClickUp/etc. connections, the no-auth internal posture is no longer just "should be closed before client-facing exposure" — it's closer to a prerequisite for the config-template step existing at all safely. (This is deliberate current-state, not an oversight — the no-auth posture was a conscious sequencing choice, not a surprise gap.)
- **Centralized file storage access** — the Dropbox connection is no longer a one-off "pick a folder" browser interaction; it's a persistent per-client integration, a meaningfully different technical shape (likely real Dropbox API integration, not just a local folder picker).

**Boris's own forward-looking signal, 2026-07-17**: "looking at the deferred tasks, I think we are getting close to planning authentication and dropbox features." Recorded as a signal worth watching for, **not** a decision to start building — the gradual-build discipline above (validate each layer before generalizing, wait for a concrete trigger) still applies. When this vision is revisited, re-read this whole section first — it reframes what "auth" and "Dropbox integration" would even need to accomplish, a different (bigger) shape than the original gradual-build sequencing envisioned.

## Where things actually stand now (context as of this migration, 2026-07-27)

None of steps 2-6 above, nor the Onboarding Orchestrator flow itself, have been built. What *has* moved since this vision was captured is the auth groundwork specifically (self-hosted WebAuthn/TOTP design finalized, database schema built and verified on Neon dev, Phase 2 build plan underway) — tracked separately as its own workstream rather than folded into this note, since that work is concrete and in progress while everything else here remains conceptual.

**Update 2026-08-07**: auth is now largely shipped (see [[Auth & Persistence Index]]), and step 5's own gate — "read the real OpenAPI doc first" — is done. See [[QMS API Index]] and its companion notes for the full read, plus a same-day correction from Boris: this API is a read-heavy operations/export surface for facilities **already live on QMS**, not a channel for net-new onboarding data intake — a separate team imports new clients' data by other means, and Orchestrator's tools only prepare data beforehand. That directly affects step 3 above: the "API path" idea (credential screen → "look up data in the DB" as an alternative to file upload during onboarding prep) assumed a new client's data would already be reachable via this API at prep time, which per the correction it isn't — there's nothing to look up for a genuinely new client. **Open question, not resolved**: whether "API path" still makes sense for a narrower case (an existing multi-facility client onboarding one more facility, where the company record already exists in QMS) — worth asking Boris directly rather than assuming either way before this step is designed for real. What the API *is* good for — see [[QMS API - Tool Opportunities]]'s Go-Live Readiness Auditor — is a plausible new tool for the existing suite, not a mechanism for step 3's entry flow. Step 5 (QMS API integration) still blocked on a real base URL (QMS's `servers` field is empty in the spec — Boris confirming with a colleague).
