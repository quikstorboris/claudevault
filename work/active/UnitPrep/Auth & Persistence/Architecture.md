---
date: 2026-07-27
description: "Locked v1 architecture for OO (Onboarding Orchestrator) auth: self-hosted WebAuthn/TOTP, opaque session cookie (not JWT), Postgres/Neon, Admin>Security nav, interface-first third-party strategy."
tags: [work-note, unitprep, auth]
status: active
quarter: Q3-2026
project: unitprep
---

# Auth & Persistence — Architecture

Locked 2026-07-20, following the Onboarding Orchestrator nav restructuring and Group Prep net-new-client fix (see [[UnitPrep Architecture Overview|UnitPrep]] and [[Platform Vision (Onboarding Orchestrator)|UnitPrep Platform Vision]]). This is the agreed plan; nothing described here was built yet as of the source conversation — see [[Phase 2 Progress]] and [[Database Schema]] for what has actually been built since.

## Why now, not speculative

Auth was previously deferred with an explicit trigger ("right before QMS API integration needs it"). It ended up being triggered by a different, equally concrete need instead: introducing user roles (Admin, Implementation Manager, Department Manager, View-only) for the admin panel, which requires real user identity to exist at all. Persistence (Postgres/Neon) is justified by the same trigger — user records need to be durable.

## Identity/session architecture — decided

- **Self-hosted, not a managed identity SaaS.** WorkOS/Clerk were considered and explicitly rejected. Uses vetted Rust libraries: `webauthn-rs` (Kanidm project — mature, audited via real production use) for WebAuthn/passkey verification, plus TOTP (`totp-rs` or similar) as a fallback, authenticator-app only, never SMS.
- **Auth logic lives in the Rust backend (`unitprep-api`), not Next.js** — consistent with the project's "thin frontend, domain-driven backend" principle. The WebAuthn ceremony (`navigator.credentials.create()/.get()`) must run in browser JS — no way around that — but Next.js just relays the raw ceremony result to Rust for verification and session issuance.
- **Passkeys are the primary factor, not "2FA on top of something else."** A passkey is already inherently multi-factor (possession + biometric/PIN unlock) and phishing-resistant (bound to origin) in a way TOTP fundamentally isn't (TOTP codes can be captured/relayed by an adversary-in-the-middle proxy). TOTP is a fallback for un-enrolled devices, not a mandatory second step stacked on a passkey.
- **Device-bound passkeys** (private key never leaves specific hardware — TPM/Secure Enclave/hardware key) are the stronger variant vs. synced passkeys (iCloud Keychain/Google Password Manager). ~~Device-bound should be required specifically for accounts that will hold QMS/Dropbox credentials.~~ — **requirement dropped 2026-07-29, see below.**
  - **Decision reversed, 2026-07-29**: device-bound is **not** required, and synced passkeys are explicitly acceptable, for any account. Two reasons, both concrete rather than theoretical. First, **Boris works remotely on occasion** — a credential that cannot leave one machine means being locked out whenever that machine isn't to hand, and the fallback for that is exactly the break-glass/re-enrolment path this design treats as a heavily-logged exception, not a routine. Second, when the first real ceremony was run, **Windows Hello produced a synced credential by default** (`backup_eligible: true`) — so enforcing device-bound would reject the ordinary path on the ordinary browser, to protect QMS/Dropbox credentials that do not exist yet. Requiring the stronger variant is only worth its cost once there is something behind it *and* a workable answer for the multi-device case; neither holds today.
  - What survives the reversal: `webauthn_credentials.device_bound` is still recorded, now **correctly** (previously it defaulted to `true` for every row regardless of truth). It is informational only — nothing refuses a credential on it. An admin reviewing which users are on synced vs hardware-bound passkeys is a genuinely useful view later, and the value costs nothing to keep accurate at registration.
  - If this is ever revisited, the honest version is *per-action* rather than per-account: require a fresh device-bound factor at the moment someone views or edits a stored third-party credential (i.e. fold it into step-up re-auth, Phase 4), rather than blocking enrolment up front.
