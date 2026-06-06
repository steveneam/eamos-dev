# Backend Build Ledger Runtime Design

## Scope

This pass turns the external build ledger into a backend-owned runtime contract.
It covers every current ledger lane in one horizontal readiness model: source
assets, local adapters, clinical source tables, gene/protein views, restricted
predictors, ACMG/PVS1, literature, and the AI gateway.

The contract is surfaced by provider-cache health and the source-asset preflight.
It must be sanitized: no secret values, private object URIs, local cache paths,
or signed URLs.

## Storage Decisions

Supabase Storage remains the private durable source whenever an object is
reasonable to keep as a release-pinned artifact. Supabase Postgres remains the
durable source for relational clinical and literature tables. Render persistent
disk is a runtime cache only for readers that require filesystem paths or
materialized indexes. No app build or startup path may download source assets.

| Asset or lane | Durable source | Runtime source | Reason |
| --- | --- | --- | --- |
| hg38.2bit | Supabase private Storage | Render disk local cache | twobit readers require a local path; object storage is durable, disk is runtime only. |
| dbSNP VCF/tabix | Supabase private Storage | Render disk bgzip/tabix cache | pysam/tabix readers require local indexed files and dbSNP dominates disk size. |
| ClinVar VCF/tabix | Supabase private Storage | Render disk bgzip/tabix cache | local ClinVar lookup needs indexed filesystem access. |
| RepeatMasker | Supabase private Storage for source or derived release | Render disk compact interval cache | runtime uses indexed intervals, not raw scans. |
| phyloP bigWig | Supabase private Storage | Render disk bigWig cache | pyBigWig requires efficient filesystem-backed range reads. |
| MANE/RefSeq/Gencode transcript model | Supabase private Storage for offline raw GFF inputs | Render disk compact immutable transcript index | raw GFF parsing is offline-only; runtime lookup/search/report/viewer/batch use the compact artifact. |
| MONDO, HPO, ClinGen, GenCC | Supabase Postgres | Supabase Postgres | relational tables are small enough and do not require Render disk. |
| Gene View | Depends on hg38 plus compact transcript/protein assets | Render disk where underlying readers require it | viewer should consume the same immutable runtime assets as lookup/report. |
| Protein/Pfam/HMMER | Supabase private Storage for release bundles | Render disk Pfam HMM plus hmmpress indexes | HMMER needs local files and indexes; no startup extraction or hmmpress. |
| AlphaMissense | Supabase private Storage for bgzip/tabix artifact | Render disk tabix cache | local lookup needs indexed file; public serialization stays locked. |
| ESM1b | Supabase private Storage for assembled bgzip/tabix artifact | Render disk tabix cache | assembly is offline; runtime only reads the indexed artifact. |
| GPN-MSA | Remote Hugging Face/signed URL plus Supabase metadata | Remote HTTP byte-range | ledger calls for zero local cache until a concrete local need exists. |
| CI-SpliceAI | Supabase private Storage for approved model/cache metadata | Render disk model/ref/cache when enabled | isolated compute lane needs local model and reference files, not main-path startup. |
| NMDetective-B/PVS1 | Repo/Supabase Postgres for small rules and overrides | In-repo code plus optional tiny table | pure code decision tree is sufficient; disk is not justified. |
| CAPICE | None until license/model-feature decision | Disabled | blocked by SpliceAI feature dependency and model review. |
| MaveDB | Supabase Postgres and/or private Storage tabix | Postgres or Render disk tabix | CC0 records can be relational; indexed cache only if performance requires it. |
| ACMG classifier | In-repo code, optional VCEP override table | In-repo code/Postgres | no large runtime asset. |
| Literature engine | Supabase Postgres/pgvector | Supabase Postgres/pgvector | publication edges and embeddings are relational/vector data. |
| AI gateway | API broker config only | Render service process | no source asset; enforce de-ID and no PHI logging. |

## Runtime Rules

- Render disk is never the durable source of truth.
- Startup downloads and startup materialization are disabled.
- Raw MANE/RefSeq/Gencode GFF parsing is offline-only.
- Runtime readers consume compact immutable artifacts, indexed files, or
  relational tables.
- Restricted predictors remain non-public unless terms and field policy are
  explicitly reviewed.
- Health/preflight exposes readiness status and storage policy only, not paths
  or private object identifiers.

## Implementation Shape

Add a shared `build_ledger` service with static ledger rows plus dynamic probes
for current runtime assets:

- hg38 runtime inspection and materialization metadata status.
- AlphaMissense and ESM1b indexed asset inspections.
- protein annotation asset and HMMER runner state.
- local evidence gate state for lookup/search/gene_viewer/workbench.
- source-manifest readiness for Tier 1/2/3 assets.

Provider-cache health returns the sanitized ledger for operators and frontend
runtime diagnostics. Source-asset preflight returns the same ledger for local
and deployment checks. Existing explicit materializer helpers remain available,
but app startup refuses the legacy startup materialization flag.
