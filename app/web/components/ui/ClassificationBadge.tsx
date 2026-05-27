import { cn } from '@/lib/utils'

type Classification =
  | 'Pathogenic'
  | 'Likely pathogenic'
  | 'VUS'
  | 'Likely benign'
  | 'Benign'
  | string

interface Config {
  bg: string
  text: string
  border: string
  dot: string
}

// Classification ramp tokens (globals.css). Steven's mandate (2026-05-26):
// P=red, LP=red-orange, VUS=true yellow, LB=lime, B=green. Grey (--cls-na-*) is
// reserved for unresolved / conflicting / no-data / NA — never a tier color, and
// it is the fallback for anything we cannot map.
const PATHOGENIC: Config = { bg: 'var(--cls-path-bg)', text: 'var(--cls-path-text)', border: 'var(--cls-path-bdr)', dot: 'var(--cls-path-dot)' }
const LIKELY_PATHOGENIC: Config = { bg: 'var(--cls-lpath-bg)', text: 'var(--cls-lpath-text)', border: 'var(--cls-lpath-bdr)', dot: 'var(--cls-lpath-dot)' }
const VUS: Config = { bg: 'var(--cls-vus-bg)', text: 'var(--cls-vus-text)', border: 'var(--cls-vus-bdr)', dot: 'var(--cls-vus-dot)' }
const LIKELY_BENIGN: Config = { bg: 'var(--cls-lben-bg)', text: 'var(--cls-lben-text)', border: 'var(--cls-lben-bdr)', dot: 'var(--cls-lben-dot)' }
const BENIGN: Config = { bg: 'var(--cls-ben-bg)', text: 'var(--cls-ben-text)', border: 'var(--cls-ben-bdr)', dot: 'var(--cls-ben-dot)' }
const NA: Config = { bg: 'var(--cls-na-bg)', text: 'var(--cls-na-text)', border: 'var(--cls-na-bdr)', dot: 'var(--cls-na-dot)' }

const CONFIGS: Record<string, Config> = {
  'pathogenic': PATHOGENIC,
  'likely pathogenic': LIKELY_PATHOGENIC,
  'vus': VUS,
  'uncertain significance': VUS,
  'uncertain_significance': VUS,
  'likely benign': LIKELY_BENIGN,
  'benign': BENIGN,
  // Explicit non-tiers → grey, not a verdict color.
  'conflicting interpretations of pathogenicity': NA,
  'conflicting': NA,
  'not provided': NA,
  'no classification': NA,
  'unknown': NA,
}

function resolveConfig(classification: string): Config {
  const key = classification.trim().toLowerCase()
  // Unknown / unmapped classifications fall back to grey-NA, never to a tier.
  return CONFIGS[key] ?? NA
}

interface ClassificationBadgeProps {
  classification: Classification
  className?: string
  reviewStars?: number | null
}

function clampStars(n: number | null | undefined): number | null {
  if (n == null || !isFinite(n)) return null
  const clamped = Math.max(0, Math.min(4, Math.round(n)))
  return clamped
}

// Inline SVG star: filled or outline, 11×11px, inherits currentColor.
function Star({ filled }: { filled: boolean }) {
  return (
    <svg
      width="11"
      height="11"
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={{ display: 'inline', verticalAlign: 'middle', flexShrink: 0 }}
    >
      <path
        d="M12 2l2.9 6.3 6.9 1-5 4.9 1.2 6.8L12 18l-6 3.1 1.2-6.8-5-4.9 6.9-1z"
        fill={filled ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth={filled ? 0 : 1.5}
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function ClassificationBadge({ classification, className, reviewStars }: ClassificationBadgeProps) {
  const cfg = resolveConfig(classification)
  const stars = clampStars(reviewStars)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] border',
        className,
      )}
      style={{
        background: cfg.bg,
        color: cfg.text,
        borderColor: cfg.border,
        borderWidth: '0.5px',
      }}
    >
      <span
        className="shrink-0 rounded-full"
        style={{ width: 6, height: 6, background: cfg.dot }}
      />
      {classification}
      {stars !== null && (
        <span
          className="inline-flex items-center gap-[1px] ml-1"
          style={{ fontVariantNumeric: 'tabular-nums', fontSize: 10, lineHeight: 1 }}
        >
          {Array.from({ length: 4 }, (_, i) => (
            <Star key={i} filled={i < stars} />
          ))}
          <span style={{ marginLeft: 2 }}>{stars}</span>
        </span>
      )}
    </span>
  )
}
