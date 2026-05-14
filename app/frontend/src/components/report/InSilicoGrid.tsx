type PredictorTone = 'warn' | 'ok' | 'neutral'

interface PredictorCard {
  name: string
  score: number      // 0..1, formatted to 2 dp
  threshold: number  // 0..1
  verdict: string
  tone: PredictorTone
  metaMax?: string   // override "1.00"
}

interface InSilicoGridProps {
  cards?: PredictorCard[]
  consensus?: string
}

const SAMPLE_CARDS: PredictorCard[] = [
  { name: 'REVEL',         score: 0.82, threshold: 0.75, verdict: 'Pathogenic supporting', tone: 'warn' },
  { name: 'AlphaMissense', score: 0.91, threshold: 0.56, verdict: 'Likely pathogenic',     tone: 'warn' },
  { name: 'MetaLR',        score: 0.78, threshold: 0.50, verdict: 'Deleterious',           tone: 'warn' },
  { name: 'SpliceAI Δ',    score: 0.05, threshold: 0.20, verdict: 'No splice impact',      tone: 'ok'   },
]

const SAMPLE_CONSENSUS =
  'Predictors converge: three protein-effect predictors all cross their pathogenic thresholds (REVEL, AlphaMissense, MetaLR); SpliceAI sits well below the 0.20 splice-altering cutoff. No disagreement to flag — the in-silico signal is internally consistent with the ClinVar Likely Pathogenic call.'

export function InSilicoGrid({
  cards = SAMPLE_CARDS,
  consensus = SAMPLE_CONSENSUS,
}: InSilicoGridProps) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: 'var(--ink-3)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 10,
        }}
      >
        In-silico predictions
      </div>
      <div className="pred-grid">
        {cards.map((card) => {
          const tone = card.tone
          return (
            <div key={card.name} className="pred-card">
              <div className="pred-name">{card.name}</div>
              <div className={`pred-score ${tone === 'neutral' ? '' : tone}`}>
                {card.score.toFixed(2)}
              </div>
              <div className="pred-bar">
                <div
                  className={`pred-bar-fill${tone === 'ok' ? ' ok' : ''}`}
                  style={{ width: `${Math.round(card.score * 100)}%` }}
                />
                <div
                  className="pred-bar-threshold"
                  style={{ left: `${Math.round(card.threshold * 100)}%` }}
                />
              </div>
              <div className="pred-meta">
                <span>0.00</span>
                <span>{card.threshold.toFixed(2)} ↦</span>
                <span>{card.metaMax ?? '1.00'}</span>
              </div>
              <span className={`pred-verdict ${tone}`}>{card.verdict}</span>
            </div>
          )
        })}
      </div>
      <div className="pred-disagree">
        <strong>Predictors converge:</strong>{' '}
        {consensus.replace(/^Predictors converge:\s*/, '')}
      </div>
    </div>
  )
}
