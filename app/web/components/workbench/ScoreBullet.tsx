/* ───────────────────────────────────────────────────────────────────────
   ScoreBullet — a compact value + tiny zoned bar for efficiency scores in
   the CRISPR tables (Pass D / docs/workbench-interpretability). The bar makes
   magnitude legible in grayscale (length + marker position), so colour is never
   the only cue. Uses the SCORE palette (--teal-deep / --warn / --err), NOT the
   ACMG --cls-* verdict ramp.

   `sense`:
     higher-better — good above the high threshold (on-target efficiency)
     lower-better  — good below the low threshold (off-target risk)
     band          — good between the thresholds (GC% sweet spot)
─────────────────────────────────────────────────────────────────────── */

type Sense = 'higher-better' | 'lower-better' | 'band'
type Tone = 'good' | 'mid' | 'bad'

interface ScoreBulletProps {
  value: number
  min: number
  max: number
  /** [low, high] zone boundaries in value units. */
  thresholds: [number, number]
  sense: Sense
  /** Pre-formatted number shown beside the bar. */
  display: string
  /** Dim + dash the bar when the value is illustrative (not source-backed). */
  muted?: boolean
  title?: string
}

const TONE_FILL: Record<Tone, string> = {
  good: 'color-mix(in oklab, var(--teal-deep) 18%, transparent)',
  mid: 'color-mix(in oklab, var(--warn) 18%, transparent)',
  bad: 'color-mix(in oklab, var(--err) 14%, transparent)',
}
const TONE_NUM: Record<Tone, string> = {
  good: 'score-good',
  mid: 'score-mid',
  bad: 'score-bad',
}

function tierAt(frac: number, loF: number, hiF: number, sense: Sense): Tone {
  if (sense === 'band') return frac >= loF && frac < hiF ? 'good' : 'mid'
  if (sense === 'higher-better') return frac >= hiF ? 'good' : frac >= loF ? 'mid' : 'bad'
  return frac < loF ? 'good' : frac < hiF ? 'mid' : 'bad' // lower-better
}

export function ScoreBullet({
  value,
  min,
  max,
  thresholds,
  sense,
  display,
  muted,
  title,
}: ScoreBulletProps) {
  const span = Math.max(1e-6, max - min)
  const frac = (v: number) => Math.min(1, Math.max(0, (v - min) / span))
  const [lo, hi] = thresholds
  const loF = frac(lo)
  const hiF = frac(hi)
  const valF = frac(value)

  const zones: Array<{ w: number; tone: Tone }> =
    sense === 'higher-better'
      ? [
          { w: loF, tone: 'bad' },
          { w: hiF - loF, tone: 'mid' },
          { w: 1 - hiF, tone: 'good' },
        ]
      : sense === 'lower-better'
        ? [
            { w: loF, tone: 'good' },
            { w: hiF - loF, tone: 'mid' },
            { w: 1 - hiF, tone: 'bad' },
          ]
        : [
            { w: loF, tone: 'mid' },
            { w: hiF - loF, tone: 'good' },
            { w: 1 - hiF, tone: 'mid' },
          ]

  const numClass = muted ? '' : TONE_NUM[tierAt(valF, loF, hiF, sense)]

  return (
    <span className={`score-bullet${muted ? ' is-muted' : ''}`} title={title}>
      <span className={`sb-num ${numClass}`}>{display}</span>
      <span className="sb-track" aria-hidden="true">
        <span className="sb-zones">
          {zones.map((z, i) => (
            <span
              key={i}
              className="sb-zone"
              style={{ flexGrow: Math.max(0, z.w), background: muted ? 'transparent' : TONE_FILL[z.tone] }}
            />
          ))}
        </span>
        <span className="sb-marker" style={{ left: `${valF * 100}%` }} />
      </span>
    </span>
  )
}
