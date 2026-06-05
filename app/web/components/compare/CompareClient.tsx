'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { WorkRail } from '@/components/layout/WorkRail'
import { readCompareVariants, type CompareStash } from '@/lib/variant-file'
import { applyFilters, cacheResolvedPanel, type ActiveFilter } from '@/lib/compare-filters'
import { getPanel } from '@/lib/panels'
import { createBatch, getBatchJob } from '@/lib/batch'
import type { BatchFilters, ParsedVariant as BatchVariant } from '@/lib/backend'
import { ScopeGate } from './ScopeGate'
import { VariantTable } from './VariantTable'
import './compare.css'

/**
 * Multi-variant view (`/compare`). Parse a dropped file into a cohort, scope it
 * with the filter bar (live preview of N + est time in the scope summary), then
 * GENERATE to run the lookup. For large VCFs the filter + per-variant lookup runs
 * server-side as a batch job (spec §5.3 scope gate → §5.4 submit), so output is
 * gated behind an explicit button with a running state, not live. The mock
 * simulates the run; the real async engine (done/total progress) is P4/P5.
 */
type RunStatus = 'idle' | 'running' | 'done'

/** Map a browser-parsed cohort row to the backend batch variant shape. */
function toBatchVariant(v: { raw: string; gene: string | null; variant: string | null; query: string }): BatchVariant {
  return { raw: v.raw, query: v.query, gene: v.gene, variant: v.variant, warnings: [] }
}

/** Translate the active scope chips into the batch filter payload. */
function toBatchFilters(filters: ActiveFilter[]): BatchFilters {
  const out: BatchFilters = {}
  const panel = filters.find((f) => f.kind === 'panel' && f.panelSlug)
  if (panel?.panelSlug) out.panel_slug = panel.panelSlug
  if (filters.some((f) => f.kind === 'pass')) out.pass_only = true
  const regions = filters.filter((f) => f.kind === 'region' && f.region).map((f) => f.region as string)
  if (regions.length) out.regions = regions
  const af = filters.find((f) => f.kind === 'af')
  if (af?.maxAf != null) out.max_af = af.maxAf
  return out
}

