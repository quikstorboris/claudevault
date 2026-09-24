---
description: "Things that have bitten before and will bite again — pitfalls, edge cases, and testing traps"
tags:
  - brain
---

# Gotchas

Things that have bitten before and will bite again.

## A `.git` folder found inside a raw file-mirror backup may be empty

A backup folder having a `.git` directory doesn't mean it has history -- a byte-for-byte file mirror can carry an empty `git init` skeleton along with everything else. Confirm with `find .git/objects -type f | wc -l` or `git fsck` before trusting it as a source of history to recover. Full incident and the rest of the migration steps in [[Laptop Migration]].

## Verify a parser's real output by running it — don't re-derive it by hand from raw XML

Found 2026-08-14 while diagnosing why the Template Tagger found zero candidates in a real filled document (see [[2026-08-14-filled-document-field-detection-shipped|Filled-document field detection]]). Manually extracting `<w:t>` text from `first_late_notice.docx`'s raw `document.xml` with a quick Python regex made it look like `docx_surgeon::read_docx` concatenates paragraphs with **zero separator** ("...SERVICE300 RODGERS BLDG..." — no space, no newline) — which would have meant a real, invasive change to `docx-surgeon`'s core text-flattening model was needed before any label-boundary detection could work on free text at all.

That was wrong. Actually running `read_docx` against the same file (via a throwaway `#[ignore]`d test, `println!`-ing the real `FlatText`) showed paragraphs genuinely ARE joined by `\n` — confirmed by the crate's own doc comments and existing tests (`separates_paragraphs_with_a_newline`), which a plain grep for "paragraph" would have surfaced immediately. The manual regex extraction simply didn't replicate what the real parser does (it doesn't insert the separator the parser does), so it produced a plausible-looking but false signal about the actual data shape.

**How to apply**: before concluding "the flattened/parsed output has property X" from reading raw source by hand, run the actual parser (a throwaway test is fine) and inspect its real output — especially before scoping a fix around the absence of something the parser might already provide. A wrong assumption here nearly triggered a much bigger, unnecessary change than the real fix needed.

## `ts-rs`'s `export_to` path resolves relative to a hidden `./bindings/` default, and differs by which crate's test binary triggers the export

Found 2026-09-23 in `unitprep-api` while wiring `ts-rs` to generate `unitprep-ui`'s tool-session response types (see [[Session 2026-09-23 — GatedRouter Permission-Gate Manifest, Audit-Log Commit Ordering Fix & Cross-Repo Type Generation]]). A per-type `#[ts(export, export_to = "../../unitprep-ui/types/generated/")]` (2 `..`, empirically correct for a type in the main crate's `src/api/upload.rs`) worked for `UploadResponse`/`ValidateResponse`/`AnalyzeResponse`, but the exact same 2-`..` value on `DiscoverResponse` in `src/api/discover/dto.rs` silently produced no output file at all — no error, no panic, test reported `ok`.

**Root cause, found by reading `ts-rs-macros`' own source, not the docs**: `export_to`'s value is stored verbatim as `output_path()` — no `CARGO_MANIFEST_DIR` involved at the macro level. The actual write path is `Config::out_dir()` (default `"./bindings"`, overridable via `TS_RS_EXPORT_DIR`) joined with each type's own `output_path()`. So the working 2-`..` value was actually resolving as `<cwd>/bindings/../../unitprep-ui/...` = `<cwd's parent>/unitprep-ui/...` — coincidentally correct for types in the main crate, but **when `DiscoverResponse`'s `export_all()` call recursively re-exported its dependency types (`UnitFileCandidate`, `FieldMappingEntry`, from the separate `unit-group` crate, configured with 3 `..` for *their own* crate's CWD context) from *this* crate's test process, those dependency types' paths resolved from the wrong base** — landing one directory too shallow (`~/unitprep-ui/` instead of `~/Development/unitprep-ui/`), and something in that partial-failure path caused the whole batch (including `DiscoverResponse` itself) to silently not write.

**Fix, and the actually-robust pattern**: don't hand-compute per-type relative `../../` paths at all. Use bare `#[ts(export)]` (no `export_to`) on every type, and set `TS_RS_EXPORT_DIR` to an **absolute** path once, e.g. `TS_RS_EXPORT_DIR=/home/.../unitprep-ui/types/generated cargo test --workspace export_bindings`. This is deterministic and CWD-independent regardless of which crate's test binary triggers the export or how deep a dependency chain runs. Wrapped in `unitprep-ui`'s own `npm run generate-types` script so nobody has to remember the exact invocation.

## `@testing-library/user-event`'s `setup()` installs its own `navigator.clipboard` stub, clobbering one set up earlier

Found 2026-09-23 in `unitprep-ui` writing a copy-button test for `SecretField.tsx` (see [[Session 2026-09-23 — Frontend Test Coverage Priorities 1-4 (Auth, Admin, API-Client Libs, Facility Policy Tabs)]]). A `beforeEach` that did `Object.defineProperty(navigator, "clipboard", { value: { writeText: vi.fn() } })` before each test, then called `userEvent.setup()` inside the test body, silently never saw its own stub invoked — `writeText` had 0 calls even though the button's real `onClick` handler unquestionably ran.

**Why**: `userEvent.setup()` installs its own `navigator.clipboard` stub internally (to back its own `user.copy()`/`user.paste()` API), which runs *after* the `beforeEach` and overwrites it.

**Fix**: call `userEvent.setup()` first, *then* stub `navigator.clipboard` — order matters, and a stub set up in a shared `beforeEach` that runs before any test's own `userEvent.setup()` call will always lose.

## Postgres RLS: `SELECT ... FOR UPDATE` is governed by the table's UPDATE policy too, not just its SELECT policy

Found 2026-08-13 in unitprep-api while writing a real concurrency test for [[Key Decisions|the last-active-admin lock fix]]. `auth.roles` has a permissive SELECT policy (`roles_select_authenticated` — any authenticated caller) and a separate, admin-only UPDATE policy (`roles_update_admin_only`). A plain `SELECT id FROM auth.roles WHERE key = 'admin'` under a non-admin's RLS context returns the row fine. The exact same query with `FOR UPDATE` added returns **zero rows** for that same non-admin caller — a hard `RowNotFound`, not a graceful denial, and no error naming RLS as the cause.

**Why**: Postgres treats acquiring a row lock as a preliminary step toward a possible future update, so `FOR UPDATE`/`FOR SHARE` checks the row against the relevant UPDATE (or DELETE) policy in addition to the SELECT policy — even though nothing about the statement itself is an UPDATE. This is genuinely confusing because the query *looks* read-only.

**Practical implication**: any helper that does `SELECT ... FOR UPDATE` against an RLS-protected table must be called from a transaction whose RLS context (role/permission GUCs) actually satisfies that table's UPDATE policy, not just its SELECT policy — even if the helper's own job is just reading and locking, never writing. Confirmed by direct reproduction: same GUC setup, same query, only the presence of `FOR UPDATE` changed the row count from 4 to 0.

**How to verify this class of bug directly**: reproduce via `psql` as the real application role (not the owner), setting the same `app.current_user_*` GUCs the real code path sets, then compare the row count with and without `FOR UPDATE` on the identical query.

##### How this is known

Reproduced directly on unitprep-api's dev database: `SELECT id, key FROM auth.roles` with `app.current_user_id` set (no admin role) returned all 4 rows; `SELECT id FROM auth.roles WHERE key = 'admin' FOR UPDATE` under the identical GUC setup returned 0 rows. Adding `admin` to the RLS context's role set fixed it immediately, confirmed via a real two-connection concurrency test that then passed.

## WSL: `bash -lc` doesn't reliably source `nvm`, so `npx` silently runs the Windows toolchain instead

Found 2026-08-14 verifying [[2026-08-14-milestone-5-dry-consolidation-shipped|Milestone 5]]'s frontend work. On this machine, `unitprep-ui`'s real Node is installed via `nvm` (`~/.nvm/versions/node/v24.18.0/bin`), but `wsl.exe -e bash -lc "cd <repo> && npx tsc --noEmit"` does not reliably run the `.bashrc` lines that source `nvm.sh` for this invocation shape. `PATH` then falls through to the Windows Node install at `/mnt/c/Program Files/nodejs`, so `npx` resolves to Windows `npx.cmd`. That shells out via `cmd.exe` with the WSL path translated to a UNC path (`\\wsl.localhost\...`), which real `cmd.exe` rejects outright.

