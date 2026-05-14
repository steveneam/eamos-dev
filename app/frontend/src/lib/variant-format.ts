export type VariantFormat = 'rsid' | 'coord' | 'hgvs' | 'gene-p' | 'gene' | 'unknown'

const PATTERNS: [VariantFormat, RegExp][] = [
  ['rsid',   /^rs\d+$/i],
  ['coord',  /^(?:chr)?(?:\d{1,2}|[xyXY])(?::[gGcC]\.\d|\s*[:\-]\s*\d+\s*[:\-]\s*[acgtACGT]+\s*>\s*[acgtACGT]+)/],
  ['hgvs',   /^[A-Z][A-Z0-9_]+\.\d+:[cnmrCNMRgG]\./],
  ['gene-p', /\bp\.[A-Z][a-z]{2}\d+/],
  ['gene',   /^[A-Z][A-Z0-9]+\s+[cnmrCNMRgG]\.\d+/],
]

export function classify(query: string): VariantFormat {
  const q = query.trim()
  for (const [format, pattern] of PATTERNS) {
    if (pattern.test(q)) return format
  }
  return 'unknown'
}

export const FORMAT_HINTS: Record<VariantFormat, string> = {
  rsid:    'dbSNP identifier',
  coord:   'Genomic coordinate',
  hgvs:   'Transcript HGVS',
  'gene-p': 'Gene + protein change',
  gene:    'Gene + cDNA change',
  unknown: 'Variant query',
}
