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
    key: 'vep',
    label: 'VEP',
    href: 'https://www.ensembl.org/Tools/VEP',
    description: 'Ensembl Variant Effect Predictor',
  },
  {
    key: 'spliceai',
    label: 'SpliceAI',
    href: 'https://spliceailookup.broadinstitute.org/',
    description: 'Deep learning splicing impact scores',
  },
  {
    key: 'gnomad',
    label: 'gnomAD',
    href: 'https://gnomad.broadinstitute.org/',
    description: 'Population allele frequencies',
  },
  {
    key: 'alphamissense',
    label: 'AlphaMissense',
    href: 'https://alphamissense.hegelab.org/',
    description: 'Protein-impact scores from AlphaMissense',
  },
  {
    key: 'pubmed',
    label: 'PubMed',
    href: 'https://pubmed.ncbi.nlm.nih.gov/',
    description: 'NCBI biomedical literature',
  },
]

export function getSourceMeta(key: string): SourceMeta | undefined {
  return SOURCES.find((s) => s.key === key.toLowerCase())
}
