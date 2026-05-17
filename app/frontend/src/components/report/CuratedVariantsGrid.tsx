import type { CuratedVariantsDistribution } from '@/lib/backend'

type RowKind = 'p' | 'vus' | 'b'

interface DistRow {
  kind: RowKind
  label: string
  cells: Array<{ value: number; heat?: string }>  // 4 cells: LOF / Missense+Indel / Non-coding / Synonymous
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

function heatClass(value: number, max: number, heatPrefix: string, levels: number): string | undefined {
  if (value <= 0 || max <= 0) return undefined
  const ratio = value / max
  const tier = Math.min(levels, Math.max(1, Math.ceil(ratio * levels)))
  return `${heatPrefix}-${tier}`
}

function mapRows(
  cells: Record<string, number>,
  rowTotals: Record<string, number>,
): DistRow[] {
  return ROW_DEFS.map(({ kind, label, prefix, heatPrefix, levels }) => {
    const values = COL_SUFFIXES.map((suffix) => cells[`${prefix}_${suffix}`] ?? 0)
    const max = Math.max(...values)
    const total = rowTotals[prefix] ?? values.reduce((a, b) => a + b, 0)
    return {
      kind,
      label,
      cells: values.map((value) => ({ value, heat: heatClass(value, max, heatPrefix, levels) })),
      total,
    }
  })
}

export function CuratedVariantsGrid({ data }: CuratedVariantsGridProps) {
  if (!data) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
        No curated variants distribution available for this gene.
      </p>
    )
  }

  const rows = mapRows(data.cells, data.row_totals ?? {})
  const sub = data.subtitle || `${data.total.toLocaleString()} classified variants`
  const reading = data.reading

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
            {row.cells.map((cell, i) => (
              <div
                key={i}
                className={cell.heat ? `vd-cell ${cell.heat}` : 'vd-cell'}
              >
                {cell.value}
              </div>
            ))}
            <div className="vd-cell total">{row.total}</div>
          </div>
        ))}
      </div>
      <div className="vardist-reading">
        <strong>Reading:</strong> {reading}
      </div>
    </div>
  )
}
