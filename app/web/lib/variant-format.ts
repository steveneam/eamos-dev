export type VariantFormat = 'rsid' | 'coord' | 'hgvs' | 'gene-p' | 'gene' | 'unknown'

const PATTERNS: [VariantFormat, RegExp][] = [
  ['rsid',   /^rs\d+$/i],
  ['coord',  /^(?:chr)?(?:\d{1,2}|[xyXYmM])(?::[gGcC]\.\d|\s*[:-]\s*\d+\s*[:-]\s*[acgtACGT]+\s*(?:>|[:-])\s*[acgtACGT]+)/],
  ['hgvs',   /^[A-Z][A-Z0-9_]+\.\d+:[cnmrCNMRgG]\./],
  ['gene-p', /\bp\.[A-Z][a-z]{2}\d+/],
  ['gene',   /^[A-Z][A-Z0-9]+\s+[cnmrCNMRgG]\.\d+/],
]

function classify(query: string): VariantFormat {
  const q = query.trim()
  for (const [format, pattern] of PATTERNS) {
    if (pattern.test(q)) return format
  }
  return 'unknown'
}

/**
 * UX-only mirror of the backend `normalize_variant_query` (BE-8). Strips a
 * leading `GENE:` / `NM_…:` / `ENST…:` accession+colon when an HGVS token
 * follows (so `RPE65:c.260A>G` → `c.260A>G`) and collapses internal
 * whitespace. Genomic coords / rsIDs are left untouched. NEVER lowercases —
 * `A>G` and `p.Asp87Gly` are case-significant. The backend normalizes
 * authoritatively; this just gives instant, consistent feedback before the
 * request is built.
 */
export function cleanQuery(raw: string): string {
  const collapsed = raw.trim().replace(/\s+/g, ' ')
  return collapsed.replace(/^[A-Za-z][A-Za-z0-9_.]*\s*:\s*(?=[cpnmrgCPNMRG]\.)/, '')
}

/**
 * FE-14 client guard: should the report short-circuit to the `malformed`
 * state WITHOUT sending a request? Only when the input is unparseable *every*
 * way. `classify()` was built for a combined `GENE c.xxx` string, so a bare
 * rsID / protein / genomic token (all valid backend inputs) won't match the
 * gene+cDNA pattern once the gene is prepended. Treat as unparseable only
 * when BOTH the gene-prefixed probe AND the cleaned token on its own are
 * `unknown` — otherwise let the backend (the authoritative normalizer) decide
 * and emit `input_unparseable:<kind>` if it really can't parse it.
 */
export function isLikelyUnparseable(gene: string, cdna: string): boolean {
  const cleaned = cleanQuery(cdna)
  if (!cleaned) return true
  const probe = `${gene.trim().toUpperCase()} ${cleaned}`.trim()
  return classify(probe) === 'unknown' && classify(cleaned) === 'unknown'
}
