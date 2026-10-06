---
date: 2026-10-05
description: "Risk investigations behind the Efficiency Refactor plan: why the in-process session cache is NOT being done, the exact conditions under which the AEAD (ChaCha20) modules may be consolidated, the last_seen_at throttle SQL design, and the detect-vendor findings."
tags: [work-note, unitprep, efficiency, refactor, decisions, security]
status: active
quarter: Q4-2026
project: unitprep
---

# Efficiency Refactor - Decisions and Investigations

Companion to [[Efficiency Refactor - Master Plan and Progress]] and [[Efficiency Refactor - Findings Reference]]. Boris asked (2026-10-05) that two risky ideas be investigated thoroughly and acted on only if no risk remains. Findings below were gathered by read-only reviewers and spot-checked; they are static analysis (no compile, no profile).

## Decision 1 - In-process session-resolution cache: NOT DOING

**Idea:** cache `auth.resolve_session()` results in memory to save one DB round trip per authenticated request.
**Verdict: NOT WORTH IT.** It saves 1 of ~4-5 round trips and weakens security guarantees the docs make.

Why:
- **What `resolve_session` returns and what depends on it** (`migrations/20261002180000_add_user_permission_grants.up.sql:93-125`, `SECURITY DEFINER`, validity is its WHERE clause: token match, not revoked, `expires_at > now()`, `last_seen_at` within idle window, user active and not deleted): `user_id` (identity, `app.current_user_id` GUC, audit actor, self-target guards), `role_keys` (becomes the `app.current_user_roles` GUC that EVERY RLS admin bypass reads - highest sensitivity), `permission_keys` (Rust `require_permission` gates), `elevated_until` (step-up), `requires_step_up` (403s everything except `/auth/totp/step-up` and `/health/whoami`), `passkey_reverified_until`.
- **Invalidation surface is wide.** In-process events a cache must evict on: logout (`auth_logout.rs:68`), logout-everywhere (`:70`, needs a user_id->tokens index), admin deactivate/reactivate/recovery (`auth_user_status.rs:51,214`, `auth_invites.rs:537,685`; real revocation is a DB TRIGGER `users_revoke_access_paths_on_deactivation`, migration `20260730150000`, so Rust does not know the tokens), role grant/revoke (`auth_user_role.rs:152,318`), per-user permission grant/revoke (`auth_user_permissions.rs:301,313`), step-up (`auth_totp.rs:467` -> `auth.record_step_up`), passkey reverify (`auth_passkey_reverify.rs:311`).
- **Events a cache can NEVER see:** `auth.role_permissions` edits (migrations only, e.g. `20260807120000`, `20260808130000`, `20260909140000`, `20260909180000`, `20261002200000`, applied by an external process; the app does not run migrations), soft-delete by hand SQL (no Rust sets `deleted_at`), role renames, FK cascades, the `bootstrap-admin` CLI (separate process; harmless since it only touches empty/un-enrolled accounts), anything run by hand in psql, and any other instance.
- **Docs contradicted:** `AUTHENTICATION.md` ~92-96 and ~105 ("Revocation is instant and complete"), `THREAT_MODEL.md` ~88-89, and the `begin_rls_transaction` docstring (`authenticated_user.rs:~432-436`: "nothing here caches across requests ... no separate cache to invalidate"). Stale `role_keys` after a demotion would keep full RLS-admin visibility; stale `requires_step_up=true` would lock a user out after a successful step-up.
- **Idle timeout:** a cache hit skips the `last_seen_at` bump, so either the idle timeout silently becomes absolute or a write-behind reintroduces the DB write.
- **Topology:** RUNBOOK.md 75-81 and THREAT_MODEL.md 109, 125-127 say "single instance" as a deliberate current limitation, but nothing in code enforces it (AUTHENTICATION.md ~680 even contains one line saying multi-instance is planned). Any scale-out would silently break a cache's revocation guarantee.
- **Tests:** no test assumes no-caching (HTTP integration tests use an unreachable pool and never reach `resolve_session`); the `#[ignore]`d real-DB tests call SQL directly. A cache placed inside `query_session` would break the one asserting the SQL is valid, unless bypassable.

