import type { LookupResponse } from './backend'

export const RPE65_SAMPLE: LookupResponse = {
  query: 'RPE65 c.260A>G',
  species: 'human',
  warnings: [],
  report_payload: {
    patient_id: 'sample',
    case_label: 'RPE65 p.Asp87Gly',
    report_title: 'RPE65 c.260A>G — Variant Interpretation Report',
    clinical_phenotype: 'Leber Congenital Amaurosis 2 (LCA2) / Retinitis Pigmentosa 20 (RP20). Autosomal recessive retinal dystrophy characterised by severe visual impairment from infancy, nystagmus, and markedly reduced or absent ERG response.',
    ai_clinical_summary:
      'RPE65 p.Asp87Gly is concordant with autosomal recessive retinal dystrophy phenotypes. ClinVar lists it as Likely Pathogenic with two-star review status, supported by REVEL 0.82 — above the strong pathogenic threshold. Three RPE65-related trials are currently recruiting, including Voretigene neparvovec (Luxturna), FDA-approved for biallelic RPE65 retinal dystrophy. Confirmation of homozygosity and segregation testing are the immediate next steps before clinical decision-making proceeds.',
    variant_summary_rows: [
      {
        gene: 'RPE65',
        transcript_hgvs: 'NM_000329.3:c.260A>G',
        protein_change: 'p.Asp87Gly',
        genomic_hg38: 'chr1:68,894,934A>G',
        variation_type: 'SNV',
        consequence: 'missense_variant',
      },
    ],
    acmg_classification: 'Likely Pathogenic — ACMG/AMP criteria: PM1, PM2, PP3 (REVEL 0.82). ClinVar VCV000099473 · 2 stars · 4 submitters.',
    expanded_evidence:
      'ClinVar: Likely Pathogenic (2 stars, 4 submitters, VCV000099473). gnomAD v4: absent from 807,162 alleles (MAF < 1.2e-6). VEP: missense, moderate impact, SIFT deleterious (0.01), PolyPhen-2 probably damaging (0.987). SpliceAI: max delta score 0.04 (below splicing threshold). REVEL: 0.82 — high support for pathogenicity.',
    clinical_integration:
      'Variant is consistent with RPE65-associated Leber Congenital Amaurosis 2 (LCA2) and Retinitis Pigmentosa 20. Biallelic pathogenic variants in RPE65 cause the autosomal recessive form. Luxturna (voretigene neparvovec) is FDA-approved gene therapy for confirmed biallelic RPE65 mutations.',
    expected_symptoms:
      'Severe visual impairment from infancy or early childhood, nystagmus, photophobia, absent or markedly reduced ERG, preserved retinal structure in early years with progressive degeneration.',
    recommendations:
      'Confirm biallelic status: segregation analysis and phasing of any second RPE65 variant. Ophthalmology review with ERG and retinal imaging. Genetic counselling for family members. Evaluate eligibility for Luxturna gene therapy if biallelic RPE65 pathogenic variants confirmed.',
    therapeutic_landscape:
      'Voretigene neparvovec (Luxturna, Spark Therapeutics) is FDA-approved (2017) for confirmed biallelic RPE65 mutation-associated retinal dystrophy. Three additional gene therapy trials are actively recruiting (NCT05858983, NCT04516369, NCT04657926).',
    limitations:
      'Report generated with fixture data in development mode. Evidence reflects database snapshot at time of analysis. ACMG classification requires formal review by a certified variant interpretation laboratory.',
    variant_decoder:
      'c.260A>G — position 260 in the coding sequence of NM_000329.3; adenine substituted by guanine. This changes codon 87 from GAC (Aspartate/Asp/D) to GGC (Glycine/Gly/G). Asp87 is located in the retinoid isomerohydrolase catalytic domain; Gly substitution removes a charged side chain critical for substrate binding.',
    pubmed_articles: [
      {
        pmid: '28274730',
        title: 'Pharmacological and gene therapy based rescue of cytochrome P450-mediated monooxygenase deficiency in RPE65',
        authors: 'Cheng T, Bhatt A, Kulkarni A et al.',
        journal: 'Invest Ophthalmol Vis Sci',
        year: '2017',
        url: 'https://pubmed.ncbi.nlm.nih.gov/28274730/',
      },
    ],
    ai_generated_sections: ['ai_clinical_summary', 'clinical_integration', 'recommendations', 'variant_decoder'],
  },
  evidence: [
    {
      source: 'clinvar',
      status: 'completed',
      request_identity: { gene: 'RPE65', cdna: 'c.260A>G' },
      summary: {
        classification: 'Likely pathogenic',
        review_stars: 2,
        submitter_count: 4,
        accession: 'VCV000099473',
        condition: 'Leber congenital amaurosis 2',
      },
      warnings: [],
      source_url: 'https://www.ncbi.nlm.nih.gov/clinvar/variation/99473/',
    },
    {
      source: 'vep',
      status: 'completed',
      request_identity: { transcript: 'NM_000329.3', cdna: 'c.260A>G' },
      summary: {
        consequence: 'missense_variant',
        impact: 'MODERATE',
        sift: { pred: 'deleterious', score: 0.01 },
        polyphen: { pred: 'probably_damaging', score: 0.987 },
        revel: 0.82,
      },
      warnings: [],
      source_url: 'https://www.ensembl.org/Tools/VEP',
    },
    {
      source: 'spliceai',
      status: 'completed',
      request_identity: { gene: 'RPE65', cdna: 'c.260A>G' },
      summary: {
        max_delta: 0.04,
        interpretation: 'Low splicing impact',
      },
      warnings: [],
      source_url: 'https://spliceailookup.broadinstitute.org/',
    },
    {
      source: 'gnomad',
      status: 'completed',
      request_identity: { gene: 'RPE65', cdna: 'c.260A>G' },
      summary: {
        allele_count: 0,
        allele_number: 807162,
        allele_frequency: null,
        interpretation: 'Absent from gnomAD v4',
      },
      warnings: [],
      source_url: 'https://gnomad.broadinstitute.org/',
    },
    {
      source: 'alphamissense',
      status: 'completed',
      request_identity: { uniprot_id: 'Q16518', residue: 87 },
      summary: {
        score: 0.71,
        pathogenicity_category: 'likely_pathogenic',
      },
      warnings: [],
      source_url: 'https://alphamissense.hegelab.org/',
    },
  ],
}
