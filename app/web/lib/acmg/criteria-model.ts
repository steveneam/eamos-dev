// ACMG criteria TEACHING model — the data + combine logic behind the interactive
// "change the criteria → watch the points move" explainer on the submission page.
//
// This is a *teaching tool, not the classifier*. The real EAMOS advisory comes
// from the backend acmg_points_engine.py (surfaced via eamos_computed_
// classification); this module lets a user hand-toggle criteria and strengths to
// learn how the Tavtigian-2020 points framework combines them. It is a faithful
// TS port of the vault `Wiki/assets/acmg-explainer.html` Criteria-mode compute(),
// with the tier cuts + model posterior delegated to lib/acmg/points.ts so the explainer
// and the report's instruments never drift.
//
// The active Vitest coverage lives beside this module in app/web.

import type {
  EamosComputedBenignCut,
  EamosComputedClassification,
  EamosComputedTier,
} from '@/lib/backend'
import { modelPosterior, tierByNet } from './points'

export type CriteriaStrength = 'very_strong' | 'strong' | 'moderate' | 'supporting' | 'stand_alone'
export type CriteriaDirection = 'pathogenic' | 'benign'

/** Applied points per strength. BA1 is a stand-alone override, not a summand. */
export const STRENGTH_POINTS: Record<CriteriaStrength, number> = {
  very_strong: 8,
  strong: 4,
  moderate: 2,
  supporting: 1,
  stand_alone: 0,
}

export const STRENGTH_LABEL: Record<CriteriaStrength, string> = {
  very_strong: 'Very Strong',
  strong: 'Strong',
  moderate: 'Moderate',
  supporting: 'Supporting',
  stand_alone: 'Stand-alone',
}

export interface CriterionDef {
  code: string
  category: string
  direction: CriteriaDirection
  /** Selectable strengths (variable per-application). Empty ⇒ fixed at `def`. */
  strengths: CriteriaStrength[]
  /** Default applied strength. */
  def: CriteriaStrength
  desc: string
  /** Mutually-exclusive partners — switching this on switches those off. */
  excl: string[]
}

const SS: CriteriaStrength[] = ['very_strong', 'strong', 'moderate', 'supporting']

