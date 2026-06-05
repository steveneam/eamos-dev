'use client'

import { useState } from 'react'
import type { ClassificationTier } from '@/lib/backend'
import { tierDotClass } from './tier'

/**
 * The shared presentational row under BOTH saved-variant cards (§2) and
 * related-variant lanes (§4): class dot · gene · compact HGVS, with the full
 * transcript HGVS behind a caret/hover disclosure (locked decision §3). Carries
 * NO chrome (no checkbox/remove/pin/+) — wrappers add that — so the two card
 * families never drift. Design: docs/workspace-rail/phase-3-4-design.md §1.
 */
export interface VariantCardRowProps {
  gene: string | null
  /** Compact HGVS (e.g. `c.2276G>T`), already the display form. */
  hgvs: string | null
  classification?: ClassificationTier | null
  /** Full transcript-qualified HGVS (e.g. `NM_206933.4:c.2276G>T`); when present
   *  and distinct from `hgvs`, the caret/hover disclosure reveals it. */
  hgvsFull?: string | null
  /** Opens the variant's report. The identity is a button so it's keyboard-reachable. */
  onOpen?: () => void
}

function Caret() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" width="11" height="11">
      <polyline points="9 6 15 12 9 18" />
    </svg>
  )
}

export function VariantCardRow({ gene, hgvs, classification, hgvsFull, onOpen }: VariantCardRowProps) {
  const [open, setOpen] = useState(false)
  const hasFull = Boolean(hgvsFull && hgvsFull !== hgvs)

  return (
    <div className="lib-row" data-open={open ? 'true' : 'false'}>
      <button type="button" className="lib-row-id" onClick={onOpen} title={onOpen ? 'Open report' : undefined}>
        <span className={`lib-dot ${tierDotClass(classification)}`} aria-hidden />
        <span className="lib-gene">{gene ?? '—'}</span>
        {hgvs ? (
          <>
            <span className="lib-sep" aria-hidden>·</span>
            <span className="lib-hgvs">{hgvs}</span>
          </>
        ) : null}
      </button>
      {hasFull ? (
        <button
          type="button"
          className="lib-row-caret"
          aria-expanded={open}
          aria-label={open ? 'Hide full transcript HGVS' : 'Show full transcript HGVS'}
          onClick={() => setOpen((o) => !o)}
        >
          <Caret />
        </button>
      ) : null}
      {hasFull ? (
        <div className="lib-row-full">
          <code className="lib-hgvs-full">{hgvsFull}</code>
        </div>
      ) : null}
    </div>
  )
}
