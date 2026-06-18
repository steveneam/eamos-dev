---
type: project
date: 2026-06-18
---

# Batch Async Upload Progress

Batch C3-on-C1 showed that the reusable capability is the job lifecycle, not the compare page. Keep upload creation, polling, terminal-status detection, and paged result collection in shared Batch client helpers so any surface can render backend `queued`, `running`, `completed`, `failed`, or `cancelled` status with `done` and `total`.

Related: [[batch-async-upload-progress]], [[compare-batch-ui]], [[batch-backend-async-jobs]]

Files:
- `app/web/lib/batch.ts`
- `app/web/lib/variant-file.ts`
- `app/web/components/compare/VariantImport.tsx`
- `app/web/components/compare/CompareClient.tsx`

Lesson: when backend work becomes asynchronous, promote the lifecycle contract into a small shared client primitive before wiring a specific screen.

What's easier now: the next Batch, Workbench, or report-side upload flow can reuse `pollBatchJob` and `collectBatchResults` and only decide how to display progress.
