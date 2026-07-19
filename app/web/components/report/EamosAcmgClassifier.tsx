import { Disclosure } from '@/components/ui/Disclosure'
import { EvidenceChip } from '@/components/ui/EvidenceChip'
import type {
  AcmgCaseContextLimitation,
  AcmgCode,
  AcmgCriteriaScaffold,
  EamosComputedClassification,
} from '@/lib/backend'
import { criteriaStateFromComputed } from '@/lib/acmg/criteria-model'
import { modelPosteriorFromComputed } from '@/lib/acmg/points'
import { AcmgExplainer } from '@/components/acmg/AcmgExplainer'
import { AcmgGrid } from './AcmgGrid'
import { ConfidenceChannel } from './ConfidenceChannel'

interface Counts {
  pvs: number
  ps: number
  pm: number
  pp: number
  ba: number
  bs: number
  bp: number
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

  if (pathCall && benCall) {
    return { verdict: 'Uncertain significance', rule: 'Pathogenic and benign criteria conflict; resolved to VUS.' }
  }
  if (pathCall === 'Pathogenic') {
    return { verdict: 'Pathogenic', rule: 'Met criteria satisfy an ACMG Pathogenic combination.' }
  }
  if (pathCall === 'Likely pathogenic') {
    return { verdict: 'Likely pathogenic', rule: 'Met criteria satisfy an ACMG Likely-pathogenic combination.' }
  }
  if (benCall === 'Benign') {
    return { verdict: 'Benign', rule: 'Stand-alone BA1 or at least 2 strong benign criteria met.' }
  }
  if (benCall === 'Likely benign') {
    return { verdict: 'Likely benign', rule: 'Met criteria satisfy an ACMG Likely-benign combination.' }
  }
  return {
    verdict: 'Uncertain significance',
    rule: 'The met criteria do not combine into a pathogenic or benign classification.',
  }
}

function LegacyCategoricalView({ data }: { data: AcmgCriteriaScaffold }) {
  const met = data.criteria.filter((c) => c.verdict === 'met').map((c) => c.code)
  const counts: Counts = { pvs: 0, ps: 0, pm: 0, pp: 0, ba: 0, bs: 0, bp: 0 }
  for (const code of met) {
    const cat = categorize(code)
    if (cat) counts[cat] += 1
  }
  const { verdict, rule } = classify(counts)
  const pathCodes = met.filter((c) => c.startsWith('P'))
  const benignCodes = met.filter((c) => c.startsWith('B'))

  return (
    <Disclosure
      kicker="Legacy categorical view"
      showLabel="Show legacy categorical view (Richards-2015)"
      hideLabel="Hide legacy categorical view"
      summary={`${verdict} - rule-based count (no points)`}
    >
      <p style={{ margin: '0 0 12px', fontSize: 12, lineHeight: 1.55, color: 'var(--ink-3)' }}>
        The original <strong style={{ color: 'var(--ink)' }}>Richards-2015 combining rules</strong> applied to the met
        criteria: a categorical count with no point total or posterior. Kept for audit; the point-based advisory above
        supersedes it.
      </p>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
        <EvidenceChip size="lg" dot classification={verdict} title="Legacy Richards-2015 categorical classification">
          {verdict}
        </EvidenceChip>
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

      <div className="eamos-kicker" style={{ marginBottom: 8 }}>All 28 ACMG criteria - met highlighted</div>
      <AcmgGrid criteria={data.criteria} />
    </Disclosure>
  )
}

const COMPUTED_WARNING_LABELS: Record<string, string> = {
  'acmg_case_context_not_scored:PM3_phase_in_trans_required':
    'PM3 needs confirmed phase with a second disease-causing allele before EAMOS can score it.',
  'acmg_case_context_not_scored:PP4_phenotype_specificity_required':
    'PP4 needs phenotype specificity or family-case context before EAMOS can score it.',
  'functional_source_assertions_context_only:assay_validation_missing':
    'Functional assertions remain context only because no versioned assay-validation record was supplied.',
  'functional_assertions_context_only:none_selected_for_counting':
    'Functional assertions remain context only because none was selected by the predeclared assay policy.',
  'functional_assertion_not_counted:selected_candidate_cardinality':
    'Functional evidence was not scored because the policy requires exactly one best-validated assertion.',
  'population_cspec_not_applied:popmax_faf_missing':
    'The disease-specific population thresholds were not applied because popmax filtering allele frequency was missing.',
}

