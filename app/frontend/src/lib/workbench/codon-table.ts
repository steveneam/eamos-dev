/* ───────────────────────────────────────────────────────────────────────
   Workbench codon table + consequence prediction.
   Ported verbatim from `e:\Web tool\Claude Design\Workbench\data.js`
   (translate / consequenceOf). `consequenceOf` is parameterised instead of
   bound to a `this.sequence` singleton so it is pure and unit-testable.
─────────────────────────────────────────────────────────────────────── */

export type Base = 'A' | 'T' | 'C' | 'G'
/** A pending edit value: a base, or '-' for a single-base deletion. */
export type EditBase = Base | '-'

export type ConsequenceKind = 'synonymous' | 'missense' | 'stop' | 'frameshift'

export interface Consequence {
  kind: ConsequenceKind
  label: string
  detail: string
}

export type AaClass =
  | 'hydro'
  | 'aroma'
  | 'cys'
  | 'polar'
  | 'basic'
  | 'acid'
  | 'stop'

// Standard genetic code. 1-letter codes; '*' = stop.
export const codonTable: Record<string, string> = {
  TTT: 'F', TTC: 'F', TTA: 'L', TTG: 'L',
  CTT: 'L', CTC: 'L', CTA: 'L', CTG: 'L',
  ATT: 'I', ATC: 'I', ATA: 'I', ATG: 'M',
  GTT: 'V', GTC: 'V', GTA: 'V', GTG: 'V',
  TCT: 'S', TCC: 'S', TCA: 'S', TCG: 'S',
  CCT: 'P', CCC: 'P', CCA: 'P', CCG: 'P',
  ACT: 'T', ACC: 'T', ACA: 'T', ACG: 'T',
  GCT: 'A', GCC: 'A', GCA: 'A', GCG: 'A',
  TAT: 'Y', TAC: 'Y', TAA: '*', TAG: '*',
  CAT: 'H', CAC: 'H', CAA: 'Q', CAG: 'Q',
  AAT: 'N', AAC: 'N', AAA: 'K', AAG: 'K',
  GAT: 'D', GAC: 'D', GAA: 'E', GAG: 'E',
  TGT: 'C', TGC: 'C', TGA: '*', TGG: 'W',
  CGT: 'R', CGC: 'R', CGA: 'R', CGG: 'R',
  AGT: 'S', AGC: 'S', AGA: 'R', AGG: 'R',
  GGT: 'G', GGC: 'G', GGA: 'G', GGG: 'G',
}

export const aaThree: Record<string, string> = {
  A: 'Ala', R: 'Arg', N: 'Asn', D: 'Asp', C: 'Cys',
  E: 'Glu', Q: 'Gln', G: 'Gly', H: 'His', I: 'Ile',
  L: 'Leu', K: 'Lys', M: 'Met', F: 'Phe', P: 'Pro',
  S: 'Ser', T: 'Thr', W: 'Trp', Y: 'Tyr', V: 'Val',
  '*': 'Stop',
}

// Biochemical class → AA-pill background tint key.
export const aaClass: Record<string, AaClass> = {
  A: 'hydro', V: 'hydro', L: 'hydro', I: 'hydro', P: 'hydro', G: 'hydro',
  F: 'aroma', W: 'aroma', Y: 'aroma',
  M: 'cys', C: 'cys',
  S: 'polar', T: 'polar', N: 'polar', Q: 'polar',
  K: 'basic', R: 'basic', H: 'basic',
  D: 'acid', E: 'acid',
  '*': 'stop',
}

/** Translate an in-frame DNA window to a 1-letter peptide. '?' for bad codons. */
export function translate(seq: string): string {
  let aa = ''
  for (let i = 0; i + 2 < seq.length; i += 3) {
    aa += codonTable[seq.substr(i, 3).toUpperCase()] || '?'
  }
  return aa
}

/**
 * Predict the consequence of swapping (or deleting) the base at window index
 * `idx` to `newBase`. `startingCodonNumber` is the protein codon number of the
 * first codon in `refSeq` (e.g. 78 for the RPE65 window).
 */
export function consequenceOf(
  refSeq: string,
  idx: number,
  newBase: EditBase,
  startingCodonNumber: number,
): Consequence {
  if (newBase === '-') {
    // Deletion → frameshift (single-base; multiple-of-3 in-frame deletion is M-002).
    return {
      kind: 'frameshift',
      label: 'Frameshift',
      detail:
        'Single-base deletion → reading-frame shift, premature stop predicted downstream.',
    }
  }
  const codonIdx = Math.floor(idx / 3)
  const codonOffset = idx % 3
  const refCodon = refSeq.substr(codonIdx * 3, 3)
  const altCodon =
    refCodon.substr(0, codonOffset) + newBase + refCodon.substr(codonOffset + 1)
  const refAA = codonTable[refCodon]
  const altAA = codonTable[altCodon]
  const aaNum = startingCodonNumber + codonIdx
  if (refAA === altAA) {
    return {
      kind: 'synonymous',
      label: 'Synonymous',
      detail: `${refCodon}→${altCodon} both encode ${aaThree[refAA] || refAA}${aaNum}. No protein change.`,
    }
  }
  if (altAA === '*') {
    return {
      kind: 'stop',
      label: 'Stop gained',
      detail: `${refCodon}→${altCodon} introduces a premature stop at codon ${aaNum} (p.${aaThree[refAA]}${aaNum}*).`,
    }
  }
  return {
    kind: 'missense',
    label: 'Missense',
    detail: `p.${aaThree[refAA]}${aaNum}${aaThree[altAA]} — ${refCodon}→${altCodon}.`,
  }
}
