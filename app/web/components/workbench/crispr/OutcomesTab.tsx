'use client'

import { useEffect, useRef, useState } from 'react'
import { analyzeTide, getWorkbenchTraceDisclosure } from '@/lib/api'
import { outcomeDisclosure } from '@/lib/workbench/crispr-disclosure'
import { disclosureChipClass, disclosureView } from '@/lib/workbench/source-disclosure'
import type { CrisprTideResult } from '@/lib/workbench/crispr-tide-sample'
import { IndelSpectrum } from './IndelSpectrum'
import type { ProcessingDisclosureV1, WorkbenchDesignContextV1 } from '@/lib/backend'
import { useAuth } from '@/components/auth/AuthProvider'

/**
 * Authenticated observed TIDE analysis. Missing providers fail closed; no
 * trace-derived sample or predicted repair output is substituted.
 */
export function OutcomesTab({
  designContext,
  onResultDigest,
}: {
  designContext: WorkbenchDesignContextV1 | null
  onResultDigest?: (digest: string) => void
}) {
  const { user, loading: authLoading, getAccessToken } = useAuth()
  const [control, setControl] = useState<File | null>(null)
  const [edited, setEdited] = useState<File | null>(null)
  const [cutIndex, setCutIndex] = useState(100)
  const [res, setRes] = useState<CrisprTideResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cancelled, setCancelled] = useState(false)
  const [processing, setProcessing] = useState<ProcessingDisclosureV1 | null>(null)
  const [runContext, setRunContext] = useState<WorkbenchDesignContextV1 | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!user) return
    const controller = new AbortController()
    getAccessToken()
      .then((token) => token
        ? getWorkbenchTraceDisclosure(token, { signal: controller.signal })
        : null)
      .then((disclosure) => {
        if (!controller.signal.aborted) setProcessing(disclosure)
      })
      .catch(() => {
        if (!controller.signal.aborted) setProcessing(null)
      })
    return () => controller.abort()
  }, [getAccessToken, user])
  const outcomeInfo = outcomeDisclosure(res)
  const sourceDisclosure = res
    ? disclosureView(res.source_disclosure, {
        source_status: 'unavailable',
        provider_id: 'tide_provider_unverified',
        provider_label: outcomeInfo.sourceLabel,
        warnings: res.warnings,
      })
    : null

  const clearComputed = () => {
    setRes(null)
    setError(null)
  }

  const run = async () => {
    if (!user) {
      setError('Sign in before uploading traces for server-side outcome analysis.')
      return
    }
    if (!designContext) {
      setError('Resolve an exact source-backed selection before outcome analysis.')
      return
    }
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
    setCancelled(false)
    const token = await getAccessToken()
    if (!token) {
      setError('Your session is unavailable. Sign in again before uploading traces.')
      setLoading(false)
      return
    }
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const response = await analyzeTide(control, edited, cutIndex, {
        signal: controller.signal,
        accessToken: token,
      })
      setRes(response)
      setRunContext(designContext)
      onResultDigest?.(designContext.context_digest)
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        setCancelled(true)
        return
      }
      setError(e instanceof Error ? e.message : 'TIDE analysis failed')
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
        setLoading(false)
      }
    }
  }

  return (
    <div className="crispr-outcomes">
      <div className="tool-form">
        <div className="field">
          <span className="field-label">Control trace (.ab1)</span>
          <label className="align-read-btn align-file-btn">
            {control ? 'Replace file' : 'Choose file'}
            <input
              type="file"
              accept=".ab1,.abi"
              hidden
              disabled={loading}
              onChange={(e) => {
                setControl(e.target.files?.[0] ?? null)
                clearComputed()
              }}
            />
          </label>
        </div>
        <div className="field">
          <span className="field-label">Edited trace (.ab1)</span>
          <label className="align-read-btn align-file-btn">
            {edited ? 'Replace file' : 'Choose file'}
            <input
              type="file"
              accept=".ab1,.abi"
              hidden
              disabled={loading}
              onChange={(e) => {
                setEdited(e.target.files?.[0] ?? null)
                clearComputed()
              }}
            />
          </label>
        </div>
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
          disabled={loading || authLoading || !user || !designContext}
          title="Compare edited vs control traces to estimate indel outcomes"
        >
          {loading ? 'Analyzing...' : 'Analyze outcomes'}
        </button>
        {loading ? (
          <button type="button" className="align-read-btn" onClick={() => abortRef.current?.abort()}>
            Cancel
          </button>
        ) : null}
        <span className="tool-panel-sub">
          {control?.name ?? 'no control'} / {edited?.name ?? 'no edited'} /{' '}
          {outcomeInfo.sourceLabel}
        </span>
      </div>

      <div className="workbench-context-binding" role="note">
        {!user
          ? 'Sign-in required. Trace files are not uploaded until you start analysis.'
          : processing
            ? `${processing.provider_label}: server processing; raw input persisted ${processing.raw_input_persisted ? 'yes' : 'no'}; retention ${processing.retention.replaceAll('_', ' ')}.`
            : 'Checking authenticated trace-processing disclosure…'}
      </div>
      {cancelled ? (
        <div className="workbench-context-binding" role="status">
          Outcome analysis cancelled. Uploaded files remain only in this component and no result was saved.
        </div>
      ) : null}
      {runContext && (!designContext || runContext.context_digest !== designContext.context_digest) ? (
        <div className="workbench-stale" role="status">
          This outcome result is stale for the current selection.
        </div>
      ) : null}

      {!res && (
        <div className="crispr-caveats">
          <div className="help-note">
            Runs require the authenticated TIDE provider and two AB1 traces.
            No sample result is substituted. Lindel or other repair predictions
            remain separate and are shown only when returned with provider proof.
          </div>
        </div>
      )}

      {error && <div className="crispr-error">{error}</div>}

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
          <div className="ic-callouts">
            <div className="ic-stat">
              <span className="label">Editing efficiency</span>
              <span className="value">
                {typeof res.editing_efficiency === 'number'
                  ? `${(res.editing_efficiency * 100).toFixed(0)}%`
                  : 'Not reported'}
              </span>
            </div>
            <div className="ic-stat">
              <span className="label">{outcomeInfo.fitLabel}</span>
              <span className="value">
                {typeof res.r_squared === 'number'
                  ? res.r_squared.toFixed(2)
                  : 'Not reported'}
              </span>
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
          {res.warnings?.length ? (
            <div className="help-note">Remarks: {res.warnings.join(', ')}</div>
          ) : null}
          <div className="help-note">{outcomeInfo.predictionLine}</div>
          <div className="help-note">{res.notes}</div>
        </>
      )}
    </div>
  )
}
