/* Row layout for the v2 sequence viewer's CodonDetail.

   Splits the flat window into fixed-size rows of `rowBp` real bases, with each
   truncated intron's ellipsis cell flushing the current row and emitting its
   own gap separator. Extracted from `CodonDetail.tsx` as a pure function so the
   chunking + intron-gap interaction can be unit-tested without a DOM. */

import type { FlatBase } from './gene-window'

export type LayoutItem =
  | { kind: 'row'; indices: number[] }
  | { kind: 'gap'; intronNum: number; omitted: number }

/** Floor for bases-per-row so a very narrow manual setting stays usable. */
export const MIN_BP = 12

/**
 * Group flat-window indices into rows of at most `rowBp` real bases. An
 * `intron-gap` cell ends the current row (even if partial) and becomes its own
 * `gap` item, so omitted-intron separators always sit between rows.
 */
export function buildLayout(flat: FlatBase[], rowBp: number): LayoutItem[] {
  const items: LayoutItem[] = []
  let cur: number[] = []
  flat.forEach((b, i) => {
    if (b.kind === 'intron-gap') {
      if (cur.length) {
        items.push({ kind: 'row', indices: cur })
        cur = []
      }
      items.push({ kind: 'gap', intronNum: b.intronNum, omitted: b.intronOmitted })
      return
    }
    cur.push(i)
    if (cur.length >= rowBp) {
      items.push({ kind: 'row', indices: cur })
      cur = []
    }
  })
  if (cur.length) items.push({ kind: 'row', indices: cur })
  return items
}
