// B5 - Evidence Fingerprint. Four independent axes (rarity, predictors,
// conservation, constraint) on one benign-to-pathogenic baseline. Missing axes
// render as no-data markers; no axis is fabricated.

export interface FingerprintAxis {
  key: string
  label: string
  /** 0 = benign end, 1 = pathogenic end; null = no data for this axis. */
  value: number | null
  detail?: string
}

const clamp01 = (n: number) => Math.max(0, Math.min(1, n))

export function EvidenceFingerprint({ axes }: { axes: FingerprintAxis[] }) {
  const scored = axes.filter((a) => a.value != null) as (FingerprintAxis & { value: number })[]
  const pathCount = scored.filter((a) => a.value > 0.5).length
  const benCount = scored.filter((a) => a.value < 0.5).length
  const consensusPath = pathCount >= benCount
  const agree = consensusPath ? pathCount : benCount
  const direction = consensusPath ? 'pathogenic' : 'benign'
  const summary = scored.length === 0 ? 'No axes available' : `${agree} of ${scored.length} axes point ${direction}`
  const ariaLabel = `Evidence fingerprint: ${summary}. ${axes
    .map((a) =>
      `${a.label} ${
        a.value == null
          ? 'no data'
          : a.value > 0.5
            ? 'pathogenic-leaning'
            : a.value < 0.5
              ? 'benign-leaning'
              : 'neutral'
      }`,
    )
    .join('; ')}.`

  return (
    <figure role="img" aria-label={ariaLabel} style={{ margin: 0, minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
        <span className="eamos-kicker">Evidence fingerprint</span>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-2)' }}>{summary}</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {axes.map((a) => (
          <div key={a.key} style={{ display: 'grid', gridTemplateColumns: '74px 1fr', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 10.5, color: 'var(--ink-3)' }} title={a.detail}>
              {a.label}
            </span>
            <div style={{ position: 'relative', height: 12 }}>
              <div
                aria-hidden
                style={{
                  position: 'absolute',
                  top: 5,
                  left: 0,
                  right: 0,
                  height: 2,
                  borderRadius: 2,
                  background:
                    'linear-gradient(90deg, var(--cls-ben-bdr) 0%, var(--line) 50%, var(--cls-path-bdr) 100%)',
                }}
              />
              {a.value == null ? (
                <span style={{ position: 'absolute', right: 0, top: -2, fontSize: 10, color: 'var(--ink-5)' }}>-</span>
              ) : (
                <span
                  aria-hidden
                  title={a.detail}
                  style={{
                    position: 'absolute',
                    left: `${clamp01(a.value) * 100}%`,
                    top: 0,
                    transform: 'translateX(-50%)',
                    width: 9,
                    height: 9,
                    marginTop: 1.5,
                    borderRadius: 999,
                    background: a.value > 0.5 ? 'var(--cls-path-text)' : a.value < 0.5 ? 'var(--cls-ben-text)' : 'var(--ink-3)',
                    boxShadow: '0 0 0 1.5px var(--bg)',
                  }}
                />
              )}
            </div>
          </div>
        ))}
      </div>

      <div aria-hidden style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 9, color: 'var(--ink-5)' }}>
        <span>benign</span>
        <span>pathogenic</span>
      </div>

      <table className="sr-only">
        <caption>Evidence fingerprint - four axes on a benign-to-pathogenic scale</caption>
        <tbody>
          {axes.map((a) => (
            <tr key={a.key}>
              <th scope="row">{a.label}</th>
              <td>
                {a.value == null
                  ? 'no data'
                  : a.value > 0.5
                    ? 'pathogenic-leaning'
                    : a.value < 0.5
                      ? 'benign-leaning'
                      : 'neutral'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}
