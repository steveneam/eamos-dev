/* ───────────────────────────────────────────────────────────────────────
   Workbench v2 gene-window builders + consequence prediction.

   Ported from `e:\Web tool\Claude Design\Workbench v2\data.js`
   (buildFlatWindow / buildCodons / translateTriplet / consequenceAt),
   restructured as pure functions over a `GeneWindowData` argument so they
   are testable in isolation. The shared codon/AA tables live in
   `codon-table.ts`; this module owns the intron/splice-aware window model.
─────────────────────────────────────────────────────────────────────── */

import { aaThree, codonTable, type Base, type EditBase } from './codon-table'

export type ClinClass = 'p' | 'lp' | 'vus' | 'lb' | 'b'

/** A coding exon segment. `cdsStart`/`cdsEnd` are 1-based CDS coordinates. */
export interface ExonInfo {
  num: number
  cdsStart: number
  cdsEnd: number
  genomicLen: number
}

export interface IntronInfo {
  num: number
  lenBp: number
}

/** A contiguous slice of the transcript shown in the viewer window. */
export type WindowSegment =
  | { kind: 'exon'; exonNum: number; cdsStart: number; cdsEnd: number; seq: string }
  | {
      kind: 'intron'
      intronNum: number
      totalLen: number
      /** 5′ donor flank (lowercase). */
      fiveSeq: string
      /** 3′ acceptor flank (lowercase). */
      threeSeq: string
    }

export interface QueriedVariant {
  cdsPos: number
  refBase: Base
  altBase: Base
  codonNumber: number
  codonOffset: number
  aaRef: string
  aaAlt: string
  hgvsP: string
  hgvsC: string
  classification: ClinClass
}

export interface ClinvarVariant {
  /** CDS position, or an HGVS intronic offset string like `231+1`. */
  cdsPos: number | string
  hgvsC: string
  hgvsP: string
  cls: ClinClass
  cv: string
  queried?: boolean
  splice?: boolean
}

export interface DomainInfo {
  aaStart: number
  aaEnd: number
  label: string
  shortLabel?: string
}

export interface ProteinFeatures {
  signalPeptide: { aaStart: number; aaEnd: number } | null
  transmembrane: Array<{ aaStart: number; aaEnd: number; label: string }>
  domains: Array<{ aaStart: number; aaEnd: number; label: string }>
  activeSites: Array<{ aa: number; residue: string; label: string }>
  membraneBinding: Array<{ aaStart: number; aaEnd: number; label: string }>
  palmitoylation: Array<{ aa: number; residue: string; label: string }>
}

export interface RestrictionSite {
  name: string
  site: string
  /** First base of the recognition site, as a flat-window index. */
  flatPos: number
}

export interface WindowFeature {
  type: 'oligo'
  cdsStart: number
  cdsEnd: number
  label: string
}

export interface GeneWindowData {
  gene: string
  transcript: string
  ensg: string
  chrom: string
  nativeStrand: 'forward' | 'reverse'

  geneLength: number
  totalExons: number
  cdsLength: number
  proteinLength: number
  utr5Length: number
  utr3Length: number
  mrnaLength: number

  exons: ExonInfo[]
  introns: IntronInfo[]
  windowSegments: WindowSegment[]
  queriedVariant: QueriedVariant
  clinvar: ClinvarVariant[]
  exonVariantCount: Record<number, number>
  domains: DomainInfo[]
  proteinFeatures: ProteinFeatures
  genomicCoords: { chrom: string; start: number; end: number; strand: '+' | '-' }
  conservation: number[]
  restriction: RestrictionSite[]
  features: WindowFeature[]
}

// ─── Flat window ────────────────────────────────────────────────────────

export type FlatBase =
  | {
      flatPos: number
      base: string
      kind: 'exon'
      exonNum: number
      cdsPos: number
    }
  | {
      flatPos: number
      base: string
      kind: 'intron'
      intronNum: number
      intronEnd: '5prime' | '3prime'
      intronOffset: number
      isSplice: boolean
    }
  | {
      flatPos: number
      base: string
      kind: 'intron-gap'
      intronNum: number
      intronOmitted: number
    }

