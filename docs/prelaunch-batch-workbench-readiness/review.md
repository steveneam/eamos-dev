# Prelaunch Batch And Workbench Architecture Review

Status: draft for Steven review.
Created: 2026-06-28 by Codex.
Reviewed target: `docs/prelaunch-batch-workbench-readiness/design.md` plus current
Batch, Workbench, auth, rate-limit, and cache code on `main` at `e41008d`.

## Findings

### 1. Batch frontend mock fallback will hide real launch failures

Severity: high.

Evidence:

- `app/web/lib/batch.ts` catches all inline `createBatch` failures and returns a
  completed `mock-job-*` when `upload_ref` is absent.
- `app/backend/app/api/routes/batch.py` currently authenticates only
  `/api/v1/batch/uploads`; inline `POST /api/v1/batch` is public.
- Existing signed-in transports such as `app/web/lib/chat.ts` and
  `app/web/lib/library-sync.ts` fetch the Supabase session and attach
  `Authorization: Bearer <token>`.

Why it matters:

If inline Batch create is auth-gated or rate-limited before launch, the current
web fallback would turn 401/429/backend errors into a mock completed job for
small inline cohorts. That is the wrong user experience and the wrong safety
signal. The user would see a result surface, but it would not be backend-backed.

Recommendation:

- Add a shared Batch auth transport path matching chat/library sync.
- Stop using mock fallback for auth, validation, rate-limit, or backend errors.
- Keep an explicit offline/demo fallback only when the UI intentionally enters a
  preview mode and labels the output as preview.

### 2. Batch ownership is missing from the upload, create, and get lifecycle

Severity: high if Batch is launch-gated by login.

Evidence:

- `StoredUpload` and `StoredBatchJob` in `app/backend/app/services/batch.py`
  do not carry `user_id` or principal metadata.
- `/api/v1/batch/uploads` authenticates and rate-limits by principal, but the
  returned `upload_ref` is not bound to that principal inside `BatchService`.
- `/api/v1/batch/{job_id}` is public and returns any job by ID.

Why it matters:

Random IDs reduce accidental access, but they are not an ownership model. If
Batch becomes a signed-in feature, create and get should be scoped to the same
principal. This is also the foundation for future persisted job history.

Recommendation:

- Add owner-aware in-memory records first: `user_id`, `provider`, created time,
  and expiry.
- Require auth on create and get.
- Enforce upload_ref owner match during create.
- Enforce job owner match during get.
- Add a distinct Batch job rate-limit scope rather than reusing upload-only
  limits.

### 3. Batch persistence should reuse the existing SQLAlchemy app-db pattern

Severity: medium. Launch impact depends on whether reloadable history is
required.

Evidence:

- `app/backend/app/core/db.py` already defines SQLAlchemy records and
  `build_session_factory`, `initialize_database`, and `session_scope`.
- Cache repos use small repository classes around this session factory.
- `BatchService` currently stores uploads/jobs in process memory and writes
  upload snapshots to local disk.

Why it matters:

If the product needs reloadable Batch history, using the existing app-db pattern
is more consistent than introducing Supabase tables, queues, object storage, or
DuckDB for launch. Supabase/Postgres can be considered later if cross-device
Batch history becomes a product requirement.

Recommendation:

Keep in-memory Batch for the smallest launch pass unless Steven requires job
history. If persistence is required, add an optional local SQL repository behind
`BatchService`:

- `batch_jobs`
- `batch_job_results`
- `batch_uploads` metadata

Do not store raw VCF bytes in the SQL app DB. Store bounded parsed metadata,
sanitized warnings, and result payloads.

### 4. Workbench source/fallback disclosure is fragmented across tools

Severity: medium.

Evidence:

- CRISPR outcomes use `source_backed`, `analysis_kind`, and
  `provider_label`.
- ssODN uses `template_source` and warning codes such as mock genomic window.
- Primer exposes placement/thermo/specificity notes.
- Viewer uses scaffold and per-track warnings.
- `app/web/lib/workbench/crispr-disclosure.ts` implements a CRISPR-specific
  disclosure model, but there is no shared Workbench source-status taxonomy.

Why it matters:

Workbench can launch as mixed source-backed/fallback, but only if users can
reliably understand what is source-backed, local, fallback, gated, or
unavailable. Fragmented labels make that harder to maintain and test.

Recommendation:

Add an additive shared disclosure contract rather than rewriting every schema:

```text
source_status: source_backed | local_provider | fallback | fixture | gated | unavailable
provider_id
provider_label
source_version
cache_status
warnings
requirements
```

