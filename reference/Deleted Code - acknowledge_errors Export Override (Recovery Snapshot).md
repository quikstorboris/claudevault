---
date: 2026-07-28
description: "Verbatim recovery snapshot of the acknowledge_errors export-override pathway (BE+FE), deleted 2026-07-28 as dead code. Restore from here if the bulk-override feature is wanted back."
tags: [reference, unitprep]
status: archived
---

# Deleted Code — `acknowledge_errors` Export Override (Recovery Snapshot)

**Purpose of this note**: Boris asked to preserve the full code for this feature before deletion, in case testing later shows a need to bring it back — distinct from "Import As Is" (`acknowledgedGroupNames`), which is a separate, still-live per-group feature and was NOT touched. See [[Third Hardening Pass (Pre-Auth-Resume)]] for why this was deleted rather than restored as a real feature.

## Why it was deleted, not restored

Backend blocks `/export` when `Severity::Error` validation issues remain unresolved; `acknowledge_errors: true` was a bulk override to export anyway. The only two real `Severity::Error` issue types (`BLANK_UNITGROUP`, `DUPLICATE_UNITS`, `unit-group/src/validation/mod.rs`) both already have inline correction UI (`IssueCard` → `onCorrectionSaved` → `/correct`/`/correct-group`) in `ScanResultsPage.tsx`. The only condition that stays unconditionally blocking is `files_errored` (a file that failed to parse) — correctly so; that shouldn't be overridable. The frontend's own `Continue` button (`ScanResultsPage.tsx`) is disabled until `everythingResolved` (`issue_count === 0`), so by the time it's clickable `validation.ready` is already true — no UI path ever set `acknowledged=true`. Confirmed distinct from "Import As Is": that's `WarningsSection.tsx`'s per-group `acknowledgedGroupNames` mechanism (marks one flagged group as accepted without correction), a completely different, still-live feature untouched by this deletion.

## Backend — `unitprep-api`

### `src/api/export.rs` — the `ExportRequest.acknowledge_errors` field

```rust
#[derive(Debug, Deserialize)]
pub struct ExportRequest {
    pub session_id: String,

    /// Explicit human override for exporting despite unresolved
    /// Severity::Error validation issues (e.g. after reviewing them via
    /// the inline correction UI and deciding to proceed anyway). Defaults
    /// to false so old clients that don't send this field keep the
    /// existing blocking behavior.
    #[serde(default)]
    pub acknowledge_errors: bool,
}
```

### `src/api/export.rs` — the two branches inside `export()` that check it

```rust
    if !validation.ready && !request.acknowledge_errors {
        tracing::warn!(
            session_id = %request.session_id,
            issue_count = validation.issue_count,
            error_count = validation.error_count,
            "Export blocked by validation failures"
        );

        return (
            StatusCode::BAD_REQUEST,
            Json(ApiErrorBody {
                error: "validation_unresolved",
                message: "Validation issues must be resolved before export".to_string(),
            }),
        )
            .into_response();
    }

    if !validation.ready && request.acknowledge_errors {
        tracing::warn!(
            session_id = %request.session_id,
            error_count = validation.error_count,
            "Export proceeding despite unresolved validation errors — acknowledged by user"
        );
    }
```

(Deletion collapses these to an unconditional block on `!validation.ready`.)

## Frontend — `unitprep-ui`

### `components/export/useExportDownload.ts` — full file as it stood before deletion

