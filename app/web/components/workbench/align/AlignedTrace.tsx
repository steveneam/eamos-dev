'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import type { AlignmentCell } from '@/lib/workbench/alignment-pairwise'
import type { ReadTrace } from './read-model'

interface AlignedTraceProps {
  /** Alignment columns — one column per cell, shared by the char rows + trace. */
  cells: AlignmentCell[]
  trace: ReadTrace | null
  /** read base index = trimStart + cell.editedIndex. */
  trimStart: number
  realMismatch: Set<number>
  lowQMismatch: Set<number>
  hetIndices: Set<number>
  /** reference indices matched by the Find search. */
  searchHits: Set<number>
  activeSearchStart: number | null
  /** Active difference column (chip / ◀▶ jump). */
  activeCol: number | null
  showTrace: boolean
  readLabel: string
}

const Q_TOP = 2
const Q_MAXH = 8
const REF_Y = 22
const READ_Y = 38
const TRACE_TOP = 48
const TRACE_BASELINE = 168
const HET_Y = 172
const FULL_HEIGHT = 182
const CHARS_HEIGHT = 46
const Q_MAX = 60

/** One shared base-column coordinate for the ref/read characters AND the trace:
 *  the trace is warped so each read peak sits exactly under its base column, and
 *  one compression control + one scroll drive both (true 1:1 correspondence). */