function computedWarningLabel(value: string): string {
  if (value.startsWith('functional_assertion_not_counted:')) {
    return `Functional evidence was not scored: ${value.split(':').at(-1)?.replaceAll('_', ' ')}.`
  }
  return COMPUTED_WARNING_LABELS[value] ?? value
}

function computedLimitationKey(limitation: AcmgCaseContextLimitation): string {
  return [
    limitation.code,
    limitation.reason,
    limitation.missing_inputs.join(','),
  ].join(':')
}

function computedCaseContextMessages(computed: EamosComputedClassification): Array<{ key: string; message: string }> {
  if (computed.limitations?.length) {
    return computed.limitations.map((limitation) => ({
      key: computedLimitationKey(limitation),
      message: limitation.message,
    }))
  }
  return (computed.warnings ?? []).map((warning) => ({
    key: warning,
    message: computedWarningLabel(warning),
  }))
}

export function EamosAcmgClassifier({
  data,
  computed,
}: {
  data?: AcmgCriteriaScaffold | null
  computed?: EamosComputedClassification | null
}) {
  if (!computed && !data) return null
  const modelPosterior = computed ? modelPosteriorFromComputed(computed) : null
  const modelPosteriorSummary = computed?.ba1_override
    ? 'BA1 stand-alone · model posterior not applicable'
    : modelPosterior === null
      ? 'model posterior unavailable'
      : `model posterior ${(modelPosterior * 100).toFixed(1)}%`
  const caseContextMessages = computed ? computedCaseContextMessages(computed) : []

  return (
    <div style={{ marginTop: 'var(--report-subpanel-gap)' }}>
      {computed && (
        <Disclosure
          kicker="EAMOS-computed ACMG/AMP advisory"
          showLabel="Show the points breakdown"
          hideLabel="Hide the points breakdown"
          summary={
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <EvidenceChip size="sm" dot classification={computed.tier} title="EAMOS point-based advisory classification">
                {computed.tier}
              </EvidenceChip>
              <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>{modelPosteriorSummary}</span>
            </span>
          }
        >
          <div aria-label="EAMOS-computed ACMG/AMP advisory classification">
            <p style={{ margin: '0 0 14px', fontSize: 12, lineHeight: 1.55, color: 'var(--ink-3)' }}>
              Combines the predictors above (PP3/BP4) with population, loss-of-function and validated functional evidence into a{' '}
              <strong style={{ color: 'var(--ink)' }}>Tavtigian-2020 point score</strong>. EAMOS-computed{' '}
              <strong style={{ color: 'var(--ink)' }}>advisory</strong>; the curated clinical classification in section 1 takes
              precedence.
            </p>

            {caseContextMessages.length ? (
              <div
                role="note"
                style={{
                  margin: '0 0 14px',
                  border: '0.5px solid var(--warn)',
                  borderRadius: 'var(--r-sm)',
                  background: 'color-mix(in srgb, var(--warn) 7%, transparent)',
                  padding: '10px 12px',
                }}
              >
                <div className="eamos-kicker" style={{ marginBottom: 7 }}>Evidence not scored</div>
                <ul style={{ margin: 0, paddingLeft: 16, color: 'var(--ink-3)', fontSize: 11.5, lineHeight: 1.5 }}>
                  {caseContextMessages.map((item) => (
                    <li key={item.key}>{item.message}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <AcmgExplainer initialState={criteriaStateFromComputed(computed)} anchor={computed} />

            <div style={{ marginTop: 14, paddingTop: 10, borderTop: '0.5px solid var(--line)' }}>
              <ConfidenceChannel computed={computed} />
            </div>
          </div>
        </Disclosure>
      )}

      {data && (
        <div style={{ marginTop: computed ? 12 : 0 }}>
          <LegacyCategoricalView data={data} />
        </div>
      )}
    </div>
  )
}
