'use client'

import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react'
import type { AlleleMode, SelectionOrientationV1 } from '@/lib/backend'
import type { DesignSelectionDraft, LocusEditV1 } from '@/lib/workbench/design-context'
import {
  buildFullLocusRows,
  genomicPositionAt,
  isReverseDisplay,
  reverseComplement,
  type FullLocusRow,
  type FullLocusRows,
} from '@/lib/workbench/full-locus-layout'
import type { FullLocusViewModel } from '@/lib/workbench/full-locus-adapter'

interface FullLocusSelection {
  anchorGenomic: number
  focusGenomic: number
}

export interface FullLocusInitialState {
  selection: { genomicStart: number; genomicEnd: number } | null
  orientation: SelectionOrientationV1
  edits: LocusEditV1[]
  editRevision: number
}

interface FullLocusViewerProps {
  model: Extract<FullLocusViewModel, { kind: 'ready' }>
  alleleMode: AlleleMode
  initialState?: FullLocusInitialState | null
  onDesignSelectionChange?: (draft: DesignSelectionDraft | null) => void
  onTranscriptChange?: (transcript: string) => void
}

type CoordinateMode = 'sequence' | 'genomic'
type BaseKind = 'exon' | 'intron' | 'utr5' | 'utr3' | 'cds' | 'unknown'

interface EditHistoryState {
  edits: LocusEditV1[]
  undo: LocusEditV1[][]
  redo: LocusEditV1[][]
  revision: number
}

const ROW_GAP = 1
const ESTIMATED_ROW_HEIGHT = 24
const OVERSCAN_ROWS = 12
const EDGE_SCROLL_PX = 44
const MAX_RANGE_EDIT_BASES = 500
const MAX_LIVE_EDITS = 500

function bandKindAtCol(row: FullLocusRow, col: number): BaseKind {
  let cdsHit = false
  for (const band of row.bands) {
    if (col < band.colStart || col >= band.colEnd) continue
    if (band.kind === 'cds') {
      cdsHit = true
      continue
    }
    return band.kind
  }
  return cdsHit ? 'cds' : 'unknown'
}

function rowStartsNewBand(row: FullLocusRow): string | null {
  const fresh = row.bands.find(
    (band) => band.colStart === 0 && (band.kind === 'exon' || band.kind === 'intron'),
  )
  return fresh?.label ?? null
}

function formatCoord(value: number): string {
  return value.toLocaleString('en-US')
}

function reducedMotionScrollBehavior(): ScrollBehavior {
  if (typeof window === 'undefined') return 'auto'
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
}

function complementBase(base: string): string {
  return ({ A: 'T', C: 'G', G: 'C', T: 'A', N: 'N' } as Record<string, string>)[
    base.toUpperCase()
  ] ?? 'N'
}

function offsetForGenomic(rows: FullLocusRows, genomicPosition: number): number | null {
  if (genomicPosition < rows.locusStart || genomicPosition > rows.locusEnd) return null
  return isReverseDisplay(rows.orientation, rows.strand)
    ? rows.locusEnd - genomicPosition
    : genomicPosition - rows.locusStart
}

function normalizedSelection(selection: FullLocusSelection | null): [number, number] | null {
  if (!selection) return null
  return [
    Math.min(selection.anchorGenomic, selection.focusGenomic),
    Math.max(selection.anchorGenomic, selection.focusGenomic),
  ]
}

function displayBase(
  rows: FullLocusRows,
  row: FullLocusRow,
  col: number,
  alleleMode: AlleleMode,
  editsByPosition: ReadonlyMap<number, LocusEditV1>,
  variantSubstitutionSupported: boolean,
): { base: string; edited: boolean; inserted: boolean; deleted: boolean } {
  const genomicPosition = genomicPositionAt(rows, row.rowIndex * rows.basesPerRow + col)
  const reverse = isReverseDisplay(rows.orientation, rows.strand)
  const sourceBase = row.bases[col]?.toUpperCase() ?? 'N'
  if (genomicPosition == null) {
    return { base: sourceBase, edited: false, inserted: false, deleted: false }
  }
  const edit = editsByPosition.get(genomicPosition)
  if (edit?.kind === 'del') {
    return { base: '·', edited: true, inserted: false, deleted: true }
  }
  if (edit?.kind === 'sub') {
    return {
      base: reverse ? complementBase(edit.alt) : edit.alt,
      edited: true,
      inserted: false,
      deleted: false,
    }
  }
  let base = sourceBase
  if (
    alleleMode === 'variant' &&
    variantSubstitutionSupported &&
    row.variantPin?.col === col &&
    row.variantPin.altBase
  ) {
    base = reverse ? complementBase(row.variantPin.altBase) : row.variantPin.altBase
  }
  return {
    base,
    edited: Boolean(edit),
    inserted: edit?.kind === 'ins',
    deleted: false,
  }
}

interface RowDOMProps {
  row: FullLocusRow
  rows: FullLocusRows
  coordinateMode: CoordinateMode
  alleleMode: AlleleMode
  selection: [number, number] | null
  editsByPosition: ReadonlyMap<number, LocusEditV1>
  variantSubstitutionSupported: boolean
}

