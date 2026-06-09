// Shared score-scale grammar for the report's continuous evidence bars (design
// sweep Pass B). §2 In-silico (EvidenceBar) and §3 Constraint (ConstraintGauge)
// are the same idea — a horizontal banded track with a value marker (and, for
// §3, a threshold tick) — so they share ONE primitive here: identical pin glyph,
// identical band/threshold rendering, off the `--cls-*` class ramp. Each section
// keeps its own scale math (calibrated 0..1 vs raw constraint units) and only
// hands this component the resolved 0..1 positions, colours, and labels.
//
// §1 MAVE deliberately does NOT use this — it's a discrete OddsPath strength
// ladder (named buckets, no continuous axis), so forcing a pin-on-axis would
// imply a precision the Brnich bands don't have. It only shares the colour ramp.

const clamp01 = (n: number) => Math.max(0, Math.min(1, n))

/**
 * The shared value marker: a down-triangle on a short stem with a `--bg` ring so
 * it reads on any band colour. `muted` (mock / not-yet-wired) drops it to ink-4.
 * Positioned absolutely against a relatively-positioned track whose top is y=0.
 */
export function ScorePin({ pos, muted, title }: { pos: number; muted?: boolean; title?: string }) {
  const color = muted ? 'var(--ink-4)' : 'var(--ink)'
  return (
    <span
      aria-hidden
      title={title}
      style={{
        position: 'absolute',
        left: `${clamp01(pos) * 100}%`,
        top: -7,
        transform: 'translateX(-50%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        pointerEvents: 'none',
      }}
    >
      <span style={{ width: 0, height: 0, borderLeft: '4px solid transparent', borderRight: '4px solid transparent', borderTop: `6px solid ${color}` }} />
      <span style={{ width: 2, height: 12, marginTop: -1, background: color, borderRadius: 1, boxShadow: '0 0 0 1.5px var(--bg)' }} />
    </span>
  )
}

export interface ScaleBand {
  /** Width as a fraction of the track (0..1); the bands should sum to ~1. */
  frac: number
  color: string
  title?: string
}

/**
 * A banded scale track + optional boundary separators, threshold tick, and pin.
 * Chrome (height / radius / border / background) is passed per-caller so §2's
 * bordered soft-fill cell and §3's bare band row stay pixel-faithful while
 * sharing the band, tick, and pin rendering.
 */
export function ScaleTrack({
  bands,
  height = 8,
  radius = 4,
  border,
  background,
  separators,
  threshold,
  pin,
}: {
  bands: ScaleBand[]
  height?: number
  radius?: number
  border?: string
  background?: string
  /** Draw `--bg` separators at the band boundaries (calibrated multi-tier bars). */
  separators?: boolean
  threshold?: { pos: number; title?: string } | null
  pin?: { pos: number; muted?: boolean; title?: string } | null
}) {
  // Cumulative interior boundaries (after each band except the last).
  const bounds: number[] = []
  let acc = 0
  for (let i = 0; i < bands.length - 1; i++) {
    acc += bands[i].frac
    bounds.push(acc)
  }
  return (
    <div style={{ position: 'relative', height, borderRadius: radius, border, background }}>
      <div style={{ position: 'absolute', inset: 0, borderRadius: radius, overflow: 'hidden', display: 'flex' }}>
        {bands.map((b, i) => (
          <span
            key={i}
            title={b.title}
            style={{ width: `${b.frac * 100}%`, background: b.color, cursor: b.title ? 'help' : 'default' }}
          />
        ))}
      </div>
      {separators &&
        bounds.map((p, i) => (
          <span
            key={`sep-${i}`}
            aria-hidden
            style={{ position: 'absolute', left: `${p * 100}%`, top: 0, bottom: 0, width: 1, background: 'var(--bg)', opacity: 0.75 }}
          />
        ))}
      {threshold && (
        <span
          aria-hidden
          title={threshold.title}
          style={{ position: 'absolute', left: `${clamp01(threshold.pos) * 100}%`, top: -2, height: height + 4, width: 1, background: 'var(--ink-4)', opacity: 0.6 }}
        />
      )}
      {pin && <ScorePin pos={pin.pos} muted={pin.muted} title={pin.title} />}
    </div>
  )
}
