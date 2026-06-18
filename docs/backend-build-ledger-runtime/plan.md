# Backend Build Ledger Runtime Plan

1. Add the shared backend build ledger service.
   - Encode every build-ledger lane in one ordered contract.
   - Attach dynamic inspections for hg38, AlphaMissense, ESM1b, protein assets,
     local evidence gates, and source manifest readiness.
   - Keep serialization sanitized.

2. Wire all selected surfaces horizontally.
   - Add `build_ledger` to `/api/v1/health/provider-cache`.
   - Add `build_ledger` to `eamos_source_asset_preflight`.
   - Keep the existing narrower provider summaries in place for compatibility.

3. Enforce runtime asset policy.
   - Remove app-startup coordinate resolver downloads.
   - Fail closed if the legacy startup materialization flag is enabled.
   - Update deployment guidance to seed/materialize by explicit off-peak
     process only.

4. Harden the batch.
   - Add tests for required ledger rows and sanitization.
   - Add tests for preflight ledger output.
   - Add a startup policy test.

5. Compact coordinate index runtime pass.
   - Add the read-only compact index reader and fixture artifact.
   - Build runtime resolver instances from the compact index path with raw GFF
     paths disabled.
   - Wire lookup/search/report, Gene View, local evidence, and batch through
     the shared compact-index contract where those backend boundaries already
     exist.
   - Add explicit sanitized provider-cache and preflight readiness probes for
     the compact index.

6. Verify.
   - Run targeted backend pytest for health, preflight, runtime predictors,
     clinical source tables, literature, and startup policy.
   - Run lint/format checks where available.
   - Run `git diff --check`.

7. Continue materialization from the current execution checklist.
   - Use `docs/backend-build-ledger-runtime/materialization-plan.md` for the
     compact coordinate index and local-adapter runtime sequence.
   - Keep that checklist aligned with live SG health and Supabase inventory
     before provider flips.

## Agile Materialization Backlog

Use this section as the session-to-session pointer for remaining build-ledger
materialization work. Before starting any item, re-run the read-only baseline
checks because live SG, Supabase metadata, and local staging can move
independently:

```powershell
cd app/backend
python -m app.cli.eamos_source_asset_preflight --compact
python -m app.cli.eamos_clingen_local_preflight --compact
```

Also compare live SG provider-cache before any runtime decision. Do not flip
providers, env vars, or startup materialization from this backlog unless the
task explicitly reaches that acceptance gate.

### M0 - Ledger Baseline

Goal: capture the true current state from local preflight and live SG
provider-cache.

Acceptance criteria:

- Current ledger rows are grouped as ready, available, source-ready, disabled,
  missing, or gated.
- Local-ready versus live-ready differences are called out explicitly.
- No Storage, Supabase, Render, or env mutation is performed.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_source_asset_preflight --compact
```

Out of scope: downloads, uploads, Render disk writes, provider flips.

### M1 - ClinGen/CSpec Generated SQLite Sync

Goal: move the already-built ClinGen eRepo/CSpec local SQLite artifact through
the generated-artifact lane, or prove that live SG already points at the same
ready artifact.

Context: local `eamos_clingen_local_preflight --compact` reports a ready
ClinGen eRepo/CSpec full snapshot (`eamos.clingen_local.v1`) with eRepo
classification rows and CSpec entities. This is distinct from the smaller
ClinGen gene-validity table import.

Relevant references:

- `docs/clingen-local-materialization/plan.md`
- `app/backend/app/services/clingen_local.py`
- `app/backend/app/services/generated_source_artifacts.py`
- `app/backend/app/cli/eamos_generated_artifact_upload.py`
- `app/backend/app/cli/eamos_generated_artifact_sync.py`

Acceptance criteria:

- The `clingen_local` generated artifact has a private Storage identity and
  checksum manifest, or live SG provider-cache proves the same runtime artifact
  is already ready.
- Runtime/preflight output remains sanitized: no local paths, object URIs,
  raw rows, or secrets.
- `build_ledger.items.clingen_local_adapter.status` is `ready` on the target
  runtime before relying on local-first ClinGen behavior.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_clingen_local_preflight --compact --require-ready
python -m app.cli.eamos_generated_artifact_upload --artifact clingen_local --compact
```

Out of scope: PubMed local, literature RAG, CSpec UI rendering.

### M2 - Existing-Object Metadata Reconciliation

Goal: reconcile durable metadata for private Storage objects that already
exist, starting with dbSNP and phyloP.

Context: prior inventory found dbSNP and phyloP objects in private Storage, but
ledger rows still report `source_ready_for_materialization` because metadata
and runtime materialization rows are incomplete.

Acceptance criteria:

- `source_asset_objects` records exist for dbSNP and phyloP with role, size,
  checksum, license/provenance, and non-public access policy.
- Preflight no longer reports these sources as metadata-unknown.
- No Render disk seeding or local-evidence enablement happens in this task.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_source_asset_preflight --compact
```

Out of scope: ClinVar/RepeatMasker upload, runtime file placement.

### M3 - Small Clinical Table Imports

Goal: import release-pinned MONDO, HPO, ClinGen gene-validity, and GenCC tables
into private Supabase/Postgres.

Context: this is the `clinical_source_tables` ledger row, not the ClinGen
eRepo/CSpec SQLite artifact from M1.

Acceptance criteria:

- Fixture-scale clinical table data is replaced or augmented by release-pinned
  imports.
- Source versions and import timestamps are recorded.
- Existing public report/lookup contracts remain unchanged.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clinical_source_tables.py tests/test_health_api.py -q
python -m app.cli.eamos_source_asset_preflight --compact
```

Out of scope: local-evidence gate, PubMed/RAG.

### M4 - Local Evidence Runtime Probes

