
# UnitPrep (OO) - Tech Stack

Built 2026-10-01 from a full scan of `unitprep-api` (v1.9.55) and `unitprep-ui` (v1.6.53) manifests, CI, scripts and config, for Boris's CTO presentation.

**Last updated:** 2026-10-01 (initial build). Current as of `unitprep-api` v1.9.55 / `unitprep-ui` v1.6.53.

**Caveats for the presenter**
- There is **no OAuth2/OIDC** for sign-in. Auth is passkeys (WebAuthn) plus TOTP. The only OAuth is the *outbound* Dropbox OAuth2 flow.
- **Hosting is undecided** (THREAT_MODEL: "deployment hasn't chosen yet"); Cloudflare is the likely edge, not adopted.
- "Why" bullets come from code comments where they exist (`Cargo.toml`); otherwise they are standard rationale, not recorded decisions. See the vault's Key Decisions note for recorded ones.

## Backend (Rust)

### Rust 1.96 (pinned in `rust-toolchain.toml`, 2021 edition, Cargo workspace of 7 crates)

- Area: Language and build
- What it does: Whole backend. Crates: `core`, `dedup`, `unit-group`, `docx-surgeon`, `template-tagger`, `tagger-pipeline`, plus the root `unitprep` binary.
- Why we use it:
    - Memory safety, no null or data-race crashes
    - Pinned toolchain = identical builds locally and in CI
    - Separate crates keep each tool's domain logic apart from HTTP orchestration

### Axum 0.8

- Area: HTTP API framework
- What it does: Routing, multipart upload, extractors.
- Why we use it:
    - Built on Tokio/Tower, async and middleware-friendly
    - Typed extractors (authenticated user) make auth checks hard to forget

### Tokio

- Area: Async runtime
- What it does: Concurrent I/O, e.g. parallel Process Street calls via `futures::join_all`.
- Why we use it:
    - Standard Rust runtime
    - Many in-flight requests without a thread each

### Tower-HTTP

- Area: Middleware
- What it does: CORS, catch-panic, trace, request-id.
- Why we use it:
    - Handler panic returns our own JSON 500 instead of dropping the connection
    - Per-request correlation ID for traceable logs

### tower_governor (`governor`)

- Area: Rate limiting
- What it does: Throttles unauthenticated auth endpoints.
- Why we use it:
    - In-process, no new infrastructure
    - Same self-hosted-library preference as the rest of auth

### PostgreSQL 18 (Neon in dev, `postgres:18` in Docker)

- Area: Database
- What it does: System of record: clients, auth, audit, tool runs.
- Why we use it:
    - Row-Level Security, 70+ policies enforcing access in the DB itself
    - `citext` (case-insensitive emails), `jsonb`, `pg_trgm` (fuzzy search)
    - ~180 migration files, versioned and reversible (up/down)

### Neon

- Area: Managed Postgres
- What it does: Hosted dev DB behind a transaction-mode PgBouncer pooler.
- Why we use it:
    - Serverless Postgres, no DB server to run
    - TLS-only

### SQLx 0.8 (`rustls`, offline `.sqlx` cache)

- Area: DB access
- What it does: Async, compile-time-checked SQL.
- Why we use it:
    - Queries verified against the schema at build time
    - Pure-Rust TLS, no OpenSSL
    - Native UUID/TIMESTAMPTZ/INET/JSONB mapping

### webauthn-rs

- Area: Auth: passkeys
- What it does: Passkey registration and sign-in (verified with Windows Hello and Proton Pass).
- Why we use it:
    - Phishing-resistant, no passwords to leak or reuse
    - Records device-bound vs synced credentials

### totp-rs

- Area: Auth: 2nd factor
- What it does: TOTP fallback for devices without a passkey.
- Why we use it:
    - RFC 6238 handled correctly (base32, skew window, `otpauth://`)
    - QR drawn in the browser, no heavy server image deps

### ChaCha20-Poly1305

- Area: Encryption at rest
- What it does: Encrypts TOTP secrets, Dropbox/Process Street/Elavon credentials in the DB, client data fields.
- Why we use it:
    - Authenticated encryption detects tampering
    - Ciphertext bound to the user ID, can't be swapped between rows
    - Fast without AES hardware

### sha2 + getrandom + base64

- Area: Auth: sessions
- What it does: Session tokens.
- Why we use it:
    - OS CSPRNG-generated
    - Only the hash is stored, a DB leak doesn't expose live sessions
    - Opaque cookie verified by DB lookup, no JWT

### axum-extra (cookies), time, hex

- Area: Auth plumbing
- What it does: Session cookie handling; hex-encoded keys (survives shell/`.env` quoting that mangles base64 `+`/`=`).

### thiserror / anyhow

- Area: Error handling
- What it does: Typed auth errors; ergonomic propagation.

### serde / serde_json

- Area: Serialization
- What it does: JSON in/out of the API and JSONB columns.

### ts-rs

- Area: Backend-to-frontend contract
- What it does: Generates TypeScript types from Rust structs.
- Why we use it:
    - One source of truth for API shapes
    - CI fails if generated types drift from the UI

### reqwest (rustls)

- Area: Outbound HTTP
- What it does: Process Street API; Dropbox API/OAuth2.
- Why we use it:
    - TLS stack matches SQLx, no second OpenSSL tree

### calamine

- Area: File ingestion
- What it does: Reads uploaded .xlsx/.xls exports from other vendors.
- Why we use it:
    - Pure Rust, read-only

### csv + encoding_rs

- Area: File ingestion
- What it does: CSV parse/write with legacy-encoding handling.

### quick-xml + zip

