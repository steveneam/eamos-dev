type EvLevel = 'def' | 'strong' | 'mod' | 'lim'
type Inheritance = 'AR' | 'AD' | 'XL' | 'MT'

interface Condition {
  name: string
  cases: number
  evidence: EvLevel
  evidenceLabel: string
  inheritance: Inheritance
  metaTag: string         // e.g. "OMIM #204100" — the b tag inside is parsed simply
  metaTagBold?: string    // e.g. "OMIM"
  src: string             // sources list
}

interface AssociatedConditionsProps {
  conditions?: Condition[]
  sub?: string
}

const SAMPLE: Condition[] = [
  {
    name: 'Leber Congenital Amaurosis 2 (LCA2)',
    cases: 412,
    evidence: 'def',
    evidenceLabel: 'Definitive',
    inheritance: 'AR',
    metaTagBold: 'OMIM',
    metaTag: '#204100',
    src: 'OMIM · Monarch · DECIPHER · GenCC · ClinGen',
  },
  {
    name: 'Retinitis Pigmentosa 20 (RP20)',
    cases: 218,
    evidence: 'def',
    evidenceLabel: 'Definitive',
    inheritance: 'AR',
    metaTagBold: 'OMIM',
    metaTag: '#613794',
    src: 'OMIM · Monarch · GenCC',
  },
  {
    name: 'RPE65-Related Dominant Retinopathy',
    cases: 14,
    evidence: 'mod',
    evidenceLabel: 'Moderate',
    inheritance: 'AD',
    metaTag: 'No OMIM entry',
    src: 'OMIM · GenCC · ClinGen · MONDO',
  },
  {
    name: 'Severe Early-Childhood-Onset Retinal Dystrophy',
    cases: 9,
    evidence: 'mod',
    evidenceLabel: 'Moderate',
    inheritance: 'AR',
    metaTag: 'Orphanet ORPHA:71862',
    src: 'Orphanet · GenCC',
  },
  {
    name: 'RPE65-Related Recessive Retinopathy (umbrella)',
    cases: 5,
    evidence: 'def',
    evidenceLabel: 'Definitive',
    inheritance: 'AR',
    metaTag: 'MONDO:0019200',
    src: 'PubMed · GenCC · MONDO · DECIPHER · OMIM · ClinGen',
  },
]

export function AssociatedConditions({
  conditions = SAMPLE,
  sub = '5 conditions · OMIM + GenCC + ClinGen + MONDO',
}: AssociatedConditionsProps) {
  return (
    <div style={{ marginTop: 22 }}>
      <div className="vardist-title" style={{ marginBottom: 4 }}>
        Associated conditions
        <span className="vardist-sub">{sub}</span>
      </div>
      <div className="conds">
        {conditions.map((c, i) => (
          <div key={i} className="cond">
            <div className="cond-cases">
              <span className="n">{c.cases}</span>
              <span className="l">cases</span>
            </div>
            <div className="cond-main">
              <div className="name">{c.name}</div>
              <div className="meta">
                <span className="meta-tag">
                  {c.metaTagBold && <b>{c.metaTagBold}</b>}
                  {c.metaTagBold ? ` ${c.metaTag}` : c.metaTag}
                </span>
                <span className="ev-level">
                  <span className={`ev-bars ${c.evidence}`}>
                    <span /><span /><span />
                  </span>
                  {c.evidenceLabel}
                </span>
                <span className="src">{c.src}</span>
              </div>
            </div>
            <div className="cond-inherit">{c.inheritance}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
