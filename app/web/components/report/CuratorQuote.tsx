import { type ReactNode } from 'react'

/**
 * Shared curator quote block for ClinGen/VCEP and ClinVar free-text
 * interpretations. The left rule and indent carry the quote semantics.
 */
export function CuratorQuote({ children }: { children?: ReactNode }) {
  return (
    <blockquote
      style={{
        margin: 0,
        borderLeft: '3px solid var(--teal-bdr)',
        background: 'var(--teal-tint)',
        borderRadius: '0 var(--r-sm) var(--r-sm) 0',
        padding: '8px 12px',
        fontFamily: 'var(--body)',
        fontSize: 13,
        lineHeight: 1.55,
        color: 'var(--ink-2)',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      {children}
    </blockquote>
  )
}