/**
 * Flatten `windowSegments` into a base-per-cell array. Exon bases carry CDS
 * coords; intron flanks carry signed offsets (+N from the preceding exon end,
 * −N from the following exon start) and a splice flag for the GT/AG dinucs.
 * Each truncated intron contributes one `intron-gap` ellipsis cell.
 */
export function buildFlatWindow(data: GeneWindowData): FlatBase[] {
  const bases: FlatBase[] = []
  let i = 0
  data.windowSegments.forEach((seg) => {
    if (seg.kind === 'exon') {
      seg.seq.split('').forEach((ch, k) => {
        bases.push({
          flatPos: i++,
          base: ch.toUpperCase(),
          kind: 'exon',
          exonNum: seg.exonNum,
          cdsPos: seg.cdsStart + k,
        })
      })
    } else {
      const five = seg.fiveSeq.split('')
      five.forEach((ch, k) => {
        bases.push({
          flatPos: i++,
          base: ch.toLowerCase(),
          kind: 'intron',
          intronNum: seg.intronNum,
          intronEnd: '5prime',
          intronOffset: k + 1,
          isSplice: k === 0 || k === 1,
        })
      })
      bases.push({
        flatPos: i++,
        base: '…',
        kind: 'intron-gap',
        intronNum: seg.intronNum,
        intronOmitted: seg.totalLen - seg.fiveSeq.length - seg.threeSeq.length,
      })
      const three = seg.threeSeq.split('')
      three.forEach((ch, k) => {
        const offsetFromAcceptor = three.length - k
        bases.push({
          flatPos: i++,
          base: ch.toLowerCase(),
          kind: 'intron',
          intronNum: seg.intronNum,
          intronEnd: '3prime',
          intronOffset: -offsetFromAcceptor,
          isSplice: k === three.length - 2 || k === three.length - 1,
        })
      })
    }
  })
  return bases
}

export interface Codon {
  codonNum: number
  bases: [number, number, number]
  cdsPositions: [number, number, number]
  spansSplice: boolean
}

/** Reading-frame triplets along the spliced CDS (exon bases only). */
export function buildCodons(flat: FlatBase[]): Codon[] {
  const exonOnly = flat.filter(
    (b): b is Extract<FlatBase, { kind: 'exon' }> => b.kind === 'exon',
  )
  const codons: Codon[] = []
  for (let i = 0; i + 2 < exonOnly.length; i += 3) {
    const a = exonOnly[i]
    const b = exonOnly[i + 1]
    const c = exonOnly[i + 2]
    codons.push({
      codonNum: Math.ceil(a.cdsPos / 3),
      bases: [a.flatPos, b.flatPos, c.flatPos],
      cdsPositions: [a.cdsPos, b.cdsPos, c.cdsPos],
      spansSplice: !(a.exonNum === b.exonNum && b.exonNum === c.exonNum),
    })
  }
  return codons
}

export function translateTriplet(triplet: string): string {
  if (!triplet || triplet.length !== 3) return '?'
  if (triplet.includes('-') || triplet.includes('…')) return '-'
  return codonTable[triplet.toUpperCase()] || '?'
}

export type ConsequenceKind =
  | 'synonymous'
  | 'missense'
  | 'stop'
  | 'frameshift'
  | 'splice'
  | 'intronic'
  | 'unknown'

export interface Consequence {
  kind: ConsequenceKind
  label: string
  detail: string
}

/**
 * Predict the consequence of substituting (or `-`-deleting) the base at flat
 * index `flatIdx`. Intronic positions return splice-/intronic-specific kinds.
 */
