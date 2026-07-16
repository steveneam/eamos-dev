'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { WorkRail } from '@/components/layout/WorkRail'
import { RailFoot } from '@/components/layout/RailFoot'
import {
  clearCompareStash,
  makeSourceId,
  mergeSources,
  readCompareVariants,
  sourcesLabel,
  stashCompareSources,
  type CompareStash,
  type ImportMeta,
  type ImportSource,
  type ParsedVariant,
} from '@/lib/variant-file'
import { applyFilters, cacheResolvedPanel, filterChipLabel, type ActiveFilter } from '@/lib/compare-filters'
import { CLASS_RANK, classifyVerdict, summarizeCohort } from '@/lib/batch-summary'
import type { BatchChatScope } from '@/lib/chat'
import { getPanel } from '@/lib/panels'
import { collectBatchResults, createBatch, pollBatchJob, uploadBatch } from '@/lib/batch'
import type { BatchResult } from '@/lib/backend'
import { LibrarySection } from '@/components/library/LibrarySection'
import { ScopeGate } from './ScopeGate'
import { BatchTable, rowFromParsed, rowFromResult } from './BatchTable'
import {
  isBatchIssue,
  issueCopy,
  progressFromError,
  progressFromJob,
  toBatchFilters,
  toBatchVariant,
  type BatchProgress,
  type RunStatus,
} from './batchRunModel'
import { VariantImport } from './VariantImport'
import { CompareAiPanel } from './CompareAiPanel'
import { IconScope, IconCheck, IconList, IconPlus, IconRemove, IconChevron } from '@/components/icons/Icon'
import './compare.css'

// Stable empty references for the no-cohort scope preview (so the dimmed rail
// doesn't churn props each render).
const NO_VARIANTS: ParsedVariant[] = []
const NO_FILTERS: ActiveFilter[] = []
const NO_SOURCES: ImportSource[] = []
const noop = () => {}

// Max cohort variants sent in the Ask-Eamos bounded sample (the backend caps at
// 100 too) — the classification mix + panel coverage still summarise the whole
// cohort; this only bounds the per-variant list so the prompt window stays tight.
const CHAT_SAMPLE = 60

/** Drop the zero-count classes so the chat's cohort summary stays tight. */
function countsFromDist(dist: Record<string, number>): Record<string, number> {
  return Object.fromEntries(Object.entries(dist).filter(([, n]) => n > 0))
}

/**
 * Multi-variant view (`/compare`). Parse a dropped file into a cohort, scope it
 * with the filter bar (live preview of N + est time in the scope summary), then
 * GENERATE to run the lookup. For large VCFs the filter + per-variant lookup runs
 * server-side as a batch job (spec §5.3 scope gate → §5.4 submit), so output is
 * gated behind an explicit button with a running state, not live. The mock
 * simulates the run; the real async engine (done/total progress) is P4/P5.
 */
