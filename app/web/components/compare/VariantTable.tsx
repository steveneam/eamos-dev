'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { reportHrefForQuery } from '@/lib/variant-search'
import type { ParsedVariant } from '@/lib/variant-file'
import type { Panel } from '@/lib/backend'
import { panelBadge, type PanelBadge } from '@/lib/panels.mock'
import { CopyButton } from '@/components/ui/CopyButton'
import { saveVariants } from '@/lib/variant-library'

type PanelMembership = { slug: string; badge: PanelBadge; symbols: Set<string> }
type SortKey = 'idx' | 'gene' | 'variant'
type SortState = { key: SortKey; dir: 'asc' | 'desc' }
/** A row tagged with its stable original cohort position (1-based) so the #
 *  column travels with the row when other columns are sorted. */
type IndexedRow = { v: ParsedVariant; n: number }

/**
 * Variant cohort table. Sticky header + an Excel-style split-pane: toggle "Split
 * view" to get two independently-scrolling viewports over the SAME rows, with a
 * draggable divider (compare row 5 against row 950 without losing your place).
 * Columns sort (gene A→Z, variant by position low→high); a copy button yields
 * an Excel-paste-ready table. Row virtualization is the follow-up for true
 * 1000+ row performance.
 */
const PANE_HEIGHT = 560

function withFromCompare(href: string | null): string | null {
  if (!href) return null
  return href.includes('?') ? `${href}&from=compare` : `${href}?from=compare`
}

/** Sort key for the Variant column: genomic position for VCF rows
 *  (chrom-POS-ref-alt), else the first number in the HGVS string (c.247 → 247).
 *  Rows without a parseable position sort to the end. */
function variantPos(v: ParsedVariant): number {
  const genomic = /^(?:chr)?\w+-(\d+)-/i.exec(v.query ?? '')
  if (genomic) return Number(genomic[1])
  const m = /(\d+)/.exec(v.variant ?? v.query ?? '')
  return m ? Number(m[1]) : Number.POSITIVE_INFINITY
}

function sortIndexed(rows: IndexedRow[], sort: SortState | null): IndexedRow[] {
  if (!sort) return rows
  const dir = sort.dir === 'asc' ? 1 : -1
  const out = rows.slice()
  out.sort((a, b) => {
    let cmp = 0
    if (sort.key === 'gene') {
      const ga = (a.v.gene ?? '').toUpperCase()
      const gb = (b.v.gene ?? '').toUpperCase()
      // Empty gene always sorts to the end, regardless of direction.
      if (!ga && gb) return 1
      if (ga && !gb) return -1
      cmp = ga.localeCompare(gb)
    } else if (sort.key === 'variant') {
      cmp = variantPos(a.v) - variantPos(b.v)
    } else {
      cmp = a.n - b.n // sort by original cohort position
    }
    if (cmp === 0) cmp = a.n - b.n // stable tiebreak on original order
    return cmp * dir
  })
  return out
}

function escHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/** Excel/Sheets-friendly clipboard payload: rich HTML table + plain TSV. */
function copyPayload(rows: ParsedVariant[]): { html: string; text: string } {
  const headers = ['Gene', 'Variant', 'Source line']
  const cells = rows.map((v) => [v.gene ?? '', v.variant ?? v.query, v.raw])
  const text = [headers, ...cells].map((r) => r.join('\t')).join('\n')
  const thead = `<tr>${headers.map((h) => `<th>${escHtml(h)}</th>`).join('')}</tr>`
  const tbody = cells.map((r) => `<tr>${r.map((c) => `<td>${escHtml(c)}</td>`).join('')}</tr>`).join('')
  const html = `<table><thead>${thead}</thead><tbody>${tbody}</tbody></table>`
  return { html, text }
}

