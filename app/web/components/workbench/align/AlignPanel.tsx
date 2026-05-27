'use client'

import { useMemo, useRef, useState } from 'react'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import {
  compareSequences,
  makeAlignmentSeed,
  normalizeAlignResponse,
  type AlignApiResponseShape,
  type AlignTraceView,
  type AlignmentCell,
  type AlignmentDifference,
  type PairwiseAlignment,
  type TargetAlignment,
} from '@/lib/workbench/alignment-pairwise'

interface AlignPanelProps {
  data: GeneWindowData
  cdna: string
}

type AlignApiStatus = 'idle' | 'loading' | 'success' | 'error'

// Next.js port: read NEXT_PUBLIC_API_BASE_URL (empty = same-origin rewrites
// from next.config.ts) rather than Vite's import.meta.env.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''
const ALIGN_API_URL = `${API_BASE_URL}/api/v1/align`

export function AlignPanel({ data, cdna }: AlignPanelProps) {
  const seed = useMemo(() => makeAlignmentSeed(data), [data])
  const seedKey = `${seed.reference}|${seed.edited}|${seed.targetReferenceIndex ?? 'none'}`

  return <AlignPanelForm key={seedKey} data={data} cdna={cdna} seed={seed} />
}

function AlignPanelForm({
  data,
  cdna,
  seed,
}: AlignPanelProps & { seed: ReturnType<typeof makeAlignmentSeed> }) {
  const [referenceInput, setReferenceInput] = useState(seed.reference)
  const [editedInput, setEditedInput] = useState(seed.edited)
  const [traceFile, setTraceFile] = useState<File | null>(null)
  const [traceView, setTraceView] = useState<AlignTraceView | null>(null)
  const [traceSource, setTraceSource] = useState<string | null>(null)
  const [apiStatus, setApiStatus] = useState<AlignApiStatus>('idle')
  const [apiError, setApiError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const comparison = useMemo(
    () => compareSequences(referenceInput, editedInput, seed.targetReferenceIndex),
    [editedInput, referenceInput, seed.targetReferenceIndex],
  )
  const alignment = comparison.alignment

  const clearTrace = () => {
    setTraceFile(null)
    setTraceView(null)
    setTraceSource(null)
    setApiStatus('idle')
    setApiError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const runApiAlignment = async () => {
    setApiStatus('loading')
    setApiError(null)

    try {
      const response =
        traceFile && isJsonFile(traceFile)
          ? await readTraceJson(traceFile)
          : await requestApiAlignment({
              gene: data.gene,
              cdna,
              userSequence: comparison.edited.sequence,
              traceFile,
            })
      const trace = normalizeAlignResponse(response)

      setTraceView(trace)
      setTraceSource(traceFile?.name ?? '/api/v1/align')
      setApiStatus('success')
      if (trace.reference) setReferenceInput(trace.reference)
      if (trace.read) setEditedInput(trace.read)
    } catch (error) {
      setApiStatus('error')
      setApiError(errorMessage(error))
    }
  }

  return (
    <div className="align-panel">
      <div className="tool-panel-head">
        <div>
          <h2 className="tool-panel-title">Pairwise sequence alignment</h2>
          <span className="tool-panel-sub">
            {data.gene} {cdna} - reference window vs pasted edit/read
          </span>
        </div>
        <div className="align-actions">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setEditedInput(referenceInput)}
          >
            Match reference
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setEditedInput(seed.edited)}
          >
            Use variant
          </button>
          <button
            type="button"
            className="btn-teal"
            onClick={() => {
              setReferenceInput(seed.reference)
              setEditedInput(seed.edited)
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="align-source-grid">
        <div className="align-source-card">
          <div className="align-source-head">
            <div>
              <span className="field-label">Trace input</span>
              <b>AB1 / API response</b>
            </div>
            <span className={`align-status ${apiStatus}`}>{apiStatusLabel(apiStatus)}</span>
          </div>
          <label className="field align-file-field">
            <span className="field-label">Sanger trace</span>
            <input
              ref={fileInputRef}
              className="field-input align-file"
              type="file"
              accept=".ab1,.abi,.json,application/json"
              disabled={apiStatus === 'loading'}
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null
                setTraceFile(file)
                setTraceView(null)
                setTraceSource(null)
                setApiStatus('idle')
                setApiError(null)
              }}
            />
          </label>
          <div className="align-upload-row">
            <button
              type="button"
              className="btn-teal"
              onClick={runApiAlignment}
              disabled={apiStatus === 'loading'}
            >
              {apiStatus === 'loading' ? 'Aligning...' : 'Run API align'}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={clearTrace}
              disabled={apiStatus === 'loading'}
            >
              Clear trace
            </button>
            <span className="align-file-meta">{traceFile?.name ?? 'No trace file'}</span>
          </div>
        </div>

        <div className="align-source-card">
          <div className="align-source-head">
            <div>
              <span className="field-label">Browser fallback</span>
              <b>Paste / FASTA</b>
            </div>
            <span className={`align-status ${comparison.issues.length ? 'error' : 'success'}`}>
              {comparison.issues.length ? 'Needs input' : 'Ready'}
            </span>
          </div>
          <div className="align-source-stats">
            <Metric label="Reference" value={`${comparison.reference.sequence.length} bp`} />
            <Metric label="Read" value={`${comparison.edited.sequence.length} bp`} />
            <Metric
              label="Target"
              value={
                seed.targetReferenceIndex === null
                  ? 'Outside'
                  : `Ref ${seed.targetReferenceIndex + 1}`
              }
            />
          </div>
        </div>
      </div>

      <div className="align-input-row">
        <label className="field align-field">
          <span className="field-label">Reference sequence</span>
          <textarea
            className="align-textarea"
            value={referenceInput}
            spellCheck={false}
            onChange={(event) => setReferenceInput(event.target.value)}
          />
          <span className="align-input-meta">
            {comparison.reference.sequence.length} bp
          </span>
        </label>

        <label className="field align-field">
          <span className="field-label">Edited/read sequence</span>
          <textarea
            className="align-textarea"
            value={editedInput}
            spellCheck={false}
            onChange={(event) => setEditedInput(event.target.value)}
          />
          <span className="align-input-meta">{comparison.edited.sequence.length} bp</span>
        </label>
      </div>

      {comparison.issues.length > 0 && (
        <div className="align-error" role="alert">
          {comparison.issues.map((issue) => (
            <div key={`${issue.field}-${issue.message}`}>{issue.message}</div>
          ))}
        </div>
      )}

      {alignment ? (
        <div className="align-results">
          <AlignmentSummary alignment={alignment} />
          <TargetCard
            target={alignment.target}
            targetLabel={seed.targetLabel}
            targetReferenceIndex={seed.targetReferenceIndex}
          />
          <AlignmentBlock alignment={alignment} targetLabel={seed.targetLabel} />
          <DifferenceList differences={alignment.differences} />
        </div>
      ) : (
        <div className="align-empty">
          Paste A/C/G/T/N sequence in both fields to compare this window.
        </div>
      )}

      <TracePanel
        trace={traceView}
        status={apiStatus}
        error={apiError}
        sourceLabel={traceSource}
        targetLabel={seed.targetLabel}
      />
    </div>
  )
}

