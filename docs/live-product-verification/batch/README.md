# Batch / Compare V2 verification

Lane B implements the engine contract without materializing scientific source
artifacts. The supported release envelope is GRCh38 called-site VCF/VCF.gz,
one proband or at most three family samples, and sequence-resolved SNVs/short
indels. BCF, gVCF blocks, cohort matrices, non-canonical contigs, SV/CNV
symbolic alleles, and files beyond the measured WES envelope fail with typed
guidance.

## Truth and privacy invariants

- Uploads are owner-bound, opaque, single-use, expiring files with mode `0600`.
  The client filename and VCF sample names never enter result rows or durable
  workflow state.
- The original upload digest and byte/record/sample envelope are immutable.
  Gzip input is boundedly expanded into the same private staging slot so both
  ordinary gzip and BGZF reach HTSlib consistently.
- In the strict V2 path, input `GENE`, `ANN`, frequency, and classification
  fields are provenance only. Coordinate intervals are the filter authority.
  The pre-existing sampleless compatibility path may retain submitted gene/cDNA
  as query identity, but carries no V2 execution or source-snapshot claim and
  never promotes submitted protein, classification, or frequency values.
- Reference checking and normalization fail closed until a pinned `bcftools`
  binary, GRCh38 FASTA/index, manifest digest, and functional probe are mounted.
- The 5,000-row annotation cap is applied after cheap filtering and normalized
  duplicate collapse. Raw WES rows may exceed it.
- A completed row comes from direct Report V2 lookup. Every shared value carries
  its Report execution disclosure, and all rows in one job bind to one direct
  Report source snapshot.
- The owner-scoped recovery ledger stores only job/owner/lease metadata. The
  workflow ledger stores normalized results and de-identified sample
  provenance; neither stores raw VCF bytes.
- TSV, CSV, JSONL, and VCF exports stream from the workflow ledger. Terminal V2
  exports carry a SHA-256 digest, row count, source-snapshot ID, and deterministic
  export ID; the manifest exposes the corresponding `BatchExportV2` receipts.
- The built-in panel list remains explicitly `custom` and unavailable as a
  source-backed V2 snapshot. It cannot masquerade as HGNC/MANE/GenCC/Mondo or
  PanelApp material.

## Runtime flow

```text
owner upload -> bounded receipt -> cheap coordinate/genotype filters
             -> pinned REF check + normalization -> normalized dedupe/cap
             -> durable owner lease -> direct Report V2 lookup
             -> snapshot-bound paging -> digested streaming export
```

## Verification commands

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_batch_api.py \
  app/backend/tests/test_batch_panel_schemas.py \
  app/backend/tests/test_vcf_ingest.py \
  app/backend/tests/test_panels_api.py \
  app/backend/tests/test_batch_wes_*.py

cd app/backend
.venv/bin/python -m app.fixtures.batch.benchmark_wes
```

The material/runtime requests remain unexecuted and are recorded in
`material-request.md`. They require the separate Wave 3 approval card before
any download, build, mount, provider change, or deployment action.
