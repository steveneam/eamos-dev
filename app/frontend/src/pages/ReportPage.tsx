import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { SearchShell, type SearchSubmit } from '@/components/search/SearchShell'
import { VariantHeader } from '@/components/report/VariantHeader'
import { VariantDecoder } from '@/components/report/VariantDecoder'
import { AIStack } from '@/components/aistack/AIStack'
import { EvidenceTable } from '@/components/report/EvidenceTable'
import { DiseaseSection } from '@/components/report/DiseaseSection'
import { TrialsSection } from '@/components/report/TrialsSection'
import { PubMedSection } from '@/components/report/PubMedSection'
import { LimitationsSection } from '@/components/report/LimitationsSection'
import { LocusContext } from '@/components/report/LocusContext'
import { InSilicoGrid } from '@/components/report/InSilicoGrid'
import { AcmgCriteriaFold } from '@/components/report/AcmgCriteriaFold'
import { CuratedVariantsGrid } from '@/components/report/CuratedVariantsGrid'
import { AssociatedConditions } from '@/components/report/AssociatedConditions'
import { PublicationsCallout } from '@/components/report/PublicationsCallout'
import { Card } from '@/components/ui/Card'
import { variantLookup } from '@/lib/api'
import { RPE65_SAMPLE } from '@/lib/sample-report'
import { SOURCES } from '@/lib/sources'
import type { LookupResponse } from '@/lib/backend'

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; data: LookupResponse }
  | { kind: 'error'; message: string }
  | { kind: 'offline' }

export function ReportPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const gene = params.get('gene')?.trim() ?? ''
  const cdna = params.get('cdna')?.trim() ?? ''
  const demo = params.get('demo') !== null

  const [state, setState] = useState<LoadState>({ kind: 'idle' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false

    if (demo || (!gene && !cdna)) {
      setState({ kind: 'ready', data: RPE65_SAMPLE })
      return
    }

    if (!gene || !cdna) {
      setState({
        kind: 'error',
        message: 'Both a gene and a cDNA (or HGVS) change are required.',
      })
      return
    }

    setState({ kind: 'loading' })
    variantLookup({ gene, cdna, species: 'human' })
      .then((data) => {
        if (!cancelled) setState({ kind: 'ready', data })
      })
      .catch((err: Error) => {
        if (cancelled) return
        // fetch() throws TypeError for connection-refused / DNS / CORS — i.e.
        // the dev backend isn't running. 4xx/5xx responses come through
        // parseResponse as a plain Error and route to the generic branch.
        if (err instanceof TypeError) {
          setState({ kind: 'offline' })
        } else {
          setState({ kind: 'error', message: err.message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [gene, cdna, demo, attempt])

  const handleSearch = (payload: SearchSubmit) => {
    if (payload.mode === 'lookup') {
      const p = new URLSearchParams({ gene: payload.gene, cdna: payload.variant })
      navigate(`/report?${p.toString()}`)
    } else {
      const p = new URLSearchParams({ q: payload.query, mode: 'ai' })
      navigate(`/report?${p.toString()}`)
    }
  }

  const initialGene = gene
  const initialVariant = cdna

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<ModePill current="report" />}>
        <div className="mx-auto" style={{ maxWidth: 620 }}>
          <SearchShell
            variant="nav"
            initialGene={initialGene}
            initialVariant={initialVariant}
            onSubmit={handleSearch}
          />
        </div>
      </TopNav>

      <main className="mx-auto px-8" style={{ maxWidth: 920, padding: '32px 32px 80px' }}>
        {state.kind === 'loading' && <LoadingBlock query={`${gene} ${cdna}`.trim()} />}
        {state.kind === 'error' && (
          <ErrorBlock
            variant="generic"
            message={state.message}
            query={`${gene} ${cdna}`.trim()}
            canRetry={Boolean(gene && cdna)}
            onRetry={() => setAttempt((n) => n + 1)}
          />
        )}
        {state.kind === 'offline' && (
          <ErrorBlock
            variant="offline"
            query={`${gene} ${cdna}`.trim()}
            canRetry={Boolean(gene && cdna)}
            onRetry={() => setAttempt((n) => n + 1)}
          />
        )}
        {state.kind === 'ready' && (
          <ReportBody data={state.data} query={`${gene} ${cdna}`.trim() || state.data.query} />
        )}
      </main>
    </div>
  )
}

interface ReportBodyProps {
  data: LookupResponse
  query: string
}

function ReportBody({ data, query }: ReportBodyProps) {
  const payload = data.report_payload
  const contextLabel =
    payload.variant_summary_rows[0]?.gene && payload.variant_summary_rows[0]?.protein_change
      ? `${payload.variant_summary_rows[0].gene} ${payload.variant_summary_rows[0].protein_change}`
      : query

  return (
    <div className="flex flex-col gap-3.5">
      <VariantHeader payload={payload} query={query} />
      <AIStack payload={payload} runId={null} contextLabel={contextLabel} />

      <Card number={2} title="Locus context" meta="ClinVar · ±40bp window">
        <LocusContext />
      </Card>

      <Card number={3} title="Evidence by source" meta="live · last refreshed 2 min ago">
        <InSilicoGrid />
        <EvidenceTable evidence={data.evidence} embedded />
        <AcmgCriteriaFold />
      </Card>

      <Card number={4} title="Gene context & associated conditions" meta="RPE65 · NM_000329.3">
        <DiseaseSection payload={payload} embedded />
        <CuratedVariantsGrid />
        <AssociatedConditions />
        <PublicationsCallout />
      </Card>

      <VariantDecoder decoder={payload.variant_decoder} number={5} />
      <TrialsSection payload={payload} number={6} />
      <PubMedSection articles={payload.pubmed_articles} number={7} />
      <LimitationsSection text={payload.limitations} number={8} />
    </div>
  )
}

function LoadingBlock({ query }: { query: string }) {
  return (
    <section
      aria-busy="true"
      aria-live="polite"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '28px 32px',
      }}
    >
      <header className="flex items-center gap-3">
        <span
          aria-hidden
          style={{
            width: 18,
            height: 18,
            border: '2px solid var(--line)',
            borderTopColor: 'var(--teal)',
            borderRadius: '50%',
            animation: 'eamos-spin 0.9s linear infinite',
          }}
        />
        <div>
          <div
            className="uppercase"
            style={{
              fontSize: 10.5,
              fontWeight: 600,
              letterSpacing: '0.1em',
              color: 'var(--ink-4)',
            }}
          >
            Looking up variant
          </div>
          <div
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 14,
              color: 'var(--ink)',
              marginTop: 2,
            }}
          >
            {query || '—'}
          </div>
        </div>
      </header>

      <ul
        className="mt-5 grid gap-2"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', listStyle: 'none', padding: 0, margin: 0 }}
      >
        {SOURCES.map((src, i) => (
          <li
            key={src.key}
            className="flex items-center gap-2"
            style={{
              padding: '8px 12px',
              background: 'var(--bg-soft)',
              border: '0.5px solid var(--line)',
              borderRadius: 10,
              fontSize: 12.5,
              color: 'var(--ink-3)',
            }}
          >
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: 999,
                background: 'var(--teal)',
                animation: `eamos-pulse 1.6s ease-in-out ${i * 0.18}s infinite`,
              }}
            />
            {src.label}
          </li>
        ))}
      </ul>

      <p
        className="mt-5"
        style={{ fontSize: 12, color: 'var(--ink-4)', margin: '20px 0 0' }}
      >
        Real-API queries can take up to ~15 seconds; mock mode returns instantly.
      </p>

      <style>{`
        @keyframes eamos-spin { to { transform: rotate(360deg); } }
        @keyframes eamos-pulse {
          0%, 100% { opacity: 0.35; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.25); }
        }
      `}</style>
    </section>
  )
}

