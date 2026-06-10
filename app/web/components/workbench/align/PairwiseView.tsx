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
      <Lede
        alignment={alignment}
        activeDiff={safeActive}
        diffCount={diffCount}
        hetCount={hetIndices.size}
        onStep={step}
      />
      <Summary
        alignment={alignment}
        referenceLength={referenceLength}
        showMismatch={showMismatch}
        showGap={showGap}
        onToggleMismatch={() => setShowMismatch((value) => !value)}
        onToggleGap={() => setShowGap((value) => !value)}
      />
      <div className="align-spans-caption">
        Ref {formatRange(alignment.referenceStart, alignment.referenceEnd)} · Read{' '}
        {formatRange(alignment.editedStart, alignment.editedEnd)}
      </div>
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

/**
 * Tier 1 of the result card — the headline read. Identity is the loudest thing,
 * with the active difference (or an exact-match note) as the supporting clause
 * and the ◀▶ nav lifted up beside it so stepping is where the eye already is.
 */
function Lede({
  alignment,
  activeDiff,
  diffCount,
  hetCount,
  onStep,
}: {
  alignment: PairwiseAlignment
  activeDiff: number
  diffCount: number
  hetCount: number
  onStep: (delta: number) => void
}) {
  const exact = diffCount === 0
  return (
    <div className="align-lede">
      <div className="align-lede-id">
        <b>{formatPercent(alignment.identity)}</b>
        <span>identity</span>
      </div>
      <div className="align-lede-detail">
        {exact ? (
          <span className="align-lede-exact">Exact match — no mismatches or gaps</span>
        ) : (
          <span className="align-lede-diff">{differenceLabel(alignment.differences[activeDiff])}</span>
        )}
        {hetCount > 0 && <span className="align-lede-het">· {hetCount} het</span>}
      </div>
      {diffCount > 0 && (
        <div className="align-diff-nav" aria-label="Step through differences">
          <button type="button" className="align-nav-btn" onClick={() => onStep(-1)} aria-label="Previous difference">
            ◀
          </button>
          <span className="align-diff-count">
            {activeDiff + 1} / {diffCount}
          </span>
          <button type="button" className="align-nav-btn" onClick={() => onStep(1)} aria-label="Next difference">
            ▶
          </button>
        </div>
      )}
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
      <Metric
        label="Coverage"
        value={`${coverage}%`}
        tip="Percent of the reference window this read's alignment spans (how much of the reference the read covers)."
      />
      <Metric
        label="Matches"
        value={String(alignment.matches)}
        tip="Number of aligned positions where the read matches the reference."
      />
      <Metric
        label="Mismatches"
        value={String(alignment.mismatches)}
        tone={alignment.mismatches > 0 ? 'err' : 'ok'}
        onClick={alignment.mismatches > 0 ? onToggleMismatch : undefined}
        open={alignment.mismatches > 0 ? showMismatch : undefined}
        tip="Aligned positions where the read base differs from the reference (substitutions). Click to show or hide them below."
      />
      <Metric
        label="Gaps"
        value={String(alignment.gaps)}
        tone={alignment.gaps > 0 ? 'warn' : undefined}
        onClick={alignment.gaps > 0 ? onToggleGap : undefined}
        open={alignment.gaps > 0 ? showGap : undefined}
        tip="Insertions or deletions — positions present in one sequence but not the other. Click to show or hide them below."
      />
    </div>
  )
}

function Metric({
  label,
  value,
  tone,
  onClick,
  open,
  tip,
}: {
  label: string
  value: string
  tone?: 'ok' | 'warn' | 'err'
  onClick?: () => void
  open?: boolean
  tip?: string
}) {
  const className = `align-metric${onClick ? ' toggle' : ''}${open ? ' open' : ''}`
  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick} title={tip}>
        <span>
          {label}
          {open !== undefined && <i className="align-metric-caret">{open ? '▾' : '▸'}</i>}
        </span>
        <b className={tone}>{value}</b>
      </button>
    )
  }
  return (
    <div className={className} title={tip}>
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
