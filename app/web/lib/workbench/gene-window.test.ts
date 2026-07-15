import { describe, it, expect } from 'vitest'
import {
  buildCodons,
  buildFlatWindow,
  consequenceAt,
  translateTriplet,
  type FlatBase,
} from './gene-window'
import { RPE65_V2 } from './sample-rpe65-v2'

const flat = buildFlatWindow(RPE65_V2)
const codons = buildCodons(flat)

function flatIdxOfCds(cds: number): number {
  return flat.findIndex((b) => b.kind === 'exon' && b.cdsPos === cds)
}

describe('buildFlatWindow', () => {
  it('flattens exon/intron/gap segments with one gap cell per truncated intron', () => {
    // 15 exon3 + (30 + 1 gap + 30) intron3 + 93 exon4
    //  + (30 + 1 gap + 30) intron4 + 15 exon5 = 245 cells.
    expect(flat.length).toBe(245)
    expect(flat.filter((b) => b.kind === 'intron-gap').length).toBe(2)
  })

  it('tags the GT donor / AG acceptor dinucleotides as splice bases', () => {
    const donor = flat.filter(
      (b): b is Extract<FlatBase, { kind: 'intron' }> =>
        b.kind === 'intron' && b.intronNum === 3 && b.intronEnd === '5prime',
    )
    expect(donor.slice(0, 2).every((b) => b.isSplice)).toBe(true)
    expect(donor[0].base).toBe('g')
    expect(donor[1].base).toBe('t')
  })

  it('does not add a gap cell when the full intron sequence is displayed', () => {
    const fullIntron = buildFlatWindow({
      ...RPE65_V2,
      windowSegments: [
        { kind: 'exon', exonNum: 1, cdsStart: 1, cdsEnd: 3, seq: 'ATG' },
        {
          kind: 'intron',
          intronNum: 1,
          totalLen: 4,
          fiveSeq: 'gt',
          threeSeq: 'ag',
        },
        { kind: 'exon', exonNum: 2, cdsStart: 4, cdsEnd: 6, seq: 'GAA' },
      ],
    })

    expect(fullIntron.some((b) => b.kind === 'intron-gap')).toBe(false)
    expect(fullIntron.map((b) => b.base).join('')).toBe('ATGgtagGAA')
  })
})

describe('buildCodons', () => {
  it('codon 87 covers c.259–261 and reads GAC (Asp) — guards the coherence fix', () => {
    const c87 = codons.find((c) => c.codonNum === 87)
    expect(c87).toBeDefined()
    expect(c87!.cdsPositions).toEqual([259, 260, 261])
    const triplet = c87!.bases.map((i) => flat[i].base).join('')
    expect(triplet).toBe('GAC')
    expect(translateTriplet(triplet)).toBe('D')
  })

  it('uses absolute CDS frame when the visible window starts mid-codon', () => {
    expect(buildCodons(midCodonFlat())).toEqual([
      {
        codonNum: 2,
        bases: [2, 3, 4],
        cdsPositions: [4, 5, 6],
        spansSplice: false,
      },
    ])
  })
})

describe('consequenceAt', () => {
  it('c.260 A>G is Missense p.Asp87Gly', () => {
    const c = consequenceAt(flat, flatIdxOfCds(260), 'G')
    expect(c.kind).toBe('missense')
    expect(c.detail.startsWith('p.Asp87Gly')).toBe(true)
  })

  it('deleting c.260 is a Frameshift', () => {
    expect(consequenceAt(flat, flatIdxOfCds(260), '-').kind).toBe('frameshift')
  })

  it('GAC→GAT (third base of codon 87) is Synonymous', () => {
    expect(consequenceAt(flat, flatIdxOfCds(261), 'T').kind).toBe('synonymous')
  })

  it('substituting a canonical GT donor base is a splice disruption', () => {
    const donorG = flat.findIndex(
      (b) =>
        b.kind === 'intron' &&
        b.intronNum === 3 &&
        b.intronEnd === '5prime' &&
        b.intronOffset === 1,
    )
    expect(consequenceAt(flat, donorG, 'A').kind).toBe('splice')
  })

  it('a deep-intronic substitution is reported as intronic', () => {
    const deep = flat.findIndex(
      (b) =>
        b.kind === 'intron' &&
        b.intronNum === 3 &&
        b.intronEnd === '5prime' &&
        b.intronOffset === 15,
    )
    expect(consequenceAt(flat, deep, 'A').kind).toBe('intronic')
  })

  it('predicts consequences from absolute CDS frame when the window starts mid-codon', () => {
    const c = consequenceAt(midCodonFlat(), 2, 'T')

    expect(c.kind).toBe('stop')
    expect(c.detail).toContain('GAA→TAA')
  })

  it('returns unknown when the full codon is not visible', () => {
    expect(consequenceAt(midCodonFlat(), 0, 'T').kind).toBe('unknown')
  })
})

function midCodonFlat(): FlatBase[] {
  return [
    { flatPos: 0, base: 'A', kind: 'exon', exonNum: 1, cdsPos: 2 },
    { flatPos: 1, base: 'C', kind: 'exon', exonNum: 1, cdsPos: 3 },
    { flatPos: 2, base: 'G', kind: 'exon', exonNum: 1, cdsPos: 4 },
    { flatPos: 3, base: 'A', kind: 'exon', exonNum: 1, cdsPos: 5 },
    { flatPos: 4, base: 'A', kind: 'exon', exonNum: 1, cdsPos: 6 },
  ]
}
