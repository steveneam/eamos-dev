interface NearbyVariant {
  left: number
  classification: 'p' | 'lp' | 'vus' | 'lb' | 'b'
  title: string
  queried?: boolean
}

interface CodonCell {
  aa: string
  dna: string
  dnaAlt?: string  // alternate base for queried codon (rendered with .alt)
  dnaPost?: string // remaining bases after alt
  pos: number
  queried?: boolean
}

interface LocusContextProps {
  coords?: string
  centreLabel?: string
  nearby?: NearbyVariant[]
  codons?: CodonCell[]
  workbenchHref?: string
}

const SAMPLE_NEARBY: NearbyVariant[] = [
  { left: 8,  classification: 'p',   title: 'c.236A>G p.Asp79Gly · Pathogenic' },
  { left: 18, classification: 'lp',  title: 'c.241C>T p.Arg81Cys · Likely Pathogenic' },
  { left: 26, classification: 'p',   title: 'c.247G>A p.Ala83Thr · Pathogenic' },
  { left: 34, classification: 'vus', title: 'c.253T>C · VUS' },
  { left: 42, classification: 'lp',  title: 'c.257C>G · Likely Pathogenic' },
  { left: 50, classification: 'lp',  title: 'c.260A>G p.Asp87Gly · queried · Likely Pathogenic', queried: true },
  { left: 58, classification: 'vus', title: 'c.268A>G · VUS' },
  { left: 66, classification: 'lb',  title: 'c.271G>A · Likely Benign' },
  { left: 74, classification: 'p',   title: 'c.277C>T p.Arg93Cys · Pathogenic' },
  { left: 82, classification: 'vus', title: 'c.283G>C · VUS' },
  { left: 90, classification: 'lp',  title: 'c.289G>A p.Glu97Lys · Likely Pathogenic' },
]

const SAMPLE_CODONS: CodonCell[] = [
  { aa: 'Tyr', dna: 'TAT', pos: 82 },
  { aa: 'Arg', dna: 'CGG', pos: 83 },
  { aa: 'Glu', dna: 'GAA', pos: 84 },
  { aa: 'Pro', dna: 'CCT', pos: 85 },
  { aa: 'Val', dna: 'GTG', pos: 86 },
  { aa: 'Asp → Gly', dna: 'G', dnaAlt: 'G', dnaPost: 'C', pos: 87, queried: true },
  { aa: 'Lys', dna: 'AAG', pos: 88 },
  { aa: 'Thr', dna: 'ACA', pos: 89 },
  { aa: 'Val', dna: 'GTC', pos: 90 },
  { aa: 'Ala', dna: 'GCC', pos: 91 },
  { aa: 'Ile', dna: 'ATT', pos: 92 },
]

const LANE_TOPS: Record<NearbyVariant['classification'], string> = {
  p: '0%', lp: '25%', vus: '50%', lb: '75%', b: '100%',
}

export function LocusContext({
  coords = 'chr1 : 68,444,849 — 68,444,889  ·  RPE65 exon 4  ·  (+) strand',
  centreLabel = 'c.260A>G',
  nearby = SAMPLE_NEARBY,
  codons = SAMPLE_CODONS,
  workbenchHref = '/workbench?gene=RPE65&cdna=c.260A%3EG',
}: LocusContextProps) {
  const queried = nearby.find((v) => v.queried)
  const markerLeft = queried?.left ?? 50

  return (
    <div className="locus">
      <div className="locus-bar">
        <div className="locus-coords">{coords}</div>
        <div className="locus-zoom" role="group" aria-label="Zoom level">
          <button type="button">Gene</button>
          <button type="button">Exon</button>
          <button type="button" className="active">Codon</button>
        </div>
      </div>

      <div className="locus-track">
        <div className="locus-row variants">
          <span className="axis-label">ClinVar variants nearby</span>
          <div className="lane">
            <div className="lane-line p" /><span className="lane-label" style={{ top: '0%' }}>P</span>
            <div className="lane-line lp" /><span className="lane-label" style={{ top: '25%' }}>LP</span>
            <div className="lane-line vus" /><span className="lane-label" style={{ top: '50%' }}>VUS</span>
            <div className="lane-line lb" /><span className="lane-label" style={{ top: '75%' }}>LB</span>
            <div className="lane-line b" /><span className="lane-label" style={{ top: '100%' }}>B</span>

            {nearby.map((v, i) => (
              <span
                key={i}
                className={`locus-dot ${v.classification}${v.queried ? ' queried' : ''}`}
                style={{ left: `${v.left}%`, top: LANE_TOPS[v.classification] }}
                title={v.title}
              />
            ))}

            <div className="locus-marker" data-label={centreLabel} style={{ left: `${markerLeft}%` }} />
          </div>
        </div>

        <div className="locus-row codons">
          {codons.map((c, i) => (
            <div key={i} className={c.queried ? 'codon queried' : 'codon'}>
              <span className="aa">{c.aa}</span>
              <span className="dna">
                {c.dna}
                {c.dnaAlt && <span className="alt">{c.dnaAlt}</span>}
                {c.dnaPost}
              </span>
              <span className="pos">{c.pos}</span>
            </div>
          ))}
        </div>

        <div className="locus-legend">
          <div className="locus-legend-item"><span className="dot" style={{ background: '#B82B2B' }} />Pathogenic</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: '#BA7517' }} />Likely Pathogenic</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: '#94a3b8' }} />VUS</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: '#6FA88F' }} />Likely Benign</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: '#1D9E75' }} />Benign</div>
          <div className="locus-legend-item" style={{ marginLeft: 'auto' }}>
            <a
              href={workbenchHref}
              style={{
                color: 'var(--teal-deep)',
                textDecoration: 'underline',
                textUnderlineOffset: 3,
              }}
            >
              Open full sequence in Workbench ↗
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
