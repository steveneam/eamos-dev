// §1 MaveDB functional evidence (PS3/BS3) — multiplexed assays of variant effect
// (MAVE / deep mutational scanning). Strength comes from the ClinGen SVI OddsPath
// framework (Brnich 2020), shown as a PS3/BS3 dual-badge (left = ACMG code,
// right = assay count). MaveDB is not wired yet, so under the MOCK-EVERYTHING-
// UNWIRED policy we render a realistic, clearly-tagged illustrative assay (the
// numbers are coherent with a damaging missense) plus the Brnich strength
// ladder, then keep the live MaveDB search link. Swap for `mavedb_functional`
// once Codex ships it.

const PS3_TIP = 'PS3 — lab experiments show the variant damages protein function (evidence it is pathogenic).'
const BS3_TIP = 'BS3 — lab experiments show the variant leaves protein function normal (evidence it is benign).'
const ODDSPATH_TIP =
  'OddsPath: how well the assay separates known pathogenic from benign variants — higher = stronger damaging (PS3), lower = stronger normal (BS3). Sets the evidence strength (Brnich 2020).'
const MAVE_TIP =
  'MAVE / deep mutational scanning: a single experiment measuring the functional effect of thousands of variants at once.'
const MOCK_TIP = 'Illustrative assay — not yet wired to live data. Replaced once MaveDB is connected.'
const SCORE_TIP = 'Normalized functional score: 1.0 ≈ wild-type activity, 0 ≈ complete loss of function.'

const dotted: React.CSSProperties = { borderBottom: '1px dotted var(--ink-5)', cursor: 'help' }

// Brnich 2020 / ClinGen SVI OddsPath → ACMG functional-evidence strength.
const BRNICH_BANDS = [
  { key: 'BS3_Strong', label: 'BS3 Strong', dir: 'benign' as const, min: 0, max: 0.053 },
  { key: 'BS3_Moderate', label: 'BS3 Mod', dir: 'benign' as const, min: 0.053, max: 0.23 },
  { key: 'BS3_Supporting', label: 'BS3 Sup', dir: 'benign' as const, min: 0.23, max: 0.48 },
  { key: 'Indeterminate', label: 'Indet.', dir: 'none' as const, min: 0.48, max: 2.1 },
  { key: 'PS3_Supporting', label: 'PS3 Sup', dir: 'path' as const, min: 2.1, max: 4.3 },
  { key: 'PS3_Moderate', label: 'PS3 Mod', dir: 'path' as const, min: 4.3, max: 18.7 },
  { key: 'PS3_Strong', label: 'PS3 Strong', dir: 'path' as const, min: 18.7, max: Infinity },
] as const

function bandForOddsPath(op: number) {
  return BRNICH_BANDS.find((b) => op >= b.min && op < b.max) ?? BRNICH_BANDS[3]
}

function dirTone(dir: 'benign' | 'path' | 'none') {
  if (dir === 'path')
    return { bg: 'var(--cls-lpath-bg)', bd: 'var(--cls-lpath-bdr)', ink: 'var(--cls-lpath-text)', dot: 'var(--cls-lpath-dot)' }
  if (dir === 'benign')
    return { bg: 'var(--cls-ben-bg)', bd: 'var(--cls-ben-bdr)', ink: 'var(--cls-ben-text)', dot: 'var(--cls-ben-dot)' }
  return { bg: 'var(--cls-na-bg)', bd: 'var(--cls-na-bdr)', ink: 'var(--cls-na-text)', dot: 'var(--cls-na-dot)' }
}

// Illustrative damaging assay coherent with a missense in a catalytic enzyme.
const MOCK_ASSAY = {
  assayName: 'Isomerohydrolase activity (cell-based 11-cis-retinol production)',
  normalizedScore: 0.31,
  oddsPath: 6.8,
  variantsScored: 142,
  pathogenicControls: 18,
  benignControls: 24,
  accession: 'urn:mavedb:00000000-x-0',
}

