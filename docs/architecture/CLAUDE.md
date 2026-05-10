# architecture/

Field guides and pipeline documentation for the Eamos data pipeline. Each guide covers one external data source: API format, authentication, field map, and tool integration notes.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `clinvar-guide.md` | ClinVar NCBI eutils — esearch + esummary two-step flow, field map, variation ID resolution | Changing or debugging `app/tools/clinvar.py` |
| `ensembl-vep-guide.md` | Ensembl VEP REST — HGVS input, consequence fields, genomic coord output | Changing or debugging `app/tools/ensembl_vep.py` |
| `spliceai-guide.md` | SpliceAI REST endpoint — `GENE:c.cdna` input format, delta score fields | Changing or debugging `app/tools/spliceai.py` |
| `franklin-api-field-guide.md` | Franklin (Genoox) API — auth flow, search endpoint, classification field map | Changing or debugging `app/tools/franklin.py` |
| `api-research.md` | All external APIs summarised — auth methods, rate limits, input formats | Onboarding to the data layer, choosing a new source |
| `backend-core-workflow.md` | End-to-end pipeline: intake → tools → rules → draft → review; data flow diagram | Understanding how the full pipeline fits together |
| `solution-brief.md` | Product rationale and clinical problem framing | Explaining the product scope or clinical context |