interface ErrorBlockProps {
  variant: 'generic' | 'offline'
  message?: string
  query: string
  canRetry: boolean
  onRetry: () => void
}

function ErrorBlock({ variant, message, query, canRetry, onRetry }: ErrorBlockProps) {
  const isOffline = variant === 'offline'
  const title = isOffline ? 'Backend offline' : 'Lookup failed'

  return (
    <section
      role="alert"
      style={{
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 14,
        padding: '24px 28px',
        color: 'var(--ink)',
      }}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="inline-flex shrink-0 items-center justify-center"
          style={{
            width: 28,
            height: 28,
            borderRadius: 999,
            background: 'var(--bg)',
            border: '0.5px solid var(--warn-bdr)',
            color: 'var(--warn)',
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <h2
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 600,
              fontSize: 16,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
              margin: 0,
            }}
          >
            {title}
          </h2>
          {query && (
            <div
              className="mt-1"
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 12.5,
                color: 'var(--ink-3)',
              }}
            >
              {query}
            </div>
          )}
          {isOffline ? (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
              }}
            >
              The Eamos backend isn't responding on{' '}
              <code
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 12.5,
                  background: 'var(--bg)',
                  border: '0.5px solid var(--line)',
                  padding: '1px 6px',
                  borderRadius: 4,
                }}
              >
                localhost:8000
              </code>
              . Start it from{' '}
              <code
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 12.5,
                  background: 'var(--bg)',
                  border: '0.5px solid var(--line)',
                  padding: '1px 6px',
                  borderRadius: 4,
                }}
              >
                app/backend
              </code>{' '}
              with{' '}
              <code
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 12.5,
                  background: 'var(--bg)',
                  border: '0.5px solid var(--line)',
                  padding: '1px 6px',
                  borderRadius: 4,
                }}
              >
                python -m uvicorn app.main:create_app --factory --reload
              </code>
              .
            </p>
          ) : (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
                wordBreak: 'break-word',
              }}
            >
              {message}
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {canRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 transition-colors"
                style={{
                  padding: '7px 14px',
                  borderRadius: 10,
                  border: '0.5px solid var(--ink-2)',
                  background: 'var(--ink-2)',
                  color: '#fff',
                  fontSize: 12.5,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Try again
              </button>
            )}
            <Link
              to="/"
              style={{
                padding: '7px 14px',
                borderRadius: 10,
                border: '0.5px solid var(--line-2)',
                background: 'var(--bg)',
                color: 'var(--ink-2)',
                fontSize: 12.5,
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              Back to search
            </Link>
            {!isOffline && (
              <Link
                to="/report?demo=1"
                style={{
                  fontSize: 12,
                  color: 'var(--ink-3)',
                  textDecoration: 'underline',
                  textUnderlineOffset: 3,
                  marginLeft: 4,
                }}
              >
                View the RPE65 sample report instead
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
