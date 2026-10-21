---
date: "2026-10-20"
description: "Standing rule for comments in unitprep-api Rust code so the generated rustdoc pages are accurate, readable, and consistent: what to write, how to format it, and the 'flag quick wins' habit."
tags:
  - brain
---

# Rustdoc and code comment standard (backend)

**Standing rule, set by Boris 2026-10-20.** Comments in `unitprep-api` are written so the generated rustdoc pages (`cargo doc`) carry minimal but informative, consistently formatted documentation for everything in the backend. It applies to code written or touched **from now on**. Nothing is being rewritten retroactively. Also recorded in `unitprep-api/CLAUDE.md`, because a vault-only rule has already failed once to reach a session working in the repo (see [[Dev Principles]] #3 and the `CLAUDE.md` file-size law for that history).

## Why

Rustdoc is a developer-facing map of the backend: module tree, types, signatures, and whatever the comments say. It explains nothing the comments do not. A function with no `///` shows only its signature. So the documentation is exactly as good as the comments, and they are cheap to write well at the moment the code is written.

**Audience** (decided 2026-10-20): developers who work inside the backend: Boris, a future hire or contractor, and AI coding sessions. Also a plain-English orientation for a non-developer reader, which is why every module's first sentence must stand alone. It is **internal**: it describes security internals, so never publish it to docs.rs or the open web.

## The rules

1. **Every module gets a `//!` header.** First sentence: what this part of the app is for, in plain English a non-developer can follow, no jargon in that sentence. Then, only if useful, a few lines on how it fits (what calls it, what it must not do). Keep module overviews current: when a module's job changes, update its `//!` in the same change (a stale overview is worse than none).
2. **Every non-trivial item gets a `///` summary.** Functions, structs, enums, traits, consts, and type aliases that are more than a one-line getter. First line is one sentence in the third person that does not restate the signature. A trivial private helper whose name says everything may go without.
3. **Say what the signature cannot.** Why it exists, invariants, units, side effects (writes the DB, calls an external service), who must call it first, what it must never do (log PII). Leave out anything the types already show.
4. **Add the standard sections only when true:** `# Errors` (when it returns `Err`, and what kinds), `# Panics` (when it can panic), `# Examples` (a short snippet, see 6). Never write an empty or boilerplate section.
5. **Format for rustdoc, not for the editor.**
   - Code, types and identifiers in backticks: `` `Vec<String>` `` (an unquoted `Vec<String>` is parsed as an HTML tag).
   - Link other items with `` [`Name`] `` only if that item is documented and visible; otherwise use plain backticks.
   - Escape literal square brackets as `\[Middle\]`; they are otherwise read as links.
   - URLs in angle brackets `<https://example.com>` or backticks.
   - **No vault wikilinks in code comments** (`[[note]]`): rustdoc reads them as a broken link and only Boris's vault can resolve them. Say it in prose and name the note in backticks, for example: see the vault note `Real Documents Are the Spec`.
   - Use real Markdown lists and short paragraphs; blank line before a list.
6. **Snippets.** Add a short example when a function is easy to misuse or its input/output shape is not obvious (parsers, matchers, formatters). In the library crates (`core`, `dedup`, `unit-group`, `docx-surgeon`, `template-tagger`, `tagger-pipeline`) a ```` ```rust ```` block is compiled and run by `cargo test --doc`, so it cannot rot: prefer that. In the `unitprep` binary crate doc examples are **not** run, so mark non-verified ones ```` ```text ```` rather than letting a wrong example look authoritative.
7. **Examples contain fake data only.** Never a real tenant name, email, phone, or client ID in a comment or snippet (the standing PII rule; see [[Real Documents Are the Spec]]).
8. **`//` stays for implementation reasons; `///` and `//!` are the contract.** A long "why this was done this way" note inside a function body stays a normal comment. The doc comment says what the item is for and promises; the inline comment explains the awkward how.
9. **Keep it minimal.** One good sentence beats a paragraph. No tutorial prose, no change history ("added in v1.9.130": that is the changelog's job).

## The habit: flag quick wins while you work

Whenever you write or edit code in this repo, look at the doc comments around what you touch and, **in the same turn**, say what is cheap to improve for the rustdoc, or just do it when it is in the files you are already changing: a missing module `//!`, an item with no `///`, a stale module overview, a broken link or bare URL, an obviously useful snippet. Flag, do not go on a repository-wide cleanup unless Boris asks. Same spirit as the file-size flag in `unitprep-api/CLAUDE.md`.

## Checking

```bash
cd ~/Development/unitprep-api
cargo doc --workspace --no-deps --document-private-items
```

- `--workspace` includes the library crates; `--document-private-items` is required because a binary crate has no public API and almost everything is private; `--no-deps` skips documenting every dependency (about 30 s instead of 8 min).
- Open it: `file://wsl.localhost/Ubuntu/home/bmaksimov/Development/unitprep-api/target/doc/unitprep/index.html` in a Windows browser, or serve it with `cd target/doc && python3 -m http.server 8000` and open `http://localhost:8000/unitprep/`.
- `target/doc/` is deleted by `cargo clean` (so is all of `target/`); just rebuild.
- **New code must add no new rustdoc warnings.** The pre-existing ones (see "Open" below) are not yours to fix unless you are in that file anyway.

## Open

- 11 pre-existing rustdoc warnings across `unitprep-core` (3), `docx-surgeon` (2), `unitprep-template-tagger` (3) and the `unitprep` binary (3) as of 2026-10-20: a broken `[[...]]` note link in `process_street/client.rs`, bare URLs in `auth/webauthn_backend.rs` and `startup/config.rs`, an unquoted `Vec<String>`, unescaped `[Middle]`, and links to private items. Boris said not to fix retroactively; clean up opportunistically when touching those files.
- `startup/mod.rs`'s module overview still says "What `main` does" and omits the Sentry step, and `startup::run` has no `///`: a good first candidate when that file is next touched.
- Once the warnings are cleared, consider making a clean `cargo doc` (with `RUSTDOCFLAGS="-D warnings"`) a step in `scripts/preflight.sh`. Not before: it would fail today.
- A real API route reference (request/response shapes) would be a separate OpenAPI-style effort; rustdoc does not provide one.
- Frontend (`unitprep-ui`) TypeScript is outside this rule; if wanted later it would be a TSDoc equivalent.
