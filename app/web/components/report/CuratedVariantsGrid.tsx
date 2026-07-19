'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import type {
  ClassificationTier,
  ConsequenceBucketV1,
  CuratedVariantPageV1,
  CuratedVariantsDistribution,
} from '@/lib/backend'
import { buildReportHrefV1, buildWorkbenchHrefV1 } from '@/lib/backend'
import { useLibrary } from '@/components/library/useLibrary'
import {
  getCuratedVariants,
  saveCanonicalVariant,
  sendCanonicalVariantToBatch,
  stashPaperTarget,
} from '@/lib/report-workflow'

type RowKind = 'p' | 'vus' | 'b'

interface DistCell {
  key: string
  value: number
  heat?: string
  isQuery: boolean
  classification: ClassificationTier
  consequence: ConsequenceBucketV1
}

interface DistRow {
  kind: RowKind
  label: string
  cells: DistCell[]
  total: number
}

interface CuratedVariantsGridProps {
  data?: CuratedVariantsDistribution | null
  gene?: string | null
}

const ROW_DEFS: Array<{
  kind: RowKind
  label: string
  prefix: string
  classification: ClassificationTier
  heatPrefix: string
  levels: number
}> = [
  { kind: 'p', label: 'Pathogenic', prefix: 'pathogenic', classification: 'pathogenic', heatPrefix: 'heat', levels: 3 },
  { kind: 'vus', label: 'VUS', prefix: 'vus', classification: 'vus', heatPrefix: 'heat-v', levels: 2 },
  { kind: 'b', label: 'Benign', prefix: 'benign', classification: 'benign', heatPrefix: 'heat-b', levels: 3 },
]

const COL_SUFFIXES: ConsequenceBucketV1[] = ['lof', 'missense', 'noncoding', 'synonymous']
const COL_LABELS: Record<ConsequenceBucketV1, string> = {
  lof: 'LOF',
  missense: 'Missense + Indel',
  noncoding: 'Non-coding',
  synonymous: 'Synonymous',
}

function heatClass(value: number, max: number, heatPrefix: string, levels: number): string | undefined {
  if (value <= 0 || max <= 0) return undefined
  const ratio = value / max
  const tier = Math.min(levels, Math.max(1, Math.ceil(ratio * levels)))
  return `${heatPrefix}-${tier}`
}

function mapRows(
  cells: Record<string, number>,
  rowTotals: Record<string, number>,
  queryCell: string | null | undefined,
): DistRow[] {
  return ROW_DEFS.map(({ kind, label, prefix, classification, heatPrefix, levels }) => {
    const keyedValues = COL_SUFFIXES.map((consequence) => {
      const key = `${prefix}_${consequence}`
      return { key, value: cells[key] ?? 0, consequence }
    })
    const values = keyedValues.map((item) => item.value)
    const max = Math.max(...values)
    const total = rowTotals[prefix] ?? values.reduce((sum, value) => sum + value, 0)
    return {
      kind,
      label,
      cells: keyedValues.map(({ key, value, consequence }) => ({
        key,
        value,
        classification,
        consequence,
        heat: heatClass(value, max, heatPrefix, levels),
        isQuery: key === queryCell,
      })),
      total,
    }
  })
}

function queryBucketLabel(queryCell: string | null | undefined): string | null {
  if (!queryCell) return null
  for (const row of ROW_DEFS) {
    const prefix = `${row.prefix}_`
    if (!queryCell.startsWith(prefix)) continue
    const suffix = queryCell.slice(prefix.length) as ConsequenceBucketV1
    return `${row.label} / ${COL_LABELS[suffix] ?? suffix}`
  }
  return queryCell
}

