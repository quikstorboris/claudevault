---
date: 2026-10-01
description: "Canonical list of every tool/technology UnitPrep (OO) uses, front and back end — name, area, what it is and why. Built for the CTO presentation. KEEP CURRENT: add a row whenever a new tool is introduced."
tags: [reference, unitprep, tech-stack]
status: active
---

# UnitPrep Tech Stack

Built 2026-10-01 from a full scan of `unitprep-api` (v1.9.55) and `unitprep-ui` (v1.6.53) manifests, CI, scripts and config, for Boris's CTO presentation. Pull from here instead of re-scanning the code.

**STANDING RULE: whenever a new tool, library, service or infrastructure piece is introduced to either repo, add a row here in the same session and bump "Last updated" below.** The rule is also recorded in both repos' `CLAUDE.md` and in Boris's auto-memory.

**Last updated:** 2026-10-05 (gzip response compression via tower-http `compression-gzip`; shared in-house outbound-HTTP retry/timeout helper `integrations::http`, no new crate). Earlier: 2026-10-02 (ClickUp integration + per-user permission grants). Current as of `unitprep-api` v1.9.65 (pending) / `unitprep-ui` v1.6.55.

**Caveats for the presenter**
- There is **no OAuth2/OIDC** for sign-in. Auth is passkeys (WebAuthn) plus TOTP. The only OAuth is the *outbound* Dropbox OAuth2 flow.
- **Hosting is undecided** (THREAT_MODEL: "deployment hasn't chosen yet"); Cloudflare is the likely edge, not adopted.
- "Why" bullets come from code comments where they exist (`Cargo.toml`); otherwise they are standard rationale, not recorded decisions. See [[Key Decisions]] for recorded ones.

## Backend (Rust)