**Only conceivably acceptable if ALL held:** single instance proven, TTL <= ~2 s, explicit eviction on every in-process event above, fail-closed on admin/role-sensitive routes, DB write still done. At that point the gain is too small to justify the risk. **Re-open only if** the app is deployed multi-instance with a measured auth-latency problem (then use a design that moves revocation checks to the DB, not around it).

**What we do instead (no cache):**
- A1: throttle the `last_seen_at` write and merge the two `set_config` calls (4 -> 3 pre-handler round trips plus much less write load).
- Rejected alternatives: (C) resolve + set_config in one SQL inside the handler's transaction - the extractor runs BEFORE the handler opens its transaction and returns the connection to the pool; making the extractor own the transaction is a ~54-file refactor with pool-concurrency implications (max 20) and gains only 1 round trip, the same as merging `set_config`; (D) `BEGIN; SELECT ...` simple-protocol batching - sqlx does not pipeline that with bind params; (E) a pre-baked function returning GUC strings - saves nothing.
- Round trips per authenticated request today: resolve_session 1, BEGIN 1, set_config 2, handler queries, COMMIT 1; a rejected session adds `check_session_expired` (~`authenticated_user.rs:258`); write handlers add a separate inline pooled `audit_log::record` (56 call sites; making it atomic inside the tx or spawning it is a separate, optional Tier-2 idea with semantic trade-offs - not in the plan).

### `last_seen_at` throttle - design (chunk A1)
A plain conditional UPDATE would return zero rows when the bump is skipped (looks like "no session"), so separate lookup from bump. New migration replacing the function (same signature `(p_token_hash bytea, p_idle_minutes integer)`, same return table `(user_id uuid, role_keys text[], permission_keys text[], elevated_until timestamptz, requires_step_up boolean, passkey_reverified_until timestamptz)`, `LANGUAGE sql SECURITY DEFINER SET search_path TO 'auth','public'`):
```sql
WITH live AS (
  SELECT s.token_hash, s.last_seen_at, s.elevated_until, s.requires_step_up,
         s.passkey_reverified_until, u.id AS uid
    FROM auth.sessions s JOIN auth.users u ON u.id = s.user_id
   WHERE s.token_hash = p_token_hash AND s.revoked_at IS NULL
     AND s.expires_at > now()
     AND s.last_seen_at > now() - make_interval(mins => p_idle_minutes)
     AND u.deleted_at IS NULL AND u.status = 'active'
),
bump AS (
  UPDATE auth.sessions s SET last_seen_at = now() FROM live
   WHERE s.token_hash = live.token_hash AND s.revoked_at IS NULL
     AND s.last_seen_at < now() - make_interval(secs => LEAST(60, p_idle_minutes * 6))
  RETURNING 1
)
SELECT live.uid, (role_keys subquery as today), (permission_keys UNION subquery as today),
       live.elevated_until, live.requires_step_up, live.passkey_reverified_until
  FROM live;
```
(A data-modifying CTE always executes even if unreferenced.) Verify `CREATE OR REPLACE` preserves `GRANT EXECUTE ... TO app_service`.
**Correctness:** stored `last_seen_at` lags real activity by at most T (60 s, or idle*6 s for tiny idle settings). A session can therefore expire up to T EARLY (fail-safe), never late; idle window effectively `[idle-T, idle]`; absolute `expires_at` unaffected. Secondary readers (`auth_users.rs` "last seen" `max(last_seen_at)`, `auth.check_session_expired` migration `20260804170000`) become up to T stale - informational/audit only; `check_session_expired` only runs after `resolve_session` returned no row. Concurrency improves: the row lock is taken at most once per T per session instead of every request. Small snapshot-read window vs. the old UPDATE's post-lock recheck (a revoke committing in the same millisecond may be missed by the read) - no wider than the existing resolve-to-handler gap. `app_service` has NO UPDATE grant on `auth.sessions` (migration `20260729220000`); mutation only via SECURITY DEFINER functions and the trigger - keep it that way.
**Tests:** real-DB `#[ignore]` tests (second call within T leaves `last_seen_at` unchanged; idle session still rejected; revoked/deactivated rejected; returned columns equal) and rerun `query_sessions_own_sql_is_valid_against_the_real_schema` (`authenticated_user.rs:~560`) via `cargo test -- --ignored query_session`.
**Docs to update:** `AUTHENTICATION.md` (~92-104), `THREAT_MODEL.md` (~88), docstrings in `authenticated_user.rs` (~11-14, 104-110, 432-436).

