'use client'

import { useState } from 'react'
import type {
  AlignmentComparison,
  AlignmentDifference,
  PairwiseAlignment,
} from '@/lib/workbench/alignment-pairwise'
import { AlignedTrace } from './AlignedTrace'
import type { ReadTrace } from './read-model'

interface PairwiseViewProps {
  comparison: AlignmentComparison
  readLabel: string
  searchHits: Set<number>
  activeSearchStart: number | null
  /** Active difference index — shared across metric strip, chips, and the trace. */
  activeDiff: number
  onActiveDiff: (index: number) => void
  trace: ReadTrace | null
  trimStart: number
  realMismatch: Set<number>
  lowQMismatch: Set<number>
  hetIndices: Set<number>
  showTrace: boolean
  /** Reference length, for the coverage metric. */
  referenceLength: number
}

/** Metric strip + ◀▶ nav + a single shared-coordinate ref/read/trace track + chips. */
export function PairwiseView({
  comparison,
  readLabel,
  searchHits,
  activeSearchStart,
  activeDiff,
  onActiveDiff,
  trace,
  trimStart,
  realMismatch,
  lowQMismatch,
  hetIndices,
  showTrace,
  referenceLength,
}: PairwiseViewProps) {
  const alignment = comparison.alignment
  const [showMismatch, setShowMismatch] = useState(true)
  const [showGap, setShowGap] = useState(true)

  if (comparison.issues.length > 0) {
    return (
      <div className="align-error" role="alert">
        {comparison.issues.map((issue) => (
          <div key={`${issue.field}-${issue.message}`}>{issue.message}</div>
        ))}
      </div>
    )
  }
  if (!alignment) {
    return <div className="align-empty">No valid A/C/G/T/N sequence to align.</div>
  }

  const diffColumns = alignment.cells.flatMap((cell, index) => (cell.kind === 'match' ? [] : [index]))
  const diffCount = alignment.differences.length
  const safeActive = diffCount > 0 ? Math.min(activeDiff, diffCount - 1) : 0
  const activeCol = diffCount > 0 ? diffColumns[safeActive] : null

  const step = (delta: number) => {
    if (diffCount === 0) return
    onActiveDiff((safeActive + delta + diffCount) % diffCount)
  }

  return (
    <div className="align-results">
      <Summary
        alignment={alignment}
        referenceLength={referenceLength}
        showMismatch={showMismatch}
        showGap={showGap}
        onToggleMismatch={() => setShowMismatch((value) => !value)}
        onToggleGap={() => setShowGap((value) => !value)}
      />
      {diffCount > 0 && (
        <div className="align-diff-nav" aria-label="Step through differences">
          <button type="button" className="align-nav-btn" onClick={() => step(-1)} aria-label="Previous difference">
            ◀
          </button>
          <span className="align-diff-count">
            {safeActive + 1} / {diffCount}
          </span>
          <button type="button" className="align-nav-btn" onClick={() => step(1)} aria-label="Next difference">
            ▶
          </button>
          <span className="align-diff-current">{differenceLabel(alignment.differences[safeActive])}</span>
        </div>
      )}
      <AlignedTrace
        cells={alignment.cells}
        trace={trace}
        trimStart={trimStart}
        realMismatch={realMismatch}
        lowQMismatch={lowQMismatch}
        hetIndices={hetIndices}
        searchHits={searchHits}
        activeSearchStart={activeSearchStart}
        activeCol={activeCol}
        showTrace={showTrace}
        readLabel={readLabel}
      />
      <DifferenceList
        differences={alignment.differences}
        activeDiff={safeActive}
        onSelect={onActiveDiff}
        showMismatch={showMismatch}
        showGap={showGap}
      />
    </div>
  )
}

function Summary({
  alignment,
  referenceLength,
  showMismatch,
  showGap,
  onToggleMismatch,
  onToggleGap,
}: {
  alignment: PairwiseAlignment
  referenceLength: number
  showMismatch: boolean
  showGap: boolean
  onToggleMismatch: () => void
  onToggleGap: () => void
}) {
  const coverage =
    referenceLength > 0
      ? Math.round(((alignment.referenceEnd - alignment.referenceStart) / referenceLength) * 100)
      : 0
  return (
    <div className="align-summary" aria-label="Alignment summary">
      <Metric label="Identity" value={formatPercent(alignment.identity)} tone="ok" />
      <Metric label="Coverage" value={`${coverage}%`} />
      <Metric label="Matches" value={String(alignment.matches)} />
      <Metric
        label="Mismatches"
        value={String(alignment.mismatches)}
        tone={alignment.mismatches > 0 ? 'err' : 'ok'}
        onClick={alignment.mismatches > 0 ? onToggleMismatch : undefined}
        open={alignment.mismatches > 0 ? showMismatch : undefined}
      />
      <Metric
        label="Gaps"
        value={String(alignment.gaps)}
        tone={alignment.gaps > 0 ? 'warn' : undefined}
        onClick={alignment.gaps > 0 ? onToggleGap : undefined}
        open={alignment.gaps > 0 ? showGap : undefined}
      />
      <Metric label="Ref span" value={formatRange(alignment.referenceStart, alignment.referenceEnd)} />
      <Metric label="Read span" value={formatRange(alignment.editedStart, alignment.editedEnd)} />
    </div>
  )
}

function Metric({
  label,
  value,
  tone,
  onClick,
  open,
}: {
  label: string
  value: string
  tone?: 'ok' | 'warn' | 'err'
  onClick?: () => void
  open?: boolean
}) {
  const className = `align-metric${onClick ? ' toggle' : ''}${open ? ' open' : ''}`
  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick} title="Show / hide these differences">
        <span>
          {label}
          {open !== undefined && <i className="align-metric-caret">{open ? '▾' : '▸'}</i>}
        </span>
        <b className={tone}>{value}</b>
      </button>
    )
  }
  return (
    <div className={className}>
      <span>{label}</span>
      <b className={tone}>{value}</b>
    </div>
  )
}

function DifferenceList({
  differences,
  activeDiff,
  onSelect,
  showMismatch,
  showGap,
}: {
  differences: AlignmentDifference[]
  activeDiff: number
  onSelect: (index: number) => void
  showMismatch: boolean
  showGap: boolean
}) {
  if (differences.length === 0) {
    return <div className="align-diff-note ok">No mismatches or gaps in the aligned span.</div>
  }

  const visible = differences
    .map((difference, index) => ({ difference, index }))
    .filter(({ difference }) => (difference.kind === 'gap' ? showGap : showMismatch))
  if (visible.length === 0) return null

  return (
    <div className="align-diff-list" aria-label="Alignment differences">
      {visible.map(({ difference, index }) => (
        <button
          key={`${difference.referenceIndex ?? 'ins'}-${difference.editedIndex ?? 'del'}-${index}`}
          type="button"
          className={`align-diff-chip ${difference.kind}${index === activeDiff ? ' active' : ''}`}
          onClick={() => onSelect(index)}
        >
          {differenceLabel(difference)}
        </button>
      ))}
    </div>
  )
}

function differenceLabel(difference: AlignmentDifference): string {
  if (difference.referenceIndex === null) {
    return `ins ${difference.editedBase} @ read ${Number(difference.editedIndex) + 1}`
  }
  if (difference.editedIndex === null) {
    return `ref ${difference.referenceIndex + 1}: ${difference.referenceBase}→gap`
  }
  return `ref ${difference.referenceIndex + 1}: ${difference.referenceBase}→${difference.editedBase}`
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function formatRange(start: number, end: number): string {
  if (end <= start) return '-'
  return `${start + 1}-${end}`
}