// The 28 ACMG/AMP criteria, grouped by evidence category (vault order). Variable
// strengths reflect ClinGen SVI per-criterion ranges; PP5/BP6 are kept for
// completeness but flagged discouraged in their description.
export const CRITERIA: CriterionDef[] = [
  // Population
  { code: 'PM2', category: 'Population', direction: 'pathogenic', strengths: [], def: 'supporting', desc: 'Meets active rare-frequency policy', excl: ['BS1', 'BA1'] },
  { code: 'PS4', category: 'Population', direction: 'pathogenic', strengths: ['strong', 'moderate', 'supporting'], def: 'strong', desc: 'Enriched in affecteds vs controls', excl: [] },
  { code: 'BS1', category: 'Population', direction: 'benign', strengths: ['strong', 'moderate', 'supporting'], def: 'strong', desc: 'AF higher than disease allows', excl: ['PM2'] },
  { code: 'BS2', category: 'Population', direction: 'benign', strengths: [], def: 'strong', desc: 'Seen in healthy adults', excl: [] },
  { code: 'BA1', category: 'Population', direction: 'benign', strengths: [], def: 'stand_alone', desc: 'Meets active stand-alone benign policy', excl: ['PM2'] },
  // Computational
  { code: 'PVS1', category: 'Computational', direction: 'pathogenic', strengths: SS, def: 'very_strong', desc: 'Null variant in a LoF gene', excl: ['PM4'] },
  { code: 'PS1', category: 'Computational', direction: 'pathogenic', strengths: ['strong', 'moderate'], def: 'strong', desc: 'Same amino-acid change as a known pathogenic variant', excl: ['PM5'] },
  { code: 'PM1', category: 'Computational', direction: 'pathogenic', strengths: [], def: 'moderate', desc: 'In a mutational hot-spot / functional domain', excl: [] },
  { code: 'PM4', category: 'Computational', direction: 'pathogenic', strengths: [], def: 'moderate', desc: 'Protein length change (non-repeat)', excl: ['PVS1', 'BP3'] },
  { code: 'PM5', category: 'Computational', direction: 'pathogenic', strengths: ['moderate', 'supporting'], def: 'moderate', desc: 'Novel missense at a known-pathogenic residue', excl: ['PS1'] },
  { code: 'PP2', category: 'Computational', direction: 'pathogenic', strengths: [], def: 'supporting', desc: 'Missense in a low-benign-missense gene', excl: [] },
  { code: 'PP3', category: 'Computational', direction: 'pathogenic', strengths: ['strong', 'moderate', 'supporting'], def: 'supporting', desc: 'In-silico predictors agree: damaging', excl: ['BP4'] },
  { code: 'BP1', category: 'Computational', direction: 'benign', strengths: [], def: 'supporting', desc: 'Missense in a truncating-only gene', excl: [] },
  { code: 'BP3', category: 'Computational', direction: 'benign', strengths: [], def: 'supporting', desc: 'In-frame indel in a repeat region', excl: ['PM4'] },
  { code: 'BP4', category: 'Computational', direction: 'benign', strengths: ['strong', 'moderate', 'supporting'], def: 'supporting', desc: 'In-silico predictors agree: benign', excl: ['PP3'] },
  { code: 'BP7', category: 'Computational', direction: 'benign', strengths: [], def: 'supporting', desc: 'Synonymous, no predicted splice impact', excl: [] },
  // Functional
  { code: 'PS3', category: 'Functional', direction: 'pathogenic', strengths: ['strong', 'moderate', 'supporting'], def: 'strong', desc: 'Validated functional assay: damaging', excl: ['BS3'] },
  { code: 'BS3', category: 'Functional', direction: 'benign', strengths: ['strong', 'moderate', 'supporting'], def: 'strong', desc: 'Validated functional assay: no damage', excl: ['PS3'] },
  // De novo / segregation
  { code: 'PS2', category: 'De novo / segregation', direction: 'pathogenic', strengths: ['very_strong', 'strong', 'moderate', 'supporting'], def: 'strong', desc: 'Confirmed de novo', excl: [] },
  { code: 'PM6', category: 'De novo / segregation', direction: 'pathogenic', strengths: [], def: 'moderate', desc: 'Assumed de novo (unconfirmed)', excl: [] },
  { code: 'PP1', category: 'De novo / segregation', direction: 'pathogenic', strengths: ['strong', 'moderate', 'supporting'], def: 'supporting', desc: 'Co-segregates with disease', excl: [] },
  { code: 'BS4', category: 'De novo / segregation', direction: 'benign', strengths: [], def: 'strong', desc: 'Lack of segregation', excl: [] },
  // Allelic / phase
  { code: 'PM3', category: 'Allelic / phase', direction: 'pathogenic', strengths: ['very_strong', 'strong', 'moderate', 'supporting'], def: 'moderate', desc: 'In trans with a pathogenic variant (recessive)', excl: [] },
  { code: 'BP2', category: 'Allelic / phase', direction: 'benign', strengths: [], def: 'supporting', desc: 'In trans (dominant) / in cis with pathogenic', excl: [] },
  // Phenotype / other
  { code: 'PP4', category: 'Phenotype / other', direction: 'pathogenic', strengths: ['moderate', 'supporting'], def: 'supporting', desc: 'Phenotype highly specific for the gene', excl: [] },
  { code: 'PP5', category: 'Phenotype / other', direction: 'pathogenic', strengths: [], def: 'supporting', desc: 'Reputable source: pathogenic (discouraged)', excl: [] },
  { code: 'BP5', category: 'Phenotype / other', direction: 'benign', strengths: [], def: 'supporting', desc: 'Alternate molecular cause found', excl: [] },
  { code: 'BP6', category: 'Phenotype / other', direction: 'benign', strengths: [], def: 'supporting', desc: 'Reputable source: benign (discouraged)', excl: [] },
]

export const CRITERIA_BY_CODE: Record<string, CriterionDef> = Object.fromEntries(
  CRITERIA.map((c) => [c.code, c]),
)

export const CRITERIA_CATEGORIES: string[] = [...new Set(CRITERIA.map((c) => c.category))]

/** Per-criterion on/off + chosen strength. */
export type CriteriaState = Record<string, { on: boolean; strength: CriteriaStrength }>

/** A fresh state with every criterion off at its default strength. */
export function initialCriteriaState(): CriteriaState {
  const state: CriteriaState = {}
  for (const c of CRITERIA) state[c.code] = { on: false, strength: c.def }
  return state
}

export interface AppliedCriterion {
  code: string
  direction: CriteriaDirection
  strength: CriteriaStrength
  /** SIGNED applied points (pathogenic +, benign −). */
  points: number
}

export interface CriteriaResult {
  sumPathogenic: number // ΣP (positive)
  sumBenign: number // ΣB (positive magnitude)
  net: number // ΣP − ΣB
  tier: EamosComputedTier
  conflict: boolean
  reason: string
  ba1: boolean
  modelPosterior: number | null
  dependencyNotes: string[]
  applied: AppliedCriterion[]
}

/**
 * Combine the selected criteria into a points result. Faithful to the vault
 * Criteria-mode rules: BA1 is a hard Benign override outside the point sum.
 * This replays the explicit Eamos-v1 conflict cap for historical what-if parity;
 * future rulesets must supply their own conflict policy.
 */
