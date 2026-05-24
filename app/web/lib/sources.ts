export interface SourceMeta {
  key: string
  label: string
  href: string
  description: string
}

export const SOURCES: SourceMeta[] = [
  {
    key: 'clinvar',
    label: 'ClinVar',
    href: 'https://www.ncbi.nlm.nih.gov/clinvar/',
    description: 'NCBI variant classification archive',
  },
  {
    key: 'gnomad',
    label: 'gnomAD',
    href: 'https://gnomad.broadinstitute.org/',
    description: 'Population allele frequencies',
  },
  {
    key: 'spliceai',
    label: 'SpliceAI',
    href: 'https://spliceailookup.broadinstitute.org/',
    description: 'Deep learning splicing impact scores',
  },
  {
    key: 'ensembl',
    label: 'Ensembl',
    href: 'https://www.ensembl.org/',
    description: 'Genome annotation & Variant Effect Predictor',
  },
  {
    key: 'pubmed',
    label: 'PubMed',
    href: 'https://pubmed.ncbi.nlm.nih.gov/',
    description: 'NCBI biomedical literature',
  },
  {
    key: 'clinicaltrials',
    label: 'ClinicalTrials.gov',
    href: 'https://clinicaltrials.gov/',
    description: 'NIH clinical trials registry',
  },
]

// Legacy/backend source keys that map onto a canonical SOURCES entry, so
// per-source lookups (e.g. the evidence table's `vep` row) keep resolving
// after the VEP→Ensembl rename.
const SOURCE_ALIASES: Record<string, string> = {
  vep: 'ensembl',
  ensembl_vep: 'ensembl',
}

export function getSourceMeta(key: string): SourceMeta | undefined {
  const k = key.toLowerCase()
  return SOURCES.find((s) => s.key === k || s.key === SOURCE_ALIASES[k])
}
