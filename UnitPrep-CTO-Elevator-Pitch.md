# UnitPrep / Onboarding Orchestrator - Elevator Pitch

## The 30-second version

UnitPrep (the Onboarding Orchestrator) is an internal platform that replaces manual, error-prone facility onboarding work. It pulls client and facility data straight from Process Street, cleans and validates customer data files (duplicate-tenant detection, unit-group preparation, QMS template tagging), and tracks every step in a durable history. It is built in Rust and Next.js with security, auditability and performance designed in from the start, so a pilot can grow into a supported product without a rewrite.

## What it does (features)

- **Client and facility creation from Process Street.** Read-only integration with the Intake, Merchant and Contract workflows replaces re-keying data by hand.
- **Duplicate-tenant detection.** Finds tenants with inconsistent contact details across units, with XLSX and CSV correction reports ready to send to facility managers.
- **Unit-group preparation.** Analyzes unit files from multiple vendor formats and prepares them for QMS import, with validation and inline correction of issues.
- **QMS template tagging.** Edits Word templates in place with matched tags, so formatting is preserved.
- **Vendor-format registry.** New source-system formats are onboarded through data, not code changes.
- **Integrations.** Dropbox and Elavon credentials are managed from an admin page, not environment files.
- **Onboarding Work history.** A durable per-facility record of every tool run.
- **Admin and audit tooling.** Role-based access, invites, security and activity logs, and a PDF audit-log export.

## Security and safeguards

- **Passwordless sign-in.** Passkeys (WebAuthn) are the primary login, so there are no passwords to steal or reuse. TOTP is the fallback, and enrolment is mandatory.
- **Defense in depth on data.** PostgreSQL row-level security enforces access in the database itself, with 70+ policies. A missed check in application code cannot leak data.
- **Encryption at rest.** Stored credentials and TOTP secrets use authenticated encryption (ChaCha20-Poly1305), bound to the owning record.
- **Safe sessions.** Tokens are random, only a hash is stored, and sessions can be revoked. A database leak does not expose live sessions.
- **Abuse protection.** Rate limiting on public endpoints, and handler panics return a clean error instead of dropping the connection.
- **Least privilege.** The app connects to the database as a restricted role, not a superuser. Integrations and administration are admin-only permissions.
- **Break-glass recovery.** A CLI-only admin bootstrap has no web surface at all.
- **Full audit trail.** Security and activity events are logged and exportable.

## Quality and supply-chain controls

- **Automated gates before every push:** formatting, strict linting (warnings fail the build), the full test suite, dependency vulnerability scanning (cargo-audit, npm audit) and secret scanning (gitleaks).
- **Hundreds of automated tests:** unit, property-based, HTTP-integration against the real router, race tests, and browser end-to-end tests.
- **Types shared across the stack.** TypeScript types are generated from the Rust structs, and CI fails if they drift.
- **Compile-time-checked SQL.** Queries are verified against the schema at build time.
- **Reversible migrations.** About 180 versioned database migrations, each with an up and down.
- **Real findings, real fixes.** The scanners and live testing have already caught and closed a critical Next.js vulnerability, a RUSTSEC advisory, a CORS gap and an identity-matching bug.

## Efficiency

- **Compiled, memory-safe Rust** handles large rent-roll and tenant files quickly and predictably.
- **Concurrent I/O.** Process Street calls run in parallel rather than one after another.
- **Measured and tuned.** A quadratic comparison pass in the dedup tool was found by profiling and pruned.
- **Pooled database connections** through a transaction-mode pooler keep connection overhead low.
- **Small frontend footprint.** Six production frontend dependencies means fewer things to patch.

## Architecture and maintainability

- **Clean separation of concerns.** A Cargo workspace splits shared ingestion (`core`), each tool's domain logic (`dedup`, `unit-group`, tagger crates) and the HTTP layer, so each tool can change independently.
- **Container-based dev environment.** Docker Compose gives a repeatable setup with an ephemeral test database.
- **CI-ready from day one.** The preflight gate and GitHub Actions pipeline are already in place for a team to pick up.
- **Self-hosted libraries over paid services.** Auth, rate limiting and encryption run in-process, so there is no vendor lock-in or new infrastructure to buy.
- **Documented.** Threat model, authentication design, runbook, audit-retention policy and a project knowledge base.

## Where it stands

- It is a pilot, so hosting and production rollout depend on management's decision.
- Everything above runs today in development and is exercised against real client data.
- A production deployment would need: a hosting decision (Cloudflare is the likely edge), a named backup owner for break-glass access, and monitoring and alerting.