export function VariantTable({ rows, activePanels }: { rows: ParsedVariant[]; activePanels: Panel[] }) {
  const membership = useMemo<PanelMembership[]>(
    () =>
      activePanels.map((p) => ({
        slug: p.slug,
        badge: panelBadge(p),
        symbols: new Set(p.genes.map((g) => g.symbol.toUpperCase())),
      })),
    [activePanels],
  )
  const [split, setSplit] = useState(false)
  const [sort, setSort] = useState<SortState | null>(null)
  const [topFrac, setTopFrac] = useState(0.5)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const indexed = useMemo<IndexedRow[]>(() => rows.map((v, i) => ({ v, n: i + 1 })), [rows])
  const sorted = useMemo(() => sortIndexed(indexed, sort), [indexed, sort])
  const payload = useMemo(() => copyPayload(sorted.map((r) => r.v)), [sorted])

  // --- Selection state ---
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [saveFlash, setSaveFlash] = useState<number | null>(null) // count saved, null = idle
  const dragAnchorIdx = useRef<number | null>(null) // index in `sorted` of drag start
  const isDragging = useRef(false)
  const [dragActive, setDragActive] = useState(false)

  // Clear selection when rows change (new compare result loaded).
  useEffect(() => {
    setSelected(new Set())
  }, [rows])

  const onSort = (key: SortKey) =>
    setSort((s) => (s && s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))

  const onPointerDown = (e: React.PointerEvent) => {
    dragging.current = true
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const frac = (e.clientY - rect.top) / rect.height
    setTopFrac(Math.min(0.85, Math.max(0.15, frac)))
  }
  const onPointerUp = (e: React.PointerEvent) => {
    dragging.current = false
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch {
      // capture may already be released
    }
  }

  // --- Row selection handlers ---
  const toggleRow = (query: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(query)) next.delete(query)
      else next.add(query)
      return next
    })
  }

  const headerCheckState: 'all' | 'none' | 'partial' = useMemo(() => {
    if (selected.size === 0) return 'none'
    const allSelected = sorted.every((r) => selected.has(r.v.query))
    return allSelected ? 'all' : 'partial'
  }, [selected, sorted])

  const toggleAll = () => {
    if (headerCheckState === 'all') {
      setSelected(new Set())
    } else {
      setSelected(new Set(sorted.map((r) => r.v.query)))
    }
  }

  // Drag-to-select: row-level handlers. anchorIdx is stored on mousedown.
  const onRowMouseDown = (e: React.MouseEvent, sortedIdx: number, query: string) => {
    // Ignore clicks on checkbox or report link.
    const target = e.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'A' || target.closest('a')) return
    isDragging.current = true
    dragAnchorIdx.current = sortedIdx
    setDragActive(true)
    // Replace selection with just this row on mousedown.
    setSelected(new Set([query]))
  }

  const onRowMouseEnter = (sortedIdx: number) => {
    if (!isDragging.current || dragAnchorIdx.current === null) return
    const anchor = dragAnchorIdx.current
    const lo = Math.min(anchor, sortedIdx)
    const hi = Math.max(anchor, sortedIdx)
    const range = new Set(sorted.slice(lo, hi + 1).map((r) => r.v.query))
    setSelected(range)
  }

  // End drag on window mouseup.
  useEffect(() => {
    const end = () => {
      isDragging.current = false
      setDragActive(false)
    }
    window.addEventListener('mouseup', end)
    return () => window.removeEventListener('mouseup', end)
  }, [])

  // --- Save action ---
  const handleSave = () => {
    const toSave = sorted.filter((r) => selected.has(r.v.query)).map((r) => r.v)
    const added = saveVariants(toSave)
    setSelected(new Set())
    setSaveFlash(added)
    setTimeout(() => setSaveFlash(null), 1500)
  }

  // Shared table props.
  const tableProps = {
    rows: sorted,
    membership,
    sort,
    onSort,
    selected,
    onToggleRow: toggleRow,
    headerCheckState,
    onToggleAll: toggleAll,
    onRowMouseDown,
    onRowMouseEnter,
    dragActive,
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        {saveFlash !== null ? (
          <span
            style={{
              fontSize: 11.5,
              fontWeight: 600,
              color: 'var(--teal-deep)',
              padding: '5px 11px',
              borderRadius: 8,
              border: '0.5px solid var(--teal-bdr)',
              background: 'var(--teal-tint)',
            }}
          >
            ✓ Saved {saveFlash} to library
          </span>
        ) : selected.size > 0 ? (
          <button
            type="button"
            onClick={handleSave}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 11px',
              borderRadius: 8,
              border: '0.5px solid var(--teal-bdr)',
              background: 'var(--teal-tint)',
              color: 'var(--teal-deep)',
              fontSize: 11.5,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Save selected ({selected.size}) →
          </button>
        ) : null}
        <CopyButton text={payload} label="Copy table for spreadsheet" />
        {rows.length >= 2 && (
          <button
            type="button"
            aria-pressed={split}
            onClick={() => setSplit((s) => !s)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 11px',
              borderRadius: 8,
              border: `0.5px solid ${split ? 'var(--teal-bdr)' : 'var(--line-2)'}`,
              background: split ? 'var(--teal-tint)' : 'var(--bg)',
              color: split ? 'var(--teal-deep)' : 'var(--ink-2)',
              fontSize: 11.5,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <span aria-hidden>⊟</span> {split ? 'Single view' : 'Split view'}
          </button>
        )}
      </div>

      {split ? (
        <div
          ref={containerRef}
          style={{
            height: PANE_HEIGHT,
            display: 'flex',
            flexDirection: 'column',
            border: '0.5px solid var(--line)',
            borderRadius: 14,
            overflow: 'hidden',
          }}
        >
          <div style={{ flex: `${topFrac} 1 0`, overflow: 'auto', minHeight: 0 }}>
            <Table {...tableProps} />
          </div>
          <div
            role="separator"
            aria-orientation="horizontal"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            style={{
              height: 12,
              flexShrink: 0,
              cursor: 'row-resize',
              background: 'var(--bg-soft2)',
              borderTop: '0.5px solid var(--line)',
              borderBottom: '0.5px solid var(--line)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              touchAction: 'none',
            }}
          >
            <span aria-hidden style={{ width: 34, height: 3, borderRadius: 2, background: 'var(--ink-5)' }} />
          </div>
          <div style={{ flex: `${1 - topFrac} 1 0`, overflow: 'auto', minHeight: 0 }}>
            <Table {...tableProps} />
          </div>
        </div>
      ) : (
        <div
          style={{
            maxHeight: PANE_HEIGHT,
            overflow: 'auto',
            border: '0.5px solid var(--line)',
            borderRadius: 14,
          }}
        >
          <Table {...tableProps} />
        </div>
      )}
    </div>
  )
}