## Decision 2 - AEAD (ChaCha20-Poly1305) modules

**Idea:** de-duplicate the three encryption modules: `src/auth/totp.rs` (~68-205), `src/clients/encryption.rs`, `src/integrations/secrets.rs`.
**Verdict:** golden-vector tests + a shared PRIVATE core with thin wrappers are **SAFE WITH CONDITIONS**; merging the modules or their public APIs is **NOT WORTH IT**; caching the key in a `OnceLock` is **NO**.

### Facts (all three modules)
Byte-identical wire format `[0x01][12-byte random nonce][ChaCha20Poly1305(key, nonce, msg, aad) = ciphertext || 16-byte tag]`; same crate (`chacha20poly1305` 0.10.1, `Payload{msg,aad}`); same constants (`FORMAT_VERSION=1`, `NONCE_LEN=12`, min length 29); key = hex-decoded trimmed env var used directly (no KDF/domain tag/salt); nonce from `getrandom::fill` per call; decrypt checks length then version BEFORE loading the key; single undifferentiated "authentication failed" for wrong key / wrong AAD / tamper (deliberate: no decryption oracle). So a shared core produces/accepts exactly the same bytes: no re-encryption migration needed.

| Aspect | `auth/totp.rs` | `clients/encryption.rs` | `integrations/secrets.rs` |
|---|---|---|---|
| Env var | `TOTP_ENCRYPTION_KEY` | `CLIENT_PII_ENCRYPTION_KEY` | `INTEGRATION_SECRETS_ENCRYPTION_KEY` |
| Plaintext | `&[u8]`/`Vec<u8>` | `&[u8]`/`Vec<u8>` | `&str`/`String` (UTF-8 checked on decrypt) |
| Error type | `TotpError::{NotConfigured(String), Undecryptable, Unusable(String)}` | `EncryptionError::{NotConfigured(String), Undecryptable}` (+ `impl Error`) | plain `String`, different text per failure incl. "(see .env.local)" |
| `is_configured()` | yes | yes | no |
| AAD | raw 16 bytes of `user_id` UUID | caller-supplied | caller-supplied |
| Design stance | per-class key | doc says deliberately NOT a shared abstraction; separate key from TOTP for different blast radius | one key for all integrations; AAD per integration |

AAD bytes in use: TOTP = user UUID bytes; `client_ops.tool_runs.source:{session_id}` and `...records:{session_id}`; party PII `"{facility_id}:{role}:{index}"`; facility secrets AND Elavon credentials BOTH use `facility_id.as_bytes()` with the same key (pre-existing: separated only by plaintext shape - do not change); integrations `b"dropbox_configuration:1"`, `b"process_street_settings:1"`, `"user_clickup_credentials:{user_id}"`.
Call sites: TOTP (`api/auth_totp.rs:216,185,265,374`, `auth/totp.rs:296`); client PII (`client_ops/tool_runs.rs:68,96,119,132`, `clients/merchant_account_mapping.rs:192,450,483,519,549`, `clients/repository.rs:592,1011,1028`, `reencrypt_sources.rs:17`; handlers hard-code "CLIENT_PII_ENCRYPTION_KEY is not configured" in `clients_elavon.rs:86`, `clients_resync.rs:96`, `clients_manual_link.rs:83`); integrations (`dropbox/config.rs:86-87`, `api/dropbox_settings.rs:124-125,246,254`, `process_street/config.rs:47`, `api/process_street_settings.rs:132,323`, `api/clickup_connection.rs:185,319,445`).

