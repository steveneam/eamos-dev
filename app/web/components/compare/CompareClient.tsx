'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { readCompareVariants, type CompareStash } from '@/lib/variant-file'
import { applyFilters, type ActiveFilter } from '@/lib/compare-filters'
import { ScopeGate } from './ScopeGate'
import { VariantTable } from './VariantTable'

/**
 * Multi-variant view (`/compare`). Parse a dropped file into a cohort, scope it
 * with the filter bar (live preview of N + est time in the scope summary), then
 * GENERATE to run the lookup. For large VCFs the filter + per-variant lookup runs
 * server-side as a batch job (spec §5.3 scope gate → §5.4 submit), so output is
 * gated behind an explicit button with a running state, not live. The mock
 * simulates the run; the real async engine (done/total progress) is P4/P5.
 */
type RunStatus = 'idle' | 'running' | 'done'

export function CompareClient() {
  const [stash, setStash] = useState<CompareStash | null>(null)
  const [hydrated, setHydrated] = useState(false)
  const [filters, setFilters] = useState<ActiveFilter[]>([])
  const [status, setStatus] = useState<RunStatus>('idle')

  useEffect(() => {
    setStash(readCompareVariants())
    setHydrated(true)
  }, [])

  // Mock run: hold a "running" state briefly so the loading affordance shows.
  // Codex's engine replaces this with real job submit + done/total progress.
  useEffect(() => {
    if (status !== 'running') return
    const t = setTimeout(() => setStatus('done'), 900)
    return () => clearTimeout(t)
  }, [status])

  // Changing the scope invalidates output — you re-run, like resubmitting a job.
  const changeFilters = (next: ActiveFilter[]) => {
    setFilters(next)
    setStatus('idle')
  }

  const variants = stash?.variants ?? []
  const res = applyFilters(variants, filters)

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<ModePill current="report" />} />
      <main
        className="mx-auto"
        style={{ width: '100%', maxWidth: 'var(--maxw-report-frame)', padding: '32px 32px 80px' }}
      >
        <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-2" style={{ fontSize: 12, color: 'var(--ink-4)' }}>
          <Link href="/" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
            Search
          </Link>
          <span style={{ color: 'var(--ink-5)' }}>/</span>
          <span>Compare variants</span>
        </nav>

        <header
          className="mb-5"
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}
        >
          <div>
            <h1
              style={{
                fontFamily: 'var(--display)',
                fontWeight: 400,
                fontSize: 30,
                letterSpacing: '-0.02em',
                color: 'var(--ink)',
                margin: 0,
              }}
            >
              Compare variants
            </h1>
            {hydrated && variants.length > 0 && (
              <p style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink-3)', margin: '6px 0 0' }}>
                {variants.length} variant{variants.length === 1 ? '' : 's'}
                {stash?.source ? ` · from ${stash.source}` : ''}
              </p>
            )}
          </div>

          {hydrated && variants.length > 0 && (
            <button
              type="button"
              onClick={() => setStatus('running')}
              disabled={status === 'running'}
              style={generateBtn(status)}
            >
              {status === 'running' ? (
                <>
                  <Spinner /> Generating…
                </>
              ) : status === 'done' ? (
                'Regenerate →'
              ) : (
                'Generate results →'
              )}
            </button>
          )}
        </header>

        {!hydrated ? null : variants.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <ScopeGate variants={variants} filters={filters} onChange={changeFilters} />
            {status === 'idle' ? (
              <GeneratePrompt scoped={res.activePanels.length > 0} onGenerate={() => setStatus('running')} />
            ) : status === 'running' ? (
              <LoadingCard />
            ) : res.shown.length === 0 ? (
              <EmptyScope onClear={() => changeFilters([])} />
            ) : (
              <VariantTable rows={res.shown} activePanels={res.activePanels} />
            )}
          </>
        )}
      </main>
    </div>
  )
}

function Spinner({ light = true }: { light?: boolean }) {
  return (
    <span
      aria-hidden
      style={{
        display: 'inline-block',
        width: 13,
        height: 13,
        marginRight: 7,
        verticalAlign: '-2px',
        borderRadius: '50%',
        border: `2px solid ${light ? 'rgba(255,255,255,0.4)' : 'var(--line-2)'}`,
        borderTopColor: light ? '#fff' : 'var(--teal-deep)',
        animation: 'eamos-spin 0.7s linear infinite',
      }}
    />
  )
}

