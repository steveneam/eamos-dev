'use client'

import { useMemo } from 'react'
import { Disclosure } from '@/components/ui/Disclosure'
import type { PublicationTimeline } from '@/lib/backend'

interface PublicationTimelineChartProps {
  /** Variant-scope per-year series (live). */
  timeline: PublicationTimeline
  /** Gene-scope per-year series (currently illustrative mock). */
  geneTimeline?: PublicationTimeline | null
  /** Which series to plot — driven by the §6 scope toggle. */
  scope?: 'variant' | 'gene'
  /** True when the gene series is mock; surfaces a "Mock" tag on the gene view. */
  geneMock?: boolean
}

interface YearPoint {
  year: number
  count: number
}

// publications_by_year is SPARSE (only years with count > 0, sorted ascending).
// Zero-fill the gap years here so the x-axis is continuous year-to-year.
function buildSeries(timeline: PublicationTimeline): YearPoint[] {
  const raw = timeline.publications_by_year ?? []
  if (raw.length === 0) return []
  const sorted = [...raw].sort((a, b) => a.year - b.year)
  const byYear = new Map(sorted.map((p) => [p.year, p.count]))
  const minYear = sorted[0].year
  const maxYear = sorted[sorted.length - 1].year
  const series: YearPoint[] = []
  for (let year = minYear; year <= maxYear; year += 1) {
    series.push({ year, count: byYear.get(year) ?? 0 })
  }
  return series
}

const W = 600
const H = 226
const PAD = { left: 56, right: 16, top: 14, bottom: 48 }
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom
const baseY = PAD.top + plotH

export function PublicationTimelineChart({
  timeline,
  geneTimeline,
  scope = 'variant',
  geneMock = false,
}: PublicationTimelineChartProps) {
  const isGene = scope === 'gene' && geneTimeline != null
  const active = isGene ? geneTimeline : timeline
  const showMock = isGene && geneMock
  const series = useMemo(() => buildSeries(active), [active])

  if (series.length === 0) return null

  const n = series.length
  const minYear = series[0].year
  const maxYear = series[n - 1].year
  const peakCount = Math.max(1, ...series.map((p) => p.count))
  const step = Math.max(1, Math.ceil(peakCount / 4))
  const axisMax = step * Math.ceil(peakCount / step)
  const yTicks: number[] = []
  for (let v = 0; v <= axisMax; v += step) yTicks.push(v)

  const xFor = (i: number) => (n === 1 ? PAD.left + plotW / 2 : PAD.left + (i / (n - 1)) * plotW)
  const yFor = (count: number) => baseY - (count / axisMax) * plotH

  const linePath = series
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${xFor(i).toFixed(1)},${yFor(p.count).toFixed(1)}`)
    .join(' ')
  const areaPath = `${linePath} L${xFor(n - 1).toFixed(1)},${baseY.toFixed(1)} L${xFor(0).toFixed(1)},${baseY.toFixed(1)} Z`

  const labelStep = Math.max(1, Math.ceil(n / 8))
  const undated = active.total_without_year ?? 0
  const rangeLabel = minYear === maxYear ? `${minYear}` : `${minYear}–${maxYear}`

  const rangeText = undated > 0 ? `${rangeLabel} · +${undated} undated` : rangeLabel
  const summary = showMock ? (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      {rangeText}
      <span className="eamos-mock" title="Illustrative gene-wide per-year distribution — not yet wired to live data.">
        Mock
      </span>
    </span>
  ) : (
    rangeText
  )

  return (
    <Disclosure
      flush
      kicker={isGene ? 'Gene publications over time' : 'Variant publications over time'}
      showLabel="Show timeline"
      hideLabel="Hide timeline"
      summary={summary}
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label={`Publications per year from ${rangeLabel}, peak of ${peakCount} in a single year`}
        style={{ display: 'block' }}
      >
        {yTicks.map((tick) => {
          const y = yFor(tick)
          return (
            <g key={tick}>
              <line
                x1={PAD.left}
                y1={y}
                x2={W - PAD.right}
                y2={y}
                stroke="var(--line)"
                strokeWidth="0.5"
              />
              <line x1={PAD.left - 5} y1={y} x2={PAD.left} y2={y} stroke="var(--ink-4)" strokeWidth="1" />
              <text
                x={PAD.left - 9}
                y={y + 3}
                textAnchor="end"
                style={{ fontSize: 9.5, fill: 'var(--ink-4)', fontFamily: 'var(--mono)' }}
              >
                {tick}
              </text>
            </g>
          )
        })}

        <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={baseY} stroke="var(--ink-4)" strokeWidth="1" />
        <line x1={PAD.left} y1={baseY} x2={W - PAD.right} y2={baseY} stroke="var(--ink-4)" strokeWidth="1" />

        <path d={areaPath} fill="var(--teal)" fillOpacity={showMock ? 0.05 : 0.1} />
        <path
          d={linePath}
          fill="none"
          stroke="var(--teal)"
          strokeWidth="1.75"
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeDasharray={showMock ? '4 3' : undefined}
          strokeOpacity={showMock ? 0.75 : 1}
        />

        {series.map((p, i) => {
          const cx = xFor(i)
          const cy = yFor(p.count)
          const showLabel = i % labelStep === 0 || i === n - 1
          return (
            <g key={p.year}>
              {p.count > 0 && <circle cx={cx} cy={cy} r="3" fill="var(--teal)" />}
              <circle cx={cx} cy={cy} r="9" fill="transparent">
                <title>{`${p.year}: ${p.count} ${p.count === 1 ? 'publication' : 'publications'}`}</title>
              </circle>
              {showLabel && (
                <>
                  <line x1={cx} y1={baseY} x2={cx} y2={baseY + 5} stroke="var(--ink-4)" strokeWidth="1" />
                  <text
                    x={cx}
                    y={baseY + 17}
                    textAnchor="middle"
                    style={{ fontSize: 9.5, fill: 'var(--ink-4)', fontFamily: 'var(--mono)' }}
                  >
                    {p.year}
                  </text>
                </>
              )}
            </g>
          )
        })}

        <text
          x={PAD.left + plotW / 2}
          y={H - 6}
          textAnchor="middle"
          style={{ fontSize: 11, fontWeight: 600, fill: 'var(--ink-3)' }}
        >
          Year
        </text>
        <text
          x={16}
          y={PAD.top + plotH / 2}
          textAnchor="middle"
          transform={`rotate(-90 16 ${PAD.top + plotH / 2})`}
          style={{ fontSize: 11, fontWeight: 600, fill: 'var(--ink-3)' }}
        >
          Number of publications
        </text>
      </svg>
      <p style={{ fontSize: 11, color: 'var(--ink-4)', margin: '6px 2px 0' }}>
        {active.total_with_year} dated {active.total_with_year === 1 ? 'publication' : 'publications'}
        {isGene ? ` across ${rangeLabel} (gene-wide)` : ''}
        {undated > 0 && ` · ${undated} without a publication year`}
      </p>
    </Disclosure>
  )
}