function AlignmentSummary({ alignment }: { alignment: PairwiseAlignment }) {
  return (
    <div className="align-summary" aria-label="Alignment summary">
      <Metric label="Mode" value={alignment.method === 'local' ? 'Local' : 'Positional'} />
      <Metric label="Identity" value={formatPercent(alignment.identity)} tone="ok" />
      <Metric label="Matches" value={String(alignment.matches)} />
      <Metric label="Mismatches" value={String(alignment.mismatches)} tone={alignment.mismatches > 0 ? 'err' : 'ok'} />
      <Metric label="Gaps" value={String(alignment.gaps)} tone={alignment.gaps > 0 ? 'warn' : undefined} />
      <Metric
        label="Ref span"
        value={formatRange(alignment.referenceStart, alignment.referenceEnd)}
      />
      <Metric label="Read span" value={formatRange(alignment.editedStart, alignment.editedEnd)} />
    </div>
  )
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: 'ok' | 'warn' | 'err'
}) {
  return (
    <div className="align-metric">
      <span>{label}</span>
      <b className={tone}>{value}</b>
    </div>
  )
}

function TargetCard({
  target,
  targetLabel,
  targetReferenceIndex,
}: {
  target: TargetAlignment
  targetLabel: string
  targetReferenceIndex: number | null
}) {
  return (
    <div className={`align-target-card ${target.state}`}>
      <div>
        <span className="field-label">Target</span>
        <b>{targetLabel}</b>
      </div>
      <div className="align-target-copy">
        {targetReferenceIndex === null
          ? 'Target is outside the loaded reference window.'
          : targetText(target)}
      </div>
    </div>
  )
}

