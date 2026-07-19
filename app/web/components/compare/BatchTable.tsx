'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { reportHrefForQuery } from '@/lib/variant-search'
import type { ParsedVariant } from '@/lib/variant-file'
import type { BatchResult, Panel } from '@/lib/backend'
import { panelBadge, type PanelBadge } from '@/lib/panels.mock'
import { CopyButton } from '@/components/ui/CopyButton'
import { saveVariants } from '@/lib/variant-library'
import { CLASS_RANK, classifyVerdict } from '@/lib/batch-summary'
import { CohortSummary } from './CohortSummary'

/**
 * The Batch cohort table — one table for both states on /compare. Before a run
 * it shows the parsed cohort (preview); after a server run the same table fills
 * in ClinVar / ACMG / gnomAD AF and the AF filter lights up. It carries the
 * Excel-style split-pane (a draggable divider to compare row 5 against row 950),
 * column sort, drag-to-select + save-to-library, a spreadsheet copy, and a TSV
 * download, with the cohort summary pinned on top. Both states feed it a single
 * normalized BatchRow, so the experience never diverges.
 */
const PANE_HEIGHT = 560

/** Normalized row — the parsed-preview and server-annotated states both map to
 *  this shape so the table renders identically in either. */
export interface BatchRow {
  /** 1-based original cohort position; travels with the row when sorted. */
  n: number
  /** Stable id for selection (the query, or the server variant_key). */
  key: string
  /** Freeform query for the report link. */
  query: string
  gene: string | null
  /** HGVS (c.) when annotated, else the parsed variant / variant_key. */
  label: string
  /** Source line (VCF row / pasted text) — hover provenance. */
  raw: string
  clinvar: string | null
  acmg: string | null
  gnomadAf: number | null
  reportHref: string | null
  workbenchHref: string | null
}

function withFromCompare(href: string | null): string | null {
  if (!href) return null
  return href.includes('?') ? `${href}&from=compare` : `${href}?from=compare`
}

/** Parsed-cohort preview row → BatchRow (no annotations yet). */
export function rowFromParsed(v: ParsedVariant, i: number): BatchRow {
  return {
    n: i + 1,
    key: v.query,
    query: v.query,
    gene: v.gene ?? null,
    label: v.variant ?? v.query,
    raw: v.raw ?? v.query,
    clinvar: null,
    acmg: null,
    gnomadAf: null,
    reportHref: withFromCompare(reportHrefForQuery(v.query)),
    workbenchHref: null,
  }
}

/** Server-annotated result row → BatchRow. */
export function rowFromResult(r: BatchResult, i: number): BatchRow {
  const query = r.hgvs_c && r.gene ? `${r.gene} ${r.hgvs_c}` : r.variant_key
  return {
    n: i + 1,
    key: r.variant_key,
    query,
    gene: r.gene ?? null,
    label: r.hgvs_c ?? r.variant_key,
    raw: r.variant_key,
    clinvar: r.clinvar_verdict ?? null,
    acmg: r.acmg_classification ?? null,
    gnomadAf: r.gnomad_af ?? null,
    reportHref: withFromCompare(r.report_href ?? reportHrefForQuery(query)),
    workbenchHref:
      r.gene && r.hgvs_c
        ? `/workbench?${new URLSearchParams({ gene: r.gene, cdna: r.hgvs_c, tool: 'viewer' }).toString()}`
        : null,
  }
}

type PanelMembership = { slug: string; badge: PanelBadge; symbols: Set<string> }
type SortKey = 'idx' | 'gene' | 'variant' | 'clinical'
type SortState = { key: SortKey; dir: 'asc' | 'desc' }

const AF_OPTIONS: { label: string; value: number | null }[] = [
  { label: 'All', value: null },
  { label: '≤ 5%', value: 0.05 },
  { label: '≤ 1%', value: 0.01 },
  { label: '≤ 0.1%', value: 0.001 },
]

/** Sort key for the Variant column: genomic position for VCF rows
 *  (chrom-POS-ref-alt), else the first number in the HGVS string (c.247 → 247). */
