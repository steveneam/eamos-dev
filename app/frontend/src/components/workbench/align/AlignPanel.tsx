import { useMemo, useState } from 'react'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import {
  compareSequences,
  makeAlignmentSeed,
  type AlignmentCell,
  type AlignmentDifference,
  type PairwiseAlignment,
  type TargetAlignment,
} from '@/lib/workbench/alignment-pairwise'

interface AlignPanelProps {
  data: GeneWindowData
  cdna: string
}

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

  const comparison = useMemo(
    () => compareSequences(referenceInput, editedInput, seed.targetReferenceIndex),
    [editedInput, referenceInput, seed.targetReferenceIndex],
  )
  const alignment = comparison.alignment

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
