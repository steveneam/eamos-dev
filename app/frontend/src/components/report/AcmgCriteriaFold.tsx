type AcmgCode =
  | 'PVS1'
  | 'PS1' | 'PS2' | 'PS3' | 'PS4'
  | 'PM1' | 'PM2' | 'PM3' | 'PM4' | 'PM5' | 'PM6'
  | 'PP1' | 'PP2' | 'PP3' | 'PP4' | 'PP5'
  | 'BA1'
  | 'BS1' | 'BS2' | 'BS3' | 'BS4'
  | 'BP1' | 'BP2' | 'BP3' | 'BP4' | 'BP5' | 'BP6' | 'BP7'

type Verdict = 'met' | 'met-benign' | 'unmet'

interface Criterion {
  code: AcmgCode
  label: string
  verdict: Verdict
}

interface AcmgCriteriaFoldProps {
  criteria?: Criterion[]
  intro?: string
  note?: string
}

const SAMPLE: Criterion[] = [
  { code: 'PM2',  label: 'Absent / extremely rare in controls',         verdict: 'met' },
  { code: 'PM5',  label: 'Different missense at known path. residue',   verdict: 'met' },
  { code: 'PP3',  label: 'Multiple in-silico predictors converge',      verdict: 'met' },
  { code: 'PP4',  label: 'Phenotype highly specific for gene',          verdict: 'met' },

  { code: 'PVS1', label: 'LOF in a LOF mechanism gene',                 verdict: 'unmet' },
  { code: 'PS1',  label: 'Same AA change as known pathogenic',          verdict: 'unmet' },
  { code: 'PS2',  label: 'De novo (confirmed maternity/paternity)',     verdict: 'unmet' },
  { code: 'PS3',  label: 'Functional studies support damage',           verdict: 'unmet' },
  { code: 'PS4',  label: 'Significantly enriched in cases',             verdict: 'unmet' },
  { code: 'PM1',  label: 'Mutational hot spot / critical domain',       verdict: 'unmet' },
  { code: 'PM3',  label: 'In trans with path. variant (recessive)',     verdict: 'unmet' },
  { code: 'PM4',  label: 'Protein length changes',                      verdict: 'unmet' },
  { code: 'PM6',  label: 'Assumed de novo',                             verdict: 'unmet' },
  { code: 'PP1',  label: 'Co-segregation with disease',                 verdict: 'unmet' },
  { code: 'PP2',  label: 'Missense in low-tolerance gene',              verdict: 'unmet' },
  { code: 'PP5',  label: 'Reputable source reports as path. (retired)', verdict: 'unmet' },

  { code: 'BA1',  label: 'AF > 5% in any pop',                          verdict: 'unmet' },
  { code: 'BS1',  label: 'AF > expected for disorder',                  verdict: 'unmet' },
  { code: 'BS2',  label: 'Observed in healthy individual',              verdict: 'unmet' },
  { code: 'BS3',  label: 'Functional studies support no impact',        verdict: 'unmet' },
  { code: 'BS4',  label: 'Lack of segregation',                         verdict: 'unmet' },
  { code: 'BP1',  label: 'Missense in LOF-only gene',                   verdict: 'unmet' },
  { code: 'BP2',  label: 'In trans with path. in dominant',             verdict: 'unmet' },
  { code: 'BP3',  label: 'In-frame indel in repetitive region',         verdict: 'unmet' },
  { code: 'BP4',  label: 'In-silico predicts no impact',                verdict: 'unmet' },
  { code: 'BP5',  label: 'Alternate molecular cause',                   verdict: 'unmet' },
  { code: 'BP6',  label: 'Reputable benign (retired)',                  verdict: 'unmet' },
  { code: 'BP7',  label: 'Silent / non-splice with no impact',          verdict: 'unmet' },
]

const SAMPLE_INTRO =
  'An automated read of the standard ACMG/AMP criteria for this variant. This is supporting evidence, not a classification. Eamos does not issue ACMG classifications — clinical judgement, segregation, and functional data are required before a final call.'

const SAMPLE_NOTE =
  'Met criteria above provide moderate-to-supporting evidence consistent with the Likely Pathogenic ClinVar classification. The unmet criteria reflect evidence types that haven’t been observed for this variant (e.g. functional studies, de novo observation) — they do not contradict pathogenicity.'

export function AcmgCriteriaFold({
  criteria = SAMPLE,
  intro = SAMPLE_INTRO,
  note = SAMPLE_NOTE,
}: AcmgCriteriaFoldProps) {
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
        <p className="intro">
          {intro.split(/\b(This is supporting evidence, not a classification\.)\b/).map((part, i) =>
            part === 'This is supporting evidence, not a classification.' ? (
              <strong key={i}>{part}</strong>
            ) : (
              part
            ),
          )}
        </p>

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

        <div className="acmg-note">
          <strong>Note:</strong> {note}
        </div>
      </div>
    </details>
  )
}
