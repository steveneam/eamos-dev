# Backend Build Ledger Runtime Spec

## Public Shape

`build_backend_build_ledger(settings, ...)` returns a JSON-serializable object:

- `mode`: `backend_build_ledger`
- `source`: source ledger name
- `startup_downloads_allowed`: always false
- `raw_gff_runtime_allowed`: always false
- `supabase_private_storage_is_durable_source`: true
- `items`: ordered readiness rows
- `status_counts`: counts by row status
- `storage_summary`: counts by Render disk role and durable source

Each row includes:

- `item_id`
- `label`
- `group`
- `source_ids`
- `engine`
- `durable_source`
- `runtime_source`
- `render_disk_role`
- `storage_decision`
- `status`
- `runtime_wired`
- `public_serialization_allowed`
- `startup_download_allowed`
- `raw_source_runtime_allowed`
- `blockers`
- `wired_surfaces`
- `next_action`

The output must not include filesystem paths, private object URIs, signed URLs,
service-role keys, or user-submitted variant identities.

## Required Rows

The ledger must include rows for:

- hg38.2bit
- dbSNP local adapter
- ClinVar local adapter
- RepeatMasker local adapter
- phyloP conservation reader
- compact coordinate/transcript index
- local evidence orchestrator gate
- MONDO/HPO/ClinGen/GenCC clinical source tables
- Gene View
- Protein/Pfam/HMMER
- AlphaMissense
- ESM1b
- GPN-MSA
- CI-SpliceAI
- NMDetective/PVS1
- CAPICE
- MaveDB
- ACMG classifier
- literature engine
- AI gateway
- sequence/primer/CRISPR/alignment workbench

## Dynamic Status Rules

- hg38 status comes from `inspect_hg38_runtime_asset`.
- compact coordinate index status comes from `inspect_compact_coordinate_index`.
  The health/preflight payload includes readiness, schema version, artifact
  version, genome build, record counts, and checksum verification state only.
  It must not include the compact artifact path, raw GFF paths, object URIs, or
  user variant identities.
- AlphaMissense and ESM1b statuses come from their predictor runtime probes.
- Protein/Pfam status comes from protein asset inspection plus the active
  protein annotation service status when present.
- clinical source table rows use source-manifest readiness and parser/import
  references.
- local evidence status follows `LocalEvidenceRuntimeGate`.
- lanes with no approved runtime yet report planned or blocked statuses, not
  fabricated readiness.

## Compact Coordinate Index Runtime Contract

The runtime compact coordinate index is a read-only JSONL/JSONL.GZ artifact
with `schema_version = eamos.coordinate_index.v1`. It contains one metadata
record plus `variant` and `transcript` records:

- `variant` rows map gene/transcript/cDNA plus optional accession identifiers to
  canonical GRCh38 VCF identity and RefSeq genomic HGVS.
- `transcript` rows carry compact MANE/RefSeq/Gencode projection geometry for
  Gene View and local-evidence transcript mapping.

Raw MANE, RefSeq, and Gencode GFF parsing is an offline build concern. Runtime
lookup, search/parse, Variant Evidence Report hydration, Gene View, local
evidence, and batch paths must construct their coordinate resolver with the
compact index path and `mane_gff_path = refseq_gff_path = null`.

## Lifecycle Contract

`create_app` must not call a downloader or materializer during startup. If the
legacy coordinate resolver startup materialization flag is enabled, startup must
fail closed with a policy error so the deployment cannot silently pull private
assets. Approved materialization happens through explicit off-peak processes
after the Render disk is mounted and verified.

## Verification

Tests must cover:

- provider-cache health returns the build ledger.
- provider-cache health output remains path/object-URI sanitized.
- source-asset preflight returns the same ledger shape.
- the ledger includes AlphaMissense, MONDO/HPO clinical tables, Gene View,
  Protein/Pfam, and compact coordinate index rows.
- startup coordinate materialization is disabled by policy.