function variantPos(r: BatchRow): number {
  const genomic = /^(?:chr)?\w+-(\d+)-/i.exec(r.query ?? '')
  if (genomic) return Number(genomic[1])
  const m = /(\d+)/.exec(r.label ?? r.query ?? '')
  return m ? Number(m[1]) : Number.POSITIVE_INFINITY
}

function clinicalRank(r: BatchRow): number {
  return CLASS_RANK[classifyVerdict(r.acmg, r.clinvar)]
}

function sortRows(rows: BatchRow[], sort: SortState | null): BatchRow[] {
  if (!sort) return rows
  const dir = sort.dir === 'asc' ? 1 : -1
  const out = rows.slice()
  out.sort((a, b) => {
    let cmp = 0
    if (sort.key === 'gene') {
      const ga = (a.gene ?? '').toUpperCase()
      const gb = (b.gene ?? '').toUpperCase()
      if (!ga && gb) return 1
      if (ga && !gb) return -1
      cmp = ga.localeCompare(gb)
    } else if (sort.key === 'variant') {
      cmp = variantPos(a) - variantPos(b)
    } else if (sort.key === 'clinical') {
      cmp = clinicalRank(a) - clinicalRank(b)
    } else {
      cmp = a.n - b.n
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
function tableText(rows: BatchRow[], annotated: boolean): { html: string; text: string } {
  const headers = annotated
    ? ['#', 'Gene', 'Variant', 'ClinVar', 'ACMG', 'gnomAD AF', 'Source']
    : ['#', 'Gene', 'Variant', 'Source line']
  const cells = rows.map((r) =>
    annotated
      ? [String(r.n), r.gene ?? '', r.label, r.clinvar ?? '', r.acmg ?? '', r.gnomadAf == null ? '' : String(r.gnomadAf), r.raw]
      : [String(r.n), r.gene ?? '', r.label, r.raw],
  )
  const text = [headers, ...cells].map((row) => row.join('\t')).join('\n')
  const thead = `<tr>${headers.map((h) => `<th>${escHtml(h)}</th>`).join('')}</tr>`
  const tbody = cells.map((row) => `<tr>${row.map((c) => `<td>${escHtml(c)}</td>`).join('')}</tr>`).join('')
  return { html: `<table><thead>${thead}</thead><tbody>${tbody}</tbody></table>`, text }
}

function downloadTsv(rows: BatchRow[], annotated: boolean): void {
  const { text } = tableText(rows, annotated)
  const blob = new Blob([text], { type: 'text/tab-separated-values;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `eamos-batch-${rows.length}-variants.tsv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function BatchTable({
  rows,
  annotated,
  activePanels,
  panelGenes,
  panelLabel,
}: {
  rows: BatchRow[]
  /** True once the server has annotated the cohort (ClinVar/ACMG/AF columns + filter). */
  annotated: boolean
  activePanels: Panel[]
  /** Active panel gene symbols (union) → panel-coverage card. */
  panelGenes?: string[]
  panelLabel?: string
}) {
  const router = useRouter()
  const searchParams = useSearchParams()
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
  const [compareOpen, setCompareOpen] = useState(() => searchParams.get('view') === 'compare')
  // Default sort: actionable-first (P/LP pinned) once annotated, else cohort order.
  const [sort, setSort] = useState<SortState | null>(annotated ? { key: 'clinical', dir: 'asc' } : null)
  const [afMax, setAfMax] = useState<number | null>(null)
  const [topFrac, setTopFrac] = useState(0.5)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  // When the cohort gets annotated (results arrive), pin actionable-first once —
  // adjust during render rather than in an effect (react.dev "you might not need
  // an effect"). Clear selection + AF filter on any row-set change.
  const [prevAnnotated, setPrevAnnotated] = useState(annotated)
  const [prevRows, setPrevRows] = useState(rows)
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  if (annotated !== prevAnnotated) {
    setPrevAnnotated(annotated)
    if (annotated) setSort({ key: 'clinical', dir: 'asc' })
  }
  if (rows !== prevRows) {
    setPrevRows(rows)
    setSelected(new Set())
    setAfMax(null)
  }

  const summary = useMemo(
    () =>
      // CohortSummary reads variant_key / gene / acmg / clinvar — map each row.
      summarizeRows(rows, panelGenes),
    [rows, panelGenes],
  )
  const sorted = useMemo(() => sortRows(rows, sort), [rows, sort])
  const visible = useMemo(
    () => (afMax == null ? sorted : sorted.filter((r) => r.gnomadAf == null || r.gnomadAf <= afMax)),
    [sorted, afMax],
  )
  const hidden = sorted.length - visible.length
  const payload = useMemo(() => tableText(visible, annotated), [visible, annotated])

  const [saveFlash, setSaveFlash] = useState<number | null>(null)
  const dragAnchorIdx = useRef<number | null>(null)
  const isDragging = useRef(false)
  const [dragActive, setDragActive] = useState(false)

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
  const onSeparatorKeyDown = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 0.1 : 0.05
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setTopFrac((value) => Math.max(0.15, value - step))
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setTopFrac((value) => Math.min(0.85, value + step))
    } else if (e.key === 'Home') {
      e.preventDefault()
      setTopFrac(0.15)
    } else if (e.key === 'End') {
      e.preventDefault()
      setTopFrac(0.85)
    }
  }

  const toggleRow = (key: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })

  const headerCheckState: 'all' | 'none' | 'partial' = useMemo(() => {
    if (selected.size === 0) return 'none'
    return visible.every((r) => selected.has(r.key)) ? 'all' : 'partial'
  }, [selected, visible])

  const toggleAll = () =>
    setSelected(headerCheckState === 'all' ? new Set() : new Set(visible.map((r) => r.key)))

  const onRowMouseDown = (e: React.MouseEvent, idx: number, key: string) => {
    const target = e.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'A' || target.closest('a')) return
    isDragging.current = true
    dragAnchorIdx.current = idx
    setDragActive(true)
    setSelected(new Set([key]))
  }

  const onRowMouseEnter = (idx: number) => {
    if (!isDragging.current || dragAnchorIdx.current === null) return
    const lo = Math.min(dragAnchorIdx.current, idx)
    const hi = Math.max(dragAnchorIdx.current, idx)
    setSelected(new Set(visible.slice(lo, hi + 1).map((r) => r.key)))
  }

  useEffect(() => {
    const end = () => {
      isDragging.current = false
      setDragActive(false)
    }
    window.addEventListener('mouseup', end)
    return () => window.removeEventListener('mouseup', end)
  }, [])

  const handleSave = () => {
    const toSave = visible
      .filter((r) => selected.has(r.key))
      .map((r) => ({ raw: r.raw, gene: r.gene, variant: r.label, query: r.query }))
    const added = saveVariants(toSave)
    setSelected(new Set())
    setSaveFlash(added)
    setTimeout(() => setSaveFlash(null), 1500)
  }

  const selectedRows = visible.filter((row) => selected.has(row.key))
  const canCompare = selectedRows.length >= 2 && selectedRows.length <= 3
  const setComparisonOpen = (open: boolean) => {
    setCompareOpen(open)
    const params = new URLSearchParams(searchParams.toString())
    params.set('view', open ? 'compare' : 'cohort')
    router.replace(`/compare?${params.toString()}`, { scroll: false })
  }

  const tableProps = {
    rows: visible,
    membership,
    annotated,
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
      <CohortSummary summary={summary} panelLabel={panelLabel} />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
            {hidden > 0 ? `${visible.length} of ${sorted.length}` : `${sorted.length}`}
            {annotated ? ' annotated · server-computed' : ' variants · preview'}
          </span>
          {annotated && (
            <>
              <span aria-hidden style={{ color: 'var(--line-2)' }}>·</span>
              <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>gnomAD AF</span>
              <div role="group" aria-label="Filter by gnomAD allele frequency" style={{ display: 'inline-flex', gap: 4 }}>
                {AF_OPTIONS.map((opt) => {
                  const active = afMax === opt.value
                  return (
                    <button
                      key={opt.label}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setAfMax(opt.value)}
                      style={{
                        padding: '3px 9px',
                        borderRadius: 7,
                        border: `0.5px solid ${active ? 'var(--teal-bdr)' : 'var(--line-2)'}`,
                        background: active ? 'var(--teal-tint)' : 'var(--bg)',
                        color: active ? 'var(--teal-deep)' : 'var(--ink-3)',
                        fontSize: 11,
                        fontWeight: 600,
                        fontFamily: 'var(--mono)',
                        cursor: 'pointer',
                      }}
                    >
                      {opt.label}
                    </button>
                  )
                })}
              </div>
            </>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
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
            <span className="flex flex-wrap items-center gap-2">
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
              <button
                type="button"
                disabled={!canCompare}
                title={canCompare ? 'Compare selected variants' : 'Select 2 or 3 variants to compare'}
                onClick={() => setComparisonOpen(true)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '5px 11px',
                  borderRadius: 8,
                  border: '0.5px solid var(--line-2)',
                  background: 'var(--bg)',
                  color: 'var(--ink-2)',
                  fontSize: 11.5,
                  fontWeight: 600,
                  cursor: canCompare ? 'pointer' : 'not-allowed',
                  opacity: canCompare ? 1 : 0.5,
                }}
              >
                Compare {selected.size}
              </button>
            </span>
          ) : null}
          <CopyButton text={payload} label="Copy table for spreadsheet" />
          <button
            type="button"
            onClick={() => downloadTsv(visible, annotated)}
            disabled={visible.length === 0}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 11px',
              borderRadius: 8,
              border: '0.5px solid var(--line-2)',
              background: 'var(--bg)',
              color: 'var(--ink-2)',
              fontSize: 11.5,
              fontWeight: 600,
              cursor: visible.length === 0 ? 'not-allowed' : 'pointer',
              opacity: visible.length === 0 ? 0.5 : 1,
            }}
          >
            <span aria-hidden>↓</span> TSV
          </button>
          {sorted.length >= 2 && (
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
      </div>

      {compareOpen && canCompare && (
        <VariantComparison rows={selectedRows} onClose={() => setComparisonOpen(false)} />
      )}
      {compareOpen && !canCompare && (
        <section
          className="mb-4 flex flex-wrap items-center justify-between gap-3"
          role="status"
          style={{ border: '0.5px solid var(--teal-bdr)', borderRadius: 10, background: 'var(--teal-tint)', padding: '10px 12px', color: 'var(--ink-2)', fontSize: 12 }}
        >
          <span>Select 2 or 3 rows to open the typed comparison view.</span>
          <button type="button" onClick={() => setComparisonOpen(false)} style={{ minHeight: 36, padding: '5px 10px', borderRadius: 7, border: '0.5px solid var(--line)', background: 'var(--bg)', color: 'var(--ink-2)', cursor: 'pointer' }}>
            Return to cohort
          </button>
        </section>
      )}

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
            aria-label="Resize Batch comparison panes"
            aria-valuemin={15}
            aria-valuemax={85}
            aria-valuenow={Math.round(topFrac * 100)}
            aria-valuetext={`Top pane ${Math.round(topFrac * 100)} percent`}
            tabIndex={0}
            className="cmp-separator"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            onKeyDown={onSeparatorKeyDown}
            style={{
              height: 16,
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
        <div style={{ maxHeight: PANE_HEIGHT, overflow: 'auto', border: '0.5px solid var(--line)', borderRadius: 14 }}>
          <Table {...tableProps} />
        </div>
      )}
    </div>
  )
}

