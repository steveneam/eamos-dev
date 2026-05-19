import { useMemo } from 'react'
import type { IndelBin } from '@/lib/workbench/crispr-tide-sample'

interface IndelSpectrumProps {
  spectrum: IndelBin[]
  /** Render the AI-predicted series alongside observed (Blueprint 2). */
  showPredicted: boolean
}

const PAD_L = 38
const PAD_B = 26
const PAD_T = 10
const H = 200
const GROUP_W = 34

/**
 * Hand-rolled SVG grouped bar chart (Observed vs AI-Predicted indel
 * frequencies), same zero-dependency approach as the Workbench PhyloP
 * conservation track. Falls back to a single observed series when no
 * repair-outcome model is available (real backend until §7 ships weights).
 */
export function IndelSpectrum({ spectrum, showPredicted }: IndelSpectrumProps) {
  const { w, max, ticks } = useMemo(() => {
    const max = Math.max(
      0.05,
      ...spectrum.flatMap((b) => [b.observed, b.predicted ?? 0]),
    )
    const niceMax = Math.ceil(max * 10) / 10
    return {
      w: PAD_L + spectrum.length * GROUP_W + 12,
      max: niceMax,
      ticks: [0, 0.25, 0.5, 0.75, 1].map((f) => f * niceMax),
    }
  }, [spectrum])

  const plotH = H - PAD_T - PAD_B
  const y = (v: number) => PAD_T + plotH * (1 - v / max)
  const barW = showPredicted ? 11 : 16

  return (
    <div className="indel-chart">
      <svg
        viewBox={`0 0 ${w} ${H}`}
        role="img"
        aria-label="Indel frequency spectrum, observed versus AI-predicted"
        preserveAspectRatio="xMinYMid meet"
      >
        {ticks.map((t) => (
          <g key={t}>
            <line
              className="ic-grid"
              x1={PAD_L}
              x2={w - 6}
              y1={y(t)}
              y2={y(t)}
            />
            <text className="ic-ytick" x={PAD_L - 6} y={y(t) + 3}>
              {Math.round(t * 100)}%
            </text>
          </g>
        ))}

        {spectrum.map((b, i) => {
          const gx = PAD_L + i * GROUP_W
          const isWt = b.size === 0
          const cx = gx + GROUP_W / 2
          return (
            <g key={b.size}>
              <rect
                className={`ic-bar observed${isWt ? ' wt' : ''}`}
                x={showPredicted ? cx - barW - 1 : cx - barW / 2}
                y={y(b.observed)}
                width={barW}
                height={Math.max(0, PAD_T + plotH - y(b.observed))}
              >
                <title>{`indel ${b.size > 0 ? '+' : ''}${b.size}: observed ${(b.observed * 100).toFixed(1)}%`}</title>
              </rect>
              {showPredicted && b.predicted != null && (
                <rect
                  className="ic-bar predicted"
                  x={cx + 1}
                  y={y(b.predicted)}
                  width={barW}
                  height={Math.max(0, PAD_T + plotH - y(b.predicted))}
                >
                  <title>{`indel ${b.size > 0 ? '+' : ''}${b.size}: predicted ${(b.predicted * 100).toFixed(1)}%`}</title>
                </rect>
              )}
              <text className="ic-xtick" x={cx} y={H - PAD_B + 14}>
                {b.size > 0 ? `+${b.size}` : b.size}
              </text>
            </g>
          )
        })}

        <line
          className="ic-axis"
          x1={PAD_L}
          x2={w - 6}
          y1={PAD_T + plotH}
          y2={PAD_T + plotH}
        />
      </svg>

      <div className="ic-legend">
        <span>
          <i className="sw observed" /> Observed (TIDE)
        </span>
        {showPredicted && (
          <span>
            <i className="sw predicted" /> AI-predicted
          </span>
        )}
        <span className="ic-note">0 = unmodified · − deletion · + insertion</span>
      </div>
    </div>
  )
}
