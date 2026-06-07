// §1 MaveDB functional evidence (PS3/BS3) — multiplexed assays of variant effect
// (MAVE / deep mutational scanning). Strength comes from the ClinGen SVI OddsPath
// framework (Brnich 2020), shown as a PS3/BS3 dual-badge (left = ACMG code,
// right = assay count as a confidence signal). Mock-first: most variants have no
// MAVE assay, so the block honestly shows the "no data" state with an external
// jump, while exposing the planned surface (labelled) until MaveDB is wired.

const PS3_TIP = 'PS3 — lab experiments show the variant damages protein function (evidence it is pathogenic).'
const BS3_TIP = 'BS3 — lab experiments show the variant leaves protein function normal (evidence it is benign).'
const ODDSPATH_TIP =
  'OddsPath: how well the assay separates known pathogenic from benign variants — higher = stronger damaging (PS3), lower = stronger normal (BS3). Sets the evidence strength (Brnich 2020).'
const MAVE_TIP =
  'MAVE / deep mutational scanning: a single experiment measuring the functional effect of thousands of variants at once.'
const MOCK_TIP = 'Preview — not yet wired to live data. Illustrative until MaveDB is connected.'

const dotted: React.CSSProperties = { borderBottom: '1px dotted var(--ink-5)', cursor: 'help' }

export function MaveFunctionalBlock({ gene, query }: { gene?: string | null; query?: string | null }) {
  // No MAVE assay is wired yet → honest "uncurated / no data" state (5-state E).
  const term = gene ?? query ?? ''
  const mavedbHref = `https://www.mavedb.org/#/search?search=${encodeURIComponent(term)}`

  return (
    <div style={{ marginTop: 16, border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', background: 'var(--bg-soft)', padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
        <span className="eamos-kicker" title={MAVE_TIP} style={{ cursor: 'help', borderBottom: '1px dotted var(--ink-5)' }}>
          MAVE functional evidence · PS3/BS3
        </span>
        {/* dual badge: ACMG code (left) + assay-count confidence signal (right) */}
        <span style={{ display: 'flex', gap: 6 }}>
          <span
            title="Functional ACMG code (PS3 damaging / BS3 normal) — none until a calibrated assay is curated."
            style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--cls-na-text)', border: '0.5px solid var(--cls-na-bdr)', background: 'var(--cls-na-bg)', borderRadius: 999, padding: '1px 7px', cursor: 'help' }}
          >
            None
          </span>
          <span
            title="Number of independent MAVE assays — a confidence signal, not the strength."
            style={{ fontSize: 10, fontWeight: 700, color: 'var(--ink-4)', border: '0.5px solid var(--line)', background: 'var(--bg)', borderRadius: 999, padding: '1px 7px', cursor: 'help' }}
          >
            0 assays
          </span>
        </span>
      </div>

      <p style={{ fontSize: 12.5, color: 'var(--ink-3)', margin: '10px 0 0', lineHeight: 1.55 }}>
        No multiplexed functional assay (<span title={MAVE_TIP} style={dotted}>MAVE / DMS</span>) for this variant in
        MaveDB yet.{' '}
        <span className="eamos-mock" title={MOCK_TIP} style={{ verticalAlign: 'middle' }}>Needs live data</span>{' '}
        When a calibrated assay exists this shows a{' '}
        <span title={PS3_TIP} style={dotted}>PS3</span>/<span title={BS3_TIP} style={dotted}>BS3</span> dual-badge with
        the normalized score, <span title={ODDSPATH_TIP} style={dotted}>OddsPath</span>-derived strength, and per-assay
        provenance.
      </p>
      <a
        href={mavedbHref}
        target="_blank"
        rel="noopener noreferrer"
        style={{ display: 'inline-block', marginTop: 8, fontSize: 11.5, color: 'var(--teal-deep)', textDecoration: 'none', borderBottom: '1px dotted var(--teal-bdr)' }}
      >
        Search MaveDB for {gene ?? 'this gene'} ↗
      </a>
    </div>
  )
}
