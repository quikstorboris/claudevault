---
description: "Things that have bitten before and will bite again — pitfalls, edge cases, and testing traps"
tags:
  - brain
---

# Gotchas

Things that have bitten before and will bite again.

## Verify a parser's real output by running it — don't re-derive it by hand from raw XML

Found 2026-08-14 while diagnosing why the Template Tagger found zero candidates in a real filled document (see [[2026-08-14-filled-document-field-detection-shipped|Filled-document field detection]]). Manually extracting `<w:t>` text from `first_late_notice.docx`'s raw `document.xml` with a quick Python regex made it look like `docx_surgeon::read_docx` concatenates paragraphs with **zero separator** ("...SERVICE300 RODGERS BLDG..." — no space, no newline) — which would have meant a real, invasive change to `docx-surgeon`'s core text-flattening model was needed before any label-boundary detection could work on free text at all.

That was wrong. Actually running `read_docx` against the same file (via a throwaway `#[ignore]`d test, `println!`-ing the real `FlatText`) showed paragraphs genuinely ARE joined by `\n` — confirmed by the crate's own doc comments and existing tests (`separates_paragraphs_with_a_newline`), which a plain grep for "paragraph" would have surfaced immediately. The manual regex extraction simply didn't replicate what the real parser does (it doesn't insert the separator the parser does), so it produced a plausible-looking but false signal about the actual data shape.

**How to apply**: before concluding "the flattened/parsed output has property X" from reading raw source by hand, run the actual parser (a throwaway test is fine) and inspect its real output — especially before scoping a fix around the absence of something the parser might already provide. A wrong assumption here nearly triggered a much bigger, unnecessary change than the real fix needed.

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

## This laptop has ~2GB of RAM headroom — local model inference and the vault's own test suite will freeze it

Established 2026-07-30 by freezing the machine hard enough to need a cold reboot.
Read this before running anything heavy.

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

## `unitprep-ui` clients are frontend-only, browser-tab-scoped state

A "client" (name, contact info, Dropbox path, etc.) has no backend entity at all — it's stored in `sessionStorage` under `unitprep:clients` (see `lib/clients.tsx`), scoped per browser tab, and evaporates when the tab closes. There is no `POST /clients` endpoint and none is planned until the platform-vision persistence work lands.

**How to apply:** navigating directly to a `/clients/[clientId]/...` route (e.g. in an E2E test, or a bookmarked/shared URL) without that client having been created in *that specific browser tab's* session shows the app's own "this client isn't in the current browser session" guard, not the actual page — this is correct, expected behavior, not a bug. Playwright tests reaching a client-scoped route need to seed `sessionStorage` via `page.addInitScript()` before navigating, matching the `Client` shape in `lib/clients.tsx`.
