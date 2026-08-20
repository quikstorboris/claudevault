---
date: 2026-08-03
description: "For unitprep-api (and by extension similar repos under the same convention), Boris has delegated the decision of WHEN to bump the version, WHICH part…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-03T19:12:44.301Z"
scope: project
projects: ["unitprep-api"]
confidence: verified
---

# Boris delegates version-bump and git-tag authority to the agent, standing

For unitprep-api (and by extension similar repos under the same convention), Boris has delegated the decision of WHEN to bump the version, WHICH part to bump (major/minor/patch), and WHETHER/WHAT git tags to create — the agent should just act and notify him afterward, not ask first. This is a standing authorization, not a one-time approval for a single bump.

Practical convention already established in this repo (verified from git history, not assumed): CHANGELOG.md follows Keep a Changelog with an [Unreleased] section; a version bump means (1) renaming [Unreleased] to a dated version heading with a short rationale paragraph in the same voice as prior entries — what now works, and an explicit "what is NOT here yet" so the number doesn't overclaim, (2) adding a fresh empty [Unreleased] with "Nothing yet." above it, (3) bumping Cargo.toml's version, (4) committing the feature work and the version-bump-metadata (CHANGELOG+Cargo.toml+Cargo.lock) as separate commits (matching this repo's own historical shape: a "Bump version to X" commit distinct from feature commits), and (5) creating an annotated git tag (`vX.Y.Z`) pointing at the right commit and pushing it to origin.

Semver judgment call worth carrying forward: this project treats a MINOR bump as "adds functionality that did not exist before" (verbatim reasoning found in the historical 1.2.0-bump commit message) — even fixes/hardening bundled into the same release don't downgrade it to a patch if genuine new capability shipped alongside them. Don't default to the smallest-sounding number; check what actually shipped since the last tag.

Tag placement matters: point the tag at the commit that represents the FINAL state of that version's intended scope, not just "wherever Cargo.toml's version string last read that number" — interim commits made while preparing the NEXT version's changes will still say the OLD version string in Cargo.toml until the bump commit itself changes it, and tagging one of those would incorrectly sweep unrelated new work into the old release.

Discovered a real gap while acting on this the first time: v1.2.0 was never tagged at all (tag sequence jumped v1.1.5 -> nothing -> the agent's own v1.3.0). Backfilled it retroactively pointing at the actual last commit still at that version, matching this repo's own established retroactive-tagging convention (v1.0.0 through v1.1.5 were themselves all tagged retroactively in one batch, per their own tag messages) - worth checking for other retroactive-tagging gaps in a repo before assuming the tag sequence is complete.
