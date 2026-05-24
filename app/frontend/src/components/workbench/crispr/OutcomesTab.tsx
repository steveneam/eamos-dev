import { useState } from 'react'
import { analyzeTide } from '@/lib/api'
import type { CrisprTideResult } from '@/lib/workbench/crispr-tide-sample'
import { IndelSpectrum } from './IndelSpectrum'

/**
 * Post-CRISPR editing-outcome scaffold. Two Sanger trace inputs and a Cas9
 * cleavage base index drive the TIDE-shaped result. This tab remains
 * mock-first until the backend endpoint and AB1 parsing land.
 */
export function OutcomesTab() {
  const [control, setControl] = useState<File | null>(null)
  const [edited, setEdited] = useState<File | null>(null)
  const [cutIndex, setCutIndex] = useState(100)
  const [res, setRes] = useState<CrisprTideResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
          {loading ? 'Analyzing...' : 'Run TIDE analysis'}
        </button>
        <span className="tool-panel-sub">
          {control?.name ?? 'no control'} / {edited?.name ?? 'no edited'}
        </span>
      </div>

      <div className="crispr-caveats">
        <div className="help-note">
          Current output is an observed-only TIDE scaffold backed by the
          frontend sample when the gated endpoint is absent. AB1 parsing and
          the numerical solver are backend planning items.
        </div>
        <div className="help-note">
          crisprScore is not a TIDE provider. A later Cas9 integration can add
          its Lindel-derived frameshift probability as a separate score.
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
              <span className="label">Fit R2</span>
              <span className="value">{res.r_squared.toFixed(2)}</span>
            </div>
            <div className="ic-stat">
              <span className="label">Cut index</span>
              <span className="value">{res.cut_site_index}</span>
            </div>
            <div className="ic-stat">
              <span className="label">Series</span>
              <span className="value">
                {res.predicted_available ? 'observed + predicted' : 'observed-only'}
              </span>
            </div>
          </div>
          <IndelSpectrum
            spectrum={res.spectrum}
            showPredicted={res.predicted_available}
          />
          <div className="help-note">{res.notes}</div>
        </>
      )}
    </div>
  )
}
