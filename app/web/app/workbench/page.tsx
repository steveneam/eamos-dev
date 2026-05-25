import { Suspense } from 'react'
import { WorkbenchClient } from '@/components/workbench/WorkbenchClient'

// Workbench route (`/workbench`). WorkbenchClient reads query params via
// useSearchParams, which requires a Suspense boundary at build time.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <WorkbenchClient />
    </Suspense>
  )
}
