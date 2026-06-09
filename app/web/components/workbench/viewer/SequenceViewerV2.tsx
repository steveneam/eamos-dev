'use client'
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
  type ClinvarVariant,
  type FlatBase,
  type GeneWindowData,
} from '@/lib/workbench/gene-window'
import {
  editReducer,
  initialEditState,
  type Edit,
  type EditMap,
} from '@/lib/workbench/edit-state'
import type { Base } from '@/lib/workbench/codon-table'
import type { AlleleMode, PrimerPair } from '@/lib/backend'
import type { SelectionSummary, StrandMode, TrackState } from './viewer-types'
import { GeneMinimap } from './GeneMinimap'
import { CodonDetail } from './CodonDetail'
import { ProteinView } from './ProteinView'
import { HistoryTimeline } from './HistoryTimeline'
import { ViewerToolbar } from './ViewerToolbar'
import { EditPopoverV2 } from './EditPopoverV2'
import { ZoomSlider } from './ZoomSlider'
import { IconChevron, IconGene, IconProtein, IconList } from '@/components/icons/Icon'
import type { ReactNode } from 'react'

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
  /** Range actions driven from the side-panel edit hub (FE-5.6 Unit C).
   *  The reducer + selection state stay in the viewer; the side panel only
   *  invokes these via the ref. */
  delSelection: () => void
  replaceSelection: (seq: string) => void
  clearSelection: () => void
}

interface SequenceViewerV2Props {
  data: GeneWindowData
  trackOn: TrackState
  strandMode: StrandMode
  baseW: number
  /** Drives the hover-revealed zoom slider inside the Sequence window. */
  onBaseW: (w: number) => void
  /** Reference/control vs variant-applied sequence basis (GV-006). The
   *  adapter already applied the SNV to `data` in `variant` mode; this is
   *  passed through so the queried codon shows its ref→alt change. */
  alleleMode: AlleleMode
  /** Hide the gene minimap (collapsible nav; minimap only). Driven from
   *  outside (ZoomSlider "Hide map" + the new inline section-header
   *  chevron via `onToggleMinimap`). */
  navCollapsed: boolean
  /** Optional callback so the inline section-header chevron above the
   *  minimap can drive the same external state the ZoomSlider button does.
   *  Falls back to a noop — the prop is optional for backwards-compat. */
  onToggleMinimap?: () => void
  onScratchChange: (entries: ScratchEntry[]) => void
  onSelectionChange: (selection: SelectionSummary | null) => void
  onEditCountChange?: (count: number) => void
  onActiveExonChange?: (n: number) => void
  /** Clicking a ClinVar dot focuses it: jumps to the position and reports the
   *  variant up so the Scratchpad log can show an info card. */
  onClinvarSelect?: (variant: ClinvarVariant) => void
  /** ClinVar id (`cv`) of the currently focused dot → drives its active ring. */
  activeClinvar?: string | null
  /** A primer pair toggled on in the Primer tool → a rough directional amplicon
   *  bracket over the sequence. Primer positions aren't in the contract yet
   *  (see docs/workbench-backend-wiring), so this is a schematic spanning the
   *  queried variant, not base-anchored. */
  selectedPrimer?: PrimerPair | null
}

