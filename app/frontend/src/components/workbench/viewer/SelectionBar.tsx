import { useState } from 'react'
import { posDisplay, type FlatBase, type GeneWindowData } from '@/lib/workbench/gene-window'

interface SelectionBarProps {
  data: GeneWindowData
  flat: FlatBase[]
  selection: { start: number; end: number } | null
  hasEdit: (idx: number) => boolean
  onDelRange: (lo: number, hi: number) => void
  onReplace: (lo: number, hi: number, seq: string) => void
  onClear: () => void
}

function spanSummary(flat: FlatBase[], lo: number, hi: number): string {
  const slice = flat.slice(lo, hi + 1)
  const exonic = slice.filter((b) => b.kind === 'exon').length
  const intronic = slice.filter((b) => b.kind === 'intron').length
  if (exonic && intronic) return `${exonic} exonic + ${intronic} intronic bp`
  if (exonic)
    return `${exonic} exonic bp · ${Math.floor(exonic / 3)} codon${
      Math.floor(exonic / 3) === 1 ? '' : 's'
    }${exonic % 3 ? ` + ${exonic % 3} bp` : ''}`
  if (intronic) return `${intronic} intronic bp`
  return ''
}

/** Selection summary + range actions. Port of `buildSelectionContent()`. */
export function SelectionBar({
  data,
  flat,
  selection,
  hasEdit,
  onDelRange,
  onReplace,
  onClear,
}: SelectionBarProps) {
  const [replace, setReplace] = useState('')

  if (!selection) {
    return (
      <div className="sv-selbar">
        <div className="sv-selbar-inner">
          <div className="sv-selbar-empty">
            <b>Tip.</b> Click a base to edit it (A/T/C/G · del · insert). Drag across
            bases for a range; <b>shift-click</b> extends. Press a letter key with a base
            selected to substitute; <b>⌫</b> deletes.
          </div>
        </div>
      </div>
    )
  }

  const lo = Math.min(selection.start, selection.end)
  const hi = Math.max(selection.start, selection.end)
  const len = hi - lo + 1
  const loB = flat[lo]
  const hiB = flat[hi]

  return (
    <div className="sv-selbar">
      <div className="sv-selbar-inner">
        <div className="sv-selbar-left">
          {len === 1 ? (
            <>
              <span className="sv-selbar-label">Selection</span>
              <span className="sv-selbar-pos">{posDisplay(data, loB)}</span>
              <span className="sv-selbar-base">
                Reference base: <b>{loB.kind === 'intron-gap' ? '—' : loB.base.toUpperCase()}</b>
                {hasEdit(lo) ? ' — edited' : ''}
              </span>
              <span className="sv-selbar-base dim">Click the base again to open editor.</span>
            </>
          ) : (
            <>
              <span className="sv-selbar-label">Range · {len} bp</span>
              <span className="sv-selbar-pos">
                {posDisplay(data, loB)} → {posDisplay(data, hiB)}
              </span>
              <span className="sv-selbar-base">{spanSummary(flat, lo, hi)}</span>
            </>
          )}
        </div>

        <div className="sv-selbar-actions">
          {len > 1 ? (
            <>
              <button
                type="button"
                className="sv-selbar-btn del"
                onClick={() => onDelRange(lo, hi)}
              >
                Delete {len} bases
              </button>
              <input
                className="sv-selbar-input wide"
                placeholder={`Paste replacement (max ${len * 2} bp)`}
                aria-label="Replacement sequence"
                spellCheck={false}
                value={replace}
                onChange={(e) => setReplace(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    const v = replace.toUpperCase().replace(/[^ATCG]/g, '')
                    if (v) onReplace(lo, hi, v)
                  }
                }}
              />
              <button
                type="button"
                className="sv-selbar-btn ins"
                onClick={() => {
                  const v = replace.toUpperCase().replace(/[^ATCG]/g, '')
                  if (v) onReplace(lo, hi, v)
                }}
              >
                Replace →
              </button>
              <button type="button" className="sv-selbar-btn ghost" onClick={onClear}>
                Clear
              </button>
            </>
          ) : (
            <button type="button" className="sv-selbar-btn ghost" onClick={onClear}>
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
