import { describe, expect, it } from 'vitest'
import {
  blockedCodes,
  computeCriteria,
  CRITERIA,
  CRITERIA_BY_CODE,
  criteriaStateFromComputed,
  initialCriteriaState,
  STRENGTH_POINTS,
  type CriteriaState,
  type CriteriaStrength,
} from './criteria-model'
import type { EamosComputedClassification } from '../backend'

// Pins the teaching explainer's combine logic to the vault
// `Wiki/assets/acmg-explainer.html` Criteria-mode rules + the Tavtigian-2020
// worked examples in docs/report-acmg-viz/spec.md §4. The teaching model and the
// report instruments share lib/acmg/points.ts, so a drift here is a drift in the
// thing we tell users the framework does.

/** Turn codes on at their default strength. */
function on(...codes: string[]): CriteriaState {
  const state = initialCriteriaState()
  for (const c of codes) state[c].on = true
  return state
}
/** Turn a single code on at a chosen strength, layered on a base state. */
function withStrength(base: CriteriaState, code: string, strength: CriteriaStrength): CriteriaState {
  return { ...base, [code]: { on: true, strength } }
}

describe('criteria table', () => {
  it('has the 28 ACMG/AMP criteria, indexed by code', () => {
    expect(CRITERIA).toHaveLength(28)
    expect(CRITERIA_BY_CODE.PVS1.direction).toBe('pathogenic')
    expect(CRITERIA_BY_CODE.BA1.direction).toBe('benign')
    expect(CRITERIA_BY_CODE.BA1.def).toBe('stand_alone')
  })
  it('point values follow Tavtigian-2020', () => {
    expect(STRENGTH_POINTS.very_strong).toBe(8)
    expect(STRENGTH_POINTS.strong).toBe(4)
    expect(STRENGTH_POINTS.moderate).toBe(2)
    expect(STRENGTH_POINTS.supporting).toBe(1)
    expect(STRENGTH_POINTS.stand_alone).toBe(0)
  })
})

describe('computeCriteria — Tavtigian-2020 worked examples (spec §4)', () => {
  it('1 Very Strong + 1 Strong = +12 → Pathogenic', () => {
    // PVS1 (default very_strong, +8) + PS3 (default strong, +4)
    const r = computeCriteria(on('PVS1', 'PS3'))
    expect(r.net).toBe(12)
    expect(r.tier).toBe('Pathogenic')
  })
  it('2 Moderate + 1 Supporting = +5 → VUS', () => {
    // PM1 (+2) + PM6 (+2) + PM2 (+1)
    const r = computeCriteria(on('PM1', 'PM6', 'PM2'))
    expect(r.net).toBe(5)
    expect(r.tier).toBe('VUS')
  })
  it('PVS1 + PM2 (Supporting) = +9 → Likely Pathogenic', () => {
    const r = computeCriteria(on('PVS1', 'PM2'))
    expect(r.net).toBe(9)
    expect(r.tier).toBe('Likely Pathogenic')
  })
})

describe('computeCriteria — overrides + caps', () => {
  it('BA1 is a hard Benign override regardless of pathogenic points', () => {
    const r = computeCriteria(on('PVS1', 'BA1'))
    expect(r.ba1).toBe(true)
    expect(r.tier).toBe('Benign')
    expect(r.net).toBe(8)
    expect(r.sumBenign).toBe(0)
    expect(r.modelPosterior).toBeNull()
    expect(r.applied.find((item) => item.code === 'BA1')?.points).toBe(0)
  })
  it('the historical Eamos-v1 cap resolves strong opposing evidence to VUS', () => {
    const r = computeCriteria(on('PVS1', 'BS1'))
    expect(r.net).toBe(4)
    expect(r.conflict).toBe(true)
    expect(r.tier).toBe('VUS')
  })
  it('a single ≤1-supporting opposing point does NOT trip the conflict cap', () => {
    // PVS1 (+8) + a lone benign Supporting BP7 (−1): net +7, allowed → LP
    const r = computeCriteria(on('PVS1', 'BP7'))
    expect(r.net).toBe(7)
    expect(r.conflict).toBe(false)
    expect(r.tier).toBe('Likely Pathogenic')
  })
  it('respects a chosen strength (PS3 Moderate = +2, not +4)', () => {
    const r = computeCriteria(withStrength(on('PM1'), 'PS3', 'moderate'))
    expect(r.net).toBe(4)
    expect(r.applied.find((a) => a.code === 'PS3')?.points).toBe(2)
  })
  it('does not count PS3 without independent same-direction evidence', () => {
    const r = computeCriteria(on('PS3'))
    expect(r.net).toBe(0)
    expect(r.applied.find((item) => item.code === 'PS3')).toBeUndefined()
    expect(r.dependencyNotes).toContain(
      'PS3 needs independent same-direction evidence before it enters the point sum.',
    )
  })
  it('two Strong benign criteria = −8 → Benign', () => {
    const r = computeCriteria(on('BS1', 'BS2'))
    expect(r.net).toBe(-8)
    expect(r.tier).toBe('Benign')
  })
  it('caps combined PP3 plus PM1 pathogenic points at four', () => {
    const r = computeCriteria(withStrength(on('PM1'), 'PP3', 'strong'))
    expect(r.net).toBe(4)
    expect(r.applied.find((item) => item.code === 'PP3')?.points).toBe(2)
  })
})

