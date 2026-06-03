// MOCK panel catalogue for the P3 panel-picker + scope-gate UI shell.
//
// ⚠️ TEMPORARY — replace when Codex's panel ENDPOINTS land. The contract TYPES
// (Panel / PanelSummary / PanelGene / PanelSource) now live in `lib/backend.ts`
// (mirroring app/backend/app/schemas/panels.py, canaried by test_frontend_contract.py);
// this file only supplies illustrative MOCK DATA + the client-side scope preview until
// `GET /api/v1/panels` + `GET /api/v1/panels/{slug}` exist. Then swap MOCK_PANELS /
// getMockPanel for a real `lib/panels.ts` API client. Gene lists, HGNC ids, validity, and
// confidences below are ILLUSTRATIVE subsets, not curated panels.
import type { Panel, PanelConfidence, PanelGene, PanelSource, PanelSummary } from './backend'
import type { ParsedVariant } from './variant-file'

function g(symbol: string, hgnc_id: string, moi: string, confidence: PanelConfidence = 'green'): PanelGene {
  return { symbol, hgnc_id, confidence, moi, provenance: [], warnings: [] }
}

const IRD: Panel = {
  id: 'mock-ird',
  name: 'Inherited retinal disease',
  slug: 'inherited-retinal-disease',
  source: 'panelapp-au',
  version: 'mock-v4.2',
  provenance_url: 'https://panelapp.agha.umccr.org/panels/',
  intervals_ref: 'hg38',
  warnings: [],
  genes: [
    g('ABCA4', 'HGNC:34', 'AR'),
    g('USH2A', 'HGNC:12601', 'AR'),
    g('RPE65', 'HGNC:10294', 'AR'),
    g('RPGR', 'HGNC:10295', 'XL'),
    g('CRB1', 'HGNC:2343', 'AR'),
    g('RHO', 'HGNC:10012', 'AD'),
    g('EYS', 'HGNC:21555', 'AR'),
    g('CEP290', 'HGNC:29021', 'AR'),
    g('PRPH2', 'HGNC:9942', 'AD'),
    g('BEST1', 'HGNC:1242', 'AD', 'amber'),
    g('CHM', 'HGNC:1894', 'XL'),
    g('RP1', 'HGNC:10263', 'AD', 'amber'),
  ],
}

const CARDIAC: Panel = {
  id: 'mock-cardiac',
  name: 'Cardiomyopathy & arrhythmia',
  slug: 'cardiomyopathy-arrhythmia',
  source: 'panelapp-au',
  version: 'mock-v2.7',
  provenance_url: 'https://panelapp.agha.umccr.org/panels/',
  intervals_ref: 'hg38',
  warnings: [],
  genes: [
    g('MYH7', 'HGNC:7577', 'AD'),
    g('MYBPC3', 'HGNC:7551', 'AD'),
    g('TNNT2', 'HGNC:11949', 'AD'),
    g('TNNI3', 'HGNC:11947', 'AD'),
    g('TPM1', 'HGNC:12010', 'AD', 'amber'),
    g('SCN5A', 'HGNC:10593', 'AD'),
    g('KCNQ1', 'HGNC:6294', 'AD'),
    g('KCNH2', 'HGNC:6251', 'AD'),
    g('LMNA', 'HGNC:6636', 'AD'),
    g('PKP2', 'HGNC:9024', 'AD'),
    g('DSP', 'HGNC:3052', 'AD', 'amber'),
  ],
}

const HEREDITARY_CANCER: Panel = {
  id: 'mock-hboc',
  name: 'Hereditary cancer (core)',
  slug: 'hereditary-cancer',
  source: 'clingen-gencc',
  version: 'mock-v1.0',
  provenance_url: 'https://search.clinicalgenome.org/',
  intervals_ref: 'hg38',
  warnings: [],
  genes: [
    g('BRCA1', 'HGNC:1100', 'AD'),
    g('BRCA2', 'HGNC:1101', 'AD'),
    g('TP53', 'HGNC:11998', 'AD'),
    g('PALB2', 'HGNC:26144', 'AD'),
    g('ATM', 'HGNC:795', 'AD', 'amber'),
    g('CHEK2', 'HGNC:16627', 'AD', 'amber'),
    g('MLH1', 'HGNC:7127', 'AD'),
    g('MSH2', 'HGNC:7325', 'AD'),
    g('MSH6', 'HGNC:7329', 'AD'),
    g('PMS2', 'HGNC:9122', 'AD'),
    g('APC', 'HGNC:583', 'AD'),
  ],
}

const PANELS: Panel[] = [IRD, CARDIAC, HEREDITARY_CANCER]

/** Mock of `GET /api/v1/panels` (summaries only). */
export const MOCK_PANELS: PanelSummary[] = PANELS.map((p) => ({
  id: p.id,
  name: p.name,
  slug: p.slug,
  source: p.source,
  version: p.version,
  provenance_url: p.provenance_url,
  gene_count: p.genes.length,
  intervals_ref: p.intervals_ref,
  warnings: p.warnings,
}))

/** Mock of `GET /api/v1/panels/{slug}` (full gene list). */
export function getMockPanel(slug: string): Panel | null {
  return PANELS.find((p) => p.slug === slug) ?? null
}

export const PANEL_SOURCE_LABEL: Record<PanelSource, string> = {
  'panelapp-au': 'PanelApp Australia',
  'panelapp-gel': 'PanelApp (GEL)',
  'clingen-gencc': 'ClinGen / GenCC',
  custom: 'Custom',
}

export interface PanelScope {
  total: number
  /** Gene known (CSV/list path) and in the panel. */
  matched: ParsedVariant[]
  /** Gene known but not in the panel — filtered out. */
  excluded: ParsedVariant[]
  /** Genomic-only (VCF) variants — gene unknown client-side; require the server-side
   *  interval filter (MANE→hg38 BED, Codex P2). Not droppable client-side. */
  intervalPending: ParsedVariant[]
}

/**
 * Client-side preview of a panel ∩ cohort intersection by GENE SYMBOL only.
 * This is the small-file path (spec §4); the authoritative interval-first filter
 * (§6.4) runs server-side once Codex's hg38 BED resource lands.
 */
export function scopeVariantsToPanel(variants: ParsedVariant[], panel: Panel | null): PanelScope {
  if (!panel) {
    return { total: variants.length, matched: variants, excluded: [], intervalPending: [] }
  }
  const symbols = new Set(panel.genes.map((gene) => gene.symbol.toUpperCase()))
  const matched: ParsedVariant[] = []
  const excluded: ParsedVariant[] = []
  const intervalPending: ParsedVariant[] = []
  for (const v of variants) {
    if (!v.gene) intervalPending.push(v)
    else if (symbols.has(v.gene.toUpperCase())) matched.push(v)
    else excluded.push(v)
  }
  return { total: variants.length, matched, excluded, intervalPending }
}
