import type {
  AcmgCode,
  AcmgCriteriaScaffold,
  AcmgCriterion as AcmgCriterionData,
} from '@/lib/backend'

type DisplayVerdict = 'met' | 'met-benign' | 'unmet'

interface Criterion {
  code: AcmgCode
  label: string
  verdict: DisplayVerdict
}

interface AcmgCriteriaFoldProps {
  data?: AcmgCriteriaScaffold | null
}

const ACMG_LABELS: Record<AcmgCode, string> = {
  PVS1: 'LOF in a LOF mechanism gene',
  PS1:  'Same AA change as known pathogenic',
  PS2:  'De novo (confirmed maternity/paternity)',
  PS3:  'Functional studies support damage',
  PS4:  'Significantly enriched in cases',
  PM1:  'Mutational hot spot / critical domain',
  PM2:  'Absent / extremely rare in controls',
  PM3:  'In trans with path. variant (recessive)',
  PM4:  'Protein length changes',
  PM5:  'Different missense at known path. residue',
  PM6:  'Assumed de novo',
  PP1:  'Co-segregation with disease',
  PP2:  'Missense in low-tolerance gene',
  PP3:  'Multiple in-silico predictors converge',
  PP4:  'Phenotype highly specific for gene',
  PP5:  'Reputable source reports as path. (retired)',
  BA1:  'AF > 5% in any pop',
  BS1:  'AF > expected for disorder',
  BS2:  'Observed in healthy individual',
  BS3:  'Functional studies support no impact',
  BS4:  'Lack of segregation',
  BP1:  'Missense in LOF-only gene',
  BP2:  'In trans with path. in dominant',
  BP3:  'In-frame indel in repetitive region',
  BP4:  'In-silico predicts no impact',
  BP5:  'Alternate molecular cause',
  BP6:  'Reputable benign (retired)',
  BP7:  'Silent / non-splice with no impact',
}

function isBenignCode(code: AcmgCode): boolean {
  return code.startsWith('B')
}

function mapCriteria(items: AcmgCriterionData[]): Criterion[] {
  return items.map((c) => ({
    code: c.code,
    label: ACMG_LABELS[c.code],
    verdict:
      c.verdict === 'met'
        ? isBenignCode(c.code)
          ? 'met-benign'
          : 'met'
        : 'unmet',
  }))
}

export function AcmgCriteriaFold({ data }: AcmgCriteriaFoldProps) {
  if (!data) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
        No ACMG criteria scaffold available for this variant.
      </p>
    )
  }

  const criteria = mapCriteria(data.criteria)
  const intro = data.intro
  const note = data.note

  const met = criteria.filter((c) => c.verdict === 'met' || c.verdict === 'met-benign').length
  const unmet = criteria.length - met

  return (
    <details className="fold">
      <summary className="fold-summary">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
        ACMG criteria — automated scaffolding
        <span className="count">{met} met · {unmet} unmet · ACMG 2015 + 2022 PP3/BP4</span>
      </summary>
      <div className="fold-body">
        {intro && (
          <p className="intro">
            {intro.split(/\b(This is supporting evidence, not a classification\.)\b/).map((part, i) =>
              part === 'This is supporting evidence, not a classification.' ? (
                <strong key={i}>{part}</strong>
              ) : (
                part
              ),
            )}
          </p>
        )}

        <div className="acmg-grid">
          {criteria.map((c) => {
            const cls =
              c.verdict === 'met'
                ? 'acmg-cell met'
                : c.verdict === 'met-benign'
                ? 'acmg-cell met-benign'
                : 'acmg-cell'
            return (
              <div key={c.code} className={cls}>
                <span className="code">{c.code}</span>
                <span className="label-l">{c.label}</span>
              </div>
            )
          })}
        </div>

        {note && (
          <div className="acmg-note">
            <strong>Note:</strong> {note}
          </div>
        )}
      </div>
    </details>
  )
}
