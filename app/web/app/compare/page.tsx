import { Suspense } from 'react'
import { CompareClient } from '@/components/compare/CompareClient'
import { SurfaceLoadingShell } from '@/components/layout/SurfaceLoadingShell'

// Multi-variant comparison route (`/compare`). CompareClient renders ModePill,
// which reads search params, so it needs a Suspense boundary at build time.
export default function Page() {
  return (
    <Suspense fallback={<SurfaceLoadingShell surface="compare" />}>
      <CompareClient />
    </Suspense>
  )
}
