# Backend Build Ledger Runtime Design

## Status

Draft.

## Summary

The backend build ledger is now wired into SG health and preflight, but the live
runtime is only partially through the ledger. The core policy controls are
working: startup downloads are disabled and raw GFF runtime scans are disabled.
Predictor lanes are backend/admin-wired first; commercialization and launch
filtering are metadata decisions after the data path exists. The stalled work is
operational materialization: the compact coordinate index, local indexed
adapters, predictor model/score artifacts, and Pfam/HMMER runtime assets need
explicit off-startup seeding and verification.

The recommended direction is to keep the existing health ledger contract, add a
narrow explicit materialization lane for the compact coordinate index, and treat
Render persistent disk seeding as a runtime-shell or service-process operation.
Render API one-off jobs cannot write the web service persistent disk, so they
must not be used as the disk seeding mechanism.

## Context and Scope

This design refreshes the backend-owned runtime plan against:

- The external synthesis at
  `C:\Users\seamegdool\Desktop\Claude code and website tips\EAMOS Web Tool\Wiki\syntheses\build-ledger.md`.
- Live SG provider-cache health for `eamos-dev-sg` on 2026-06-06.
- Current backend code under `app/backend`.
- Render persistent disk behavior for service `srv-d8ctvoh9rddc73a27nb0`.

This document covers backend runtime readiness, materialization sequencing, and
operator verification. It does not change frontend contracts or config docs.

## Current Progress

Live SG is healthy, but the ledger is mixed:

| Lane | Live status | Interpretation |
| --- | --- | --- |
| `hg38_2bit` | `ready` | Foundation reference cache is seeded and runtime-wired. |
| `coordinate_compact_index` | `missing` | Runtime reader is wired, but the immutable compact index artifact is absent from disk. |
| `gene_view` | `runtime_partial` | Blocked by compact coordinate index and protein runtime readiness. |
| `protein_pfam` | `disabled` | Pfam/HMMER CLI exists, but SG runtime is not enabled/prepared. |
| dbSNP/ClinVar/RepeatMasker/phyloP adapters | `source_ready_for_materialization` | Sources are approved, but runtime indexed artifacts are not seeded as a horizontal batch. |
| `local_evidence_orchestrator` | `disabled` | Correctly gated until indexed assets are seeded and verified. |
| `alphamissense` | `missing_source_file` | Runtime probe and report serialization are wired; asset materialization is missing. |
| `esm1b` | `missing_source_file` | Runtime probe and report serialization are wired; launch-gate metadata remains attached. |
| `ci_spliceai` | `score_cache_missing` | Runtime lane is backend/admin-wired; model/reference/score cache materialization is missing. |
| `capice` | `model_artifact_missing` | Runtime scaffold is backend/admin-wired; model and feature-cache materialization are missing. |
| `nmdetective_pvs1` | `pure_code_available` | Pure-code decision support is available. |
| `clinical_source_tables` | `import_ready` | Ready for explicit Supabase Postgres import. |
| `literature_engine` | `live_fetch_built_bulk_edges_pending` | Live fetch works; bulk edges/vector work remain pending. |
| `ai_gateway` | `gateway_planned` | Not wired yet. |

The main stall is not a failed deploy or policy confusion. It is that the
ledger now exposes several artifacts whose approved runtime seeding process is
not yet complete.

## Goals

- Keep `/api/v1/health/provider-cache` and source-asset preflight as the
  backend source of truth for build-ledger readiness.
- Seed runtime assets only through explicit off-startup processes.
- Make the compact coordinate index ready on SG without re-enabling startup
  materialization.
- Preserve predictor provenance and launch-gate metadata, but do not use it to
  block backend/admin predictor integration.
- Keep health, preflight, and CLI output sanitized: no secrets, private object
  URIs, signed URLs, or local filesystem paths.
- Give future agents a clear sequence for unsticking stalled ledger rows.

## Non-Goals

- No frontend, schema mirror, Claude, or config-doc changes.
- No GPN-MSA, MaveDB, literature bulk, or AI gateway implementation in this
  pass.