**Why this is dangerous rather than just broken**: the failure is silent. `npm`/`npx` doesn't error loudly on the UNC-path failure — it falls back to fetching a placeholder joke package (literally named `typescript`, prints a Star Wars pun) from the registry and runs *that* instead of the real local `tsc`. The command exits 0-looking, `tsc --noEmit` appears to run, and nothing in the output says "wrong toolchain" — it just silently didn't check anything. Hit independently twice in the same session: once from a direct `wsl.exe` invocation, once inside a subagent's first attempt, before either noticed.

**How to avoid it**: never trust bare `npx`/`npm` output from a `wsl.exe -e bash -lc` invocation on a machine where Node comes from `nvm`. Prepend the real bin dir explicitly in the same command string and confirm the version inline:
```
wsl.exe -e bash -lc 'export PATH="$HOME/.nvm/versions/node/v24.18.0/bin:$PATH" && node --version && cd <repo> && npx tsc --noEmit'
```
If `node --version` doesn't print the expected `nvm`-managed version, the rest of the command's output cannot be trusted. This generalizes beyond `unitprep-ui`: any Windows-hosted session invoking a WSL repo's npm toolchain via a fresh non-interactive `bash -lc` should assume PATH is wrong until proven otherwise, not the other way around.

**Same root cause hit again 2026-08-21, different symptom, on the new laptop (`QSLP14`)**: a bare `node`/`npm` in a fresh `bash -lc` wasn't silently wrong here, it was simply `command not found` — this distro's `nvm` isn't loaded by `.bashrc` in a way a non-interactive `bash -lc` picks up at all, so there was no Windows fallback to silently mask (no Windows Node was even installed on this machine). Same fix, explicit every time: `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"` before any `node`/`npm`/`npx` call. See [[New Laptop Migration — QSLP14]].

## This laptop has ~2GB of RAM headroom — local model inference and the vault's own test suite will freeze it

Established 2026-07-30 by freezing the machine hard enough to need a cold reboot.
Read this before running anything heavy.

> [!warning] This is `QSLP15`. As of 2026-08-21 Boris is on a new machine, `QSLP14` — everything below is unverified for it.
> Not re-established from scratch here; the **standing rules** (no full vault test suite, no unbounded `qmd` reranking, no local model servers) are cheap enough to keep following regardless of hardware, so they still apply below. But the specific hardware facts (Dell Latitude 5550, 16GB RAM, no dedicated VRAM, the exact freeze cause) describe the *old* machine and should not be assumed true of the new one. What's actually known about `QSLP14` so far, from WSL's own view only (not full Windows host telemetry — `(TBC)`): 15GB RAM visible to WSL2, 22 logical CPUs, ~13GB free at the time it was checked. Whether it has the same low-RAM-headroom problem is genuinely unknown — re-verify before assuming either way, and update this note (not just this callout) once it is.

**The hardware**: Dell Latitude 5550, Intel Core Ultra 7 155U (a low-power
U-series part), **16GB RAM**, Intel integrated graphics with **no dedicated
VRAM**, and an NPU that nothing in this stack can currently use.

**The constraint that actually matters**: at idle, minutes after a reboot, this
machine runs at **86-87% memory used — roughly 2GB free**. Not because anything is
broken; it is WSL (~700MB, and it grows), Telegram (~590MB), three `claude`
processes at ~400MB each, Defender, and Chrome. There is no single hog to kill.
So *any* multi-GB allocation goes straight to swap, the NVMe pins at 100%, and the
machine stops responding rather than merely slowing down.

**What caused the freeze**, all concurrently: a `cargo build`, the vault's
1183-test suite (which spawns dozens of node subprocesses in parallel), and qmd
benchmarking that loaded three GGUF models — a 1.7B expansion model, a 0.6B
reranker, and a 300M embedding model.

### Standing rules earned from it

1. **Never run the vault's full test suite** (`.claude/scripts/tests/`). It is the
   obsidian-mind *template's* own suite — not this vault's note content, and not
   UnitPrep's. Nothing auto-runs it: no hook, no CI. It executes only because
   someone chose to. After editing a template file, run **only that file's
   test** — two files was 65 tests in ~1.2 seconds. If a full run is ever
   genuinely required, use `--test-concurrency=2` with nothing else running.