/** Map BatchRows onto the cohort-summary input (variant-shape from `key`,
 *  classification from acmg/clinvar). */
function summarizeRows(rows: BatchRow[], panelGenes?: string[]) {
  return summarizeCohortLocal(
    rows.map((r) => ({ variant_key: r.key, gene: r.gene, acmg_classification: r.acmg, clinvar_verdict: r.clinvar })),
    panelGenes,
  )
}

// Re-export through a thin local alias so the import stays a single line above.
import { summarizeCohort as summarizeCohortLocal } from '@/lib/batch-summary'

function VariantComparison({ rows, onClose }: { rows: BatchRow[]; onClose: () => void }) {
  const fields: Array<{ label: string; value: (row: BatchRow) => React.ReactNode }> = [
    { label: 'Gene', value: (row) => row.gene ?? <MissingValue /> },
    { label: 'Variant', value: (row) => row.label || <MissingValue /> },
    { label: 'ClinVar', value: (row) => row.clinvar ?? <MissingValue /> },
    { label: 'ACMG', value: (row) => row.acmg ?? <MissingValue /> },
    {
      label: 'gnomAD AF',
      value: (row) => row.gnomadAf == null ? <MissingValue /> : formatAf(row.gnomadAf),
    },
    {
      label: 'Actions',
      value: (row) => (
        <span className="flex flex-wrap gap-2">
          {row.reportHref && <Link href={row.reportHref}>Report</Link>}
          {row.workbenchHref && <Link href={row.workbenchHref}>Workbench</Link>}
        </span>
      ),
    },
  ]
  return (
    <section
      className="mb-4"
      aria-labelledby="batch-variant-comparison-title"
      style={{ border: '0.5px solid var(--teal-bdr)', borderRadius: 12, background: 'var(--bg)', padding: '14px 16px' }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id="batch-variant-comparison-title" style={{ margin: 0, fontSize: 14, fontWeight: 650, color: 'var(--ink)' }}>
            Variant comparison
          </h3>
          <p style={{ margin: '3px 0 0', fontSize: 11.5, color: 'var(--ink-4)' }}>
            Typed Batch facts only. Missing source values stay unavailable.
          </p>
        </div>
        <button type="button" onClick={onClose} style={{ padding: '5px 10px', borderRadius: 8, border: '0.5px solid var(--line-2)', background: 'var(--bg)', color: 'var(--ink-2)', fontSize: 11.5, fontWeight: 600, cursor: 'pointer' }}>
          Close comparison
        </button>
      </div>
      <div style={{ overflowX: 'auto', marginTop: 12 }}>
        <table style={{ minWidth: 520, width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <th scope="col" style={{ textAlign: 'left', padding: '8px 10px', color: 'var(--ink-4)' }}>Field</th>
              {rows.map((row) => (
                <th key={row.key} scope="col" style={{ textAlign: 'left', padding: '8px 10px', color: 'var(--ink)' }}>
                  {row.gene ?? 'Variant'} · {row.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.label} style={{ borderTop: '0.5px solid var(--line)' }}>
                <th scope="row" style={{ textAlign: 'left', padding: '8px 10px', color: 'var(--ink-4)', fontWeight: 600 }}>
                  {field.label}
                </th>
                {rows.map((row) => (
                  <td key={row.key} style={{ padding: '8px 10px', color: 'var(--ink-2)', verticalAlign: 'top' }}>
                    {field.value(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function MissingValue() {
  return <span style={{ color: 'var(--ink-4)' }}>Unavailable</span>
}

type TableProps = {
  rows: BatchRow[]
  membership: PanelMembership[]
  annotated: boolean
  sort: SortState | null
  onSort: (key: SortKey) => void
  selected: Set<string>
  onToggleRow: (key: string) => void
  headerCheckState: 'all' | 'none' | 'partial'
  onToggleAll: () => void
  onRowMouseDown: (e: React.MouseEvent, idx: number, key: string) => void
  onRowMouseEnter: (idx: number) => void
  dragActive: boolean
}

function Table({
  rows,
  membership,
  annotated,
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
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, userSelect: dragActive ? 'none' : undefined }}>
      <thead>
        <tr>
          <Th style={{ width: 36, padding: '10px 8px 10px 14px' }}>
            <input
              type="checkbox"
              name="batch-select-all"
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
          {annotated && <SortTh col="clinical" label="ClinVar / ACMG" sort={sort} onSort={onSort} />}
          {annotated && <Th style={{ textAlign: 'right' }}>gnomAD AF</Th>}
          <Th style={{ textAlign: 'right' }}>Actions</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, idx) => {
          const isSelected = selected.has(r.key)
          return (
            <tr
              key={`${r.key}-${r.n}`}
              onMouseDown={(e) => onRowMouseDown(e, idx, r.key)}
              onMouseEnter={() => onRowMouseEnter(idx)}
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
                  style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: 'var(--teal-deep)', padding: 0, border: 'none' }}
                />
              )}
              <Td style={{ padding: '10px 8px 10px 14px' }}>
                <input
                  type="checkbox"
                  name={`batch-row-${r.n}`}
                  aria-label={`Select ${r.gene ?? r.query}`}
                  checked={isSelected}
                  onChange={() => onToggleRow(r.key)}
                  style={{ cursor: 'pointer', accentColor: 'var(--teal-deep)' }}
                />
              </Td>
              <Td style={{ textAlign: 'right', color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>{r.n}</Td>
              <Td style={{ fontWeight: 600, color: 'var(--ink)' }}>
                <span style={{ display: 'inline-flex', flexWrap: 'wrap', alignItems: 'center', gap: 5 }}>
                  <span>{r.gene ?? '—'}</span>
                  {r.gene
                    ? membership
                        .filter((m) => m.symbols.has((r.gene as string).toUpperCase()))
                        .map((m) => <PanelTag key={m.slug} badge={m.badge} />)
                    : null}
                </span>
              </Td>
              <Td
                title={r.raw !== r.label ? r.raw : undefined}
                style={{ fontFamily: 'var(--mono)', fontSize: 12, fontVariantNumeric: 'tabular-nums', color: 'var(--ink-2)' }}
              >
                {r.label}
              </Td>
              {annotated && (
                <Td>
                  <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 1 }}>
                    <Verdict value={r.clinvar} muted />
                    <Verdict value={r.acmg} />
                  </span>
                </Td>
              )}
              {annotated && (
                <Td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-2)' }}>
                  {r.gnomadAf == null ? <span style={{ color: 'var(--ink-5)' }}>—</span> : formatAf(r.gnomadAf)}
                </Td>
              )}
              <Td style={{ textAlign: 'right' }}>
                {r.reportHref || r.workbenchHref ? (
                  <span className="flex flex-wrap justify-end gap-2">
                    {r.reportHref && (
                      <Link href={r.reportHref} style={{ fontSize: 12, fontWeight: 600, color: 'var(--teal-deep)', textDecoration: 'none' }}>
                        Report
                      </Link>
                    )}
                    {r.workbenchHref && (
                      <Link href={r.workbenchHref} style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-2)', textDecoration: 'none' }}>
                        Workbench
                      </Link>
                    )}
                  </span>
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

function verdictColor(v?: string | null): string {
  const s = (v ?? '').toLowerCase()
  if (!s) return 'var(--ink-5)'
  if (s.includes('conflict') || s.includes('uncertain') || s.includes('vus')) return 'var(--ink-3)'
  if (s.includes('likely pathogenic')) return 'var(--warn)'
  if (s.includes('pathogenic')) return 'var(--err)'
  if (s.includes('benign')) return 'var(--teal-deep)'
  return 'var(--ink-2)'
}

function Verdict({ value, muted = false }: { value: string | null; muted?: boolean }) {
  if (!value) return <span style={{ fontSize: muted ? 10.5 : 12, color: 'var(--ink-5)' }}>—</span>
  return (
    <span style={{ fontSize: muted ? 10.5 : 12, fontWeight: muted ? 400 : 600, color: verdictColor(value) }}>{value}</span>
  )
}

function formatAf(af: number): string {
  if (af === 0) return '0'
  if (af < 0.0001) return af.toExponential(1)
  return `${(af * 100).toFixed(af < 0.01 ? 3 : 2)}%`
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

function Td({ children, style, title }: { children: React.ReactNode; style?: React.CSSProperties; title?: string }) {
  return (
    <td title={title} style={{ padding: '10px 14px', verticalAlign: 'top', ...style }}>
      {children}
    </td>
  )
}

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
    <span aria-hidden style={{ display: 'inline-flex', flexDirection: 'column', lineHeight: 0.62, fontSize: 8, color: dir ? 'var(--teal-deep)' : 'var(--ink-5)' }}>
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