export function consequenceAt(
  flat: FlatBase[],
  flatIdx: number,
  newBase: EditBase,
): Consequence {
  const pos = flat[flatIdx]
  if (!pos) return { kind: 'unknown', label: 'Unknown', detail: '' }

  if (newBase === '-') {
    if (pos.kind === 'exon')
      return {
        kind: 'frameshift',
        label: 'Frameshift',
        detail: `Single-base deletion at c.${pos.cdsPos} shifts reading frame; premature stop predicted downstream.`,
      }
    if (pos.kind === 'intron' && pos.isSplice)
      return {
        kind: 'splice',
        label: 'Splice signal disruption',
        detail: `Deletes a base of the canonical ${
          pos.intronEnd === '5prime' ? 'donor (GT)' : 'acceptor (AG)'
        } splice signal of intron ${pos.intronNum}.`,
      }
    return {
      kind: 'intronic',
      label: 'Deep intronic deletion',
      detail:
        'Single-base deletion in intronic sequence away from canonical splice signals; likely no impact on splicing.',
    }
  }

  if (pos.kind === 'intron') {
    if (pos.isSplice)
      return {
        kind: 'splice',
        label: 'Splice signal disruption',
        detail: `Alters a base of the canonical ${
          pos.intronEnd === '5prime' ? '5′ donor (GT)' : '3′ acceptor (AG)'
        } dinucleotide of intron ${pos.intronNum}; predicted to abolish splicing.`,
      }
    if (Math.abs(pos.intronOffset) <= 6)
      return {
        kind: 'splice',
        label: 'Near-splice region',
        detail: `Position is within 6 nt of the ${
          pos.intronEnd === '5prime' ? 'donor' : 'acceptor'
        } of intron ${pos.intronNum}; may weaken splicing.`,
      }
    return {
      kind: 'intronic',
      label: 'Deep intronic',
      detail: `Position is ${Math.abs(pos.intronOffset)} nt into intron ${
        pos.intronNum
      }; unlikely to affect splicing without specific evidence.`,
    }
  }

  if (pos.kind !== 'exon') return { kind: 'unknown', label: 'Unknown', detail: '' }

  const flatExons = flat.filter(
    (b): b is Extract<FlatBase, { kind: 'exon' }> => b.kind === 'exon',
  )
  const idxInCds = flatExons.findIndex((b) => b.flatPos === flatIdx)
  if (idxInCds < 0) return { kind: 'unknown', label: 'Unknown', detail: '' }
  const codonStart = idxInCds - (idxInCds % 3)
  const refTriplet = flatExons
    .slice(codonStart, codonStart + 3)
    .map((b) => b.base)
    .join('')
  const offset = idxInCds - codonStart
  const altTriplet =
    refTriplet.substr(0, offset) + newBase + refTriplet.substr(offset + 1)
  const refAA = codonTable[refTriplet]
  const altAA = codonTable[altTriplet]
  const codonNum = Math.ceil(flatExons[codonStart].cdsPos / 3)

  if (refAA === altAA)
    return {
      kind: 'synonymous',
      label: 'Synonymous',
      detail: `${refTriplet}→${altTriplet} both encode ${
        aaThree[refAA] || refAA
      }${codonNum}. No protein change.`,
    }
  if (altAA === '*')
    return {
      kind: 'stop',
      label: 'Stop gained',
      detail: `${refTriplet}→${altTriplet} introduces a premature stop at codon ${codonNum} (p.${aaThree[refAA]}${codonNum}*).`,
    }
  return {
    kind: 'missense',
    label: 'Missense',
    detail: `p.${aaThree[refAA]}${codonNum}${aaThree[altAA]} — ${refTriplet}→${altTriplet}.`,
  }
}

export const COMPLEMENT: Record<string, string> = {
  A: 'T', T: 'A', C: 'G', G: 'C',
  a: 't', t: 'a', c: 'g', g: 'c',
  N: 'N', '-': '-', '…': '…',
}

/** Human label for a flat base position (c.260 / c.231+1 / —). */
export function posDisplay(data: GeneWindowData, b: FlatBase | undefined): string {
  if (!b) return '—'
  if (b.kind === 'exon') return `c.${b.cdsPos}`
  if (b.kind === 'intron') {
    const ex =
      b.intronEnd === '5prime'
        ? data.exons.find((e) => e.num === b.intronNum)
        : data.exons.find((e) => e.num === b.intronNum + 1)
    if (!ex) return '—'
    const edge = b.intronEnd === '5prime' ? ex.cdsEnd : ex.cdsStart
    return `c.${edge}${b.intronOffset > 0 ? '+' : ''}${b.intronOffset}`
  }
  return '—'
}

export function classLabel(cls: ClinClass): string {
  return (
    { p: 'Pathogenic', lp: 'Likely Pathogenic', vus: 'VUS', lb: 'Likely Benign', b: 'Benign' }[
      cls
    ] || cls
  )
}
