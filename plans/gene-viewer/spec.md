# Gene Viewer Implementation Spec

Section edited: 2026-05-18 12:01 +1000 · Codex.

## What

Build a gene-agnostic Workbench gene viewer backend contract and service that
returns an exact, render-ready transcript window for the selected variant. The
first live acceptance example is RPE65 `c.260A>G`, but the implementation must
resolve genes and transcripts generically. The viewer must support an explicit
reference/control versus variant-applied mode so the user can decide which
sequence basis they are inspecting and, later, which basis downstream tools use.

## Context

Today the Workbench viewer is driven by `RPE65_V2`, a TypeScript sample in
`app/frontend/src/lib/workbench/sample-rpe65-v2.ts`. The viewer components and
pure helpers in `app/frontend/src/components/workbench/viewer/**` and
`app/frontend/src/lib/workbench/gene-window.ts` are useful and should not be
rewritten first. The backend has real sequence context for primer/CRISPR
through `app/backend/app/services/sequence_context.py`, but that context is a
narrow engine template, not a full transcript viewer payload.

The supplied RPE65 brief asks for exact DNA, correct coordinate systems, rich
annotations, and fast viewer payloads. This spec adopts those product
requirements while fitting the existing Eamos app instead of replacing the
project stack.

## Requirements

- The backend must expose a viewer endpoint that accepts `gene`, `cdna`,
  optional `transcript`, `species`, `genome_build`, `allele_mode`, `window`,
  and requested `tracks`.
- The endpoint must return a typed payload that can be adapted into the current
  frontend `GeneWindowData` shape without hard-coded RPE65 assumptions.
- The first live path must support human GRCh38 coding SNVs resolved from cDNA
  HGVS, including reverse-strand genes such as RPE65.
- The service must fetch or derive reference/control sequence first, then apply
  the variant overlay only when `allele_mode == "variant"`.
- The response must preserve both the reference/control sequence and the active
  display sequence, plus a structured record of any applied variant.
- The default `allele_mode` must be `reference` unless the user or UI explicitly
  chooses `variant`.
- The response must include transcript/gene identity, exon/CDS/UTR structure,
  intron-flank segments, queried variant metadata, protein feature tracks where
  available, nearby/density variant tracks where available, and provenance.
- Frontend viewer modes should be genomic, sequence, and protein. The protein
  mode replaces the removed exon-only mode and should render a domain-aware
  lollipop view for protein-coordinate ClinVar variants.
- RPE65 data may be used for fixtures and live smoke checks, but no service
  branch may special-case RPE65 except a temporary canonical-transcript mapping
  fallback already consistent with the existing `CANONICAL_TRANSCRIPTS` pattern.
- Missing or inconsistent source data must return structured errors/warnings;
  the backend must not silently mutate an allele if the reference base does not
  match the normalized variant.
- Fixture/offline mode must remain deterministic and must continue to let the
  Workbench render when live providers are disabled.

## Design

### Backend Modules

Add:

- `app/backend/app/schemas/gene_viewer.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/tests/test_gene_viewer.py`

Extend:

- `app/backend/app/api/routes/workbench.py` or a new route module mounted under
  the existing `/api/v1` prefix.
- `app/backend/app/main.py` only as needed to wire the service.
- `app/backend/tests/test_frontend_contract.py` once frontend mirror types are
  added.
- `app/frontend/src/lib/backend.ts` and `app/frontend/src/lib/api.ts` in the
  frontend integration slice, not during backend-only service work.

### Endpoint

Preferred first endpoint:

```text
POST /api/v1/viewer
```

Initial request model:

```python
AlleleMode = Literal["reference", "variant"]
ViewerTrack = Literal[
    "sequence",
    "exons",
    "clinvar",
    "protein_features",
    "restriction",
    "conservation",
]

class ViewerWindowRequest(BaseModel):
    kind: Literal["around_variant", "cds_range"] = "around_variant"
    cds_start: int | None = None
    cds_end: int | None = None
    cds_flank_bp: int = 120
    intron_flank_bp: int = 30

class GeneViewerRequest(BaseModel):
    gene: str
    cdna: str
    transcript: str | None = None
    species: str = "human"
    genome_build: str = "GRCh38"
    allele_mode: AlleleMode = "reference"
    window: ViewerWindowRequest = Field(default_factory=ViewerWindowRequest)
    tracks: list[ViewerTrack] = Field(default_factory=lambda: [
        "sequence",
        "exons",
        "clinvar",
        "protein_features",
        "restriction",
    ])
```