describe('blockedCodes — mutual exclusion', () => {
  it('turning on PP3 blocks BP4', () => {
    expect(blockedCodes(on('PP3')).has('BP4')).toBe(true)
  })
  it('PVS1 blocks PM4', () => {
    expect(blockedCodes(on('PVS1')).has('PM4')).toBe(true)
  })
  it('population and functional dependency pairs block both directions', () => {
    expect(blockedCodes(on('PM2')).has('BS1')).toBe(true)
    expect(blockedCodes(on('PM2')).has('BA1')).toBe(true)
    expect(blockedCodes(on('BA1')).has('PM2')).toBe(true)
    expect(blockedCodes(on('PS3')).has('BS3')).toBe(true)
    expect(blockedCodes(on('BS3')).has('PS3')).toBe(true)
  })
})

describe('criteriaStateFromComputed — variant seeding round-trip', () => {
  // A minimal engine payload: PS3 Strong (+4) + PM2 Supporting (+1) = net +5 → VUS.
  const computed: EamosComputedClassification = {
    acmg_version_pin: {
      framework: 'x',
      ruleset_id: 'ruleset-x',
      ruleset_version: '1',
      conflict_policy_id: 'eamos_legacy_vus_cap',
      pvs1_revision: 'x',
      pp3_calibration: 'x',
      vcep_id: null,
      population_policy_id: 'population-x',
      population_policy_version: '1',
      cspec_overlay_id: null,
      cspec_overlay_version: null,
      population_policy_diff: [],
    },
    net_points: 5,
    sum_pathogenic: 5,
    sum_benign: 0,
    tier: 'VUS',
    classification_basis: 'bayesian_points',
    conflict: { is_conflicting: false },
    ba1_override: false,
    aggregate_evidence_likelihood_ratio: 10,
    prior_odds: 1 / 9,
    posterior_odds: 10 / 9,
    model_posterior: 10 / 19,
    benign_cut: 'tavtigian_2020',
    per_criterion: [
      { code: 'PS3', direction: 'pathogenic', triggered: true, applied_strength: 'strong', points: 4 },
      { code: 'PM2', direction: 'pathogenic', triggered: true, applied_strength: 'supporting', points: 1 },
      { code: 'BS1', direction: 'benign', triggered: false, applied_strength: null, points: 0 },
    ],
  }

  it('ticks the triggered criteria at their applied strength, leaves the rest off', () => {
    const state = criteriaStateFromComputed(computed)
    expect(state.PS3).toEqual({ on: true, strength: 'strong' })
    expect(state.PM2.on).toBe(true)
    expect(state.BS1.on).toBe(false)
    expect(state.PVS1.on).toBe(false)
  })

  it('re-computes to the same net + tier as the engine (no drift on an unmodified seed)', () => {
    const r = computeCriteria(criteriaStateFromComputed(computed), computed.benign_cut)
    expect(r.net).toBe(computed.net_points)
    expect(r.tier).toBe(computed.tier)
  })

  it('seeds BA1 as a stand-alone benign override', () => {
    const ba1: EamosComputedClassification = {
      ...computed,
      net_points: 0,
      sum_pathogenic: 0,
      tier: 'Benign',
      classification_basis: 'ba1_standalone_override',
      ba1_override: true,
      aggregate_evidence_likelihood_ratio: null,
      prior_odds: null,
      posterior_odds: null,
      model_posterior: null,
      per_criterion: [{ code: 'BA1', direction: 'benign', triggered: true, applied_strength: null, points: 0 }],
    }
    const r = computeCriteria(criteriaStateFromComputed(ba1), 'tavtigian_2020')
    expect(r.ba1).toBe(true)
    expect(r.tier).toBe('Benign')
  })
})
