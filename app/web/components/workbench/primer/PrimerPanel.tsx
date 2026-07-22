'use client'

import { useRef, useState } from 'react'
import type {
  PrimerMode,
  PrimerPair,
  PrimerRequest,
  PrimerResponse,
  WorkbenchDesignContextV1,
} from '@/lib/backend'
import { designPrimers } from '@/lib/api'
import { canonicalJson, sha256Hex } from '@/lib/workbench/design-context'
import { parsePrimerConstraints, primerErrorMessage } from '@/lib/workbench/primer-form'
import { disclosureChipClass, disclosureView } from '@/lib/workbench/source-disclosure'
import type { WorkbenchDerivedResultV1 } from '@/lib/workbench/workspace'
import { PrimerResultCard } from './PrimerResultCard'

interface PrimerPanelProps {
  gene: string
  cdna: string
  /** Pair toggled "show on gene view" + its setter (drives the viewer overlay). */
  selected?: PrimerPair | null
  onSelect?: (pair: PrimerPair | null) => void
  designContext: WorkbenchDesignContextV1 | null
  restoredResultDigest?: string
  restoredDerivedResult?: WorkbenchDerivedResultV1
  onResultDigest?: (digest: string, summary: WorkbenchDerivedResultV1) => void
  executionBlockedReason: string | null
}

const MODES: Array<{ v: PrimerMode; label: string; tip: string }> = [
  {
    v: 'sanger',
    label: 'Sanger',
    tip: 'Sanger sequencing primers — flank the target with a larger amplicon for clean reads across the variant.',
  },
  {
    v: 'qpcr',
    label: 'qPCR',
    tip: 'qPCR primers — a short amplicon optimised for quantitative / real-time PCR.',
  },
]

/** Honest loading: the request is a single synchronous call, so we show one
 *  pending state with the real phases it covers — not a fabricated per-stage
 *  ticker (DESIGN.md principle #4 / plans/primer-integration.md §4.3). */
const PHASES = ['Constraints', 'Primer3 thermodynamics', 'Specificity screen']

function downloadText(filename: string, content: string, mediaType: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: `${mediaType};charset=utf-8` }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function primerTsv(response: PrimerResponse): string {
  const header = [
    'index', 'forward', 'reverse', 'tm_forward', 'tm_reverse', 'gc_forward',
    'gc_reverse', 'product_size', 'specificity_hits', 'structure_risk',
  ]
  const rows = response.pairs.map((pair) => [
    pair.index, pair.forward, pair.reverse, pair.tm_forward, pair.tm_reverse,
    pair.gc_forward, pair.gc_reverse, pair.product_size, pair.specificity_hits,
    pair.secondary_structure_risk ?? 'not_assessed',
  ].join('\t'))
  return [header.join('\t'), ...rows].join('\n')
}

function primerFasta(response: PrimerResponse): string {
  return response.pairs.flatMap((pair) => [
    `>pair_${pair.index}_forward`, pair.forward,
    `>pair_${pair.index}_reverse`, pair.reverse,
  ]).join('\n')
}

/**
 * Primer tool panel — the first reference implementation of the DESIGN.md
 * Dashboard Interaction Language (plans/primer-integration.md §5). Requests
 * execute only against an operational backend provider.
 * Mirrors `CrisprPanel`. Sits in the shared Workbench shell below the viewer.
 */