2. **Never invoke `qmd query` from the CLI without `--no-rerank`**, and never
   benchmark it. That is what loads the big models. See
   [[Gotchas#`om search` timed out on every novel query because LLM reranking is unbounded on a CPU-only machine]].
3. **No local model servers. Ollama was fully removed 2026-07-30** — uninstalled
   via `winget uninstall Ollama.Ollama`, `~/.ollama` deleted (3.68GB of
   `qwen2.5-coder:3b` and `llama3.2:latest` reclaimed), its Startup shortcut
   deleted, and the now-dead `ocx-llama3-2-latest` agent definition removed from
   `~/.claude/agents/`. Idle it only cost ~100MB, so it was not the drain — it was
   the *risk*: the moment a 2GB model loaded there was no headroom left. Boris's
   decision, and it should not be reinstalled on this machine. The four
   `ocx-gpt-5-*` agents are unaffected; they route to remote models and cost this
   machine nothing.

   **Do not propose local models here again** — not ollama, not llama.cpp, not
   GPU or NPU offload. The memory arithmetic does not work, for the reasons under
   "Hardware facts" below.
4. **Don't leave a dev server running** after verifying something. A stale
   `unitprep` binary on port 8080 both consumes memory and has now twice produced
   a *false* verification result by answering probes with pre-fix code.
5. **WSL is capped** as of 2026-07-30 via `C:\Users\bmaksimov\.wslconfig`: 6GB
   memory, 2GB swap, and `autoMemoryReclaim=gradual` under `[experimental]`. The
   reclaim setting is the one that matters — WSL grows to hold page cache and does
   not return it eagerly, which on this machine is indistinguishable from a leak.
   The cap itself is deliberately generous: Rust is CPU-bound rather than
   memory-bound and `unitprep-api` sits under 1GB idle. **Changes need
   `wsl --shutdown` to take effect**, which kills any open VS Code remote session,
   so it was left to apply on the next natural restart.

### Hardware facts worth not re-deriving

- **The three different GPU memory numbers all describe one pool.** System > About
  says 128MB (the OEM's fixed framebuffer carve-out), dxdiag says 2.00GB (a
  clamped legacy WDDM value, meaningless for an iGPU), Task Manager says 8.8GB
  *shared*. Task Manager is the honest one: the iGPU dynamically borrows up to
  about half of system RAM. **Shared GPU memory IS system RAM**, so offloading
  model layers to the iGPU relieves nothing — it moves the same pressure into the
  same 16GB and adds a consumer.
- **The NPU (Intel AI Boost) cannot be used here.** qmd runs on llama.cpp, whose
  backends are CPU/CUDA/Metal/Vulkan/SYCL — there is **no NPU backend**. Intel's
  NPU is reachable only through OpenVINO, a different inference stack, so using it
  would mean porting qmd's inference layer and converting each model to OpenVINO
  IR with NPU-compatible quantization. It is not a config flag. Don't propose it
  again without that context.

## This vault's own test suite has two load-sensitive integration tests — a red run is not necessarily a broken vault

Observed 2026-07-30. `.claude/scripts/tests/qmd-refresh.integration.test.ts` fails in the **full-suite** run while passing **13/13 in isolation**, consistently in both directions. The failing case (`sentinel is bumped when qmd resolves`) takes **~900ms alone and ~5000ms under full-suite parallelism**. `classify-message.test.ts`'s subprocess cases showed the same shape earlier the same day (88ms alone, 2237ms under load) but that one recovered on a re-run.

What is known, stated without overclaiming: both tests spawn real subprocesses and do real qmd work, so their duration scales with vault size and machine load. The suite was green (1183/1183, twice) earlier the same day, and the vault grew from roughly 80 to 88 notes in between. The correlation is with **vault size plus parallel load**, not with any note's content being wrong — no assertion about vault *data* is failing.

**How to triage rather than panic**: run the suspect file on its own first. If it passes in isolation and the failing case's duration is an order of magnitude above its solo time, it is this. Do not "fix" it by editing notes; nothing about the content is wrong. A genuine content regression shows up in `vault-wikilinks.test.ts` or the frontmatter validator, and fails in isolation too.

**Worth actually fixing when someone has an appetite for it** — a suite that is normally-red trains everyone to ignore it, which costs more than the tests are worth. The honest options are to give those integration tests a load-tolerant timeout, mark them serial rather than parallel, or move them out of the default run into an explicit integration target.

> [!note] Status 2026-07-30: green twice, cause plausibly removed, not declared fixed.
> After LLM reranking was disabled in `om`'s search path (see
> [[Gotchas#`om search` timed out on every novel query because LLM reranking is unbounded on a CPU-only machine]]),
> the full suite ran **1182/1182 twice consecutively** and this file passed
> **13/13 in isolation**. CPU contention from reranking is a plausible shared
> cause — that is *inferred*, not established. Two green runs do not retire a
> load-sensitive flake. If it reappears, the triage above still applies.

## `om search` timed out on every novel query because LLM reranking is unbounded on a CPU-only machine

Diagnosed and fixed 2026-07-30. Every `om search` call failed with
`search failed: qmd timeout on tools/call`. The wiring was fine — `health`
reported no warnings, the index was healthy (88 files, 420 vectors) — because
nothing was broken in the sense that word usually means. The search was simply
slower than the client would wait, **every time the query was one nobody had run
before**.

**The measurements**, all against this vault on this machine:

| what ran | cold / novel | repeat of the same query |
|---|---|---|
| `query` (full pipeline) | **110s** | 7.1s |
| ├─ query expansion (HyDE, 1.7B model) | 28.5s | 0ms |
| ├─ embedding | ~4-5s | ~5s |
| └─ **reranking 22 chunks** (0.6B cross-encoder) | **75.1s** | 4ms |
| `query --no-rerank` (novel) | 15s | — |
| `vsearch` (vector only) | 7.5s | — |

Against `CALL_TIMEOUT_MS = 45_000` in `lib/mcp-qmd-client.ts`, a novel query
could not finish. Reranking alone is ~2s **per candidate** and the default
candidate limit is 40.

**The part that makes this genuinely deceptive: qmd caches expansion output and
rerank scores per query.** So the same query re-run returns in seconds, which is
why the failure reads as intermittent flakiness and why "retry it" appeared to
be a working remedy. It is not flaky. It is deterministic, keyed on whether that
exact query has been asked before — and the *first* ask is the one that matters,
because that is the one you actually needed answered.

**Why the machine matters, and why this is not fixable by tuning.** These are
local GGUF models under llama.cpp, and this box has Intel integrated graphics
only — no discrete GPU — so all three stages are CPU inference on 14 cores.
qmd's own tool description says, of `rerank`: *"Set to false for faster results
on CPU-only machines."* The hardware is the constraint, not the configuration.

**The fix**: `rerank: false` in `qmdSearch`'s arguments
(`lib/mcp-qmd-client.ts`). Retrieval quality is not thrown away with it —
`om` already sends both a lexical and a vector sub-query (`subQueries`) which are
fused; reranking only *reorders* that candidate set, it does not produce it.
Verified after the change with a novel query, which returned immediately with a
91% top hit that was exactly the right note.

**Raising the timeout was considered and rejected.** It is the obvious move and
it is a crutch: it converts "search fails" into "search blocks the agent for two
minutes", and it would have hidden the fact that the cost is per-candidate and
therefore grows with the vault. Boris's call, and the right one.

**What this probably also explains** (marked inferred, not verified): the
load-sensitive integration test above. Both spawn real qmd work, and CPU
contention from reranking is the kind of thing that only bites under
parallelism. The full suite has since run green twice (1182/1182) and the
previously-failing file passes 13/13 alone — but two green runs do not retire a
load-sensitive flake, so treat it as improved-and-watch, not fixed.

**Standing note**: the fix is template code, so per the mirroring rule below it
was copied to `.shardmind/templates/.claude/scripts/lib/mcp-qmd-client.ts` in
the same pass; the two are byte-identical.

## `qmd` was never actually installed, and `om search` silently drops any note path with punctuation

Two separate, unrelated failures were both hiding behind the same symptom (`search failed: qmd timeout on tools/call` / "qmd launcher exited"), diagnosed 2026-07-29:

**1. `@tobilu/qmd` wasn't installed at all.** `npm ls -g @tobilu/qmd` was empty and `~/.cache/qmd/` didn't exist — `health`'s "launcher found" was a false positive (it doesn't verify the binary actually resolves). Fix: `npm i -g @tobilu/qmd`, then re-run `.scripts/qmd-bootstrap.ts` from the vault root. First real `query`/`embed` call downloads two local GGUF models (an embedding model, ~330MB, and a reranker, ~1.28GB) and can take 1-2 minutes — expected, not a hang.

> [!warning] The "just retry up to 3 times" advice that used to be here was wrong, and superseded 2026-07-30.
> It read the right symptom off the wrong cause. Cold model *download/load* is real and does happen once, but it is not why searches kept timing out — see
> [[Gotchas#`om search` timed out on every novel query because LLM reranking is unbounded on a CPU-only machine]]. Retrying "worked" because qmd **caches** rerank scores per query, so the second attempt at the *same* query was cheap. A retry of a *different* query timed out just the same, which is why search felt randomly broken rather than consistently slow. The fix is `rerank: false`, not persistence.

**2. `search`'s own path-matching silently drops any note whose real path contains punctuation qmd's indexer strips.** qmd's indexer (`handelize` in its `store.js`) collapses any run of characters that isn't a Unicode letter/digit/`$` into a single hyphen per path segment — so `Auth & Persistence/Phase 2 Progress.md` is reported in `structuredContent.results[].file` as `Auth-Persistence/Phase-2-Progress.md`. The `om` server's own `pathKey` (`.claude/scripts/lib/mcp-qmd-client.ts`) only collapsed whitespace, not other punctuation — so the two keys never compared equal and the note was reported as "withheld: outside this repo's scope" **even though it genuinely was in scope**. This is silent and permanent: the note stays readable via `expand`/resources, just invisible to `search`, so it looks like a scoping decision rather than a bug. Fixed by making `pathKey` replicate qmd's `handelize` exactly (per-segment collapse, extension-preserving on the filename) — see the fix and its regression tests in `mcp-qmd-client.ts`/`mcp-qmd-client.test.ts`.

**Why this generalizes**: any obsidian-mind vault using this `om`/qmd template will hit failure 2 the moment a note or folder title has an `&`, parentheses, a comma, or similar — not exotic, e.g. this vault's own `work/active/UnitPrep/Auth & Persistence/` folder was affected.

**Regression-proofed 2026-07-29.** The fix lives in template code, not vault content, so a template re-apply would have silently reverted it. There is no git remote on this vault to push upstream to — but the template is *vendored inside the vault* at `.shardmind/templates/`, which is what `/om-vault-upgrade` applies from, so that vendored copy is the thing that would clobber a fix. Both `lib/mcp-qmd-client.ts` and `tests/mcp-qmd-client.test.ts` are now byte-identical between `.claude/scripts/` and `.shardmind/templates/.claude/scripts/`, and the 34 regression tests pass when run against the template copy directly. **Standing rule this earned: any fix to `.claude/scripts/` must be mirrored into `.shardmind/templates/.claude/scripts/` in the same pass, or it is a fix with an expiry date.**

**Live-fix caveat**: editing `mcp-qmd-client.ts` does not affect the already-running `om` MCP server process (Node doesn't hot-reload). The MCP connection must be restarted (reconnect the server, or restart the session) before a fix like this takes effect — confirmed by re-running `search` post-edit and seeing the same stale withholding until restart.

## UnitPrep has no auth by design — don't flag it as a surprise finding

`unitprep-api` and `unitprep-ui` currently have no authentication or authorization anywhere — any client that can reach the API can create, read, correct, and export any session if it knows/guesses the session UUID. This is called out in both READMEs as an accepted, deliberate gap for the current internal, single-operator usage pattern, not an oversight.

**Why it looks like a bug but isn't:** an independent architecture review (run through Grok, 2026-07-15) reached the identical conclusion unprompted — no auth, UUID-only session ids, full session data in memory, acceptable for single-operator internal use, blocking for client-facing/multi-user. Two independent reviews landing on the same assessment is corroboration this is a correctly-scoped decision, not a blind spot. Boris asked for this specifically to be logged as project history and called out later rather than fixed at the time.

**How to apply:** don't raise this as a surprise security finding in reviews of this codebase. Do flag it if scope is about to change (client-facing access, deployment beyond internal use) — that's the stated trigger for revisiting it. The trigger fired 2026-07-20: real auth planning is now underway (see [[UnitPrep Architecture Overview]] and the auth workstream notes under `work/active/UnitPrep/Auth & Persistence/`), driven by needing user roles for an admin panel. Nothing was built as of that date, still pure architecture/design — this guidance still applies to the *current, unchanged code* until that work lands.

## A stray, unexplained git branch cost two days of review accuracy

2026-07-23: a branch `claude/orchestrator-db-organization-psnq8b` was found on `unitprep-api`'s GitHub origin, containing one commit authored/committed as `Claude <noreply@anthropic.com>` — not Boris's own git identity, and not created by the session that found it. It sat unmerged and diverged from `main` for part of a day. A full-codebase review done from that branch's checkout missed two full days of real feature work (dedup note-copy rework, multi-vendor discovery) that had already landed on `main`, and undercounted the test suite by ~30 tests as a result.

**Why it matters beyond the one incident:** the branch's origin was never conclusively identified (no scheduled task/cron in the account explains it, `gh` wasn't authenticated to check further). It was cherry-picked onto `main` and the orphan branch deleted. See [[Patterns]] for the resulting standing rule (main-only, no incidental branches).

**How to apply:** before trusting a "full codebase review" or similar audit, confirm it actually ran from `main` and that `main` is what you think it is — a checkout on any other branch can silently be stale relative to real shipped work, with no obvious symptom until counts (tests, files, features) don't add up.

## UnitPrep "sibling" hooks/components don't stay in sync on their own — a fix to one needs an explicit check of its documented mirror

Happened twice across two consecutive passes: `useSessionAction`/`useSessionPost`'s `sessionExpired` reset asymmetry (fixed in [[Fourth Pass - File Splits, Concurrency Fixes, Dead Code Removal]]), then `useExportDownload`/`useDedupExport` — the latter's own doc comment says "Mirrors `useExportDownload`" and was still missing both of that hook's stale-state and reentrancy fixes a full pass later (caught and fixed in [[Fifth Pass - Adversarial Review Findings Fixed]]).

**Why it keeps happening:** this codebase has several deliberately-duplicated "sibling" hooks/components (one per tool — Group Prep vs. dedup) that share a shape and a comment claiming parity, but are separate files with no compiler or lint check enforcing they actually stay identical. Fixing a bug in one doesn't touch the other; nothing fails if they drift.

**How to apply:** whenever fixing a bug in a hook/component that has a documented "mirrors X" / "same as X" sibling, explicitly go read the sibling and check whether it has the identical gap — don't assume a doc comment claiming parity means it's actually still true. When reviewing this codebase, grep for other "mirrors"/"sibling"/"same as" comments and verify each pair before assuming parity holds.

## Column-level UPDATE grants will silently doom a direct SQL UPDATE on a restricted column, at runtime, invisible to lazy-pool unit tests

Caught in review 2026-08-04, before it shipped: an early draft of a
"reissue an invite" code path re-applied a user's role via a raw `UPDATE
auth.users SET role = ...` inside an RLS transaction. `unitprep-api`
deliberately holds `role` outside `app_service`'s column-level UPDATE
grant (`restrict_users_update_columns` names it explicitly as "the
escalation vector that migration exists for") — every other role/status
change goes through a `SECURITY DEFINER` function
(`auth.set_user_role`/`auth.set_user_status`) specifically because a
direct UPDATE on that column is refused at the grant layer, independent
of RLS. The draft would have compiled clean and passed the whole test
suite (it uses a lazy, never-actually-connected pool, so no SQL runs) and
only failed against a real database, with a permission-denied error that
looks like an RLS problem, not a column-grant one.

**How to apply**: before writing (or accepting in review) any new direct
`UPDATE auth.<table>` in this codebase, check the column list against
that table's own grant migration (`restrict_users_update_columns` for
`auth.users`) — column-level grants aren't visible in the RLS policy
definitions, and this project's own unit-test style (lazy pool,
unreachable by design) cannot catch this class of mistake at all, so it
has to be caught by inspection.

## A one-off backgrounded shell command does not reliably survive past that single tool call — use the harness's own backgrounding, not nohup/disown

Tried twice 2026-08-04/05 while spinning up a throwaway `unitprep-api`
instance on a spare port to verify changes without touching Boris's
already-running dev server. `wsl.exe -e bash -lc "... &"` plus
`nohup`/`disown`/`setsid` inside that one command did not keep the
process alive once the tool call itself returned — the next poll found
nothing listening. What actually worked: passing `run_in_background:
true` to the calling tool itself (rather than backgrounding manually
inside the command string), which persisted the process correctly across
separate subsequent tool calls.

**A related, cheaper mistake from the same session**: redirecting a
verification server's stdout to a conventional-looking log path
(`/tmp/unitprep-api.log`) collided with the *same* path Boris's own
already-running server had open — a plain `>` redirect truncates the
underlying inode even for a process with an already-open file descriptor
to it, so the truncation landed on the live process's log, not a fresh
file. Harmless here (ephemeral tracing output, not the audit database),
but the fix is cheap: give any throwaway verification process a
port-or-PID-suffixed log path, never a path that might already be in use
by something real.

## Process Street's "sister site" sharing has no definitive link between facilities — do not assume the "first-time" facility is always resolvable

Found 2026-08-28 designing the [[Process Street Integration — Kickoff & Findings|OO x Process Street integration]]. Multi-facility companies get a separate Intake/Progress run per facility, gated by a field `"Is this their first time filling out this form?"`. Confirmed via Prairie Enterprises' 3 real facilities: Highway 20 answered "Yes" and has full real Corporate Info/Fees/Liabilities/Tax/DLQ/Commission/Coverage data on its own run; Carpentersville and Pyott Road both answered "No" and have `null` in every one of those same fields on their own runs. **PS stores no field linking a "No" facility to the actual sister run that has the data** — it's tribal knowledge only a human onboarding rep holds, not a resolvable API relationship.

> [!danger] Don't forget this fact about PS itself, even though OO's own design no longer depends on resolving it (see the 2026-08-28 follow-up below)
> **Not yet observed**: what happens when a "No" facility answers "Yes, this facility uses different Fees/DLQ" than its sister. Does PS then re-populate that facility's own fields fully, partially, or not at all? Every real example checked so far — Beau Ryan's 9 facilities, the Fortra Storage 8-facility cohort, and 2 of Prairie Enterprises' 3 facilities — had that step genuinely still `NotCompleted`, so this override path has never actually been observed with real data. Relevant again only if OO ever tries to auto-infer sharing directly from PS instead of via its own explicit copy action.

**How to apply**: when this is picked back up, find or wait for a real completed example where a "No" facility diverges from its sister on one category, and confirm the actual PS behavior before finalizing any resolution logic. **Superseded 2026-08-28** — see the follow-up below: [[Client & Facility Schema (Process Street-Sourced)]] no longer tries to infer PS's own sharing at all, so this specific override-path question stops being a live design risk for OO (it remains true and worth keeping as a fact about PS itself, just not something OO needs to resolve).

**Confirmed NOT subject to this gap**: the "Owner/District Manager/Manager Level Users" free-text fields ARE copy-pasted verbatim onto every facility's own run regardless of the first-time flag (byte-identical text confirmed across 2 Beau Ryan facilities) — different people can manage different facilities under one company, so this category was never a single-source problem the way fees/tax/DLQ/coverage are.

**2026-08-28 follow-up**: Boris raised a sharper version of this risk — that shared fee/tax/DLQ/coverage data might be captured on the first-filled facility as **free text naming which specific sister facility each item applies to**, not as clean structured data at all. Checked directly against Prairie Enterprises: could not confirm or deny this, because Carpentersville and Pyott Road's relevant fields are genuinely blank (that step hasn't been reached), not populated with differentiating prose. But real evidence for the underlying risk turned up anyway on Highway 20's own (completed) run: `Delinquency Notes:` is literally `"SEE FEE INFO FIELDS"` — a human using a notes field as an internal pointer rather than a fixed value — and `Any Other Fees:`/`Specials:` are long free-text blocks meant to be read as prose, not parsed as single values.

**2026-08-28, later same day — OO's design sidesteps this rather than resolving it**: Boris confirmed DLQ policies vary across sister facilities just as often as Taxes do (Prairie being uniform is one observed case, not a rule). Rather than trying to automatically infer which facility is the "real" source, [[Client & Facility Schema (Process Street-Sourced)]] dropped the shared-row model entirely — every facility now owns its own Fees/Taxes/Delinquency/Coverage/Specials data independently, always, and "sharing" is an explicit, per-category, one-time "Same for each facility" copy action a human triggers deliberately (with a source-facility picker and an overwrite warning), not something OO infers from PS automatically. **This means the PS-side ambiguity documented above no longer blocks or risks OO's own correctness** — kept here purely as a fact about how PS itself behaves, in case PS data is ever read more directly again, not as a live design risk.

## Process Street's "Owner Level Users" free-text field has at least two genuinely different human-entered formats in production

Found 2026-08-28 building [[Client & Facility Schema (Process Street-Sourced)|Phase 1 ingestion]]. Beau Ryan's facilities use one comma-separated line per person (`"Beau Ryan, beau@rockspring.com, 832-978-3228"`). Prairie Enterprises' Highway 20 uses a completely different multi-line-per-person, blank-line-separated format (name on its own line, then an email sometimes prefixed `"Primary: "`, sometimes a second email, then a phone, then a blank line before the next person). A parser assuming either format alone silently mis-splits the other — the first version of `clients::people::parse_people_block` (assuming the comma format) turned Highway 20's 3 real owners into 10 garbage single-line "people."

**How to apply**: `parse_people_block` now detects format per paragraph-like chunk (splits on blank lines first, then checks whether every line in a chunk contains a comma before deciding whether to treat each line as its own person or the whole chunk as one multi-line person). Confirms Boris's own instinct from this same conversation that this needed a real comb-through across sample clients rather than assuming one universal shape — this is that comb-through's first real finding. Don't assume a third format won't show up in a client not yet examined.

## Process Street's `GET /workflow-runs` defaults to `status=Active` only — silently hides most real data

Found 2026-08-31 chasing down Contract Order runs for two real, known clients (Tri County Mini Storage, Dubuqueland Mini Storage) that a straightforward by-name search across all "Active" Contract Order runs simply couldn't find — both names were absent from every one of the 22 runs the default listing returned. Confirmed directly: `status=Completed` immediately surfaced both (`Order for Tri County Mini Storage`, `Order for Dubuqueland Mini Storage`), and a further probe (`status=Archived`) surfaced 20 more Contract Order runs never seen before either. Valid status values, confirmed by testing each: `Active`, `Completed`, `Archived`, `Deleted` — `Stopped`/`Paused`/`Cancelled`/`Canceled` all return a 400 `Invalid status`, and `status=all` is not a real value either (also 400).

**Why this is dangerous rather than just an obvious filter**: nothing about the API response signals that anything was omitted — no warning, no total count, no indication a filter is even in effect. A workflow like Contract Order marks its runs `Completed` once the order is processed, so this default silently returns almost none of them for exactly the workflow where "find the run for this client" matters most. Every earlier inventory taken this session for Intake/Progress (83 runs) and New Merchant Account (41+ runs) was very likely ALSO Active-only and therefore incomplete in the same way, just never caught because the specific clients checked happened to still be Active.

**How to apply**: any code that lists or searches `/workflow-runs` for a true inventory must query across `Active` + `Completed` + `Archived` explicitly and merge the results (not `Deleted` — that's genuinely gone). Fixed in `src/process_street/client.rs::ProcessStreetClient::list_workflow_runs`, which now does this internally rather than leaving it to every caller to remember. If a byname/by-client search anywhere in this integration ever comes back empty for a client Boris says exists, check this first before concluding the client genuinely has no data for that workflow.

## Process Street's real API rate limit is undocumented publicly, but the live headers reveal it: 2,500 requests/API-key/hour

Found 2026-08-31 while diagnosing why the first-ever person-index sync took a very long time. PS's own docs, help center, and every third-party integration guide checked (Rollout, Stitchflow) confirm the rate limit is not published anywhere. But every real response — success or error — carries the actual numbers in its headers regardless: `X-Api-Key-Rate-Limit-Limit: 2500` / `X-Api-Key-Rate-Limit-Remaining` / `X-Api-Key-Rate-Limit-Reset` (a ~1-hour rolling window), and a separate, much more generous `X-Ip-Rate-Limit-Limit: 1000` on a ~1-second rolling window (never the binding constraint in practice).

**Why this matters for this integration specifically**: a full first-ever sync needs roughly one request per ~20 fields per run (`/form-fields` paginates at a fixed ~20/page, ignoring `limit`), across every real run in a workflow. 348 real Intake runs alone came out to roughly 1,700–2,000 requests — most of the hourly budget before Merchant Account or Contract Order even start. `clients::sync` processes runs strictly sequentially (no concurrency) — slow, but this is very possibly what's kept it from tripping the 429 in the first place; parallelizing would still need to stay paced against this same 2,500/hour ceiling, so it would shrink wall-clock time only up to the point of fully saturating the budget, not by however many workers are added.

**How to apply**: if `clients::sync` (or anything else calling the PS API in a loop) is ever made concurrent, rate-limit it explicitly against ~2,500/hour per key rather than assuming PS will just 429 gracefully if exceeded — check the real headers on a live call first if the limit ever needs re-confirming, since it isn't written down anywhere PS controls.

## A background task shouldn't copy another task's "fire on startup" pattern without re-checking why that pattern existed

Found 2026-08-31 building the Process Street person-index sync (`clients::sync::start_background_sync_task`). Copied `client_ops::vendor_format::start_refresh_task`'s shape wholesale, including firing immediately on every server start (not just on its own schedule) — that task's own justification is that an empty vendor cache would otherwise block real request handling until the first tick. Never re-examined whether that justification applied to the new task before copying the behavior. It didn't: an empty person-search index just means fewer search results, nothing breaks. Confirmed as a real cost, not just a theoretical one: a restart-triggered first sync measurably slowed down an unrelated live test hitting the same dev database at the same time it was running.

**How to apply**: when reusing another task's shape (interval timing, retry behavior, fire-on-startup, etc.), check the reasoning behind each specific behavior, not just the shape as a whole — a pattern that's correct for the precedent's own constraints (blocking real requests) can be actively harmful for a superficially similar task with different constraints (a nightly batch job hitting a live third-party API with a real hourly rate limit, see the entry above). Fixed by switching `start_background_sync_task` to sleep until the next occurrence of a configurable wall-clock time (`client_ops.process_street_settings.sync_time`, default midnight UTC) instead of firing immediately + repeating on a fixed interval.

## `unitprep-ui` clients are frontend-only, browser-tab-scoped state

A "client" (name, contact info, Dropbox path, etc.) has no backend entity at all — it's stored in `sessionStorage` under `unitprep:clients` (see `lib/clients.tsx`), scoped per browser tab, and evaporates when the tab closes.

> [!warning] Correction, 2026-09-03
> This note originally said "there is no `POST /clients` endpoint and none is planned" — that's now wrong. `POST /clients` (`api::clients_create`) shipped in Phase 3 of [[Process Street Integration — Kickoff & Findings|the Process Street integration]] and creates a real `clients.companies`/`clients.facilities` row per selected facility. The `sessionStorage`-only *browser session cache* described below is a separate, still-real concern layered on top — the client list a given tab shows locally, refreshed from the real backend via `ClientsProvider`'s own fetch, not the source of truth itself anymore.

**How to apply:** navigating directly to a `/clients/[clientId]/...` route (e.g. in an E2E test, or a bookmarked/shared URL) without that client having been created in *that specific browser tab's* session shows the app's own "this client isn't in the current browser session" guard, not the actual page — this is correct, expected behavior, not a bug. Playwright tests reaching a client-scoped route need to seed `sessionStorage` via `page.addInitScript()` before navigating, matching the `Client` shape in `lib/clients.tsx`.

## Never hold a database transaction open across a live external API call

Found live, 2026-09-03, in `unitprep-api`'s Process Street integration -- twice, in two different endpoints (`api::clients_elavon`'s Elavon-tab "link" action, and the original `api::clients_create` "Add to OO" flow), both opening an RLS transaction (`begin_rls_transaction`) *before* fetching data from Process Street's live API, then doing the actual database write using that same still-open transaction afterward.

**What actually happened**: one of Boris's repeated "link" attempts left a Postgres backend sitting `idle in transaction` for 3+ minutes, holding a lock. Every other query needing that lock queued behind it -- including the session-resolution query behind `GET /clients` -- surfacing as a 36-second request, a 401, and "the client list looks empty" (the company row itself was never touched; it was just unreachable behind the stuck lock). Confirmed via `pg_stat_activity` (`state = 'idle in transaction'`, `wait_event_type = 'Lock'` on the blocked query) -- not inferred, directly observed on the real Neon dev branch. Fixed by killing the stuck backend (`pg_terminate_backend`) to unblock immediately, then restructuring both endpoints into three phases: (1) a short DB-only transaction for any fail-fast check, closed before any network call; (2) the live PS fetch, with *no* transaction open at all; (3) a fresh, short transaction opened only for the actual write.

**Why this is a real, recurring risk, not a one-off**: a slow third-party response, or the request's own client cancelling mid-flight, can both leave a transaction open indefinitely -- Postgres has no way to know the difference between "still working" and "orphaned," so it just keeps the lock. The window of exposure is exactly as long as the external call takes, which is entirely outside this codebase's control once PS is having a slow moment. A larger connection pool (see the very next entry) doesn't fix this — it can make the *symptom* rarer to hit immediately (fewer contended connections) while making an actual leak sit unnoticed for longer before something finally collides with it.

**How to apply**: before adding any code that does `begin_rls_transaction` (or `pool.begin()`) followed by a call to an external API (Process Street, Dropbox, anything not the local database), check whether the transaction genuinely needs to span the network call. It almost never does -- fetch first, write second, and only open the transaction for the write. If a live test suite exists for the endpoint (`#[ignore]`d tests hitting the real API + real Postgres, this codebase's own established pattern), a transaction-holding bug like this usually won't show up there either, since those tests don't model a slow/cancelled request -- this needs a live, real-usage check (`pg_stat_activity` for `idle in transaction`), not just a green test suite, to catch.

## Entity identity keyed on email alone breaks the moment two real people share one inbox

Found 2026-09-08 in `unitprep-api`'s Process Street integration, real Dubuqueland Mini Storage data. `clients.people` was found/created purely by `SELECT id FROM clients.people WHERE email = $1` in three separate call sites (ingest-time `link_person_to_facility`, the Users-tab "Add"/self-heal `upsert_person_and_link_to_facility`, and the frontend's own "already linked" match). This works fine when every person has their own address, and silently breaks when they don't: a real family-run client (the Soppe family) shares one inbox (`dubuquemini@gmail.com`) across several genuinely distinct owners. Every one of them collapsed into the *same* `clients.people` row -- whichever was processed first claimed it, every subsequent same-email person's own insert into `(facility, person, role)` silently hit `ON CONFLICT DO NOTHING`, and the row's stored name became whoever happened to be first in the raw source data, not any particular one of them reliably.

**Why this is dangerous rather than just an edge case**: nothing errors. The first person to claim the shared row looks completely correct. Everyone after them just silently vanishes from the roster (no error, no warning) and their name may later get silently reassigned to someone else's if a "self-heal"/refresh pass ever touches that row again.

**How to apply**: before treating a contact field (email, phone, anything meant to disambiguate people/entities) as a sufficient identity key on its own, ask whether the real-world data can have two genuinely distinct entities sharing that field's value -- a shared department inbox, a shared family email, a shared support alias. If yes, identity needs at least one more field (here: `(email, full_name)`, both case-insensitive) for *finding-or-creating*. Fixed in `clients::repository::link_person_to_facility`/`upsert_person_and_link_to_facility`.

**A subtlety worth keeping**: a "self-heal"/refresh pass that corrects a *known, already-identified* row (by its own id) is a different operation from *resolving* which row a new candidate belongs to, and needs different matching rules. Requiring an exact name match on the self-heal path would have broken its actual job (correcting a name that's already wrong, e.g. Sand-Sto's real "Irene Chen - (301) 787-9221" → "Irene Chen"). The fix here splits the two: `heal_person_in_place` corrects a known `person_id` directly (no re-resolution, so no ambiguity possible), while the "add a new candidate" path does the (email, name) resolution and only applies a same-email different-name self-heal correction when there is exactly one such candidate (unambiguous) -- two or more different-named candidates sharing that email+role is left alone rather than guessed at. Full writeup in [[Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap]].

## A missing CORS `allow_methods` entry makes every route using that HTTP method look like the server is down, not a permissions error

Found live 2026-09-08 in `unitprep-api`, trying to use a just-shipped "delete client" button. The browser reported a generic **"Could not reach the API server"** -- indistinguishable from the server actually being offline -- while the backend's own request log showed the `OPTIONS` preflight succeeding (200 status) with no follow-up `DELETE` request ever arriving at all. The server was healthy and simply never saw the real request.

**Why**: `tower_http::cors::CorsLayer::allow_methods([...])` in `router.rs` listed `GET/POST/PUT/PATCH` but never `DELETE`, even though several real routes use `.delete(...)` (facility-person unlink, Elavon unlink, client delete, role revocation). DELETE isn't a CORS-"simple" method (only GET/HEAD/POST with plain bodies are), so a browser always sends a preflight `OPTIONS` first and only sends the real request if that preflight's `Access-Control-Allow-Methods` response includes it. With DELETE absent from the list, the preflight succeeds (200) but implicitly refuses the actual method -- the browser silently drops the real request client-side. This had been silently affecting every existing DELETE route the whole time, not just the new one; it just took someone routing through a real cross-origin browser flow with DevTools/logs open on both sides to notice, since a direct-handler-call test (this codebase's own default test style) never goes through `CorsLayer` at all.

**How to apply**: whenever a new route is added using an HTTP method not already in active use elsewhere in the API (this codebase went a while with only GET/POST/PUT/PATCH before DELETE routes existed), check `CorsLayer::allow_methods` includes it *before* assuming a "could not reach the server"-shaped failure means the backend is actually down or misconfigured at the network level. A real HTTP-level regression test exists now (`http_integration_tests::a_delete_route_is_allowed_by_the_cors_preflight`) asserting a live preflight's `Access-Control-Allow-Methods` header actually contains the method under test -- confirmed by temporarily reverting the fix that it fails exactly this way (`git stash` the one-line change, re-ran, got `expected DELETE in Allow-Methods, got: GET,POST,PUT,PATCH`). Same class of bug as this file's own credentialed-CORS regression test above -- invisible to any test that doesn't route through the real `Router`. Full writeup in [[Session 2026-09-08 — Dubuqueland Live Bug Hunt, Person Identity Fix & CORS Delete Gap]].

## The application's own Postgres connection pool can be the bottleneck, not Neon or its pooler

Found 2026-09-03 in `unitprep-api` right after fixing the concurrency work described in [[Process Street Integration — Kickoff & Findings|the Process Street integration]]'s own session notes: making `api::clients_detail`'s Company/Facility Policies endpoints run several independent DB reads concurrently (`tokio::join!`, one connection each) barely helped -- `facility_policies` stayed at ~630ms, no better than before. `src/db.rs`'s own `PgPoolOptions` was capped at `max_connections(5)`, so with up to 7 concurrent transactions from one request, 2 of them simply queued for a free connection instead of running in parallel, undoing most of the fix. Bumped to 20 -- safe here specifically because `DATABASE_URL` is Neon's own pooled (`-pooler`) endpoint, itself a PgBouncer sitting in front of Postgres, built to absorb far more app-side connections than that.

**How to apply**: when a concurrency fix (parallel queries, parallel transactions) doesn't move latency the way the math suggests it should, check the actual connection pool size the app itself configured (`PgPoolOptions::new().max_connections(...)` or equivalent) before assuming the database or its infrastructure is the ceiling -- an app-level pool sized for the old, sequential access pattern silently caps any new concurrent one.

## Plain `bash source`/`grep` extraction of a value from `unitprep-api`'s `.env.local` silently truncates or empties it

Found 2026-09-09 in [[Session 2026-09-09 — Admin-Only Integrations Nav, integrations.manage Permission, and Editable Dropbox Settings]] while trying to run `sqlx migrate run` against the Neon dev DB. `.env.local`'s values are double-quote-wrapped (`KEY="postgresql://..."`) and some (Neon connection strings) contain an unescaped `&` in the query string (`?sslmode=require&channel_binding=require`). `source .env.local` in plain bash treats that `&` as a job-control operator mid-line, backgrounding the first half and silently never setting the real variable (`${#VAR}` came back `0` with no error). Capturing the same grep/cut/sed pipeline straight into a shell variable via `$(...)` inside one large multi-layered quoted command (Bash tool -> `wsl.exe` -> inner `bash -lc`) also came back empty more than once, even after fixing the `&` issue -- some other escaping loss through that specific chain, not fully root-caused.

**How to apply**: never `source` this file (or extract a value from it into a shell variable) directly for one-off shell use. Extract with `grep '^KEY=' .env.local | cut -d= -f2- | sed 's/^"//; s/"$//' > /tmp/value.txt`, redirected to a **file**, then read it back in a **separate, simple** command (`"$(cat /tmp/value.txt)"`) rather than trying to capture and use it in one composite command. Also: a stray prose comment elsewhere in this same file (documenting a since-replaced Neon pooler fallback) contains a real cleartext Postgres password inline, not on a `KEY=value` line -- invisible to any redaction that only matches `^VAR=`, and it leaked into a grep's tool output during this session before being noticed. Worth a cleanup pass on that file; until then, never grep/cat broad ranges of `.env.local` without redacting full lines, not just `=`-delimited ones.

## Absolute Storage Management is not a representative client -- don't use it as a design reference

Boris's own call, 2026-09-17: Absolute is "by no means a good example for anything... a very unique client implementation." Confirmed independently while designing better Merchant Account correlation -- both real Absolute examples checked (Milton Self Storage, Main Street Storage) submit their Merchant Account application as a PDF import rather than the normal interactive form (`What_Application_Type_Did_the_Client_Submit: "The client submitted a .PDF"`), which leaves **every** owner/signer/address/EIN/bank field blank -- there is no fallback signal to try for this subset, not just a weaker one. Same signer/contact (`shane.carlson@absolutemgmt.com`) appears across multiple unrelated real facilities, since it's the management company's own staff filling out the form, not the actual property owner -- a real, structural violation of the "shared person/email doesn't identify one facility" assumption most correlation logic (see the next entry) otherwise relies on.

**Good reference clients for this kind of design work instead**: **Prairie Enterprises**, **Dubuqueland**, **Affordable Storage (Beau Ryan)** -- normal interactive-form submissions with real owner/address data, multi-facility structure, and (for Prairie/Affordable) the sister-facility title/nickname conventions most correlation logic is actually built around.

**How to apply**: when validating a new correlation/matching heuristic against real data, checking it against an Absolute-managed facility tells you almost nothing about how it'll perform on the normal case -- don't let a failure there read as a general weakness, and don't let a pass there read as validation either. Test against the three clients above first. See [[Session 2026-09-17 — Merchant Account Correlation, Business_DBA Signal & Two Live Data Bugs]] for the investigation this was learned from.

## STRICT RULE (2026-09-09): `unitprep-api`/`unitprep-ui` exist ONLY in WSL — never a Windows/Dropbox/OneDrive clone

> [!danger] If you are about to `Read`/`Edit`/`Write` a path containing `Dropbox`, `OneDrive`, or any Windows drive letter for `unitprep-api`/`unitprep-ui` source, STOP. The only real repos are `~/Development/unitprep-api` and `~/Development/unitprep-ui` inside WSL. Nothing else is canonical, regardless of what it looks like or what's sitting in it.

**What happened**: while building the Elavon QMS/Pinpad credentials feature, a session correctly worked in WSL for the backend, but for the frontend it found `C:\Users\bmaksimov\KoBre Dropbox\Boris Maksimov\Documents\unitprep-ui` already had uncommitted changes sitting in it (from an earlier same-day session) and, reasoning from its own memory of that prior session, built new UI work there too. That checkout turned out to be **stale and structurally diverged** from WSL: WSL's `main` already had `252ca83 Split the facility detail page into nine tab components` committed and pushed, which moved `ElavonTab` out of the monolithic `page.tsx` the session was editing into its own file, `components/facility/ElavonTab.tsx`. The session's UI edit landed in a file shape that no longer matched reality.

**How this was confirmed, not assumed**: `git fetch` + comparing local HEAD to `origin/main` in WSL showed both `unitprep-api` (`1.9.24`) and `unitprep-ui` (`1.6.29`) exactly matched GitHub — zero unpushed commits. Every one of today's (2026-09-09) memory-recorded features that had been described as "left uncommitted in [the Dropbox checkout]" was independently found already properly committed and pushed in WSL under a real commit (`fc42391` for the admin-only Integrations/Dropbox-settings work, `3a8d6a2`/`bcd0a94` for the nav rearrange/log-page split). **Boris also confirmed independently**: he runs both dev servers from WSL when testing, which is itself standing evidence that WSL is the live, current environment — the Dropbox checkouts were never actually being run against.

**Full inventory of what existed and why, as of 2026-09-09** (all now deleted, see below):
- `C:\Users\bmaksimov\KoBre Dropbox\Boris Maksimov\Documents\unitprep-api` — a real clone of `github.com/quikstorboris/unitprep-api`, but **96 commits behind** (last commit 2026-08-20). Almost certainly a leftover Windows-native clone from before WSL became the primary dev environment, kept alive only by Dropbox's own file sync, never actually built/run/committed to since.
- `C:\Users\bmaksimov\KoBre Dropbox\Boris Maksimov\Documents\unitprep-ui` — same story, closer to current (last real commit 2026-09-08) but still 7 commits behind WSL, and its own uncommitted local changes (nav rearrange, Dropbox settings page, audit-log page split) turned out to be **exact duplicates of work already properly committed in WSL** — not divergent, valuable work, just orphaned re-attempts.
- `C:\Users\bmaksimov\KoBre Dropbox\QS Fileserver\Shared\Claude Skills\Duplicate Check\unitprep-api` — a small (592K) clone bundled inside the shared `duplicate-tenant-check` skill package. Confirmed the skill's own `duplicate_tenant_check.py` has zero import/dependency on it — a stray reference copy from whoever wrote that skill, never cleaned up, not needed by the skill at runtime.
- `C:\Users\bmaksimov\OneDrive - Kobre Holdings, LLC\Documents\temp\unitprep-ui` — not even a git repo (`fatal: not a git repository`), just an empty stray `node_modules/sharp` folder, 0 bytes of real content.

**What was done about it**: the real content of all four (excluding regenerable `node_modules`/`.next`/`target` build output) was zipped to `~/Desktop/stale-unitprep-repo-backups-2026-09-09.zip` as a just-in-case backup, then all four source folders were permanently deleted. Nothing under `Dropbox` or `OneDrive` should exist for these two repos going forward.

**How to apply**: before trusting any `unitprep-api`/`unitprep-ui` file path, confirm it starts with `~/Development/` inside WSL. If a Windows-side path for either repo is ever found again (a new clone, a sync artifact, anything), do not read from it, do not write to it, and do not treat its presence as evidence of anything — flag it to Boris and stop. See [[Session 2026-09-09 — Elavon QMS & Pinpad Credentials Section]] for the full incident writeup.

**Root cause narrowed 2026-09-09**, in [[Session 2026-09-09 — Codebase Audit Follow-Through, God-File Refactors, README Rewrite, and Coherent Ship]]: the escaping loss through the Bash tool -> `wsl.exe` -> inner `bash -lc` chain isn't specific to `.env.local`'s `&` character at all -- a plain `export NVM_DIR="$HOME/.nvm"; echo "[$NVM_DIR]"` (zero special characters, unrelated to this file) printed an empty value in the same call, while a bare `echo $HOME` in isolation worked fine. The pattern: **multi-statement `;`-separated commands inside one `wsl.exe -d <distro> -- bash -lc "cmd1; cmd2"` string lose shell variable state between statements**, even for trivial exports -- not fully root-caused (some layer of that four-hop chain re-parses or re-quotes the string in a way that drops the assignment before the second statement sees it). **Reliable workaround**: never pass multi-statement command strings inline through this chain. Write the commands to a real `.sh` file (via the Write tool, through the `\\wsl$\...` UNC path) and execute it with `wsl.exe -d <distro> -- bash -lc "bash /path/to/script.sh"` instead -- single-command invocation through the chain is reliable; multi-statement ones are not.

## Neon: `suspend_timeout_seconds: 0` means "use the plan default," not "never suspend" -- that's `-1`

Misread live during [[Session 2026-09-21–22 — Neon Compute-Usage Root Cause & Login-Stuck-After-Idle Fix|the 2026-09-21/22 compute-usage investigation]], and it cost real time. Both `unitprep-api`'s Neon endpoints showed `suspend_timeout_seconds: 0` via `GET /projects/{id}/endpoints`, which was read as "autosuspend fully disabled" (`0` intuitively reads as "off"). It isn't. Per Neon's own API docs (`api-docs.neon.tech/reference/updateprojectendpoint`) and confirmed live by Neon staff in their Discord support channel: `0` means *"use the plan default"* (300s / 5 min on Free); the value that actually means "never suspend" is `-1`. Free plan can't edit this field in either direction -- not a bug, a deliberate restriction (the Console UI shows it greyed out with an upgrade prompt; the API rejects a PATCH with `"modifying the suspend interval is not permitted on this account"`).

**Why this is easy to get backwards**: `0` reads as "off"/"disabled" in most boolean-ish contexts, and Neon's own account-level `default_endpoint_settings.suspend_timeout_seconds` field also showed `0`, reinforcing the wrong read. A support ticket got half-drafted around "reset this account's stuck never-suspend config" before Neon staff corrected it same-day -- the account had never even held a paid plan, so there was no stuck leftover setting to fix in the first place.

**How to apply**: if a Neon endpoint's compute is staying active far longer than expected, don't diagnose via `suspend_timeout_seconds`'s raw value on Free/Launch plans -- assume the plan default (300s) is genuinely in effect and look for what's actually generating traffic inside that window instead (see the very next entry, which was the real cause here). Only on a Scale plan does an arbitrary `suspend_timeout_seconds` value mean what it looks like it means.

## A background poll whose interval matches the platform's idle-suspend window perpetually prevents the compute from ever suspending

Real root cause of [[Session 2026-09-21–22 — Neon Compute-Usage Root Cause & Login-Stuck-After-Idle Fix|the 2026-09-21/22 Neon compute-usage investigation]] (Process Street was the initial, reasonable-but-wrong suspicion -- see that note for why it was ruled out). `unitprep-api`'s `client_ops::vendor_format::start_refresh_task` runs two background loops (Units, Tenants) that each query Postgres every 300 seconds, forever, for as long as the server process is up. Neon's Free-plan default idle-suspend timeout is also 300 seconds. Every tick landed close enough to the timeout boundary to reset Neon's idle clock just before it would have fired -- so any time the dev server was left running, real autosuspend never got a genuine idle window to act in. Confirmed against the Neon operations log: two earlier multi-day continuous-`active` stretches (2026-08-21→26, 2026-09-11→15) line up with the server simply having been left running, in an account whose suspend timeout was the untouched Free-plan default the entire time -- not a config problem, a collision problem.

**Why this is easy to miss**: nothing errors, nothing looks wrong in either system's own logs -- Neon correctly reports the compute as genuinely active (it is, technically, every 300s), and the app's own background-refresh doc comment explicitly justified the interval as "never a meaningful load on Postgres," which is true in isolation and says nothing about its *cadence* relative to the hosting platform's own idle-suspend window.

**How to apply**: when adding or reviewing any background poll/refresh loop against a serverless-autosuspend database (Neon, and likely similar platforms), check its interval against the platform's actual idle-suspend timeout, not just against "is this too much load." An interval at or near that timeout is the worst case -- it guarantees the compute never gets to suspend for as long as the process runs, regardless of real traffic. Fixed here by widening the interval to 4 hours (still same-day pickup for a self-service-added vendor row, the property the original 5-minute choice was protecting). Worth a pass over this codebase's other periodic background tasks (the `router.rs` 60s rate-limit-bucket cleanup is in-memory only, so it doesn't touch Postgres/Neon and isn't at risk the same way) if a similar symptom shows up again.

## Next.js 16 + Turbopack dev mode: a soft client-side navigation can silently fail to complete after a long-idle tab

Assessed (not confirmed via live repro) 2026-09-22 in `unitprep-ui`, diagnosing [[Session 2026-09-21–22 — Neon Compute-Usage Root Cause & Login-Stuck-After-Idle Fix|a login-stuck-after-idle bug]]: after leaving a tab idle a long time, a passkey login would visibly succeed (server logs confirm real, authenticated `/auth/login/finish` and `/health/whoami` responses) but the UI stayed on `/login` -- `router.replace("/clients")` appeared to do nothing, no error thrown or logged anywhere. `Ctrl+Shift+R` always fixed it.

The app's own auth-state code (the login page, the `useSyncExternalStore`-based `useCurrentUser` singleton, the protected-shell guard) was read through and is correct -- the client genuinely had a valid, checked, authenticated user before attempting to navigate. The likely mechanism: Turbopack (the current default `next dev` bundler as of Next.js 16) keeps a long-lived HMR/dev-router connection to the tab, which can go stale after a long idle period, causing the *next* client-side soft navigation to silently fail to complete rather than throwing. This is dev-mode-only in nature (a `next build && next start` production run has no Turbopack HMR to go stale), but the app currently only ever runs via `next dev`.

**How to apply**: for a redirect that follows an infrequent, high-stakes event (login success, not a hot navigation path), prefer a hard navigation (`window.location.assign(path)`) over the client router (`router.replace`/`router.push`) -- it can't be affected by stale client-router/HMR state at all, since it forces a real fresh page load. Don't blanket-apply this to routine in-app navigation (loses the instant client-transition UX for no reason there); reach for it specifically where "silently doesn't work after this app has sat idle" would be confusing and hard to diagnose for the person hitting it. Fixed in `app/login/page.tsx`'s post-login redirect; the sibling "already signed in, bounce away from /login" redirect in the same file was deliberately left as `router.replace`, since it isn't the path that follows a long-idle gap.

## `unitprep-api`'s RLS SELECT policies gate on two GUCs, not one -- a raw `psql` query missing the second one silently returns zero rows

Hit live 2026-09-22 in [[Session 2026-09-22 — Re-sync Never Refreshed ps_person_index (Users Tab Candidates Went Stale)|the Elavon resync investigation]], diagnosing whether Main Street Storage's `clients.facility_merchant_accounts` row actually existed. `SET app.current_user_id = '<any-uuid>';` is enough to satisfy the broad "any authenticated" SELECT policies (`ps_person_index`, `ps_task_status`, `clients.facilities`, etc.), but role-gated tables (`clients.facility_merchant_accounts`, `clients.facility_merchant_account_parties`) additionally check `auth.current_user_has_role(p_role_key)`, which reads a *second*, separate GUC -- `current_setting('app.current_user_roles', true)`, a comma-separated list -- and returns `false` if it's unset. A `psql` session that only sets `app.current_user_id` gets a real, silent **0 rows** back from a role-gated table, indistinguishable at the SQL level from "the row genuinely doesn't exist."

**How to apply**: when querying this app's own dev DB directly via `psql` (bypassing the app's own `begin_rls_transaction`, which always sets both), set both GUCs before trusting an empty result from any table more sensitive than "any authenticated read" -- `SET app.current_user_id = '00000000-0000-0000-0000-000000000000'; SET app.current_user_roles = 'onboarding_manager,department_manager';` covers every `client_ops`-gated table in this schema. A `\d <table>` first to read its actual RLS policies (not just guessing from the table name) confirms which GUC(s) a given table's own SELECT policy actually needs.

## Process Street task ids are shared across every run of the same workflow template -- they are not unique per run

Found 2026-09-23 investigating [[Session 2026-09-23 — Milton Mix-Up, Manual Link Action & EIN-Address Disambiguation|the Knapp's Self Stor of Milton Freewater / "Milton Self Storage" mix-up]], comparing two different real Merchant Account runs' own task lists side by side. Both runs -- genuinely different real businesses, different real applications -- returned the *exact same* set of `ps_task_id` values (`gGkUh4u-X0ya-MZBtERI1g` = "Step to Add Customer Success Team", `iNLen-9tK7YqTrOgAodFEA` = "Add Credentials to QMS", etc.), in the same order, for the same 💳 New Merchant Account workflow. A task's id identifies its *position in the checklist template*, not the specific run instance it belongs to.

**Why this matters, and doesn't break anything already built**: `clients.ps_task_status`'s own `UNIQUE (facility_id, workflow, ps_task_id)` constraint is scoped by `facility_id` already, so this fact doesn't cause any data-integrity problem in the existing schema -- it's scoped correctly by accident/design, not exposed to a collision. But it does mean: (1) a `ps_task_id` alone is never a safe key to look anything up by without also scoping to a specific run/facility; (2) code matching a task by *name* (`credentials_added_to_qms_from_tasks`'s `task.name.trim().eq_ignore_ascii_case(...)`) is the right approach, not matching by id, since the id carries no run-specific identity at all; (3) the same template-position id reappearing across runs is exactly what makes `clients.ps_task_status.id` (the local `BIGSERIAL`, assigned in the order `upsert_task_status` first sees each task for one specific facility) a usable, stable proxy for "checklist step order" per facility -- see `clients_onboarding_summary.rs`'s own module doc for where this gets relied on.

**How to apply**: never assume a `ps_task_id` (or a `ps_run_id` collision, for that matter -- not checked here but worth the same suspicion) uniquely identifies a real-world thing without also checking which facility/run it's scoped to. If debugging by comparing raw PS API task-list JSON across two different runs of the same workflow, expect the ids to line up even when nothing else about the two runs does.