function generateBtn(status: RunStatus): React.CSSProperties {
  const done = status === 'done'
  const running = status === 'running'
  return {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '11px 24px',
    borderRadius: 12,
    border: `0.5px solid ${done ? 'var(--teal-bdr)' : 'var(--teal-deep)'}`,
    background: done ? 'var(--teal-tint)' : 'var(--teal-deep)',
    color: done ? 'var(--teal-deep)' : '#fff',
    fontSize: 14,
    fontWeight: 700,
    cursor: running ? 'progress' : 'pointer',
    opacity: running ? 0.85 : 1,
    boxShadow: done || running ? 'none' : '0 6px 18px -8px rgba(21,107,80,0.5)',
  }
}

function GeneratePrompt({ scoped, onGenerate }: { scoped: boolean; onGenerate: () => void }) {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px dashed var(--line-2)',
        borderRadius: 14,
        padding: '36px 28px',
        textAlign: 'center',
      }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 17, margin: 0, color: 'var(--ink)' }}>
        Generate to run the lookup
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--ink-3)', margin: '8px auto 0', maxWidth: 460 }}>
        Large VCFs aren’t filtered in real time. Set your scope above
        {scoped ? ' (filters applied)' : ''}, then generate to run the per-variant lookup.
      </p>
      <button
        type="button"
        onClick={onGenerate}
        style={{
          marginTop: 18,
          padding: '11px 26px',
          borderRadius: 12,
          border: '0.5px solid var(--teal-deep)',
          background: 'var(--teal-deep)',
          color: '#fff',
          fontSize: 14,
          fontWeight: 700,
          cursor: 'pointer',
          boxShadow: '0 6px 18px -8px rgba(21,107,80,0.5)',
        }}
      >
        Generate results →
      </button>
    </section>
  )
}

function LoadingCard() {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '44px 28px',
        textAlign: 'center',
        color: 'var(--ink-2)',
      }}
    >
      <Spinner light={false} />
      <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>Running lookup…</span>
      <p style={{ fontSize: 12.5, lineHeight: 1.6, color: 'var(--ink-4)', margin: '10px auto 0', maxWidth: 420 }}>
        Filtering and looking up your variants. Larger cohorts run as a background job — results appear
        here as they complete.
      </p>
    </section>
  )
}

function EmptyState() {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '28px 28px',
        color: 'var(--ink-2)',
      }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 16, margin: 0, color: 'var(--ink)' }}>
        No variants to compare yet
      </h2>
      <p style={{ fontSize: 13.5, lineHeight: 1.6, margin: '10px 0 0' }}>
        Attach a variant file from the search bar — a VCF, or a CSV/TSV/plain-text list with one
        variant per line — and the parsed variants will appear here.
      </p>
      <Link
        href="/"
        style={{
          display: 'inline-block',
          marginTop: 16,
          padding: '7px 14px',
          borderRadius: 10,
          border: '0.5px solid var(--ink-2)',
          background: 'var(--ink-2)',
          color: '#fff',
          fontSize: 12.5,
          fontWeight: 600,
          textDecoration: 'none',
        }}
      >
        Back to search
      </Link>
    </section>
  )
}

function EmptyScope({ onClear }: { onClear: () => void }) {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '24px 24px',
        color: 'var(--ink-2)',
      }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 15, margin: 0, color: 'var(--ink)' }}>
        No variants match these filters
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, margin: '8px 0 0' }}>
        None of the named-gene variants fall in the active panel(s). Genomic variants without a gene
        symbol are filtered server-side (interval intersection) once the batch engine lands — widen the
        scope or clear the filters to see the full cohort.
      </p>
      <button
        type="button"
        onClick={onClear}
        style={{
          marginTop: 14,
          padding: '7px 14px',
          borderRadius: 10,
          border: '0.5px solid var(--line-2)',
          background: 'var(--bg)',
          color: 'var(--ink-2)',
          fontSize: 12.5,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Clear all filters
      </button>
    </section>
  )
}