Initial response model should be close to, but not constrained by,
`GeneWindowData`. Backend fields stay snake_case and the frontend adapter maps
to camelCase.

Required response groups:

- `identity`: `gene`, `ensembl_gene_id`, `requested_transcript`,
  `resolved_transcript`, `transcript_aliases`, `species`, `genome_build`.
- `locus`: `chrom`, `gene_start`, `gene_end`, `strand`.
- `summary`: `gene_length`, `total_exons`, `cds_length`, `protein_length`,
  `utr5_length`, `utr3_length`, `mrna_length`.
- `segments`: exon and intron flank segments in display order, including CDS
  positions for exon bases and omitted lengths for introns.
- `queried_variant`: normalized HGVS, CDS position, genomic coordinate, ref,
  alt, codon/protein summary, and classification if known.
- `sequences`: `allele_mode`, `reference_window_sequence`,
  `display_window_sequence`, and `applied_variant`.
- `tracks`: ClinVar variants/density, protein features, conservation, and
  restriction sites where requested and available.
- `provenance`: provider names, source ids/URLs, checksums, source versions
  where available, and warnings.

Protein-view projection requirements:

- ClinVar coding variants should carry enough data for the frontend to project
  them to amino-acid coordinates when `hgvs_p`, codon number, or CDS position
  is available.
- Protein lollipop marker labels should use DNA/cDNA notation first and protein
  consequence second.
- Marker size must not be labelled as patient frequency unless the backend
  provides a real frequency/count source. For ClinVar-only data, use uniform
  markers or explicitly label size as same-residue record aggregation.
- Protein domains/features should prefer source-backed Ensembl translation
  overlap and later UniProt/Pfam/CDD/SMART hydration when available.

### Service Flow

1. Normalize input using the existing `normalize_sequence_query()` behavior.
2. Resolve transcript identity:
   - Use the provided transcript when present.
   - Otherwise prefer MANE Select/source canonical data.
   - Fall back to a small configured canonical map only when source lookup does
     not provide a canonical transcript.
3. Fetch transcript structure and source identifiers:
   - Ensembl lookup/overlap for gene, transcript, exon, CDS, MANE, and
     translation id.
   - Preserve both RefSeq and Ensembl aliases when available.
4. Resolve the variant:
   - Reuse VariantValidator where already configured for cDNA HGVS -> GRCh38.
   - Validate that source reference allele matches the requested HGVS.
5. Build the transcript-oriented window:
   - Exon segments are in transcript 5 prime to 3 prime order.
   - Intron segments include only configured donor/acceptor flanks and a gap.
   - Reverse-strand genes must render in transcript orientation while retaining
     genomic coordinates and strand.
6. Apply allele mode:
   - `reference`: display sequence equals reference/control sequence.
   - `variant`: display sequence applies the requested variant to the display
     window and records exactly what changed.
   - First implementation supports SNV overlays; indels return a structured
     unsupported warning/error unless explicitly implemented.
7. Hydrate tracks:
   - Exon/CDS/UTR tracks are required.
- Protein features can use Ensembl translation overlap first and UniProt
  feature JSON where an accession is available.
- ClinVar can start with window-bounded E-utilities or fixture data; do not
  claim complete gene-wide density without pagination/source coverage.
8. Return the payload through Pydantic validation.

## Decisions

- Decision: add a new viewer endpoint instead of embedding viewer payloads in
  primer/CRISPR/alignment responses.
  Alternatives: extend every tool response or keep frontend-only viewer data.
  Rationale: one viewer contract avoids drift and lets tools converge later.
  Reversible: yes, but downstream code should not duplicate coordinate logic.

- Decision: default to `allele_mode="reference"`.
  Alternatives: default to variant-applied display.
  Rationale: reference/control sequence is the coordinate truth; variant mode
  should be an explicit user choice.
  Reversible: yes, via UI/default request change.