function AlignmentBlock({
  alignment,
  targetLabel,
}: {
  alignment: PairwiseAlignment
  targetLabel: string
}) {
  return (
    <div className="align-block" aria-label="Pairwise alignment rows">
      <AlignmentRow
        label="Ref"
        cells={alignment.cells}
        targetLabel={targetLabel}
        renderCell={(cell) => cell.referenceBase}
      />
      <AlignmentRow
        label="Match"
        cells={alignment.cells}
        targetLabel={targetLabel}
        renderCell={(cell) => cell.mark}
        mark
      />
      <AlignmentRow
        label="Edited"
        cells={alignment.cells}
        targetLabel={targetLabel}
        renderCell={(cell) => cell.editedBase}
      />
    </div>
  )
}

function AlignmentRow({
  label,
  cells,
  targetLabel,
  renderCell,
  mark = false,
}: {
  label: string
  cells: AlignmentCell[]
  targetLabel: string
  renderCell: (cell: AlignmentCell) => string
  mark?: boolean
}) {
  return (
    <div className="align-row">
      <span className="align-row-label">{label}</span>
      <span className="align-row-seq">
        {cells.map((cell, index) => (
          <span
            key={`${label}-${index}`}
            className={baseClass(cell, mark)}
            title={cellTitle(cell, targetLabel)}
          >
            {renderCell(cell)}
          </span>
        ))}
      </span>
    </div>
  )
}

function DifferenceList({ differences }: { differences: AlignmentDifference[] }) {
  if (differences.length === 0) {
    return <div className="align-diff-note ok">No mismatches or gaps in the aligned span.</div>
  }

  const visible = differences.slice(0, 24)
  const hidden = differences.length - visible.length

  return (
    <div className="align-diff-list" aria-label="Alignment differences">
      {visible.map((difference, index) => (
        <span
          key={`${difference.referenceIndex ?? 'ins'}-${difference.editedIndex ?? 'del'}-${index}`}
          className={`align-diff-chip ${difference.kind}`}
        >
          {differenceLabel(difference)}
        </span>
      ))}
      {hidden > 0 && <span className="align-diff-more">+{hidden} more</span>}
    </div>
  )
}

function TracePanel({
  trace,
  status,
  error,
  sourceLabel,
  targetLabel,
}: {
  trace: AlignTraceView | null
  status: AlignApiStatus
  error: string | null
  sourceLabel: string | null
  targetLabel: string
}) {
  const idle = !trace && status !== 'loading' && status !== 'error'

  return (
    <div className="align-trace-section" aria-label="AB1 trace result">
      <div className="align-section-head">
        <div>
          <span className="field-label">Trace channels</span>
          <b>{sourceLabel ?? 'No trace loaded'}</b>
        </div>
        {trace && <span className="align-target-pill">{traceTargetText(trace, targetLabel)}</span>}
      </div>

      {status === 'loading' && (
        <div className="align-trace-empty">Waiting for /api/v1/align...</div>
      )}

      {status === 'error' && (
        <div className="align-error" role="alert">
          <div>{error ?? 'Alignment request failed.'}</div>
          <div>Browser alignment remains available from the pasted sequences.</div>
        </div>
      )}

      {trace && (
        <>
          {trace.hasTrace ? (
            <ChromatogramTrace trace={trace} targetLabel={targetLabel} />
          ) : (
            <div className="align-trace-empty">
              Alignment response did not include trace channel values.
            </div>
          )}
          {!trace.hasTrace && <BaseCallQualityStrip trace={trace} targetLabel={targetLabel} />}
          {trace.warnings.length > 0 && (
            <div className="align-warning-list" aria-label="Alignment response warnings">
              {trace.warnings.map((warning) => (
                <span key={warning}>{warning}</span>
              ))}
            </div>
          )}
        </>
      )}

      {idle && (
        <div className="align-trace-empty">
          No trace response loaded. The browser alignment above is using pasted sequence input.
        </div>
      )}
    </div>
  )
}

