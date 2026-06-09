import type { CSSProperties, ReactNode } from 'react'

// The one external "go to the source" link for the report — the teal-deep,
// underline-offset, trailing-↗ link that points at the authoritative record
// (gnomAD, ClinGen, ClinVar, dbNSFP, …). Before this it was hand-rolled
// near-identically across §3/§4 and the clinical blocks; the report's most
// trust-bearing element now resolves to one signature. The trailing ↗ is
// appended automatically; `fontSize` + `style` cover the per-site layout
// (a marginLeft/auto push) while the link treatment stays fixed.
//
// Deliberately NOT used for the bolder no-underline PubMed action, the
// icon+toggle PubMed buttons, MaveDB's dotted "search" link, or the disease-ID /
// hero entity chips — those are different affordances and are left as-is.

export function SourceLink({
  href,
  children,
  fontSize = 11.5,
  style,
}: {
  href: string
  children: ReactNode
  fontSize?: number
  style?: CSSProperties
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        fontSize,
        color: 'var(--teal-deep)',
        textDecoration: 'underline',
        textUnderlineOffset: 3,
        ...style,
      }}
    >
      {children} ↗
    </a>
  )
}