export function MaveFunctionalBlock({ gene, query }: { gene?: string | null; query?: string | null }) {
  const term = gene ?? query ?? ''
  const mavedbHref = `https://www.mavedb.org/#/search?search=${encodeURIComponent(term)}`

  const a = MOCK_ASSAY
  const band = bandForOddsPath(a.oddsPath)
  const tone = dirTone(band.dir)
  const code = band.dir === 'path' ? 'PS3' : band.dir === 'benign' ? 'BS3' : null
  const codeTip = band.dir === 'path' ? PS3_TIP : band.dir === 'benign' ? BS3_TIP : 'Indeterminate — the assay does not provide ACMG functional evidence at a calibrated strength.'

  return (
    <div style={{ marginTop: 16, border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', background: 'var(--bg-soft)', padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
        <span className="eamos-kicker" title={MAVE_TIP} style={{ cursor: 'help', borderBottom: '1px dotted var(--ink-5)' }}>
          MAVE functional evidence · PS3/BS3
        </span>
        {/* dual badge: ACMG code (left) + assay-count confidence signal (right) + mock tag */}
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            title={codeTip}
            style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: tone.ink, border: `0.5px solid ${tone.bd}`, background: tone.bg, borderRadius: 999, padding: '1px 7px', cursor: 'help' }}
          >
            {code ? `${code} · ${band.label.replace(/^(PS3|BS3) /, '')}` : 'Indeterminate'}
          </span>
          <span
            title="Number of independent MAVE assays — a confidence signal, not the strength."
            style={{ fontSize: 10, fontWeight: 700, color: 'var(--ink-4)', border: '0.5px solid var(--line)', background: 'var(--bg)', borderRadius: 999, padding: '1px 7px', cursor: 'help' }}
          >
            1 assay
          </span>
          <span className="eamos-mock" title={MOCK_TIP}>Mock</span>
        </span>
      </div>

      <p style={{ fontSize: 12.5, color: 'var(--ink-3)', margin: '10px 0 0', lineHeight: 1.55 }}>
        Multiplexed functional assay (<span title={MAVE_TIP} style={dotted}>MAVE / DMS</span>) measuring{' '}
        {a.assayName}. The normalized score and{' '}
        <span title={ODDSPATH_TIP} style={dotted}>OddsPath</span> place this variant in the{' '}
        <strong style={{ color: tone.ink }}>{band.key.replace(/_/g, ' ')}</strong> functional-evidence band.
      </p>

      {/* metric row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10, marginTop: 12 }}>
        <Metric label="Normalized score" value={a.normalizedScore.toFixed(2)} hint="1.0 = WT · 0 = null" tip={SCORE_TIP} />
        <Metric label="OddsPath" value={a.oddsPath.toFixed(1)} hint={band.key.replace(/_/g, ' ')} tip={ODDSPATH_TIP} />
        <Metric label="Variants scored" value={a.variantsScored.toLocaleString()} hint="in the assay" />
        <Metric label="Controls" value={`${a.pathogenicControls}P · ${a.benignControls}B`} hint="for calibration" />
      </div>

      {/* Brnich 2020 strength ladder */}
      <div style={{ marginTop: 14 }}>
        <div className="eamos-kicker" style={{ marginBottom: 6 }} title={ODDSPATH_TIP}>
          OddsPath strength scale (Brnich 2020)
        </div>
        <div style={{ display: 'flex', gap: 3 }}>
          {BRNICH_BANDS.map((b) => {
            const active = b.key === band.key
            const t = dirTone(b.dir)
            return (
              <div
                key={b.key}
                title={`${b.label}${b.max === Infinity ? ` (OddsPath ≥ ${b.min})` : ` (OddsPath ${b.min}–${b.max})`}`}
                style={{
                  flex: 1,
                  textAlign: 'center',
                  fontSize: 8.5,
                  fontWeight: active ? 700 : 600,
                  letterSpacing: '0.01em',
                  padding: '5px 2px',
                  borderRadius: 5,
                  border: `0.5px solid ${active ? t.dot : 'var(--line)'}`,
                  background: active ? t.bg : 'var(--bg)',
                  color: active ? t.ink : 'var(--ink-4)',
                  boxShadow: active ? `inset 0 -2px 0 ${t.dot}` : 'none',
                  whiteSpace: 'nowrap',
                  cursor: 'help',
                }}
              >
                {b.label}
              </div>
            )
          })}
        </div>
      </div>

      {/* per-assay provenance + live search link */}
      <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', fontSize: 11 }}>
        <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-4)' }} title="MaveDB score-set accession (illustrative)">
          {a.accession}
        </span>
        <a
          href={mavedbHref}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--teal-deep)', textDecoration: 'none', borderBottom: '1px dotted var(--teal-bdr)' }}
        >
          Search MaveDB for {gene ?? 'this gene'} ↗
        </a>
      </div>
    </div>
  )
}

function Metric({ label, value, hint, tip }: { label: string; value: string; hint?: string; tip?: string }) {
  return (
    <div style={{ border: '0.5px solid var(--line)', borderRadius: 'var(--r-sm)', background: 'var(--bg)', padding: '8px 10px' }}>
      <div className="eamos-kicker" style={tip ? { cursor: 'help', borderBottom: '1px dotted var(--ink-5)', display: 'inline-block' } : undefined} title={tip}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 16, fontWeight: 600, color: 'var(--ink)', marginTop: 3, lineHeight: 1.1 }}>
        {value}
      </div>
      {hint && <div style={{ fontSize: 10, color: 'var(--ink-4)', marginTop: 2 }}>{hint}</div>}
    </div>
  )
}
