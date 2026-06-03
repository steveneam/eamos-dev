import { Suspense } from 'react'
import { CompareClient } from '@/components/compare/CompareClient'

// Multi-variant comparison route (`/compare`). CompareClient renders ModePill,
// which reads search params, so it needs a Suspense boundary at build time.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <CompareClient />
    </Suspense>
  )
}
