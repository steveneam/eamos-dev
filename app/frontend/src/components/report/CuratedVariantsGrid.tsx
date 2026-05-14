type RowKind = 'p' | 'vus' | 'b'

interface DistRow {
  kind: RowKind
  label: string
  cells: Array<{ value: number; heat?: string }>  // 4 cells: LOF / Missense+Indel / Non-coding / Synonymous
  total: number
}

interface CuratedVariantsGridProps {
  rows?: DistRow[]
  sub?: string
  reading?: string
}

const SAMPLE_ROWS: DistRow[] = [
  {
    kind: 'p',
    label: 'Pathogenic',
    cells: [
      { value: 210, heat: 'heat-3' },
      { value: 187, heat: 'heat-3' },
      { value: 6,   heat: 'heat-1' },
      { value: 3,   heat: 'heat-1' },
    ],
    total: 406,
  },
  {
    kind: 'vus',
    label: 'VUS',
    cells: [
      { value: 1,   heat: 'heat-v-1' },
      { value: 342, heat: 'heat-v-2' },
      { value: 51,  heat: 'heat-v-1' },
      { value: 32,  heat: 'heat-v-1' },
    ],
    total: 426,
  },
  {
    kind: 'b',
    label: 'Benign',
    cells: [
      { value: 0 },
      { value: 11,  heat: 'heat-b-1' },
      { value: 198, heat: 'heat-b-2' },
      { value: 245, heat: 'heat-b-3' },
    ],
    total: 454,
  },
]

const SAMPLE_READING =
  'LOF and missense both contribute substantially to pathogenicity in RPE65 — LOF is a well-established disease mechanism. The 342 missense VUS reflect the deep interpretation tail typical of recessive disease genes.'

export function CuratedVariantsGrid({
  rows = SAMPLE_ROWS,
  sub = '1,286 classified variants · ClinVar + UniProt',
  reading = SAMPLE_READING,
}: CuratedVariantsGridProps) {
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