export function CompareClient() {
  const searchParams = useSearchParams()
  const [stash, setStash] = useState<CompareStash | null>(null)
  const [hydrated, setHydrated] = useState(false)
  const [filters, setFilters] = useState<ActiveFilter[]>([])
  const [status, setStatus] = useState<RunStatus>('idle')
  // Server-computed batch results; null means none yet or a failed run.
  const [results, setResults] = useState<BatchResult[] | null>(null)
  const [progress, setProgress] = useState<BatchProgress | null>(null)
  // True when the scope changed after a run — the visible output no longer matches
  // the filters, so Regenerate is the prompt (we keep the table rather than wipe it).
  const [stale, setStale] = useState(false)
  // Bumped when a panel's full gene list resolves so applyFilters re-runs.
  const [, bumpCache] = useState(0)
  // The in-place import panel (drop / browse / paste) shown when adding a source
  // to an existing cohort — so you can get back to import without losing output.
  const [addingSource, setAddingSource] = useState(false)
  const loadedSlugs = useRef<Set<string>>(new Set())
  const uploadFilesRef = useRef<Map<string, File>>(new Map())
  const runSeq = useRef(0)

  useEffect(() => {
    setStash(readCompareVariants())
    setHydrated(true)
  }, [])

  useEffect(() => () => {
    runSeq.current += 1
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

  // Generate = submit a batch job + poll to completion. Oversized single-file
  // VCF imports keep their original File in memory, so Generate can hand the
  // backend an upload_ref instead of the browser-capped preview rows.
  const runBatch = useCallback(
    async (runFilters: ActiveFilter[]) => {
      const runId = runSeq.current + 1
      runSeq.current = runId
      const isCurrentRun = () => runSeq.current === runId
      setStatus('running')
      setResults(null)
      setProgress(null)
      setStale(false)
      try {
        const filtersPayload = toBatchFilters(runFilters)
        const uploadSource = stash?.sources.length === 1 ? stash.sources[0] : null
        const uploadFile =
          uploadSource?.clientTruncated ? uploadFilesRef.current.get(uploadSource.id) : undefined
        let usedUpload = false
        let job: Awaited<ReturnType<typeof createBatch>>

        if (uploadFile) {
          setProgress({
            stage: 'uploading',
            done: 0,
            total: uploadSource?.clientParsedCount ?? variants.length,
            usedUpload: true,
          })
          const upload = await uploadBatch(uploadFile)
          usedUpload = true
          job = await createBatch({
            upload_ref: upload.upload_ref,
            filters: filtersPayload,
          })
        } else {
          job = await createBatch({
            variants: variants.map(toBatchVariant),
            filters: filtersPayload,
          })
        }

        if (!isCurrentRun()) return
        setProgress({
          stage: 'queued',
          jobId: job.job_id,
          done: 0,
          total: job.n_to_lookup,
          nInput: job.n_input,
          nToLookup: job.n_to_lookup,
          estSeconds: job.est_seconds,
          usedUpload,
        })
        const final = await pollBatchJob(job.job_id, {
          limit: 200,
          onUpdate: (next) => {
            if (isCurrentRun()) setProgress(progressFromJob(next, usedUpload))
          },
          shouldContinue: isCurrentRun,
        })
        if (!isCurrentRun()) return
        setProgress(progressFromJob(final, usedUpload))
        if (final.status !== 'completed') {
          setResults(null)
          return
        }
        const collected = await collectBatchResults(final, { limit: 200, shouldContinue: isCurrentRun })
        if (isCurrentRun()) setResults(collected)
      } catch (error) {
        if (!isCurrentRun()) return
        setProgress((prev) => progressFromError(error, prev, variants.length))
      }
      if (isCurrentRun()) setStatus('done')
    },
    [stash?.sources, variants],
  )

  // Changing the scope makes the current run stale, but DON'T wipe the table —
  // keep it on screen and surface Regenerate so you can re-run with the new scope
  // (the offline preview re-filters live, so staleness only matters once you've run).
  const changeFilters = (next: ActiveFilter[]) => {
    setFilters(next)
    if (status !== 'idle') setStale(true)
  }

  // The cohort changed (source added / removed / cleared) — reset to a fresh idle
  // state so the user re-scopes and re-runs against the new inputs.
  const resetRun = useCallback(() => {
    runSeq.current += 1
    setStatus('idle')
    setResults(null)
    setProgress(null)
    setStale(false)
  }, [])

  // Load variants from an in-page import (drop / browse / paste) without bouncing
  // back to the search bar. `merge` appends the import as a NEW source (tracked
  // individually for provenance); otherwise it replaces the cohort. Persists to
  // the same sessionStorage stash the search bar writes, then re-renders in place.
  const loadVariants = useCallback(
    (parsed: ParsedVariant[], meta: ImportMeta, merge = false) => {
      if (parsed.length === 0) return
      const source: ImportSource = {
        id: makeSourceId(),
        name: meta.name,
        kind: meta.kind,
        text: meta.text,
        variants: parsed,
        clientTruncated: meta.clientTruncated,
        clientParseLimit: meta.clientParseLimit,
        clientParsedCount: meta.clientParsedCount,
      }
      if (!merge) uploadFilesRef.current.clear()
      if (meta.uploadFile) uploadFilesRef.current.set(source.id, meta.uploadFile)
      setStash((prev) => {
        const sources = merge && prev ? [...prev.sources, source] : [source]
        stashCompareSources(sources)
        return { savedAt: Date.now(), source: sourcesLabel(sources), variants: mergeSources(sources), sources }
      })
      resetRun()
    },
    [resetRun],
  )

  // Remove one source — the deduped cohort re-derives from what remains; removing
  // the last one returns to the empty import state.
  const removeSource = useCallback(
    (id: string) => {
      uploadFilesRef.current.delete(id)
      setStash((prev) => {
        if (!prev) return prev
        const sources = prev.sources.filter((s) => s.id !== id)
        if (sources.length === 0) {
          clearCompareStash()
          uploadFilesRef.current.clear()
          return null
        }
        stashCompareSources(sources)
        return { savedAt: Date.now(), source: sourcesLabel(sources), variants: mergeSources(sources), sources }
      })
      resetRun()
    },
    [resetRun],
  )

  // Start over — drop the whole cohort + scope and return to the import hero.
  const clearCohort = useCallback(() => {
    clearCompareStash()
    uploadFilesRef.current.clear()
    setStash(null)
    setFilters([])
    setAddingSource(false)
    resetRun()
  }, [resetRun])

  // Sample-VCF deep link (/compare?demo=1) — auto-generate the dropped cohort
  // once it hydrates so the landing pill lands on a populated result.
  const autoRan = useRef(false)
  useEffect(() => {
    if (autoRan.current || searchParams.get('demo') !== '1' || !hydrated || variants.length === 0) return
    autoRan.current = true
    runBatch([])
  }, [searchParams, hydrated, variants.length, runBatch])

  // Ask-Eamos cohort scope — a bounded summary of the resolved cohort (size +
  // source/panel/filter provenance + classification mix + the most actionable
  // variants), mirroring the backend BatchContext. Built from the rows the table
  // shows: server-annotated results when present, else the scoped preview. Null
  // until a cohort loads, so the rail's chat stays idle until there's something to
  // ground in. Reuses the pure cohort summariser; never carries the raw VCF/INFO.
  const batchScope: BatchChatScope | null = (() => {
    if (variants.length === 0) return null
    const panels = res.activePanels.map((p) => p.name)
    const panelGenes = res.activePanels.flatMap((p) => p.genes.map((g) => g.symbol))
    const filterLabels = filters.filter((f) => f.kind !== 'panel').map((f) => filterChipLabel(f))
    const sources = (stash?.sources ?? []).map((s) => s.name).slice(0, 24)

    if (results && results.length > 0) {
      const rank = (r: BatchResult) =>
        CLASS_RANK[classifyVerdict(r.acmg_classification, r.clinvar_verdict)]
      const summary = summarizeCohort(
        results.map((r) => ({
          variant_key: r.variant_key,
          gene: r.gene,
          acmg_classification: r.acmg_classification,
          clinvar_verdict: r.clinvar_verdict,
        })),
        panelGenes,
      )
      return {
        variant_count: results.length,
        annotated: true,
        sources,
        panels,
        filters: filterLabels,
        classification_counts: countsFromDist(summary.classDist),
        panel_missing_genes: summary.panel?.missedGenes ?? [],
        variants: results
          .slice()
          .sort((a, b) => rank(a) - rank(b))
          .slice(0, CHAT_SAMPLE)
          .map((r) => ({
            gene: r.gene ?? null,
            variant: r.hgvs_c ?? r.variant_key,
            clinical_significance: r.clinvar_verdict ?? null,
            acmg_classification: r.acmg_classification ?? null,
            classification: classifyVerdict(r.acmg_classification, r.clinvar_verdict),
            gnomad_af: r.gnomad_af ?? null,
          })),
      }
    }

    const shown = res.shown
    const summary = summarizeCohort(
      shown.map((v) => ({ variant_key: v.query, gene: v.gene })),
      panelGenes,
    )
    return {
      variant_count: shown.length,
      annotated: false,
      sources,
      panels,
      filters: filterLabels,
      classification_counts: countsFromDist(summary.classDist),
      panel_missing_genes: summary.panel?.missedGenes ?? [],
      variants: shown
        .slice(0, CHAT_SAMPLE)
        .map((v) => ({ gene: v.gene ?? null, variant: v.variant ?? v.query })),
    }
  })()
  const runWarnings = progress?.warnings ?? []
  const completedEmpty = Array.isArray(results) && results.length === 0 && progress?.stage === 'completed'

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
            aiPanel={<CompareAiPanel batch={batchScope} />}
            foot={<RailFoot />}
            output={
              <div style={{ padding: '16px 22px 80px 24px' }}>
                {variants.length === 0 ? (
                  <div style={{ maxWidth: 640, margin: '4px auto 0' }}>
                    <EmptyState onVariants={(v, meta) => loadVariants(v, meta, false)} />
                  </div>
                ) : (
                  <>
                    {/* Sources — every input that produced this cohort, always on
                        screen so its provenance is auditable. Remove one, add more
                        (drop / browse / paste, in place), or start over. */}
                    <SourcesBar
                      sources={stash?.sources ?? NO_SOURCES}
                      total={variants.length}
                      addingOpen={addingSource}
                      onToggleAdd={() => setAddingSource((o) => !o)}
                      onRemove={removeSource}
                      onClear={clearCohort}
                    />
                    {addingSource && (
                      <div style={{ marginBottom: 14 }}>
                        <VariantImport
                          onVariants={(v, meta) => {
                            loadVariants(v, meta, true)
                            setAddingSource(false)
                          }}
                        />
                      </div>
                    )}
                    {/* The Generate/Regenerate control rides the right once there's
                        output to re-run; on a stale scope it turns solid with a hint. */}
                    {status !== 'idle' && (
                      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 12, marginBottom: 14 }}>
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
                    {status === 'idle' ? (
                      <GeneratePrompt
                        count={variants.length}
                        source={stash?.source}
                        scoped={res.activePanels.length > 0}
                        onGenerate={() => runBatch(filters)}
                      />
                    ) : status === 'running' ? (
                      <LoadingCard progress={progress} />
                    ) : isBatchIssue(progress?.stage) && progress ? (
                      <>
                        <BatchRunIssue progress={progress} />
                        {res.shown.length === 0 ? (
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
                    ) : completedEmpty && progress ? (
                      <>
                        {stale && <StaleRunNotice />}
                        <BatchEmptyRun progress={progress} onClear={() => changeFilters([])} />
                      </>
                    ) : results && results.length > 0 ? (
                      <>
                        {stale && <StaleRunNotice />}
                        <BatchWarnings warnings={runWarnings} />
                        <BatchTable
                          rows={results.map(rowFromResult)}
                          annotated
                          activePanels={res.activePanels}
                          panelGenes={res.activePanels.flatMap((p) => p.genes.map((g) => g.symbol))}
                          panelLabel={res.activePanels.map((p) => p.name).join(' + ') || undefined}
                        />
                      </>
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

function LoadingCard({ progress }: { progress: BatchProgress | null }) {
  const done = Math.max(0, progress?.done ?? 0)
  const total = Math.max(0, progress?.total ?? 0)
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0
  const statusLabel =
    progress?.stage === 'uploading'
      ? 'Uploading VCF'
      : progress?.status === 'queued' || progress?.stage === 'queued'
        ? 'Queued'
        : progress?.status === 'running' || progress?.stage === 'running'
          ? 'Running lookup'
          : progress?.status === 'completed' || progress?.stage === 'completed'
            ? 'Completed'
            : 'Preparing job'

  return (
    <section
      aria-live="polite"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '24px 26px',
        color: 'var(--ink-2)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
          <Spinner light={false} />
          <span style={{ fontSize: 14, fontWeight: 650, color: 'var(--ink)' }}>{statusLabel}</span>
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
          {total > 0 ? `${done} / ${total}` : 'waiting'}
          {progress?.usedUpload ? ' · server parsed' : ''}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label="Batch lookup progress"
        aria-valuemin={0}
        aria-valuemax={total || 100}
        aria-valuenow={total > 0 ? done : undefined}
        style={{
          position: 'relative',
          height: 9,
          borderRadius: 999,
          background: 'var(--bg-soft2)',
          border: '0.5px solid var(--line)',
          overflow: 'hidden',
          marginTop: 15,
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            width: `${pct}%`,
            background: 'var(--teal-deep)',
            borderRadius: 999,
            transition: 'width var(--dur-2) var(--ease-standard)',
          }}
        />
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 11, fontSize: 11.5, color: 'var(--ink-4)' }}>
        {progress?.nInput != null && <span>Input {progress.nInput.toLocaleString()}</span>}
        {progress?.nToLookup != null && <span>Lookup {progress.nToLookup.toLocaleString()}</span>}
        {progress?.estSeconds != null && progress.estSeconds > 0 && <span>Est. {Math.ceil(progress.estSeconds)}s</span>}
        {progress?.jobId && <span style={{ fontFamily: 'var(--mono)' }}>{progress.jobId}</span>}
      </div>
    </section>
  )
}

function BatchRunIssue({ progress }: { progress: BatchProgress }) {
  const copy = issueCopy(progress)
  return (
    <section
      role="alert"
      style={{
        background: copy.tone === 'error' ? 'var(--err-tint)' : 'var(--warn-tint)',
        border: `0.5px solid ${copy.tone === 'error' ? 'var(--err-bdr, var(--err))' : 'var(--warn-bdr)'}`,
        borderRadius: 14,
        padding: '20px 22px',
        color: copy.tone === 'error' ? 'var(--err)' : 'var(--warn-text)',
        marginBottom: 14,
      }}
    >
      <h2 style={{ fontSize: 14, fontWeight: 650, color: 'inherit', margin: 0 }}>{copy.title}</h2>
      <p style={{ fontSize: 12.5, lineHeight: 1.6, margin: '7px 0 0' }}>
        {copy.body}
      </p>
      {progress.done > 0 || progress.total > 0 ? (
        <p style={{ fontFamily: 'var(--mono)', fontSize: 11.5, margin: '9px 0 0' }}>
          {progress.done} / {progress.total} variants completed
        </p>
      ) : null}
      <BatchWarnings warnings={progress.warnings ?? []} compact />
    </section>
  )
}

function BatchEmptyRun({ progress, onClear }: { progress: BatchProgress; onClear: () => void }) {
  const nInput = progress.nInput ?? 0
  const nAfterFilters = progress.nAfterFilters ?? progress.nToLookup ?? 0
  return (
    <section
      aria-live="polite"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '22px 24px',
        color: 'var(--ink-2)',
      }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 15, margin: 0, color: 'var(--ink)' }}>
        No variants to annotate after filters
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, margin: '8px 0 0', color: 'var(--ink-3)' }}>
        The Batch run completed, but the active scope removed every input variant. Widen the scope or clear the filters, then regenerate.
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 11, fontSize: 11.5, color: 'var(--ink-4)' }}>
        {nInput > 0 && <span>Input {nInput.toLocaleString()}</span>}
        <span>After filters {nAfterFilters.toLocaleString()}</span>
        {progress.jobId && <span style={{ fontFamily: 'var(--mono)' }}>{progress.jobId}</span>}
      </div>
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
      <BatchWarnings warnings={progress.warnings ?? []} compact />
    </section>
  )
}

function StaleRunNotice() {
  return (
    <section
      aria-live="polite"
      style={{
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 12,
        padding: '10px 13px',
        marginBottom: 12,
        color: 'var(--warn-text)',
        fontSize: 12.5,
        lineHeight: 1.45,
      }}
    >
      Showing the previous Batch run. Regenerate to apply the current scope.
    </section>
  )
}

function BatchWarnings({ warnings, compact = false }: { warnings: string[]; compact?: boolean }) {
  const unique = Array.from(new Set(warnings.filter(Boolean)))
  if (unique.length === 0) return null
  const shown = unique.slice(0, compact ? 3 : 5)
  const remaining = unique.length - shown.length
  return (
    <section
      aria-label="Batch warnings"
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 8,
        flexWrap: 'wrap',
        margin: compact ? '12px 0 0' : '0 0 12px',
        padding: compact ? 0 : '9px 11px',
        borderRadius: compact ? undefined : 12,
        border: compact ? undefined : '0.5px solid var(--line)',
        background: compact ? undefined : 'var(--bg-soft)',
      }}
    >
      <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--ink-4)' }}>
        Warnings
      </span>
      {shown.map((warning) => (
        <span
          key={warning}
          title={warning}
          style={{
            maxWidth: 260,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontFamily: 'var(--mono)',
            fontSize: 10.5,
            color: 'var(--ink-3)',
            padding: '2px 6px',
            borderRadius: 6,
            border: '0.5px solid var(--line-2)',
            background: 'var(--bg)',
          }}
        >
          {warning}
        </span>
      ))}
      {remaining > 0 && (
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>+{remaining} more</span>
      )}
    </section>
  )
}

