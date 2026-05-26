/**
 * Landing typographic primitives.
 *
 * One h2 spec + one h3 spec for the whole landing surface — Spectral 400 on
 * the warm-paper ground, fluid clamps for h2, fixed 18px for tile/card h3s.
 * The audit before this primitive flagged five different h2 styles and four
 * different h3 styles on a single page; this is the canonical shape.
 *
 * Do not pass `fontWeight` / `fontFamily` overrides through `style`. The point
 * is that every section's heading reads as the same voice; if a section needs
 * "more rank," express it via layout, color, or the in-card content, not type.
 */
import type { CSSProperties, ReactNode } from 'react'

interface HeadingProps {
  children: ReactNode
  className?: string
  style?: CSSProperties
  id?: string
}

export function LandingH2({ children, className, style, id }: HeadingProps) {
  return (
    <h2
      id={id}
      className={className}
      style={{
        fontFamily: 'var(--display)',
        fontWeight: 400,
        fontSize: 'clamp(30px, 3.6vw, 42px)',
        lineHeight: 1.08,
        letterSpacing: '-0.02em',
        color: 'var(--hero-ink)',
        margin: 0,
        textWrap: 'balance',
        ...style,
      }}
    >
      {children}
    </h2>
  )
}

export function LandingH3({ children, className, style, id }: HeadingProps) {
  return (
    <h3
      id={id}
      className={className}
      style={{
        fontFamily: 'var(--display)',
        fontWeight: 400,
        fontSize: 18,
        lineHeight: 1.22,
        letterSpacing: '-0.015em',
        color: 'var(--hero-ink)',
        margin: 0,
        ...style,
      }}
    >
      {children}
    </h3>
  )
}