```typescript
"use client";

import { useState } from "react";

import { downloadBlob, useSessionAction } from "@/lib/useSessionAction";

interface UseExportDownloadResult {
  exporting: boolean;
  downloadComplete: boolean;
  error: string | null;
  sessionExpired: boolean;
  handleExport: () => Promise<void>;
}

const FALLBACK_FILENAME =
  "UnitPrep_Output.zip";

/**
 * Owns the /export request and the resulting browser download. Kept
 * separate from useAnalysis so an export-time error doesn't have to
 * share state with (and potentially hide) the already-rendered analysis
 * results — see ExportCompletePage for how the two errors are displayed
 * differently.
 */
export function useExportDownload(
  sessionId: string,
  acknowledgeErrors: boolean = false
): UseExportDownloadResult {
  const { pending, error, sessionExpired, run } =
    useSessionAction(sessionId, "/export");

  const [
    downloadComplete,
    setDownloadComplete,
  ] = useState(false);

  const handleExport = async () => {
    const result = await run({
      acknowledge_errors:
        acknowledgeErrors,
    });

    if (result.kind !== "ok") return;

    const blob =
      await result.response.blob();

    downloadBlob(
      blob,
      result.response.headers.get(
        "Content-Disposition"
      ),
      FALLBACK_FILENAME
    );

    setDownloadComplete(true);
  };

  return {
    exporting: pending,
    downloadComplete,
    error,
    sessionExpired,
    handleExport,
  };
}
```

### `components/ExportCompletePage.tsx` — the `acknowledgeErrors` prop wiring (excerpt)

```typescript
interface ExportCompletePageProps {
  sessionId: string;
  acknowledgeErrors: boolean;
  onBack: () => void;
  onHome: () => void;
}

export default function ExportCompletePage({
  sessionId,
  acknowledgeErrors,
  onBack,
  onHome,
}: ExportCompletePageProps) {
  // ...
  const {
    exporting,
    downloadComplete,
    error: exportError,
    sessionExpired: exportExpired,
    handleExport,
  } = useExportDownload(
    sessionId,
    acknowledgeErrors
  );
  // ...
```

### `app/clients/[clientId]/unit-groups/[sessionId]/export/page.tsx` — full file as it stood before deletion

```typescript
"use client";

import {
  useParams,
  useRouter,
  useSearchParams,
} from "next/navigation";

import ExportCompletePage from "@/components/ExportCompletePage";
import { cancelSession } from "@/lib/api";

export default function ExportPage() {
  const router = useRouter();

  const { clientId, sessionId } = useParams<{
    clientId: string;
    sessionId: string;
  }>();

  const acknowledgeErrors =
    useSearchParams().get("ack") ===
    "1";

  return (
    <main className="p-8">
      <ExportCompletePage
        key={sessionId}
        sessionId={sessionId}
        acknowledgeErrors={
          acknowledgeErrors
        }
        onBack={() =>
          router.push(
            `/clients/${clientId}/unit-groups/${sessionId}`
          )
        }
        onHome={() => {
          cancelSession(sessionId);
          router.replace(
            `/clients/${clientId}/info`
          );
        }}
      />
    </main>
  );
}
```

### `app/clients/[clientId]/unit-groups/[sessionId]/page.tsx` — the `?ack=1` URL construction (excerpt)

```typescript
        onExport={(acknowledged) =>
          router.push(
            acknowledged
              ? `/clients/${clientId}/unit-groups/${sessionId}/export?ack=1`
              : `/clients/${clientId}/unit-groups/${sessionId}/export`
          )
        }
```

`ScanResultsPage.tsx`'s `onExport` prop type was `(acknowledged: boolean) => void`, called only as `onExport(false)` from the "Continue" button (`disabled={!everythingResolved}`) — no call site ever passed `true`.

## How to restore

1. Re-add `ExportRequest.acknowledge_errors` and the two branches in `src/api/export.rs`.
2. Re-add the `acknowledgeErrors` param to `useExportDownload`, the prop on `ExportCompletePage`, and the `useSearchParams().get("ack")` read + `?ack=1` URL branch.
3. The part that would need actual *new* work, not just restoration: an actual UI trigger. Nothing in the deleted code ever called this path from a real button — restoring the plumbing alone reproduces the same dead-code state. A real restore needs a visible "Export anyway" action added to `ScanResultsPage.tsx`, gated on unresolved `Severity::Error` issues specifically (not all issues, matching backend's `ready` semantics) — this UI does not exist anywhere in history and would need to be designed fresh.

## Related

- [[Third Hardening Pass (Pre-Auth-Resume)]]
- [[Frontend v1.1.3 - Test Coverage Expansion]]