function RowDOM({
  row,
  rows,
  coordinateMode,
  alleleMode,
  selection,
  editsByPosition,
  variantSubstitutionSupported,
}: RowDOMProps) {
  const codonStartCols = new Set(row.codonMarks.map((mark) => mark.col))
  const clinvarCols = new Map<number, string>()
  for (const pin of row.clinvarPins) {
    if (!clinvarCols.has(pin.col)) clinvarCols.set(pin.col, pin.label)
  }
  const variantCol = row.variantPin?.col ?? -1
  const fresh = rowStartsNewBand(row)
  const padLength = rows.basesPerRow - row.bases.length
  const rowStart = coordinateMode === 'sequence' ? row.sequenceStart : row.genomicStart
  const rowEnd = coordinateMode === 'sequence' ? row.sequenceEnd : row.genomicEnd

  return (
    <div className={`fl-row${row.variantPin ? ' fl-row--has-variant' : ''}`}>
      <div className="fl-row-coord">
        <span className="fl-row-coord-start">{formatCoord(rowStart)}</span>
        {fresh ? <span className="fl-row-band-label">{fresh}</span> : null}
      </div>
      <div className="fl-row-bases" aria-hidden="true">
        {row.bases.split('').map((_, col) => {
          const displayOffset = row.rowIndex * rows.basesPerRow + col
          const genomicPosition = genomicPositionAt(rows, displayOffset)
          const view = displayBase(
            rows,
            row,
            col,
            alleleMode,
            editsByPosition,
            variantSubstitutionSupported,
          )
          const kind = bandKindAtCol(row, col)
          const isVariant = col === variantCol
          const isClinvar = clinvarCols.has(col)
          const isCodonStart = codonStartCols.has(col)
          const selected =
            genomicPosition != null &&
            selection != null &&
            genomicPosition >= selection[0] &&
            genomicPosition <= selection[1]
          const classes = [
            'fl-base',
            `fl-base--${kind}`,
            isCodonStart ? 'fl-base--codon-start' : '',
            isClinvar ? 'fl-base--clinvar' : '',
            isVariant ? 'fl-base--variant' : '',
            selected ? 'fl-base--selected' : '',
            view.edited ? 'fl-base--edited' : '',
            view.deleted ? 'fl-base--deleted' : '',
          ]
            .filter(Boolean)
            .join(' ')
          const title = isVariant
            ? row.variantPin?.label
            : isClinvar
              ? clinvarCols.get(col)
              : genomicPosition != null
                ? `${rows.chrom}:${genomicPosition}`
                : undefined
          return (
            <span
              key={col}
              className={classes}
              data-offset={displayOffset}
              data-genomic={genomicPosition ?? undefined}
              title={title}
            >
              {view.base}
              {view.inserted ? <sup className="fl-base-insert">+</sup> : null}
            </span>
          )
        })}
        {padLength > 0
          ? Array.from({ length: padLength }, (_, index) => (
              <span key={`pad-${index}`} className="fl-base fl-base--pad">
                &nbsp;
              </span>
            ))
          : null}
      </div>
      <div className="fl-row-end">{formatCoord(rowEnd)}</div>
    </div>
  )
}

const MemoRowDOM = memo(RowDOM)

function selectionLabel(
  rows: FullLocusRows,
  selection: FullLocusSelection | null,
  editCount: number,
  revision: number,
): string {
  const range = normalizedSelection(selection)
  if (!range) return 'No range selected. Use search, coordinates, pointer drag, or arrow keys.'
  const length = range[1] - range[0] + 1
  return `${rows.chrom}:${formatCoord(range[0])}-${formatCoord(range[1])}, ${formatCoord(length)} bp, ${rows.orientation.replaceAll('_', ' ')}, ${editCount} edit${editCount === 1 ? '' : 's'}, revision ${revision}`
}

