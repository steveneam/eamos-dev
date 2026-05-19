import { useState } from 'react'
import type { PrimerMode, PrimerRequest, PrimerResponse } from '@/lib/backend'
import { designPrimers } from '@/lib/api'
import { PrimerResultCard } from './PrimerResultCard'

interface PrimerPanelProps {
  gene: string
  cdna: string
}

const MODES: Array<{ v: PrimerMode; label: string }> = [
  { v: 'sanger', label: 'Sanger' },
  { v: 'qpcr', label: 'qPCR' },
  { v: 'arms', label: 'ARMS' },
]

/** Honest loading: the request is a single synchronous call, so we show one
 *  pending state with the real phases it covers — not a fabricated per-stage
 *  ticker (DESIGN.md principle #4 / plans/primer-integration.md §4.3). */
const PHASES = ['Constraints', 'Primer3 thermodynamics', 'Specificity screen']

const ARMS_MARKERS = ['primer_mode_arms', 'arms']

/**
 * Primer tool panel — the first reference implementation of the DESIGN.md
 * Dashboard Interaction Language (plans/primer-integration.md §5). Mock-first
 * against the frozen `POST /api/v1/primer` contract; no contract/schema edits.
 * Mirrors `CrisprPanel`. Sits in the shared Workbench shell below the viewer.
 */
export function PrimerPanel({ gene, cdna }: PrimerPanelProps) {
  const [mode, setMode] = useState<PrimerMode>('sanger')
  const [tmMin, setTmMin] = useState(58)
  const [tmMax, setTmMax] = useState(62)
  const [prodMin, setProdMin] = useState(300)
  const [prodMax, setProdMax] = useState(700)
  const [avoidSnps, setAvoidSnps] = useState(true)

  const [res, setRes] = useState<PrimerResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [armsUnsupported, setArmsUnsupported] = useState(false)

  const run = async () => {
    setLoading(true)
    setError(null)
    setArmsUnsupported(false)
    try {
      const payload: PrimerRequest = {
        gene,
        cdna,
        mode,
        tm_min: tmMin,
        tm_max: tmMax,
        product_size_min: prodMin,
        product_size_max: prodMax,
        avoid_snps: avoidSnps,
      }
      const r = await designPrimers(payload)
      setRes(r)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Primer design failed'
      if (mode === 'arms' && ARMS_MARKERS.some((m) => msg.toLowerCase().includes(m))) {
        setArmsUnsupported(true)
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  // Offline mock always serves the Sanger fixture; flag the honest mismatch.
  const mockModeMismatch = res !== null && res.mode !== mode

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
              onClick={() => setMode(m.v)}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="tool-form">
        <label className="field">
          <span className="field-label">Tm min (°C)</span>
          <input
            className="field-input"
            type="number"
            min={45}
            max={75}
            value={tmMin}
            onChange={(e) => setTmMin(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span className="field-label">Tm max (°C)</span>
          <input
            className="field-input"
            type="number"
            min={45}
            max={75}
            value={tmMax}
            onChange={(e) => setTmMax(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span className="field-label">Product min (bp)</span>
          <input
            className="field-input"
            type="number"
            min={50}
            max={2000}
            step={10}
            value={prodMin}
            onChange={(e) => setProdMin(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span className="field-label">Product max (bp)</span>
          <input
            className="field-input"
            type="number"
            min={50}
            max={2000}
            step={10}
            value={prodMax}
            onChange={(e) => setProdMax(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span className="field-label">Avoid SNPs</span>
          <select
            className="field-select"
            value={avoidSnps ? 'yes' : 'no'}
            onChange={(e) => setAvoidSnps(e.target.value === 'yes')}
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
          disabled={loading}
        >
          {loading ? 'Designing…' : 'Generate & validate'}
        </button>
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
        Demo serves the RPE65 c.260 fixture. Constraints and SNP-avoidance are
        passed to the design engine; real mode runs local Primer3 with an
        in-template specificity screen (whole-genome UCSC isPcr is opt-in,
        M-002C — gated). This is not an NCBI Primer-BLAST validation.
      </div>

      {error && <div className="primer-error">{error}</div>}

      {armsUnsupported && (
        <div className="primer-empty">
          ARMS real-mode design isn’t implemented yet (backend M-002
          follow-up). Sanger and qPCR modes are available now.
        </div>
      )}

      {res && !armsUnsupported && (
        <>
          {mockModeMismatch && (
            <div className="primer-mock-note">
              Offline demo: the bundled fixture is Sanger, so {' '}
              {MODES.find((m) => m.v === mode)?.label} mode is showing the
              Sanger pairs. Connect the backend for true{' '}
              {MODES.find((m) => m.v === mode)?.label} output.
            </div>
          )}
          <div className="primer-feed">
            {res.pairs.map((p) => (
              <div key={p.index} className="primer-feed-item">
                <PrimerResultCard pair={p} />
              </div>
            ))}
            {res.pairs.length === 0 && (
              <div className="primer-empty">
                No primer pairs satisfied the constraints. Widen the Tm or
                product-size window and try again.
              </div>
            )}
          </div>
        </>
      )}

      {!res && !loading && !error && !armsUnsupported && (
        <div className="primer-prompt">
          Set your constraints and run <b>Generate &amp; validate</b> to design
          primer pairs for {gene} {cdna}. Each pair resolves into a one-glance
          verdict, the core thermodynamics, and an audit drawer.
        </div>
      )}
    </div>
  )
}
