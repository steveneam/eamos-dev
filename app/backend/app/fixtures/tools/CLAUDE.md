# tools/

Fixture JSON files — one per external data source. Returned verbatim by tools when `USE_REAL_APIS=false`.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `clingen_fixtures.json` | ClinGen ERepo fixture response | Debugging ClinGen consensus in fixture mode |
| `clinvar_fixtures.json` | ClinVar fixture response | Debugging ClinVar tool in fixture mode |
| `computational_annotations_fixtures.json` | Computational deep-dive fixture response with source-labeled predictor and conservation rows | Debugging computational annotations in fixture mode |
| `gene_disease_fixtures.json` | Gene-disease mechanism/inheritance fixture response | Debugging disease mechanism/inheritance in fixture mode |
| `molecular_context_fixtures.json` | Molecular context fixture response with gnomAD constraint and ClinGen dosage | Debugging report molecular context in fixture mode |
| `gnomad_fixtures.json` | gnomAD fixture response | Debugging gnomAD tool in fixture mode |
| `pubmed_fixtures.json` | PubMed fixture response | Debugging PubMed tool in fixture mode |
| `litvar2_fixtures.json` | LitVar2 fixture response | Debugging LitVar2 tool in fixture mode |
| `variant_validator_fixtures.json` | VariantValidator fixture response | Debugging coordinate resolver in fixture mode |
| `spliceai_fixtures.json` | SpliceAI fixture response | Debugging SpliceAI tool in fixture mode |
| `vep_fixtures.json` | Ensembl VEP fixture response | Debugging VEP tool in fixture mode |
