'use client'

import { useState } from 'react'
import type { PopulationAgeHistogramView } from '@/lib/backend'
import { CopyButton } from '@/components/ui/CopyButton'

function formatInteger(value: number | null | undefined): string {
  return value == null ? 'Not reported' : new Intl.NumberFormat('en-US').format(value)
}

// The four age series, in display + export order.
const AGE_SERIES: Array<{ label: string; sequencingType: AgeChartSequencingType; seriesKind: AgeChartSeriesKind }> = [
  { label: 'Exome · variant carriers', sequencingType: 'exome', seriesKind: 'variant_carriers' },
  { label: 'Exome · all individuals', sequencingType: 'exome', seriesKind: 'all_individuals' },
  { label: 'Genome · variant carriers', sequencingType: 'genome', seriesKind: 'variant_carriers' },
  { label: 'Genome · all individuals', sequencingType: 'genome', seriesKind: 'all_individuals' },
]

// Tab-separated grid (age bin × the four series) for one-click paste into Excel/Sheets.
function buildAgeDistributionTsv(histograms: PopulationAgeHistogramView[]): string {
  const series = AGE_SERIES.map((s) => ({
    label: s.label,
    bins: (() => {
      const hist = findAgeHistogram(histograms, s.sequencingType, s.seriesKind)
      return hist ? ageChartBins(hist) : []
    })(),
  }))
  const labelOrder: string[] = []
  series.forEach((s) => s.bins.forEach((bin) => {
    if (!labelOrder.includes(bin.label)) labelOrder.push(bin.label)
  }))
  const header = ['Age', ...series.map((s) => s.label)].join('\t')
  const rows = labelOrder.map((label) =>
    [label, ...series.map((s) => {
      const bin = s.bins.find((b) => b.label === label)
      return bin ? String(bin.count) : ''
    })].join('\t'),
  )
  return [header, ...rows].join('\n')
}

export function PopulationAgeDistribution({ histograms }: { histograms: PopulationAgeHistogramView[] }) {
  // No world map here — it adds nothing to an age view. The four charts (exome /
  // genome × variant carriers / all individuals) get the full width as a clean 2×2.
  const hasData = histograms.length > 0
  return (
    <div
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 8,
        background: 'var(--bg)',
        padding: 12,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div style={{ minWidth: 0 }}>
          <div className="eamos-kicker">Source age distribution</div>
          <div style={{ marginTop: 6, fontSize: 11, lineHeight: 1.45, color: 'var(--ink-4)' }}>
            Exact gnomAD age-bin counts split by sequencing track — exomes and genomes, each shown for
            variant carriers and for all individuals.
          </div>
        </div>
        {hasData && <CopyButton text={buildAgeDistributionTsv(histograms)} label="Copy age distribution data" />}
      </div>
      <AgeHistogramGrid histograms={histograms} />
    </div>
  )
}

type AgeChartSequencingType = 'exome' | 'genome'
type AgeChartSeriesKind = 'variant_carriers' | 'all_individuals'

function AgeHistogramGrid({ histograms }: { histograms: PopulationAgeHistogramView[] }) {
  // Four charts in a 2×2: exome / genome × variant carriers / all individuals. Colour
  // tracks the sequencing source (exome blue, genome purple); the title names the series.
  const panels: Array<{
    key: string
    title: string
    sequencingType: AgeChartSequencingType
    seriesKind: AgeChartSeriesKind
    fill: string
    unit: string
  }> = [
    { key: 'exome-carriers', title: 'Exome · variant carriers', sequencingType: 'exome', seriesKind: 'variant_carriers', fill: '#3d7dbf', unit: 'carriers' },
    { key: 'exome-all', title: 'Exome · all individuals', sequencingType: 'exome', seriesKind: 'all_individuals', fill: '#3d7dbf', unit: 'individuals' },
    { key: 'genome-carriers', title: 'Genome · variant carriers', sequencingType: 'genome', seriesKind: 'variant_carriers', fill: '#8059b7', unit: 'carriers' },
    { key: 'genome-all', title: 'Genome · all individuals', sequencingType: 'genome', seriesKind: 'all_individuals', fill: '#8059b7', unit: 'individuals' },
  ]

  return (
    <div
      className="mt-3"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: 10,
      }}
    >
      {panels.map((panel) => (
        <AgeHistogramCard
          key={panel.key}
          title={panel.title}
          histogram={findAgeHistogram(histograms, panel.sequencingType, panel.seriesKind)}
          fill={panel.fill}
          unit={panel.unit}
        />
      ))}
    </div>
  )
}