- No startup download path for coordinate assets or protein assets.
- No use of Render one-off jobs to mutate the service persistent disk.

## Constraints

- SG uses Render service `srv-d8ctvoh9rddc73a27nb0` with persistent disk mounted
  at `/var/data/eamos`.
- Render persistent disks are available to the live service runtime only. They
  are not available during build, pre-deploy, one-off jobs, or another service.
- The app intentionally fails startup when
  `COORDINATE_RESOLVER_ASSET_MATERIALIZATION_ENABLED=true`.
- Docker runtime and service env can be used, but secrets must not be printed.
- Existing unrelated frontend/doc dirtiness must remain untouched.

## Proposed Design

### 1. Treat The Ledger As A Readiness Board

The build ledger should keep representing each lane as one of three states:

- `ready`: runtime artifact, table, or code path is present and verified.
- `source_ready_for_materialization` or equivalent: approvals/source readiness
  are complete, but runtime materialization remains.
- `planned`, `disabled`, `blocked`, or `missing`: the lane is intentionally not
  ready yet.

This prevents "wired" from being confused with "operationally ready". For
example, compact coordinate index and local adapters can be `runtime_wired=true`
while still reporting missing or unseeded artifacts.

### 2. Add A Narrow Compact-Index Materialization Path

The current coordinate materializer downloads raw coordinate inputs and hg38
runtime files, not the immutable compact coordinate index. The compact index
needs its own explicit backend materialization flow modeled after the Pfam
runtime materializer:

- Input: a private Supabase Storage object URI or an operator-provided local
  artifact path.
- Output: `eamos-coordinate-index.latest.jsonl.gz` at
  `COORDINATE_RESOLVER_COMPACT_INDEX_PATH`.
- Verification: size and SHA256/MD5 when manifest data is available, plus
  `CompactCoordinateIndex.inspection(verify_checksum=True)` for schema and
  record validation.
- Write behavior: download/copy to a temp file in the destination directory,
  verify, then atomically replace the final artifact.
- Output: sanitized JSON with readiness, status, counts, checksum verification
  flags, and no path or object URI values.

The flow must be run explicitly during an off-peak window. It must not be
called by `create_app`.

### 3. Use Runtime Shell Or Service Process For SG Disk Seeding

Because Render one-off jobs cannot access the service persistent disk, SG disk
seeding has two valid operational paths:

- Render Shell/SSH/SCP into the live service instance, followed by checksum
  verification and atomic rename on `/var/data/eamos`.
- A committed backend CLI executed from the live service shell, using the
  service environment and writing to the mounted disk.

The committed CLI is preferable for repeatability, but the first compact-index
seed can also be done with SCP if the verified artifact already exists outside
Render.

### 4. Sequence Ledger Recovery Horizontally

After compact index readiness, the remaining ledger work should proceed in
small horizontal batches:

1. Compact coordinate index: unblock lookup/search/report/Gene View/batch
   coordinate resolution and remove one Gene View blocker.
2. Pfam/HMMER runtime: materialize Pfam, run `hmmpress`, and enable protein
   annotation only after health reports available.
3. Local indexed adapter batch: dbSNP, ClinVar, RepeatMasker, and phyloP should
   be seeded as a grouped runtime batch before enabling local evidence flows.
4. Clinical source table import: import MONDO/HPO/ClinGen/GenCC into Supabase
   Postgres through an explicit migration/import path.
5. Predictor lanes: keep AlphaMissense, ESM1b, CI-SpliceAI, and CAPICE
   backend/admin-wired, but report missing runtime artifacts until their local
   files, models, score caches, and manifests are materialized.

## Architecture View

```text
Private durable sources
  Supabase Storage / Supabase Postgres / approved remote metadata
        |
        | explicit operator CLI or import, never app startup
        v
Render runtime cache or Postgres tables
  /var/data/eamos/... or Supabase relational/vector tables
        |
        | read-only runtime probes
        v
Provider-cache health + source-asset preflight
        |
        v
Ledger rows: ready, missing, disabled, blocked, source-ready
```

