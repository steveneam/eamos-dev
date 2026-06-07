import { Disclosure } from '@/components/ui/Disclosure'
import type { AcmgCriteriaScaffold, AcmgCode } from '@/lib/backend'
import { AcmgGrid } from './AcmgGrid'

/**
 * Eamos automated ACMG/AMP classification (report v3) — InterVar-style. Takes the
 * criteria the report already assigned (the §1 28-criterion scaffold) and applies
 * the Richards et al. 2015 *combining* rules to estimate a 5-tier verdict. Useful
 * for NOVEL variants with no ClinVar/ClinGen call. It is a rule-based starting
 * point, NOT a substitute for the expert-panel classification above.
 */

interface Counts {
  pvs: number
  ps: number
  pm: number
  pp: number
  ba: number
  bs: number
  bp: number
}

const VERDICT_THEME: Record<string, { bg: string; border: string; text: string }> = {
  Pathogenic: { bg: 'var(--cls-path-bg)', border: 'var(--cls-path-bdr)', text: 'var(--cls-path-text)' },
  'Likely pathogenic': { bg: 'var(--cls-lpath-bg)', border: 'var(--cls-lpath-bdr)', text: 'var(--cls-lpath-text)' },
  'Uncertain significance': { bg: 'var(--cls-vus-bg)', border: 'var(--cls-vus-bdr)', text: 'var(--cls-vus-text)' },
  'Likely benign': { bg: 'var(--cls-lben-bg)', border: 'var(--cls-lben-bdr)', text: 'var(--cls-lben-text)' },
  Benign: { bg: 'var(--cls-ben-bg)', border: 'var(--cls-ben-bdr)', text: 'var(--cls-ben-text)' },
}

function categorize(code: AcmgCode): keyof Counts | null {
  if (code === 'PVS1') return 'pvs'
  if (code.startsWith('PS')) return 'ps'
  if (code.startsWith('PM')) return 'pm'
  if (code.startsWith('PP')) return 'pp'
  if (code === 'BA1') return 'ba'
  if (code.startsWith('BS')) return 'bs'
  if (code.startsWith('BP')) return 'bp'
  return null
}

// Richards 2015 combining rules → {verdict, rule explanation}.
function classify({ pvs, ps, pm, pp, ba, bs, bp }: Counts): { verdict: string; rule: string } {
  const pathogenic =
    (pvs >= 1 && (ps >= 1 || pm >= 2 || (pm === 1 && pp === 1) || pp >= 2)) ||
    ps >= 2 ||
    (ps === 1 && (pm >= 3 || (pm === 2 && pp >= 2) || (pm === 1 && pp >= 4)))
  const likelyPath =
    (pvs === 1 && pm === 1) ||
    (ps === 1 && (pm === 1 || pm === 2)) ||
    (ps === 1 && pp >= 2) ||
    pm >= 3 ||
    (pm === 2 && pp >= 2) ||
    (pm === 1 && pp >= 4)
  const benign = ba >= 1 || bs >= 2
  const likelyBenign = (bs === 1 && bp === 1) || bp >= 2

  const pathCall = pathogenic ? 'Pathogenic' : likelyPath ? 'Likely pathogenic' : null
  const benCall = benign ? 'Benign' : likelyBenign ? 'Likely benign' : null

  if (pathCall && benCall)
    return { verdict: 'Uncertain significance', rule: 'Pathogenic and benign criteria conflict — resolved to VUS.' }
  if (pathCall === 'Pathogenic')
    return { verdict: 'Pathogenic', rule: 'Met criteria satisfy an ACMG Pathogenic combination.' }
  if (pathCall === 'Likely pathogenic')
    return { verdict: 'Likely pathogenic', rule: 'Met criteria satisfy an ACMG Likely-pathogenic combination.' }
  if (benCall === 'Benign')
    return { verdict: 'Benign', rule: 'Stand-alone (BA1) or ≥2 strong benign criteria met.' }
  if (benCall === 'Likely benign')
    return { verdict: 'Likely benign', rule: 'Met criteria satisfy an ACMG Likely-benign combination.' }
  return {
    verdict: 'Uncertain significance',
    rule: 'The met criteria do not combine into a pathogenic or benign classification.',
  }
}