function sourceActionBtn(active: boolean): React.CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
    padding: '5px 10px',
    borderRadius: 9,
    border: `0.5px solid ${active ? 'var(--teal-bdr)' : 'var(--line-2)'}`,
    background: active ? 'var(--teal-tint)' : 'var(--bg)',
    color: active ? 'var(--teal-deep)' : 'var(--ink-2)',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
  }
}

/** The always-on provenance strip: every input that produced the cohort, with a
 *  per-source remove, an Add (drop / browse / paste in place), and Start over. */
function SourcesBar({
  sources,
  total,
  addingOpen,
  onToggleAdd,
  onRemove,
  onClear,
}: {
  sources: ImportSource[]
  total: number
  addingOpen: boolean
  onToggleAdd: () => void
  onRemove: (id: string) => void
  onClear: () => void
}) {
  return (
    <section style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 7 }}>
          <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-4)' }}>
            Sources
          </span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
            {sources.length} · {total} variant{total === 1 ? '' : 's'}
          </span>
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button type="button" onClick={onToggleAdd} aria-expanded={addingOpen} style={sourceActionBtn(addingOpen)}>
            <IconPlus size={12} /> {addingOpen ? 'Close' : 'Add'}
          </button>
          <button type="button" onClick={onClear} title="Clear the cohort and start over" style={sourceActionBtn(false)}>
            Start over
          </button>
        </div>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {sources.map((s) => (
          <SourceChip key={s.id} source={s} onRemove={() => onRemove(s.id)} />
        ))}
      </div>
    </section>
  )
}