function findAgeHistogram(
  histograms: PopulationAgeHistogramView[],
  sequencingType: AgeChartSequencingType,
  seriesKind: AgeChartSeriesKind,
): PopulationAgeHistogramView | null {
  return (
    histograms.find(
      (histogram) =>
        histogram.sequencing_type === sequencingType && histogram.series_kind === seriesKind,
    ) ?? null
  )
}

function AgeHistogramCard({
  title,
  histogram,
  fill,
  unit,
}: {
  title: string
  histogram: PopulationAgeHistogramView | null
  fill: string
  unit: string
}) {
  const [hoveredBin, setHoveredBin] = useState<number | null>(null)
  const bins = histogram ? ageChartBins(histogram) : []
  const maxCount = Math.max(0, ...bins.map((bin) => bin.count))
  const { yMax, ticks } = niceAxis(maxCount)
  const chartWidth = 340
  const chartHeight = 192
  // Left gutter holds the rotated axis label (x=12) AND the right-anchored y-tick
  // numbers (at padLeft-7). Wide enough that the longest thousands-separated tick
  // ("20,000") clears the rotated label without overlap.
  const padLeft = 56
  const padRight = 10
  const padTop = 14
  const padBottom = 38
  const plotWidth = chartWidth - padLeft - padRight
  const plotHeight = chartHeight - padTop - padBottom
  const groupWidth = bins.length > 0 ? plotWidth / bins.length : plotWidth
  const barWidth = Math.max(4, Math.min(18, groupWidth * 0.58))

  return (
    <div
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 8,
        background: 'var(--bg-soft)',
        padding: 10,
        minWidth: 0,
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.2 }}>
          {title}
        </div>
        {histogram && (
          <div style={{ fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums', fontSize: 10.5, color: 'var(--ink-3)' }}>
            n={formatInteger(histogramTotal(histogram))}
          </div>
        )}
      </div>

      {!histogram || bins.length === 0 ? (
        <div
          style={{
            minHeight: 154,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--ink-4)',
            fontSize: 11.5,
            textAlign: 'center',
            padding: 10,
          }}
        >
          Age distribution not reported
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          role="img"
          aria-label={`${title} age histogram`}
          style={{ width: '100%', minHeight: 174, display: 'block' }}
        >
          {ticks.map((tick) => {
            const y = padTop + plotHeight - (yMax > 0 ? (tick / yMax) * plotHeight : 0)
            return (
              <g key={tick}>
                <line x1={padLeft} y1={y} x2={chartWidth - padRight} y2={y} style={{ stroke: 'var(--line)' }} strokeWidth="0.8" />
                <text x={padLeft - 7} y={y + 3} textAnchor="end" fontSize="8.2" style={{ fill: 'var(--ink-4)', fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums' }}>
                  {formatInteger(tick)}
                </text>
              </g>
            )
          })}
          <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + plotHeight} style={{ stroke: 'var(--ink-5)' }} strokeWidth="0.8" />
          <line x1={padLeft} y1={padTop + plotHeight} x2={chartWidth - padRight} y2={padTop + plotHeight} style={{ stroke: 'var(--ink-5)' }} strokeWidth="0.8" />

          {bins.map((bin, binIndex) => {
            const height = yMax > 0 ? (bin.count / yMax) * plotHeight : 0
            const visibleHeight = bin.count > 0 ? Math.max(2, height) : 0
            const cx = padLeft + binIndex * groupWidth + groupWidth / 2
            const x = cx - barWidth / 2
            const y = padTop + plotHeight - visibleHeight
            const hovered = hoveredBin === binIndex
            const showLabel =
              bins.length <= 9 || binIndex % 2 === 0 || bin.label.startsWith('<') || bin.label.endsWith('+')
            return (
              <g
                key={`${bin.label}-${binIndex}`}
                onMouseEnter={() => setHoveredBin(binIndex)}
                onMouseLeave={() => setHoveredBin((current) => (current === binIndex ? null : current))}
              >
                {/* Full-column hit area so the (often thin) bar is easy to hover. */}
                <rect x={padLeft + binIndex * groupWidth} y={padTop} width={groupWidth} height={plotHeight} fill="transparent" />
                {hovered && (
                  <rect x={padLeft + binIndex * groupWidth} y={padTop} width={groupWidth} height={plotHeight} fill={fill} opacity={0.08} />
                )}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={visibleHeight}
                  rx="1.5"
                  fill={fill}
                  opacity={bin.count > 0 ? (hovered ? 1 : 0.88) : 0}
                >
                  <title>{`${title}, age ${bin.label}: ${formatInteger(bin.count)} ${unit}`}</title>
                </rect>
                {hovered && bin.count > 0 && (
                  <text
                    x={cx}
                    y={Math.max(8, y - 4)}
                    textAnchor="middle"
                    fontSize="8.5"
                    fontWeight={700}
                    style={{ fill: 'var(--ink)', fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums' }}
                  >
                    {formatInteger(bin.count)}
                  </text>
                )}
                {showLabel && (
                  <text x={cx} y={chartHeight - 20} textAnchor="middle" fontSize="7.6" style={{ fill: hovered ? 'var(--ink)' : 'var(--ink-4)', fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums' }}>
                    {bin.label}
                  </text>
                )}
              </g>
            )
          })}

          <text x={padLeft + plotWidth / 2} y={chartHeight - 6} textAnchor="middle" fontSize="9.5" style={{ fill: 'var(--ink-3)' }}>
            Age
          </text>
          <text x="12" y={padTop + plotHeight / 2} textAnchor="middle" fontSize="9.5" style={{ fill: 'var(--ink-3)' }} transform={`rotate(-90 12 ${padTop + plotHeight / 2})`}>
            {unit === 'carriers' ? '# variant carriers' : '# individuals'}
          </text>
        </svg>
      )}
    </div>
  )
}

function ageChartBins(histogram: PopulationAgeHistogramView): Array<{ label: string; count: number }> {
  const bins: Array<{ label: string; count: number }> = []
  if (histogram.n_smaller != null) {
    bins.push({ label: '<30', count: histogram.n_smaller })
  }
  bins.push(...histogram.bins.map((bin) => ({ label: bin.label, count: bin.count })))
  if (histogram.n_larger != null) {
    bins.push({ label: '80+', count: histogram.n_larger })
  }
  return bins
}

function histogramTotal(histogram: PopulationAgeHistogramView): number {
  return histogram.bins.reduce((sum, bin) => sum + bin.count, 0) + (histogram.n_smaller ?? 0) + (histogram.n_larger ?? 0)
}

// Round the count axis to a clean scale: pick a "nice" step (1 / 2 / 5 × 10ⁿ)
// aiming for ~5 intervals, so ticks land on whole readable numbers (0, 10, 20, 30,
// 40, 50) instead of the quartered values a raw max produced (0, 13, 25, 38, 50).
function niceAxis(maxCount: number): { yMax: number; ticks: number[] } {
  if (maxCount <= 0) return { yMax: 1, ticks: [0, 1] }
  if (maxCount <= 5) {
    return { yMax: maxCount, ticks: Array.from({ length: maxCount + 1 }, (_, index) => index) }
  }
  const rawStep = maxCount / 5
  const magnitude = 10 ** Math.floor(Math.log10(rawStep))
  const normalized = rawStep / magnitude
  const niceStep = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * magnitude
  const yMax = Math.ceil(maxCount / niceStep) * niceStep
  const ticks: number[] = []
  for (let tick = 0; tick <= yMax + niceStep / 2; tick += niceStep) {
    ticks.push(Math.round(tick))
  }
  return { yMax, ticks }
}

