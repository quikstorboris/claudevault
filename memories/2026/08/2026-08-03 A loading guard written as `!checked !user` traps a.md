---
date: 2026-08-03
description: "When a component distinguishes \"haven't checked auth state yet\" from \"checked, and nobody is signed in\" via two separate flags (e.g."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-03T21:46:52.849Z"
scope: general
projects: []
confidence: verified
---

# A loading guard written as `!checked || !user` traps a signed-out visitor in the loading message forever

When a component distinguishes "haven't checked auth state yet" from "checked, and nobody is signed in" via two separate flags (e.g. `checked: boolean` and `user: T | null`, the pattern this codebase's CurrentUserProvider/ClientsProvider use), a render guard of the form `if (!checked || !user) return <Loading/>` collapses both false-ish states into one branch. The signed-out case then never escapes the loading branch, because `!user` stays true forever for an anonymous visitor -- there is no subsequent state transition that would make the condition go false. It renders correctly for the *authenticated* path (checked flips true, user becomes truthy) and only breaks the *unauthenticated* path, which makes it easy to ship unnoticed if the page is only ever eyeballed while signed in.

The fix is two separate guards in the right order: `if (!checked) return <Loading/>` first, then `if (!user) return <SignedOutView/>`, then the real content. Whenever a page reads both a "checked" flag and a nullable "current value" from the same auth/session hook, treat that as a sign three-way branching (loading / absent / present) is needed, not two.

This generalizes beyond one page: it applies to any component consuming a `{checked, user}`-shaped hook (or the equivalent `{status: 'idle'|'loading'|'ready', data}` pattern) directly rather than going through a single derived enum.

##### How this is known

Caught live in unitprep-ui's new `/account` page 2026-08-03: the page rendered "Checking your session…" forever when visited signed-out (confirmed via the whoami network request completing with a real 401 while the UI never advanced), because the guard was `if (!checked || !user)`. Splitting it into two sequential guards fixed it immediately, verified by reloading signed-out and seeing the "Sign in to manage your account" branch render.

## How this is known

Reproduced in the browser against the real running dev server: signed-out visit to /account stuck on the loading text with a real 401 already returned over the network; fixed by splitting the guard, then reloaded and confirmed the correct sign-in prompt rendered.