export function CompareClient() {
  const searchParams = useSearchParams()
  const [stash, setStash] = useState<CompareStash | null>(null)
  const [hydrated, setHydrated] = useState(false)
  const [filters, setFilters] = useState<ActiveFilter[]>([])
  const [status, setStatus] = useState<RunStatus>('idle')
  // Bumped when a panel's full gene list resolves so applyFilters re-runs.
  const [, bumpCache] = useState(0)
  const loadedSlugs = useRef<Set<string>>(new Set())

  useEffect(() => {
    setStash(readCompareVariants())
    setHydrated(true)
  }, [])

  const variants = useMemo(() => stash?.variants ?? [], [stash])
  const res = applyFilters(variants, filters)

  // Resolve full panels (genes) for active preset chips → the shared cache, so
  // client-side membership uses real panel genes (mock fallback when offline).
  useEffect(() => {
    for (const f of filters) {
      if (f.kind === 'panel' && f.panelSlug && !loadedSlugs.current.has(f.panelSlug)) {
        const slug = f.panelSlug
        loadedSlugs.current.add(slug)
        getPanel(slug).then((p) => {
          if (p) {
            cacheResolvedPanel(p)
            bumpCache((v) => v + 1)
          }
        })
      }
    }
  }, [filters])

  // Generate = submit a batch job + poll to completion. The backend's immediate
  // in-memory summary path returns done==total at once; offline it falls back to
  // a mock job and the client-side table (already computed) stands in.
  const runBatch = useCallback(
    async (runFilters: ActiveFilter[]) => {
      setStatus('running')
      try {
        const job = await createBatch({
          variants: variants.map(toBatchVariant),
          filters: toBatchFilters(runFilters),
        })
        if (!job.job_id.startsWith('mock-')) {
          for (let i = 0; i < 30; i++) {
            const j = await getBatchJob(job.job_id)
            if (j.status !== 'queued' && j.status !== 'running') break
            if (j.total > 0 && j.done >= j.total) break
            await new Promise((r) => setTimeout(r, 500))
          }
        }
      } catch {
        // Offline / network — the mock job + client-side table already cover it.
      }
      setStatus('done')
    },
    [variants],
  )

  // Changing the scope invalidates output — you re-run, like resubmitting a job.
  const changeFilters = (next: ActiveFilter[]) => {
    setFilters(next)
    setStatus('idle')
  }

  // Sample-VCF deep link (/compare?demo=1) — auto-generate the dropped cohort
  // once it hydrates so the landing pill lands on a populated result.
  const autoRan = useRef(false)
  useEffect(() => {
    if (autoRan.current || searchParams.get('demo') !== '1' || !hydrated || variants.length === 0) return
    autoRan.current = true
    runBatch([])
  }, [searchParams, hydrated, variants.length, runBatch])

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<ModePill current="compare" />}>
        <NavContext count={hydrated ? variants.length : 0} source={stash?.source} />
      </TopNav>

      {!hydrated ? null : variants.length === 0 ? (
        <main
          className="mx-auto"
          style={{ width: '100%', maxWidth: 'var(--maxw-report-frame)', padding: '40px 32px 80px' }}
        >
          <EmptyState />
        </main>
      ) : (
        <div style={{ maxWidth: 'var(--maxw-workbench)', margin: '0 auto', padding: '16px 24px 80px' }}>
          <WorkRail
            surface="compare"
            title="Scope"
            output={
              <div style={{ padding: '0 0 0 24px' }}>
                {/* The idle GeneratePrompt card already carries the CTA — only show
                    the top Generate/Regenerate control once there's output to re-run,
                    so the idle state doesn't leave a lone button over empty space. */}
                {status !== 'idle' && (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
                    <button
                      type="button"
                      onClick={() => runBatch(filters)}
                      disabled={status === 'running'}
                      className={`cmp-cta ${status === 'done' ? 'cmp-cta--done' : 'cmp-cta--solid'}${status === 'running' ? ' cmp-cta--running' : ''}`}
                    >
                      {status === 'running' ? (
                        <>
                          <Spinner /> Generating…
                        </>
                      ) : (
                        'Regenerate →'
                      )}
                    </button>
                  </div>
                )}
                {status === 'idle' ? (
                  <GeneratePrompt scoped={res.activePanels.length > 0} onGenerate={() => runBatch(filters)} />
                ) : status === 'running' ? (
                  <LoadingCard />
                ) : res.shown.length === 0 ? (
                  <EmptyScope onClear={() => changeFilters([])} />
                ) : (
                  <VariantTable rows={res.shown} activePanels={res.activePanels} />
                )}
              </div>
            }
          >
            <ScopeGate variants={variants} filters={filters} onChange={changeFilters} />
          </WorkRail>
        </div>
      )}
    </div>
  )
}

/** Page context shown in the nav center (breadcrumb + title + cohort size) so
 *  the body leads straight with the output — no tall header band above it. */
function NavContext({ count, source }: { count: number; source?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0 }}>
      <Link href="/" style={{ fontSize: 12.5, color: 'var(--ink-4)', textDecoration: 'none', whiteSpace: 'nowrap' }}>
        Search
      </Link>
      <span style={{ color: 'var(--ink-5)' }}>/</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', whiteSpace: 'nowrap' }}>Compare variants</span>
      {count > 0 && (
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11.5,
            color: 'var(--ink-4)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          · {count} variant{count === 1 ? '' : 's'}
          {source ? ` · ${source}` : ''}
        </span>
      )}
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
      <button type="button" onClick={onGenerate} className="cmp-cta cmp-cta--solid" style={{ marginTop: 18 }}>
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
