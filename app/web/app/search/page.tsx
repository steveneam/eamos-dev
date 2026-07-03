import { Suspense } from 'react'
import type { Metadata } from 'next'
import { SearchResultsClient } from '@/components/search/SearchResultsClient'

export const metadata: Metadata = {
  title: 'Search - Eamos',
  description: 'Authenticated Eamos search results.',
}

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchPageFallback />}>
      <SearchResultsClient />
    </Suspense>
  )
}

function SearchPageFallback() {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-soft)',
        display: 'grid',
        placeItems: 'center',
        color: 'var(--ink-4)',
        fontSize: 13,
      }}
      role="status"
      aria-label="Loading search"
    >
      Loading search
    </div>
  )
}
