# Eamos Local Coordinate Resolver

Status: Active backend prototype
Type: Coordinate resolution algorithm and CLI-backed workflow
Owner: Codex backend
Added: 2026-06-04 02:53 +1000 - Codex
Last updated: 2026-06-04 02:53 +1000 - Codex

## What It Does

The Eamos Local Coordinate Resolver converts gene, transcript, and HGVS cDNA
inputs into canonical GRCh38 VCF identity fields:
`CHROM`, `POS`, `REF`, `ALT`, `genomic_hg38`, and `genomic_hgvs`.

It is the coordinate source of truth for search-bar resolution, Workbench
fixtures, report input normalization, and the batch VCF pipeline. Client uploads
do not need to arrive with GRCh38 `CHROM/POS/REF/ALT` if they carry resolvable
gene/transcript/HGVS context.

Workbench may still keep render-hydration snapshots for offline UI tests, but
those snapshots are not coordinate-resolution inputs.

## Why It Is Eamos-Original

The resolver owns the Eamos workflow and output contract. It uses local
MANE/RefSeq transcript exon/CDS geometry, local hg38 reference sequence, Eamos
normalization rules, and deterministic VCF allele normalization. It handles
coding substitutions, UTR coordinates, intronic offsets, deletions, insertions,
duplications, delins, and DNA-level frameshift-causing events such as `c.3326dup`
or `c.24del`.

ClinVar/SPDI and VariantValidator are not runtime coordinate dependencies. They
are offline validation oracles and troubleshooting references. Batch VCF jobs
must not call them once per variant.

## Runtime Policy

Runtime order:

1. Resolve locally from MANE/RefSeq transcript geometry and local hg38 reference
   sequence.
2. Use optional Eamos-owned snapshots only when explicitly supplied for
   regression fixtures or hand-curated internal overrides.
3. Use live external APIs only as explicit fallback in developer/live validation
   modes, never as the batch hot path.

The canonical internal key remains `chrom-pos-ref-alt`, for example
`5-112839660-C-T`, because gnomAD, SpliceAI, BED interval filters, and batch
dedup use bare chromosome coordinates. The precise RefSeq accession form is
preserved separately as `genomic_hgvs`, for example
`NC_000005.10:g.112839660C>T`.

## Source Of Truth

- Local resolver:
  `app/backend/app/services/eamos_coordinate_resolver.py`
- Compact runtime index reader:
  `app/backend/app/services/compact_coordinate_index.py`
- Search resolver integration:
  `app/backend/app/services/search_input_resolver.py`
- Developer CLI:
  `app/backend/app/cli/eamos_search_input.py`
- Project-100 oracle validation harness:
  `app/backend/scripts/validate_project_100_coordinates.py`
- Project-100 validation snapshot:
  `app/backend/app/fixtures/hardening/project_100_coordinate_validation.json`
- Tests:
  - `app/backend/tests/test_eamos_coordinate_resolver.py`
  - `app/backend/tests/test_search_input_resolver.py`
  - `app/backend/tests/test_eamos_search_input_cli.py`

## Required Local Assets

- Runtime compact coordinate index:
  `app/backend/data/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz`
- Runtime hg38 reference:
  `app/backend/data/bio_assets/genomes/hg38.2bit`
- Offline MANE RefSeq GFF input:
  `app/backend/data/bio_assets/transcripts/MANE.GRCh38.v1.5.refseq_genomic.gff.gz`
- Offline all-RefSeq GRCh38.p14 GFF input:
  `app/backend/data/bio_assets/transcripts/GCF_000001405.40_GRCh38.p14_genomic.gff.gz`

Raw MANE/RefSeq/Gencode GFF parsing is offline-only. Runtime resolver instances
built from `Settings` read the compact immutable index and do not scan raw GFF.
Supabase/Postgres should store metadata, checksums, versions, and object paths
only; raw genomic assets belong in private object storage or the backend local
cache.

## Current Verification

As of 2026-06-04:

- 10/10 Project-100 control variants resolve locally without live APIs.
- 100/100 Project-100 rows resolve locally from MANE/RefSeq plus hg38 reference.
- 100/100 local Project-100 coordinates match ClinVar/SPDI.
- 100/100 local Project-100 coordinates match VariantValidator GRCh38 VCF
  output in the offline validation harness.

VariantValidator validation of 100 rows took about eight minutes in the Windows
backend environment. That is acceptable for offline oracle validation and
unacceptable for batch VCF runtime.

Opt-in local asset proof:

```powershell
cd app/backend
$env:EAMOS_VERIFY_PROJECT_100_COORDINATES='1'
python -m pytest tests/test_eamos_coordinate_resolver.py -q
```

External oracle proof:

```powershell
cd app/backend
python scripts/validate_project_100_coordinates.py --validate-variant-validator --sleep-seconds 0.05
```

## Caveats

- Protein-only descriptions such as `p.Arg1109fs` do not uniquely define a
  genomic coordinate. They must be paired with cDNA, transcript, ClinVar ID,
  rsID, or another source-backed DNA-level candidate before coordinate
  resolution.
- Production should add a compact precompiled Eamos transcript projection index
  release process around the new runtime reader so request startup never parses
  the full RefSeq GFF on a cold process.
- Liftover is out of scope for v1. The resolver assumes GRCh38/hg38 and should
  flag or refuse hg19/hg37 inputs until a dedicated liftover policy exists.
