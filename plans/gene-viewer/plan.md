# Gene Viewer Implementation Plan

Section edited: 2026-05-18 15:18 +1000 - Codex.

## Shared Decisions Before Work Starts

- Backend owns the new viewer contract and any mirror changes to
  `app/frontend/src/lib/backend.ts`.
- First default display mode is reference/control. Variant-applied mode is an
  explicit request/UI toggle.
- Frontend viewer modes should be genomic, sequence, and protein. The protein
  view replaces the removed exon-only view and should use a domain-aware
  lollipop track for ClinVar variants projected to protein coordinates.
- RPE65 `c.260A>G` is the live acceptance example, not a hard-coded service
  branch.
- Do not modify primer, CRISPR, or alignment request/response schemas until the
  viewer endpoint is implemented and reviewed.

## Task GV-001 - Backend Viewer Schemas And Offline Fixture

Status: DONE 2026-05-18 14:38 +1000 · Codex. Backend-only schemas, fixture
provider, RPE65 offline fixture, and fixture validation tests are implemented.
No frontend files or existing Workbench tool contracts changed.

Goal: define the typed backend viewer request/response contract and fixture
mode without live provider work.

Context: the current viewer sample lives in
`app/frontend/src/lib/workbench/sample-rpe65-v2.ts`; backend Workbench fixtures
live under `app/backend/app/fixtures/workbench`.

Relevant files:

- `app/backend/app/schemas/gene_viewer.py`
- `app/backend/app/fixtures/workbench/viewer_rpe65.json`
- `app/backend/tests/test_gene_viewer.py`
- `app/backend/tests/test_frontend_contract.py` only if TS mirror is included

Proposed approach:

- Add Pydantic models for `GeneViewerRequest`, `ViewerWindowRequest`,
  `GeneViewerResponse`, segments, queried variant, sequences, tracks, and
  provenance.
- Transcribe the current RPE65 sample into a backend JSON fixture with the new
  snake_case contract.
- Add a fixture provider that validates the JSON through the Pydantic response
  model.

Acceptance criteria:

- Fixture mode returns a valid RPE65 viewer response.
- The fixture includes reference/control sequence, active display sequence, and
  `allele_mode`.
- No frontend code or existing Workbench tool contracts change.

Source reference: `plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_gene_viewer.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

Out of scope: live Ensembl/ClinVar/UniProt calls.

## Task GV-002 - Transcript Window Builder And Variant Overlay

Status: DONE 2026-05-18 14:38 +1000 · Codex. Pure transcript window builder,
SNV overlay, plus-strand tests, reverse-strand transcript-order tests, and
reference-mismatch fail-closed tests are implemented.

Goal: implement the pure coordinate/window layer that turns a resolved
transcript model plus a variant into viewer segments.

Context: this is the accuracy core. It must be independent of external HTTP so
it can be thoroughly unit-tested.

Relevant files:

- `app/backend/app/services/gene_viewer.py`
- future `app/backend/app/services/coordinate_utils.py` if the module gets too
  large
- `app/backend/tests/test_gene_viewer.py`

Proposed approach:

- Define internal dataclasses for transcript exons, CDS bounds, introns,
  window segments, and variant projection.
- Build windows in transcript 5 prime to 3 prime order.
- Implement SNV overlay for `reference` and `variant` modes.
- Add synthetic plus-strand and reverse-strand tests, then RPE65 c.260A>G
  fixture tests.

Acceptance criteria:

- Reverse-strand transcripts render in transcript order.
- `reference` mode leaves the reference base unchanged and highlights the
  queried variant.
- `variant` mode changes only the requested SNV base in the active display
  sequence.
- Reference-base mismatches fail closed.

Source reference: `plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_gene_viewer.py -q
python -m pytest tests/test_sequence_context.py -q
```

Out of scope: external data source clients.

## Task GV-003 - Source-Backed Viewer Provider

Status: DONE 2026-05-18 14:56 +1000 - Codex. Added the real-mode provider
boundary, source-client protocol, VariantValidator/Ensembl HTTP source-client
skeleton, mocked official-source provider tests, source provenance handling,
unsupported-input validation, and provider-failure mapping. Default tests make
no network calls. The default HTTP client resolves VariantValidator and Ensembl
sequence windows but deliberately keeps full transcript-structure hydration
behind the source-client seam until GV-008 live-smoke hardening.

Goal: resolve source-backed transcript structure, reference sequence, and
variant coordinates for live mode.

Context: existing `SequenceContextService` already normalizes cDNA HGVS and
uses VariantValidator plus Ensembl sequence for narrow engine context. The
viewer needs a richer transcript model.

Relevant files:

- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/services/sequence_context.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_gene_viewer.py`

Proposed approach:

- Reuse `normalize_sequence_query()` and VariantValidator resolution where
  possible.
- Add provider seams for Ensembl transcript/gene lookup, Ensembl sequence, and
  optional protein feature lookup. GV-008 later hardened the default HTTP
  client for Ensembl symbol/transcript hydration and Ensembl translation
  protein-feature overlap.
- Mock all provider responses in default tests.
- Preserve source metadata and URLs in response provenance.