export function computeCriteria(
  state: CriteriaState,
  benignCut: EamosComputedBenignCut = 'tavtigian_2020',
): CriteriaResult {
  let sumPathogenic = 0
  let sumBenign = 0
  let ba1 = false
  const pEl: { code: string; pts: number; strength: CriteriaStrength }[] = []
  const bEl: { code: string; pts: number; strength: CriteriaStrength }[] = []
  const dependencyNotes: string[] = []

  for (const def of CRITERIA) {
    const s = state[def.code]
    if (!s?.on) continue
    const pts = STRENGTH_POINTS[s.strength]
    if (def.direction === 'pathogenic') {
      sumPathogenic += pts
      pEl.push({ code: def.code, pts, strength: s.strength })
    } else {
      if (def.code === 'BA1') {
        ba1 = true
      } else {
        sumBenign += pts
      }
      bEl.push({ code: def.code, pts, strength: s.strength })
    }
  }

  const ps3Index = pEl.findIndex((item) => item.code === 'PS3')
  if (ps3Index >= 0 && !pEl.some((item) => item.code !== 'PS3')) {
    sumPathogenic -= pEl[ps3Index].pts
    pEl.splice(ps3Index, 1)
    dependencyNotes.push('PS3 needs independent same-direction evidence before it enters the point sum.')
  }
  const bs3Index = bEl.findIndex((item) => item.code === 'BS3')
  if (bs3Index >= 0 && !bEl.some((item) => item.code !== 'BS3' && item.code !== 'BA1')) {
    sumBenign -= bEl[bs3Index].pts
    bEl.splice(bs3Index, 1)
    dependencyNotes.push('BS3 needs independent same-direction evidence before it enters the point sum.')
  }

  const pp3 = pEl.find((item) => item.code === 'PP3')
  const pm1 = pEl.find((item) => item.code === 'PM1')
  if (pp3 && pm1 && pp3.pts + pm1.pts > 4) {
    const adjustment = pp3.pts - Math.max(0, 4 - pm1.pts)
    pp3.pts -= adjustment
    sumPathogenic -= adjustment
  }

  const net = sumPathogenic - sumBenign
  let tier: EamosComputedTier
  let conflict = false
  let reason = ''

  if (ba1) {
    tier = 'Benign'
    reason = 'BA1 stand-alone benign override'
  } else {
    if (sumPathogenic > 0 && sumBenign > 0) {
      const lean = net > 0 ? 'P' : net < 0 ? 'B' : '0'
      const disc = lean === 'P' ? bEl : lean === 'B' ? pEl : sumPathogenic >= sumBenign ? bEl : pEl
      const discMax = disc.reduce((a, d) => Math.max(a, d.pts), 0)
      if (lean === '0' || disc.length > 1 || discMax > 1) {
        conflict = true
        reason = `conflicting evidence (${disc.map((d) => d.code).join(', ')}) exceeds the ≤1-supporting allowance → VUS`
      }
    }
    tier = conflict ? 'VUS' : tierByNet(net, benignCut)
  }

  const applied: AppliedCriterion[] = [
    ...pEl.map((e) => ({ code: e.code, direction: 'pathogenic' as const, strength: e.strength, points: e.pts })),
    ...bEl.map((e) => ({
      code: e.code,
      direction: 'benign' as const,
      strength: e.strength,
      points: e.code === 'BA1' ? 0 : -e.pts,
    })),
  ]

  return {
    sumPathogenic,
    sumBenign,
    net,
    tier,
    conflict,
    reason,
    ba1,
    modelPosterior: ba1 ? null : modelPosterior(net),
    dependencyNotes,
    applied,
  }
}

/** Codes that are mutually exclusive with an already-on criterion (so the UI can
 *  disable them). Mirrors the vault's `excl` blocking. */
export function blockedCodes(state: CriteriaState): Set<string> {
  const blocked = new Set<string>()
  for (const def of CRITERIA) {
    if (state[def.code]?.on) for (const x of def.excl) blocked.add(x)
  }
  return blocked
}

/**
 * Seed a teaching state from a real engine classification — the variant's
 * triggered `per_criterion` become the ticked criteria at their applied strength.
 * This is what lets the report's explainer open pre-ticked to *this variant's*
 * call so a clinician can ask "what if PS3 were Strong?" from the real evidence.
 * Untriggered/demoted rows stay off; unknown codes are ignored. A fixed-strength
 * code keeps its default; a variable one takes the applied strength when valid.
 */
export function criteriaStateFromComputed(computed: EamosComputedClassification): CriteriaState {
  const state = initialCriteriaState()
  for (const c of computed.per_criterion) {
    if (!c.triggered) continue
    const def = CRITERIA_BY_CODE[c.code]
    if (!def) continue
    let strength: CriteriaStrength = def.def
    const s = c.applied_strength
    if (s === 'very_strong' || s === 'strong' || s === 'moderate' || s === 'supporting') {
      strength = def.strengths.length === 0 ? def.def : def.strengths.includes(s) ? s : def.def
    } else if (c.code === 'BA1') {
      strength = 'stand_alone'
    }
    state[c.code] = { on: true, strength }
  }
  return state
}
