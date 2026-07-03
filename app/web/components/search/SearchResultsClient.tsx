'use client'

import { useEffect, useMemo, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { AuthMenu } from '@/components/auth/AuthMenu'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { TopNav } from '@/components/layout/TopNav'
import { searchEamos, SearchRequestError } from '@/lib/search/api'
import { searchHrefForQuery } from '@/lib/variant-search'
import type { SearchDocType, SearchHit, SearchResponse } from '@/lib/backend'

type SearchState =
  | { kind: 'idle' }
  | { kind: 'loading'; query: string }
  | { kind: 'ready'; query: string; data: SearchResponse }
  | { kind: 'error'; query: string; error: SearchRequestError | Error }

type SearchFetchState = Extract<SearchState, { kind: 'ready' | 'error' }>

type SafeTarget = { href: string; external: boolean }

const DOC_LABELS: Record<SearchDocType, string> = {
  report: 'Report',
  run: 'Run',
  library_variant: 'Saved variant',
  popular_variant: 'Popular variant',
  publication: 'Publication',
  trial: 'Trial',
  report_section: 'Report section',
  gene: 'Gene',
  condition: 'Condition',
  gene_disease: 'Gene disease',
  source: 'Source',
}

const MATCH_LABELS: Record<SearchHit['match_type'], string> = {
  exact_run_id: 'Run ID',
  exact_report_id: 'Report ID',
  exact_patient_id: 'Patient ID',
  exact_variant: 'Variant',
  full_text: 'Text',
}

const METADATA_ORDER = [
  'gene',
  'query',
  'classification',
  'pmid',
  'nct_id',
  'source_version',
  'status',
  'tier',
  'disease_id',
  'view_count',
  'publication_count',
  'trial_count',
] as const

export function SearchResultsClient() {
  const router = useRouter()
  const params = useSearchParams()
  const query = params.get('q')?.trim() ?? ''
  const [fetchState, setFetchState] = useState<SearchFetchState | null>(null)

  useEffect(() => {
    if (!query) return

    const controller = new AbortController()
    searchEamos({ query, limit: 20 }, { signal: controller.signal })
      .then((data) => {
        setFetchState({ kind: 'ready', query, data })
      })
      .catch((error: Error) => {
        if (error.name === 'AbortError') return
        setFetchState({ kind: 'error', query, error })
      })

    return () => controller.abort()
  }, [query])

  const state: SearchState =
    !query
      ? { kind: 'idle' }
      : fetchState?.query === query
        ? fetchState
        : { kind: 'loading', query }

  const handleSubmit = (raw: string) => {
    const href = searchHrefForQuery(raw)
    if (href) router.push(href)
  }

  const resultCount =
    state.kind === 'ready' ? state.data.results.length : state.kind === 'idle' ? 0 : null

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<AuthMenu tone="light" />}>
        <div className="mx-auto" style={{ width: '100%', maxWidth: 760 }}>
          <EamosSearch size="compact" tone="light" onSubmit={handleSubmit} />
        </div>
      </TopNav>

      <main
        style={{
          width: '100%',
          maxWidth: 980,
          margin: '0 auto',
          padding: '34px 20px 56px',
        }}
      >
        <header style={{ display: 'grid', gap: 8, marginBottom: 18 }}>
          <div className="eamos-kicker">Search</div>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              gap: 16,
              flexWrap: 'wrap',
            }}
          >
            <h1
              style={{
                margin: 0,
                fontFamily: 'var(--display)',
                fontWeight: 400,
                fontSize: 28,
                lineHeight: 1.16,
                color: 'var(--ink)',
              }}
            >
              {query ? 'Search results' : 'Search Eamos'}
            </h1>
            {resultCount !== null && query && (
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 12,
                  color: 'var(--ink-4)',
                }}
              >
                {resultCount} {resultCount === 1 ? 'result' : 'results'}
              </span>
            )}
          </div>
          {query ? (
            <p
              style={{
                margin: 0,
                fontSize: 14,
                color: 'var(--ink-3)',
                overflowWrap: 'anywhere',
              }}
            >
              Query: <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>{query}</span>
            </p>
          ) : (
            <p style={{ margin: 0, fontSize: 14, color: 'var(--ink-3)' }}>
              Search indexed Eamos records from the bar above.
            </p>
          )}
        </header>

        {state.kind === 'idle' && <EmptyQueryPanel />}
        {state.kind === 'loading' && <LoadingPanel query={state.query} />}
        {state.kind === 'error' && <ErrorPanel query={state.query} error={state.error} />}
        {state.kind === 'ready' &&
          (state.data.results.length > 0 ? (
            <SearchResultList results={state.data.results} />
          ) : (
            <NoResultsPanel query={state.query} />
          ))}
      </main>
    </div>
  )
}

