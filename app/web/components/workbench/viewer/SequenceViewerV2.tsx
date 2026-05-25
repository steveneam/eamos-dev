'use client'
import { forwardRef, useImperativeHandle, useMemo } from 'react'
import { buildFlatWindow } from '@/lib/workbench/gene-window'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import type { AlleleMode } from '@/lib/backend'
import type { SelectionSummary, StrandMode, TrackState } from './viewer-types'

/** Pass-1 skeleton: renders a flat sequence strip from `GeneWindowData`.
 *
 *  DEFERRED (pass 2+):
 *  - Full edit / undo-redo state (`edit-state.ts` + `editReducer`)
 *  - GeneMinimap (gene-wide exon density overview)
 *  - HistoryTimeline (edit history panel)
 *  - ProteinView (domain lollipop view)
 *  - CodonDetail (per-codon popup)
 *  - EditPopoverV2 (right-click substitute/delete/insert)
 *  - ViewerToolbar (copy / jump / export actions)
 *  - Click/drag selection → SelectionSummary callbacks
 *  - Keyboard shortcuts (A/T/C/G to substitute, ⌫ to delete)
 */

export interface ScratchEntry {
  idx: number
  cdsPos: number
  ref: string
  alt: string
  conseq: { kind: string; label: string; detail: string }
}

export interface SequenceViewerHandle {
  jumpToExon: (n: number) => void
  jumpToCdsPos: (p: number) => void
  resetEdits: () => void
  delSelection: () => void
  replaceSelection: (seq: string) => void
  clearSelection: () => void
}

interface SequenceViewerV2Props {
  data: GeneWindowData
  trackOn: TrackState
  strandMode: StrandMode
  baseW: number
  navCollapsed: boolean
  alleleMode: AlleleMode
  onScratchChange?: (entries: ScratchEntry[]) => void
  onSelectionChange?: (summary: SelectionSummary | null) => void
  onActiveExonChange?: (exon: number) => void
}

// Base colour tokens matching globals.css --base-* variables.
const BASE_COLORS: Record<string, string> = {
  A: 'var(--base-A)',
  T: 'var(--base-T)',
  C: 'var(--base-C)',
  G: 'var(--base-G)',
}

export const SequenceViewerV2 = forwardRef<SequenceViewerHandle, SequenceViewerV2Props>(
  function SequenceViewerV2({ data, baseW, navCollapsed: _navCollapsed, alleleMode: _alleleMode }, ref) {
    useImperativeHandle(ref, () => ({
      jumpToExon: (_n: number) => { /* pass-2 */ },
      jumpToCdsPos: (_p: number) => { /* pass-2 */ },
      resetEdits: () => { /* pass-2 */ },
      delSelection: () => { /* pass-2 */ },
      replaceSelection: (_seq: string) => { /* pass-2 */ },
      clearSelection: () => { /* pass-2 */ },
    }))

    const flat = useMemo(() => buildFlatWindow(data), [data])

    return (
      <div
        className="sv-skeleton"
        style={{
          padding: '16px 20px',
          overflowX: 'auto',
        }}
        role="region"
        aria-label="Sequence viewer"
      >
        <div
          style={{
            display: 'inline-flex',
            flexWrap: 'wrap',
            gap: 1,
            fontFamily: 'var(--mono)',
            fontSize: Math.max(8, baseW - 2),
            lineHeight: 1,
          }}
        >
          {flat.map((b) => {
            const isExon = b.kind === 'exon'
            const isGap = b.kind === 'intron-gap'
            const upperBase = b.base.toUpperCase()
            const color = isExon ? (BASE_COLORS[upperBase] ?? 'var(--ink-3)') : 'var(--ink-5)'

            return (
              <span
                key={b.flatPos}
                title={
                  isExon
                    ? `c.${b.cdsPos} · ${upperBase} · exon ${b.exonNum}`
                    : isGap
                      ? `${b.intronOmitted} bp omitted`
                      : `intron ${b.intronNum}`
                }
                style={{
                  display: 'inline-block',
                  width: baseW,
                  textAlign: 'center',
                  color,
                  fontWeight: isExon ? 600 : 400,
                  background: isGap ? 'var(--bg-soft)' : undefined,
                  borderRadius: isGap ? 2 : undefined,
                  padding: isGap ? '0 2px' : undefined,
                  cursor: 'default',
                }}
              >
                {b.base}
              </span>
            )
          })}
        </div>

        <p
          style={{
            marginTop: 12,
            fontSize: 11,
            color: 'var(--ink-4)',
            fontFamily: 'var(--mono)',
          }}
        >
          {data.gene} · {data.transcript} · {flat.length} displayed bases
          (exon 3 tail → intron 3 → exon 4 → intron 4 → exon 5 head)
          · edit/history/protein-view wiring deferred to pass 2
        </p>
      </div>
    )
  }
)