| Tool | Area | What it is / why we picked it |
|---|---|---|
| **Rust 1.96** (pinned in `rust-toolchain.toml`, 2021 edition, Cargo workspace of 7 crates) | Language and build | Whole backend. Crates: `core`, `dedup`, `unit-group`, `docx-surgeon`, `template-tagger`, `tagger-pipeline`, plus the root `unitprep` binary.<br>• Memory safety, no null or data-race crashes<br>• Pinned toolchain = identical builds locally and in CI<br>• Separate crates keep each tool's domain logic apart from HTTP orchestration |
| **Axum 0.8** | HTTP API framework | Routing, multipart upload, extractors.<br>• Built on Tokio/Tower, async and middleware-friendly<br>• Typed extractors (authenticated user) make auth checks hard to forget |
| **Tokio** | Async runtime | Concurrent I/O, e.g. parallel Process Street calls via `futures::join_all`.<br>• Standard Rust runtime<br>• Many in-flight requests without a thread each |
| **Tower-HTTP** | Middleware | CORS, catch-panic, trace, request-id, gzip response compression (`compression-gzip`, added 2026-10-05; pulls `async-compression`, `compression-codecs`, `compression-core`, `tokio-util`).<br>• Handler panic returns our own JSON 500 instead of dropping the connection<br>• Per-request correlation ID for traceable logs<br>• Large JSON/CSV payloads shrink ~80-90%; already-compressed formats (ZIP, XLSX, DOCX, PDF) are excluded |
| **tower_governor** (`governor`) | Rate limiting | Throttles unauthenticated auth endpoints.<br>• In-process, no new infrastructure<br>• Same self-hosted-library preference as the rest of auth |
| **PostgreSQL 18** (Neon in dev, `postgres:18` in Docker) | Database | System of record: clients, auth, audit, tool runs.<br>• Row-Level Security, 70+ policies enforcing access in the DB itself<br>• `citext` (case-insensitive emails), `jsonb`, `pg_trgm` (fuzzy search)<br>• ~180 migration files, versioned and reversible (up/down) |
| **Neon** | Managed Postgres | Hosted dev DB behind a transaction-mode PgBouncer pooler.<br>• Serverless Postgres, no DB server to run<br>• TLS-only |
| **SQLx 0.8** (`rustls`, offline `.sqlx` cache) | DB access | Async, compile-time-checked SQL.<br>• Queries verified against the schema at build time<br>• Pure-Rust TLS, no OpenSSL<br>• Native UUID/TIMESTAMPTZ/INET/JSONB mapping |
| **webauthn-rs** | Auth: passkeys | Passkey registration and sign-in (verified with Windows Hello and Proton Pass).<br>• Phishing-resistant, no passwords to leak or reuse<br>• Records device-bound vs synced credentials |
| **totp-rs** | Auth: 2nd factor | TOTP fallback for devices without a passkey.<br>• RFC 6238 handled correctly (base32, skew window, `otpauth://`)<br>• QR drawn in the browser, no heavy server image deps |
| **ChaCha20-Poly1305** | Encryption at rest | Encrypts TOTP secrets, Dropbox/Process Street/Elavon credentials in the DB, client data fields.<br>• Authenticated encryption detects tampering<br>• Ciphertext bound to the user ID, can't be swapped between rows<br>• Fast without AES hardware |
| **sha2** + **getrandom** + **base64** | Auth: sessions | Session tokens.<br>• OS CSPRNG-generated<br>• Only the hash is stored, a DB leak doesn't expose live sessions<br>• Opaque cookie verified by DB lookup, no JWT |
| **axum-extra** (cookies), **time**, **hex** | Auth plumbing | Session cookie handling; hex-encoded keys (survives shell/`.env` quoting that mangles base64 `+`/`=`). |
| **thiserror / anyhow** | Error handling | Typed auth errors; ergonomic propagation. |
| **serde / serde_json** | Serialization | JSON in/out of the API and JSONB columns. |
| **ts-rs** | Backend-to-frontend contract | Generates TypeScript types from Rust structs.<br>• One source of truth for API shapes<br>• CI fails if generated types drift from the UI |
| **reqwest** (rustls) | Outbound HTTP | Process Street API; Dropbox API/OAuth2.<br>• TLS stack matches SQLx, no second OpenSSL tree |
| **calamine** | File ingestion | Reads uploaded .xlsx/.xls exports from other vendors.<br>• Pure Rust, read-only |
| **csv + encoding_rs** | File ingestion | CSV parse/write with legacy-encoding handling. |
| **quick-xml + zip** | Tagger / DOCX; ZIP export | Reads/edits Word templates as XML inside the .docx zip (`docx-surgeon`); builds ZIP exports.<br>• In-place edit preserves template formatting |
| **rust_xlsxwriter** | Exports | Formatted XLSX dedup reports. |
| **printpdf** (no default features) | Exports | Audit-log PDF report.<br>• 14 built-in PDF fonts, no font files to ship<br>• Default features dropped to avoid an HTML-engine dependency tree |
| **chrono / chrono-tz** | Date and time | UTC storage; correct Pacific display incl. DST. |
| **strsim, regex, once_cell** | Matching logic | Fuzzy name/address similarity (unit-group, dedup, Process Street correlation). |
| **parking_lot** | Concurrency | In-memory caches (vendor-format registry).<br>• Locks don't get permanently poisoned by a panic |
| **bincode** | Sessions | Compact binary serialization of durable tool sessions. |
| **uuid** | IDs | v4 identifiers for sessions and records. |
| **tracing / tracing-subscriber** | Observability | Structured logs, request spans, SQLx slow-query logging. |
| **dotenvy** | Config | `.env.local` in dev; real env vars when deployed. |

## Frontend

| Tool | Area | What it is / why we picked it |
|---|---|---|
| **Next.js 16** (App Router) | Framework | Routing, layouts, dev/build server.<br>• Route groups split public (login/invite) from app-shell pages<br>• `proxy.ts` = coarse session-cookie gate, signed-out users never see protected UI |
| **React 19** | UI | Components plus custom hooks (abortable ops, infinite log feeds, save status). |
| **TypeScript 5** | Language | Strict typing, shared with backend via `ts-rs` types. |
| **Tailwind CSS 4** (PostCSS) | Styling | Utility-first dark theme.<br>• No separate stylesheet to maintain<br>• Consistent design tokens |
| **qrcode** | Auth UX | Renders TOTP enrolment QR from the `otpauth://` URI in the browser. |
| **fflate** | Client-side files | In-browser ZIP handling (e.g. peeking XLSX headers pre-upload).<br>• Tiny, fast, zero dependencies |
| **Node 24** (`.nvmrc`) | Runtime | Pinned in `.nvmrc` and the Docker image. |