function SearchResultList({ results }: { results: SearchHit[] }) {
  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {results.map((hit) => (
        <SearchResultCard key={hit.source_key} hit={hit} />
      ))}
    </div>
  )
}

function SearchResultCard({ hit }: { hit: SearchHit }) {
  const target = safeTarget(hit.target_href)
  const metadata = useMemo(() => metadataBadges(hit), [hit])
  const updatedAt = formatDate(hit.updated_at)
  const visibilityLabel = hit.visibility_scope === 'private' ? 'Workspace' : titleCase(hit.visibility_scope)

  return (
    <article
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-lg)',
        boxShadow: 'var(--elev-1)',
        padding: '18px 20px',
        display: 'grid',
        gap: 12,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 14,
        }}
        className="flex-col sm:flex-row"
      >
        <div style={{ minWidth: 0, display: 'grid', gap: 6 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            <Badge>{DOC_LABELS[hit.doc_type]}</Badge>
            <Badge muted>{MATCH_LABELS[hit.match_type]}</Badge>
            <Badge muted>{visibilityLabel}</Badge>
          </div>
          <h2
            style={{
              margin: 0,
              fontSize: 17,
              lineHeight: 1.3,
              fontWeight: 650,
              color: 'var(--ink)',
              overflowWrap: 'anywhere',
            }}
          >
            {hit.title}
          </h2>
          {hit.subtitle && (
            <p
              style={{
                margin: 0,
                color: 'var(--ink-3)',
                fontSize: 13,
                lineHeight: 1.45,
                overflowWrap: 'anywhere',
              }}
            >
              {hit.subtitle}
            </p>
          )}
        </div>
        <ResultAction target={target} />
      </div>

      {hit.snippet && (
        <p
          style={{
            margin: 0,
            color: 'var(--ink-2)',
            fontSize: 13.5,
            lineHeight: 1.55,
            overflowWrap: 'anywhere',
          }}
        >
          {hit.snippet}
        </p>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
          borderTop: '0.5px solid var(--line)',
          paddingTop: 10,
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {metadata.map(([key, value]) => (
            <Badge key={key} muted>
              {labelForMetadata(key)}: {value}
            </Badge>
          ))}
        </div>
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: 'var(--ink-4)',
            overflowWrap: 'anywhere',
          }}
        >
          {updatedAt ?? hit.source_key}
        </span>
      </div>
    </article>
  )
}

function ResultAction({ target }: { target: SafeTarget | null }) {
  const style = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 34,
    padding: '7px 13px',
    borderRadius: 'var(--r-md)',
    border: '0.5px solid var(--line-2)',
    background: target ? 'var(--ink-2)' : 'var(--bg-soft)',
    color: target ? 'var(--bg)' : 'var(--ink-4)',
    textDecoration: 'none',
    fontSize: 12.5,
    fontWeight: 600,
    whiteSpace: 'nowrap' as const,
  }

  if (!target) {
    return <span style={style}>No route</span>
  }
  if (target.external) {
    return (
      <a href={target.href} target="_blank" rel="noopener noreferrer" style={style}>
        Open source
      </a>
    )
  }
  return (
    <Link href={target.href} style={style}>
      Open result
    </Link>
  )
}

function EmptyQueryPanel() {
  return (
    <StatePanel title="No query entered" tone="neutral">
      Search for a gene, condition, source, publication, trial, or saved variant from the bar above.
    </StatePanel>
  )
}

function LoadingPanel({ query }: { query: string }) {
  return (
    <section
      role="status"
      aria-busy="true"
      aria-label={`Searching ${query}`}
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-lg)',
        boxShadow: 'var(--elev-1)',
        padding: 20,
        display: 'grid',
        gap: 12,
      }}
    >
      {[0, 1, 2].map((item) => (
        <div
          key={item}
          style={{
            height: item === 0 ? 22 : 52,
            borderRadius: 'var(--r-md)',
            background: 'var(--bg-soft2)',
            opacity: 1 - item * 0.16,
          }}
        />
      ))}
    </section>
  )
}

function NoResultsPanel({ query }: { query: string }) {
  return (
    <StatePanel title="No indexed results" tone="neutral">
      No result matched <QueryInline query={query} />. Structured variants still open a report when the query includes a gene and HGVS change.
    </StatePanel>
  )
}

