'use client'

/* FullLocusViewer — FGV-003 proof slice.

   Renders ViewerFullLocus rows in plain DOM. No selection, edit, scratchpad,
   minimap, or color schemes this slice — those land in FGV-004+ once we
   know what the row model actually feels like on RPE65/ABCA4. */

import { memo, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type {
  FullLocusRow,
  FullLocusRows,
} from '@/lib/workbench/full-locus-layout'
import type { FullLocusViewModel } from '@/lib/workbench/full-locus-adapter'

interface FullLocusViewerProps {
  model: Extract<FullLocusViewModel, { kind: 'ready' }>
}

type CoordinateMode = 'sequence' | 'genomic'
type BaseKind = 'exon' | 'intron' | 'utr5' | 'utr3' | 'cds' | 'unknown'

function bandKindAtCol(row: FullLocusRow, col: number): BaseKind {
  let cdsHit = false
  for (const band of row.bands) {
    if (col < band.colStart || col >= band.colEnd) continue
    if (band.kind === 'cds') {
      cdsHit = true
      continue
    }
    return band.kind
  }
  if (cdsHit) return 'cds'
  return 'unknown'
}

function rowStartsNewBand(row: FullLocusRow): string | null {
  const fresh = row.bands.find(
    (b) => b.colStart === 0 && (b.kind === 'exon' || b.kind === 'intron'),
  )
  return fresh ? fresh.label : null
}

function formatCoord(n: number): string {
  return n.toLocaleString('en-US')
}

function reducedMotionScrollBehavior(): ScrollBehavior {
  if (typeof window === 'undefined') return 'smooth'
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
}

interface RowDOMProps {
  row: FullLocusRow
  basesPerRow: number
  coordinateMode: CoordinateMode
}

function RowDOM({ row, basesPerRow, coordinateMode }: RowDOMProps) {
  const codonStartCols = new Set<number>()
  for (const mark of row.codonMarks) codonStartCols.add(mark.col)

  const clinvarCols = new Map<number, string>()
  for (const pin of row.clinvarPins) {
    if (!clinvarCols.has(pin.col)) clinvarCols.set(pin.col, pin.label)
  }

  const variantCol = row.variantPin?.col ?? -1
  const fresh = rowStartsNewBand(row)
  const padLength = basesPerRow - row.bases.length
  const rowStart = coordinateMode === 'sequence' ? row.sequenceStart : row.genomicStart
  const rowEnd = coordinateMode === 'sequence' ? row.sequenceEnd : row.genomicEnd

  return (
    <div className={`fl-row${row.variantPin ? ' fl-row--has-variant' : ''}`}>
      <div className="fl-row-coord">
        <span className="fl-row-coord-start">{formatCoord(rowStart)}</span>
        {fresh ? <span className="fl-row-band-label">{fresh}</span> : null}
      </div>
      <div className="fl-row-bases">
        {row.bases.split('').map((base, col) => {
          const kind = bandKindAtCol(row, col)
          const isVariant = col === variantCol
          const isClinvar = clinvarCols.has(col)
          const isCodonStart = codonStartCols.has(col)
          const classes = [
            'fl-base',
            `fl-base--${kind}`,
            isCodonStart ? 'fl-base--codon-start' : '',
            isClinvar ? 'fl-base--clinvar' : '',
            isVariant ? 'fl-base--variant' : '',
          ]
            .filter(Boolean)
            .join(' ')
          const title = isVariant
            ? row.variantPin?.label
            : isClinvar
              ? clinvarCols.get(col)
              : undefined
          return (
            <span key={col} className={classes} title={title}>
              {base.toUpperCase()}
            </span>
          )
        })}
        {padLength > 0
          ? Array.from({ length: padLength }, (_, i) => (
              <span key={`pad-${i}`} className="fl-base fl-base--pad">
                &nbsp;
              </span>
            ))
          : null}
      </div>
      <div className="fl-row-end">{formatCoord(rowEnd)}</div>
    </div>
  )
}

const MemoRowDOM = memo(RowDOM)

function LocusHeader({
  rows,
  gene,
  coordinateMode,
  onCoordinateMode,
}: {
  rows: FullLocusRows
  gene: string
  coordinateMode: CoordinateMode
  onCoordinateMode: (mode: CoordinateMode) => void
}) {
  return (
    <div className="fl-header">
      <div className="fl-header-left">
        <span className="fl-header-gene">{gene}</span>
        <span className="fl-header-sep">·</span>
        <span className="fl-header-coord">
          {rows.chrom}:{formatCoord(rows.locusStart)}–{formatCoord(rows.locusEnd)} ({rows.strand})
        </span>
        <span className="fl-header-sep">·</span>
        <span className="fl-header-build">{rows.genomeBuild}</span>
      </div>
      <div className="fl-header-right">
        <span className="fl-header-stat">{formatCoord(rows.totalBases)} bp</span>
        <span className="fl-header-sep">·</span>
        <span className="fl-header-stat">{formatCoord(rows.rowCount)} rows</span>
        <span className="fl-header-sep">·</span>
        <span className="fl-header-stat">{rows.basesPerRow} bp/row</span>
        <div className="fl-coord-toggle" aria-label="Full-gene coordinate mode">
          <button
            type="button"
            className={coordinateMode === 'sequence' ? 'active' : ''}
            onClick={() => onCoordinateMode('sequence')}
          >
            1-based
          </button>
          <button
            type="button"
            className={coordinateMode === 'genomic' ? 'active' : ''}
            onClick={() => onCoordinateMode('genomic')}
          >
            Genomic
          </button>
        </div>
      </div>
    </div>
  )
}

const ROW_GAP = 1
const ESTIMATED_ROW_HEIGHT = 22
const OVERSCAN_ROWS = 10

export function FullLocusViewer({ model }: FullLocusViewerProps) {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const measureRef = useRef<HTMLDivElement | null>(null)
  const didInitialScrollRef = useRef(false)
  const [coordinateMode, setCoordinateMode] = useState<CoordinateMode>('sequence')
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportH, setViewportH] = useState(0)
  const [rowHeight, setRowHeight] = useState(ESTIMATED_ROW_HEIGHT)

  const rows = model.rows
  const rowCount = rows.rows.length
  const rowSlot = rowHeight + ROW_GAP
  const totalHeight = Math.max(0, rowCount * rowSlot - ROW_GAP)

  // Windowing math needs the live viewport height and a real row height. Rows
  // are uniform single-line monospace, so any mounted row is representative —
  // measure one and reuse it for every off-screen row we never mount.
  useLayoutEffect(() => {
    const scroller = scrollerRef.current
    if (!scroller) return
    const sync = () => {
      setViewportH(scroller.clientHeight)
      const rowEl = measureRef.current
      if (rowEl) {
        const h = rowEl.getBoundingClientRect().height
        if (h > 0) setRowHeight((prev) => (Math.abs(prev - h) > 0.5 ? h : prev))
      }
    }
    sync()
    if (typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(sync)
    ro.observe(scroller)
    return () => ro.disconnect()
  }, [])

  const overscanPx = OVERSCAN_ROWS * rowSlot
  const startIndex = Math.max(0, Math.floor((scrollTop - overscanPx) / rowSlot))
  const endIndex = Math.min(rowCount, Math.ceil((scrollTop + viewportH + overscanPx) / rowSlot))

  const visibleRows = useMemo(() => {
    const out: FullLocusRow[] = []
    for (let i = startIndex; i < endIndex; i += 1) {
      const row = rows.rows[i]
      if (row) out.push(row)
    }
    return out
  }, [rows, startIndex, endIndex])

  // Centre the variant row once — only after a measured row height + viewport
  // exist, so the index→pixel math lands on the right row even when it never
  // mounted at scrollTop 0.
  useEffect(() => {
    if (rows.variantRowIndex == null) return
    if (didInitialScrollRef.current || viewportH <= 0) return
    const scroller = scrollerRef.current
    if (!scroller) return
    didInitialScrollRef.current = true
    const target = rows.variantRowIndex * rowSlot - scroller.clientHeight * 0.3
    scroller.scrollTo({ top: Math.max(0, target), behavior: reducedMotionScrollBehavior() })
  }, [rows.variantRowIndex, rowSlot, viewportH])

  const warnings = model.warnings

  return (
    <div className="fl-viewer">
      <LocusHeader
        rows={rows}
        gene={model.gene}
        coordinateMode={coordinateMode}
        onCoordinateMode={setCoordinateMode}
      />
      <div
        className="fl-scroller"
        ref={scrollerRef}
        onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
      >
        <div className="fl-rows" style={{ position: 'relative', height: totalHeight }}>
          {visibleRows.map((row, k) => (
            <div
              key={row.rowIndex}
              ref={k === 0 ? measureRef : undefined}
              className="fl-row-anchor"
              style={{ position: 'absolute', left: 0, right: 0, top: row.rowIndex * rowSlot }}
            >
              <MemoRowDOM row={row} basesPerRow={rows.basesPerRow} coordinateMode={coordinateMode} />
            </div>
          ))}
        </div>
      </div>
      {warnings.length > 0 ? (
        <div className="fl-provenance" role="note">
          {warnings.map((w) => (
            <span key={w} className="fl-provenance-warn">{w}</span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function FullLocusUnsupportedBanner({
  gene,
  onBackToWindow,
}: {
  gene: string
  onBackToWindow: () => void
}) {
  return (
    <div className="fl-unsupported" role="status">
      <p>
        Full-gene view is available for the curated stress matrix
        (RPE65, CFTR, BRCA1, ABCA4, TP53). It is not available for
        <span className="fl-unsupported-gene"> {gene}</span> yet.
      </p>
      <button type="button" className="fl-unsupported-btn" onClick={onBackToWindow}>
        Back to Window view
      </button>
    </div>
  )
}