export function PrimerPanel({
  gene,
  cdna,
  selected,
  onSelect,
  designContext,
  restoredResultDigest,
  restoredDerivedResult,
  onResultDigest,
  executionBlockedReason,
}: PrimerPanelProps) {
  const [mode, setMode] = useState<PrimerMode>('sanger')
  const [tmMin, setTmMin] = useState('58')
  const [tmMax, setTmMax] = useState('62')
  const [prodMin, setProdMin] = useState('300')
  const [prodMax, setProdMax] = useState('700')
  const [avoidSnps, setAvoidSnps] = useState(true)

  const [res, setRes] = useState<PrimerResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runDigest, setRunDigest] = useState<string | null>(null)
  const [cancelled, setCancelled] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const clearRunState = () => {
    setRes(null)
    setError(null)
    setRunDigest(null)
    setCancelled(false)
  }

  const chooseMode = (nextMode: PrimerMode) => {
    if (loading) return
    setMode(nextMode)
    clearRunState()
  }

  const updateConstraint = (
    setter: (nextValue: string) => void,
    nextValue: string,
  ) => {
    setter(nextValue)
    clearRunState()
  }

  const run = async () => {
    if (loading) return

    setError(null)
    setRes(null)
    setCancelled(false)
    if (!designContext) {
      setError('Resolve a source-backed selection before running primer design.')
      return
    }
    if (executionBlockedReason) {
      setError(executionBlockedReason)
      return
    }

    const parsedConstraints = parsePrimerConstraints({
      tmMin,
      tmMax,
      productMin: prodMin,
      productMax: prodMax,
    })
    if (!parsedConstraints.ok) {
      setError(parsedConstraints.error)
      return
    }

    setLoading(true)
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const constraints = parsedConstraints.values
      const payload: PrimerRequest = {
        gene,
        cdna,
        design_context: designContext,
        mode,
        tm_min: constraints.tmMin,
        tm_max: constraints.tmMax,
        product_size_min: constraints.productMin,
        product_size_max: constraints.productMax,
        avoid_snps: avoidSnps,
      }
      const r = await designPrimers(payload, { signal: controller.signal })
      if (r.mode !== mode) throw new Error('The primer provider returned an incompatible mode.')
      const resultDigest = await sha256Hex(canonicalJson({
        context_digest: designContext.context_digest,
        request: payload,
        response: r,
      }))
      const summary: WorkbenchDerivedResultV1 = {
        schema_version: 'workbench_derived_result.v1',
        tool: 'primer',
        context_digest: designContext.context_digest,
        result_digest: resultDigest,
        recorded_at: new Date().toISOString(),
        title: `${r.pairs.length} ${mode} primer pair${r.pairs.length === 1 ? '' : 's'}`,
        metrics: {
          mode,
          pair_count: r.pairs.length,
          recommended_pair: r.pairs.find((pair) => pair.recommended)?.index ?? null,
          provider: r.source_disclosure?.provider_label ?? 'unavailable',
          specificity_scope: 'template_or_provider_reported',
        },
      }
      setRes(r)
      setRunDigest(designContext.context_digest)
      onResultDigest?.(resultDigest, summary)
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        setCancelled(true)
        return
      }
      const msg = primerErrorMessage(e)
      setRes(null)
      setError(msg)
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
        setLoading(false)
      }
    }
  }

  const sourceDisclosure = res
    ? disclosureView(res.source_disclosure, {
        source_status: 'unavailable',
        provider_id: 'workbench_primer_unverified',
        provider_label: 'Unverified primer provider',
      })
    : null
  const resultIsStale = Boolean(
    runDigest && (!designContext || runDigest !== designContext.context_digest),
  )

  return (
    <div className="primer-panel">
      <div className="tool-panel-head">
        <div>
          <h2 className="tool-panel-title">Primer design &amp; validation</h2>
          <span className="tool-panel-sub">
            Primer3 thermodynamics · in-template / UCSC isPcr specificity
          </span>
        </div>
        <div className="seg" role="tablist" aria-label="Primer mode">
          {MODES.map((m) => (
            <button
              key={m.v}
              type="button"
              role="tab"
              aria-selected={mode === m.v}
              className={mode === m.v ? 'active' : ''}
              onClick={() => chooseMode(m.v)}
              disabled={loading}
              title={m.tip}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="tool-form">
        <label className="field" title="Lowest acceptable primer melting temperature (°C).">
          <span className="field-label">Tm min (°C)</span>
          <input
            className="field-input"
            type="number"
            min={45}
            max={75}
            step={0.1}
            value={tmMin}
            onChange={(e) => updateConstraint(setTmMin, e.currentTarget.value)}
            disabled={loading}
          />
        </label>
        <label
          className="field"
          title="Highest acceptable primer melting temperature (°C). Keep the min–max window tight so forward and reverse anneal at one temperature."
        >
          <span className="field-label">Tm max (°C)</span>
          <input
            className="field-input"
            type="number"
            min={45}
            max={75}
            step={0.1}
            value={tmMax}
            onChange={(e) => updateConstraint(setTmMax, e.currentTarget.value)}
            disabled={loading}
          />
        </label>
        <label className="field" title="Smallest acceptable PCR amplicon size (bp).">
          <span className="field-label">Product min (bp)</span>
          <input
            className="field-input"
            type="number"
            min={50}
            max={2000}
            step={10}
            value={prodMin}
            onChange={(e) => updateConstraint(setProdMin, e.currentTarget.value)}
            disabled={loading}
          />
        </label>
        <label className="field" title="Largest acceptable PCR amplicon size (bp).">
          <span className="field-label">Product max (bp)</span>
          <input
            className="field-input"
            type="number"
            min={50}
            max={2000}
            step={10}
            value={prodMax}
            onChange={(e) => updateConstraint(setProdMax, e.currentTarget.value)}
            disabled={loading}
          />
        </label>
        <label
          className="field"
          title="Avoid placing primer 3′ ends over known SNPs, which can cause allele dropout."
        >
          <span className="field-label">Avoid SNPs</span>
          <select
            className="field-select"
            value={avoidSnps ? 'yes' : 'no'}
            onChange={(e) => {
              setAvoidSnps(e.currentTarget.value === 'yes')
              clearRunState()
            }}
            disabled={loading}
          >
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </label>
      </div>

      <div className="btn-row">
        <button
          type="button"
          className="btn-teal primer-go"
          onClick={run}
          disabled={loading || !designContext || Boolean(executionBlockedReason)}
          title="Run Primer3 thermodynamics + the specificity screen to design and validate primer pairs for this target."
        >
          {loading ? 'Designing…' : 'Generate & validate'}
        </button>
        {loading ? (
          <button
            type="button"
            className="align-read-btn"
            onClick={() => abortRef.current?.abort()}
          >
            Cancel
          </button>
        ) : null}
        <span className="tool-panel-sub">
          {gene} · {cdna} · {MODES.find((m) => m.v === mode)?.label}
        </span>
      </div>

      {loading && (
        <div className="primer-phases" aria-live="polite">
          {PHASES.map((p) => (
            <span key={p} className="primer-phase">
              <i className="primer-phase-dot" />
              {p}
            </span>
          ))}
        </div>
      )}

      <div className="help-note">
        Constraints and SNP-avoidance are
        passed to the design engine; real mode runs local Primer3 with an
        in-template specificity screen; whole-genome UCSC isPcr remains gated.
        This is not an NCBI Primer-BLAST validation.
      </div>

      <div className="workbench-context-binding" role="note">
        {designContext
          ? `Bound to ${designContext.selection.chrom}:${designContext.selection.genomic_start.toLocaleString('en-US')}-${designContext.selection.genomic_end.toLocaleString('en-US')} · ${designContext.selection.sequence_basis} · revision ${designContext.selection.edit_revision}`
          : 'Exact source-backed context is unresolved. Primer requests are disabled.'}
      </div>

      {executionBlockedReason ? (
        <div className="workbench-stale" role="alert">{executionBlockedReason}</div>
      ) : null}
      {cancelled ? (
        <div className="workbench-context-binding" role="status">
          Primer design cancelled. No result was saved.
        </div>
      ) : null}

      {resultIsStale ? (
        <div className="workbench-stale" role="status">
          Previous primer results are retained but stale because the selection or edit revision changed.
        </div>
      ) : null}

      {!res && restoredResultDigest && restoredDerivedResult ? (
        <div className="workbench-context-binding" role="note">
          Retained derived summary: {restoredDerivedResult.title} · result {restoredResultDigest.slice(0, 10)}. Primer sequences are not persisted; rerun to restore them.
        </div>
      ) : null}
      {!res && restoredResultDigest && !restoredDerivedResult ? (
        <div className="workbench-context-binding" role="note">
          This tab retained only prior primer result identity ({restoredResultDigest.slice(0, 10)}). Rerun to restore details.
        </div>
      ) : null}

      {error && <div className="primer-error">{error}</div>}

      {res && (
        <>
          {sourceDisclosure && (
            <div className="workbench-source-line" role="note">
              <span
                className={`workbench-source-chip ${disclosureChipClass(sourceDisclosure.status)}`}
              >
                {sourceDisclosure.statusLabel}
              </span>
              <span>{sourceDisclosure.providerLabel}</span>
              {sourceDisclosure.cacheStatus && (
                <span className="workbench-source-muted">
                  {sourceDisclosure.cacheStatus}
                </span>
              )}
            </div>
          )}
          <div className="primer-feed">
            {res.pairs.map((p) => (
              <div key={p.index} className="primer-feed-item">
                <PrimerResultCard
                  pair={p}
                  selected={selected?.index === p.index}
                  onToggleOverlay={() =>
                    onSelect?.(selected?.index === p.index ? null : p)
                  }
                />
              </div>
            ))}
            {res.pairs.length === 0 && (
              <div className="primer-empty">
                No primer pairs satisfied the constraints. Widen the Tm or
                product-size window and try again.
              </div>
            )}
          </div>
          <div className="workbench-export-row" aria-label="Primer exports">
            <button type="button" onClick={() => downloadText(`${gene}-primers.tsv`, primerTsv(res), 'text/tab-separated-values')}>Export TSV</button>
            <button type="button" onClick={() => downloadText(`${gene}-primers.fasta`, primerFasta(res), 'text/plain')}>Export FASTA</button>
            <button
              type="button"
              onClick={() => downloadText(
                `${gene}-primer-manifest.json`,
                JSON.stringify({
                  schema_version: 'workbench_primer_manifest.v1',
                  gene,
                  cdna,
                  context_digest: runDigest,
                  mode: res.mode,
                  pair_count: res.pairs.length,
                  source_disclosure: res.source_disclosure ?? null,
                  generated_at: new Date().toISOString(),
                }, null, 2),
                'application/json',
              )}
            >
              Export manifest
            </button>
          </div>
        </>
      )}

      {!res && !loading && !error && (
        <div className="primer-prompt">
          Set your constraints and run <b>Generate &amp; validate</b> to design
          primer pairs for {gene} {cdna}. Each pair resolves into a one-glance
          verdict, the core thermodynamics, and an audit drawer.
        </div>
      )}
    </div>
  )
}
