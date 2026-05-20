# Gene Viewer Architecture Design

Status: Draft

Section edited: 2026-05-18 12:01 +1000 · Codex.

## Summary

The Workbench gene viewer should become the shared sequence authority for the
viewer, primer, CRISPR, and alignment tools. The recommended direction is a
backend-owned, gene-agnostic viewer payload built from a resolved transcript,
reference/control sequence, a variant overlay, and source-labelled annotations.
The frontend keeps its existing viewer interaction model, but stops relying on
the bundled RPE65-only sample as the primary data source.

## Context And Scope

The supplied RPE65 backend brief correctly prioritizes exact sequence,
coordinates, transcript structure, protein features, and render-ready payloads.
It is also broader than the current Eamos architecture: it proposes a new
project skeleton, PostgreSQL, Redis, Celery, SQLModel, and ingest pipelines.
Eamos already has a FastAPI backend, Workbench engine endpoints, a shared
frontend contract canary, and a mature React viewer surface.

Current implementation:

- `app/frontend/src/components/workbench/WorkbenchShell.tsx` hard-codes
  `RPE65_V2` into the viewer and passes the same sample into the side panel.
- `app/frontend/src/lib/workbench/gene-window.ts` defines the current
  `GeneWindowData` shape and pure flattening/codon/consequence helpers.
- `app/backend/app/services/sequence_context.py` resolves a narrow sequence
  context for real primer and CRISPR engines, but it does not return a full
  transcript/exon/intron/protein viewer model.
- `app/backend/app/api/routes/workbench.py` exposes `/api/v1/primer`,
  `/api/v1/crispr`, and `/api/v1/align`, with no viewer endpoint yet.

This design covers the backend contract and integration path for a real,
gene-agnostic viewer. It includes the frontend adapter/toggle because the API
shape must be useful to the existing viewer, but it does not implement frontend
code in this planning task.

Official API references checked while drafting:

- Ensembl REST `sequence/region` returns genomic sequence for a region and has
  a 10 Mb request limit:
  https://rest.ensembl.org/documentation/info/sequence_region
- Ensembl REST `overlap/id` and `overlap/region` return features including
  transcripts, exons, CDS, variants, and MANE annotations, with 5 Mb overlap
  limits:
  https://rest.ensembl.org/documentation/info/overlap_id and
  https://rest.ensembl.org/documentation/info/overlap_region
- Ensembl REST `overlap/translation` returns protein features for a translation:
  https://rest.ensembl.org/documentation/info/overlap_translation
- NCBI documents ClinVar programmatic access through E-utilities
  `esearch`, `esummary`, `elink`, and `efetch`:
  https://www.ncbi.nlm.nih.gov/clinvar/docs/programmatic_access/

## Goals

- Build a gene-agnostic backend viewer contract that can render RPE65 now and
  other human genes once transcript and variant resolution succeeds.
- Keep one coordinate model for the viewer and downstream primer, CRISPR, and
  alignment tools.
- Preserve the current viewer's useful frontend model: exon/intron segments,
  codon detail, ClinVar density, protein features, selected variant, and edit
  scratchpad behavior.
- Preserve the frontend's genomic and sequence views, and replace the removed
  exon-only third view with a protein view. The protein view should show
  protein domains/features and ClinVar variants projected to amino-acid
  coordinates.
- Support an explicit reference/control versus variant-applied mode so users
  know whether they are inspecting the source reference or the altered allele.
- Label data provenance and limitations clearly enough that generated sequences
  and annotations are auditable.

## Non-Goals

- Do not replace the whole backend with the project skeleton from the supplied
  document.
- Do not introduce PostgreSQL, Redis, Celery, PostGIS, or SQLModel in the first
  viewer slice.
- Do not make primer, CRISPR, or alignment depend on a new viewer context until
  the viewer contract is implemented and contract-tested.
- Do not claim whole-genome or production-grade ClinVar/UniProt completeness
  before ingestion, caching, and source versioning are implemented.

## Constraints

- The current repo supports Python `>=3.10`; do not force a Python 3.12
  migration for this feature.
