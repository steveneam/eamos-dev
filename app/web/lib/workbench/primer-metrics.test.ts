import { describe, it, expect } from 'vitest'
import { classifyPair, parseNotes } from './primer-metrics'
import { PRIMER_SAMPLE } from './primer-sample'
import type { PrimerPair } from '@/lib/backend'

const [p1, p2, p3] = PRIMER_SAMPLE.pairs

describe('classifyPair — RPE65 primer fixture', () => {
  it('pair #1 (1 hit, balanced Tm, flanks target) → Specific / teal', () => {
    const c = classifyPair(p1)
    expect(c.badge.key).toBe('specific')
    expect(c.badge.label).toBe('Specific')
    expect(c.badge.tone).toBe('teal')
    expect(c.deltaTmWarn).toBe(false)
    expect(c.spansTarget).toBe(true)
  })

  it('pair #2 (1 hit, ΔTm 2.6 > 2) → Thermo warning + amber ΔTm gauge', () => {
    const c = classifyPair(p2)
    expect(c.badge.key).toBe('thermo')
    expect(c.badge.tone).toBe('warn')
    expect(c.deltaTm).toBeCloseTo(2.6, 5)
    expect(c.deltaTmWarn).toBe(true)
  })

  it('pair #3 (2 specificity hits) → Off-target risk / err', () => {
    const c = classifyPair(p3)
    expect(c.badge.key).toBe('offtarget')
    expect(c.badge.label).toBe('Off-target risk')
    expect(c.badge.tone).toBe('err')
  })
})

describe('classifyPair — synthetic edges', () => {
  const base: PrimerPair = {
    index: 9,
    forward: 'A',
    reverse: 'T',
    tm_forward: 60,
    tm_reverse: 60,
    gc_forward: 50,
    gc_reverse: 50,
    product_size: 400,
    specificity_hits: 1,
    notes: 'single specific hit; spans the queried base.',
    recommended: false,
  }

  it('0 specificity hits → Check orientation / warn', () => {
    const c = classifyPair({ ...base, specificity_hits: 0 })
    expect(c.badge.key).toBe('orientation')
    expect(c.badge.label).toBe('Check orientation')
    expect(c.badge.tone).toBe('warn')
  })

  it('negative specificity hits are treated as an orientation concern', () => {
    const c = classifyPair({ ...base, specificity_hits: -1 })
    expect(c.badge.key).toBe('orientation')
    expect(c.badge.tone).toBe('warn')
  })

  it('synthetic ΔTm > 2 → Thermo warning + amber gauge flag', () => {
    const c = classifyPair({ ...base, tm_forward: 58, tm_reverse: 62.5 })
    expect(c.deltaTm).toBeCloseTo(4.5, 5)
    expect(c.deltaTmWarn).toBe(true)
    expect(c.badge.key).toBe('thermo')
  })

  it('GC outside 35–70 → thermo flag even with 1 clean hit', () => {
    const c = classifyPair({ ...base, gc_forward: 78 })
    expect(c.gcOutOfBand).toBe(true)
    expect(c.thermoFlag).toBe(true)
    expect(c.badge.key).toBe('thermo')
  })

  it('1 clean hit but notes explicitly "does not span" → Check orientation', () => {
    const c = classifyPair({
      ...base,
      notes: 'Single hit but does not span the queried base.',
    })
    expect(c.spansTarget).toBe(false)
    expect(c.badge.key).toBe('orientation')
  })
})

describe('parseNotes — defensive, never throws', () => {
  it('extracts the fixture pair #1 prose', () => {
    const n = parseNotes(p1.notes)
    expect(n.raw).toBe(p1.notes)
    expect(n.spansTarget).toBe(true) // "flanks c.260…"
  })

  it('extracts provider, product sizes and the Primer-BLAST caveat', () => {
    const n = parseNotes(
      'Provider ucsc_isPcr; products 487/512 bp; spans queried base. ' +
        'This is not an NCBI Primer-BLAST validation.',
    )
    expect(n.provider).toBe('ucsc_ispcr')
    expect(n.productSizes).toBe('487/512 bp')
    expect(n.spansTarget).toBe(true)
    expect(n.primerBlastCaveat).toMatch(/not an NCBI Primer-BLAST/i)
  })

  it('does not treat a Primer-BLAST caveat as the specificity provider', () => {
    const n = parseNotes('This is not an NCBI Primer-BLAST validation.')
    expect(n.provider).toBeUndefined()
    expect(n.primerBlastCaveat).toMatch(/not an NCBI Primer-BLAST/i)
  })

  it('keeps negative span wording from being classified as spanning', () => {
    expect(parseNotes('Single product, not spanning the queried base.').spansTarget).toBe(false)
    expect(parseNotes('Single product fails to flank the queried base.').spansTarget).toBe(false)
  })

  it('degrades to raw on unmatched prose without throwing', () => {
    const weird = 'lorem ipsum {[(*&^%$#@!'
    const n = parseNotes(weird)
    expect(n.raw).toBe(weird)
    expect(n.provider).toBeUndefined()
    expect(n.spansTarget).toBeUndefined()
  })

  it('handles undefined / null / empty without throwing', () => {
    expect(() => parseNotes(undefined)).not.toThrow()
    expect(() => parseNotes(null)).not.toThrow()
    expect(parseNotes(undefined).raw).toBe('')
    expect(parseNotes('').raw).toBe('')
  })
})
