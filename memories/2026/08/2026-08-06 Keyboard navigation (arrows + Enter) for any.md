---
date: 2026-08-06
description: "Boris's explicit standing preference, stated while asking for arrow-key + Enter navigation on a fuzzy-search user-picker dropdown that only supported…"
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-08-06T15:54:49.204Z"
scope: general
projects: []
confidence: unverified
---

# Keyboard navigation (arrows + Enter) for any dropdown-with-a-list should be built in by default, not added only when asked

Boris's explicit standing preference, stated while asking for arrow-key + Enter navigation on a fuzzy-search user-picker dropdown that only supported mouse clicks: keyboard navigation for a dropdown/combobox-style list (arrow up/down to move a highlight, Enter to act on it, typically Escape to close) is a baseline UI/UX expectation, not a nice-to-have to bolt on reactively per-component when someone happens to notice one is missing it and asks. When building or reviewing any searchable dropdown, autocomplete, or multi-select-with-a-list UI, keyboard navigation should be considered and implemented as part of that work by default, in accordance with ordinary UI/UX best practice -- the same way a submit button needs a disabled state, not something that only gets added once a user complains they couldn't tab through it.

Practical shape that satisfied this the first time (UnitPrep's audit-log filter dropdowns, React): a `highlightedIndex` piece of state over whatever flat list is currently visible in the dropdown; ArrowDown/ArrowUp move it (wrapping at the ends is a reasonable default); Enter acts on the highlighted item -- what "acts on" means depends on the list's own semantics (a pick-one-then-close combobox selects and closes; a checkbox list of independent toggles should toggle and stay open, since closing on every Enter would defeat being able to check several in a row); Escape closes. Reset the highlight when the visible list's contents change (e.g. on every keystroke in the dropdown's own search box) -- do this inside the same event handler that changes the search text, not in a `useEffect` keyed on the search value: calling `setState` synchronously inside an effect body triggers an extra, avoidable cascading render for a change that was already known at the point the input's `onChange` fired (React's own `react-hooks/set-state-in-effect` lint rule catches this class of mistake).

Also worth remembering: a *partial* ARIA combobox implementation (just slapping `role="combobox"` / `aria-expanded` / `aria-autocomplete` onto the input without the full pattern -- an associated `role="listbox"`, `role="option"` on each row, `aria-controls` linking the two, `aria-activedescendant` tracking the highlight) is arguably worse than no ARIA role at all, since it signals combobox semantics to assistive tech without actually providing them. `eslint-plugin-jsx-a11y`'s `role-has-required-aria-props` rule will flag the missing pieces. Don't half-implement this: either build the complete pattern or leave the ARIA attributes off and rely on the visual highlight + native keyboard events, which is what shipped here.
