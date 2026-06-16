// Cohort summary math for the batch results dashboard (spec §5.5b). Pure +
// side-effect free so the table render stays thin and the logic is testable
// without a DOM. Everything here derives from a BatchResult: the classification
// distribution from acmg/clinvar verdicts, and the variant-type / substitution
// breakdowns from the `CHROM-POS-REF-ALT` variant_key. Per the batch plan, the
// variant-derived summaries (type / indel / substitution / per-gene / panel
// coverage) light up from a parsed cohort today; the classification
// distribution fills in once the async engine (C1) returns real ACMG calls.
import type { BatchResult } from './backend'

export type VariantClass = 'P' | 'LP' | 'VUS' | 'LB' | 'B' | 'unclassified'

export const CLASS_ORDER: VariantClass[] = ['P', 'LP', 'VUS', 'LB', 'B', 'unclassified']

/** Normalise an ACMG / ClinVar verdict string to a 5-tier class (+unclassified).
 *  ACMG takes precedence; ClinVar (incl. INFO/CLNSIG passthrough) is the
 *  fallback so the headline is populated before the engine annotates. */
export function classifyVerdict(
  acmg?: string | null,
  clinvar?: string | null,
): VariantClass {
  const s = (acmg || clinvar || '').toLowerCase().replace(/[_/]+/g, ' ').trim()
  if (!s) return 'unclassified'
  if (s.includes('conflict')) return 'VUS'
  if (s.includes('uncertain') || s.includes('vus')) return 'VUS'
  if (s.includes('likely pathogenic')) return 'LP'
  if (s.includes('likely benign')) return 'LB'
  if (s.includes('pathogenic')) return 'P'
  if (s.includes('benign')) return 'B'
  return 'unclassified'
}

const CLASS_RANK: Record<VariantClass, number> = {
  P: 0,
  LP: 1,
  VUS: 2,
  LB: 3,
  B: 4,
  unclassified: 5,
}

/** Severity rank for actionable-first ordering (P/LP pinned to top). */
export function resultRank(r: BatchResult): number {
  return CLASS_RANK[classifyVerdict(r.acmg_classification, r.clinvar_verdict)]
}

/** Stable sort that pins P then LP to the top; ties keep input order. */
export function sortByActionable(results: BatchResult[]): BatchResult[] {
  return results
    .map((r, i) => ({ r, i }))
    .sort((a, b) => resultRank(a.r) - resultRank(b.r) || a.i - b.i)
    .map((x) => x.r)
}

export interface ParsedKey {
  chrom: string
  pos: number
  ref: string
  alt: string
}

/** Split a `CHROM-POS-REF-ALT` variant_key. Returns null for keys that are not
 *  positional (e.g. an unresolved HGVS string that never reached coordinates). */
export function parseVariantKey(key: string): ParsedKey | null {
  const parts = key.split('-')
  if (parts.length !== 4) return null
  const [chrom, posStr, ref, alt] = parts
  if (!/^\d+$/.test(posStr) || !ref || !alt) return null
  if (!/^[acgtn]+$/i.test(ref) || !/^[acgtn]+$/i.test(alt)) return null
  return { chrom, pos: Number(posStr), ref: ref.toUpperCase(), alt: alt.toUpperCase() }
}

export type VariantType = 'snv' | 'ins' | 'del' | 'mnv'

export function variantType(ref: string, alt: string): VariantType {
  if (ref.length === 1 && alt.length === 1) return 'snv'
  if (alt.length > ref.length) return 'ins'
  if (alt.length < ref.length) return 'del'
  return 'mnv'
}

export type SbsClass = 'C>A' | 'C>G' | 'C>T' | 'T>A' | 'T>C' | 'T>G'
export const SBS_CLASSES: SbsClass[] = ['C>A', 'C>G', 'C>T', 'T>A', 'T>C', 'T>G']

const COMP: Record<string, string> = { A: 'T', C: 'G', G: 'C', T: 'A' }

/** Strand-collapsed 6-class substitution (pyrimidine reference), the standard
 *  mutational-spectrum binning. Null for non-SNV or non-ACGT bases. */
export function substitutionClass(ref: string, alt: string): SbsClass | null {
  if (ref.length !== 1 || alt.length !== 1) return null
  let r = ref.toUpperCase()
  let a = alt.toUpperCase()
  if (!COMP[r] || !COMP[a] || r === a) return null
  if (r === 'A' || r === 'G') {
    r = COMP[r]
    a = COMP[a]
  }
  return `${r}>${a}` as SbsClass
}

export interface GeneCount {
  gene: string
  n: number
}

export interface PanelCoverage {
  total: number
  hit: number
  hitGenes: string[]
  missedGenes: string[]
}

export interface CohortSummary {
  total: number
  classDist: Record<VariantClass, number>
  classified: number
  geneCounts: GeneCount[]
  typeCounts: Record<VariantType, number>
  positional: number
  indelLengths: number[]
  subSpectrum: Record<SbsClass, number>
  subTotal: number
  panel: PanelCoverage | null
}

function emptyClassDist(): Record<VariantClass, number> {
  return { P: 0, LP: 0, VUS: 0, LB: 0, B: 0, unclassified: 0 }
}

function emptySpectrum(): Record<SbsClass, number> {
  return { 'C>A': 0, 'C>G': 0, 'C>T': 0, 'T>A': 0, 'T>C': 0, 'T>G': 0 }
}

/** Compute the cohort summary. `panelGenes` (uppercased symbols, deduped across
 *  active panels) drives the panel-coverage card when ≥1 panel is active. */
export function summarizeCohort(
  results: BatchResult[],
  panelGenes?: string[],
): CohortSummary {
  const classDist = emptyClassDist()
  const subSpectrum = emptySpectrum()
  const typeCounts: Record<VariantType, number> = { snv: 0, ins: 0, del: 0, mnv: 0 }
  const geneMap = new Map<string, number>()
  const hitUpper = new Set<string>()
  const indelLengths: number[] = []
  let positional = 0
  let subTotal = 0

  for (const r of results) {
    classDist[classifyVerdict(r.acmg_classification, r.clinvar_verdict)] += 1

    if (r.gene) {
      geneMap.set(r.gene, (geneMap.get(r.gene) ?? 0) + 1)
      hitUpper.add(r.gene.toUpperCase())
    }

    const key = parseVariantKey(r.variant_key)
    if (key) {
      positional += 1
      const t = variantType(key.ref, key.alt)
      typeCounts[t] += 1
      if (t === 'ins' || t === 'del') {
        indelLengths.push(Math.abs(key.alt.length - key.ref.length))
      }
      const sub = substitutionClass(key.ref, key.alt)
      if (sub) {
        subSpectrum[sub] += 1
        subTotal += 1
      }
    }
  }

  const geneCounts = [...geneMap.entries()]
    .map(([gene, n]) => ({ gene, n }))
    .sort((a, b) => b.n - a.n || a.gene.localeCompare(b.gene))

  const classified = results.length - classDist.unclassified

  let panel: PanelCoverage | null = null
  if (panelGenes && panelGenes.length > 0) {
    const total = panelGenes.length
    const hitGenes: string[] = []
    const missedGenes: string[] = []
    for (const g of panelGenes) {
      if (hitUpper.has(g.toUpperCase())) hitGenes.push(g)
      else missedGenes.push(g)
    }
    panel = { total, hit: hitGenes.length, hitGenes, missedGenes }
  }

  return {
    total: results.length,
    classDist,
    classified,
    geneCounts,
    typeCounts,
    positional,
    indelLengths,
    subSpectrum,
    subTotal,
    panel,
  }
}
