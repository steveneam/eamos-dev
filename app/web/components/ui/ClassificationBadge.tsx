import { cn } from '@/lib/utils'
import { resolveClassificationConfig } from '@/lib/classification'

type Classification =
  | 'Pathogenic'
  | 'Likely pathogenic'
  | 'VUS'
  | 'Likely benign'
  | 'Benign'
  | string

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
  const cfg = resolveClassificationConfig(classification)
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
