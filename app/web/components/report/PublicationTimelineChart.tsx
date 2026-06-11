'use client'

import { useMemo, useState } from 'react'
import { Disclosure } from '@/components/ui/Disclosure'
import type { PublicationTimeline, PubMedArticle } from '@/lib/backend'

interface PublicationTimelineChartProps {
  timeline: PublicationTimeline
  articles?: PubMedArticle[]
  onOpenArticle?: (article: PubMedArticle) => void
}

interface YearPoint {
  year: number
  count: number
}

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

function publicationYear(article: PubMedArticle): number | null {
  const value = article.publication_date || article.year || ''
  const match = String(value).match(/(\d{4})/)
  return match ? Number(match[1]) : null
}

function articleMeta(article: PubMedArticle): string {
  return [article.authors, article.journal, article.publication_date || article.year]
    .filter(Boolean)
    .join(' | ')
}

const W = 600
const H = 226
const PAD = { left: 56, right: 16, top: 14, bottom: 48 }
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom
const baseY = PAD.top + plotH

export function PublicationTimelineChart({
  timeline,
  articles = [],
  onOpenArticle,
}: PublicationTimelineChartProps) {
  const [hoveredYear, setHoveredYear] = useState<number | null>(null)
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const series = useMemo(() => buildSeries(timeline), [timeline])
  const articlesByYear = useMemo(() => {
    const grouped = new Map<number, PubMedArticle[]>()
    for (const article of articles) {
      const year = publicationYear(article)
      if (year == null) continue
      const bucket = grouped.get(year) ?? []
      bucket.push(article)
      grouped.set(year, bucket)
    }
    return grouped
  }, [articles])

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
  const points = series.map((point, i) => ({
    ...point,
    x: xFor(i),
    y: yFor(point.count),
  }))

  const linePath = series
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${xFor(i).toFixed(1)},${yFor(p.count).toFixed(1)}`)
    .join(' ')
  const areaPath = `${linePath} L${xFor(n - 1).toFixed(1)},${baseY.toFixed(1)} L${xFor(0).toFixed(1)},${baseY.toFixed(1)} Z`

  const labelStep = Math.max(1, Math.ceil(n / 8))
  const undated = timeline.total_without_year ?? 0
  const rangeLabel = minYear === maxYear ? `${minYear}` : `${minYear}-${maxYear}`
  const rangeText = undated > 0 ? `${rangeLabel} | +${undated} undated` : rangeLabel
  const summary = (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      {rangeText}
      <span
        style={{
          border: '0.5px solid var(--teal-bdr, var(--line))',
          background: 'var(--teal-tint)',
          borderRadius: 999,
          color: 'var(--teal-deep)',
          fontSize: 10,
          fontWeight: 700,
          padding: '1px 6px',
          textTransform: 'uppercase',
        }}
      >
        Live
      </span>
    </span>
  )

  const hoveredPoint = hoveredYear == null ? null : points.find((point) => point.year === hoveredYear) ?? null
  const tooltipW = 124
  const tooltipX =
    hoveredPoint == null
      ? 0
      : Math.max(PAD.left, Math.min(W - PAD.right - tooltipW, hoveredPoint.x - tooltipW / 2))
  const tooltipY = hoveredPoint == null ? 0 : Math.max(PAD.top, hoveredPoint.y - 42)
  const selectedCount = selectedYear == null ? 0 : series.find((p) => p.year === selectedYear)?.count ?? 0
  const selectedArticles = selectedYear == null ? [] : articlesByYear.get(selectedYear) ?? []
  const loadedGap = Math.max(0, selectedCount - selectedArticles.length)

  return (
    <Disclosure
      flush
      kicker="Variant publications over time"
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

        <path d={areaPath} fill="var(--teal)" fillOpacity={0.1} />
        <path
          d={linePath}
          fill="none"
          stroke="var(--teal)"
          strokeWidth="1.75"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {points.map((p, i) => {
          const showLabel = i % labelStep === 0 || i === n - 1
          const activePoint = hoveredYear === p.year || selectedYear === p.year
          const hasCount = p.count > 0
          return (
            <g
              key={p.year}
              role={hasCount ? 'button' : undefined}
              tabIndex={hasCount ? 0 : -1}
              aria-label={`${p.year}: ${p.count} ${p.count === 1 ? 'publication' : 'publications'}`}
              onMouseEnter={() => setHoveredYear(p.year)}
              onMouseLeave={() => setHoveredYear(null)}
              onFocus={() => setHoveredYear(p.year)}
              onBlur={() => setHoveredYear(null)}
              onClick={() => hasCount && setSelectedYear(p.year)}
              onKeyDown={(event) => {
                if (!hasCount) return
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelectedYear(p.year)
                }
              }}
              style={{ cursor: hasCount ? 'pointer' : 'default', outline: 'none' }}
            >
              {hasCount && (
                <>
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={activePoint ? 10 : 6}
                    fill="var(--teal)"
                    opacity={activePoint ? 0.14 : 0}
                    style={{ transition: 'opacity var(--dur-1) var(--ease-standard), r var(--dur-1) var(--ease-standard)' }}
                  />
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={activePoint ? 4.6 : 3}
                    fill="var(--teal)"
                    stroke="var(--bg)"
                    strokeWidth={activePoint ? 1.5 : 0}
                    style={{ transition: 'r var(--dur-1) var(--ease-standard), stroke-width var(--dur-1) var(--ease-standard)' }}
                  />
                </>
              )}
              <circle cx={p.x} cy={p.y} r="10" fill="transparent">
                <title>{`${p.year}: ${p.count} ${p.count === 1 ? 'publication' : 'publications'}`}</title>
              </circle>
              {showLabel && (
                <>
                  <line x1={p.x} y1={baseY} x2={p.x} y2={baseY + 5} stroke="var(--ink-4)" strokeWidth="1" />
                  <text
                    x={p.x}
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

        {hoveredPoint && (
          <g pointerEvents="none">
            <rect
              x={tooltipX}
              y={tooltipY}
              width={tooltipW}
              height="31"
              rx="6"
              fill="var(--ink)"
              opacity="0.94"
            />
            <text
              x={tooltipX + 10}
              y={tooltipY + 13}
              style={{ fontSize: 10.5, fill: 'var(--bg)', fontWeight: 700 }}
            >
              {hoveredPoint.year}
            </text>
            <text
              x={tooltipX + 10}
              y={tooltipY + 25}
              style={{ fontSize: 10, fill: 'var(--bg-soft)' }}
            >
              {hoveredPoint.count} {hoveredPoint.count === 1 ? 'publication' : 'publications'}
            </text>
          </g>
        )}

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
        {undated > 0 && ` | ${undated} without a publication year`}
      </p>
      {selectedYear != null && (
        <div
          role="dialog"
          aria-label={`Publications from ${selectedYear}`}
          style={{
            marginTop: 10,
            border: '0.5px solid var(--line)',
            borderRadius: 'var(--r-sm)',
            background: 'var(--bg)',
            boxShadow: 'var(--elev-3)',
            padding: 12,
          }}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)' }}>
                {selectedYear}: {selectedCount} {selectedCount === 1 ? 'publication' : 'publications'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--ink-4)', marginTop: 2 }}>
                {selectedArticles.length} loaded row{selectedArticles.length === 1 ? '' : 's'}
                {loadedGap > 0 ? `, ${loadedGap} not loaded in the visible list` : ''}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSelectedYear(null)}
              className="eamos-toggle-btn"
              style={{ padding: '4px 8px', fontSize: 11 }}
            >
              Close
            </button>
          </div>
          {selectedArticles.length > 0 ? (
            <div
              style={{
                marginTop: 10,
                maxHeight: 220,
                overflowY: 'auto',
                borderTop: '0.5px solid var(--line)',
              }}
            >
              {selectedArticles.map((article) => (
                <button
                  key={article.pmid}
                  type="button"
                  onClick={() => onOpenArticle?.(article)}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    background: 'transparent',
                    border: 0,
                    borderBottom: '0.5px solid var(--line)',
                    padding: '9px 2px',
                    cursor: onOpenArticle ? 'pointer' : 'default',
                  }}
                >
                  <span style={{ display: 'block', fontSize: 12.5, fontWeight: 650, color: 'var(--ink)' }}>
                    {article.title || `PMID ${article.pmid}`}
                  </span>
                  <span style={{ display: 'block', fontSize: 10.5, color: 'var(--ink-4)', marginTop: 2 }}>
                    PMID {article.pmid}
                    {articleMeta(article) ? ` | ${articleMeta(article)}` : ''}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 11.5, color: 'var(--ink-4)', margin: '10px 0 0' }}>
              No loaded publication rows for this year yet. Load more rows or open PubMed to inspect the full live set.
            </p>
          )}
        </div>
      )}
    </Disclosure>
  )
}
