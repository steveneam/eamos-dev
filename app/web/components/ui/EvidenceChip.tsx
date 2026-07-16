import type { CSSProperties, ReactNode } from 'react'
import { resolveClassificationConfig } from '@/lib/classification'

// The one verdict / strength / support chip grammar for the report. Before this,
// the same idea — a tinted, 0.5px-bordered pill stating an ACMG verdict, a
// strength band, or a support badge — was hand-rolled five different ways
// (CallCards, MAVE PS3/BS3, LoF PVS1, Eamos-ACMG, plus the canonical
// ClassificationBadge). This primitive captures the SHARED grammar (border
// treatment, tone application, optional leading dot, pill/rect shape) so every
// chip is built one way and a change to "what a coloured pill means" lands once.
//
// The size tiers are DELIBERATE, not arbitrary: the report ranks chips by
// prominence — the Eamos auto-verdict (lg) reads louder than a §3 support badge
// (sm) or the secondary MAVE band badge (xs). The tokens below preserve the
// exact px each callsite already shipped; this convergence is geometry-only, no
// visual redraw. Colour always resolves to the design-system tokens — either via
// a classification string (→ --cls-* through lib/classification) or an explicit
// tone (strength bands / curator tones that aren't a classification tier).
//
// The canonical ClassificationBadge (hero) keeps its own file (it carries the
// review-star logic); this primitive follows its geometry rather than replacing
// it. Source-access tags remain a separate, non-verdict vocabulary.

export interface EvidenceTone {
  bg: string
  border: string
  text: string
  /** Leading-dot fill; falls back to `text` when omitted. */
  dot?: string
}

// font / vertical-pad / horizontal-pad / dot-diameter, matched to the shipped
// chip hierarchy (xs MAVE band · sm §3 support badge · md LoF strength · lg
// Eamos verdict). Changing a value here re-tunes that whole tier at once.
const SIZES = {
  xs: { font: 10, padY: 1, padX: 7, dot: 5 },
  sm: { font: 10.5, padY: 4, padX: 7, dot: 6 },
  md: { font: 12, padY: 1, padX: 8, dot: 6 },
  lg: { font: 13, padY: 4, padX: 11, dot: 8 },
} as const

interface EvidenceChipProps {
  children: ReactNode
  /** Resolve tone from a classification string (P/LP/VUS/LB/B → --cls-*). */
  classification?: string
  /** …or pass an explicit tone (strength band / curator / neutral count). */
  tone?: EvidenceTone
  size?: keyof typeof SIZES
  /** Leading status dot (tone.dot ?? tone.text), sized to the tier. */
  dot?: boolean
  /** Uppercase + letter-tracked — the canonical ACMG-badge treatment. */
  uppercase?: boolean
  /** Pill (full radius) vs rect (--r-sm) for multi-token, wrapping badges. */
  shape?: 'pill' | 'rect'
  title?: string
  className?: string
  style?: CSSProperties
}

export function EvidenceChip({
  children,
  classification,
  tone,
  size = 'md',
  dot = false,
  uppercase = false,
  shape = 'pill',
  title,
  className,
  style,
}: EvidenceChipProps) {
  const t: EvidenceTone =
    tone ??
    (() => {
      const cfg = resolveClassificationConfig(classification ?? '')
      return { bg: cfg.bg, border: cfg.border, text: cfg.text, dot: cfg.dot }
    })()
  const s = SIZES[size]

  return (
    <span
      className={className}
      title={title}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: dot ? 6 : 0,
        fontSize: s.font,
        fontWeight: 700,
        lineHeight: 1.15,
        letterSpacing: uppercase ? '0.04em' : undefined,
        textTransform: uppercase ? 'uppercase' : undefined,
        padding: `${s.padY}px ${s.padX}px`,
        borderRadius: shape === 'pill' ? 999 : 'var(--r-sm)',
        border: `0.5px solid ${t.border}`,
        background: t.bg,
        color: t.text,
        whiteSpace: shape === 'pill' ? 'nowrap' : undefined,
        overflowWrap: shape === 'rect' ? 'anywhere' : undefined,
        ...style,
      }}
    >
      {dot && (
        <span
          aria-hidden
          style={{ width: s.dot, height: s.dot, borderRadius: 999, flexShrink: 0, background: t.dot ?? t.text }}
        />
      )}
      {children}
    </span>
  )
}