export function CuratedVariantsGrid({ data, gene }: CuratedVariantsGridProps) {
  const router = useRouter()
  const { variants: savedVariants } = useLibrary()
  const [selectedCell, setSelectedCell] = useState<DistCell | null>(null)
  const [pages, setPages] = useState<CuratedVariantPageV1[]>([])
  const [pageIndex, setPageIndex] = useState(0)
  const [pageState, setPageState] = useState<'idle' | 'loading' | 'error'>('idle')

  if (!data) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
        No curated variants distribution available for this gene.
      </p>
    )
  }

  const rows = mapRows(data.cells, data.row_totals ?? {}, data.query_cell)
  const sub = data.subtitle || `${data.total.toLocaleString()} classified variants`
  const reading = data.reading
  const queryLabel = data.query_accession
    ? `${data.query_accession}${data.query_classification ? ` · ${data.query_classification}` : ''}`
    : 'Query variant'
  const queryBucket = queryBucketLabel(data.query_cell)
  const page = pages[pageIndex] ?? null

  const loadCell = async (cell: DistCell) => {
    if (!gene || cell.value <= 0) return
    setSelectedCell(cell)
    setPageState('loading')
    try {
      const result = await getCuratedVariants({
        gene,
        classification: cell.classification,
        consequence: cell.consequence,
        limit: 20,
      })
      setPages([result])
      setPageIndex(0)
      setPageState('idle')
    } catch {
      setPages([])
      setPageState('error')
    }
  }

  const loadNext = async () => {
    if (!selectedCell || !gene || !page?.next_cursor) return
    const cached = pages[pageIndex + 1]
    if (cached) {
      setPageIndex((index) => index + 1)
      return
    }
    setPageState('loading')
    try {
      const result = await getCuratedVariants({
        gene,
        classification: selectedCell.classification,
        consequence: selectedCell.consequence,
        cursor: page.next_cursor,
        limit: 20,
      })
      setPages((current) => [...current.slice(0, pageIndex + 1), result])
      setPageIndex((index) => index + 1)
      setPageState('idle')
    } catch {
      setPageState('error')
    }
  }

  return (
    <div className="vardist-wrap">
      <div className="vardist-title">
        Curated variants distribution
        <span className="vardist-sub">{sub}</span>
      </div>
      <div className="vardist">
        <div className="vd-cell col-header" style={{ textAlign: 'left' }}>Classification</div>
        {COL_SUFFIXES.map((suffix) => <div className="vd-cell col-header" key={suffix}>{COL_LABELS[suffix]}</div>)}
        <div className="vd-cell col-header">Total</div>

        {rows.map((row) => (
          <div key={row.kind} style={{ display: 'contents' }}>
            <div className={`vd-cell row-label ${row.kind}`}>
              <span className="ldot" />{row.label}
            </div>
            {row.cells.map((cell) => {
              const className = ['vd-cell', cell.heat, cell.isQuery ? 'query-hit' : null]
                .filter(Boolean)
                .join(' ')
              const title = cell.isQuery ? queryLabel : `${row.label}, ${COL_LABELS[cell.consequence]}`
              return cell.value > 0 && gene ? (
                <button
                  type="button"
                  key={cell.key}
                  className={`${className} vd-action`}
                  title={`${title}. Open ${cell.value} curated variant${cell.value === 1 ? '' : 's'}.`}
                  aria-label={`${row.label}, ${COL_LABELS[cell.consequence]}: ${cell.value}. Open curated variants.`}
                  aria-pressed={selectedCell?.key === cell.key}
                  onClick={() => void loadCell(cell)}
                >
                  {cell.value}
                  {cell.isQuery && <span className="vd-query-badge">Query</span>}
                </button>
              ) : (
                <div key={cell.key} className={className} title={cell.isQuery ? queryLabel : undefined}>
                  {cell.value}
                  {cell.isQuery && <span className="vd-query-badge">Query</span>}
                </div>
              )
            })}
            <div className="vd-cell total">{row.total}</div>
          </div>
        ))}
      </div>
      <div className="vardist-reading"><strong>Reading:</strong> {reading}</div>
      {queryBucket && (
        <div className="vardist-query-note"><strong>Query bucket:</strong> {queryLabel} maps to {queryBucket}.</div>
      )}

      {selectedCell && (
        <section className="curated-page" aria-label="Curated variants in selected distribution cell">
          <div className="curated-page-head">
            <div>
              <strong>{ROW_DEFS.find((row) => row.classification === selectedCell.classification)?.label}</strong>
              <span>{COL_LABELS[selectedCell.consequence]}</span>
            </div>
            {page && <span>{page.total.toLocaleString()} source-backed records</span>}
          </div>
          {pageState === 'loading' && <p role="status">Loading curated variants…</p>}
          {pageState === 'error' && <p role="alert">Curated variants are temporarily unavailable.</p>}
          {pageState !== 'loading' && page && page.items.length === 0 && <p>No records were returned for this cell.</p>}
          {page && page.items.length > 0 && (
            <div className="curated-list">
              {page.items.map((variant) => {
                const identity = `${variant.gene} ${variant.cdna}`.toLowerCase()
                const saved = savedVariants.some((candidate) => candidate.id === identity)
                return (
                  <article key={variant.variant_key} className="curated-row">
                    <div className="curated-identity">
                      <strong>{variant.gene}</strong>
                      <code>{variant.cdna}</code>
                      <span>{variant.transcript ?? 'Transcript unavailable'}</span>
                    </div>
                    <div className="curated-actions" aria-label={`Actions for ${variant.gene} ${variant.cdna}`}>
                      <Link href={buildReportHrefV1(variant, 'report')}>Report</Link>
                      <Link href={buildWorkbenchHrefV1(variant, { tool: 'viewer' })}>Workbench</Link>
                      <button type="button" onClick={() => { stashPaperTarget(variant); router.push('/paper') }}>Papers</button>
                      <button type="button" onClick={() => { sendCanonicalVariantToBatch(variant, 'Curated variants'); router.push('/compare') }}>Batch</button>
                      <button type="button" disabled={saved} onClick={() => saveCanonicalVariant(variant, selectedCell.classification)}>
                        {saved ? 'Saved' : 'Save'}
                      </button>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
          {page && (
            <div className="curated-pager">
              <button type="button" disabled={pageIndex === 0} onClick={() => setPageIndex((index) => index - 1)}>Previous</button>
              <span>Page {pageIndex + 1}</span>
              <button type="button" disabled={!page.next_cursor || pageState === 'loading'} onClick={() => void loadNext()}>Next</button>
            </div>
          )}
          {page && (
            <p className="curated-source">{page.source_disclosure.provider_label} · {page.source_disclosure.source_status}</p>
          )}
        </section>
      )}

      <style>{`
        .vd-action { min-height: 44px; border: 0; font: inherit; cursor: pointer; position: relative; }
        .vd-action:hover { box-shadow: inset 0 0 0 2px var(--teal); }
        .vd-action:focus-visible { outline: 3px solid var(--teal); outline-offset: -3px; z-index: 1; }
        .curated-page { margin-top: 14px; border: 0.5px solid var(--line); border-radius: var(--r-md); overflow: hidden; background: var(--bg); }
        .curated-page > p { margin: 0; padding: 14px; color: var(--ink-3); font-size: 12px; }
        .curated-page-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; background: var(--bg-soft); border-bottom: 0.5px solid var(--line); color: var(--ink-3); font-size: 11px; }
        .curated-page-head div { display: inline-flex; align-items: baseline; gap: 8px; }
        .curated-page-head strong { color: var(--ink); font-size: 12px; }
        .curated-list { display: grid; }
        .curated-row { display: grid; grid-template-columns: minmax(170px, 1fr) auto; gap: 12px; align-items: center; padding: 10px 12px; border-bottom: 0.5px solid var(--line); }
        .curated-identity { display: flex; flex-wrap: wrap; align-items: baseline; gap: 7px; min-width: 0; }
        .curated-identity strong { font-size: 12px; }
        .curated-identity code { color: var(--ink-2); font-size: 11.5px; }
        .curated-identity span { width: 100%; color: var(--ink-4); font-size: 10px; }
        .curated-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 4px; }
        .curated-actions a, .curated-actions button, .curated-pager button { min-height: 44px; padding: 5px 8px; border: 0.5px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--ink-3); font: 600 10.5px var(--body); text-decoration: none; cursor: pointer; }
        .curated-actions a:hover, .curated-actions button:hover:not(:disabled), .curated-pager button:hover:not(:disabled) { background: var(--bg-soft); color: var(--ink); }
        .curated-actions a:focus-visible, .curated-actions button:focus-visible, .curated-pager button:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }
        .curated-actions button:disabled, .curated-pager button:disabled { color: var(--ink-5); cursor: default; }
        .curated-pager { display: flex; align-items: center; justify-content: flex-end; gap: 8px; padding: 8px 12px; }
        .curated-pager span, .curated-source { color: var(--ink-4); font-size: 10.5px; }
        .curated-source { margin: 0; padding: 7px 12px; background: var(--bg-soft); border-top: 0.5px solid var(--line); }
        @media (max-width: 700px) {
          .curated-row { grid-template-columns: 1fr; }
          .curated-actions { justify-content: flex-start; }
          .curated-page-head { align-items: flex-start; flex-direction: column; }
        }
      `}</style>
    </div>
  )
}
