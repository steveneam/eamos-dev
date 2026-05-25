import type {
  InSilicoPredictions,
  PredictorCard as PredictorCardData,
  PredictorVerdict,
} from '@/lib/backend'

type PredictorTone = 'warn' | 'ok' | 'neutral'

interface PredictorRowDisplay {
  name: string
  score: number
  threshold: number
  verdict: string
  tone: PredictorTone
  sourceUrl?: string | null
}

interface InSilicoGridProps {
  data?: InSilicoPredictions | null
}

const VERDICT_TONE: Record<PredictorVerdict, PredictorTone> = {
  damaging: 'warn',
  tolerated: 'ok',
  uncertain: 'neutral',
}

const TONE_COLOR: Record<PredictorTone, string> = {
  warn: 'var(--warn)',
  ok: 'var(--teal)',
  neutral: 'var(--ink-4)',
}

const TONE_VERDICT_STYLE: Record<PredictorTone, { background: string; color: string; border: string }> = {
  warn:    { background: 'var(--warn-tint)',  color: '#633806',          border: '0.5px solid var(--warn-bdr)' },
  ok:      { background: 'var(--teal-tint)', color: 'var(--teal-deep)', border: '0.5px solid #cbe3d8' },
  neutral: { background: 'var(--bg-soft)',   color: 'var(--ink-3)',     border: '0.5px solid var(--line)' },
}

function displayName(name: PredictorCardData['name']): string {
  return name === 'SpliceAI' ? 'SpliceAI Δ' : name
}

function mapRows(items: PredictorCardData[]): PredictorRowDisplay[] {
  return items.map((c) => ({
    name: displayName(c.name),
    score: c.score,
    threshold: c.threshold,
    verdict: c.verdict_label || c.verdict,
    tone: VERDICT_TONE[c.verdict],
    sourceUrl: c.source_url ?? null,
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

  // AlphaMissense is on hold per user decision (2026-05-19) — hidden from the
  // report UI; the predictor stays in the contract/payload assets so this is
  // a one-line revert once it is re-approved. See agent_handoff DECISIONS.
  const rows = mapRows((data.cards ?? []).filter((c) => c.name !== 'AlphaMissense'))
  const consensus = data.consensus_note
  if (rows.length === 0) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '0 0 18px' }}>
        No visible in-silico predictions available for this variant.
      </p>
    )
  }

  // Strip the "Predictors converge:" prefix if the backend already includes it.
  const consensusText = consensus?.replace(/^Predictors converge:\s*/i, '') ?? null

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

      {/* Analytical comparison strip: one row per predictor */}
      <div
        style={{
          border: '0.5px solid var(--line)',
          borderRadius: 'var(--r-md)',
          overflow: 'hidden',
        }}
      >
        {rows.map((row, i) => {
          const verdictStyle = TONE_VERDICT_STYLE[row.tone]
          const barColor = TONE_COLOR[row.tone]
          const scorePercent = Math.min(100, Math.round(row.score * 100))
          const thresholdPercent = Math.min(100, Math.round(row.threshold * 100))
          const isLast = i === rows.length - 1

          return (
            <div
              key={row.name}
              style={{
                display: 'grid',
                gridTemplateColumns: '100px 1fr 90px',
                alignItems: 'center',
                gap: 16,
                padding: '12px 16px',
                background: 'var(--bg)',
                borderBottom: isLast ? 'none' : '0.5px solid var(--line)',
              }}
            >
              {/* Predictor name + score */}
              <div>
                <div
                  style={{
                    fontSize: 10.5,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: 'var(--ink-4)',
                    marginBottom: 4,
                  }}
                >
                  {row.name}
                </div>
                <div
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 18,
                    fontWeight: 500,
                    lineHeight: 1,
                    color: barColor,
                    letterSpacing: '-0.01em',
                  }}
                >
                  {row.score.toFixed(2)}
                </div>
              </div>

              {/* Score bar with threshold marker */}
              <div>
                <div
                  style={{
                    position: 'relative',
                    height: 5,
                    background: 'var(--bg-soft2)',
                    borderRadius: 3,
                    overflow: 'visible',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: `${scorePercent}%`,
                      background: barColor,
                      borderRadius: 3,
                    }}
                  />
                  {/* Threshold tick */}
                  <div
                    aria-label={`Threshold ${row.threshold.toFixed(2)}`}
                    style={{
                      position: 'absolute',
                      top: -3,
                      bottom: -3,
                      left: `${thresholdPercent}%`,
                      width: '0.5px',
                      background: 'var(--ink-3)',
                    }}
                  />
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginTop: 4,
                    fontFamily: 'var(--mono)',
                    fontSize: 9.5,
                    color: 'var(--ink-4)',
                  }}
                >
                  <span>0.00</span>
                  <span style={{ color: 'var(--ink-3)' }}>
                    {row.threshold.toFixed(2)} threshold
                  </span>
                  <span>1.00</span>
                </div>
              </div>

              {/* Verdict badge */}
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    padding: '3px 10px',
                    borderRadius: 4,
                    fontSize: 10.5,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    whiteSpace: 'nowrap',
                    ...verdictStyle,
                  }}
                >
                  {row.verdict}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Consensus note as a plain statement, not a callout stripe */}
      {consensusText && (
        <p
          style={{
            marginTop: 10,
            marginBottom: 0,
            fontSize: 12.5,
            lineHeight: 1.55,
            color: 'var(--ink-3)',
          }}
        >
          <strong style={{ color: 'var(--ink-2)', fontWeight: 600 }}>Predictors: </strong>
          {consensusText}
        </p>
      )}
    </div>
  )
}