Acceptance criteria:

- Live-mode provider can build the RPE65 c.260A>G viewer model with mocked
  official-source responses. GV-008 later added a live-smoked default HTTP
  Ensembl transcript/protein-feature path.
- Unsupported species/build/query kinds return structured errors.
- Provider failures map to existing Workbench-style 503 detail objects.

Source reference: supplied RPE65 backend brief and
`plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_gene_viewer.py tests/test_sequence_context.py -q
python -m pytest tests/test_workbench_api.py -q
```

Out of scope: persistent ingest database and Redis cache.

## Task GV-004 - Viewer API Route And Service Wiring

Status: DONE 2026-05-18 14:56 +1000 - Codex. Added
`app/backend/app/api/routes/gene_viewer.py`, mounted `POST /api/v1/viewer`,
wired `app.state.gene_viewer_service`, preserved fixture-mode RPE65 behavior,
made fixture variant mode apply the c.260A>G SNV, and added route tests for
fixture, injected real-mode provider, and structured error responses.

Goal: expose `POST /api/v1/viewer` through FastAPI and wire fixture/live mode.

Context: Workbench engine routes currently live in
`app/backend/app/api/routes/workbench.py`; the viewer can be added there or in
a dedicated route module mounted under the same API prefix.

Relevant files:

- `app/backend/app/api/routes/workbench.py` or
  `app/backend/app/api/routes/gene_viewer.py`
- `app/backend/app/main.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/tests/test_gene_viewer.py`

Proposed approach:

- Create a `GeneViewerService` on app state alongside the existing
  WorkbenchDesignService.
- In fixture mode, return the validated RPE65 fixture for the canonical RPE65
  request.
- In live mode, call the source-backed provider and window builder.
- Reuse `WorkbenchDesignError` shape or add a matching viewer error class.

Acceptance criteria:

- `POST /api/v1/viewer` returns 200 for RPE65 fixture mode.
- Malformed provider data returns 502; provider unavailable returns 503;
  unsupported input returns 422.
- Existing `/primer`, `/crispr`, and `/align` tests still pass unchanged.

Source reference: `plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_gene_viewer.py tests/test_workbench_api.py -q
python -m pytest tests/test_frontend_contract.py -q
```

Out of scope: frontend rendering switch.

## Task GV-005 - Frontend Contract Mirror And Adapter

Goal: mirror the backend viewer schema in TypeScript and adapt it to the
existing `GeneWindowData` renderer model.

Context: frontend contract changes are backend-led but implementation in
`app/frontend/**` should be coordinated with Claude/frontend ownership.

Relevant files:

- `app/frontend/src/lib/backend.ts`
- `app/frontend/src/lib/api.ts`
- future `app/frontend/src/lib/workbench/gene-viewer-adapter.ts`
- `app/frontend/src/lib/workbench/gene-window.ts`
- `app/backend/tests/test_frontend_contract.py`

Proposed approach:

- Add TypeScript interfaces that mirror the new Pydantic viewer models.
- Add `getGeneViewer(payload)` API function.
- Add a pure adapter from backend response to `GeneWindowData`.
- Add/confirm protein-view adapter data for domains/features and lollipop
  variants projected from ClinVar coding variants.
- Keep `RPE65_V2` as fallback/sample data until the UI integration task.

Acceptance criteria:

- Contract canary covers the new viewer schemas.
- Adapter maps fixture response into the same visible viewer data as the
  current RPE65 sample.
- Adapter exposes the three intended frontend modes: genomic, sequence, and
  protein. The old exon-only third mode should not be restored.
- No visual UI behavior changes yet.

Source reference: `plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_frontend_contract.py -q
cd ../frontend
npx vitest run
npm run build
```

Out of scope: visible reference/variant toggle.

## Task GV-006 - Frontend Viewer Data Loading And Allele Toggle

Goal: switch the Workbench viewer from hard-coded `RPE65_V2` to the viewer API
with sample fallback and a clear reference/control versus variant toggle.

Context: this is frontend-owned under the current collaboration split. The
viewer must remain visible above primer and CRISPR panels.

Relevant files:

- `app/frontend/src/components/workbench/WorkbenchShell.tsx`
- `app/frontend/src/components/workbench/CanvasHeader.tsx`
- `app/frontend/src/components/workbench/SidePanel.tsx`
- `app/frontend/src/styles/workbench.css`
- `app/frontend/src/lib/api.ts`
- `app/frontend/src/lib/workbench/gene-viewer-adapter.ts`

Proposed approach:

- Load viewer data for the active gene/cDNA request.
- Add a compact segmented toggle for reference/control and variant-applied
  mode.
- Add the third viewer mode as protein view, showing protein domains/features
  plus a ClinVar lollipop track. Do not re-add an exon-only tab.
- Re-fetch or re-adapt data when `allele_mode` changes.
- Preserve existing selection, edit hub, zoom, tracks, and side-panel behavior
  where possible.

Acceptance criteria:

- Viewer renders from backend fixture/API data.
- Toggle visibly changes c.260 from reference A to variant G for RPE65 while
  preserving variant labels and coordinates.