/** One source chip: name + its own variant count + remove. Pasted-text sources
 *  expand to show exactly what was typed (the source-consistency record). */
function SourceChip({ source, onRemove }: { source: ImportSource; onRemove: () => void }) {
  const [open, setOpen] = useState(false)
  const viewable = source.kind === 'paste' && !!source.text
  const nameStyle: React.CSSProperties = { maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }
  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', maxWidth: '100%' }}>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '5px 6px 5px 9px',
          borderRadius: 9,
          border: '0.5px solid var(--line-2)',
          background: 'var(--bg)',
          fontSize: 12,
          color: 'var(--ink)',
          maxWidth: '100%',
        }}
      >
        <span aria-hidden style={{ color: 'var(--ink-4)', display: 'inline-flex' }}>
          <IconList size={12} />
        </span>
        {viewable ? (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            title="View the pasted text"
            style={{ ...nameStyle, display: 'inline-flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', padding: 0, font: 'inherit', color: 'var(--ink)', cursor: 'pointer' }}
          >
            {source.name}
            <span
              aria-hidden
              style={{ display: 'inline-flex', color: 'var(--ink-4)', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .15s ease' }}
            >
              <IconChevron size={11} />
            </span>
          </button>
        ) : (
          <span style={nameStyle} title={source.name}>
            {source.name}
          </span>
        )}
        <span
          title={
            source.clientTruncated
              ? `${source.variants.length} shown in preview; full file parses on Generate`
              : undefined
          }
          style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: source.clientTruncated ? 'var(--teal-deep)' : 'var(--ink-4)' }}
        >
          {source.clientTruncated ? `${source.variants.length}+` : source.variants.length}
        </span>
        <button
          type="button"
          aria-label={`Remove ${source.name}`}
          onClick={onRemove}
          title="Remove this source"
          style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 18, height: 18, borderRadius: 5, border: 'none', background: 'transparent', color: 'var(--ink-4)', cursor: 'pointer' }}
        >
          <IconRemove size={13} />
        </button>
      </span>
      {source.clientTruncated && (
        <span style={{ margin: '5px 0 0 4px', fontSize: 10.5, color: 'var(--ink-4)' }}>
          Full file runs server-side
        </span>
      )}
      {viewable && open && (
        <pre
          style={{
            margin: '6px 0 0',
            padding: '8px 10px',
            maxHeight: 160,
            maxWidth: 340,
            overflow: 'auto',
            borderRadius: 8,
            border: '0.5px solid var(--line-2)',
            background: 'var(--bg-soft)',
            fontFamily: 'var(--mono)',
            fontSize: 11,
            lineHeight: 1.5,
            color: 'var(--ink-2)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {source.text}
        </pre>
      )}
    </div>
  )
}

function EmptyState({ onVariants }: { onVariants: (variants: ParsedVariant[], meta: ImportMeta) => void }) {
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
