---
date: 2026-08-13
description: "Third full front+back 'CTO-grade' code-quality audit of UnitPrep (after 2026-07-24's 9-milestone refactor and 2026-07-27's post-refactor audit shipped"
tags:
  - project-note
source_repo: bmaksimov
---

# Third CTO-Grade Audit — Auth Through Template Tagger

Third full front+back "CTO-grade" code-quality audit of UnitPrep (after 2026-07-24's 9-milestone refactor and 2026-07-27's post-refactor audit shipped as v1.1.1), covering everything shipped since: the full auth/RBAC/admin subsystem, the new QMS Template Tagging Assistant (docx-surgeon, tagger-pipeline, template-tagger crates + its UI), and a regression check of the original engine/tool UI. Boris asked for a report only, not execution — 6 parallel full-read agents (no sampling) plus a personal spot-check of the 2 highest-severity claims and one centralized build/lint/dependency pass, mirroring the prior two audits' methodology. Findings published as an HTML artifact: https://claude.ai/code/artifact/b6f97ff5-f573-4c25-99b0-646b2e3b2c01 (may not remain accessible indefinitely — this note is the durable record).

## What changed

- No code changes made — this session was audit/report only, per Boris's request. All findings below are unfixed as of this note.


## Decisions

- Split review into 6 parallel full-read agents by natural seam (core/unit-group/dedup; auth/RBAC/admin backend; template-tagger stack; API/session/infra; auth/admin frontend; tool+tagger frontend) rather than sampling — matches the methodology of both prior audits.
- Told all 6 agents NOT to run cargo/npm build-test-lint commands themselves, and ran one consolidated verification pass myself afterward instead — this machine has a documented RAM ceiling (see Gotchas) and 6 concurrent Rust/Next builds was judged a real freeze risk.
- Independently re-verified the 2 highest-severity claims (session-ownership IDOR, frontend auth-check race) by reading the exact cited code myself rather than trusting agent output blindly — both confirmed exactly as reported.
- Did not execute any fixes or write a milestone plan for approval — presented a recommended plan in the report but left it unexecuted, since the ask this time was explicitly a report/evaluation, not a refactor pass.


## Learned

- Two of the six parallel agents hit a mid-session API rate limit ('session limit, resets 12:50pm') and terminated early; 3 of the 5 failures had a resumable agentId and transcript, so SendMessage-to-resume (continue from where you left off, don't restart) recovered them with no lost work; the other 2 had to be relaunched from scratch with the identical original prompt.
- Running cargo test --workspace / clippy / cargo audit alone (no other concurrent heavy process) was fine on this RAM-constrained machine — the documented freeze risk was specifically concurrent local-LLM-plus-heavy-test-suite load, not a single sequential cargo invocation.
- A dependency-version fix applied to one crate (core's quick-xml 0.36→0.41 bump from the last audit) did not propagate to a sibling crate created afterward (docx-surgeon still pinned quick-xml 0.36) — cargo audit is the only way this surfaces; no amount of code reading finds a stale lockfile pin.
- The last audit's Next.js CVE risk assessment ruled out several advisories partly via 'no middleware.ts' and 'no next/image usage' — both are now false (proxy.ts is Next 16's renamed middleware convention; next/image is now used in 2 components), so that risk conclusion needs redoing, not just re-citing.


## Verification

cargo test --workspace: 579 passed, 0 failed, 3 ignored. cargo clippy --workspace --all-targets: 0 warnings. cargo fmt --all -- --check: 10 diff hunks across 5 files (minor drift from the 0-diff baseline the last audit established). cargo audit: 2 High (quick-xml, docx-surgeon only). tsc --noEmit: 0 errors. eslint .: 0 errors, 1 warning (a generated coverage artifact file, not source). npm audit: 6 High (3 newly-fixable via plain `npm audit fix`, 3 transitive through next's bundled postcss/sharp, same unfixable-without-major-bump situation as the last audit). The 2 High-severity code findings (IDOR, frontend auth race) were independently re-read against the live source, not just taken from agent output.


## Open

- HIGH: session-ownership IDOR — with_owned_session/with_owned_session_mut exist and are correct but have zero call sites; every session-touching handler (~17) still uses the unowned with_session/with_session_mut. owner_id is correctly stamped at creation, so this is a mechanical fix (swap call sites, rename _user->user).
- HIGH: frontend auth-check race — app/(app)/layout.tsx's loading guard never accounts for checked still being false, so RequirePermission.tsx mounts with user=null on every fresh load and silently bounces a legitimate admin hitting an admin URL directly to /clients.
- HIGH: docx-surgeon/Cargo.toml pins quick-xml 0.36.2 (2 current High RustSec advisories, directly reachable via uploaded .docx files) while core already correctly uses the patched 0.41.
- HIGH: Template Tagger UI has zero test coverage; HIGH: the admin/auth frontend subsystem overall has almost none, which is exactly where the auth-race finding was hiding.
- HIGH: auth backend's actual authenticated success path has zero DB-backed test coverage — already caused one real production incident (a queried column that no migration had added, caught live not in CI).
- HIGH: MasterGroupFileSection.tsx's hand-rolled upload fetch only checks 404, not 401 — a live gap now that passkey auth has actually shipped.
- MEDIUM: last-active-admin guard (auth_user_role.rs / auth_user_status.rs) is check-then-act with no row lock — a real concurrency race that could zero out all admins.
- MEDIUM: invite-time role assignment gated by users.manage not users.manage_roles — latent privilege-escalation seam once a narrower custom role exists.
- MEDIUM: TOTP re-enrollment takes no proof of the outgoing factor — flagged for backend confirmation, not asserted as a live exploit.
- Full list of ~20 Medium and ~21 Low findings (file splits, DRY duplication, stale doc comments, timing side-channel, etc.) is in the published artifact, not duplicated here.
- Recommended 6-milestone fix plan was written but NOT approved or started — see the artifact's final section if resuming this as an execution pass.


## Related

- [[UnitPrep Architecture Overview]]
- [[Post-Refactor Audit]]
- [[Full Review & 9-Milestone Refactor]]
- [[Code Review Watchlist]]
- [[Patterns]]


_Recorded 2026-08-13T20:15:24.470Z from `bmaksimov` via the om MCP server (routing: caller)._
