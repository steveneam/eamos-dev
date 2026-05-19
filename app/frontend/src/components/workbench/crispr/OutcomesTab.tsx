import { useState } from 'react'
import { analyzeTide } from '@/lib/api'
import type { CrisprTideResult } from '@/lib/workbench/crispr-tide-sample'
import { IndelSpectrum } from './IndelSpectrum'

/**
 * Blueprint-2 post-CRISPR editing-outcome scaffold. Two Sanger trace
 * inputs (control + edited) and the Cas9 cleavage base index drive a TIDE
 * deconvolution. Mock-first against `CRISPR_TIDE_SAMPLE` — the real
 * `POST /api/v1/crispr/tide` + AB1 parsing are a gated Codex milestone
 * (plans/crispr-integration.md §7). When the real backend returns
 * `predicted_available: false` (no repair-model weights) the chart
 * renders observed-only.
 */
export function OutcomesTab() {
  const [control, setControl] = useState<File | null>(null)
  const [edited, setEdited] = useState<File | null>(null)
  const [cutIndex, setCutIndex] = useState(100)
  const [res, setRes] = useState<CrisprTideResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    if (!control || !edited) {
      setError('Upload both a control and an edited Sanger trace (.ab1 / JSON).')
      return
    }
    setLoading(true)
    setError(null)
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
            onChange={(e) => setControl(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="field">
          <span className="field-label">Edited trace (.ab1 / JSON)</span>
          <input
            className="field-input crispr-file"
            type="file"
            accept=".ab1,.json"
            onChange={(e) => setEdited(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="field">
          <span className="field-label">Cas9 cleavage base index</span>
          <input
            className="field-input"
            type="number"
            min={1}
            value={cutIndex}
            onChange={(e) => setCutIndex(Number(e.target.value))}
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
          {loading ? 'Analysing…' : 'Run TIDE analysis'}
        </button>
        <span className="tool-panel-sub">
          {control?.name ?? 'no control'} · {edited?.name ?? 'no edited'}
        </span>
      </div>

      <div className="help-note">
        Sanger TIDE (Brinkman 2014) deconvolution. AB1 parsing, the NNLS
        solver, and the endpoint are a gated backend milestone (§7); this
        scaffold is mock-first. CRISPResso2 NGS and the SPROUT/inDelphi
        repair predictor are deferred — production runs are observed-only
        until repair-model weights are sourced.
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
              <span className="label">Fit R²</span>
              <span className="value">{res.r_squared.toFixed(2)}</span>
            </div>
            <div className="ic-stat">
              <span className="label">Cut index</span>
              <span className="value">{res.cut_site_index}</span>
            </div>
            <div className="ic-stat">
              <span className="label">Predictor</span>
              <span className="value">
                {res.predicted_available ? 'AI + observed' : 'observed-only'}
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
