import type { CSSProperties, ReactNode } from 'react'

/**
 * Canonical landing micro-label (eyebrow / kicker).
 *
 * Unifies the type spec — 10.5px / 600 / uppercase / 0.12em tracking — across the
 * four surfaces that were each hand-rolling a near-identical label (SourceStrip
 * "Powered by", SiteFooter column titles, HowItWorks step kickers, MetricBelt
 * card titles, previously drifting 10–10.5px / 600–700 / 0.08–0.12em).
 *
 * Colour is intentionally NOT baked in — it depends on the ground (cream hero vs
 * product card vs teal accent), so each call site passes it via `style`.
 */
export function LandingEyebrow({
  children,
  className = '',
  style,
}: {
  children: ReactNode
  className?: string
  style?: CSSProperties
}) {
  return (
    <span
      className={`text-[10.5px] font-semibold uppercase tracking-[0.12em] ${className}`.trim()}
      style={style}
    >
      {children}
    </span>
  )
}
