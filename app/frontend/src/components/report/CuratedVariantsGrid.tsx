import type { CuratedVariantsDistribution } from '@/lib/backend'

type RowKind = 'p' | 'vus' | 'b'

interface DistRow {
  kind: RowKind
  label: string
  cells: Array<{ key: string; value: number; heat?: string; isQuery: boolean }>
  total: number
}

interface CuratedVariantsGridProps {
  data?: CuratedVariantsDistribution | null
}

const ROW_DEFS: Array<{
  kind: RowKind
  label: string
  prefix: string
  heatPrefix: string
  levels: number
}> = [
  { kind: 'p',   label: 'Pathogenic', prefix: 'pathogenic', heatPrefix: 'heat',   levels: 3 },
  { kind: 'vus', label: 'VUS',        prefix: 'vus',        heatPrefix: 'heat-v', levels: 2 },
  { kind: 'b',   label: 'Benign',     prefix: 'benign',     heatPrefix: 'heat-b', levels: 3 },
]

const COL_SUFFIXES = ['lof', 'missense', 'noncoding', 'synonymous']
const COL_LABELS: Record<string, string> = {
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
  return ROW_DEFS.map(({ kind, label, prefix, heatPrefix, levels }) => {
    const keyedValues = COL_SUFFIXES.map((suffix) => {
      const key = `${prefix}_${suffix}`
      return { key, value: cells[key] ?? 0 }
    })
    const values = keyedValues.map((item) => item.value)
    const max = Math.max(...values)
    const total = rowTotals[prefix] ?? values.reduce((a, b) => a + b, 0)
    return {
      kind,
      label,
      cells: keyedValues.map(({ key, value }) => ({
        key,
        value,
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
    const suffix = queryCell.slice(prefix.length)
    return `${row.label} / ${COL_LABELS[suffix] ?? suffix}`
  }
  return queryCell
}

export function CuratedVariantsGrid({ data }: CuratedVariantsGridProps) {
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

  return (
    <div className="vardist-wrap">
      <div className="vardist-title">
        Curated variants distribution
        <span className="vardist-sub">{sub}</span>
      </div>
      <div className="vardist">
        <div className="vd-cell col-header" style={{ textAlign: 'left' }}>Classification</div>
        <div className="vd-cell col-header">LOF</div>
        <div className="vd-cell col-header">Missense + Indel</div>
        <div className="vd-cell col-header">Non-coding</div>
        <div className="vd-cell col-header">Synonymous</div>
        <div className="vd-cell col-header">Total</div>

        {rows.map((row) => (
          <div key={row.kind} style={{ display: 'contents' }}>
            <div className={`vd-cell row-label ${row.kind}`}>
              <span className="ldot" />{row.label}
            </div>
            {row.cells.map((cell) => (
              <div
                key={cell.key}
                className={[
                  'vd-cell',
                  cell.heat,
                  cell.isQuery ? 'query-hit' : null,
                ].filter(Boolean).join(' ')}
                title={cell.isQuery ? queryLabel : undefined}
              >
                {cell.value}
                {cell.isQuery && <span className="vd-query-badge">Query</span>}
              </div>
            ))}
            <div className="vd-cell total">{row.total}</div>
          </div>
        ))}
      </div>
      <div className="vardist-reading">
        <strong>Reading:</strong> {reading}
      </div>
      {queryBucket && (
        <div className="vardist-query-note">
          <strong>Query bucket:</strong> {queryLabel} maps to {queryBucket}.
        </div>
      )}
    </div>
  )
}
