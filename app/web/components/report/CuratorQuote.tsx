import { type ReactNode } from 'react'

/**
 * Shared "curator quote" block (report v3, design §6) — the curator's free-text
 * assessment, set off with a teal left-rule + faint wash so §1 reads as one
 * consistent grammar whether the source is ClinGen (VCEP) or ClinVar. The
 * left-rule + indent carry the "quote" semantics (DESIGN bans decorative
 * glyphs). `mock` marks a not-yet-wired interpretation.
 */
export function CuratorQuote({ children, mock = false }: { children?: ReactNode; mock?: boolean }) {
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
      {mock && (
        <span
          className="eamos-mock"
          title="The per-submitter interpretation free-text is not yet wired to live data; the classification, review status and submitter mix above are live."
        >
          Submitter interpretation — needs live data
        </span>
      )}
    </blockquote>
  )
}