### Tests today
Round trip / wrong-AAD / tamper / unknown-version / nonce-uniqueness exist in the TOTP and client modules; `secrets.rs` has NO wrong-length-key test and NO unknown-version test; indirect coverage in `merchant_account_mapping.rs:821-967`, `tool_runs.rs:515-548`, `clickup_connection.rs:720`, `dropbox_settings.rs:412`, `process_street_settings.rs:603`. **There are NO known-answer/golden-vector tests for any of the three formats.** Round-trip tests would still pass if a refactor silently changed the AAD or layout (both sides change together), and nothing checks a ciphertext written by the old code. That gap is the real finding.

### Risks of consolidating
1. Key mixup across classes (no compile-time protection today either) - mitigate with a per-module constant, never a free-form key argument.
2. AAD domain separation: there is no class tag in AAD today (separation = distinct keys, except the shared integration key separated by AAD strings). A "helpful" prefix would break every stored blob.
3. Error text/variants are consumed (503 text in `api/auth_totp.rs:113`; logs in `tool_runs.rs:77`; `secrets` strings flow through `?` into `String` errors in `dropbox/config.rs:86`, `process_street_settings.rs:132` - check whether returned to clients). A generic core must map back to each module's exact variants/text, and must not add distinguishing messages for wrong-key vs wrong-AAD.
4. Nonce reuse: not a consolidation risk as long as `getrandom::fill` per call is kept.
5. **Env caching and test races (key point):** every module re-reads its env var per call and **28 test sites set/remove the key vars at runtime**, with different values in different modules (all-zero key vs `0001..1f`). Assertions depend on removal/malformed values: `encryption.rs:241,252`, `secrets.rs:162`, `auth/totp.rs` `a_malformed_key_is_reported_as_not_configured`, `api/auth_totp.rs:703,740` (remove -> expect 503 -> re-set), `tool_runs.rs:546`. A `OnceLock` cache would make the first value permanent in the test process and break these. Pre-existing latent flake: `tool_runs.rs:515,546` use `serial(client_pii_env)` while all other CLIENT_PII tests use `serial(client_pii_encryption_key_env)` - different locks, can race.

### Conditions for D5c (all must hold, else close as "not worth it")
1. **D5b first:** golden-vector tests (hard-coded blobs generated by CURRENT code, fixed key and AAD) for all three modules, `secrets` negative tests (wrong-length key, unknown version, malformed key), a cross-class test (blob under key A fails under key B), and the serial-group-name unification - merged and green BEFORE any refactor.
2. Env read on every call; no `OnceLock`/static key.
3. Each wrapper keeps its own `KEY_ENV` const and passes it in; no shared default.
4. AAD passed through unchanged (raw bytes; no prefix/tag).
5. Preserve check order: length, version, THEN key load, THEN decrypt (a short blob returns `Undecryptable` even when the key is unset).
6. Wrappers map to exactly the current error variants and strings (incl. "(see .env.local)" and the UTF-8 message for `secrets`).
7. `src/auth/totp.rs` TOTP logic and `auth/mod.rs` re-export policy (`decrypt_secret`/`TotpError` deliberately not re-exported) untouched.
Design (if pursued): `src/crypto/aead_blob.rs`, `pub(crate)`: `BlobError {TooShort, UnknownVersion, AuthFailed, KeyMissing, KeyNotHex, KeyWrongLen(usize), Encrypt}`, `load_key(env)`, `seal(&Key, aad, pt)`, `open(&Key, aad, blob)`. Payoff is ~40 duplicated lines x3 - small; the module docs explicitly argue for separate small per-purpose modules. Honest recommendation: do D5b (real value, zero risk) and treat D5c as optional.