## Interfaces and Data

The existing public health shape should remain stable:

- `/healthz` reports service and database health.
- `/api/v1/health/provider-cache` reports `source_assets`, `providers`, and
  `build_ledger`.
- `source_assets.compact_coordinate_index.ready` is the direct acceptance
  signal for compact-index seeding.
- `build_ledger.items[item_id=coordinate_compact_index].status` mirrors the
  compact index probe.

Any new materialization CLI should follow existing CLI guardrails:

- `--compact`
- `--require-ready`
- `--force-download` or equivalent
- explicit source-object/local-artifact arguments
- sanitized JSON output
- exit non-zero when `--require-ready` is set and readiness fails

## Alternatives Considered

### Re-enable startup materialization

Rejected. It caused a failed SG deploy and violates the ledger rule that app
startup must not pull private assets or scan raw GFF inputs.

### Render API one-off job

Rejected. Render one-off jobs inherit image and environment but cannot access
the base service persistent disk. This would not seed `/var/data/eamos`.

### Build or pre-deploy command

Rejected. Render persistent disk is unavailable in build and pre-deploy phases,
and the ledger explicitly forbids startup/build-time downloads.

### Copy raw GFFs and scan at runtime

Rejected. Raw GFF runtime scans are disabled by policy and would make Gene View
and coordinate resolution slow, fragile, and hard to audit.

### Commit the compact index into the repo

Not recommended unless the artifact is tiny and policy-reviewed. The ledger
expects private durable storage plus a Render disk runtime cache for immutable
coordinate artifacts.

## Tradeoffs

The proposed design is slower operationally than a startup downloader, because
an operator must run a CLI or SSH/SCP process. That is the right tradeoff: it
keeps deploys deterministic, avoids surprise private asset downloads, and keeps
disk writes in an auditable off-peak process.

The design also separates "runtime wired" from "ready". That can look stalled,
but it is more accurate than reporting readiness before artifacts exist.

## Cross-Cutting Concerns

- Security: service-role keys are read only by backend processes and never
  emitted in output.
- Privacy: health and preflight continue to avoid user variant identities.
- Reliability: temp-file writes and atomic rename avoid partial artifact reads.
- Observability: readiness is visible through provider-cache and preflight.
- Cost: compact-index seeding does not change the major cost driver; RAM tier
  remains the larger future decision.
- Operations: SG has one disk-backed instance, so seeding and restarts should
  happen off-peak.

## Rollout and Migration

1. Confirm whether a verified compact index artifact already exists outside SG.
2. If it exists, seed `/var/data/eamos/bio_assets/transcripts` through Render
   Shell/SSH/SCP or a live-shell CLI, using a temp file plus atomic rename.
3. If it does not exist, build or obtain the compact index offline, upload it
   to private Storage with manifest identity, then materialize it on SG.
4. Verify:
   - `/healthz` returns OK.
   - `/api/v1/health/provider-cache` reports
     `source_assets.compact_coordinate_index.ready=true`.
   - `build_ledger.items.coordinate_compact_index.status=ready`.
   - AlphaMissense and ESM1b report backend serialization enabled, while ESM1b
     still carries launch-gate metadata.
5. Only after compact-index readiness, proceed to Pfam/HMMER and local indexed
   adapter batches.

Backout is straightforward: rename or remove the compact artifact and restart
or let health reflect `missing`. Do not change startup materialization flags.

## Open Questions

- Where is the production compact coordinate index artifact currently stored,
  if it exists?
- Is the compact index already uploaded to private Supabase Storage with a
  checksum manifest, or does it still need an offline build/upload step?
- Should the compact-index materializer accept local SCP-provided files, private
  Storage objects, or both?
- Which operator path is preferred for SG: Render Dashboard Shell, direct SSH,
  or a backend CLI invoked from the live shell?

## Decision

Proceed with the explicit off-startup materialization design. The first
implementation spec should target the compact coordinate index only, because it
is the smallest high-leverage blocker and does not broaden predictor behavior.
Spec and plan updates should follow after this design is reviewed.
