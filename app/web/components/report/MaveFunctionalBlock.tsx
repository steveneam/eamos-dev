// §1 MaveDB functional evidence (PS3/BS3) — multiplexed assays of variant effect
// (MAVE / deep mutational scanning). Strength comes from the ClinGen SVI OddsPath
// framework (Brnich 2020), shown as a PS3/BS3 dual-badge (left = ACMG code,
// right = assay count). When the backend has a local MaveDB CC0 hit, render it
// as uncurated live evidence. Otherwise render a source-backed empty state; do
// not infer PS3/BS3 strength without a matched functional record.

import { EvidenceChip } from '@/components/ui/EvidenceChip'
import type { FunctionalStudy } from '@/lib/backend'

const ODDSPATH_TIP =
  'OddsPath: how well the assay separates known pathogenic from benign variants — higher = stronger damaging (PS3), lower = stronger normal (BS3). Sets the evidence strength (Brnich 2020).'
const MAVE_TIP =
  'MAVE / deep mutational scanning: a single experiment measuring the functional effect of thousands of variants at once.'
const LIVE_TIP =
  'Live local MaveDB CC0 functional-score record. Shown as uncurated evidence until a calibrated PS3/BS3 assertion exists.'
const UNCURATED_TIP =
  'Uncurated functional evidence: a public functional score was found, but no ACMG PS3/BS3 strength has been asserted.'

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

interface MaveFunctionalBlockProps {
  gene?: string | null
  query?: string | null
  study?: FunctionalStudy | null
}

export function MaveFunctionalBlock({ gene, query, study }: MaveFunctionalBlockProps) {
  const term = gene ?? query ?? ''
  const mavedbHref = `https://www.mavedb.org/#/search?search=${encodeURIComponent(term)}`

  if (study) {
    const accession = study.source_accession ?? study.citation ?? study.id
    const scoreLabel = study.functional_score_label ?? 'Functional score'
    const score = formatScore(study.functional_score)
    const sourceHref = study.url ?? mavedbHref
    const linkLabel = study.url ? 'Open MaveDB record ↗' : `Search MaveDB for ${gene ?? 'this gene'} ↗`

    return (
      <div style={{ marginTop: 'var(--report-subpanel-gap)', border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', background: 'var(--bg-soft)', padding: 'var(--report-subpanel-pad)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
          <span className="eamos-kicker" title={LIVE_TIP} style={{ cursor: 'help', borderBottom: '1px dotted var(--ink-5)' }}>
            MAVE functional evidence · MaveDB
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <EvidenceChip
              size="xs"
              uppercase
              tone={{ bg: 'var(--cls-na-bg)', border: 'var(--cls-na-bdr)', text: 'var(--cls-na-text)' }}
              title={UNCURATED_TIP}
              style={{ cursor: 'help' }}
            >
              Uncurated
            </EvidenceChip>
            <EvidenceChip
              size="xs"
              tone={{ bg: 'var(--bg)', border: 'var(--line)', text: 'var(--ink-4)' }}
              title="One local MaveDB CC0 score matched this variant."
              style={{ cursor: 'help' }}
            >
              1 score
            </EvidenceChip>
          </span>
        </div>

        <p style={{ fontSize: 12.5, color: 'var(--ink-3)', margin: '10px 0 0', lineHeight: 1.55 }}>
          {study.snippet ?? 'MaveDB CC0 functional-score record matched this variant.'}{' '}
          Eamos does not convert this record into PS3/BS3 strength without calibrated assay interpretation.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10, marginTop: 12 }}>
          <Metric label={scoreLabel} value={score} hint="source reported" tip="Functional score as reported by the local MaveDB CC0 import." />
          <Metric label="Evidence status" value="Uncurated" hint="no ACMG code asserted" tip={UNCURATED_TIP} />
          <Metric label="Source" value="MaveDB" hint="CC0 local import" />
          <Metric label="Score records" value="1" hint="matched variant" />
        </div>

        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', fontSize: 11 }}>
          <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-4)' }} title="MaveDB score-set accession">
            {accession}
          </span>
          <a
            href={sourceHref}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--teal-deep)', textDecoration: 'none', borderBottom: '1px dotted var(--teal-bdr)' }}
          >
            {linkLabel}
          </a>
        </div>
      </div>
    )
  }

  return (
    <div style={{ marginTop: 'var(--report-subpanel-gap)', border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', background: 'var(--bg-soft)', padding: 'var(--report-subpanel-pad)', minWidth: 0, maxWidth: '100%', overflowX: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', minWidth: 0 }}>
        <span className="eamos-kicker" title={MAVE_TIP} style={{ cursor: 'help', borderBottom: '1px dotted var(--ink-5)', overflowWrap: 'anywhere', minWidth: 0 }}>
          MAVE functional evidence · MaveDB
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', minWidth: 0 }}>
          <EvidenceChip
            size="xs"
            uppercase
            tone={{ bg: 'var(--cls-na-bg)', border: 'var(--cls-na-bdr)', text: 'var(--cls-na-text)' }}
            title="No matched local MaveDB CC0 functional-score record was returned for this variant."
            style={{ cursor: 'help' }}
          >
            No score
          </EvidenceChip>
          <EvidenceChip
            size="xs"
            tone={{ bg: 'var(--bg)', border: 'var(--line)', text: 'var(--ink-4)' }}
            title="Functional evidence materialization is local-file backed and remains gated until a complete source artifact is present."
            style={{ cursor: 'help' }}
          >
            Artifact-gated
          </EvidenceChip>
        </span>
      </div>

      <p style={{ fontSize: 12.5, color: 'var(--ink-3)', margin: '10px 0 0', lineHeight: 1.55 }}>
        No local MaveDB CC0 functional-score record matched this variant. Eamos does not display PS3/BS3
        functional strength unless a source-backed assay record or curated assertion is present.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10, marginTop: 12 }}>
        <Metric label="Evidence status" value="Unavailable" hint="no variant-level MAVE match" />
        <Metric label="Source" value="MaveDB" hint="CC0 local import" />
        <Metric label="ACMG code" value="None" hint="PS3/BS3 not asserted" />
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="eamos-kicker" style={{ marginBottom: 6 }} title={ODDSPATH_TIP}>
          OddsPath strength scale
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(68px, 1fr))', gap: 3 }}>
          {BRNICH_BANDS.map((b) => {
            return (
              <div
                key={b.key}
                title={`${b.label}${b.max === Infinity ? ` (OddsPath ≥ ${b.min})` : ` (OddsPath ${b.min}–${b.max})`}`}
                style={{
                  flex: 1,
                  textAlign: 'center',
                  fontSize: 8.5,
                  fontWeight: 600,
                  letterSpacing: '0.01em',
                  padding: '5px 2px',
                  borderRadius: 5,
                  border: '0.5px solid var(--line)',
                  background: 'var(--bg)',
                  color: 'var(--ink-4)',
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

      <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', fontSize: 11 }}>
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

function formatScore(score: number | null | undefined): string {
  if (score == null || Number.isNaN(score)) return 'reported'
  return Number.isInteger(score) ? score.toFixed(0) : score.toPrecision(3).replace(/\.?0+$/, '')
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