export const SequenceViewerV2 = forwardRef<SequenceViewerHandle, SequenceViewerV2Props>(
  function SequenceViewerV2(
    {
      data,
      trackOn,
      strandMode,
      baseW,
      onBaseW,
      alleleMode,
      navCollapsed,
      onToggleMinimap,
      onScratchChange,
      onSelectionChange,
      onEditCountChange,
      onActiveExonChange,
      onClinvarSelect,
      activeClinvar,
      selectedPrimer,
    },
    ref,
  ) {
    const flat = useMemo(() => buildFlatWindow(data), [data])
    const codons = useMemo(() => buildCodons(flat), [flat])
    const rootRef = useRef<HTMLDivElement>(null)
    const focusSearchRef = useRef<() => void>(() => {})
    const isSelecting = useRef(false)
    const dragCleanupRef = useRef<(() => void) | null>(null)
    const selectionRef = useRef<{ start: number; end: number } | null>(null)

    const [editState, dispatch] = useReducer(editReducer, initialEditState)
    const { edits, history, cursor } = editState
    const [selection, setSelection] = useState<{ start: number; end: number } | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [jumpError, setJumpError] = useState<string | null>(null)
    const [showHistory, setShowHistory] = useState(false)
    const [restrictionHover, setRestrictionHover] = useState<string | null>(null)
    const [popover, setPopover] = useState<{ idx: number; x: number; y: number } | null>(
      null,
    )
    // Local collapse state for the inline protein + sequence windows. The
    // minimap collapse is driven externally via `navCollapsed`/`onToggleMinimap`
    // so the ZoomSlider "Hide map" button and the inline header chevron
    // stay in sync.
    const [proteinOpen, setProteinOpen] = useState(true)
    const [sequenceOpen, setSequenceOpen] = useState(true)

    const exonOf = useCallback(
      (cds: number) =>
        data.exons.find((e) => cds >= e.cdsStart && cds <= e.cdsEnd)?.num ??
        data.exons[0]?.num ??
        0,
      [data],
    )
    const activeExonKey = `${data.gene}:${data.transcript}:${data.queriedVariant.hgvsC}`
    const defaultActiveExon = useMemo(
      () => exonOf(data.queriedVariant.cdsPos),
      [data.queriedVariant.cdsPos, exonOf],
    )
    const [activeExonOverride, setActiveExonOverride] = useState<{
      key: string
      exon: number
    } | null>(null)
    const activeExon =
      activeExonOverride?.key === activeExonKey
        ? activeExonOverride.exon
        : defaultActiveExon
    const setActiveExon = useCallback(
      (exon: number) => setActiveExonOverride({ key: activeExonKey, exon }),
      [activeExonKey],
    )
    const visibleExons = useMemo(
      () =>
        Array.from(
          new Set(
            flat
              .filter((b): b is Extract<FlatBase, { kind: 'exon' }> => b.kind === 'exon')
              .map((b) => b.exonNum),
          ),
        ).sort((a, b) => a - b),
      [flat],
    )
    const visibleExonLabel = useMemo(() => formatExonList(visibleExons), [visibleExons])

    // ── Edit operations (mirror sequence-viewer.js) ──
    const commit = useCallback(
      (label: string, mutate: (m: EditMap) => void) =>
        dispatch({ type: 'commit', label, mutate }),
      [],
    )
    const applySub = useCallback(
      (idx: number, base: Base) => {
        const target = flat[idx]
        if (!target || target.kind === 'intron-gap') return
        const reff = target.base.toUpperCase()
        if (base === reff)
          commit(`Reset ${posDisplay(data, target)}`, (m) => m.delete(idx))
        else
          commit(`Substitute ${posDisplay(data, target)} ${reff}>${base}`, (m) =>
            m.set(idx, { kind: 'sub', alt: base }),
          )
      },
      [commit, data, flat],
    )
    const applyDel = useCallback(
      (lo: number, hi: number) => {
        const start = Math.max(0, lo)
        const end = Math.min(flat.length - 1, hi)
        if (start > end) return
        const label =
          start === end
            ? `Delete ${posDisplay(data, flat[start])}`
            : `Delete ${end - start + 1} bases ${posDisplay(data, flat[start])} → ${posDisplay(
                data,
                flat[end],
              )}`
        commit(label, (m) => {
          for (let i = start; i <= end; i++) {
            if (flat[i].kind === 'intron-gap') continue
            m.set(i, { kind: 'del', alt: '-' })
          }
        })
      },
      [commit, data, flat],
    )
    const applyIns = useCallback(
      (idx: number, seq: string) => {
        const target = flat[idx]
        if (!target || target.kind === 'intron-gap') return
        commit(`Insert ${seq} after ${posDisplay(data, target)}`, (m) =>
          m.set(idx, { kind: 'ins', alt: seq }),
        )
      },
      [commit, data, flat],
    )
    const applyReplace = useCallback(
      (lo: number, hi: number, seq: string) => {
        const start = Math.max(0, lo)
        const end = Math.min(flat.length - 1, hi)
        if (start > end) return
        commit(`Replace ${end - start + 1} bases with ${seq}`, (m) => {
          for (let i = start; i <= end; i++) m.delete(i)
          const usable = Math.min(seq.length, end - start + 1)
          for (let k = 0; k < usable; k++) {
            const idx = start + k
            if (flat[idx].kind === 'intron-gap') continue
            if (seq[k] !== flat[idx].base.toUpperCase())
              m.set(idx, { kind: 'sub', alt: seq[k] })
          }
          if (seq.length > usable) m.set(end, { kind: 'ins', alt: seq.substr(usable) })
          else if (seq.length < end - start + 1)
            for (let k = seq.length; k < end - start + 1; k++) {
              const idx = start + k
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

    // ── Range actions exposed to the side-panel edit hub via the handle.
    //    Declared before useImperativeHandle so its dep array is in scope. ──
    const selectionRange = useCallback(
      () =>
        selection
          ? ([
              Math.min(selection.start, selection.end),
              Math.max(selection.start, selection.end),
            ] as const)
          : null,
      [selection],
    )
    const delSelection = useCallback(() => {
      const r = selectionRange()
      if (r) applyDel(r[0], r[1])
    }, [applyDel, selectionRange])
    const replaceSelection = useCallback(
      (seq: string) => {
        const r = selectionRange()
        if (r) applyReplace(r[0], r[1], seq)
      },
      [applyReplace, selectionRange],
    )
    const clearSelection = useCallback(() => setSelection(null), [])

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
            conseq: consequenceAt(flat, k, e.alt as Base),
          })
        }
      })
      entries.sort((a, b) => a.cdsPos - b.cdsPos)
      onScratchChange(entries)
      onEditCountChange?.(edits.size)
    }, [edits, flat, onScratchChange, onEditCountChange])

    // ── Selection summary, mirrored to the side-panel edit hub (Unit C) ──
    // Deferred during an active drag: pushing the summary on every base-cross
    // re-rendered the whole shell (SidePanel + library rail + canvas) and
    // starved the band's paint (multi-second lag on fast drags). The band
    // paints from local state so it stays live; the summary flushes on mouseup
    // (and immediately for click / keyboard / jump / edit, which aren't drags).
    const flushSelectionSummary = useCallback(() => {
      const sel = selectionRef.current
      if (!sel) {
        onSelectionChange(null)
        return
      }
      const lo = Math.min(sel.start, sel.end)
      const hi = Math.max(sel.start, sel.end)
      onSelectionChange(buildSelectionSummary(data, flat, edits, lo, hi))
    }, [data, flat, edits, onSelectionChange])
    useEffect(() => {
      selectionRef.current = selection
      if (isSelecting.current) return
      flushSelectionSummary()
    }, [selection, flushSelectionSummary])

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
        if (i < 0 || i >= flat.length) return
        setSelection({ start: i, end: i })
        const b = flat[i]
        if (b?.kind === 'exon') setActiveExon(b.exonNum)
        scrollToIdx(i)
      },
      [flat, scrollToIdx, setActiveExon],
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
          setJumpError(
            `Exon ${n} not in current window${
              visibleExonLabel ? ` (window covers ${visibleExonLabel}).` : '.'
            }`,
          )
        }
      },
      [flat, jumpToFlatIdx, setActiveExon, visibleExonLabel],
    )
    useImperativeHandle(
      ref,
      () => ({
        jumpToExon,
        jumpToCdsPos,
        resetEdits,
        delSelection,
        replaceSelection,
        clearSelection,
      }),
      [
        jumpToExon,
        jumpToCdsPos,
        resetEdits,
        delSelection,
        replaceSelection,
        clearSelection,
      ],
    )

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
      rootRef.current?.classList.remove('sv-dragging-edge')
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
          flushSelectionSummary()
        }
        document.addEventListener('mousemove', move)
        document.addEventListener('mouseup', up)
        dragCleanupRef.current = () => {
          document.removeEventListener('mousemove', move)
          document.removeEventListener('mouseup', up)
        }
      },
      [cleanupSelectionDrag, flushSelectionSummary],
    )
    // Right-click opens the cursor-anchored edit menu for that base. It does
    // not disturb the selection — selecting (left-click/drag) and editing
    // (right-click / Scratchpad) are now independent flows.
    const onBaseContextMenu = useCallback((idx: number, x: number, y: number) => {
      setPopover({ idx, x, y })
    }, [])

    // Drag a selection-band edge handle. Reuses the same elementFromPoint
    // pattern as base-drag; normalizes so the left handle always drives the
    // low edge (`start`) and the right handle the high edge (`end`). The
    // `sv-dragging-edge` root class drops handle pointer-events mid-drag so
    // elementFromPoint reaches the bases underneath.
    const onSelectionEdgeDown = useCallback(
      (edge: 'start' | 'end') => {
        cleanupSelectionDrag()
        setSelection((sel) =>
          sel
            ? { start: Math.min(sel.start, sel.end), end: Math.max(sel.start, sel.end) }
            : sel,
        )
        isSelecting.current = true
        rootRef.current?.classList.add('sv-dragging-edge')
        const move = (e: MouseEvent) => {
          if (!isSelecting.current) return
          const t = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null
          const cell = t?.closest<HTMLElement>('.sv-base[data-idx]')
          if (!cell) return
          const i = parseInt(cell.dataset.idx!, 10)
          setSelection((sel) => {
            if (!sel) return sel
            if (edge === 'start') {
              const ns = Math.min(i, sel.end)
              return ns === sel.start ? sel : { start: ns, end: sel.end }
            }
            const ne = Math.max(i, sel.start)
            return ne === sel.end ? sel : { start: sel.start, end: ne }
          })
        }
        const up = () => {
          cleanupSelectionDrag()
          flushSelectionSummary()
        }
        document.addEventListener('mousemove', move)
        document.addEventListener('mouseup', up)
        dragCleanupRef.current = () => {
          document.removeEventListener('mousemove', move)
          document.removeEventListener('mouseup', up)
        }
      },
      [cleanupSelectionDrag, flushSelectionSummary],
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
          const base = e.key.toUpperCase()
          if (isBase(base)) applySub(selection.start, base)
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
    // Stable toolbar callbacks so the memoized ViewerToolbar skips re-render
    // during a selection drag (inline arrows would defeat the memo).
    const handleUndo = useCallback(() => dispatch({ type: 'undo' }), [])
    const handleRedo = useCallback(() => dispatch({ type: 'redo' }), [])
    const handleToggleHistory = useCallback(() => setShowHistory((s) => !s), [])
    const handleClearSearch = useCallback(() => {
      setSearchQuery('')
      setJumpError(null)
    }, [])
    // Clicking a ClinVar dot focuses it: jump to (and select) the base, then
    // report the variant up so the Scratchpad log can show its info card.
    const handleClinvarClick = useCallback(
      (variant: ClinvarVariant, idx: number) => {
        jumpToFlatIdx(idx)
        onClinvarSelect?.(variant)
      },
      [jumpToFlatIdx, onClinvarSelect],
    )

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
          onClearSearch={handleClearSearch}
          onStepVariant={stepVariant}
          onUndo={handleUndo}
          onRedo={handleRedo}
          onToggleHistory={handleToggleHistory}
          onReset={resetEdits}
          registerFocus={registerFocus}
        />

        {/* Three stacked windows: Gene minimap → Protein view → Sequence
            detail. Each gets a chevron header so the user can fold a window
            down without losing the others. */}
        <SectionHeader
          title="Gene minimap"
          sub={`${data.gene} · ${data.totalExons} exons`}
          open={!navCollapsed}
          onToggle={onToggleMinimap}
          icon={<IconGene size={14} />}
        />
        {!navCollapsed && (
          <GeneMinimap
            data={data}
            activeExon={activeExon}
            showDensity={trackOn.clinvar}
            onExonClick={jumpToExon}
          />
        )}

        <SectionHeader
          title="Protein view"
          sub={`${data.proteinLength || '—'} aa · ${alleleMode === 'variant' ? 'variant-applied' : 'reference'}`}
          open={proteinOpen}
          onToggle={() => setProteinOpen((o) => !o)}
          icon={<IconProtein size={14} />}
        />
        {proteinOpen && <ProteinView data={data} alleleMode={alleleMode} />}

        {/* Sequence window — wrapped so the zoom slider can hover-reveal
            scoped to this window only (not the whole viewer box, which
            would overlap the ViewerToolbar's Undo/Redo cluster). */}
        <div className="sv-sequence-wrap">
          <SectionHeader
            title="Sequence"
            sub="codons · bases"
            open={sequenceOpen}
            onToggle={() => setSequenceOpen((o) => !o)}
            icon={<IconList size={14} />}
          />
          {sequenceOpen && (
            <>
              {selectedPrimer && (
                <div
                  className="sv-primer-amplicon"
                  role="img"
                  aria-label={`Selected primer pair amplicon, ${selectedPrimer.product_size} bp, spanning ${data.queriedVariant.hgvsC}`}
                >
                  <span className="sv-pa-cap fwd">
                    <span className="sv-pa-tag">F</span> 5′→3′
                  </span>
                  <span className="sv-pa-track">
                    <span className="sv-pa-label">
                      Amplicon · {selectedPrimer.product_size} bp · spans {data.queriedVariant.hgvsC}
                      <span className="sv-pa-note">schematic — exact primer positions pending backend</span>
                    </span>
                  </span>
                  <span className="sv-pa-cap rev">
                    3′←5′ <span className="sv-pa-tag">R</span>
                  </span>
                </div>
              )}
              <div className="sv-zoom-overlay-seq" aria-hidden={false}>
                <ZoomSlider baseW={baseW} onBaseW={onBaseW} />
              </div>
              <CodonDetail
                data={data}
                flat={flat}
                codons={codons}
                baseW={baseW}
                trackOn={trackOn}
                strandMode={strandMode}
                alleleMode={alleleMode}
                edits={edits}
                selection={selection}
                activeClinvar={activeClinvar ?? null}
                searchQuery={searchQuery}
                restrictionHover={restrictionHover}
                onBaseMouseDown={onBaseMouseDown}
                onBaseContextMenu={onBaseContextMenu}
                onSelectionEdgeDown={onSelectionEdgeDown}
                onBlankMouseDown={clearSelection}
                onClinvarClick={handleClinvarClick}
                onRestrictionHover={setRestrictionHover}
                onRestrictionSelect={(s, en) => setSelection({ start: s, end: en })}
              />
            </>
          )}
        </div>

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
            anchor={{ x: popover.x, y: popover.y }}
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

/** Collapsible header bar above each viewer window (gene minimap, protein
 *  view, sequence detail). Click the row or the chevron to toggle. */
function SectionHeader({
  title,
  sub,
  open,
  onToggle,
  icon,
}: {
  title: string
  sub?: string
  open: boolean
  onToggle?: () => void
  icon?: ReactNode
}) {
  return (
    <div
      className="sv-section-head"
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={onToggle}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onToggle?.()
        }
      }}
    >
      {icon ? (
        <span className="sv-section-icon" aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <span className="sv-section-title">
        {title}
        {sub ? <span className="sv-section-sub"> · {sub}</span> : null}
      </span>
      <span className="sv-section-chev" aria-hidden="true">
        <IconChevron size={12} />
      </span>
    </div>
  )
}

