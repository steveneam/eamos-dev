import { describe, expect, it } from 'vitest'
import {
  aggregateEvidenceLikelihoodRatio,
  gaugeBands,
  gaugeBoundaries,
  modelPosterior,
  modelPosteriorOdds,
  modelPriorOdds,
  netBoundaries,
  tierByNet,
  TIER_ORDER,
  tierTokens,
} from './points'

// These pin the FE mirror to the backend acmg_points_engine.py exact values
// (docs/report-acmg-viz/spec.md §3). If an anchor here drifts, the gauge/plane/
// waterfall geometry has silently diverged from the engine — a clinical-accuracy
// bug, not a cosmetic one.

const pct1 = (n: number) => Number((modelPosterior(n) * 100).toFixed(1))

describe('modelPosterior() anchors (aggregate LR 2.08^net, prior 0.10)', () => {
  it('hits the spec §3 anchor percentages', () => {
    expect(pct1(0)).toBe(10.0)
    expect(pct1(6)).toBe(90.0)
    expect(pct1(9)).toBe(98.8)
    expect(pct1(10)).toBe(99.4)
    expect(pct1(-1)).toBe(5.1)
    expect(pct1(-7)).toBe(0.1)
  })

  it('is monotonic increasing in net and bounded to (0,1)', () => {
    let prev = -1
    for (let n = -12; n <= 14; n++) {
      const p = modelPosterior(n)
      expect(p).toBeGreaterThan(0)
      expect(p).toBeLessThan(1)
      expect(p).toBeGreaterThan(prev)
      prev = p
    }
  })

  it('uses 2.08^net, NOT 2.08^(net/8)', () => {
    expect(aggregateEvidenceLikelihoodRatio(1)).toBeCloseTo(2.08, 10)
    expect(aggregateEvidenceLikelihoodRatio(8)).toBeGreaterThan(100)
    expect(modelPriorOdds()).toBeCloseTo(1 / 9, 10)
    expect(modelPosteriorOdds(8)).toBeCloseTo(
      aggregateEvidenceLikelihoodRatio(8) * modelPriorOdds(),
      10,
    )
  })
})

describe('tierByNet() — Tavtigian-2020 default cuts (ADR-0022)', () => {
  const cut = 'tavtigian_2020' as const
  it('P ≥ +10 · LP +6..+9 · VUS 0..+5 · LB −1..−6 · B ≤ −7', () => {
    expect(tierByNet(10, cut)).toBe('Pathogenic')
    expect(tierByNet(14, cut)).toBe('Pathogenic')
    expect(tierByNet(9, cut)).toBe('Likely Pathogenic')
    expect(tierByNet(6, cut)).toBe('Likely Pathogenic')
    expect(tierByNet(5, cut)).toBe('VUS')
    expect(tierByNet(0, cut)).toBe('VUS')
    expect(tierByNet(-1, cut)).toBe('Likely Benign')
    expect(tierByNet(-6, cut)).toBe('Likely Benign')
    expect(tierByNet(-7, cut)).toBe('Benign')
    expect(tierByNet(-12, cut)).toBe('Benign')
  })
})

describe('tierByNet() — acgs_panel exception (VCEP overlay only)', () => {
  const cut = 'acgs_panel' as const
  it('LB −1..−5 · B ≤ −6 (pathogenic side unchanged)', () => {
    expect(tierByNet(-5, cut)).toBe('Likely Benign')
    expect(tierByNet(-6, cut)).toBe('Benign')
    expect(tierByNet(-7, cut)).toBe('Benign')
    // pathogenic + VUS edges identical to the default cut
    expect(tierByNet(10, cut)).toBe('Pathogenic')
    expect(tierByNet(6, cut)).toBe('Likely Pathogenic')
    expect(tierByNet(0, cut)).toBe('VUS')
  })
})

describe('netBoundaries()', () => {
  it('shifts only the benign lower edge by cut', () => {
    expect(netBoundaries('tavtigian_2020').likelyBenign).toBe(-6)
    expect(netBoundaries('acgs_panel').likelyBenign).toBe(-5)
    expect(netBoundaries('tavtigian_2020').pathogenic).toBe(10)
    expect(netBoundaries('acgs_panel').pathogenic).toBe(10)
  })
})

describe('gaugeBands() — net-points axis', () => {
  for (const cut of ['tavtigian_2020', 'acgs_panel'] as const) {
    it(`${cut}: 5 contiguous bands spanning the net domain in tier order`, () => {
      const bands = gaugeBands(cut, -10, 13)
      expect(bands.map((b) => b.tier)).toEqual([...TIER_ORDER])
      expect(bands[0].from).toBe(-10)
      expect(bands[bands.length - 1].to).toBe(13)
      for (let i = 1; i < bands.length; i++) {
        expect(bands[i].from).toBeCloseTo(bands[i - 1].to, 10) // contiguous
        expect(bands[i].from).toBeGreaterThan(bands[i - 1].from) // strictly increasing
      }
    })
  }

  it('places tier boundaries on the half-integer between net scores', () => {
    const bands = gaugeBands('tavtigian_2020')
    const band = (t: string) => bands.find((x) => x.tier === t)!
    expect(band('VUS').from).toBe(-0.5) // LB | VUS divider
    expect(band('VUS').to).toBe(5.5) // VUS | LP divider
    expect(band('Pathogenic').from).toBe(9.5) // LP | P divider
    // an exact net +6 marker falls inside Likely Pathogenic
    expect(6).toBeGreaterThan(band('Likely Pathogenic').from)
    expect(6).toBeLessThan(band('Likely Pathogenic').to)
  })
})

describe('gaugeBoundaries() — model posterior at each tier divider', () => {
  it('maps the four dividers to the model-posterior labels', () => {
    const bnd = gaugeBoundaries('tavtigian_2020')
    expect(bnd.map((b) => b.net)).toEqual([-6.5, -0.5, 5.5, 9.5])
    const p = bnd.map((b) => Number(b.modelPosterior.toFixed(2)))
    expect(p[1]).toBe(0.07) // ~LB|VUS  (prior-ish)
    expect(p[2]).toBe(0.86) // ~VUS|LP
    expect(p[3]).toBe(0.99) // ~LP|P
  })
})

describe('tierTokens()', () => {
  it('maps each tier to its --cls-* ramp key', () => {
    expect(tierTokens('Pathogenic').band).toBe('var(--cls-path-bg)')
    expect(tierTokens('Likely Pathogenic').ink).toBe('var(--cls-lpath-text)')
    expect(tierTokens('VUS').edge).toBe('var(--cls-vus-bdr)')
    expect(tierTokens('Likely Benign').band).toBe('var(--cls-lben-bg)')
    expect(tierTokens('Benign').band).toBe('var(--cls-ben-bg)')
  })
})