- **Session mechanism: one httpOnly, Secure, SameSite cookie, short-lived with rotation — frontend never reads or manages it.** Deliberate resolution of Boris's "minimize cookies, prefer server-to-server" instinct: server-to-server is right for backend-to-third-party calls (Dropbox/QMS), but a human's *browser* has no server-to-server equivalent. A bearer token in localStorage (the usual "avoid cookies" alternative) is actually less secure for a browser app (JS-readable — one XSS bug anywhere = trivial session theft); httpOnly cookies aren't readable by JS at all. The "cookies are bad" narrative is mostly about third-party tracking cookies, a different concern from first-party session cookies.
- **The cookie holds an opaque session token, not a JWT — decided, final.** A JWT's appeal (statelessness, no DB lookup) directly conflicts with the admin-panel requirement to instantly and completely revoke a session ("sign out everywhere" for a stolen device) — a JWT can't be revoked before natural expiry without maintaining a revocation list anyway, defeating the point. An opaque token looked up in Postgres on each request gives instant, complete revocation for free at negligible latency cost at this scale. Note: "JWT" (statelessness) and "per-request cryptographic signing" (DPoP-style) are independent axes — conflating them was the source of the original question.
- **DPoP was seriously considered and explicitly not adopted**, in favor of step-up re-authentication. RFC 9449 DPoP is specified for OAuth2 bearer tokens via `Authorization` headers, not cookies — adopting it would mean reverting to bearer tokens or having frontend JS actively sign a proof on every request (real frontend involvement in session mechanics, contradicting "frontend never touches session state"). No mature Rust DPoP crate exists comparable to `webauthn-rs`. **DBSC (Device Bound Session Credentials)** — a Chrome-led, emerging standard — is the actually-correct fit for "bind a cookie session to a device-held key," but isn't broadly cross-browser supported yet; worth watching, not building against. Practical stand-in adopted instead: **step-up re-authentication** (require a fresh passkey tap) for sensitive actions — viewing/editing a client's stored QMS/Dropbox credentials, changing another user's role.
  - Precise threat model DPoP covers, worth remembering: protects against a credential being physically exfiltrated and replayed later from a *different* device — does NOT protect against live XSS abuse on the original device. Both the plain-cookie model and a DPoP-protected model are equally exposed to "attacker has live code running on the page right now."

## Roles — v1 scope narrowed further (final)

