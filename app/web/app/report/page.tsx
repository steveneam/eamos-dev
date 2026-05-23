import { Suspense } from 'react'
import { ReportClient } from '@/components/report/ReportClient'

// Variant Evidence Report route (`/report`). ReportClient reads the query via
// useSearchParams, which requires a Suspense boundary at build time.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <ReportClient />
    </Suspense>
  )
}
