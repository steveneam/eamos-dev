'use client'

/* FullLocusViewer — FGV-003 proof slice.

   Renders ViewerFullLocus rows in plain DOM. No selection, edit, scratchpad,
   minimap, or color schemes this slice — those land in FGV-004+ once we
   know what the row model actually feels like on RPE65/ABCA4. */

import { useEffect, useMemo, useRef } from 'react'
import type {
  FullLocusRow,
  FullLocusRows,
} from '@/lib/workbench/full-locus-layout'
import type { FullLocusViewModel } from '@/lib/workbench/full-locus-adapter'

interface FullLocusViewerProps {
  model: Extract<FullLocusViewModel, { kind: 'ready' }>
}

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

interface RowDOMProps {
  row: FullLocusRow
  basesPerRow: number
}

function RowDOM({ row, basesPerRow }: RowDOMProps) {
  const codonStartCols = new Set<number>()
  for (const mark of row.codonMarks) codonStartCols.add(mark.col)

  const clinvarCols = new Map<number, string>()
  for (const pin of row.clinvarPins) {
    if (!clinvarCols.has(pin.col)) clinvarCols.set(pin.col, pin.label)
  }

  const variantCol = row.variantPin?.col ?? -1
  const fresh = rowStartsNewBand(row)
  const padLength = basesPerRow - row.bases.length

  return (
    <div className={`fl-row${row.variantPin ? ' fl-row--has-variant' : ''}`}>
      <div className="fl-row-coord">
        <span className="fl-row-coord-start">{formatCoord(row.genomicStart)}</span>
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
      <div className="fl-row-end">{formatCoord(row.genomicEnd)}</div>
    </div>
  )
}

function LocusHeader({ rows, gene }: { rows: FullLocusRows; gene: string }) {
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
      </div>
    </div>
  )
}

export function FullLocusViewer({ model }: FullLocusViewerProps) {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const variantRowRef = useRef<HTMLDivElement>(null)

  const rows = model.rows

  useEffect(() => {
    if (rows.variantRowIndex == null) return
    const scroller = scrollerRef.current
    const target = variantRowRef.current
    if (!scroller || !target) return
    const offset = target.offsetTop - scroller.clientHeight * 0.3
    scroller.scrollTo({ top: Math.max(0, offset), behavior: 'auto' })
  }, [rows.variantRowIndex])

  const renderedRows = useMemo(
    () =>
      rows.rows.map((row) => (
        <div
          key={row.rowIndex}
          ref={row.rowIndex === rows.variantRowIndex ? variantRowRef : undefined}
          className="fl-row-anchor"
        >
          <RowDOM row={row} basesPerRow={rows.basesPerRow} />
        </div>
      )),
    [rows],
  )

  const warnings = model.warnings

  return (
    <div className="fl-viewer">
      <LocusHeader rows={rows} gene={model.gene} />
      <div className="fl-scroller" ref={scrollerRef}>
        <div className="fl-rows">{renderedRows}</div>
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