function formatExonList(nums: number[]): string {
  if (nums.length === 0) return ''
  const consecutive = nums.every((n, i) => i === 0 || n === nums[i - 1] + 1)
  if (nums.length > 2 && consecutive) return `exons ${nums[0]}-${nums[nums.length - 1]}`
  if (nums.length === 1) return `exon ${nums[0]}`
  return `exons ${nums.join(', ')}`
}

function isBase(value: string): value is Base {
  return value === 'A' || value === 'T' || value === 'C' || value === 'G'
}

// Selection digest for the side-panel edit hub. Ported verbatim from the
// removed SelectionBar so the Scratchpad reads the same wording.
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

function buildSelectionSummary(
  data: GeneWindowData,
  flat: FlatBase[],
  edits: EditMap,
  lo: number,
  hi: number,
): SelectionSummary {
  const loB = flat[lo]
  const len = hi - lo + 1
  if (len === 1) {
    return {
      len: 1,
      loPos: posDisplay(data, loB),
      hiPos: posDisplay(data, loB),
      refBase: loB.kind === 'intron-gap' ? '—' : loB.base.toUpperCase(),
      hasEdit: edits.has(lo),
      span: '',
    }
  }
  return {
    len,
    loPos: posDisplay(data, loB),
    hiPos: posDisplay(data, flat[hi]),
    refBase: '',
    hasEdit: false,
    span: spanSummary(flat, lo, hi),
  }
}