function ErrorPanel({ query, error }: { query: string; error: SearchRequestError | Error }) {
  if (error instanceof SearchRequestError) {
    if (error.code === 'auth_required' || error.code === 'auth_expired') {
      return (
        <StatePanel title="Sign in required" tone="warning">
          <span>
            Search requires an authenticated session. Your query <QueryInline query={query} /> is still in the URL.
          </span>
          <div style={{ marginTop: 14 }}>
            <Link href="/auth" style={buttonLinkStyle}>
              Sign in
            </Link>
          </div>
        </StatePanel>
      )
    }
    if (error.code === 'rate_limited') {
      return (
        <StatePanel title="Search limit reached" tone="warning">
          {error.retryAfter
            ? `Try again after ${error.retryAfter} seconds.`
            : 'Wait a moment, then run the search again.'}
        </StatePanel>
      )
    }
    if (error.code === 'validation') {
      return (
        <StatePanel title="Query could not be accepted" tone="warning">
          {error.message}
        </StatePanel>
      )
    }
  }

  return (
    <StatePanel title="Search unavailable" tone="error">
      {error.message || 'The search backend could not be reached.'}
    </StatePanel>
  )
}

function StatePanel({
  title,
  tone,
  children,
}: {
  title: string
  tone: 'neutral' | 'warning' | 'error'
  children: ReactNode
}) {
  const warning = tone === 'warning'
  const error = tone === 'error'
  return (
    <section
      role={warning || error ? 'alert' : 'status'}
      style={{
        background: warning ? 'var(--warn-tint)' : error ? 'var(--err-tint)' : 'var(--bg)',
        border: `0.5px solid ${warning ? 'var(--warn-bdr)' : error ? 'var(--err)' : 'var(--line)'}`,
        borderRadius: 'var(--r-lg)',
        boxShadow: tone === 'neutral' ? 'var(--elev-1)' : 'none',
        padding: '20px 22px',
        color: 'var(--ink)',
      }}
    >
      <h2
        style={{
          margin: 0,
          fontSize: 16,
          lineHeight: 1.25,
          fontWeight: 650,
          color: error ? 'var(--err)' : 'var(--ink)',
        }}
      >
        {title}
      </h2>
      <div style={{ marginTop: 8, fontSize: 13.5, lineHeight: 1.6, color: 'var(--ink-2)' }}>
        {children}
      </div>
    </section>
  )
}

function QueryInline({ query }: { query: string }) {
  return <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink)' }}>{query}</span>
}

function Badge({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        minHeight: 22,
        padding: '2px 8px',
        borderRadius: 999,
        border: `0.5px solid ${muted ? 'var(--line)' : 'var(--teal-bdr)'}`,
        background: muted ? 'var(--bg-soft)' : 'var(--teal-tint)',
        color: muted ? 'var(--ink-3)' : 'var(--teal-deep)',
        fontSize: 11,
        fontWeight: 600,
        lineHeight: 1.2,
      }}
    >
      {children}
    </span>
  )
}

const buttonLinkStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: 34,
  padding: '7px 14px',
  borderRadius: 'var(--r-md)',
  border: '0.5px solid var(--ink-2)',
  background: 'var(--ink-2)',
  color: 'var(--bg)',
  textDecoration: 'none',
  fontSize: 12.5,
  fontWeight: 600,
} as const

function safeTarget(targetHref: string | null | undefined): SafeTarget | null {
  const trimmed = targetHref?.trim()
  if (!trimmed) return null
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) {
    return { href: trimmed, external: false }
  }
  try {
    const url = new URL(trimmed)
    if (url.protocol === 'https:') return { href: url.toString(), external: true }
  } catch {
    return null
  }
  return null
}

function metadataBadges(hit: SearchHit): Array<[string, string]> {
  const badges: Array<[string, string]> = []
  for (const key of METADATA_ORDER) {
    const value = hit.metadata[key]
    const formatted = formatMetadataValue(value)
    if (formatted) badges.push([key, formatted])
    if (badges.length >= 4) break
  }
  return badges
}

function formatMetadataValue(value: SearchHit['metadata'][string]): string | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  return String(value)
}

function labelForMetadata(key: string): string {
  return key.replace(/_/g, ' ')
}

function titleCase(value: string): string {
  return value ? `${value.slice(0, 1).toUpperCase()}${value.slice(1)}` : value
}

function formatDate(raw: string | null | undefined): string | null {
  if (!raw) return null
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat('en-AU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}
