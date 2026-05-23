# tools/

Data-fetch tools — one file per external database. Each tool returns fixture JSON when `USE_REAL_APIS=false` and makes live API calls when `true`. All tools accept `gene:cdna` as primary input format.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `clingen.py` | ClinGen ERepo summary classifications and source-asserted criteria | Changing or debugging ClinGen/VCEP consensus fetches |
| `base.py` | Abstract base class for all tools — fixture-vs-live switching logic | Adding a new tool, changing fixture-loading behaviour |
| `registry.py` | Tool registry — maps tool names to instances; used by the pipeline | Adding a tool to the pipeline, changing tool ordering |
| `clinvar.py` | ClinVar NCBI eutils — two-step esearch + esummary flow | Changing or debugging ClinVar fetches |
| `computational_annotations.py` | Source-labeled computational predictors, SpliceAI component scores, and conservation rows | Changing or debugging report computational deep-dive evidence |
| `ensembl_vep.py` | Ensembl VEP REST — consequence, genomic coords, canonical transcript | Changing or debugging VEP fetches |
| `gene_disease.py` | Gene-disease mechanism, inheritance, disease IDs, and HGNC normalization | Changing or debugging disease mechanism/inheritance evidence |
| `molecular_context.py` | Gene-level molecular context, gnomAD LOEUF, ClinGen dosage, and structural-overlap provenance | Changing or debugging report molecular context evidence |
| `variant_validator.py` | VariantValidator REST - strict GRCh38 VCF coordinate resolution | Changing or debugging coordinate resolution |
| `spliceai.py` | SpliceAI REST — splice delta scores | Changing or debugging SpliceAI fetches |
| `gnomad.py` | gnomAD population frequency | Changing or debugging gnomAD fetches |
| `pubmed.py` | PubMed NCBI eutils — publication search, abstract excerpts | Changing or debugging PubMed fetches |
| `litvar2.py` | LitVar2 API - variant-specific publication IDs/counts | Changing or debugging publication counts |
| `clinical_trials.py` | ClinicalTrials.gov REST API v2 — recruiting/active trials by gene | Changing or debugging clinical trials fetches |
| `report_pdf.py` | PDF report generation tool | Changing PDF export |