- Decision: first live variant overlay supports SNVs only.
  Alternatives: implement indels immediately.
  Rationale: current RPE65 example and existing edit model are SNV-centric;
  indel-aware downstream translation is already called out as deferred.
  Reversible: yes, by extending overlay and translation tests.

- Decision: no first-slice PostgreSQL/Redis/Celery migration.
  Alternatives: implement the supplied full production stack.
  Rationale: Eamos already has a working FastAPI/SQLite/fixture architecture;
  the viewer needs a trusted contract before new infrastructure.
  Reversible: yes, after source hydration and cache keys are stable.

- Assumption: RPE65 remains the first live smoke fixture, but the target
  service is any human coding gene with a resolvable transcript and cDNA HGVS.

## Versions

- Current backend package metadata requires Python `>=3.10`; this spec does
  not require a Python runtime migration.
- Existing backend dependency pins remain in `app/backend/requirements.txt`.
- Use Ensembl REST endpoints documented as current on 2026-05-18, including
  `sequence/region`, `overlap/id`, `overlap/region`, and
  `overlap/translation`.
- Use NCBI ClinVar E-utilities only through documented `esearch`, `esummary`,
  `elink`, or `efetch` flows.

## Invariants

- `USE_REAL_APIS=false` must keep the Workbench renderable from fixtures.
- Primer, CRISPR, and alignment endpoint response shapes must not change in the
  first viewer service slice.
- The frontend contract canary must pass after any `backend.ts` mirror update.
- RPE65 reverse-strand cDNA coordinate mapping must be explicitly tested.
- Reference/control and variant-applied sequences must carry the same
  coordinate provenance unless an unsupported variant type prevents this.

## Error Behavior

- Unsupported species or build: `422` with `workbench_unsupported_input:*`.
- Missing sequence/transcript source: `422` for unsupported input or `503` for
  provider availability/failure, following existing Workbench error style.
- Reference allele mismatch: fail closed with `422
  workbench_unsupported_input:reference_mismatch`.
- Ambiguous transcript selection: return `422
  workbench_unsupported_input:ambiguous_transcript` and include candidate
  transcripts in warnings/metadata when safe.
- External provider timeout/failure: return structured `503
  workbench_provider_failed:<provider>`.
- Missing optional tracks: return the viewer payload with warnings only if core
  sequence, transcript structure, and variant projection are valid.

## Testing Strategy

- Backend unit tests for transcript window building on synthetic plus-strand
  and minus-strand genes.
- Backend unit tests for SNV overlay in `reference` and `variant` modes.
- Backend fixture/API test that `POST /api/v1/viewer` returns the RPE65 sample
  shape offline and validates through Pydantic.
- Backend provider tests with mocked Ensembl/VariantValidator/UniProt/ClinVar
  responses; no network in default tests.
- Contract test update for new viewer schemas and mirrored TypeScript types.
- Frontend adapter unit tests mapping backend response to `GeneWindowData`.
- Frontend toggle tests proving reference mode and variant mode change the
  displayed base while preserving queried-variant metadata.
- Browser verification after frontend integration: viewer renders, toggle is
  visible, primer/CRISPR panels still keep viewer visible above, and no text or
  tracks overlap.
- Optional live smoke with `USE_REAL_APIS=true` for RPE65 `c.260A>G`, recorded
  as a non-default verification because it depends on external services.

## Out Of Scope

- Full gene database ingest and persistent transcript/feature tables.
- Redis/Celery/PostGIS/pgvector.
- Full ClinVar gene-wide synchronization.
- Patient uploaded sequence handling.
- Indel-aware downstream protein retranslation.
- Primer/CRISPR/alignment contract changes to consume `allele_mode` or a
  viewer context id. Those are follow-up tasks after the viewer contract is
  approved.

## Review Gate

Review and approve this spec before implementation. The safest first
implementation is backend-only: schemas, fixture payload, service skeleton,
coordinate/overlay tests, and `POST /api/v1/viewer` without switching the
frontend off `RPE65_V2` yet.