## Finding 3 - `detect-vendor` routes (chunk E2)
Confirmed dead: nothing in unitprep-ui (`lib/`, `app/`, `components/`, `e2e/`, `types/`) calls `POST /dedup/detect-vendor` or `/dedup/detect-vendor-dropbox`; leftovers are `types/api.ts:223-229 DedupDetectVendorResponse` (no consumer), a stale comment at `lib/useSessionAction.ts:56`, and an untracked stale `coverage/` HTML. API side: routes `routes.rs:1167-1170,1187-1190` (both `RouteAccess::Authenticated`, so no permission/gate-test rows), handlers `dedup.rs:441-494,496-538`, response `:423-430`, one test `dedup_tests.rs:403-416`, doc comment `:288`, `CHANGELOG.md:487` (v1.8.9, 2026-08-17). History: built for the pre-Run-Check "Vendor: X, confirm" gate (UI `b8e5f35` 2026-08-20, Dropbox variant `351b443` 2026-08-28); UI stopped calling them in `632059d` (2026-10-01, dedup folder scan UI) when the API gained `/dedup/classify-files`, `/dedup/classify-dropbox-folder`, `/dedup/file-requirements` (`862c7cb`, `dedup_files.rs`) and the old handlers were left behind. The classify routes are a strict superset (multi-file, header-only so contents never upload, return status/format/pms/role/priority/suggested). The server re-detects in `/dedup/check` and `/dedup/import-dropbox` rather than trusting the client. Unit-group equivalent: `resolve_unit_format` + `discover/format_resolution.rs:33`. No ts-rs bindings, permissions, RLS rows or docs reference the routes. Nothing breaks (only a pre-2026-10-01 cached UI bundle would 404). **Recommendation implemented as chunk E2:** delete (A) plus the cheapest slice of improvement (B): `closest_vendor` + `missing_headers` on unrecognized files, label change in `DedupFileChecklist.tsx:34`; mapped/unmapped column preview and confidence scoring are later/optional (recognition is all-or-nothing by design).

## Finding 4 - Process Street client timeout claim: CONFIRMED
`src/process_street/client.rs:126-131` `pub fn new(config) -> Self { Self { http: reqwest::Client::new(), config } }` (no timeout, no connect timeout; constructed `src/main.rs:213`). Same in `src/dropbox/client.rs:133`. ClickUp sets a 15 s timeout (`clickup/client.rs:173`). (An earlier grep for `reqwest::Client::new` missed the PS one only because of search-pattern differences; two reviewers plus a targeted read agree.)

## Other judgement calls recorded
- **tower-http compression (A7):** confirm no reverse proxy already compresses; exclude ZIP/XLSX content types.
- **`pg_trgm` (A3):** defer until `ps_person_index` is large or search latency shows; record the decision when A3 is done.
- **Audit write inline after commit (56 sites):** optional idea (same-tx insert makes it atomic but changes swallow-the-error semantics; `tokio::spawn` can lose writes on shutdown). Not in the plan; raise with Boris if wanted.
- **Session cache and key caching:** NOT DOING, see above.
- **Things reviewers found already fine (do not chase):** no `Regex::new` in hot paths; dedup typo-variant pass already has the `could_reach_threshold` prune; unit-group analysis caches per distinct group name; audit PDF export already `spawn_blocking`; audit lists/exports/tool_runs use keyset paging; session-store expiry sweep uses read then short write lock; no lock held across `.await` except the intentional Dropbox token mutex; pool is 20 with `connect_lazy`; no unused Cargo dependencies; RLS policies are GUC-based with no per-row table subqueries.