export function EamosAcmgClassifier({ data }: { data?: AcmgCriteriaScaffold | null }) {
  if (!data) return null
  const met = data.criteria.filter((c) => c.verdict === 'met').map((c) => c.code)
  const counts: Counts = { pvs: 0, ps: 0, pm: 0, pp: 0, ba: 0, bs: 0, bp: 0 }
  for (const code of met) {
    const cat = categorize(code)
    if (cat) counts[cat] += 1
  }
  const { verdict, rule } = classify(counts)
  const theme = VERDICT_THEME[verdict] ?? { bg: 'var(--cls-na-bg)', border: 'var(--cls-na-bdr)', text: 'var(--cls-na-text)' }
  const pathCodes = met.filter((c) => c.startsWith('P'))
  const benignCodes = met.filter((c) => c.startsWith('B'))

  return (
    <div style={{ marginTop: 18 }}>
      <Disclosure
        kicker="Eamos automated ACMG"
        showLabel="Show Eamos auto-classification"
        hideLabel="Hide auto-classification"
        summary={`${verdict} · rule-based (InterVar-style)`}
      >
        <p style={{ margin: '0 0 12px', fontSize: 12, lineHeight: 1.55, color: 'var(--ink-3)' }}>
          A <strong style={{ color: 'var(--ink)' }}>rule-based</strong> ACMG/AMP estimate (Richards 2015
          combining rules), computed from the criteria met in §1 — a starting point for{' '}
          <strong style={{ color: 'var(--ink)' }}>novel variants</strong>. The expert-panel call above takes
          precedence.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
          <span
            title="Automated ACMG/AMP classification from the met criteria"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 11px',
              borderRadius: 999,
              fontSize: 13,
              fontWeight: 700,
              background: theme.bg,
              border: `0.5px solid ${theme.border}`,
              color: theme.text,
            }}
          >
            <span aria-hidden style={{ width: 8, height: 8, borderRadius: 999, background: theme.text }} />
            {verdict}
          </span>
          <span style={{ fontSize: 11.5, color: 'var(--ink-4)' }}>{rule}</span>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 11.5, color: 'var(--ink-3)', marginBottom: 12 }}>
          <span>
            <span style={{ color: 'var(--ink-4)' }}>Pathogenic criteria met: </span>
            {pathCodes.length ? (
              <span style={{ fontFamily: 'var(--mono)', color: 'var(--cls-path-text)' }}>{pathCodes.join(', ')}</span>
            ) : (
              <span style={{ color: 'var(--ink-4)' }}>none</span>
            )}
          </span>
          <span>
            <span style={{ color: 'var(--ink-4)' }}>Benign criteria met: </span>
            {benignCodes.length ? (
              <span style={{ fontFamily: 'var(--mono)', color: 'var(--cls-ben-text)' }}>{benignCodes.join(', ')}</span>
            ) : (
              <span style={{ color: 'var(--ink-4)' }}>none</span>
            )}
          </span>
        </div>

        {/* The same 28-box grid as §1 — met criteria highlighted; hover any box. */}
        <div className="eamos-kicker" style={{ marginBottom: 8 }}>All 28 ACMG criteria — met highlighted</div>
        <AcmgGrid criteria={data.criteria} />

        <p style={{ margin: '12px 0 0', fontSize: 10.5, lineHeight: 1.5, color: 'var(--ink-4)' }}>
          Automated; uses base criterion strengths (no VCEP-specific overrides). Not a clinical
          classification — confirm against the expert-panel call and full ACMG review.
        </p>
      </Disclosure>
    </div>
  )
}
