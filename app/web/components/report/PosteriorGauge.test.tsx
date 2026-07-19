import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import type { EamosComputedClassification } from '@/lib/backend'
import { PosteriorGauge } from './PosteriorGauge'

function pointModelClassification(): EamosComputedClassification {
  return {
    acmg_version_pin: {
      framework: 'Richards-2015 + Tavtigian-2020 points',
      ruleset_id: 'richards_2015_tavtigian_2020_eamos_v1',
      ruleset_version: 'eamos-historical-replay-v1',
      conflict_policy_id: 'eamos_legacy_vus_cap',
      pvs1_revision: 'Abou-Tayoun-2018',
      pp3_calibration: 'eamos-revel-capped-v1+PMID:36413997',
      population_policy_id: 'acmg_svi_general_frequency_v1',
      population_policy_version: '1.0.0',
      population_policy_diff: [],
    },
    net_points: 0,
    sum_pathogenic: 0,
    sum_benign: 0,
    tier: 'VUS',
    classification_basis: 'bayesian_points',
    conflict: { is_conflicting: false },
    ba1_override: false,
    aggregate_evidence_likelihood_ratio: 1,
    prior_odds: 1 / 9,
    posterior_odds: 1 / 9,
    model_posterior: 0.1,
    benign_cut: 'tavtigian_2020',
    per_criterion: [],
  }
}

describe('PosteriorGauge', () => {
  it('labels a point-model result explicitly', () => {
    const markup = renderToStaticMarkup(
      <PosteriorGauge computed={pointModelClassification()} />,
    )

    expect(markup).toContain('model posterior')
    expect(markup).toContain('10.0%')
  })

  it('renders BA1 as not applicable without a percentage gauge', () => {
    const ba1: EamosComputedClassification = {
      ...pointModelClassification(),
      tier: 'Benign',
      classification_basis: 'ba1_standalone_override',
      ba1_override: true,
      aggregate_evidence_likelihood_ratio: null,
      prior_odds: null,
      posterior_odds: null,
      model_posterior: null,
      per_criterion: [
        {
          code: 'BA1',
          direction: 'benign',
          triggered: true,
          applied_strength: null,
          points: 0,
        },
      ],
    }

    const markup = renderToStaticMarkup(<PosteriorGauge computed={ba1} />)

    expect(markup).toContain('model posterior not applicable')
    expect(markup).toContain('audit net +0')
    expect(markup).not.toContain('10.0%')
    expect(markup).not.toContain('Tavtigian-2020 points')
  })
})
