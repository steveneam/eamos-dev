# Backend Evidence Roadmap Design

Status: Draft
Owner: Codex/backend
Last updated: 2026-06-03 23:55 +1000 - Codex

## Summary

Eamos needs a backend evidence roadmap that keeps local-first source assets,
predictor lanes, ACMG support engines, literature, and AI-provider plumbing in
the right order. The recommended direction is to keep source adapters local
first and fail closed, prepare AlphaMissense and pure-code ESM1b behind runtime
gates, build ACMG/PVS1 logic as deterministic advisory output, and defer
literature/AI-provider enablement until their storage, privacy, and licensing
paths are reviewed.

This design extends the existing local-source documents instead of replacing
them:

- `docs/local-first-data-source-strategy/design.md`
- `docs/local-first-data-source-strategy/spec.md`
- `docs/local-first-data-source-strategy/plan.md`
- `docs/local-first-data-source-strategy/source-asset-rollout.md`

## Context And Scope

Current backend work already includes:

- runtime source registry and field policy;
- local source reader proofs for VCF/tabix, bigWig, RepeatMasker text indexes,
  transcript fixtures, ClinVar fixtures, dbSNP fixtures, and orchestration
  scaffolding;
- source-registry/runtime-path metadata;
- `hg38.2bit` materialization metadata checks;
- generic tabix TSV predictor reader;
- Bergquist calibration for AlphaMissense and ESM1b;
- ESM1b codon-to-genomic SNV primitives with tests.

This design covers the next coordinated backend tracks:

1. Local-first adapter plan/spec bundle.
2. Disk-gated local adapter wiring.
3. ACMG points engine.
4. PVS1/NMD engine.
5. Literature engine.
6. AI gateway.
7. Predictor lanes.

It does not authorize Render, Vercel, Supabase, Oregon, production imports,
runtime display changes, or external-provider activation. Supabase uploads may
be used later only when explicitly needed, and the current bucket/file size
limit must be checked before any upload.

## Goals

- Keep runtime source adapters deterministic, local-first, and fail-closed when
  asset metadata, checksums, licensing, or materialization are incomplete.
- Wire local adapters only after the runtime disk shape is verified as Standard
  2 GB memory plus 60 GB disk at `/var/data`.
- Ensure there are no startup downloads. Runtime reads must use pre-seeded,
  checksum-verified local paths or mounted/cache paths.
- Make AlphaMissense materialization and runtime reading ready behind gates
  without enabling display unless explicitly approved.
- Build ESM1b assembly as pure code and keep public use blocked while score
  terms or regenerated-score provenance are unresolved.
- Add deterministic ACMG and PVS1/NMD support engines that are advisory and
  separate from ClinGen/ClinVar primary verdicts.
- Keep literature and AI gateway work schema/API/provider-abstracted first, with
  no PHI logging, no client keys, and no AI-generated verdict decisions.

## Non-Goals

- Changing Render or Vercel configuration.
- Touching Oregon resources or environments.
- Creating, mutating, or deploying Supabase resources in this design pass.
- Downloading, uploading, importing, or seeding production source assets.
- Enabling AlphaMissense display, ESM1b public serialization, SpliceAI in the
  main API path, MaveDB imports, or CAPICE.
- Making Eamos issue final clinical classifications.

## Constraints

- Existing unrelated handoff, frontend, and plan changes must be preserved.
- Supabase operations need an execution-specific approval and a current
  bucket/file size-limit check before upload.
- Render/Vercel mutations remain explicit-approval only.
- Disk-gated wiring waits for a verified 60 GB `/var/data` persistent disk.
- No startup downloads are allowed.
- Literature storage must avoid storing full abstracts or copyrighted text
  unless the license path is clear; prefer metadata, offsets, short snippets,
  and link-out.
- AI providers must be accessed only server side, through a broker with no
  client-side keys and no PHI logging.

## Proposed Design

### Track 1: Local-First Adapter Root

Treat all local sources as runtime assets with the same root contract:

- registry row with license, terms, checksum, version, storage target, and
  approved fields;
- runtime path config that resolves to a local filesystem path;
- materialization metadata for object-storage or mounted-volume deployments;
- preflight/health status that is sanitized and non-throwing;
- fail-closed reader resolution before request-time evidence use;
- source fallback rules that preserve fixture mode and live-provider fallback
  only where explicitly configured.

Existing `hg38.2bit` materialization metadata is the template. Predictor assets
should reuse the same concepts instead of getting a separate ad hoc runtime
path system.

### Track 2: Disk-Gated Local Wiring

After Steven verifies Standard 2 GB memory and 60 GB disk at `/var/data`, seed
assets off-peak and verify bytes, checksums, manifests, and materialization
rows before any request-time wiring. The first runtime wiring candidates are:

- dbSNP;
- phyloP;
- `hg38.2bit`;
- ClinVar;
- RepeatMasker;
- transcript stores;
- `LocalEvidenceOrchestrator`.

No adapter should download during startup. If a runtime asset is absent or
metadata does not match, the local path must fail closed and the caller should
fall back only where the flow explicitly allows fallback.

### Track 3: ACMG Points Engine

Build a deterministic Tavtigian/SVI points core that converts observed evidence
into transparent advisory score output. It should produce evidence rows and
point totals, not override ClinGen or ClinVar assertions. It must keep raw
source assertions and deterministic evidence separate so downstream UI can show
why a point was or was not counted.

### Track 4: PVS1/NMD Engine

Build PVS1/NMD as conservative pure code. Missing critical-region data, missing
LoF mechanism data, conflicting transcript geometry, or unsupported variant
shapes should default to false or uncertain rather than inferring pathogenic
evidence. Do not use AutoPVS1 code or data.

