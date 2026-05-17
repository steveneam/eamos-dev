import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  consequenceAt,
  posDisplay,
  type FlatBase,
  type GeneWindowData,
} from '@/lib/workbench/gene-window'
import type { Edit } from '@/lib/workbench/edit-state'
import type { Base } from '@/lib/workbench/codon-table'

interface EditPopoverV2Props {
  data: GeneWindowData
  flat: FlatBase[]
  idx: number
  current: Edit | undefined
  anchorRect: DOMRect
  onSub: (base: Base) => void
  onDel: () => void
  onIns: (seq: string) => void
  onReset: () => void
  onClose: () => void
}

const SANITISE = /[^ATCG]/g
const VIEWPORT_PAD = 8

function clampPopover(anchorRect: DOMRect, pop: HTMLDivElement | null) {
  const width = pop?.offsetWidth ?? 220
  const height = pop?.offsetHeight ?? 0
  const maxLeft = Math.max(VIEWPORT_PAD, window.innerWidth - width - VIEWPORT_PAD)
  const left = Math.min(Math.max(VIEWPORT_PAD, anchorRect.left - 80), maxLeft)
  const below = anchorRect.bottom + 6
  const above = anchorRect.top - height - 6
  const maxTop = Math.max(VIEWPORT_PAD, window.innerHeight - height - VIEWPORT_PAD)
  const top = below + height + VIEWPORT_PAD > window.innerHeight ? above : below

  return {
    top: Math.min(Math.max(VIEWPORT_PAD, top), maxTop),
    left,
  }
}

/** Base editor: substitute / delete / insert with a live consequence
 *  preview. Port of `openEdit()`. */
export function EditPopoverV2({
  data,
  flat,
  idx,
  current,
  anchorRect,
  onSub,
  onDel,
  onIns,
  onReset,
  onClose,
}: EditPopoverV2Props) {
  const popRef = useRef<HTMLDivElement>(null)
  const base = flat[idx]
  const refBase = base?.base.toUpperCase() ?? ''
  const [ins, setIns] = useState(current?.kind === 'ins' ? current.alt : '')
  const [hoverPreview, setHoverPreview] = useState<{
    kind: string
    label: string
    detail: string
  } | null>(null)
  const [position, setPosition] = useState(() => clampPopover(anchorRect, null))

  function describe(kind: 'sub' | 'del' | 'ins' | null, alt?: string) {
    if (kind === 'sub' && isBase(alt) && alt !== refBase) return consequenceAt(flat, idx, alt)
    if (kind === 'del') return consequenceAt(flat, idx, '-')
    if (kind === 'ins' && alt)
      return {
        kind: 'frameshift',
        label: `${alt.length}-bp insertion`,
        detail:
          alt.length % 3 === 0
            ? `In-frame insertion of ${alt} (${alt.length / 3} codon${alt.length === 3 ? '' : 's'}).`
            : `${alt} inserted after ${posDisplay(data, base)} shifts the reading frame.`,
      }
    return null
  }

  const currentPreview = describe(
    current?.kind ?? null,
    current?.kind === 'sub' || current?.kind === 'ins' ? current.alt : undefined,
  )
  const preview = hoverPreview ?? currentPreview

  useLayoutEffect(() => {
    const update = () => setPosition(clampPopover(anchorRect, popRef.current))
    update()
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
    }
  }, [anchorRect])

  // Outside-click / Escape close.
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      const t = e.target as HTMLElement
      if (popRef.current && !popRef.current.contains(t) && !t.closest('.sv-base')) onClose()
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    const id = window.setTimeout(() => document.addEventListener('mousedown', onDown), 50)
    document.addEventListener('keydown', onKey)
    return () => {
      window.clearTimeout(id)
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  if (!base) return null

  const subActive = (b: string) =>
    current?.kind === 'sub' ? current.alt === b : !current && refBase === b

  return createPortal(
    <div
      ref={popRef}
      className="sv-edit-pop"
      style={{ position: 'fixed', top: position.top, left: position.left }}
      role="dialog"
      aria-label={`Edit ${posDisplay(data, base)}`}
    >
      <div className="sv-pop-head">
        <span className="pos">{posDisplay(data, base)}</span>
        <span className="ref">ref {refBase}</span>
      </div>

      <div className="sv-pop-grid">
        {(['A', 'T', 'C', 'G'] as const).map((b) => (
          <button
            key={b}
            type="button"
            className={subActive(b) ? 'active' : undefined}
            onMouseEnter={() => setHoverPreview(describe('sub', b))}
            onMouseLeave={() => setHoverPreview(null)}
            onClick={() => onSub(b)}
          >
            {b}
          </button>
        ))}
        <button
          type="button"
          className={`del${current?.kind === 'del' ? ' active' : ''}`}
          onMouseEnter={() => setHoverPreview(describe('del'))}
          onMouseLeave={() => setHoverPreview(null)}
          onClick={onDel}
        >
          del
        </button>
      </div>

      <div className="sv-pop-ins">
        <input
          type="text"
          className="sv-pop-ins-input"
          placeholder="Insert sequence (e.g. ATG)"
          spellCheck={false}
          maxLength={60}
          value={ins}
          onChange={(e) => {
            const v = e.target.value.toUpperCase().replace(SANITISE, '')
            setIns(v)
            setHoverPreview(describe('ins', v))
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && ins) {
              e.preventDefault()
              onIns(ins)
            }
          }}
        />
        <button
          type="button"
          className="sv-pop-ins-btn"
          onClick={() => ins && onIns(ins)}
        >
          Insert {current?.kind === 'ins' ? 'replace' : 'after'}
        </button>
      </div>

      <div className="sv-pop-conseq">
        {preview ? (
          <>
            <span className={`cs ${preview.kind}`}>{preview.label}</span>{' '}
            <span className="dt">{preview.detail}</span>
          </>
        ) : (
          <span className="dim">Same as reference</span>
        )}
      </div>

      {current && (
        <div className="sv-pop-actions">
          <button type="button" className="ghost" onClick={onReset}>
            Reset to reference
          </button>
        </div>
      )}
    </div>,
    document.body,
  )
}

function isBase(value: string | undefined): value is Base {
  return value === 'A' || value === 'T' || value === 'C' || value === 'G'
}
