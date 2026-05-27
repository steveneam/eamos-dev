/** StackedCountBar — proportional horizontal bar with frozen-ramp segments.
 *
 * Each segment background uses the saturated `--cls-*-dot` token so white
 * tabular numerals remain legible at bar scale. Segments narrower than 32px
 * drop their inline text; consumers should pair with a tooltip or aria-label
 * for those cases.
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
                    color: '#fff',
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