- Existing `PrimerRequest`, `CrisprRequest`, and `AlignRequest` contracts stay
  stable unless the user explicitly approves a paired contract change.
- Backend schema changes are backend-led and must update
  `app/frontend/src/lib/backend.ts` plus `test_frontend_contract.py`.
- Fixture mode must continue to work offline. RPE65 remains the fixture/live
  smoke example, not a hard-coded service assumption.
- Reverse-strand genes, including RPE65, are first-class. Viewer coordinates
  must be transcript-oriented while retaining genomic provenance.

## Proposed Design

Add a backend `GeneViewerService` behind a new viewer endpoint. The service
composes transcript resolution, source-backed sequence fetch, coordinate
projection, variant overlay, annotation hydration, and render payload shaping.

Preferred first endpoint:

```text
POST /api/v1/viewer
```

Request body:

```json
{
  "gene": "RPE65",
  "cdna": "c.260A>G",
  "transcript": "NM_000329.3",
  "species": "human",
  "genome_build": "GRCh38",
  "allele_mode": "reference",
  "window": { "kind": "around_variant", "cds_flank_bp": 120, "intron_flank_bp": 30 },
  "tracks": ["sequence", "exons", "clinvar", "protein_features", "restriction"]
}
```

`POST` is preferred over the supplied brief's `GET /viewer/transcript/{id}` for
the first slice because existing Workbench engines already use payload-based
requests, and viewer state includes filters and allele mode. A transcript GET
route can be added later for deep links.

High-level flow:

1. Normalize `gene`, `cdna`, and optional `transcript` with the existing
   sequence-query logic.
2. Resolve the transcript. If `transcript` is omitted, prefer a MANE Select or
   configured canonical transcript; for RPE65, bridge the current RefSeq
   `NM_000329.3` convention to the Ensembl/MANE transcript when source data
   provides that cross-reference.
3. Build a transcript model: gene locus, strand, exons, CDS bounds, UTR lengths,
   coding coordinates, and translation id where available.
4. Fetch reference/control sequence in transcript 5 prime to 3 prime
   orientation. For introns, fetch only configured flanks and represent the
   omitted middle as a gap segment.
5. Project the requested variant onto the transcript/CDS model and validate
   that the source reference base or allele matches the normalized variant.
6. Apply the variant only as an explicit overlay. In `reference` mode, segments
   contain the reference/control sequence and the variant is highlighted. In
   `variant` mode, the active displayed sequence contains the altered allele,
   while reference sequence and coordinate provenance remain available.
7. Attach annotations: nearby ClinVar variants, exon variant density, protein
   domains and binding/active sites, restriction sites, and source metadata.
8. Return a render-ready payload that the frontend adapter maps into the
   existing `GeneWindowData` interface.

### Protein View And ClinVar Lollipop Direction

Decision added 2026-05-18 15:18 +1000 - Codex after user review: the third
viewer mode should be `protein`, not the removed exon-only mode. The protein
view should use a lollipop-style mutation track over the protein backbone and
domain/features track.

Rationale:

- GDC ProteinPaint uses a lollipop chart plus protein view: discs represent
  variants, the protein view displays coding regions and domains, and users can
  switch display tracks including a protein track:
  https://docs.gdc.cancer.gov/Data_Portal/Users_Guide/proteinpaint_lollipop/
- SRplot's lollipop mutation diagram takes UniProt position/ref/alt/point-size
  inputs and uses UniProt/Pfam APIs to add domains/motifs:
  http://www.bioinformatics.com.cn/plot_basic_lollipop_mutation_diagram_090_en
- This matches the Eamos task better than an exon-only tab: clinicians can see
  whether the queried variant and nearby ClinVar variants cluster in a domain,
  active-site region, membrane-binding region, or low-complexity segment.

ClinVar caveat: ClinVar is a curated clinical-variation database, not a cohort
occurrence table. Lollipop marker size must not imply patient frequency unless
we have a frequency/count source. First implementation should either use
uniform markers or size by explicitly labelled record aggregation at the same
protein residue.

