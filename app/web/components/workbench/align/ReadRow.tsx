'use client'

import { useMemo, useState } from 'react'
import { PairwiseView } from './PairwiseView'
import {
  analyzeRead,
  type ReadEntry,
  type ReadOrientation,
  type ReferenceState,
} from './read-model'

interface ReadRowProps {
  read: ReadEntry
  reference: ReferenceState
  searchHits: Set<number>
  activeSearchStart: number | null
  onSetOrientation: (orientation: ReadOrientation) => void
  onRemove: () => void
}

// Leading glyph telegraphs the direction/transform so the collapsed select
// itself shows which orientation is active (Steven's "icon next to it" ask).
const ORIENTATIONS: Array<{ value: ReadOrientation; label: string }> = [
  { value: 'forward', label: '→ Forward 5′→3′' },
  { value: 'reverse', label: '← Reverse 3′→5′' },
  { value: 'complement', label: '↕ Complement' },
  { value: 'reverse-complement', label: '⇄ Reverse complement' },
]

export function ReadRow({
  read,
  reference,
  searchHits,
  activeSearchStart,
  onSetOrientation,
  onRemove,
}: ReadRowProps) {
  const [showTrace, setShowTrace] = useState(true)
  const [useFullRead, setUseFullRead] = useState(false)
  const [activeDiff, setActiveDiff] = useState(0)

  const analysis = useMemo(
    () => analyzeRead(reference, read, useFullRead),
    [reference, read, useFullRead],
  )
  const { comparison, trace, trimStart, trimEnd, hetIndices, realMismatch, lowQMismatch } = analysis
  const alignment = comparison.alignment
  const trimmed = trace ? trimStart > 0 || trimEnd < trace.baseCalls.length : false

  // Reset the active difference when this read's alignment changes.
  const [seenComparison, setSeenComparison] = useState(comparison)
  if (comparison !== seenComparison) {
    setSeenComparison(comparison)
    setActiveDiff(0)
  }

  return (
    <div className="align-read-card">
      <div className="align-read-head">
        <div className="align-read-id">
          <b title={read.label}>{read.label}</b>
          <span className="align-read-meta">
            {alignment ? `${(alignment.identity * 100).toFixed(1)}% identity` : 'No alignment'}
            {' · '}
            <span className="tag-real">{realMismatch.size} real</span>
            {lowQMismatch.size > 0 && <span className="tag-lowq"> · {lowQMismatch.size} low-Q</span>}
            {hetIndices.size > 0 && <span className="tag-het"> · {hetIndices.size} het</span>}
            {trace && trimmed && ` · core ${trimStart + 1}–${trimEnd}`}
            {' · '}
            {read.source === 'ab1' ? 'Sanger' : 'Pasted'}
          </span>
        </div>
        <div className="align-read-actions">
          <select
            className="align-read-select"
            value={read.orientation}
            onChange={(event) => onSetOrientation(event.target.value as ReadOrientation)}
            title="Read orientation (forward / reverse / complement / reverse-complement)"
            aria-label="Read orientation"
          >
            {ORIENTATIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {trace && (
            <button
              type="button"
              className={`align-read-btn${useFullRead ? ' active' : ''}`}
              onClick={() => setUseFullRead((value) => !value)}
              title="Trim noisy low-quality ends, or align the full read"
            >
              {useFullRead ? 'Full read' : 'Q-trim'}
            </button>
          )}
          {trace && (
            <button
              type="button"
              className={`align-read-btn${showTrace ? ' active' : ''}`}
              onClick={() => setShowTrace((value) => !value)}
            >
              {showTrace ? 'Trace shown' : 'Trace hidden'}
            </button>
          )}
          <button
            type="button"
            className="align-read-btn remove"
            onClick={onRemove}
            aria-label="Remove read"
            title="Remove read"
          >
            ✕
          </button>
        </div>
      </div>

      <PairwiseView
        comparison={comparison}
        readLabel={read.label}
        searchHits={searchHits}
        activeSearchStart={activeSearchStart}
        activeDiff={activeDiff}
        onActiveDiff={setActiveDiff}
        trace={trace}
        trimStart={trimStart}
        realMismatch={realMismatch}
        lowQMismatch={lowQMismatch}
        hetIndices={hetIndices}
        showTrace={showTrace}
        referenceLength={reference.sequence.length}
      />
    </div>
  )
}