Expose it as a helper/model first, then thread it through Workbench responses as
optional metadata. Frontend tools can consume this through one
`workbench-source-disclosure` helper.

### 5. Panel catalog is the right intermediate artifact if source-backed panels
are needed

Severity: medium.

Evidence:

- `app/backend/app/services/panels.py` is a hard-coded local launch catalog with
  explicit warnings that PanelApp/ClinGen/GenCC materialized sources are
  pending.
- Batch already benefits from panel symbol and interval filtering.

Why it matters:

Panel UX is core to Batch. A better panel framework would improve both building
and user experience, but building it from live APIs at request time would violate
the local-asset policy.

Recommendation:

Launch can use warning-labeled panels if acceptable. If not, build a generated
local SQLite panel artifact with:

- `panel_release`
- `panel`
- `panel_gene`
- `panel_disease_map`
- `panel_gene_source_evidence`
- `panel_alias`

This should be an offline/operator materialization with manifest/checksum
preflight, not a request-time API dependency.

### 6. PubMed and DuckDB conclusions are sound

Severity: no issue.

Evidence:

- PubMed-local spec explicitly says the 200-PMID artifact is proof-only and
  recommends pausing full materialization.
- DuckDB/Parquet plan says Phase 0/1 are implemented locally and no request
  route depends on DuckDB.

Why it matters:

The current design avoids overextending launch into large data-platform work.

Recommendation:

Keep PubMed API/cache and DuckDB disabled for launch. Document this in the
release evidence so the UI does not imply PubMed-local, RAG, or analytical
serving are active.

## Architecture Optimizations

### Batch: owner-aware launch mode before persistence

The first optimization is not a database. It is a consistent ownership and
transport layer:

```text
Supabase/browser session
  -> Authorization bearer token
  -> require_authenticated_principal
  -> owner-aware upload_ref/job_id
  -> explicit error UI, no silent mock
```

This gives launch-grade safety without creating a new persistence burden.

### Batch: optional SQL persistence behind a repository

If reload/history is required, add:

```text
BatchService
  -> BatchJobRepo
  -> app DB SQLAlchemy session factory
```

Suggested tables:

```text
batch_jobs
  job_id text primary key
  user_id text not null index
  provider text not null
  source_kind text not null             -- inline | upload
  source_label text null
  status text not null index
  filters_json json not null
  n_input integer not null
  n_to_lookup integer not null
  n_after_filters integer null
  done integer not null
  total integer not null
  est_seconds real not null
  warnings_json json not null
  error_json json null
  created_at timestamptz not null index
  updated_at timestamptz not null index
  expires_at timestamptz not null index

batch_job_results
  result_id integer primary key
  job_id text not null references batch_jobs(job_id) on delete cascade
  ordinal integer not null
  variant_key text not null
  state text not null index
  gene text null index
  hgvs_c text null
  classification_rank integer null index
  payload_json json not null
  warnings_json json not null
  created_at timestamptz not null
  unique(job_id, ordinal)

batch_uploads
  upload_ref text primary key
  user_id text not null index
  provider text not null
  filename text null
  variant_count integer not null
  warnings_json json not null
  skipped_rows integer not null
  snapshot_path text null               -- local private path, never returned
  created_at timestamptz not null index
  expires_at timestamptz not null index
```

Use this only if in-memory TTL is not enough for launch. Supabase migrations are
not required for this local-first option.

### Workbench: shared source disclosure framework

Current tool-specific metadata is useful but inconsistent. The optimization is
a shared backend and frontend source-status vocabulary:

```text
source_backed
local_provider
fallback
fixture
gated
unavailable
```

The UX can then render consistent chips:

- Source-backed
- Local provider
- Preview fallback
- Fixture
- Gated
- Unavailable

This is more important than making every provider fully source-backed before
launch.

### Panels: generated panel catalog artifact

If Steven wants source-backed panels before launch, use an intermediate
generated SQLite artifact rather than Supabase or request-time APIs:

```text
PanelApp/ClinGen/GenCC/MONDO source files
  -> offline materializer
  -> panel-catalog.sqlite + manifest
  -> provider-cache readiness
  -> PanelService source-backed adapter
```

This matches the ClinVar generated-artifact model and keeps the UX fast.

## Decision Recommendations

1. Require signed-in Batch for launch and remove silent Batch mock fallback.
2. Add owner-aware in-memory Batch records now.
3. Defer Batch SQL persistence unless reloadable job history is a launch
   requirement.
4. Launch panels can remain warning-labeled local launch panels unless Steven
   wants source-backed panels as a launch blocker.
5. Add a shared Workbench source disclosure framework before broad browser QA.
6. Keep PubMed API/cache and DuckDB disabled for launch.
