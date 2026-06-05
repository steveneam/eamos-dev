'use client'

import { useState } from 'react'
import type { ClassificationTier } from '@/lib/backend'
import { tierDotClass } from './tier'
import { IconChevron } from '@/components/icons/Icon'

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
  /** Opens the variant. The identity is a button so it's keyboard-reachable. */
  onOpen?: () => void
  /** Tooltip/description for the open action — surface-specific (default "Open report"). */
  openLabel?: string
}

export function VariantCardRow({ gene, hgvs, classification, hgvsFull, onOpen, openLabel }: VariantCardRowProps) {
  const [open, setOpen] = useState(false)
  const hasFull = Boolean(hgvsFull && hgvsFull !== hgvs)

  return (
    <div className="lib-row" data-open={open ? 'true' : 'false'}>
      <button type="button" className="lib-row-id" onClick={onOpen} title={onOpen ? (openLabel ?? 'Open report') : undefined}>
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
          <IconChevron size={11} />
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
