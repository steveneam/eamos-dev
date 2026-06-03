# Backend Evidence Roadmap Spec

Status: Draft for user review
Owner: Codex/backend
Last updated: 2026-06-03 23:55 +1000 - Codex

## What

Build the next backend evidence foundation for Eamos: a local-first adapter
contract, gated runtime asset wiring, advisory ACMG/PVS1 engines, literature
and AI-gateway scaffolding, and predictor lanes with AlphaMissense prepared
behind gates and ESM1b kept license-blocked until provenance is safe.

## Context

Source design:

- `docs/backend-evidence-roadmap/design.md`

Related existing docs:

- `docs/local-first-data-source-strategy/design.md`
- `docs/local-first-data-source-strategy/spec.md`
- `docs/local-first-data-source-strategy/plan.md`
- `docs/local-first-data-source-strategy/source-asset-rollout.md`

Relevant current code:

- `app/backend/app/data_sources/registry.py`
- `app/backend/app/data_sources/runtime_assets.py`
- `app/backend/app/data_sources/source_manifest.py`
- `app/backend/app/services/indexed_sources.py`
- `app/backend/app/services/source_downloads.py`
- `app/backend/app/services/local_evidence_orchestrator.py`
- `app/backend/app/services/computational_calibration.py`
- `app/backend/app/services/esm1b_assembly.py`

## Requirements

1. Add no Render, Vercel, Oregon, or Supabase mutation as part of this spec.
2. If a future Supabase upload is needed, check the current bucket/file size
   limit before upload and record that limit in the preflight output.
3. Local runtime adapters must resolve from registry metadata, configured
   runtime paths, checksum expectations, and materialization metadata.
4. Local runtime adapters must fail closed when source URL, source version,
   checksum, license status, materialization metadata, or local path validation
   is incomplete.
5. No runtime adapter may download source assets during startup.
6. Disk-gated wiring must wait until Standard 2 GB memory and 60 GB disk at
   `/var/data` are verified.
7. Disk-gated wiring must verify byte counts, checksums, manifests, and
   materialization metadata before request-time source use.
8. Disk-gated wiring must cover dbSNP, phyloP, `hg38.2bit`, ClinVar,
   RepeatMasker, transcript stores, and `LocalEvidenceOrchestrator` only after
   the disk gate passes.
9. The ACMG points engine must be deterministic, Tavtigian/SVI-style, and
   advisory.
10. The ACMG points engine must output transparent evidence items, point totals,
    source provenance, warnings, and reasons for non-counted evidence.
11. The ACMG points engine must not override ClinGen/ClinVar primary verdicts
    or issue final clinical classifications.
12. The PVS1/NMD engine must be conservative and pure code.
13. The PVS1/NMD engine must default false or uncertain when critical-region
    data, LoF mechanism data, transcript geometry, or supported variant shape is
    missing.
14. The PVS1/NMD engine must not use AutoPVS1 code or data.
15. The literature engine starts with schema/API/fixture ETL design only.
16. Literature storage must prefer metadata, identifiers, offsets, bounded
    snippets, and links over full abstract or article text.
17. Supabase literature migrations/imports require execution-specific approval.
18. The AI gateway starts as a mocked/provider-abstracted broker.
19. The AI gateway must use de-identification allowlists, server-side keys only,
    no PHI logging, and no verdict decisions.
20. Real Groq, DeepInfra, or other provider enablement waits for secret and
    config approval.
21. AlphaMissense may be prepared behind gates with materialization/index
    preflight and a runtime adapter wrapper.
22. AlphaMissense runtime display still requires explicit approval.
23. AlphaMissense calibration must use Bergquist 2025 bands for PP3/BP4
    activation, not AlphaMissense developer class labels.
24. ESM1b can add pure-code MANE assembly job scaffolding and fixture manifests.
25. ESM1b public serialization remains blocked until score-file terms are
    confirmed or scores are regenerated from a commercial-safe source path.
26. CI-SpliceAI must stay isolated from the main API path.
27. MaveDB requires per-record CC0 gating and Supabase/import approval.
28. CAPICE remains parked until Steven chooses Pro-only, retrain, or drop.

## Design

### Adapter Root Contract

Every local adapter should be backed by:

- a `DataSourceRecord`;
- source version and checksum policy;
- allowed/restricted fields;
- runtime path config;
- optional object URI;
- materialization metadata when object storage or mounted/cache mode is used;
- preflight/health probe output;
- fail-closed reader resolution.

The `hg38.2bit` runtime asset code is the pattern. Predictor assets should
extend the same contract with generic helpers rather than separate one-off
logic.

### AlphaMissense Preflight And Adapter Wrapper

Add a preflight helper that can report:

- source ID and source version;
- configured local path;
- configured object URI when present;
- expected source MD5 from Zenodo;
- downloaded file presence;
- derived `.tbi` index presence;
- manifest presence;
- byte size if present;
- checksum status if requested;
- materialization metadata status if a store is supplied;
- bucket/file size limit when upload planning is requested.

