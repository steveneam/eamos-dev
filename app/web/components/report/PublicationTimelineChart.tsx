'use client'

import { useMemo, useState } from 'react'
import type { PublicationTimeline } from '@/lib/backend'

interface PublicationTimelineChartProps {
  timeline: PublicationTimeline
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
// left/bottom padding leaves room for the axis tick labels + axis titles.
const PAD = { left: 56, right: 16, top: 14, bottom: 48 }
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom
const baseY = PAD.top + plotH

export function PublicationTimelineChart({ timeline }: PublicationTimelineChartProps) {
  const [open, setOpen] = useState(false)
  const series = useMemo(() => buildSeries(timeline), [timeline])

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

  // Cap x-axis labels to avoid crowding; always keep first + last.
  const labelStep = Math.max(1, Math.ceil(n / 8))
  const undated = timeline.total_without_year ?? 0
  const rangeLabel = minYear === maxYear ? `${minYear}` : `${minYear}–${maxYear}`

  return (
    <div
      className="mb-5 rounded-xl overflow-hidden"
      style={{ border: '0.5px solid var(--line)', background: 'var(--bg-2, var(--bg))' }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
      >
        <span className="flex items-center gap-2">
          <svg
            width="11"
            height="11"
            viewBox="0 0 12 12"
            aria-hidden="true"
            style={{
              transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: 'transform 0.15s ease',
              color: 'var(--ink-4)',
            }}
          >
            <path d="M4 2 L8 6 L4 10" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>Publications over time</span>
          <span style={{ fontSize: 11.5, color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>{rangeLabel}</span>
        </span>
        {undated > 0 && (
          <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>+{undated} undated</span>
        )}
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1">
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

            {/* axis lines */}
            <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={baseY} stroke="var(--ink-4)" strokeWidth="1" />
            <line x1={PAD.left} y1={baseY} x2={W - PAD.right} y2={baseY} stroke="var(--ink-4)" strokeWidth="1" />

            <path d={areaPath} fill="var(--teal)" fillOpacity="0.1" />
            <path d={linePath} fill="none" stroke="var(--teal)" strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />

            {series.map((p, i) => {
              const cx = xFor(i)
              const cy = yFor(p.count)
              const showLabel = i % labelStep === 0 || i === n - 1
              return (
                <g key={p.year}>
                  {p.count > 0 && <circle cx={cx} cy={cy} r="3" fill="var(--teal)" />}
                  {/* generous transparent hit target for the native tooltip */}
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

            {/* axis titles */}
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
            {timeline.total_with_year} dated {timeline.total_with_year === 1 ? 'publication' : 'publications'}
            {undated > 0 && ` · ${undated} without a publication year`}
          </p>
        </div>
      )}
    </div>
  )
}
