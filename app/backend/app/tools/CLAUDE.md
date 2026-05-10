# tools/

Data-fetch tools — one file per external database. Each tool returns fixture JSON when `USE_REAL_APIS=false` and makes live API calls when `true`. All tools accept `gene:cdna` as primary input format.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `base.py` | Abstract base class for all tools — fixture-vs-live switching logic | Adding a new tool, changing fixture-loading behaviour |
| `registry.py` | Tool registry — maps tool names to instances; used by the pipeline | Adding a tool to the pipeline, changing tool ordering |
| `clinvar.py` | ClinVar NCBI eutils — two-step esearch + esummary flow | Changing or debugging ClinVar fetches |
| `ensembl_vep.py` | Ensembl VEP REST — consequence, genomic coords, canonical transcript | Changing or debugging VEP fetches |
| `spliceai.py` | SpliceAI REST — splice delta scores | Changing or debugging SpliceAI fetches |
| `franklin.py` | Franklin (Genoox) API — functional evidence, variant curation | Changing or debugging Franklin fetches |
| `gnomad.py` | gnomAD population frequency | Changing or debugging gnomAD fetches |
| `pubmed.py` | PubMed NCBI eutils — publication search, abstract excerpts | Changing or debugging PubMed fetches |
| `clinical_trials.py` | ClinicalTrials.gov REST API v2 — recruiting/active trials by gene | Changing or debugging clinical trials fetches |
| `report_pdf.py` | PDF report generation tool | Changing PDF export |
