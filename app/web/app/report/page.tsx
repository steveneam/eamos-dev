import { Suspense } from 'react'
import { ReportClient } from '@/components/report/ReportClient'
import { SurfaceLoadingShell } from '@/components/layout/SurfaceLoadingShell'

// Variant Evidence Report route (`/report`). ReportClient reads the query via
// useSearchParams, which requires a Suspense boundary at build time.
export default function Page() {
  return (
    <Suspense fallback={<SurfaceLoadingShell surface="report" />}>
      <ReportClient />
    </Suspense>
  )
}
