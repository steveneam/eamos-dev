import { useState } from 'react'
import { analyzeTide } from '@/lib/api'
import { outcomeDisclosure } from '@/lib/workbench/crispr-disclosure'
import type { CrisprTideResult } from '@/lib/workbench/crispr-tide-sample'
import { IndelSpectrum } from './IndelSpectrum'

/**
 * Post-CRISPR editing-outcome scaffold. Until backend metadata says otherwise,
 * this is an observed-only sample/fallback surface, not a repair predictor.
 */
export function OutcomesTab() {
  const [control, setControl] = useState<File | null>(null)
  const [edited, setEdited] = useState<File | null>(null)
  const [cutIndex, setCutIndex] = useState(100)
  const [res, setRes] = useState<CrisprTideResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const outcomeInfo = outcomeDisclosure(res)

  const clearComputed = () => {
    setRes(null)
    setError(null)
  }

  const run = async () => {
    if (!control || !edited) {
      setError('Upload both a control and an edited Sanger trace (.ab1 / JSON).')
      setRes(null)
      return
    }
    if (!Number.isFinite(cutIndex) || cutIndex < 1) {
      setError('Cut index must be a positive base index.')
      setRes(null)
      return
    }

    setLoading(true)
    setError(null)
    setRes(null)
    try {
      setRes(await analyzeTide(control, edited, cutIndex))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'TIDE analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="crispr-outcomes">
      <div className="tool-form">
        <label className="field">
          <span className="field-label">Control trace (.ab1 / JSON)</span>
          <input
            className="field-input crispr-file"
            type="file"
            accept=".ab1,.json"
            disabled={loading}
            onChange={(e) => {
              setControl(e.target.files?.[0] ?? null)
              clearComputed()
            }}
          />
        </label>
        <label className="field">
          <span className="field-label">Edited trace (.ab1 / JSON)</span>
          <input
            className="field-input crispr-file"
            type="file"
            accept=".ab1,.json"
            disabled={loading}
            onChange={(e) => {
              setEdited(e.target.files?.[0] ?? null)
              clearComputed()
            }}
          />
        </label>
        <label className="field">
          <span className="field-label">Cas9 cleavage base index</span>
          <input
            className="field-input"
            type="number"
            min={1}
            value={cutIndex}
            disabled={loading}
            onChange={(e) => {
              const parsed = Number(e.target.value)
              setCutIndex(Number.isFinite(parsed) ? Math.max(1, parsed) : 1)
              clearComputed()
            }}
          />
        </label>
      </div>

      <div className="btn-row">
        <button
          type="button"
          className="btn-teal"
          onClick={run}
          disabled={loading}
        >
          {loading ? 'Analyzing...' : 'Analyze outcomes'}
        </button>
        <span className="tool-panel-sub">
          {control?.name ?? 'no control'} / {edited?.name ?? 'no edited'} /{' '}
          {outcomeInfo.sourceLabel}
        </span>
      </div>

      <div className="crispr-caveats">
        <div className="help-note">
          Outcomes stay observed-only unless the backend returns source-backed
          TIDE or Lindel details with numeric predicted bins.
        </div>
        <div className="help-note">
          Without that contract, this tab uses the frontend sample/fallback;
          uploaded traces are not evidence of a completed TIDE solve.
        </div>
        <div className="help-note">
          Lindel-derived frameshift probability should be shown as a separate
          backend score, not blended into observed indel frequencies.
        </div>
      </div>

      {error && <div className="crispr-error">{error}</div>}

      {res && (
        <>
          <div className="ic-callouts">
            <div className="ic-stat">
              <span className="label">Editing efficiency</span>
              <span className="value">
                {(res.editing_efficiency * 100).toFixed(0)}%
              </span>
            </div>
            <div className="ic-stat">
              <span className="label">{outcomeInfo.fitLabel}</span>
              <span className="value">{res.r_squared.toFixed(2)}</span>
            </div>
            <div className="ic-stat">
              <span className="label">Cut index</span>
              <span className="value">{res.cut_site_index}</span>
            </div>
            <div className="ic-stat">
              <span className="label">Series</span>
              <span className="value">{outcomeInfo.seriesLabel}</span>
            </div>
          </div>
          <IndelSpectrum
            spectrum={res.spectrum}
            showPredicted={outcomeInfo.showPredicted}
            observedLabel={outcomeInfo.observedLegendLabel}
          />
          <div className="help-note">{outcomeInfo.predictionLine}</div>
          <div className="help-note">{res.notes}</div>
        </>
      )}
    </div>
  )
}
