/** StackedCountBar — proportional horizontal bar with frozen-ramp segments.
 *
 * Each segment background uses the saturated `--cls-*-dot` token; the count
 * numeral takes a per-tier ink (`TEXT_ON_DOT`) chosen for contrast — white on
 * the dark Pathogenic/LP/Benign dots, the dark `--cls-*-text` token on the
 * light VUS/Likely-benign dots (white fails contrast on those two). Segments
 * narrower than 32px drop their inline text; consumers should pair with a
 * tooltip or aria-label for those cases.
 */

export type RampVerdict =
  | 'Pathogenic'
  | 'Likely pathogenic'
  | 'VUS'
  | 'Likely benign'
  | 'Benign'

export interface StackedCountSegment {
  verdict: RampVerdict
  count: number
  /** Optional display label; defaults to the verdict string. */
  label?: string
}

export interface StackedCountBarProps {
  segments: StackedCountSegment[]
  /** Bar height in px. Default 22. */
  height?: number
  /** Render inline count (and label) text inside each segment. Default true. */
  showLabels?: boolean
  className?: string
  /** Required: passed to the container as aria-label. */
  ariaLabel: string
}

const DOT_TOKEN: Record<RampVerdict, string> = {
  'Pathogenic':       'var(--cls-path-dot)',
  'Likely pathogenic': 'var(--cls-lpath-dot)',
  'VUS':              'var(--cls-vus-dot)',
  'Likely benign':    'var(--cls-lben-dot)',
  'Benign':           'var(--cls-ben-dot)',
}

// Numeral ink per tier, chosen for legibility on the dot above. White reads on
// the dark path/LP/benign dots; the light VUS/LB dots need a dark ink instead.
const TEXT_ON_DOT: Record<RampVerdict, string> = {
  'Pathogenic':       '#fff',
  'Likely pathogenic': '#fff',
  'VUS':              'var(--cls-vus-text)',
  'Likely benign':    'var(--cls-lben-text)',
  'Benign':           '#fff',
}

const NARROW_THRESHOLD_PX = 32

export function StackedCountBar({
  segments,
  height = 22,
  showLabels = true,
  className,
  ariaLabel,
}: StackedCountBarProps) {
  const total = segments.reduce((sum, s) => sum + s.count, 0)

  // Empty / zero-total: single grey placeholder bar.
  if (total === 0) {
    return (
      <div
        role="img"
        aria-label={ariaLabel}
        className={className}
        style={{
          width: '100%',
          height,
          borderRadius: 4,
          overflow: 'hidden',
          background: 'var(--cls-na-dot)',
          opacity: 0.3,
        }}
      />
    )
  }

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      className={className}
      style={{
        display: 'flex',
        width: '100%',
        height,
        borderRadius: 4,
        overflow: 'hidden',
      }}
    >
      {segments
        .filter((s) => s.count > 0)
        .map((seg, i) => {
          const pct = (seg.count / total) * 100
          const label = seg.label ?? seg.verdict
          // Estimate pixel width relative to a 300px baseline; actual width is
          // determined by the browser, so we apply a conservative guard.
          const estimatedPx = (pct / 100) * 300
          const tooNarrow = estimatedPx < NARROW_THRESHOLD_PX

          return (
            <div
              key={`${seg.verdict}-${i}`}
              aria-label={`${label}: ${seg.count}`}
              title={`${label}: ${seg.count}`}
              style={{
                width: `${pct}%`,
                background: DOT_TOKEN[seg.verdict],
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                overflow: 'hidden',
              }}
            >
              {showLabels && !tooNarrow && (
                <span
                  style={{
                    color: TEXT_ON_DOT[seg.verdict],
                    fontSize: 11,
                    fontWeight: 600,
                    fontVariantNumeric: 'tabular-nums',
                    lineHeight: 1,
                    whiteSpace: 'nowrap',
                    userSelect: 'none',
                  }}
                >
                  {seg.count}
                </span>
              )}
            </div>
          )
        })}
    </div>
  )
}