## Interfaces And Data

Backend schemas should use snake_case Pydantic models. Frontend mirrors should
use the existing contract-sync pattern and adapt to `GeneWindowData`.

Important response groups:

- `identity`: gene, Ensembl gene id, requested transcript, resolved transcript,
  transcript aliases, species, genome build.
- `locus`: chromosome, gene start/end, strand, transcript start/end.
- `window`: active coordinates, allele mode, intron flank policy, source
  checksums.
- `segments`: exon and intron-flank segments in transcript display order.
- `variant`: normalized HGVS, CDS position, genomic position, ref, alt, codon
  and protein consequence when available.
- `sequences`: reference/control sequence for the active window, active display
  sequence, and a structured `applied_variant` object when in variant mode.
- `tracks`: ClinVar, exon density, protein features, conservation where
  available, restriction sites, and future tool overlays.
- `provenance`: source names, URLs or identifiers, source timestamps/versions
  where available, and warnings.

## Alternatives Considered

- Full ingest database first: stronger for production but too large for the
  current Workbench milestone. It would delay unblocking the viewer and tools.
- Extend `SequenceContextService` directly: attractive for reuse, but its
  current responsibility is a narrow engine template. A viewer service can use
  it while keeping transcript annotations and UI payload shaping separate.
- Keep viewer frontend-only and pass sequence snippets to tools: fastest, but
  risks coordinate drift between viewer, primer, CRISPR, and alignment.
- Add reference/variant mode only in frontend edits: simpler UI work, but it
  would hide whether the altered allele is source-backed and would not help
  backend tools consume the same sequence basis.

## Tradeoffs

- Returning a render-ready payload reduces frontend logic and coordinate drift,
  but makes the backend contract larger and more consequential.
- Starting with live providers plus fixture fallback avoids a database migration,
  but repeated source calls need cache discipline before heavy use.
- Defaulting to reference/control mode is safer for coordinates; users must
  explicitly choose variant-applied mode when they want tools to operate on the
  altered allele.

## Cross-Cutting Concerns

- Accuracy: fail closed on reference-base mismatch, unsupported HGVS, or
  ambiguous transcript mapping.
- Performance: keep windows bounded, return only requested tracks, and add a
  simple cache boundary before introducing Redis.
- Privacy: do not send patient-specific uploaded sequence data to external
  services without explicit future approval. The first slice uses public gene
  and variant identifiers only.
- Observability: log provider name, source identifier, transcript, window size,
  warnings, and cache hit/miss without logging raw patient files.
- Reliability: fixture mode must remain deterministic and offline; live mode
  should degrade with structured errors, not silent mock substitution.

## Rollout And Migration

1. Add backend schemas, fixture payload, and API tests without wiring the
   frontend.
2. Implement source-backed RPE65/SNV happy path and synthetic plus/minus strand
   coordinate tests.
3. Mirror the contract in `backend.ts` and add frontend adapter tests.
4. Let Claude/front-end work switch `WorkbenchShell` from hard-coded
   `RPE65_V2` to the viewer API with sample fallback and the reference/variant
   toggle.
5. After the viewer is trusted, add optional `sequence_mode` or
   `viewer_context_id` to primer, CRISPR, and alignment requests in a separate
   backend-led contract change.

## Open Questions

- Should the first UI default be reference/control mode or variant-applied
  mode? Recommendation: default to reference/control, with the queried variant
  highlighted and an explicit variant mode toggle.
- How broad should the first live annotation scope be? Recommendation: exons,
  CDS, UTRs, variant projection, and basic protein features first; ClinVar
  density can start fixture-backed or bounded to the window.
- Should long-term caching be local file/SQLite first or Redis? Recommendation:
  add an in-process/file cache boundary first and defer Redis until source call
  volume justifies another runtime.

## Decision

Proceed, after review, with a backend-led gene viewer contract and service that
uses RPE65 as the first live acceptance case but does not encode RPE65 as a
special case. Default to reference/control display, make variant-applied display
explicit, and keep primer/CRISPR/alignment contract changes as follow-up work.
