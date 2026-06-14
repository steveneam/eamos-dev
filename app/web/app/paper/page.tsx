import { Suspense } from 'react'
import type { Metadata } from 'next'
import { PaperClient } from '@/components/paper/PaperClient'

export const metadata: Metadata = {
  title: 'Paper → Variants',
  description:
    'Extract variant mentions from a publication and resolve each through Eamos source-backed candidate resolution. Research use only.',
}

// Paper → Variants intake route (`/paper`). PaperClient renders ModePill, which
// reads search params, so it needs a Suspense boundary at build time.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <PaperClient />
    </Suspense>
  )
}