export function AlignedTrace({
  cells,
  trace,
  trimStart,
  realMismatch,
  lowQMismatch,
  hetIndices,
  searchHits,
  activeSearchStart,
  activeCol,
  showTrace,
  readLabel,
}: AlignedTraceProps) {
  const [intensity, setIntensity] = useState(1)
  const [baseStep, setBaseStep] = useState(16)
  const [controlsShown, setControlsShown] = useState(false)
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => () => {
    if (hideTimer.current) clearTimeout(hideTimer.current)
  }, [])
  const reveal = () => {
    setControlsShown(true)
    if (hideTimer.current) clearTimeout(hideTimer.current)
    hideTimer.current = setTimeout(() => setControlsShown(false), 1600)
  }
  const hide = () => {
    if (hideTimer.current) clearTimeout(hideTimer.current)
    setControlsShown(false)
  }

  const width = Math.max(360, cells.length * baseStep)
  const height = showTrace && trace ? FULL_HEIGHT : CHARS_HEIGHT
  const amplitude = TRACE_BASELINE - TRACE_TOP
  const colCenter = (col: number) => col * baseStep + baseStep / 2

  // Peak anchors: which sample sits under which column (monotonic).
  const anchors = useMemo(() => {
    const out: { col: number; sample: number }[] = []
    if (!trace) return out
    cells.forEach((cell, col) => {
      if (cell.editedIndex === null) return
      const peak = trace.baseCalls[trimStart + cell.editedIndex]?.peak
      if (peak != null) out.push({ col, sample: peak })
    })
    return out
  }, [cells, trace, trimStart])

  const globalMax = useMemo(() => {
    let max = 1
    if (trace) for (const c of trace.channels) for (const v of c.values) if (v > max) max = v
    return max
  }, [trace])

  // Warp samples → x in base-column space (peak[col] → column centre).
  const polylines = useMemo(() => {
    if (!trace || !showTrace || anchors.length < 2) return []
    const minS = anchors[0].sample
    const maxS = anchors[anchors.length - 1].sample
    const stride = Math.max(1, Math.floor((maxS - minS) / Math.max(1, width * 1.5)))
    const mapped: { s: number; x: number }[] = []
    let k = 0
    for (let s = minS; s <= maxS; s += stride) {
      while (k < anchors.length - 2 && s > anchors[k + 1].sample) k += 1
      const a = anchors[k]
      const b = anchors[k + 1]
      const t = b.sample === a.sample ? 0 : (s - a.sample) / (b.sample - a.sample)
      mapped.push({ s, x: colCenter(a.col) + t * (colCenter(b.col) - colCenter(a.col)) })
    }
    return trace.channels.map((channel) => ({
      base: channel.base,
      points: mapped
        .map(({ s, x }) => {
          const v = Math.min((channel.values[s] / globalMax) * intensity, 1.3)
          return `${x.toFixed(1)},${Math.max(TRACE_TOP, TRACE_BASELINE - v * amplitude).toFixed(1)}`
        })
        .join(' '),
    }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace, showTrace, anchors, width, baseStep, intensity, globalMax, amplitude])

  const scrollToCol = (col: number) => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ left: Math.max(0, colCenter(col) - el.clientWidth / 2), behavior: 'smooth' })
  }
  useEffect(() => {
    if (activeCol !== null) scrollToCol(activeCol)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCol, baseStep])
  useEffect(() => {
    if (activeSearchStart === null) return
    const col = cells.findIndex((c) => c.referenceIndex === activeSearchStart)
    if (col >= 0) scrollToCol(col)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSearchStart, baseStep])

  if (cells.length === 0) return null

  const baseClass = (b: string) => (b === 'A' || b === 'C' || b === 'G' || b === 'T' ? b : 'gap')

  return (
    <div className="aligned-trace" onMouseMove={reveal} onMouseLeave={hide}>
      <div className={`chromatogram-controls${controlsShown ? ' show' : ''}`} aria-label="Trace scale">
        <label title="Peak intensity (vertical scale)">
          <span aria-hidden>↕</span>
          <input type="range" min={0.4} max={3} step={0.1} value={intensity} aria-label="Peak intensity"
            onChange={(e) => setIntensity(Number(e.target.value))} />
        </label>
        <label title="Base spacing (horizontal scale) — moves bases + trace together">
          <span aria-hidden>↔</span>
          <input type="range" min={9} max={48} step={1} value={baseStep} aria-label="Base spacing"
            onChange={(e) => setBaseStep(Number(e.target.value))} />
        </label>
      </div>
      <div className="aligned-trace-labels" aria-hidden>
        <span className="aln-row-label">REF</span>
        <span className="aln-row-label read" title={readLabel}>{readLabel}</span>
      </div>
      <div className="chromatogram-scroll" ref={scrollRef}>
        <div className="chromatogram-canvas" style={{ width }}>
          <svg className="chromatogram-svg" viewBox={`0 0 ${width} ${height}`} width={width} height={height}
            role="img" aria-label="Aligned reference, read and chromatogram">
            {/* column bands */}
            {cells.map((cell, col) => {
              const rb = cell.editedIndex === null ? null : trimStart + cell.editedIndex
              const isMismatch = cell.kind === 'mismatch'
              const isGap = cell.kind === 'gap'
              const lowq = rb !== null && lowQMismatch.has(rb)
              const search = cell.referenceIndex !== null && searchHits.has(cell.referenceIndex)
              const activeSearch = cell.referenceIndex !== null && cell.referenceIndex === activeSearchStart
              const activeColHit = col === activeCol
              const cls = activeColHit
                ? 'aln-band active'
                : isMismatch
                  ? `aln-band mismatch${lowq ? ' lowq' : ''}`
                  : isGap
                    ? 'aln-band gap'
                    : activeSearch
                      ? 'aln-band search-active'
                      : search
                        ? 'aln-band search'
                        : null
              if (!cls && !cell.isTarget) return null
              return (
                <g key={`band-${col}`}>
                  {cls && <rect className={cls} x={col * baseStep} y={0} width={baseStep} height={height} />}
                  {cell.isTarget && (
                    <rect className="aln-band target" x={col * baseStep + 0.75} y={0.75}
                      width={baseStep - 1.5} height={height - 1.5} />
                  )}
                </g>
              )
            })}

            {showTrace && trace && (
              <>
                <line className="chromatogram-baseline" x1={0} y1={TRACE_BASELINE} x2={width} y2={TRACE_BASELINE} />
                {polylines.map((line) => (
                  <polyline key={line.base} className={`align-trace-channel ${line.base}`} points={line.points}
                    vectorEffect="non-scaling-stroke" />
                ))}
              </>
            )}

            {/* per-column characters (+ het marker + quality bar) */}
            {cells.map((cell, col) => {
              const cx = colCenter(col)
              const rb = cell.editedIndex === null ? null : trimStart + cell.editedIndex
              const real = rb !== null && realMismatch.has(rb)
              const lowq = rb !== null && lowQMismatch.has(rb)
              const het = rb !== null && hetIndices.has(rb)
              const q = rb !== null ? (trace?.baseCalls[rb]?.qScore ?? null) : null
              const readBase = cell.editedBase
              const readCls = real ? ' mismatch' : lowq ? ' lowq' : ''
              return (
                <g key={`col-${col}`}>
                  {showTrace && trace && q !== null && q > 0 && (
                    <rect className="chromatogram-qbar" x={cx - 1.4} y={Q_TOP}
                      width={2.8} height={(Math.min(q, Q_MAX) / Q_MAX) * Q_MAXH} />
                  )}
                  <text className={`chromatogram-ref ${baseClass(cell.referenceBase)}`} x={cx} y={REF_Y}
                    textAnchor="middle">{cell.referenceBase}</text>
                  <text className={`chromatogram-letter ${baseClass(readBase)}${readCls}`} x={cx} y={READ_Y}
                    textAnchor="middle">{readBase}</text>
                  {showTrace && trace && het && (
                    <rect className="chromatogram-het" x={col * baseStep} y={HET_Y} width={baseStep} height={5} />
                  )}
                </g>
              )
            })}
          </svg>
        </div>
      </div>
    </div>
  )
}
