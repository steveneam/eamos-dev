import { describe, it, expect } from 'vitest'
import { mapGuide, revComp } from './crispr-guide-map'
import { recommendedGuideIndex } from './crispr-guide-ranking'
import { CRISPR_SAMPLE } from './crispr-sample'
import type { CrisprGuide } from '@/lib/backend'

const TEMPLATE = CRISPR_SAMPLE.ssodn!.reference_arm
const [g1, g2, g3] = CRISPR_SAMPLE.guides

describe('revComp', () => {
  it('is an involution on A/T/C/G', () => {
    const s = 'GAATGGCGACTGTCTTGTCC'
    expect(revComp(revComp(s))).toBe(s)
  })
  it('reverse-complements correctly', () => {
    expect(revComp('GAATGGCGACTGTCTTGTCC')).toBe('GGACAAGACAGTCGCCATTC')
  })
})

describe('mapGuide — RPE65 fixture guides on the ssODN reference arm', () => {
  it('+ guide 1 maps spacer at idx 1 with PAM 3′ and cut 3 bp inward', () => {
    const m = mapGuide(g1, TEMPLATE)
    expect(m.located).toBe(true)
    expect(m.spacerStart).toBe(1)
    expect(m.spacerEnd).toBe(21)
    expect(m.spacerOnPlus).toBe('GGACAAGACAGTCGCCATTC')
    expect([m.pamStart, m.pamEnd]).toEqual([21, 24])
    expect(TEMPLATE.slice(m.pamStart!, m.pamEnd!)).toBe('GGT')
    expect(m.cutIndex).toBe(18)
  })

  it('+ guide 2 maps spacer at idx 4', () => {
    const m = mapGuide(g2, TEMPLATE)
    expect(m.located).toBe(true)
    expect(m.spacerStart).toBe(4)
    expect(m.spacerEnd).toBe(24)
    expect([m.pamStart, m.pamEnd]).toEqual([24, 27])
    expect(m.cutIndex).toBe(21)
  })

  it('- guide 3 matches its reverse complement on the + strand', () => {
    const m = mapGuide(g3, TEMPLATE)
    expect(m.located).toBe(true)
    expect(m.spacerOnPlus).toBe('GGACAAGACAGTCGCCATTC')
    expect(m.spacerStart).toBe(1)
    // PAM lies 5′ of idx 1 → only 1 bp of headroom for a 3 bp PAM → off-edge.
    expect(m.pamStart).toBeNull()
    expect(m.pamEnd).toBeNull()
    expect(m.cutIndex).toBe(4)
  })

  it('returns not-located (no throw) when the spacer is absent', () => {
    const ghost: CrisprGuide = { ...g1, guide: 'AAAAAAAAAAAAAAAAAAAA' }
    const m = mapGuide(ghost, TEMPLATE)
    expect(m.located).toBe(false)
    expect(m.spacerStart).toBe(-1)
    expect(m.cutIndex).toBeNull()
  })

  it('clamps the PAM to null when a + spacer ends flush with the template', () => {
    const tpl = 'AAAAAGGACAAGACAGTCGCCATTC' // spacer ends at the last base
    const m = mapGuide(g1, tpl)
    expect(m.located).toBe(true)
    expect(m.spacerEnd).toBe(tpl.length)
    expect(m.pamStart).toBeNull()
    expect(m.cutIndex).toBe(tpl.length - 3)
  })
})

describe('recommendedGuideIndex', () => {
  const base: CrisprGuide = {
    index: 10,
    cut_position: 26,
    strand: '+',
    guide: 'GGACAAGACAGTCGCCATTC',
    pam: 'GGT',
    on_target_score: 70,
    off_target_score: 20,
    gc_percent: 60,
  }

  it('returns the guide index with the lowest off-target score', () => {
    expect(
      recommendedGuideIndex([
        { ...base, index: 10, off_target_score: 22 },
        { ...base, index: 42, off_target_score: 12 },
        { ...base, index: 99, off_target_score: 18 },
      ]),
    ).toBe(42)
  })

  it('does not treat guide indexes as array offsets', () => {
    expect(
      recommendedGuideIndex([
        { ...base, index: 7, off_target_score: 30 },
        { ...base, index: 11, off_target_score: 10 },
      ]),
    ).toBe(11)
  })

  it('returns -1 when no guides are available', () => {
    expect(recommendedGuideIndex([])).toBe(-1)
  })
})