function FullLocusViewerInner({
  model,
  alleleMode,
  initialState,
  onDesignSelectionChange,
  onTranscriptChange,
}: FullLocusViewerProps) {
  const defaultOrientation = initialState?.orientation ?? model.rows.orientation
  const defaultSelection = initialState?.selection
    ? {
        anchorGenomic: initialState.selection.genomicStart,
        focusGenomic: initialState.selection.genomicEnd,
      }
    : null
  const scrollerRef = useRef<HTMLDivElement>(null)
  const measureRef = useRef<HTMLDivElement | null>(null)
  const selectionRef = useRef<FullLocusSelection | null>(defaultSelection)
  const pointerRef = useRef<{ id: number; x: number; y: number } | null>(null)
  const autoScrollFrameRef = useRef<number | null>(null)
  const autoScrollTickRef = useRef<() => void>(() => undefined)
  const didInitialScrollRef = useRef(false)

  const [orientation, setOrientation] = useState<SelectionOrientationV1>(defaultOrientation)
  const [coordinateMode, setCoordinateMode] = useState<CoordinateMode>('genomic')
  const [selection, setSelectionState] = useState<FullLocusSelection | null>(defaultSelection)
  const [editState, setEditState] = useState<EditHistoryState>({
    edits: initialState?.edits ?? [],
    undo: [],
    redo: [],
    revision: initialState?.edits.length ? Math.max(1, initialState.editRevision) : 0,
  })
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportH, setViewportH] = useState(0)
  const [rowHeight, setRowHeight] = useState(ESTIMATED_ROW_HEIGHT)
  const [basesPerRow, setBasesPerRow] = useState(60)
  const [query, setQuery] = useState('')
  const [queryMessage, setQueryMessage] = useState<string | null>(null)
  const [coordinateStart, setCoordinateStart] = useState('')
  const [coordinateEnd, setCoordinateEnd] = useState('')
  const [replaceDraft, setReplaceDraft] = useState('')
  const [insertDraft, setInsertDraft] = useState('')
  const [announcement, setAnnouncement] = useState('Whole-gene viewer ready.')

  const rows = useMemo(
    () => buildFullLocusRows(model.fullLocus, { orientation, basesPerRow }),
    [basesPerRow, model.fullLocus, orientation],
  )
  const editsByPosition = useMemo(
    () => new Map(editState.edits.map((edit) => [edit.genomicPosition, edit])),
    [editState.edits],
  )
  const variantSubstitutionSupported = useMemo(
    () => rows.rows.some((row) => {
      const ref = row.variantPin?.refBase?.trim().toUpperCase() ?? ''
      const alt = row.variantPin?.altBase?.trim().toUpperCase() ?? ''
      return /^[ACGTN]$/.test(ref) && /^[ACGTN]$/.test(alt)
    }),
    [rows.rows],
  )
  const rowCount = rows.rows.length
  const rowSlot = rowHeight + ROW_GAP
  const totalHeight = Math.max(0, rowCount * rowSlot - ROW_GAP)
  const selectedRange = normalizedSelection(selection)

  const setSelection = useCallback((next: FullLocusSelection | null) => {
    selectionRef.current = next
    setSelectionState(next)
  }, [])

  const emitDesignSelection = useCallback(
    (
      nextSelection = selectionRef.current,
      nextEdits = editState.edits,
      nextRevision = editState.revision,
      nextOrientation = orientation,
    ) => {
      const range = normalizedSelection(nextSelection)
      if (!range) {
        onDesignSelectionChange?.(null)
        return
      }
      const edited = nextEdits.length > 0
      onDesignSelectionChange?.({
        genomicStart: range[0],
        genomicEnd: range[1],
        orientation: nextOrientation,
        sequenceBasis: edited ? 'edited' : alleleMode,
        baseAllele: alleleMode,
        editRevision: edited ? Math.max(1, nextRevision) : 0,
        edits: nextEdits,
      })
    },
    [alleleMode, editState.edits, editState.revision, onDesignSelectionChange, orientation],
  )

  useEffect(() => {
    emitDesignSelection()
  }, [alleleMode, emitDesignSelection])

  useLayoutEffect(() => {
    const scroller = scrollerRef.current
    if (!scroller) return
    const sync = () => {
      setViewportH(scroller.clientHeight)
      const width = scroller.clientWidth
      const nextBasesPerRow = width < 520 ? 30 : width < 820 ? 45 : 60
      setBasesPerRow((previous) =>
        previous === nextBasesPerRow ? previous : nextBasesPerRow,
      )
      const rowElement = measureRef.current
      if (!rowElement) return
      const measured = rowElement.getBoundingClientRect().height
      if (measured > 0) {
        setRowHeight((previous) => (Math.abs(previous - measured) > 0.5 ? measured : previous))
      }
    }
    sync()
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(sync)
    observer.observe(scroller)
    return () => observer.disconnect()
  }, [])

  const overscanPx = OVERSCAN_ROWS * rowSlot
  const startIndex = Math.max(0, Math.floor((scrollTop - overscanPx) / rowSlot))
  const endIndex = Math.min(
    rowCount,
    Math.ceil((scrollTop + viewportH + overscanPx) / rowSlot),
  )
  const visibleRows = useMemo(
    () => rows.rows.slice(startIndex, endIndex),
    [endIndex, rows.rows, startIndex],
  )

  const scrollToOffset = useCallback(
    (offset: number, behavior: ScrollBehavior = reducedMotionScrollBehavior()) => {
      const scroller = scrollerRef.current
      if (!scroller || rows.totalBases === 0) return
      const bounded = Math.max(0, Math.min(rows.totalBases - 1, Math.trunc(offset)))
      const rowIndex = Math.floor(bounded / rows.basesPerRow)
      const top = rowIndex * rowSlot - scroller.clientHeight * 0.34
      scroller.scrollTo({ top: Math.max(0, top), behavior })
    },
    [rowSlot, rows.basesPerRow, rows.totalBases],
  )

  const jumpToGenomic = useCallback(
    (position: number, select = true) => {
      const offset = offsetForGenomic(rows, position)
      if (offset == null) {
        setQueryMessage(`Coordinate is outside ${rows.chrom}:${rows.locusStart}-${rows.locusEnd}.`)
        return false
      }
      if (select) {
        const next = { anchorGenomic: position, focusGenomic: position }
        setSelection(next)
        emitDesignSelection(next)
        setAnnouncement(selectionLabel(rows, next, editState.edits.length, editState.revision))
      }
      scrollToOffset(offset)
      return true
    },
    [editState.edits.length, editState.revision, emitDesignSelection, rows, scrollToOffset, setSelection],
  )

  const returnToVariant = useCallback(() => {
    if (rows.queriedGenomicPosition == null) {
      setQueryMessage('The queried variant has no resolved full-locus coordinate.')
      return
    }
    jumpToGenomic(rows.queriedGenomicPosition)
    setQueryMessage('Returned to the queried variant.')
  }, [jumpToGenomic, rows.queriedGenomicPosition])

  useEffect(() => {
    if (didInitialScrollRef.current || viewportH <= 0) return
    const initialPosition = selectionRef.current?.focusGenomic ?? rows.queriedGenomicPosition
    if (initialPosition == null) return
    const offset = offsetForGenomic(rows, initialPosition)
    if (offset == null) return
    didInitialScrollRef.current = true
    scrollToOffset(offset, 'auto')
  }, [rows, scrollToOffset, viewportH])

  const applySearch = useCallback(() => {
    const clean = query.trim()
    if (!clean) return
    const transcriptMatch = model.transcriptOptions.find(
      (option) => option.toLowerCase() === clean.toLowerCase(),
    )
    if (transcriptMatch) {
      if (transcriptMatch === model.transcript) setQueryMessage(`${transcriptMatch} is active.`)
      else onTranscriptChange?.(transcriptMatch)
      return
    }
    const exon = /^exon\s*(\d+)$/i.exec(clean)
    if (exon) {
      const number = Number(exon[1])
      const target = rows.navigationTargets.find(
        (item) => item.kind === 'exon' && item.exonNumber === number,
      )
      if (!target) {
        setQueryMessage(`Exon ${number} is not annotated on ${rows.transcript}.`)
        return
      }
      jumpToGenomic(target.genomicStart)
      setQueryMessage(`Selected ${target.label}.`)
      return
    }
    const feature = rows.navigationTargets.find(
      (item) => item.label.toLowerCase() === clean.toLowerCase() || item.kind === clean.toLowerCase(),
    )
    if (feature) {
      jumpToGenomic(feature.genomicStart)
      setQueryMessage(`Selected ${feature.label}.`)
      return
    }
    if (/^utr$/i.test(clean)) {
      const target = rows.navigationTargets.find(
        (item) => item.kind === 'utr5' || item.kind === 'utr3',
      )
      if (!target) {
        setQueryMessage(`No UTR interval is annotated on ${rows.transcript}.`)
        return
      }
      jumpToGenomic(target.genomicStart)
      setQueryMessage(`Selected ${target.label}. Search UTR5 or UTR3 to choose an end explicitly.`)
      return
    }
    const coordinate = /^(?:(chr[^:]+):)?([0-9,]+)$/i.exec(clean)
    if (coordinate) {
      const enteredChrom = coordinate[1]?.toLowerCase().replace(/^chr/, '')
      const activeChrom = rows.chrom.toLowerCase().replace(/^chr/, '')
      if (enteredChrom && enteredChrom !== activeChrom) {
        setQueryMessage(`That coordinate is on ${coordinate[1]}, but this locus is ${rows.chrom}.`)
        return
      }
      const position = Number(coordinate[2].replaceAll(',', ''))
      if (jumpToGenomic(position)) setQueryMessage(`Selected ${rows.chrom}:${formatCoord(position)}.`)
      return
    }
    if (/^[ACGTN]{3,}$/i.test(clean)) {
      const motif = clean.toUpperCase()
      const offset = rows.displaySequence.indexOf(motif)
      if (offset < 0) {
        setQueryMessage(`Sequence ${motif} was not found in the complete locus.`)
        return
      }
      const start = genomicPositionAt(rows, offset)
      const end = genomicPositionAt(rows, offset + motif.length - 1)
      if (start == null || end == null) return
      const next = { anchorGenomic: start, focusGenomic: end }
      setSelection(next)
      emitDesignSelection(next)
      scrollToOffset(offset)
      setQueryMessage(`Selected the ${motif.length} bp sequence match.`)
      setAnnouncement(selectionLabel(rows, next, editState.edits.length, editState.revision))
      return
    }
    setQueryMessage('Try exon 7, a genomic coordinate, a transcript id, UTR, or an A/C/G/T motif.')
  }, [
    editState.edits.length,
    editState.revision,
    emitDesignSelection,
    jumpToGenomic,
    model.transcript,
    model.transcriptOptions,
    onTranscriptChange,
    query,
    rows,
    scrollToOffset,
    setSelection,
  ])

  const applyCoordinateRange = useCallback(() => {
    const start = Number(coordinateStart.replaceAll(',', ''))
    const end = Number((coordinateEnd || coordinateStart).replaceAll(',', ''))
    if (
      !Number.isSafeInteger(start) ||
      !Number.isSafeInteger(end) ||
      start < rows.locusStart ||
      end > rows.locusEnd ||
      start > end
    ) {
      setQueryMessage(`Enter a closed range within ${rows.chrom}:${rows.locusStart}-${rows.locusEnd}.`)
      return
    }
    const next = { anchorGenomic: start, focusGenomic: end }
    setSelection(next)
    emitDesignSelection(next)
    scrollToOffset(offsetForGenomic(rows, start) ?? 0)
    setAnnouncement(selectionLabel(rows, next, editState.edits.length, editState.revision))
    setQueryMessage(`Selected ${formatCoord(end - start + 1)} bp by coordinate.`)
  }, [
    coordinateEnd,
    coordinateStart,
    editState.edits.length,
    editState.revision,
    emitDesignSelection,
    rows,
    scrollToOffset,
    setSelection,
  ])

  const baseFromPoint = useCallback((x: number, y: number): number | null => {
    const element = document.elementFromPoint(x, y)?.closest<HTMLElement>('.fl-base[data-genomic]')
    if (!element) return null
    const position = Number(element.dataset.genomic)
    return Number.isSafeInteger(position) ? position : null
  }, [])

  const stopAutoScroll = useCallback(() => {
    pointerRef.current = null
    if (autoScrollFrameRef.current != null) {
      window.cancelAnimationFrame(autoScrollFrameRef.current)
      autoScrollFrameRef.current = null
    }
  }, [])

  const autoScrollTick = useCallback(() => {
    const pointer = pointerRef.current
    const scroller = scrollerRef.current
    if (!pointer || !scroller) {
      autoScrollFrameRef.current = null
      return
    }
    const bounds = scroller.getBoundingClientRect()
    let delta = 0
    if (pointer.y < bounds.top + EDGE_SCROLL_PX) {
      delta = -Math.max(3, (bounds.top + EDGE_SCROLL_PX - pointer.y) * 0.28)
    } else if (pointer.y > bounds.bottom - EDGE_SCROLL_PX) {
      delta = Math.max(3, (pointer.y - (bounds.bottom - EDGE_SCROLL_PX)) * 0.28)
    }
    if (delta !== 0) scroller.scrollTop += delta
    const genomic = baseFromPoint(pointer.x, Math.max(bounds.top + 2, Math.min(bounds.bottom - 2, pointer.y)))
    if (genomic != null) {
      const current = selectionRef.current
      if (current && current.focusGenomic !== genomic) {
        setSelection({ ...current, focusGenomic: genomic })
      }
    }
    autoScrollFrameRef.current = window.requestAnimationFrame(() => autoScrollTickRef.current())
  }, [baseFromPoint, setSelection])

  useEffect(() => {
    autoScrollTickRef.current = autoScrollTick
  }, [autoScrollTick])

  const handlePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.button !== 0) return
      const genomic = baseFromPoint(event.clientX, event.clientY)
      if (genomic == null) return
      event.preventDefault()
      event.currentTarget.focus({ preventScroll: true })
      event.currentTarget.setPointerCapture(event.pointerId)
      const current = selectionRef.current
      const next = event.shiftKey && current
        ? { ...current, focusGenomic: genomic }
        : { anchorGenomic: genomic, focusGenomic: genomic }
      setSelection(next)
      pointerRef.current = { id: event.pointerId, x: event.clientX, y: event.clientY }
      if (autoScrollFrameRef.current == null) {
        autoScrollFrameRef.current = window.requestAnimationFrame(autoScrollTick)
      }
    },
    [autoScrollTick, baseFromPoint, setSelection],
  )

  const handlePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const pointer = pointerRef.current
      if (!pointer || pointer.id !== event.pointerId) return
      event.preventDefault()
      pointer.x = event.clientX
      pointer.y = event.clientY
      const genomic = baseFromPoint(event.clientX, event.clientY)
      const current = selectionRef.current
      if (genomic != null && current && current.focusGenomic !== genomic) {
        setSelection({ ...current, focusGenomic: genomic })
      }
    },
    [baseFromPoint, setSelection],
  )

  const finishPointerSelection = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (pointerRef.current?.id !== event.pointerId) return
      stopAutoScroll()
      try {
        event.currentTarget.releasePointerCapture(event.pointerId)
      } catch {
        // Pointer capture may already have ended.
      }
      emitDesignSelection(selectionRef.current)
      setAnnouncement(
        selectionLabel(rows, selectionRef.current, editState.edits.length, editState.revision),
      )
    },
    [editState.edits.length, editState.revision, emitDesignSelection, rows, stopAutoScroll],
  )

  useEffect(() => stopAutoScroll, [stopAutoScroll])

  const commitEdits = useCallback(
    (nextEdits: LocusEditV1[], label: string) => {
      if (nextEdits.length > MAX_LIVE_EDITS) {
        setQueryMessage(
          `This browser workspace supports at most ${MAX_LIVE_EDITS} live edit positions. Reset or undo edits before adding more.`,
        )
        return
      }
      setEditState((current) => {
        const nextRevision = nextEdits.length > 0 ? Math.max(1, current.revision + 1) : 0
        const next = {
          edits: nextEdits,
          undo: [...current.undo.slice(-49), current.edits],
          redo: [],
          revision: nextRevision,
        }
        queueMicrotask(() => {
          emitDesignSelection(selectionRef.current, next.edits, next.revision)
          setAnnouncement(`${label}. ${selectionLabel(rows, selectionRef.current, next.edits.length, next.revision)}`)
        })
        return next
      })
    },
    [emitDesignSelection, rows],
  )

  const editSelection = useCallback(
    (kind: 'sub' | 'del', alt = '') => {
      const range = normalizedSelection(selectionRef.current)
      if (!range) return
      const count = range[1] - range[0] + 1
      if ((kind === 'sub' && count !== 1) || count > MAX_RANGE_EDIT_BASES) {
        setQueryMessage(
          kind === 'sub'
            ? 'Substitution requires a single selected base.'
            : `Delete at most ${MAX_RANGE_EDIT_BASES} bases in one revision.`,
        )
        return
      }
      const nextByPosition = new Map(
        editState.edits.map((edit) => [edit.genomicPosition, edit]),
      )
      for (let position = range[0]; position <= range[1]; position += 1) {
        nextByPosition.set(position, {
          genomicPosition: position,
          kind,
          alt:
            kind === 'sub' && isReverseDisplay(rows.orientation, rows.strand)
              ? complementBase(alt)
              : alt,
        })
      }
      commitEdits(
        Array.from(nextByPosition.values()).sort((a, b) => a.genomicPosition - b.genomicPosition),
        kind === 'sub' ? `Substituted ${rows.chrom}:${range[0]} with ${alt}` : `Deleted ${count} bp`,
      )
    },
    [commitEdits, editState.edits, rows],
  )

  const insertAtSelection = useCallback(() => {
    const range = normalizedSelection(selectionRef.current)
    const clean = insertDraft.replace(/\s+/g, '').toUpperCase()
    if (!range || range[0] !== range[1] || !/^[ACGTN]{1,1000}$/.test(clean)) {
      setQueryMessage('Select one base and enter 1-1,000 A/C/G/T/N bases to insert.')
      return
    }
    const genomicAlt = isReverseDisplay(rows.orientation, rows.strand)
      ? reverseComplement(clean)
      : clean
    const next = [
      ...editState.edits.filter((edit) => edit.genomicPosition !== range[0]),
      { genomicPosition: range[0], kind: 'ins' as const, alt: genomicAlt },
    ].sort((a, b) => a.genomicPosition - b.genomicPosition)
    commitEdits(next, `Inserted ${clean.length} bp after genomic-forward ${rows.chrom}:${range[0]}`)
    setInsertDraft('')
  }, [commitEdits, editState.edits, insertDraft, rows])

  const replaceSelection = useCallback(() => {
    const range = normalizedSelection(selectionRef.current)
    const clean = replaceDraft.replace(/\s+/g, '').toUpperCase()
    if (!range || !/^[ACGTN]+$/.test(clean)) {
      setQueryMessage('Select a range and enter A/C/G/T/N replacement bases.')
      return
    }
    const count = range[1] - range[0] + 1
    if (count > MAX_RANGE_EDIT_BASES || clean.length !== count) {
      setQueryMessage(`Full-locus replacement must contain exactly ${count} bases (maximum ${MAX_RANGE_EDIT_BASES}).`)
      return
    }
    const reverse = isReverseDisplay(rows.orientation, rows.strand)
    const nextByPosition = new Map(
      editState.edits.map((edit) => [edit.genomicPosition, edit]),
    )
    for (let index = 0; index < count; index += 1) {
      const genomicPosition = reverse ? range[1] - index : range[0] + index
      const genomicAlt = reverse ? complementBase(clean[index]) : clean[index]
      const reference = model.fullLocus.locus.sequence[
        genomicPosition - model.fullLocus.locus.start
      ]?.toUpperCase()
      if (genomicAlt === reference) nextByPosition.delete(genomicPosition)
      else nextByPosition.set(genomicPosition, { genomicPosition, kind: 'sub', alt: genomicAlt })
    }
    commitEdits(
      Array.from(nextByPosition.values()).sort((left, right) => left.genomicPosition - right.genomicPosition),
      `Replaced ${count} bp at ${rows.chrom}:${range[0]}-${range[1]}`,
    )
    setReplaceDraft('')
  }, [commitEdits, editState.edits, model.fullLocus.locus, replaceDraft, rows])

  const undo = useCallback(() => {
    setEditState((current) => {
      const previous = current.undo.at(-1)
      if (!previous) return current
      const nextRevision = previous.length > 0 ? Math.max(1, current.revision + 1) : 0
      const next = {
        edits: previous,
        undo: current.undo.slice(0, -1),
        redo: [current.edits, ...current.redo.slice(0, 49)],
        revision: nextRevision,
      }
      queueMicrotask(() => emitDesignSelection(selectionRef.current, next.edits, next.revision))
      return next
    })
  }, [emitDesignSelection])

  const redo = useCallback(() => {
    setEditState((current) => {
      const following = current.redo[0]
      if (!following) return current
      const nextRevision = following.length > 0 ? Math.max(1, current.revision + 1) : 0
      const next = {
        edits: following,
        undo: [...current.undo.slice(-49), current.edits],
        redo: current.redo.slice(1),
        revision: nextRevision,
      }
      queueMicrotask(() => emitDesignSelection(selectionRef.current, next.edits, next.revision))
      return next
    })
  }, [emitDesignSelection])

  const handleKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      const target = event.target as HTMLElement
      if (target.matches('input, select, textarea, button')) return
      const current = selectionRef.current
      if (event.key === 'Escape') {
        event.preventDefault()
        setSelection(null)
        emitDesignSelection(null)
        setAnnouncement('Selection cleared.')
        return
      }
      if ((event.key === 'Backspace' || event.key === 'Delete') && current) {
        event.preventDefault()
        editSelection('del')
        return
      }
      if (/^[acgtn]$/i.test(event.key) && current) {
        event.preventDefault()
        editSelection('sub', event.key.toUpperCase())
        return
      }
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
      event.preventDefault()
      const currentOffset = current
        ? offsetForGenomic(rows, current.focusGenomic) ?? 0
        : rows.variantRowIndex != null
          ? rows.variantRowIndex * rows.basesPerRow
          : 0
      const nextOffset =
        event.key === 'Home'
          ? 0
          : event.key === 'End'
            ? rows.totalBases - 1
            : event.key === 'ArrowLeft'
              ? Math.max(0, currentOffset - 1)
              : Math.min(rows.totalBases - 1, currentOffset + 1)
      const genomic = genomicPositionAt(rows, nextOffset)
      if (genomic == null) return
      const next = event.shiftKey && current
        ? { ...current, focusGenomic: genomic }
        : { anchorGenomic: genomic, focusGenomic: genomic }
      setSelection(next)
      emitDesignSelection(next)
      scrollToOffset(nextOffset, 'auto')
      setAnnouncement(selectionLabel(rows, next, editState.edits.length, editState.revision))
    },
    [editSelection, editState.edits.length, editState.revision, emitDesignSelection, rows, scrollToOffset, setSelection],
  )

  const changeOrientation = useCallback(
    (next: SelectionOrientationV1) => {
      setOrientation(next)
      didInitialScrollRef.current = false
      emitDesignSelection(selectionRef.current, editState.edits, editState.revision, next)
      setAnnouncement(`Orientation changed to ${next.replaceAll('_', ' ')}.`)
    },
    [editState.edits, editState.revision, emitDesignSelection],
  )

  const adjustSelectionEndpoint = useCallback(
    (endpoint: 'start' | 'end', delta: -1 | 1) => {
      const range = normalizedSelection(selectionRef.current)
      if (!range) return
      let start = range[0]
      let end = range[1]
      if (endpoint === 'start') start = Math.max(rows.locusStart, Math.min(end, start + delta))
      else end = Math.min(rows.locusEnd, Math.max(start, end + delta))
      const next = { anchorGenomic: start, focusGenomic: end }
      setSelection(next)
      emitDesignSelection(next)
      scrollToOffset(offsetForGenomic(rows, endpoint === 'start' ? start : end) ?? 0, 'auto')
      setAnnouncement(selectionLabel(rows, next, editState.edits.length, editState.revision))
    },
    [editState.edits.length, editState.revision, emitDesignSelection, rows, scrollToOffset, setSelection],
  )

  const viewportStartOffset = Math.max(0, Math.floor(scrollTop / rowSlot) * rows.basesPerRow)
  const viewportRows = Math.max(1, Math.ceil(viewportH / rowSlot))
  const viewportEndOffset = Math.min(
    rows.totalBases,
    viewportStartOffset + viewportRows * rows.basesPerRow,
  )
  const viewportLeft = rows.totalBases > 0 ? (viewportStartOffset / rows.totalBases) * 100 : 0
  const viewportWidth = rows.totalBases > 0
    ? Math.max(1, ((viewportEndOffset - viewportStartOffset) / rows.totalBases) * 100)
    : 100

  return (
    <div className="fl-viewer">
      <div className="fl-header">
        <div className="fl-header-left">
          <span className="fl-header-gene">{model.gene}</span>
          <span className="fl-header-sep">·</span>
          <span className="fl-header-coord">
            {rows.chrom}:{formatCoord(rows.locusStart)}-{formatCoord(rows.locusEnd)} ({rows.strand})
          </span>
          <span className="fl-header-sep">·</span>
          <span className="fl-header-build">{rows.genomeBuild}</span>
        </div>
        <div className="fl-header-right">
          <label className="fl-transcript-select">
            <span>Transcript</span>
            <select
              value={model.transcript}
              onChange={(event) => onTranscriptChange?.(event.currentTarget.value)}
              aria-label="Active transcript"
            >
              {model.transcriptOptions.map((option) => (
                <option value={option} key={option}>{option}</option>
              ))}
            </select>
          </label>
          <span className="fl-header-stat">{formatCoord(rows.totalBases)} bp</span>
          <div className="fl-coord-toggle" role="group" aria-label="Row coordinates">
            <button
              type="button"
              className={coordinateMode === 'sequence' ? 'active' : ''}
              aria-pressed={coordinateMode === 'sequence'}
              onClick={() => setCoordinateMode('sequence')}
            >
              Locus
            </button>
            <button
              type="button"
              className={coordinateMode === 'genomic' ? 'active' : ''}
              aria-pressed={coordinateMode === 'genomic'}
              onClick={() => setCoordinateMode('genomic')}
            >
              Genomic
            </button>
          </div>
        </div>
      </div>

      <div className="fl-controls">
        <form
          className="fl-search"
          onSubmit={(event) => {
            event.preventDefault()
            applySearch()
          }}
        >
          <label htmlFor="fl-locus-search">Find across complete gene</label>
          <div>
            <input
              id="fl-locus-search"
              value={query}
              onChange={(event) => setQuery(event.currentTarget.value)}
              placeholder="Exon 7, chr1:68…, transcript, UTR, or sequence"
            />
            <button type="submit">Find</button>
            <button type="button" onClick={returnToVariant}>Query variant</button>
          </div>
        </form>
        <div className="fl-coordinate-entry" role="group" aria-label="Select genomic range">
          <label>
            Start
            <input
              inputMode="numeric"
              value={coordinateStart}
              onChange={(event) => setCoordinateStart(event.currentTarget.value)}
            />
          </label>
          <label>
            End
            <input
              inputMode="numeric"
              value={coordinateEnd}
              onChange={(event) => setCoordinateEnd(event.currentTarget.value)}
            />
          </label>
          <button type="button" onClick={applyCoordinateRange}>Select range</button>
        </div>
        {queryMessage ? <p className="fl-query-message" role="status">{queryMessage}</p> : null}
      </div>

      <div className="fl-orientation-row">
        <div className="fl-orientation" role="group" aria-label="Sequence orientation">
          {(['genomic_forward', 'genomic_reverse', 'transcript'] as const).map((value) => (
            <button
              type="button"
              key={value}
              className={orientation === value ? 'active' : ''}
              aria-pressed={orientation === value}
              onClick={() => changeOrientation(value)}
            >
              {value === 'genomic_forward'
                ? 'Genomic +'
                : value === 'genomic_reverse'
                  ? 'Genomic reverse'
                  : `Transcript (${rows.strand})`}
            </button>
          ))}
        </div>
        <span className="fl-selection-summary">{selectionLabel(rows, selection, editState.edits.length, editState.revision)}</span>
      </div>

      {alleleMode === 'variant' && !variantSubstitutionSupported ? (
        <p className="fl-basis-warning" role="status">
          Variant-basis sequence is unavailable because the queried allele is not a resolved single-base substitution. Reference bases remain visible and design runs are disabled until the allele resolves.
        </p>
      ) : null}

      <button
        type="button"
        className="fl-minimap"
        aria-label="Whole-gene minimap. Select a position in the complete locus."
        onClick={(event) => {
          if (event.detail === 0) {
            returnToVariant()
            return
          }
          const bounds = event.currentTarget.getBoundingClientRect()
          const pct = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width))
          const offset = Math.floor(pct * Math.max(0, rows.totalBases - 1))
          const genomic = genomicPositionAt(rows, offset)
          if (genomic != null) jumpToGenomic(genomic)
        }}
      >
        <span className="fl-minimap-track" aria-hidden="true">
          {rows.navigationTargets
            .filter((target) => target.kind === 'exon' || target.kind === 'utr5' || target.kind === 'utr3')
            .map((target) => {
              const a = offsetForGenomic(rows, target.genomicStart) ?? 0
              const b = offsetForGenomic(rows, target.genomicEnd) ?? 0
              const left = (Math.min(a, b) / rows.totalBases) * 100
              const width = Math.max(0.35, (Math.abs(b - a) / rows.totalBases) * 100)
              return (
                <span
                  key={target.id}
                  className={`fl-minimap-feature fl-minimap-feature--${target.kind}`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                />
              )
            })}
          {rows.queriedGenomicPosition != null ? (
            <span
              className="fl-minimap-query"
              style={{
                left: `${((offsetForGenomic(rows, rows.queriedGenomicPosition) ?? 0) / rows.totalBases) * 100}%`,
              }}
            />
          ) : null}
          <span
            className="fl-minimap-viewport"
            style={{ left: `${viewportLeft}%`, width: `${viewportWidth}%` }}
          />
        </span>
      </button>

      <div
        className="fl-scroller"
        ref={scrollerRef}
        role="region"
        aria-label={`Complete ${model.gene} locus sequence`}
        aria-describedby="fl-keyboard-help fl-selection-live"
        tabIndex={0}
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishPointerSelection}
        onPointerCancel={finishPointerSelection}
        onKeyDown={handleKeyDown}
      >
        <div className="fl-rows" style={{ position: 'relative', height: totalHeight }}>
          {visibleRows.map((row, index) => (
            <div
              key={row.rowIndex}
              ref={index === 0 ? measureRef : undefined}
              className="fl-row-anchor"
              style={{ position: 'absolute', left: 0, right: 0, top: row.rowIndex * rowSlot }}
            >
              <MemoRowDOM
                row={row}
                rows={rows}
                coordinateMode={coordinateMode}
                alleleMode={alleleMode}
                selection={selectedRange}
                editsByPosition={editsByPosition}
                variantSubstitutionSupported={variantSubstitutionSupported}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="fl-touch-range" aria-label="Range endpoint controls">
        <span className="fl-touch-range-label">Range endpoints</span>
        <div className="fl-touch-endpoint">
          <span>Start</span>
          <button type="button" onClick={() => adjustSelectionEndpoint('start', -1)} disabled={!selectedRange} aria-label="Move range start one base lower">−</button>
          <output>{selectedRange ? formatCoord(selectedRange[0]) : 'None'}</output>
          <button type="button" onClick={() => adjustSelectionEndpoint('start', 1)} disabled={!selectedRange} aria-label="Move range start one base higher">+</button>
        </div>
        <div className="fl-touch-endpoint">
          <span>End</span>
          <button type="button" onClick={() => adjustSelectionEndpoint('end', -1)} disabled={!selectedRange} aria-label="Move range end one base lower">−</button>
          <output>{selectedRange ? formatCoord(selectedRange[1]) : 'None'}</output>
          <button type="button" onClick={() => adjustSelectionEndpoint('end', 1)} disabled={!selectedRange} aria-label="Move range end one base higher">+</button>
        </div>
      </div>

      <div className="fl-editbar" aria-label="Selection editing">
        <span className="fl-editbar-label">Edit selected basis</span>
        <div className="fl-base-actions" role="group" aria-label="Substitute selected base">
          {['A', 'C', 'G', 'T'].map((base) => (
            <button type="button" key={base} onClick={() => editSelection('sub', base)} disabled={!selectedRange || selectedRange[0] !== selectedRange[1]}>
              {base}
            </button>
          ))}
          <button type="button" onClick={() => editSelection('del')} disabled={!selectedRange}>Delete</button>
        </div>
        <label className="fl-insert-field">
          Replace range (same length)
          <input
            value={replaceDraft}
            onChange={(event) => setReplaceDraft(event.currentTarget.value.toUpperCase())}
            placeholder="ACGT"
          />
        </label>
        <button type="button" onClick={replaceSelection} disabled={!selectedRange}>Replace</button>
        <label className="fl-insert-field">
          Insert after genomic-forward coordinate
          <input
            value={insertDraft}
            onChange={(event) => setInsertDraft(event.currentTarget.value.toUpperCase())}
            placeholder="ACGT"
          />
        </label>
        <button type="button" onClick={insertAtSelection} disabled={!selectedRange || selectedRange[0] !== selectedRange[1]}>Insert</button>
        <button type="button" onClick={undo} disabled={editState.undo.length === 0}>Undo</button>
        <button type="button" onClick={redo} disabled={editState.redo.length === 0}>Redo</button>
        <button
          type="button"
          onClick={() => commitEdits([], 'Reset all locus edits')}
          disabled={editState.edits.length === 0}
        >
          Reset edits
        </button>
        <button
          type="button"
          onClick={() => {
            setSelection(null)
            emitDesignSelection(null)
            setAnnouncement('Selection cleared.')
          }}
          disabled={!selectedRange}
        >
          Clear range
        </button>
      </div>

      <p id="fl-keyboard-help" className="fl-keyboard-help">
        Keyboard: arrows move one base; Shift+Arrow extends; Shift+Home or Shift+End extends to a locus endpoint; A/C/G/T substitutes one selected base; Delete removes the selected range; Escape clears.
      </p>
      <span id="fl-selection-live" className="sr-only" aria-live="polite">{announcement}</span>

      {model.warnings.length > 0 ? (
        <div className="fl-provenance" role="note">
          {model.warnings.map((warning) => (
            <span key={warning} className="fl-provenance-warn">{warning}</span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function FullLocusViewer(props: FullLocusViewerProps) {
  const { model } = props
  const locus = model.fullLocus.locus
  const identity = [
    model.gene,
    model.cdna,
    model.transcript,
    locus.chrom,
    locus.start,
    locus.end,
    model.fullLocus.transcript_projection.transcript,
  ].join('|')
  return <FullLocusViewerInner key={identity} {...props} />
}

export function FullLocusUnsupportedBanner({
  gene,
  onBackToWindow,
}: {
  gene: string
  onBackToWindow: () => void
}) {
  return (
    <div className="fl-unsupported" role="status">
      <p>
        A complete source-backed locus is unavailable for <span className="fl-unsupported-gene">{gene}</span>. Eamos will not substitute a cropped window or sample locus.
      </p>
      <button type="button" className="fl-unsupported-btn" onClick={onBackToWindow}>
        Use resolved window
      </button>
    </div>
  )
}