type TableProps = {
  rows: IndexedRow[]
  membership: PanelMembership[]
  sort: SortState | null
  onSort: (key: SortKey) => void
  selected: Set<string>
  onToggleRow: (query: string) => void
  headerCheckState: 'all' | 'none' | 'partial'
  onToggleAll: () => void
  onRowMouseDown: (e: React.MouseEvent, sortedIdx: number, query: string) => void
  onRowMouseEnter: (sortedIdx: number) => void
  dragActive: boolean
}

function Table({
  rows,
  membership,
  sort,
  onSort,
  selected,
  onToggleRow,
  headerCheckState,
  onToggleAll,
  onRowMouseDown,
  onRowMouseEnter,
  dragActive,
}: TableProps) {
  return (
    <table
      style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: 13,
        userSelect: dragActive ? 'none' : undefined,
      }}
    >
      <thead>
        <tr>
          <Th style={{ width: 36, padding: '10px 8px 10px 14px' }}>
            <input
              type="checkbox"
              aria-label="Select all rows"
              checked={headerCheckState === 'all'}
              ref={(el) => {
                if (el) el.indeterminate = headerCheckState === 'partial'
              }}
              onChange={onToggleAll}
              style={{ cursor: 'pointer', accentColor: 'var(--teal-deep)' }}
            />
          </Th>
          <SortTh col="idx" label="#" sort={sort} onSort={onSort} style={{ width: 44, textAlign: 'right' }} />
          <SortTh col="gene" label="Gene" sort={sort} onSort={onSort} />
          <SortTh col="variant" label="Variant" sort={sort} onSort={onSort} />
          <Th>Source line</Th>
          <Th style={{ textAlign: 'right' }}>Report</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ v, n }, sortedIdx) => {
          const href = withFromCompare(reportHrefForQuery(v.query))
          const isSelected = selected.has(v.query)
          return (
            <tr
              key={`${v.query}-${n}`}
              onMouseDown={(e) => onRowMouseDown(e, sortedIdx, v.query)}
              onMouseEnter={() => onRowMouseEnter(sortedIdx)}
              style={{
                borderTop: '0.5px solid var(--line)',
                background: isSelected ? 'var(--teal-tint)' : undefined,
                position: 'relative',
                cursor: 'default',
              }}
            >
              {isSelected && (
                <td
                  aria-hidden
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: 3,
                    background: 'var(--teal-deep)',
                    padding: 0,
                    border: 'none',
                  }}
                />
              )}
              <Td style={{ padding: '10px 8px 10px 14px' }}>
                <input
                  type="checkbox"
                  aria-label={`Select ${v.gene ?? v.query}`}
                  checked={isSelected}
                  onChange={() => onToggleRow(v.query)}
                  style={{ cursor: 'pointer', accentColor: 'var(--teal-deep)' }}
                />
              </Td>
              <Td style={{ textAlign: 'right', color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>{n}</Td>
              <Td style={{ fontWeight: 600, color: 'var(--ink)' }}>
                <span style={{ display: 'inline-flex', flexWrap: 'wrap', alignItems: 'center', gap: 5 }}>
                  <span>{v.gene ?? '—'}</span>
                  {v.gene
                    ? membership
                        .filter((m) => m.symbols.has((v.gene as string).toUpperCase()))
                        .map((m) => <PanelTag key={m.slug} badge={m.badge} />)
                    : null}
                </span>
              </Td>
              <Td style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>{v.variant ?? v.query}</Td>
              <Td style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>{v.raw}</Td>
              <Td style={{ textAlign: 'right' }}>
                {href ? (
                  <Link href={href} style={{ fontSize: 12, fontWeight: 600, color: 'var(--teal-deep)', textDecoration: 'none' }}>
                    Open report →
                  </Link>
                ) : (
                  <span style={{ fontSize: 12, color: 'var(--ink-5)' }}>—</span>
                )}
              </Td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Th({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <th
      scope="col"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 1,
        textAlign: 'left',
        padding: '10px 14px',
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        color: 'var(--ink-4)',
        background: 'var(--bg-soft)',
        ...style,
      }}
    >
      {children}
    </th>
  )
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ padding: '10px 14px', verticalAlign: 'top', ...style }}>{children}</td>
}

