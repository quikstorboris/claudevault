---
date: 2026-10-29
description: "Read-only code review of unitprep-ui v1.6.106: nine findings (serial whoami/list/detail load chain, no shared cache, duplicate company lists, router.push navigation, unmeasured bundle and heavy screens) with file evidence."
tags: [work-note, unitprep, frontend, performance, review]
status: active
quarter: Q4-2026
project: unitprep
---

# Frontend Code Review 2026-10-29

Part of [[Frontend Performance Plan]]. Static read of `~/Development/unitprep-ui` (WSL, `main`, `cf3fa86`, v1.6.106, clean tree). **Nothing was run or measured**: no Lighthouse, no network trace, no trusted build (the `.next` folder found looked like a dev build). Anything about bundle size or heavy-list behaviour is a hypothesis for Phase 0 to confirm.

## Shape of the app (as of 2026-10-29)

- Next 16.2.9 / React 19.2.4 / Tailwind 4, ~35.9k lines of TS/TSX outside tests. 32 pages, **31 of them client components**, 209 files with `"use client"`.
- No data-fetching library. Fetching is 72 hand-rolled `useEffect`s plus `lib/useAsyncResource.ts`, all on `lib/http.ts`'s `apiRequest` / `ApiResult`.
- Two module-level stores act as the only caches: `lib/currentUser.tsx` (whoami) and `lib/clients.tsx` (full company list).
- `proxy.ts` only checks the session cookie is present (deliberately no edge round trip).
- Only 1 `next/image`, 2 files in `public/`, system fonts (Arial/Helvetica): assets are not a problem.
- Dynamic imports exist for the nine facility tabs (`components/facility/FacilityTabContent.tsx`) and two other spots.

## What is already good

- One HTTP client, consistent `ApiResult`, 401 broadcast through `lib/sessionExpiry.ts`.
- Facility tabs are separate lazy chunks; company data is fetched once per company and shared across facilities (`CompanyDetailContext`), facility reads re-fetch on `facilityId` alone (`useFacilityPageData`).
- Abort-on-newer-request on the directory (`useLatestRequest`), single-use dedup report hand-off (`lib/dedupReportCache.ts`), background-aware polling in `SyncButton`.
- The ClientsProvider no longer fetches on mount for every page (a prior Efficiency Refactor fix, see [[Efficiency Refactor - Code Review Brief]]).

## Findings (most impactful first)

| # | Finding | Evidence |
|---|---|---|
| F1 | **Every page load is a serial waterfall.** The signed-in shell renders only "Checking your session…" until `whoAmI` returns; pages and their fetches mount only after. | `app/(app)/layout.tsx:60-76`, `lib/currentUser.tsx:135` |
| F2 | **Opening any client page is a 4-step chain:** whoami, then the full `GET /clients` list, then company detail, then facility reads. `ClientLayout` blocks on the entire company list just to read one client's name, which company detail probably already contains (to confirm). | `app/(app)/clients/[clientId]/layout.tsx:20-34`, `lib/clients.tsx` |
| F3 | **No shared data cache.** `useAsyncResource` resets to `loading` on every run, so returning to a page refetches and flashes "Loading…". | `lib/useAsyncResource.ts:44` |
| F4 | **Two copies of the company list.** `useClients()` (full list, used for names/lookups by `ClientLayout`, `DiscoveryPage`, `TaggerUploadPage`, `useFacilityDropboxFolder`, `useClientsNewPreview`) and `useClientsDirectory` (filtered list for the Clients page) fetch independently. | `components/clients/directory/useClientsDirectory.ts:16-24` comment |
| F5 | **Facility page is three reads behind F1 and F2:** company detail, then facility and policies; all nine tabs share one policies read. | `components/facility/useFacilityPageData.ts` |
| F6 | **Navigation is `router.push` from a card `onClick`**, not a `<Link>`: no prefetch, no open-in-new-tab. | `app/(app)/clients/page.tsx:23` |
| F7 | **Heavy post-scan UI untested for scale (hypothesis).** No list virtualization (only the log feed has anything like it), no Web Workers; `fflate`, file sniffing and big dedup/scan result lists run on the main thread. | grep for `Worker`, `virtual` empty |
| F8 | **Bundle: measured 2026-10-29, not a big problem.** About 625 KB raw / 194 KB gzip shared by every route (React DOM plus Sentry dominate), heaviest route 734 KB raw / 227 KB gzip; no outsized route. Sentry's exact share still unmeasured. See [[Frontend Performance Plan]] progress log. | `instrumentation-client.ts`, `.next/diagnostics/route-bundle-stats.json` |
| F9 | **Minor:** ClickUp copy-jobs poll (3 s while a job runs) does not pause in a hidden tab; no `loading.tsx` or route error boundaries beyond `app/error.tsx`; no React Compiler. | `components/clickup/bulk/useCopyJobs.ts:94-98` |

## Things checked and found fine

- `useClickUpAccess` does **not** fetch; it reads the permission off the already-loaded user. (It was suspected of being a per-mount fetch.)
- Only two `setInterval`s exist (`useCopyJobs`, `useAbortableOperation`) plus the visibility-aware `SyncButton`.

## Resolution (as of 2026-10-29, end of the autonomous run; details in [[Frontend Performance Plan]])

| # | Outcome |
|---|---|
| F1 | `whoami` itself fixed (6 statements to 2, api 1.9.137). The shell still waits for it **on purpose** (TOTP and step-up gates); a non-blocking shell was rejected for a small saving against real security cost. |
| F2 | **Fixed** (ui 1.6.108): the client layout takes the name from company detail and starts it at once; about 1.2-1.5 s to about 0.4 s warm. |
| F3 | **Fixed for the hot reads** (ui 1.6.109, 1.6.110): TanStack Query cache for company, facility, policies, directory and filter options. Not migrated: whoami, ClickUp connection, tool-session hooks, facility tab hooks (by choice). |
| F4 | **Fixed** (1.6.110): the unfiltered list is retired, its module deleted. |
| F5 | Improved as a side effect of F2 and F3 (company reused when switching facilities; revisits instant). |
| F6 | **Fixed** (1.6.111): company cards are real links. |
| F7 | **Not started**: needs a real large report to profile. |
| F8 | Measured: not a problem (about 194 KB gzip shared floor). Sentry's exact share still unmeasured. |
| F9 | Hidden-tab poll slowed (not paused, deliberately); in-shell `error.tsx` and `loading.tsx` added (1.6.111). React Compiler untouched. |
| F10 / F11 | F11 (ClickUp prefetch on every company view) **fixed** (1.6.107, hover only). F10 (connection call) correct by design, left alone. |

## Related

[[Frontend Performance Plan]], [[Frontend Performance - Decisions and Discussion]], [[Latency Investigation 2026-10-20 - Round Trips vs Neon]]