- Area: Tagger / DOCX; ZIP export
- What it does: Reads/edits Word templates as XML inside the .docx zip (`docx-surgeon`); builds ZIP exports.
- Why we use it:
    - In-place edit preserves template formatting

### rust_xlsxwriter

- Area: Exports
- What it does: Formatted XLSX dedup reports.

### printpdf (no default features)

- Area: Exports
- What it does: Audit-log PDF report.
- Why we use it:
    - 14 built-in PDF fonts, no font files to ship
    - Default features dropped to avoid an HTML-engine dependency tree

### chrono / chrono-tz

- Area: Date and time
- What it does: UTC storage; correct Pacific display incl. DST.

### strsim, regex, once_cell

- Area: Matching logic
- What it does: Fuzzy name/address similarity (unit-group, dedup, Process Street correlation).

### parking_lot

- Area: Concurrency
- What it does: In-memory caches (vendor-format registry).
- Why we use it:
    - Locks don't get permanently poisoned by a panic

### bincode

- Area: Sessions
- What it does: Compact binary serialization of durable tool sessions.

### uuid

- Area: IDs
- What it does: v4 identifiers for sessions and records.

### tracing / tracing-subscriber

- Area: Observability
- What it does: Structured logs, request spans, SQLx slow-query logging.

### dotenvy

- Area: Config
- What it does: `.env.local` in dev; real env vars when deployed.

## Frontend

### Next.js 16 (App Router)

- Area: Framework
- What it does: Routing, layouts, dev/build server.
- Why we use it:
    - Route groups split public (login/invite) from app-shell pages
    - `proxy.ts` = coarse session-cookie gate, signed-out users never see protected UI

### React 19

- Area: UI
- What it does: Components plus custom hooks (abortable ops, infinite log feeds, save status).

### TypeScript 5

- Area: Language
- What it does: Strict typing, shared with backend via `ts-rs` types.

### Tailwind CSS 4 (PostCSS)

- Area: Styling
- What it does: Utility-first dark theme.
- Why we use it:
    - No separate stylesheet to maintain
    - Consistent design tokens

### qrcode

- Area: Auth UX
- What it does: Renders TOTP enrolment QR from the `otpauth://` URI in the browser.

### fflate

- Area: Client-side files
- What it does: In-browser ZIP handling (e.g. peeking XLSX headers pre-upload).
- Why we use it:
    - Tiny, fast, zero dependencies

### Node 24 (`.nvmrc`)

- Area: Runtime
- What it does: Pinned in `.nvmrc` and the Docker image.

## Testing, quality and security tooling

### cargo test + proptest

- Area: Backend tests
- What it does: Unit, HTTP-integration (real loopback router), race and property-based tests.

### serial_test

- Area: Backend tests
- What it does: Serializes tests sharing process-global env vars.

### Vitest 5 + jsdom

- Area: Frontend unit tests
- What it does: Fast, Vite-based, Jest-compatible.

### React Testing Library + user-event

- Area: Frontend component tests
- What it does: Tests behaviour as a user sees it.

### Playwright (Chromium)

- Area: E2E
- What it does: Browser flows with mocked API responses (`page.route`).

### @vitest/coverage-v8, cargo-llvm-cov

- Area: Coverage
- What it does: Source-based coverage on both stacks (tarpaulin as optional cross-check).

### Clippy (`-D warnings`) + rustfmt

- Area: Backend lint
- What it does: Warnings fail the build.

### ESLint 9 (eslint-config-next) + `tsc --noEmit`

- Area: Frontend lint
- What it does: Type and lint gates.

### cargo-audit

- Area: Supply-chain security
- What it does: RUSTSEC advisory scan; accepted ones documented in `.cargo/audit.toml`.

### npm audit

- Area: Supply-chain security
- What it does: Frontend dependency scan.

### gitleaks

- Area: Secret scanning
- What it does: Scans commits for secrets, plus a grep-based backstop script.

### `preflight.sh` + `.githooks/pre-push`

- Area: Local CI gate
- What it does: 9 steps before every push: fmt, clippy, tests, audit, gitleaks, secret scan, version/tag consistency, workflow-secrets guard, TS-binding drift.

## Infrastructure, CI/CD and external systems

### GitHub + GitHub Actions (`checkout`, `setup-node`, `Swatinem/rust-cache`)

- Area: CI/CD
- What it does: fmt, check, clippy, tests, DB tests against Postgres on every push; workflow-secrets guard.

### Docker / Docker Compose

- Area: Dev environment
- What it does: Dev containers for API and UI plus ephemeral Postgres 18 test DB.
- Why we use it:
    - Source bind-mounted, no rebuild per change
    - Tests run as the real `app_service` role, not a superuser

### sqlx-cli 0.9

- Area: Migrations
- What it does: Applies migrations in CI.

### Process Street API

- Area: Integration
- What it does: Read-only source for client/facility creation (Intake, Merchant, Contract workflows), replacing manual entry.

### Dropbox API (OAuth2)

- Area: Integration
- What it does: File access for onboarding; credentials editable in an admin page, stored encrypted.

### Elavon / QMS

- Area: Integration
- What it does: Merchant account and pinpad credentials, synced and stored encrypted.

### Cloudflare (planned, not adopted)

- Area: Edge
- What it does: Likely front door; would also give country-level geolocation for anomaly detection.

## Architectural patterns worth a slide

- **Security in layers**: passkey login, TOTP fallback, hashed session tokens, rate limiting; Postgres Row-Level Security as the last line, so a missed app-code check can't leak data.
- **Rust-to-TypeScript contract**: `ts-rs` generates types, CI fails on drift.
- **Self-hosted libraries over paid services**: rate limiting, auth, encryption all in-process.
- **Quality gates**: same checks locally on push and again in CI.

