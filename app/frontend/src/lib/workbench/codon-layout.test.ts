import { describe, it, expect } from 'vitest'
import { buildLayout, MIN_BP, type LayoutItem } from './codon-layout'
import { buildFlatWindow, type FlatBase } from './gene-window'
import { RPE65_V2 } from './sample-rpe65-v2'

const flat = buildFlatWindow(RPE65_V2)
const nonGap = flat
  .map((b, i) => (b.kind === 'intron-gap' ? -1 : i))
  .filter((i) => i >= 0)
const gapCount = flat.filter((b) => b.kind === 'intron-gap').length

const rows = (items: LayoutItem[]) =>
  items.filter((it): it is Extract<LayoutItem, { kind: 'row' }> => it.kind === 'row')
const gaps = (items: LayoutItem[]) =>
  items.filter((it): it is Extract<LayoutItem, { kind: 'gap' }> => it.kind === 'gap')

// ── Tiny deterministic flat: 5 exon · gap · 4 exon (independent of sample) ──
function exon(flatPos: number, cdsPos: number): FlatBase {
  return { flatPos, base: 'A', kind: 'exon', exonNum: 1, cdsPos }
}
function gap(flatPos: number, intronNum: number, omitted: number): FlatBase {
  return { flatPos, base: '…', kind: 'intron-gap', intronNum, intronOmitted: omitted }
}

describe('buildLayout — invariants over the real RPE65 window', () => {
  for (const rowBp of [10, 13, 24, 30, 60, 1000]) {
    it(`rowBp=${rowBp}: rows reconstruct every non-gap index in order, ${gapCount} gaps preserved`, () => {
      const items = buildLayout(flat, rowBp)
      // Every non-gap flat index appears exactly once, in original order.
      expect(rows(items).flatMap((r) => r.indices)).toEqual(nonGap)
      // Each truncated intron still yields exactly one gap separator.
      expect(gaps(items)).toHaveLength(gapCount)
      // No row exceeds the cap; no empty rows.
      for (const r of rows(items)) {
        expect(r.indices.length).toBeGreaterThanOrEqual(1)
        expect(r.indices.length).toBeLessThanOrEqual(rowBp)
      }
      // Gap metadata is carried through (introns 3 then 4 in this window).
      expect(gaps(items).map((g) => g.intronNum)).toEqual([3, 4])
      expect(gaps(items).every((g) => g.omitted > 0)).toBe(true)
    })
  }

  it('rowBp larger than any run → one row per contiguous run (45 · 153 · 45)', () => {
    const items = buildLayout(flat, 1000)
    expect(rows(items).map((r) => r.indices.length)).toEqual([45, 153, 45])
    expect(items.map((it) => it.kind)).toEqual(['row', 'gap', 'row', 'gap', 'row'])
  })
})

describe('buildLayout — gap interaction on a deterministic flat', () => {
  const tiny: FlatBase[] = [
    exon(0, 1),
    exon(1, 2),
    exon(2, 3),
    exon(3, 4),
    exon(4, 5),
    gap(5, 1, 800),
    exon(6, 6),
    exon(7, 7),
    exon(8, 8),
    exon(9, 9),
  ]

  it('a gap flushes the current (even partial) row and starts a fresh one', () => {
    const items = buildLayout(tiny, 2)
    expect(items).toEqual([
      { kind: 'row', indices: [0, 1] },
      { kind: 'row', indices: [2, 3] },
      { kind: 'row', indices: [4] }, // partial row flushed by the gap
      { kind: 'gap', intronNum: 1, omitted: 800 },
      { kind: 'row', indices: [6, 7] },
      { kind: 'row', indices: [8, 9] },
    ])
  })

  it('a leading gap emits no empty row before it', () => {
    const items = buildLayout([gap(0, 2, 5), exon(1, 1), exon(2, 2)], 5)
    expect(items).toEqual([
      { kind: 'gap', intronNum: 2, omitted: 5 },
      { kind: 'row', indices: [1, 2] },
    ])
  })

  it('the trailing partial row is emitted', () => {
    const items = buildLayout([exon(0, 1), exon(1, 2), exon(2, 3)], 2)
    expect(items).toEqual([
      { kind: 'row', indices: [0, 1] },
      { kind: 'row', indices: [2] },
    ])
  })
})

describe('MIN_BP', () => {
  it('is a small positive floor for the dynamic row size', () => {
    expect(MIN_BP).toBeGreaterThanOrEqual(1)
    expect(Number.isInteger(MIN_BP)).toBe(true)
  })
})