### Track 5: Literature Engine

Start with schema/API/fixture ETL design. Store source metadata, identifiers,
search terms, offsets, bounded snippets, and links. Avoid storing copyrighted
full abstracts unless license review explicitly approves it. Supabase
migrations and fixture imports require execution-specific approval.

### Track 6: AI Gateway

Build a mocked/provider-abstracted broker first. The broker owns provider
selection, de-identification allowlists, server-side keys, timeout handling,
structured request/response logging, and redaction. It must not log PHI, must
not expose client keys, and must not make clinical verdict decisions.

### Track 7: Predictor Lanes

AlphaMissense:

- prepare materialization, tabix index preflight, checksum manifests, and a
  runtime adapter wrapper behind gates;
- runtime display still needs explicit approval;
- use Bergquist 2025 bands for PP3/BP4 activation, not AlphaMissense developer
  class labels.

ESM1b:

- build pure-code MANE assembly job scaffolding and manifests;
- keep public serialization blocked until score-file terms are confirmed or
  scores are regenerated from a commercial-safe source path.

CI-SpliceAI:

- isolate from the main API path.

MaveDB:

- gate per record on CC0 and require Supabase/import approval.

CAPICE:

- keep parked until Steven chooses Pro-only, retrain, or drop.

## Architecture Views

Runtime asset flow:

```text
registry row
  -> source/download/import approval
  -> staged file and manifest
  -> private object or mounted-volume metadata
  -> local cache path on runtime disk
  -> materialization metadata verified
  -> reader wrapper resolves path
  -> local adapter may serve request
```

Evidence flow:

```text
normalized variant
  -> local identity/reference/transcript context
  -> approved local stores
  -> source cache or live fallback if allowed
  -> predictor lanes behind license/materialization gates
  -> deterministic advisory engines
  -> report evidence with provenance and warnings
```

AI/literature flow:

```text
variant/gene metadata
  -> safe query terms and identifiers
  -> metadata/snippet/link storage
  -> optional brokered AI summarization from allowed inputs only
  -> grounded narrative without verdict authority
```

## Interfaces And Data

Core backend interfaces should remain small:

- runtime asset plan and inspection;
- source materialization record;
- tabix predictor reader wrapper;
- local evidence orchestrator inputs and outputs;
- ACMG points evidence item and point summary;
- PVS1/NMD decision object;
- literature search/index records;
- AI broker request and response records.

The public API should not grow until each backend interface is proven with
fixtures and contract tests. Predictor display remains a separate approval.

## Alternatives Considered

### Wire Runtime Adapters Before Disk Verification

This would produce fast local tests but risky hosted behavior. It loses because
Render runtime paths and disk capacity are hard gates for large static assets.

### Enable AlphaMissense Immediately After Reader Proof

This would be useful product output, but it would bypass the materialization,
display-approval, and provenance path. The safer path is adapter readiness
first, display later.

### Build AI And Literature First

These are valuable but have more privacy, copyright, and provider-risk surface
than deterministic local evidence. They should start with schemas and mocks
after the current local-source and predictor foundation is stable.

### Use AutoPVS1 Or Existing Classifier Code

This is faster but creates licensing and clinical-validation risk. Eamos should
implement a conservative, transparent subset itself.

## Tradeoffs

- Gating local runtime reads delays visible product wins but avoids silent
  partial evidence and startup failures.
- Keeping ACMG/PVS1 advisory limits automation but preserves clinical
  integrity and avoids competing with ClinGen/ClinVar source verdicts.
- Deferring real AI providers keeps privacy and cost under control but means
  early gateway work is mostly contracts, fixtures, and mocks.
- Preparing AlphaMissense without display creates a small amount of latent
  code, but it lets the infrastructure be tested before UI exposure.

## Cross-Cutting Concerns

Security and privacy:

- no client-side provider keys;
- no PHI logging;
- no frontend direct storage or private source SQL access;
- private Supabase resources stay backend-owned.

Licensing:

- fail closed when terms, checksums, source versions, or allowed fields are
  incomplete;
- keep ESM1b, CI-SpliceAI, MaveDB, and CAPICE gated as described above.

Reliability:

- no startup downloads;
- health/preflight probes are sanitized and non-throwing;
- request-time local reads fail closed and fall back only when the flow says so.

Operations:

- check runtime disk and Supabase bucket/file size limits before source upload
  or seeding;
- seed off-peak;
- verify byte counts, checksums, materialization metadata, and reader probes.

## Rollout And Migration

1. Review this roadmap bundle.
2. Implement AlphaMissense materialization/index preflight and runtime adapter
   wrapper, still disabled for display.
3. Add ESM1b MANE assembly job scaffolding with fixture manifests only.
4. Proceed with disk-gated local adapter wiring after `/var/data` capacity is
   verified.
5. Build ACMG points and PVS1/NMD pure-code engines.
6. Draft literature schema/API/fixture ETL, then request Supabase approval if
   migrations/imports are needed.
7. Build mocked AI gateway broker, then request secret/config approval for real
   providers.

## Open Questions

- What exact runtime environment name should materialization rows use for the
  future Render Standard service?
- Which Supabase bucket or object prefix should hold AlphaMissense if upload is
  needed, and what is the current file-size limit?
- Should AlphaMissense display be enabled for public/free reports once the
  runtime adapter is ready, or held for a later clinical-language review?
- Should CAPICE be Pro-only, retrained, or dropped?

## Decision

Adopt this roadmap as the coordination layer above the existing local-first
source docs. The next implementation slice is AlphaMissense preflight/runtime
adapter readiness, followed by ESM1b assembly scaffolding, with all runtime
display, Supabase mutation, deployment mutation, and disk-wiring steps gated by
their explicit approvals and preflights.
