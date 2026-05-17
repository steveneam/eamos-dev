import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react'
import {
  buildCodons,
  buildFlatWindow,
  consequenceAt,
  posDisplay,
  type GeneWindowData,
} from '@/lib/workbench/gene-window'
import {
  editReducer,
  initialEditState,
  type Edit,
  type EditMap,
} from '@/lib/workbench/edit-state'
import type { StrandMode, TrackState } from './viewer-types'
import { GeneMinimap } from './GeneMinimap'
import { ExonStrip } from './ExonStrip'
import { CodonDetail } from './CodonDetail'
import { SelectionBar } from './SelectionBar'
import { HistoryTimeline } from './HistoryTimeline'
import { ViewerToolbar } from './ViewerToolbar'
import { EditPopoverV2 } from './EditPopoverV2'

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
}

interface SequenceViewerV2Props {
  data: GeneWindowData
  trackOn: TrackState
  strandMode: StrandMode
  baseW: number
  /** Hide the minimap + exon strip (modification #2: collapsible nav). */
  navCollapsed: boolean
  onScratchChange: (entries: ScratchEntry[]) => void
  onEditCountChange?: (count: number) => void
  onActiveExonChange?: (n: number) => void
}

export const SequenceViewerV2 = forwardRef<SequenceViewerHandle, SequenceViewerV2Props>(
  function SequenceViewerV2(
    {
      data,
      trackOn,
      strandMode,
      baseW,
      navCollapsed,
      onScratchChange,
      onEditCountChange,
      onActiveExonChange,
    },
    ref,
  ) {
    const flat = useMemo(() => buildFlatWindow(data), [data])
    const codons = useMemo(() => buildCodons(flat), [flat])
    const rootRef = useRef<HTMLDivElement>(null)
    const focusSearchRef = useRef<() => void>(() => {})
    const isSelecting = useRef(false)
    const dragCleanupRef = useRef<(() => void) | null>(null)

    const [editState, dispatch] = useReducer(editReducer, initialEditState)
    const { edits, history, cursor } = editState
    const [selection, setSelection] = useState<{ start: number; end: number } | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [jumpError, setJumpError] = useState<string | null>(null)
    const [showHistory, setShowHistory] = useState(false)
    const [restrictionHover, setRestrictionHover] = useState<string | null>(null)
    const [popover, setPopover] = useState<{ idx: number; rect: DOMRect } | null>(null)

    const exonOf = useCallback(
      (cds: number) =>
        data.exons.find((e) => cds >= e.cdsStart && cds <= e.cdsEnd)?.num ??
        data.queriedVariant.cdsPos,
      [data],
    )
    const [activeExon, setActiveExon] = useState(() =>
      exonOf(data.queriedVariant.cdsPos),
    )

    // ── Edit operations (mirror sequence-viewer.js) ──
    const commit = useCallback(
      (label: string, mutate: (m: EditMap) => void) =>
        dispatch({ type: 'commit', label, mutate }),
      [],
    )
    const applySub = useCallback(
      (idx: number, base: string) => {
        const reff = flat[idx].base.toUpperCase()
        if (base === reff)
          commit(`Reset ${posDisplay(data, flat[idx])}`, (m) => m.delete(idx))
        else
          commit(`Substitute ${posDisplay(data, flat[idx])} ${reff}>${base}`, (m) =>
            m.set(idx, { kind: 'sub', alt: base }),
          )
      },
      [commit, data, flat],
    )
    const applyDel = useCallback(
      (lo: number, hi: number) => {
        const label =
          lo === hi
            ? `Delete ${posDisplay(data, flat[lo])}`
            : `Delete ${hi - lo + 1} bases ${posDisplay(data, flat[lo])} → ${posDisplay(
                data,
                flat[hi],
              )}`
        commit(label, (m) => {
          for (let i = lo; i <= hi; i++) {
            if (flat[i].kind === 'intron-gap') continue
            m.set(i, { kind: 'del', alt: '-' })
          }
        })
      },
      [commit, data, flat],
    )
    const applyIns = useCallback(
      (idx: number, seq: string) =>
        commit(`Insert ${seq} after ${posDisplay(data, flat[idx])}`, (m) =>
          m.set(idx, { kind: 'ins', alt: seq }),
        ),
      [commit, data, flat],
    )
    const applyReplace = useCallback(
      (lo: number, hi: number, seq: string) => {
        commit(`Replace ${hi - lo + 1} bases with ${seq}`, (m) => {
          for (let i = lo; i <= hi; i++) m.delete(i)
          const usable = Math.min(seq.length, hi - lo + 1)
          for (let k = 0; k < usable; k++) {
            const idx = lo + k
            if (flat[idx].kind === 'intron-gap') continue
            if (seq[k] !== flat[idx].base.toUpperCase())
              m.set(idx, { kind: 'sub', alt: seq[k] })
          }
          if (seq.length > usable) m.set(hi, { kind: 'ins', alt: seq.substr(usable) })
          else if (seq.length < hi - lo + 1)
            for (let k = seq.length; k < hi - lo + 1; k++) {
              const idx = lo + k
              if (flat[idx].kind !== 'intron-gap') m.set(idx, { kind: 'del', alt: '-' })
            }
        })
        setSelection(null)
      },
      [commit, flat],
    )
    const resetEdits = useCallback(() => {
      if (edits.size === 0) return
      commit('Reset all edits', (m) => m.clear())
    }, [commit, edits.size])

    // ── Scratchpad: exon substitutions, mirrored to the side panel ──
    useEffect(() => {
      const entries: ScratchEntry[] = []
      edits.forEach((e, k) => {
        const b = flat[k]
        if (b?.kind === 'exon' && e.kind === 'sub') {
          entries.push({
            idx: k,
            cdsPos: b.cdsPos,
            ref: b.base.toUpperCase(),
            alt: e.alt,
            conseq: consequenceAt(flat, k, e.alt as never),
          })
        }
      })
      entries.sort((a, b) => a.cdsPos - b.cdsPos)
      onScratchChange(entries)
      onEditCountChange?.(edits.size)
    }, [edits, flat, onScratchChange, onEditCountChange])

    // ── Jump / navigation ──
    const scrollToIdx = useCallback((i: number) => {
      requestAnimationFrame(() => {
        const cell = rootRef.current?.querySelector<HTMLElement>(
          `.sv-base[data-idx="${i}"]`,
        )
        cell?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
    }, [])
    const jumpToFlatIdx = useCallback(
      (i: number) => {
        if (i < 0) return
        setSelection({ start: i, end: i })
        const b = flat[i]
        if (b?.kind === 'exon') setActiveExon(b.exonNum)
        scrollToIdx(i)
      },
      [flat, scrollToIdx],
    )
    const jumpToCdsPos = useCallback(
      (p: number) => {
        const i = flat.findIndex((b) => b.kind === 'exon' && b.cdsPos === p)
        if (i >= 0) jumpToFlatIdx(i)
      },
      [flat, jumpToFlatIdx],
    )
    const jumpToExon = useCallback(
      (n: number) => {
        const i = flat.findIndex((b) => b.kind === 'exon' && b.exonNum === n)
        if (i >= 0) jumpToFlatIdx(i)
        else {
          setActiveExon(n)
          setJumpError(`Exon ${n} not in current window (window covers exons 3–5).`)
        }
      },
      [flat, jumpToFlatIdx],
    )
    useImperativeHandle(ref, () => ({ jumpToExon, jumpToCdsPos, resetEdits }), [
      jumpToExon,
      jumpToCdsPos,
      resetEdits,
    ])

    useEffect(() => {
      onActiveExonChange?.(activeExon)
    }, [activeExon, onActiveExonChange])

    useEffect(() => {
      if (!jumpError) return
      const id = window.setTimeout(() => setJumpError(null), 3000)
      return () => window.clearTimeout(id)
    }, [jumpError])

    const jumpToQuery = useCallback(
      (raw: string) => {
        const q = raw.trim()
        if (!q) return
        let m = /^c\.?\s*(\d+)/i.exec(q)
        if (m) return jumpToCdsPos(parseInt(m[1], 10))
        m = /^p\.?\s*([A-Za-z]{1,3})\s*(\d+)/i.exec(q)
        if (m) {
          const codon = codons.find((c) => c.codonNum === parseInt(m![2], 10))
          if (codon) return jumpToFlatIdx(codon.bases[0])
        }
        m = /exon\s*(\d+)/i.exec(q)
        if (m) return jumpToExon(parseInt(m[1], 10))
        if (/^[ATCG]{3,}$/i.test(q)) {
          const s = flat
            .map((b) => (b.kind === 'intron-gap' ? '_' : b.base.toUpperCase()))
            .join('')
          const idx = s.indexOf(q.toUpperCase())
          if (idx >= 0) return jumpToFlatIdx(idx)
          return setJumpError(`Sequence "${q.toUpperCase()}" not found in current window.`)
        }
        setJumpError(`Couldn't parse "${q}". Try c.260, p.Asp87, exon 4, or ATCG sequence.`)
      },
      [codons, flat, jumpToCdsPos, jumpToExon, jumpToFlatIdx],
    )

    const variantFlatPositions = useMemo(
      () =>
        data.clinvar
          .map((v) =>
            typeof v.cdsPos === 'number'
              ? flat.findIndex((b) => b.kind === 'exon' && b.cdsPos === v.cdsPos)
              : -1,
          )
          .filter((i) => i >= 0)
          .sort((a, b) => a - b),
      [data, flat],
    )
    const stepVariant = useCallback(
      (dir: 'prev' | 'next') => {
        if (variantFlatPositions.length === 0) return
        const cur = selection
          ? selection.end
          : flat.findIndex(
              (b) => b.kind === 'exon' && b.cdsPos === data.queriedVariant.cdsPos,
            )
        let next =
          dir === 'next'
            ? variantFlatPositions.find((p) => p > cur)
            : [...variantFlatPositions].reverse().find((p) => p < cur)
        if (next == null)
          next =
            dir === 'next'
              ? variantFlatPositions[0]
              : variantFlatPositions[variantFlatPositions.length - 1]
        jumpToFlatIdx(next)
      },
      [data, flat, jumpToFlatIdx, selection, variantFlatPositions],
    )
    const variantCount = variantFlatPositions.length

    // ── Selection drag ──
    const cleanupSelectionDrag = useCallback(() => {
      isSelecting.current = false
      dragCleanupRef.current?.()
      dragCleanupRef.current = null
    }, [])

    useEffect(() => cleanupSelectionDrag, [cleanupSelectionDrag])

    const onBaseMouseDown = useCallback(
      (idx: number, shift: boolean) => {
        cleanupSelectionDrag()
        setSelection((sel) =>
          shift && sel ? { start: sel.start, end: idx } : { start: idx, end: idx },
        )
        isSelecting.current = true
        const move = (e: MouseEvent) => {
          if (!isSelecting.current) return
          const t = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null
          const cell = t?.closest<HTMLElement>('.sv-base[data-idx]')
          if (cell) {
            const i = parseInt(cell.dataset.idx!, 10)
            setSelection((sel) => (sel && sel.end !== i ? { ...sel, end: i } : sel))
          }
        }
        const up = () => {
          cleanupSelectionDrag()
        }
        document.addEventListener('mousemove', move)
        document.addEventListener('mouseup', up)
        dragCleanupRef.current = () => {
          document.removeEventListener('mousemove', move)
          document.removeEventListener('mouseup', up)
        }
      },
      [cleanupSelectionDrag],
    )
    const onBaseClick = useCallback(
      (idx: number, rect: DOMRect, shift: boolean) => {
        if (shift && selection) {
          setSelection({ start: selection.start, end: idx })
          return
        }
        setSelection({ start: idx, end: idx })
        setPopover({ idx, rect })
      },
      [selection],
    )

    // ── Keyboard ──
    useEffect(() => {
      const onKey = (e: KeyboardEvent) => {
        const tag = (document.activeElement as HTMLElement | null)?.tagName
        const inField = tag === 'INPUT' || tag === 'TEXTAREA'
        if (e.metaKey || e.ctrlKey) {
          const k = e.key.toLowerCase()
          if (k === 'z' && !e.shiftKey) {
            e.preventDefault()
            dispatch({ type: 'undo' })
          } else if ((k === 'z' && e.shiftKey) || k === 'y') {
            e.preventDefault()
            dispatch({ type: 'redo' })
          } else if (k === 'f') {
            e.preventDefault()
            focusSearchRef.current()
          }
          return
        }
        if (inField) return
        if (selection && e.key === 'Backspace') {
          applyDel(
            Math.min(selection.start, selection.end),
            Math.max(selection.start, selection.end),
          )
          e.preventDefault()
        } else if (
          selection &&
          selection.start === selection.end &&
          /^[atcgATCG]$/.test(e.key)
        ) {
          applySub(selection.start, e.key.toUpperCase())
          e.preventDefault()
        } else if (e.key === 'Escape') {
          setSelection(null)
        } else if (e.key === 'ArrowLeft' && selection) {
          const n = Math.max(0, selection.end - 1)
          setSelection({ start: n, end: n })
        } else if (e.key === 'ArrowRight' && selection) {
          const n = Math.min(flat.length - 1, selection.end + 1)
          setSelection({ start: n, end: n })
        }
      }
      window.addEventListener('keydown', onKey)
      return () => window.removeEventListener('keydown', onKey)
    }, [applyDel, applySub, flat.length, selection])

    const registerFocus = useCallback((fn: () => void) => {
      focusSearchRef.current = fn
    }, [])

    return (
      <div className="sv-root" ref={rootRef}>
        <ViewerToolbar
          searchQuery={searchQuery}
          jumpError={jumpError}
          variantCount={variantCount}
          canUndo={cursor > 0}
          canRedo={cursor < history.length}
          editCount={edits.size}
          showHistory={showHistory}
          onSearchChange={setSearchQuery}
          onJumpQuery={jumpToQuery}
          onClearSearch={() => {
            setSearchQuery('')
            setJumpError(null)
          }}
          onStepVariant={stepVariant}
          onUndo={() => dispatch({ type: 'undo' })}
          onRedo={() => dispatch({ type: 'redo' })}
          onToggleHistory={() => setShowHistory((s) => !s)}
          onReset={resetEdits}
          registerFocus={registerFocus}
        />

        {!navCollapsed && (
          <>
            <GeneMinimap
              data={data}
              activeExon={activeExon}
              showDensity={trackOn.clinvarDensity}
              onExonClick={jumpToExon}
            />
            <ExonStrip data={data} activeExon={activeExon} onPinClick={jumpToCdsPos} />
          </>
        )}

        <CodonDetail
          data={data}
          flat={flat}
          codons={codons}
          baseW={baseW}
          trackOn={trackOn}
          strandMode={strandMode}
          edits={edits}
          selection={selection}
          searchQuery={searchQuery}
          restrictionHover={restrictionHover}
          onBaseMouseDown={onBaseMouseDown}
          onBaseClick={onBaseClick}
          onClinvarClick={jumpToFlatIdx}
          onRestrictionHover={setRestrictionHover}
          onRestrictionSelect={(s, en) => setSelection({ start: s, end: en })}
        />

        <SelectionBar
          data={data}
          flat={flat}
          selection={selection}
          hasEdit={(i) => edits.has(i)}
          onDelRange={applyDel}
          onReplace={applyReplace}
          onClear={() => setSelection(null)}
        />

        {showHistory && history.length > 0 && (
          <HistoryTimeline
            history={history}
            cursor={cursor}
            onJump={(to) => dispatch({ type: 'jump', to })}
          />
        )}

        {popover && (
          <EditPopoverV2
            data={data}
            flat={flat}
            idx={popover.idx}
            current={edits.get(popover.idx) as Edit | undefined}
            anchorRect={popover.rect}
            onSub={(b) => {
              applySub(popover.idx, b)
              setPopover(null)
            }}
            onDel={() => {
              applyDel(popover.idx, popover.idx)
              setPopover(null)
            }}
            onIns={(seq) => {
              applyIns(popover.idx, seq)
              setPopover(null)
            }}
            onReset={() => {
              commit(`Reset ${posDisplay(data, flat[popover.idx])}`, (m) =>
                m.delete(popover.idx),
              )
              setPopover(null)
            }}
            onClose={() => setPopover(null)}
          />
        )}
      </div>
    )
  },
)