- Protein mode renders the RPE65 carotenoid oxygenase domain and places
  c.260A>G / p.Asp87Gly at amino acid 87 on the lollipop track.
- Backend transport failure can fall back to sample data in dev/pixel-check
  mode without masking reachable backend errors.
- Primer/CRISPR panels still render below the viewer.

Source reference: `plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/frontend
npx vitest run
npm run build
cd ../backend
python -m pytest tests/test_frontend_contract.py -q
```

Browser verification is required after this task.

## Task GV-007 - Tool Sequence-Basis Follow-Up

Goal: decide and implement how primer, CRISPR, and alignment consume the
viewer-selected sequence basis.

Context: the user specifically wants a toggle for whether work is on the
reference/control gene or the variant. The display toggle should land before
tool contract changes.

Relevant files:

- `app/backend/app/schemas/workbench.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/app/services/gene_viewer.py`
- `app/frontend/src/lib/backend.ts`
- CRISPR/primer/alignment frontend panels when active

Proposed approach:

- Add an approved optional field such as `sequence_mode:
  "reference" | "variant"` or a future `viewer_context_id`.
- Route engine sequence context through the same overlay logic used by the
  viewer.
- Preserve current defaults for existing tool calls.

Acceptance criteria:

- Tools default to existing behavior unless `sequence_mode` is explicitly set.
- A selected variant basis produces provider input consistent with the viewer
  active display sequence.
- Contract canary and tool-specific backend tests pass.

Source reference: `plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_workbench_api.py tests/test_gene_viewer.py tests/test_frontend_contract.py -q
```

Out of scope: full alignment/AB1/TIDE implementation.

## Task GV-008 - Live RPE65 Smoke And Documentation Update

Status: DONE 2026-05-18 15:18 +1000 - Codex. Default HTTP live mode now
hydrates RPE65 transcript structure from Ensembl symbol lookup, source-backed
sequence windows from Ensembl sequence/region, VariantValidator GRCh38
projection/protein consequence, and protein domains from Ensembl translation
overlap. Live RPE65 reference and variant smoke checks passed.

Goal: prove the source-backed path against RPE65 and record any provider/data
limitations.

Context: live checks are not default tests because Ensembl, VariantValidator,
UniProt, and ClinVar availability can vary.

Relevant files:

- `plans/gene-viewer/spec.md`
- `agent_handoff/RISKS.md`
- `agent_handoff/CURRENT.md`
- any endpoint/provider docs added during implementation

Proposed approach:

- Implemented Ensembl symbol/transcript parsing for coding exon/CDS projection,
  intron intervals, transcript aliases, UTR/CDS/protein summary lengths, and
  Ensembl translation protein-feature/domain parsing.
- With `USE_REAL_APIS=true`, called the source-backed viewer service for RPE65
  c.260A>G in reference and variant modes.
- Confirmed transcript `NM_000329.3` / `ENST00000262340.6` MANE Select, chr1
  reverse strand, 14 total exons, rendered exon-3 to exon-5 window
  `c.140-c.380`, selected exon 4 segment `exon-4:246-353`, reference base `A`,
  variant-applied base `G`, and protein consequence `p.Asp87Gly`.
- Confirmed protein domains from Ensembl translation overlap include
  carotenoid oxygenase ranges (`aa 16-531` Pfam and `aa 17-531` PANTHER).
- Recorded source URLs and warnings. Current live warnings:
  `live_source_transcript_from_ensembl`,
  `clinvar_track_not_live_hydrated`,
  `protein_features_from_ensembl_overlap`, and
  `ensembl_transcript:ENST00000262340`.

Acceptance criteria:

- Live RPE65 response is source-backed.
- Discrepancies documented: live Ensembl gene start is `68428822` and live
  coding window/variant offset differ from the old offline sample because the
  live response uses source transcript coordinates and window-limited sequence
  fetches; the fixture remains an offline renderer sample.
- Handoff docs identify remaining accuracy risks.

Source reference: supplied RPE65 backend brief and
`plans/gene-viewer/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_gene_viewer.py tests/test_workbench_api.py tests/test_frontend_contract.py -q
```

Verification completed:

- `cd app/backend && python -m pytest tests/test_gene_viewer.py -q`
  -> 18 passed.
- Live source-backed in-process smoke for RPE65 `c.260A>G`, reference and
  variant modes, `USE_REAL_APIS=true` semantics -> pass. Reference mode kept
  display base `A`; variant mode applied `G` at offset 180.
- Live `POST /api/v1/viewer` route smoke with `USE_REAL_APIS=true` semantics
  -> HTTP 200 in reference and variant modes with the same A-to-G base check.
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_workbench_api.py tests/test_frontend_contract.py -q`
  -> 78 passed.
- `cd app/backend && python -m ruff check app tests` -> pass.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> pass.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  -> 138 passed / 4 skipped.

Out of scope: frontend protein-view/lollipop implementation, live ClinVar
gene-wide variant hydration, cohort/frequency-sized lollipops, UniProt/Pfam/CDD
cross-source reconciliation, and downstream tool sequence-basis changes.