/** A sortable column header: a full-cell button that toggles asc/desc and
 *  shows a paired up/down arrow indicator. */
function SortTh({
  col,
  label,
  sort,
  onSort,
  style,
}: {
  col: SortKey
  label: string
  sort: SortState | null
  onSort: (key: SortKey) => void
  style?: React.CSSProperties
}) {
  const active = sort?.key === col
  const dir = active ? (sort as SortState).dir : null
  const alignRight = style?.textAlign === 'right'
  return (
    <Th style={{ ...style, padding: 0 }}>
      <button
        type="button"
        onClick={() => onSort(col)}
        aria-label={`Sort by ${label}${active ? (dir === 'asc' ? ' (ascending)' : ' (descending)') : ''}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          width: '100%',
          justifyContent: alignRight ? 'flex-end' : 'flex-start',
          padding: '10px 14px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          font: 'inherit',
          color: active ? 'var(--ink-2)' : 'inherit',
          letterSpacing: 'inherit',
          textTransform: 'inherit',
        }}
      >
        {label}
        <SortArrow dir={dir} />
      </button>
    </Th>
  )
}

function SortArrow({ dir }: { dir: 'asc' | 'desc' | null }) {
  return (
    <span
      aria-hidden
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        lineHeight: 0.62,
        fontSize: 8,
        color: dir ? 'var(--teal-deep)' : 'var(--ink-5)',
      }}
    >
      <span style={{ opacity: !dir || dir === 'asc' ? 1 : 0.3 }}>▲</span>
      <span style={{ opacity: !dir || dir === 'desc' ? 1 : 0.3 }}>▼</span>
    </span>
  )
}

function PanelTag({ badge }: { badge: PanelBadge }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '0.5px 6px',
        borderRadius: 5,
        fontFamily: 'var(--sans, inherit)',
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '0.01em',
        lineHeight: 1.5,
        background: badge.bg,
        color: badge.text,
        border: `0.5px solid ${badge.border}`,
      }}
    >
      {badge.short}
    </span>
  )
}