Add a wrapper that:

- resolves the preflighted local path;
- opens `TabixTsvPredictorReader`;
- queries exact `chrom, position, ref, alt`;
- applies AlphaMissense calibration fields;
- returns provenance and warnings;
- fails closed on missing index, checksum mismatch, wrong source ID, public
  materialization, or display-not-approved settings.

The wrapper must not add AlphaMissense to report display yet.

### ESM1b Assembly Scaffold

Add job-scaffold pieces only:

- parse score rows from fixture or injected rows;
- join to MANE/codon context through explicit inputs;
- emit genomic SNV rows using existing codon primitives;
- produce a manifest with score-source, MANE version, reference checksum,
  code version, output checksum, and warnings;
- keep output fixture-sized by default.

No production ESM1b score download, public serialization, or score-file terms
claim is in scope.

### Deterministic Advisory Engines

ACMG points and PVS1/NMD should live as pure backend services with no provider
or storage dependency. They should consume explicit evidence objects and return
structured advisory outputs that the report can show separately from primary
source verdicts.

### Literature And AI Gateway

Literature and AI gateway work should begin with contracts and fixtures:

- literature query terms, article metadata, source IDs, link-outs, snippets,
  and offsets;
- AI broker provider abstraction, mock provider, redaction/de-identification,
  timeout and error models.

No real provider keys, Supabase writes, or provider activation are in scope.

## Decisions

- Decision: keep this roadmap above the existing local-first source docs.
  - Why: the current work now spans predictors, ACMG, literature, and AI, not
    just source asset rollout.
  - Reversible: yes, by merging into the local-first docs later.

- Decision: AlphaMissense adapter readiness can proceed before display.
  - Why: materialization and reader failure paths need testing before UI
    exposure.
  - Reversible: yes.

- Decision: ESM1b public output stays blocked.
  - Why: score-file terms are unresolved unless regenerated from a safe path.
  - Reversible: only after terms or regeneration approval.

- Decision: ACMG and PVS1/NMD engines are advisory.
  - Why: Eamos should not override primary clinical source verdicts or produce
    final classifications from incomplete evidence.
  - Reversible: not recommended.

- Assumption: "runtime/display approval" for AlphaMissense means report/API
  serialization to user-visible surfaces, not internal preflight and adapter
  tests.

## Invariants

- Default tests require no network, Supabase, production source assets, or real
  AI provider keys.
- Unknown fields and unmaterialized assets deny by default.
- Checksums and byte counts must be verified before request-time local source
  reads.
- Missing local assets must not crash fixture-mode lookups.
- No startup downloads.
- No PHI in AI gateway logs.
- No AI-generated verdict decisions.
- ESM1b, CI-SpliceAI, MaveDB, and CAPICE remain gated as described in the
  requirements.

## Error Behavior

- Missing local file: adapter unavailable, fail closed.
- Missing `.tbi`: adapter unavailable, fail closed.
- Missing manifest: preflight reports not materialized; upload planning blocked.
- Checksum mismatch: adapter unavailable, fail closed.
- Unsupported runtime mode: configuration error in preflight, not request-time
  guessing.
- Materialization metadata public or frontend-readable: fail closed.
- AlphaMissense display not approved: do not serialize to user-visible report
  rows.
- ESM1b terms unresolved: fixture/internal status only.
- Literature license unclear: store metadata/link-out only.
- AI provider not configured: mock or unavailable status, no client error that
  exposes secrets.

## Testing Strategy

Focused backend tests should cover:

- AlphaMissense preflight for missing file, missing index, checksum mismatch,
  ready local path, and sanitized materialization status.
- AlphaMissense wrapper exact variant lookup and calibration with a tiny indexed
  TSV fixture.
- AlphaMissense display gate proving report serialization is unchanged until
  explicitly enabled.
- ESM1b assembly scaffold manifest generation and fail-closed codon/transcript
  mismatches.
- ACMG points deterministic totals and source-separation behavior.
- PVS1/NMD conservative false/uncertain defaults.
- AI gateway mock broker, de-identification, no PHI logging, and no verdict
  decisions.
- Literature fixture ETL without full-text storage.

Baseline checks:

```powershell
cd app/backend
python -m pytest tests/test_data_source_registry.py tests/test_source_downloads.py tests/test_indexed_source_readers.py tests/test_computational_calibration.py tests/test_esm1b_assembly.py -q
```

## Out Of Scope

- Render/Vercel mutation.
- Oregon resources.
- Supabase mutation in this pass.
- Production source download/upload/import.
- Startup downloads.
- AlphaMissense display enablement.
- ESM1b public serialization.
- CI-SpliceAI main-path wiring.
- MaveDB import.
- CAPICE decision or implementation.
- Real AI provider enablement.
