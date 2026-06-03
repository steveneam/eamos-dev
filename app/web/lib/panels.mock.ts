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

/** Colored per-row provenance tag: which panel a variant matched. */
export interface PanelBadge {
  short: string
  bg: string
  text: string
  border: string
}

// Categorical palette (DESIGN tokens). Stable color per panel so a variant in
// two panels reads as two consistent tags.
const BADGE_PALETTE: Omit<PanelBadge, 'short'>[] = [
  { bg: 'var(--teal-tint)', text: 'var(--teal-deep)', border: 'var(--teal-bdr)' },
  { bg: 'var(--warn-tint)', text: 'var(--warn-text)', border: 'var(--warn-bdr)' },
  { bg: 'var(--info-bg)', text: 'var(--info-text)', border: 'var(--info-bdr)' },
  { bg: 'var(--danger-faint)', text: 'var(--danger)', border: 'var(--danger-border)' },
]

// Explicit, distinct colors for the launch panels (so IRD/Cardiac/Cancer never collide).
const KNOWN_BADGES: Record<string, PanelBadge> = {
  'inherited-retinal-disease': { short: 'IRD', ...BADGE_PALETTE[0] },
  'cardiomyopathy-arrhythmia': { short: 'Cardiac', ...BADGE_PALETTE[1] },
  'hereditary-cancer': { short: 'Cancer', ...BADGE_PALETTE[2] },
}

function deriveShort(name: string): string {
  const words = name.replace(/\(.*?\)/g, '').split(/[\s/&]+/).filter((w) => w.length > 2)
  if (words.length >= 2) return words.map((w) => w[0]?.toUpperCase() ?? '').join('').slice(0, 4)
  return (words[0] ?? name).slice(0, 8)
}

function hashSlug(slug: string): number {
  let h = 0
  for (let i = 0; i < slug.length; i += 1) h = (h * 31 + slug.charCodeAt(i)) >>> 0
  return h
}

export function panelBadge(panel: Panel): PanelBadge {
  return KNOWN_BADGES[panel.slug] ?? { short: deriveShort(panel.name), ...BADGE_PALETTE[hashSlug(panel.slug) % BADGE_PALETTE.length] }
}

// Deterministic MOCK resolver for the custom-panel builder (spec §6.3.1 Tier A).
// Maps a free-text disease query to genes by keyword. Stands in for the real
// ClinGen/GenCC resolution behind POST /api/v1/panels/resolve (Codex) — the
// conversational/LLM front-end (Tier B) is COMING SOON until AskEamos is funded.
const KEYWORD_PRESETS: { match: RegExp; slug: string }[] = [
  { match: /retin|eye|vision|blind|macular|\brod\b|\bcone\b|\brp\b|dystroph/i, slug: 'inherited-retinal-disease' },
  { match: /heart|cardi|arrhythm|myopath|qt\b/i, slug: 'cardiomyopathy-arrhythmia' },
  { match: /cancer|tumou?r|breast|ovarian|lynch|brca|onco/i, slug: 'hereditary-cancer' },
]

// Symbol → gene index across all preset panels, for resolving pasted/attached gene lists.
const GENE_INDEX: Map<string, PanelGene> = (() => {
  const idx = new Map<string, PanelGene>()
  for (const panel of PANELS) for (const gene of panel.genes) if (!idx.has(gene.symbol)) idx.set(gene.symbol, gene)
  return idx
})()

export interface CustomPanelDraft {
  panel: Panel
  /** Human note on what resolved: preset names and/or "N gene symbols". */
  sources: string[]
}

/**
 * Resolve free text (typed keywords, gene symbols, or an attached list) into a
 * draft custom panel: union of (a) genes from keyword-matched preset panels and
 * (b) directly-named genes recognised in the index. Mock stand-in for
 * ClinGen/GenCC + HGNC resolution behind POST /panels/resolve.
 */
export function buildCustomPanel(query: string): CustomPanelDraft | null {
  const q = query.trim()
  if (!q) return null

  const matchedPresets = KEYWORD_PRESETS.filter((p) => p.match.test(q))
    .map((p) => getMockPanel(p.slug))
    .filter((p): p is Panel => Boolean(p))

  const seen = new Set<string>()
  const genes: PanelGene[] = []
  const pushGene = (gene: PanelGene) => {
    if (seen.has(gene.symbol)) return
    seen.add(gene.symbol)
    genes.push(gene)
  }
  for (const panel of matchedPresets) for (const gene of panel.genes) pushGene(gene)

  let symbolHits = 0
  for (const token of q.split(/[\s,;|\t\r\n]+/)) {
    const gene = GENE_INDEX.get(token.trim().toUpperCase())
    if (gene && !seen.has(gene.symbol)) {
      symbolHits += 1
      pushGene(gene)
    }
  }

  if (genes.length === 0) return null
  const id = `custom-${Date.now()}`
  const sources = matchedPresets.map((p) => p.name)
  if (symbolHits > 0) sources.push(`${symbolHits} gene symbol${symbolHits === 1 ? '' : 's'}`)
  return {
    sources,
    panel: {
      id,
      slug: id,
      name: q.length > 42 ? `${q.slice(0, 42).trim()}…` : q,
      source: 'custom',
      version: 'draft',
      provenance_url: undefined,
      intervals_ref: 'hg38',
      genes,
      warnings: ['Mock deterministic resolution — wires to ClinGen/GenCC + HGNC via /panels/resolve when live.'],
    },
  }
}