function ChromatogramTrace({
  trace,
  targetLabel,
}: {
  trace: AlignTraceView
  targetLabel: string
}) {
  const valueCount = trace.traceChannels.reduce(
    (max, channel) => Math.max(max, channel.values.length),
    0,
  )
  const baseStep = 26
  const width = Math.max(360, trace.baseCalls.length * baseStep, valueCount * 6)
  const height = 112
  const targetX =
    trace.targetPosition !== null && trace.targetPosition < trace.baseCalls.length
      ? trace.targetPosition * baseStep
      : null

  return (
    <div className="chromatogram">
      <svg
        className="align-trace-svg"
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        role="img"
        aria-label={`${targetLabel} trace channels`}
      >
        <title>{targetLabel} trace channels</title>
        {targetX !== null && (
          <rect
            className="align-trace-target-band"
            x={targetX}
            y={0}
            width={baseStep}
            height={height}
          />
        )}
        <line className="align-trace-baseline" x1={0} y1={height - 10} x2={width} y2={height - 10} />
        {trace.traceChannels.map((channel) => (
          <polyline
            key={channel.base}
            className={`align-trace-channel ${channel.base}`}
            points={tracePoints(channel.values, width, height)}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
      <BaseCallQualityStrip trace={trace} targetLabel={targetLabel} />
    </div>
  )
}

function BaseCallQualityStrip({
  trace,
  targetLabel,
}: {
  trace: AlignTraceView
  targetLabel: string
}) {
  if (trace.baseCalls.length === 0) return null

  return (
    <div className="align-basecall-strip">
      <div className="chromatogram-bases" aria-label="Base calls">
        {trace.baseCalls.map((call) => (
          <span
            key={`base-${call.index}`}
            className={baseCallClass(call)}
            title={baseCallTitle(call, targetLabel)}
          >
            {call.base}
          </span>
        ))}
      </div>
      <div className="chromatogram-qc" aria-label="Q scores">
        {trace.baseCalls.map((call) => (
          <span
            key={`q-${call.index}`}
            className={qualityClass(call.qScore)}
            title={baseCallTitle(call, targetLabel)}
          >
            {call.qScore ?? '-'}
          </span>
        ))}
      </div>
    </div>
  )
}

function baseClass(cell: AlignmentCell, mark: boolean): string {
  const classes = ['align-base', cell.kind]
  if (cell.isTarget) classes.push('target')
  if (mark) classes.push('align-mark')
  return classes.join(' ')
}

function cellTitle(cell: AlignmentCell, targetLabel: string): string {
  const ref = cell.referenceIndex === null ? 'insertion' : `ref ${cell.referenceIndex + 1}`
  const edited = cell.editedIndex === null ? 'gap' : `read ${cell.editedIndex + 1}`
  const target = cell.isTarget ? `, ${targetLabel}` : ''
  return `${ref}, ${edited}: ${cell.referenceBase}/${cell.editedBase}${target}`
}

function differenceLabel(difference: AlignmentDifference): string {
  if (difference.referenceIndex === null) {
    return `ins ${difference.editedBase} @ read ${Number(difference.editedIndex) + 1}`
  }
  if (difference.editedIndex === null) {
    return `ref ${difference.referenceIndex + 1}: ${difference.referenceBase}->gap`
  }
  return `ref ${difference.referenceIndex + 1}: ${difference.referenceBase}->${difference.editedBase}`
}

function baseCallClass(call: AlignTraceView['baseCalls'][number]): string {
  const classes = ['chromatogram-base', call.base]
  if (call.isTarget) classes.push('target')
  if (call.isMismatch) classes.push('mismatch')
  return classes.join(' ')
}

function qualityClass(qScore: number | null): string {
  if (qScore === null) return ''
  if (qScore < 20) return 'low'
  if (qScore < 30) return 'warn'
  return ''
}

function baseCallTitle(call: AlignTraceView['baseCalls'][number], targetLabel: string): string {
  const ref = call.referenceBase ?? '-'
  const q = call.qScore === null ? 'Q-score unavailable' : `Q${call.qScore}`
  const target = call.isTarget ? `, ${targetLabel}` : ''
  return `read ${call.index + 1}: ${call.base}, ref ${ref}, ${q}${target}`
}

function traceTargetText(trace: AlignTraceView, targetLabel: string): string {
  if (trace.targetPosition === null) return `${targetLabel}: target unavailable`

  const call = trace.baseCalls[trace.targetPosition]
  const referenceBase = call?.referenceBase ?? trace.reference[trace.targetPosition] ?? '-'
  const readBase = call?.base ?? trace.read[trace.targetPosition] ?? '-'
  const qScore = call?.qScore ?? null
  const quality = qScore === null ? 'Q-' : `Q${qScore}`

  return `${targetLabel} ref ${trace.targetPosition + 1}: ${referenceBase}->${readBase} ${quality}`
}

function tracePoints(values: number[], width: number, height: number): string {
  if (values.length === 0) return ''

  const maxValue = values.reduce((max, value) => Math.max(max, value), 1)
  const baseline = height - 10
  const amplitude = height - 20

  return values
    .map((value, index) => {
      const x = values.length === 1 ? 0 : (index / (values.length - 1)) * width
      const y = baseline - (Math.max(0, value) / maxValue) * amplitude
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

function targetText(target: TargetAlignment): string {
  if (target.state === 'outside') return 'Target is outside the aligned read segment.'
  if (target.state === 'match') return `Target matches reference (${target.referenceBase}).`
  if (target.state === 'gap') return `Target has a read gap at reference base ${target.referenceBase}.`
  return `Target differs: ${target.referenceBase}->${target.editedBase}.`
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function formatRange(start: number, end: number): string {
  if (end <= start) return '-'
  return `${start + 1}-${end}`
}

function apiStatusLabel(status: AlignApiStatus): string {
  if (status === 'loading') return 'Running'
  if (status === 'success') return 'Loaded'
  if (status === 'error') return 'Failed'
  return 'Idle'
}

function isJsonFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.json') || file.type === 'application/json'
}

async function readTraceJson(file: File): Promise<AlignApiResponseShape> {
  const parsed = JSON.parse(await file.text()) as unknown
  if (!parsed || typeof parsed !== 'object') {
    throw new Error('Trace JSON must contain an alignment response object.')
  }
  return parsed as AlignApiResponseShape
}

async function requestApiAlignment({
  gene,
  cdna,
  userSequence,
  traceFile,
}: {
  gene: string
  cdna: string
  userSequence: string
  traceFile: File | null
}): Promise<AlignApiResponseShape> {
  const payload = {
    gene,
    cdna,
    user_sequence: userSequence || null,
    ab1_blob_base64: traceFile ? await fileToBase64(traceFile) : null,
  }
  const response = await fetch(ALIGN_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Alignment request failed with status ${response.status}.`)
  }

  return (await response.json()) as AlignApiResponseShape
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Could not read trace file.'))
    reader.onload = () => {
      const result = reader.result
      if (typeof result !== 'string') {
        reject(new Error('Could not read trace file.'))
        return
      }
      const commaIndex = result.indexOf(',')
      resolve(commaIndex >= 0 ? result.slice(commaIndex + 1) : result)
    }
    reader.readAsDataURL(file)
  })
}

function errorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : 'Alignment request failed.'
  return message.length > 280 ? `${message.slice(0, 277)}...` : message
}