**v1 ships with a single role: Admin.** The originally-discussed four-role model (Admin, Implementation Manager, Department Manager, View-only) plus department-level Groups (Boris likes Atlassian's separation of Groups-at-department-level from Roles-at-user-level) is explicitly deferred, not built now — there's effectively one real user (Boris) today.

This cascades usefully: deferring Groups also defers the department-scoped RLS policies that depended on it, so v1's schema/RLS work is meaningfully lighter. Basic RLS hygiene on users/sessions/audit tables is still worth doing even with one role.

One implementation detail carried forward anyway: define the `role` column as extensible (Postgres enum, or checked text) from day one, even though "Admin" is the only valid value right now — so adding the other three roles later is adding enum values, not restructuring the column.

Enforcement must happen server-side on every privileged endpoint regardless of role count — hiding UI in Next.js is not a security boundary.

## Persistence: Postgres via Neon — locked in

SQLite was seriously argued (simpler ops, no separate service, trivial local dev) and explicitly rejected once real context was added: expected scale is 10-100 users across four role types with a growing feature surface, plus two Postgres-specific capabilities SQLite has no equivalent of:

- **Row-Level Security (RLS)** — DB-layer-enforced per-role row visibility, independent of the Rust backend's own authorization checks. Real defense-in-depth. **Important caveat**: RLS's benefit only materializes if the backend's DB connection strategy is designed around it (e.g. connecting as a role tied to the acting user, or `SET LOCAL ROLE` per request) rather than always connecting as one superuser role. Connecting as a superuser typically bypasses RLS entirely unless `FORCE ROW LEVEL SECURITY` is set.
- **JSONB** — fits OO's data shape well: client config templates are explicitly "extensible, not a closed list" of integrations (QMS API, Dropbox, ClickUp, maybe Process.st/Zoho later — see [[Platform Vision (Onboarding Orchestrator)|UnitPrep Platform Vision]]). SQLite's `json1` support is real but less capable.

Also: a SQLite database is a bare file — anyone with filesystem access has everything. Postgres enforces access at the DB layer itself, independent of the app, which matters once compliance/audit posture (CCPA, etc.) is a real concern.

**DB host: Neon** — confirmed over Supabase (its bundled-auth differentiator is moot since auth is self-hosted) and over CockroachDB/Railway/Render (no compelling advantage surfaced).

## The service-vs-library framework for third-party decisions

Resolves an apparent tension in Boris's own values: minimize third-party reliance vs. don't reinvent the wheel vs. security/audits being "less of a tradeoff" (leans toward proven/vetted approaches specifically when security is on the line). Resolution: separate **third-party services** (ongoing, hosted, billed, control ceded) from **third-party libraries** (audited, open-source, self-hosted, no ongoing vendor relationship). Prefer vetted libraries over vetted services; only reach for a service when no reasonable self-hosted alternative exists. Applied:

- Auth → library (`webauthn-rs`) — decided.
- Database → Neon is a service, but on the *infrastructure/ops* axis, not the *security-logic* axis — decided, locked in.
- ZTNA (Cloudflare Access) → pure service, no self-hosted equivalent, defense-in-depth on top of already-strong identity. **Recommendation: defer, don't build toward it, revisit only if a hosting decision makes it near-zero-incremental-cost later.**
- Email/ESP → no viable self-hosted alternative in practice. **Explicitly deferred** — want to first find out what Quikstor/QSX's existing infra already uses.
- KMS → not yet triggered (no real secrets exist to encrypt yet); same framework applies when it is.

## Still explicitly deferred to a future conversation

- Whether to introduce persistence/third-party services early (avoid future rework) vs. only when strictly needed — the general timing question.
- Third-party admin-settings and email-provider choice specifically.
- What QSX's own existing infrastructure already uses (suspected it may already have ESP/auth given QSX itself has login) — unconfirmed.
- Audit-readiness and privacy regulation compliance (CCPA named explicitly).

## Admin nav/UI design (not yet built)

Left nav gets a second top-level entry, `Admin`, alongside `Clients` — same config-driven array `LeftNav.tsx` already uses. `Admin` routes directly into a `Security` tabbed page (same config-driven tab pattern `ClientTabs.tsx` already established) — deliberately not building a multi-section Admin sub-nav yet, since Security is the only Admin section that exists.

Security's tabs, as currently scoped:
- **Authentication Policy** — org-wide 2FA requirements, allowed factors, mandatory-enrollment toggle, step-up-auth rules.
- **Users** — invite, deactivate, role assignment, per-user enrolled-factor visibility. Session/device management (list + remote revoke) and recovery/break-glass actions live here too, as per-user drill-down actions. A *global* cross-user session-overview page was raised and deferred as a future nice-to-have.
- **Groups** — department/team groupings for RLS row-visibility scoping, orthogonal to roles. Deferred to future considerations along with the multi-role work — not built for v1.
- **Audit Logs** — searchable log viewer. Break-glass events fold in here as a filtered category. Storage intent (not yet designed in detail): structured JSONB per-event-type, with the tab rendering a human-friendly summary on top.

## Third-party strategy: self-service first, interface-first design

Bias toward self-hosted for now, but don't lock the door on a third party later — knowingly willing to accept some rework cost if that swap ever happens. The concrete mechanism for keeping rework small: **build every self-hosted piece behind a clean interface/trait now**, even with only one implementation behind it — e.g. an `IdentityProvider`/`AuthBackend`-style trait wrapping the `webauthn-rs` logic, so a future third-party swap (WorkOS, a KMS vendor, an ESP) means writing a new implementation of the same interface, not rewriting every caller.

## Admin panel scope — confirmed features (not yet built)

- Session/device management: list active sessions per user, remote "sign out everywhere."
- Audit log viewer, searchable. Concrete event-type list to design against: enrollment (passkey/TOTP), password/2FA changes, login success, login failure, source IP, timestamps, and **break-glass protocol initiation itself as its own logged event type** (not just the outcome).
- Recovery/break-glass log: who approved re-enrolling a user's lost device. "Break-glass" = an emergency-access procedure that deliberately bypasses normal auth controls, reserved for genuine exceptions, heavily logged precisely because it circumvents the usual safety rails — capturing which Admin, for which user, when, and how the requester's identity was re-confirmed (this matters because "I lost my device, re-enroll me" is exactly the pretext a social-engineering attacker would use).
- **Future idea, explicitly not a requirement**: if a user is deleted as part of an extraordinary/break-glass-adjacent situation, isolate their existing work history into a restorable vault/archive rather than losing it — a "soft delete with restorable archive" pattern. Not designed, not committed to.
- A future home for the network-policy toggle (ZTNA) once trigger-gated.
- 2FA policy settings — may partly live in a third-party provider's dashboard if one is ever adopted; currently moot.
- Mandatory first-login 2FA enrollment gate.
- Email OTP: intended as at minimum a config-shell — but self-hosting auth means *we* would need to own sending it, unlike a managed-provider path. Reopens the "is it viable before an EMS decision" question.
- SMS: explicitly skipped entirely, not offered as a factor.

## See also

- [[Build Plan & Infra Checklist]] — priority-ordered phases, trigger-gated deferred items, Neon setup status, infra checklist.
- [[Database Schema]] — the table-by-table design that implements this architecture.
- [[Phase 2 Progress]] — implementation progress against Phase 2 ("Core identity & sessions").
