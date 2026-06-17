'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { WorkRail } from '@/components/layout/WorkRail'
import { RailFoot } from '@/components/layout/RailFoot'
import {
  readCompareVariants,
  stashCompareVariants,
  type CompareStash,
  type ParsedVariant,
} from '@/lib/variant-file'
import { applyFilters, cacheResolvedPanel, type ActiveFilter } from '@/lib/compare-filters'
import { getPanel } from '@/lib/panels'
import { createBatch, getBatchJob } from '@/lib/batch'
import type { BatchFilters, BatchResult, ParsedVariant as BatchVariant } from '@/lib/backend'
import { LibrarySection } from '@/components/library/LibrarySection'
import { ScopeGate } from './ScopeGate'
import { BatchTable, rowFromParsed, rowFromResult } from './BatchTable'
import { VariantImport } from './VariantImport'
import { CompareAiPanel } from './CompareAiPanel'
import { IconScope, IconCheck } from '@/components/icons/Icon'
import './compare.css'

// Stable empty references for the no-cohort scope preview (so the dimmed rail
// doesn't churn props each render).
const NO_VARIANTS: ParsedVariant[] = []
const NO_FILTERS: ActiveFilter[] = []
const noop = () => {}

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
  // Server-computed batch results (real backend); null = none yet / mock-offline.
  const [results, setResults] = useState<BatchResult[] | null>(null)
  // True when the scope changed after a run — the visible output no longer matches
  // the filters, so Regenerate is the prompt (we keep the table rather than wipe it).
  const [stale, setStale] = useState(false)
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
      setResults(null)
      setStale(false)
      try {
        const job = await createBatch({
          variants: variants.map(toBatchVariant),
          filters: toBatchFilters(runFilters),
        })
        if (!job.job_id.startsWith('mock-')) {
          // Poll to completion, then page through the server-computed results.
          let final = await getBatchJob(job.job_id, { limit: 200 })
          for (
            let i = 0;
            i < 30 &&
            final.status !== 'completed' &&
            final.status !== 'failed' &&
            final.status !== 'cancelled' &&
            !(final.total > 0 && final.done >= final.total);
            i++
          ) {
            await new Promise((r) => setTimeout(r, 500))
            final = await getBatchJob(job.job_id, { limit: 200 })
          }
          const collected = [...final.results]
          let cursor = final.page?.next_cursor ?? null
          for (let guard = 0; cursor && guard < 20; guard++) {
            const page = await getBatchJob(job.job_id, { limit: 200, cursor })
            collected.push(...page.results)
            cursor = page.page?.next_cursor ?? null
          }
          if (collected.length > 0) setResults(collected)
        }
      } catch {
        // Offline / network — the mock job + client-side table already cover it.
      }
      setStatus('done')
    },
    [variants],
  )

  // Changing the scope makes the current run stale, but DON'T wipe the table —
  // keep it on screen and surface Regenerate so you can re-run with the new scope
  // (the offline preview re-filters live, so staleness only matters once you've run).
  const changeFilters = (next: ActiveFilter[]) => {
    setFilters(next)
    if (status !== 'idle') setStale(true)
  }

  // Load variants from an in-page import (drop / browse / paste) without bouncing
  // back to the search bar. `merge` appends to the current cohort (dedup by query)
  // so a second VCF combines with the first; otherwise it replaces. Persists to
  // the same sessionStorage stash the search bar writes, then re-renders in place.
  const loadVariants = useCallback(
    (parsed: ParsedVariant[], source: string, merge = false) => {
      if (parsed.length === 0) return
      setStash((prev) => {
        const base = merge && prev ? prev.variants : []
        const seen = new Set(base.map((v) => v.query.toLowerCase()))
        const merged = base.slice()
        for (const v of parsed) {
          const key = v.query.toLowerCase()
          if (seen.has(key)) continue
          seen.add(key)
          merged.push(v)
        }
        const nextSource = merge && prev ? `${prev.source} + ${source}` : source
        stashCompareVariants(merged, nextSource)
        return { savedAt: Date.now(), source: nextSource, variants: merged }
      })
      // The cohort changed — reset to a fresh idle state (re-scope, re-run).
      setStatus('idle')
      setResults(null)
      setStale(false)
    },
    [],
  )

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

      {!hydrated ? null : (
        // One frame for both states. The rail + output column are always mounted,
        // so loading a cohort fills this frame in place instead of swapping a
        // separate centered empty card for the full rail layout. Empty → the import
        // hero sits in the output column and the scope rail shows a dimmed preview;
        // loaded → the toolbar + cohort table, with the scope rail live. No top
        // padding on the shell so the sticky rail clamps flush under the nav and its
        // full-viewport height lands the pinned foot exactly at the bottom (a short
        // page used to push it ~16px past the fold); the output column carries the
        // top/bottom breathing room instead.
        <div>
          <WorkRail
            surface="compare"
            title="Scope"
            aiTitle="Ask Eamos"
            aiPanel={<CompareAiPanel count={variants.length} source={stash?.source} />}
            foot={<RailFoot />}
            output={
              <div style={{ padding: '16px 22px 80px 24px' }}>
                {variants.length === 0 ? (
                  <div style={{ maxWidth: 640, margin: '4px auto 0' }}>
                    <EmptyState onVariants={(v, s) => loadVariants(v, s, false)} />
                  </div>
                ) : (
                  <>
                    {/* Output toolbar — Add file lives here, in the central column
                        (not tucked in the rail corner), so loading another VCF into the
                        cohort is always one click away. The Generate/Regenerate control
                        rides the right once there's output to re-run; on a stale scope
                        it turns solid with a hint so Regenerate gets its moment. */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
                      <VariantImport compact onVariants={(v, s) => loadVariants(v, s, true)} />
                      {status !== 'idle' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                          {stale && status === 'done' && (
                            <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
                              Scope changed — regenerate to apply
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={() => runBatch(filters)}
                            disabled={status === 'running'}
                            className={`cmp-cta ${status === 'running' ? 'cmp-cta--solid cmp-cta--running' : stale ? 'cmp-cta--solid' : 'cmp-cta--done'}`}
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
                    </div>
                    {status === 'idle' ? (
                      <GeneratePrompt
                        count={variants.length}
                        source={stash?.source}
                        scoped={res.activePanels.length > 0}
                        onGenerate={() => runBatch(filters)}
                      />
                    ) : status === 'running' ? (
                      <LoadingCard />
                    ) : results && results.length > 0 ? (
                      <BatchTable
                        rows={results.map(rowFromResult)}
                        annotated
                        activePanels={res.activePanels}
                        panelGenes={res.activePanels.flatMap((p) => p.genes.map((g) => g.symbol))}
                        panelLabel={res.activePanels.map((p) => p.name).join(' + ') || undefined}
                      />
                    ) : res.shown.length === 0 ? (
                      <EmptyScope
                        onClear={() => changeFilters([])}
                        intervalPending={res.intervalPending}
                        total={res.total}
                      />
                    ) : (
                      <BatchTable
                        rows={res.shown.map(rowFromParsed)}
                        annotated={false}
                        activePanels={res.activePanels}
                        panelGenes={res.activePanels.flatMap((p) => p.genes.map((g) => g.symbol))}
                        panelLabel={res.activePanels.map((p) => p.name).join(' + ') || undefined}
                      />
                    )}
                  </>
                )}
              </div>
            }
          >
            {variants.length === 0 ? (
              <>
                <ScopeLockedNotice />
                {/* Dimmed, inert preview of the scope rail — shows what unlocks once a
                    cohort loads (frame continuity) without pretending to be live. */}
                <div style={{ opacity: 0.5, pointerEvents: 'none' }} aria-hidden>
                  <ScopeGate variants={NO_VARIANTS} filters={NO_FILTERS} onChange={noop} />
                </div>
                <LibrarySection />
              </>
            ) : (
              <>
                <ScopeGate variants={variants} filters={filters} onChange={changeFilters} />
                <LibrarySection />
              </>
            )}
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
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', whiteSpace: 'nowrap' }}>Batch</span>
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

/** The idle-with-cohort state. Doubles as the "you added something" confirmation:
 *  a cohort is loaded but not yet run, so it names the count + source with a
 *  success accent (the rail un-dimming alone read as too quiet) and points at the
 *  next step — scope, then generate. */
function GeneratePrompt({
  count,
  source,
  scoped,
  onGenerate,
}: {
  count: number
  source?: string
  scoped: boolean
  onGenerate: () => void
}) {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--teal-bdr)',
        borderTop: '2px solid var(--teal)',
        borderRadius: 14,
        padding: '26px 28px 32px',
        textAlign: 'center',
      }}
    >
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 11px',
          borderRadius: 999,
          background: 'var(--teal-tint)',
          border: '0.5px solid var(--teal-bdr)',
          color: 'var(--teal-deep)',
          fontSize: 11,
          fontWeight: 700,
          fontFamily: 'var(--mono)',
          letterSpacing: '0.03em',
          textTransform: 'uppercase',
        }}
      >
        <IconCheck size={12} /> Cohort loaded
      </span>
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 19, margin: '12px 0 0', color: 'var(--ink)' }}>
        {count} variant{count === 1 ? '' : 's'} ready
        {source ? <span style={{ color: 'var(--ink-3)', fontWeight: 500 }}> · {source}</span> : null}
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--ink-3)', margin: '8px auto 0', maxWidth: 470 }}>
        Scope it with the filters on the left{scoped ? ' (filters applied)' : ''}, then generate to run the
        per-variant lookup. Large VCFs aren’t filtered in real time.
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

