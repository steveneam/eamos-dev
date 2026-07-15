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
    expect(STRENGTH_POINTS.stand_alone).toBe(8)
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
  })
  it('strong opposing evidence → conflicting VUS regardless of net', () => {
    // PS3 strong (+4) vs BS3 strong (−4): net 0, both strong → conflict
    const r = computeCriteria(on('PS3', 'BS3'))
    expect(r.net).toBe(0)
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
    const r = computeCriteria(withStrength(initialCriteriaState(), 'PS3', 'moderate'))
    expect(r.net).toBe(2)
    expect(r.applied.find((a) => a.code === 'PS3')?.points).toBe(2)
  })
  it('two Strong benign criteria = −8 → Benign', () => {
    const r = computeCriteria(on('BS1', 'BS2'))
    expect(r.net).toBe(-8)
    expect(r.tier).toBe('Benign')
  })
})

describe('blockedCodes — mutual exclusion', () => {
  it('turning on PP3 blocks BP4', () => {
    expect(blockedCodes(on('PP3')).has('BP4')).toBe(true)
  })
  it('PVS1 blocks PM4', () => {
    expect(blockedCodes(on('PVS1')).has('PM4')).toBe(true)
  })
})

describe('criteriaStateFromComputed — variant seeding round-trip', () => {
  // A minimal engine payload: PS3 Strong (+4) + PM2 Supporting (+1) = net +5 → VUS.
  const computed: EamosComputedClassification = {
    acmg_version_pin: { framework: 'x', pvs1_revision: 'x', pp3_calibration: 'x', vcep_id: null },
    net_points: 5,
    sum_pathogenic: 5,
    sum_benign: 0,
    tier: 'VUS',
    conflict: { is_conflicting: false },
    ba1_override: false,
    posterior: 0.3,
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
      ba1_override: true,
      per_criterion: [{ code: 'BA1', direction: 'benign', triggered: true, applied_strength: null, points: -8 }],
    }
    const r = computeCriteria(criteriaStateFromComputed(ba1), 'tavtigian_2020')
    expect(r.ba1).toBe(true)
    expect(r.tier).toBe('Benign')
  })
})