## Testing, quality and security tooling

| Tool | Area | What it is / why we picked it |
|---|---|---|
| **cargo test + proptest** | Backend tests | Unit, HTTP-integration (real loopback router), race and property-based tests. |
| **serial_test** | Backend tests | Serializes tests sharing process-global env vars. |
| **Vitest 5 + jsdom** | Frontend unit tests | Fast, Vite-based, Jest-compatible. |
| **React Testing Library + user-event** | Frontend component tests | Tests behaviour as a user sees it. |
| **Playwright** (Chromium) | E2E | Browser flows with mocked API responses (`page.route`). |
| **@vitest/coverage-v8, cargo-llvm-cov** | Coverage | Source-based coverage on both stacks (tarpaulin as optional cross-check). |
| **Clippy (`-D warnings`) + rustfmt** | Backend lint | Warnings fail the build. |
| **ESLint 9 (eslint-config-next) + `tsc --noEmit`** | Frontend lint | Type and lint gates. |
| **cargo-audit** | Supply-chain security | RUSTSEC advisory scan; accepted ones documented in `.cargo/audit.toml`. |
| **npm audit** | Supply-chain security | Frontend dependency scan. |
| **gitleaks** | Secret scanning | Scans commits for secrets, plus a grep-based backstop script. |
| **`preflight.sh` + `.githooks/pre-push`** | Local CI gate | 9 steps before every push: fmt, clippy, tests, audit, gitleaks, secret scan, version/tag consistency, workflow-secrets guard, TS-binding drift. |

## Infrastructure, CI/CD and external systems

| Tool | Area | What it is / why we picked it |
|---|---|---|
| **GitHub + GitHub Actions** (`checkout`, `setup-node`, `Swatinem/rust-cache`) | CI/CD | fmt, check, clippy, tests, DB tests against Postgres on every push; workflow-secrets guard. |
| **Docker / Docker Compose** | Dev environment | Dev containers for API and UI plus ephemeral Postgres 18 test DB.<br>• Source bind-mounted, no rebuild per change<br>• Tests run as the real `app_service` role, not a superuser |
| **sqlx-cli 0.9** | Migrations | Applies migrations in CI. |
| **Process Street API** | Integration | Read-only source for client/facility creation (Intake, Merchant, Contract workflows), replacing manual entry. |
| **Dropbox API (OAuth2)** | Integration | File access for onboarding; credentials editable in an admin page, stored encrypted. |
| **ClickUp API (v2, personal tokens)** | Integration | Per-user: each Orchestrator user connects their own ClickUp personal API token (stored encrypted, never shown again) so ClickUp work is attributed to them. Connection check built; task actions next. |
| **Elavon / QMS** | Integration | Merchant account and pinpad credentials, synced and stored encrypted. |
| **Cloudflare** (planned, not adopted) | Edge | Likely front door; would also give country-level geolocation for anomaly detection. |

## Architectural patterns worth a slide

- **Security in layers**: passkey login, TOTP fallback, hashed session tokens, rate limiting; Postgres Row-Level Security as the last line, so a missed app-code check can't leak data.
- **Rust-to-TypeScript contract**: `ts-rs` generates types, CI fails on drift.
- **Self-hosted libraries over paid services**: rate limiting, auth, encryption all in-process.
- **Quality gates**: same checks locally on push and again in CI.

## Related
[[UnitPrep Architecture Overview]] · [[UnitPrep CI-CD Framework]] · [[UnitPrep Docker Standards]] · [[Key Decisions]]
