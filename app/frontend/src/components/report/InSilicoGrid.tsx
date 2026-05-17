import type {
  InSilicoPredictions,
  PredictorCard as PredictorCardData,
  PredictorVerdict,
} from '@/lib/backend'

type PredictorTone = 'warn' | 'ok' | 'neutral'

interface PredictorCardDisplay {
  name: string
  score: number
  threshold: number
  verdict: string
  tone: PredictorTone
}

interface InSilicoGridProps {
  data?: InSilicoPredictions | null
}

const VERDICT_TONE: Record<PredictorVerdict, PredictorTone> = {
  damaging: 'warn',
  tolerated: 'ok',
  uncertain: 'neutral',
}

function displayName(name: PredictorCardData['name']): string {
  return name === 'SpliceAI' ? 'SpliceAI Δ' : name
}

function mapCards(items: PredictorCardData[]): PredictorCardDisplay[] {
  return items.map((c) => ({
    name: displayName(c.name),
    score: c.score,
    threshold: c.threshold,
    verdict: c.verdict_label || c.verdict,
    tone: VERDICT_TONE[c.verdict],
  }))
}

export function InSilicoGrid({ data }: InSilicoGridProps) {
  if (!data) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '0 0 18px' }}>
        No in-silico predictions available for this variant.
      </p>
    )
  }

  const cards = mapCards(data.cards)
  const consensus = data.consensus_note

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
                <span>1.00</span>
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
