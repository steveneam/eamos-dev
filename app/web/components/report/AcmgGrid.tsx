import type { AcmgCode, AcmgCriterion } from '@/lib/backend'

// Shared 28-box ACMG criterion grid — used by both the §1 criteria fold and the
// Eamos auto-classifier so they read identically. Each box hover-explains the
// criterion + whether it was met (intuitiveness pass).
export const ACMG_LABELS: Record<AcmgCode, string> = {
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

export function isBenignAcmgCode(code: AcmgCode): boolean {
  return code.startsWith('B')
}

export function AcmgGrid({ criteria }: { criteria: AcmgCriterion[] }) {
  return (
    <div className="acmg-grid">
      {criteria.map((c) => {
        const met = c.verdict === 'met'
        const cls = met
          ? isBenignAcmgCode(c.code)
            ? 'acmg-cell met-benign'
            : 'acmg-cell met'
          : 'acmg-cell'
        const label = ACMG_LABELS[c.code]
        return (
          <div
            key={c.code}
            className={cls}
            title={`${c.code} · ${label} — ${met ? 'MET' : 'not met'}`}
          >
            <span className="code">{c.code}</span>
            <span className="label-l">{label}</span>
          </div>
        )
      })}
    </div>
  )
}