function EmptyState({ onVariants }: { onVariants: (variants: ParsedVariant[], source: string) => void }) {
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
        Load a cohort to compare
      </h2>
      <p style={{ fontSize: 13.5, lineHeight: 1.6, margin: '8px 0 18px' }}>
        Drop a variant file here, or browse — a VCF, or a CSV/TSV/plain-text list with one variant
        per line. The parsed cohort appears here, ready to scope and run.
      </p>
      <VariantImport onVariants={onVariants} />
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '16px 0 0' }}>
        Or attach one from the{' '}
        <Link href="/" style={{ color: 'var(--ink-3)', textDecoration: 'underline' }}>
          search bar
        </Link>
        .
      </p>
    </section>
  )
}

/** No-cohort scope-rail header — explains why the scope preview below is dimmed,
 *  so the inert rail reads as "this unlocks with a cohort" rather than broken. */
function ScopeLockedNotice() {
  return (
    <div
      style={{
        margin: '0 0 6px',
        padding: '12px 14px',
        borderRadius: 12,
        border: '0.5px solid var(--line)',
        background: 'var(--bg-soft)',
        color: 'var(--ink-3)',
        fontSize: 12.5,
        lineHeight: 1.5,
      }}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, color: 'var(--ink-2)', marginBottom: 4 }}>
        <IconScope size={13} /> Scope unlocks with a cohort
      </span>
      Drop a file or paste a list to load variants — your gene panels and quality / frequency
      filters become active here.
    </div>
  )
}

function EmptyScope({
  onClear,
  intervalPending,
  total,
}: {
  onClear: () => void
  intervalPending: number
  total: number
}) {
  const pending = intervalPending > 0
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
        {pending ? 'These variants are scoped server-side' : 'No variants match these filters'}
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, margin: '8px 0 0' }}>
        {pending ? (
          <>
            {intervalPending === total ? `All ${total}` : `${intervalPending} of ${total}`} variant
            {intervalPending === 1 ? '' : 's'} are genomic coordinates with no gene symbol, so the panel’s
            gene match runs on the server (MANE→hg38 interval intersection) — they’re pending, not
            excluded. The offline preview can’t map coordinates to panel genes; generate against the live
            backend to resolve them.
          </>
        ) : (
          'None of the named-gene variants fall in the active panel(s). Widen the scope or clear the filters to see the full cohort.'
        )}
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