Goal: ensure dbSNP, ClinVar, RepeatMasker, and phyloP production runtime paths
are configurable and visible through sanitized health/preflight probes.

Acceptance criteria:

- Settings exist for each production runtime path/index path.
- Provider-cache or source preflight reports file readiness without leaking
  paths, object URIs, checksums that should stay private, or secrets.
- Tests prove fixture defaults are not mistaken for production configuration.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_source_asset_preflight_cli.py tests/test_health_api.py -q
```

Out of scope: Render seeding and `LOCAL_EVIDENCE_ENABLED=true`.

### M5 - phyloP Runtime Seed

Goal: place the verified phyloP bigWig on the SG Render service disk.

Acceptance criteria:

- File is copied/downloaded through a temp path, size/checksum verified, and
  atomically renamed into the configured runtime path.
- Provider-cache reports phyloP ready for lookup/report use.
- No startup download path is introduced.

Verify: live SG provider-cache plus a targeted lookup/report conservation smoke.

Out of scope: local-evidence gate flip.

### M6 - ClinVar Runtime Seed

Goal: locate or upload ClinVar GRCh38 VCF plus `.tbi`, register metadata, and
seed the indexed runtime files.

Acceptance criteria:

- ClinVar local adapter reports ready from production runtime files.
- ACMG/local evidence paths can read ClinVar without live bulk downloads.
- Health/preflight output remains sanitized.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clinvar_vcv.py tests/test_health_api.py -q
```

### M7 - RepeatMasker Runtime Index

Goal: materialize the official RepeatMasker source into the compact runtime
interval index expected by the local adapter.

Acceptance criteria:

- Runtime uses the compact interval index, not raw source scans.
- RepeatMasker provider/preflight status is ready.
- Query tests cover bounded interval lookup.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_repeatmasker_local.py tests/test_source_asset_preflight_cli.py -q
```

### M8 - dbSNP Runtime Seed

Goal: seed the dbSNP bgzip VCF plus `.tbi` from private Storage onto SG Render
disk.

Context: this is operationally larger than phyloP/ClinVar/RepeatMasker because
the object set is about 29.6 GB.

Acceptance criteria:

- dbSNP local adapter reports ready from production runtime files.
- Allele identity lookup works from local indexed files.
- Runtime memory remains bounded during probe/query.

Verify: provider-cache plus targeted dbSNP/local-evidence tests.

### M9 - Local Evidence Gate

Goal: enable local evidence only after hg38, compact index, dbSNP, ClinVar,
RepeatMasker, and phyloP are production-path verified.

Acceptance criteria:

- `LOCAL_EVIDENCE_ENABLED=true` is paired with narrow
  `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW`, initially `lookup,gene_viewer`.
- `LOCAL_EVIDENCE_REQUIRE_REAL_APIS=true` remains set.
- Lookup and Gene View smokes prove local evidence is active without broad
  fallback regressions.

Out of scope: search/workbench expansion until separate contract tests cover
those surfaces.

### M10 - MaveDB CC0 Import

Goal: materialize CC0 functional evidence after public-field review.

Acceptance criteria:

- MaveDB evidence is available to lookup/report surfaces.
- Public serialization policy is reviewed and enforced.
- No private/raw fields leak into public report payloads.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_functional_evidence.py -q
```

### M11 - ESM1b MIT-Regenerated Scores

Goal: materialize the MIT-regenerated ESM1b hg38 bgzip/tabix artifact.

Blocker: operator must provide
`C:\EamosDataStaging\esm1b\esm1b-mit-regenerated-scores.csv` with `seq_id`
values matching the staged MANE protein FASTA IDs.

Acceptance criteria:

- Runtime artifact and `.tbi` are generated from MIT-regenerated scores, not
  the non-commercial Hugging Face precomputed zip.
- Manifest records source, checksums, MANE/reference provenance, and
  `launch_gate: null` only for the clean regenerated path.
- Provider-cache/build-ledger report ESM1b ready after explicit runtime sync.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact esm1b_hg38_scores --compact
python -m pytest tests/test_esm1b_assembly.py tests/test_predictor_runtime.py -q
```

### M12 - CI-SpliceAI Runtime Artifact Set

Goal: materialize the complete CI-SpliceAI model/reference/score-cache set.

Acceptance criteria:

- Model, reference bundle, score cache, and score-cache index are all present.
- Partial artifact-set uploads remain blocked.
- Launch-gate/provenance metadata is preserved for commercialization filtering.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact ci_spliceai --compact
python -m pytest tests/test_predictor_runtime.py -q
```

### M13 - CAPICE Runtime Artifact Set

Goal: materialize the complete CAPICE model and SpliceAI-derived feature cache.

Acceptance criteria:

- Model, feature cache, and feature-cache index are all present.
- Partial artifact-set uploads remain blocked.
- CAPICE scorer is connected only once artifacts pass preflight.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact capice --compact
python -m pytest tests/test_predictor_runtime.py -q
```

### M14 - PubMed Local And Literature RAG

Goal: materialize PubMed local first, then literature RAG embeddings.

Status: deferred until Steven explicitly approves corpus logistics, storage
scope, staging, and cost.

Acceptance criteria:

- PubMed local SQLite is materialized from approved source packages and passes
  preflight.
- Literature embeddings are built offline from license-permitted rows, uploaded
  to private Storage, synced to Render disk, and never built/downloaded at
  startup.
- Chat/report retrieval uses the materialized store only after preflight is
  ready.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_local_preflight --compact --require-ready
python -m app.cli.eamos_literature_embed_preflight --compact --require-ready
python -m pytest tests/test_pubmed_local.py tests/test_literature_retrieval.py -q
```

Out of scope until approval: full PubMed/RAG corpus build, embeddings spend,
provider/env flips.
