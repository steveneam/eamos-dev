import { describe, it, expect } from 'vitest'
import { classify, cleanQuery, isLikelyUnparseable } from './variant-format'

describe('cleanQuery', () => {
  it('strips a leading GENE: / accession: prefix when an HGVS token follows', () => {
    expect(cleanQuery('RPE65:c.260A>G')).toBe('c.260A>G')
    expect(cleanQuery('NM_000329.3:c.260A>G')).toBe('c.260A>G')
    expect(cleanQuery('RPE65:p.Asp87Gly')).toBe('p.Asp87Gly')
  })

  it('collapses internal whitespace but never lowercases HGVS', () => {
    expect(cleanQuery('  RPE65   c.260A>G ')).toBe('RPE65 c.260A>G')
    // A>G and p.Asp87Gly are case-significant — must survive verbatim.
    expect(cleanQuery('RPE65:c.260A>G')).toContain('A>G')
    expect(cleanQuery('RPE65:p.Asp87Gly')).toBe('p.Asp87Gly')
  })

  it('leaves bare rsIDs / coords untouched (no spurious prefix strip)', () => {
    expect(cleanQuery('rs61752871')).toBe('rs61752871')
    expect(cleanQuery('chr1:68444869:T:C')).toBe('chr1:68444869:T:C')
  })
})

describe('isLikelyUnparseable — every MalformedBlock "try this" example must reach the request', () => {
  // Mirrors the examples listed in ReportPage's MalformedBlock. The split is
  // (gene, cdna) as the search form / URL params actually deliver them.
  const helpExamples: [string, string, string][] = [
    ['Gene + cDNA', 'RPE65', 'c.260A>G'],
    ['Transcript HGVS (gene + accession-prefixed cdna)', 'RPE65', 'NM_000329.3:c.260A>G'],
    ['Protein', 'RPE65', 'p.Asp87Gly'],
    ['dbSNP (the regression — was blocked client-side)', 'RPE65', 'rs61752871'],
  ]

  for (const [label, gene, cdna] of helpExamples) {
    it(`does NOT flag "${label}" as unparseable`, () => {
      expect(isLikelyUnparseable(gene, cdna)).toBe(false)
    })
  }

  it('still flags genuine garbage / empty input', () => {
    expect(isLikelyUnparseable('RPE65', '???not-a-variant???')).toBe(true)
    expect(isLikelyUnparseable('RPE65', 'hello world')).toBe(true)
    expect(isLikelyUnparseable('', '')).toBe(true)
  })
})

describe('genomic coordinate inputs reach the request (cross-check HIGH-2)', () => {
  // The backend `normalize_variant_query` classifies all of these as
  // `genomic` and accepts them; the client guard must NOT short-circuit them
  // to the malformed state. VCF-quad forms (`:`/`-` separated, no `>`) were
  // the regression.
  const coords = [
    '1-68444869-T-C',
    'chr1:68444869:T:C',
    'chr1:68444869:T>C',
    'chr1:g.68444869T>C',
  ]

  for (const c of coords) {
    it(`classifies "${c}" as coord, not unknown`, () => {
      expect(classify(c)).toBe('coord')
    })
    it(`does NOT flag "${c}" as unparseable`, () => {
      expect(isLikelyUnparseable('RPE65', c)).toBe(false)
    })
  }
})
