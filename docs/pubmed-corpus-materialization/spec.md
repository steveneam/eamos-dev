# PubMed Corpus Materialization Spec

## What

Build a reviewed plan for a real PubMed-local corpus, including storage sizing, cost exposure, staging logistics, upload gates, and operational sequencing. This replaces the accidental 200-PMID proof path with an explicit decision framework: a small cached artifact is not the PubMed repository. Until the corpus decision is approved, PubMed full materialization stays paused and Tier 2 predictor-cache work should be the next implementation lane.

## Context

Eamos already has the PubMed-local runtime and materialization scaffolding:

- `app/backend/app/cli/eamos_pubmed_corpus_budget.py` fetches official NCBI/PMC directory listings only and produces storage/cost scenarios.
- `app/backend/app/cli/eamos_pubmed_local_materialize.py` builds a local SQLite asset from operator-staged XML/JSONL/edge inputs. It does not download PubMed itself.
- `app/backend/app/services/pubmed_local.py` enforces seed filtering, source-file manifests, license-gated abstract persistence, checksum verification, and sanitized preflight output.
- `app/backend/app/cli/eamos_literature_embed_materialize.py` builds the RAG SQLite from PubMed-local, but only after PubMed-local exists.
- `docs/pubmed-local/plan.md` already records the earlier budget gate.
- `docs/backend-build-ledger-runtime/materialization-plan.md` currently lists Tier 1 generated SQLite artifacts as ClinGen local, PubMed local, and literature embeddings.

The correction from the 2026-06-17 session is important: a 200-PMID cache-derived SQLite was built locally from existing `app/backend/data/app.db` PubMed/LitVar cache rows. It is a proof artifact only. It is not complete enough to upload or register as production PubMed-local.

Fresh official-listing budget run on 2026-06-17:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_corpus_budget --fetch-official-listings --compact
```

Current listing sizes:

| Corpus | Compressed size | Files | Notes |
| --- | ---: | ---: | --- |
| PubMed 2026 baseline XML | 50.560 GiB | 1,334 | Baseline XML gzip only. |
| PubMed current updates | 7.694 GiB | 155 | Update XML gzip only. |
| PubMed baseline + updates | 58.254 GiB | 1,489 | Before md5 sidecars. |
| PubTator3 selector tables | 6.783 GiB | 4 | Gene/mutation/relation/bioconcept selector tables. |
| PubTator3 full BioC XML | 200.000 GiB | 10 | Not needed for selector-first import. |
| PMC OA XML baseline packages | 135.185 GiB | 39 | Commercial, non-commercial, other. |
| PMC OA text baseline packages | 104.018 GiB | 39 | Commercial, non-commercial, other. |
| PMC ID crosswalk | 0.230 GiB | 1 | PMCID/PMID/DOI crosswalk. |

Current budget assumptions from the CLI:

- Supabase Storage used: 38.0 GiB of 100.0 GiB.
- Supabase Storage headroom: 62.0 GiB.
- Supabase database used: 0.019 GiB of 8.0 GiB.
- Supabase database headroom: 7.981 GiB.

Pricing references used:

- Supabase Storage size: 100 GB included on Pro/Team, then `$0.0213/GB/month` over quota, per Supabase docs: `https://supabase.com/docs/guides/platform/manage-your-usage/storage-size`.
- Supabase database disk: 8 GB included, then `$0.125/GB` for gp3 disk, per Supabase compute/disk docs: `https://supabase.com/docs/guides/platform/compute-and-disk`.
- Supabase egress: Pro includes 250 GB egress, then `$0.09/GB`, per Supabase pricing: `https://supabase.com/pricing`.

## Requirements

1. The system must not upload, register, or enable a PubMed artifact unless its corpus scope is explicitly labeled: `proof`, `targeted_seed`, `filtered_pubmed`, or `raw_mirror`.
2. The 200-PMID cache-derived artifact must not be promoted to production PubMed-local.
3. Any full or filtered PubMed build must run offline/operator-side, never at request time, startup, deploy, Render one-off job, or Vercel build time.
4. PubMed raw FTP source downloads must stage on an explicit non-`C:` volume with enough room for compressed source, extracted/streamed temp files, derived SQLite outputs, manifests, and retry overlap.
5. Supabase Storage mutation requires Steven approval before upload. Supabase metadata registration rows require separate Steven approval.
6. PubMed-local must preserve the existing abstract license policy: persist abstract text only when the source metadata proves a permissive license; otherwise store metadata-only rows.
7. Literature embeddings must be built only from a verified PubMed-local SQLite, and must inherit metadata-only behavior for unlicensed articles.
8. Runtime flags remain unchanged until provider-cache/materialization verification is green: no `LOCAL_EVIDENCE_ENABLED`, no `PUBMED_LOCAL_ENABLED`, no `RAG_ENABLED`, no provider flip.
9. Source and generated-artifact reports must not emit local paths, raw abstracts, secrets, private object URIs, or signed URLs.

## Design

### Decision Flow

Use a four-stage gate:

1. **Budget gate:** run `eamos_pubmed_corpus_budget --fetch-official-listings --compact`; review current object sizes, Storage/database headroom, egress headroom, and version-overlap requirements.
2. **Corpus scope gate:** choose one corpus scope:
   - `targeted_seed`: small Eamos seed list only; useful for development and limited demos.
   - `filtered_pubmed`: download PubMed XML locally, filter to Eamos genes/variant terms, upload only derived SQLite and manifests.
   - `raw_mirror`: upload raw PubMed baseline/update XML to Supabase Storage.
   - `raw_plus_selectors`: raw PubMed plus PubTator selector tables for broader filtering.
3. **Offline materialization gate:** build/validate SQLite locally, preflight it, and compare resulting row counts and license profile against the chosen scope.
4. **Storage and metadata gate:** upload generated SQLite to private Storage; later register metadata rows and materialization rows only after approval.

### Recommended Path

Pause PubMed full materialization and proceed with Tier 2 predictor caches next.

If PubMed is resumed later, use `filtered_pubmed` first:

1. Download PubMed baseline/update XML to an operator staging volume, not the repo.
2. Stream parse XML and apply seed filters for the Eamos gene/variant cohort.
3. Do not keep extracted full XML on disk; process compressed XML by stream where possible.
4. Write `pubmed-local.sqlite`, `pubmed-local.manifest.json`, and a separate source-file manifest listing PubMed shard names, sizes, md5 sidecar status, source version, and seed-filter coverage.
5. Build `literature-embeddings.sqlite` from that SQLite only after PubMed-local preflight is green.
6. Upload generated SQLite artifacts only, not raw source, unless the raw-mirror gate is separately approved.

### Storage/Cost Scenarios

Approximate monthly overage estimates use current official pricing and the current 38.0 GiB Storage usage. They do not include human time, staging disk, failed retries, or dashboard/bucket cap changes.

| Scenario | Storage after upload | Immediate Storage overage | Version-overlap total | One reseed egress | Database high estimate | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| PubMed raw mirror | 96.254 GiB | $0/month; only 3.746 GiB headroom | 154.507 GiB, about $1.16/month over quota | 58.254 GiB | 0 GiB | Technically fits now, operationally unsafe without overlap room. |
| PubMed + PubTator selectors | 103.037 GiB | about $0.06/month | 168.073 GiB, about $1.45/month over quota | 65.037 GiB | 33.934 GiB DB total, about $3.24/month DB disk overage | Hold; Storage and DB estimates exceed included quotas. |
| PubMed + 5% PMC OA commercial XML placeholder | 101.365 GiB | about $0.03/month | 164.730 GiB, about $1.38/month over quota | 63.365 GiB | 2.519 GiB DB total | Hold; exact PMC package selection needed first. |
| Full PubMed + PubTator BioC + PMC XML/text | 535.687 GiB | about $9.28/month | 1033.375 GiB, about $19.88/month over quota | 497.687 GiB; about $22.29 egress over included 250 GB if downloaded once in a month | 300.019 GiB DB total, about $36.50/month DB disk overage | No-go without explicit capacity and operational approval. |

The dollar overage for object storage is not the only concern. The bigger operational issues are:

- no room for next PubMed baseline overlap under the current 100 GB included Storage quota;
- large one-time reseed egress from private Storage to Render/operator environments;
- long-running upload retries across 1,489+ objects;
- provenance and deletion/rollback policy for old PubMed baselines;
- local staging disk requirements;
- Render disk is only 60 GB and is already planned for dbSNP, phyloP, hg38, Pfam, generated SQLite, and predictor caches.

### Logistics

Required staging layout, outside the repo:

```text
D:\eamos-corpus\pubmed\
  listings\
  raw\
    baseline\
    updatefiles\
  manifests\
  derived\
    pubmed-local.sqlite
    pubmed-local.manifest.json
    literature-embeddings.sqlite
    literature-embeddings.manifest.json
  logs\
```

Minimum staging capacity:

- `targeted_seed`: less than 10 GiB, depending on fetched PMIDs and embeddings.
- `filtered_pubmed`: 120-180 GiB recommended. This covers 58.254 GiB compressed XML, temporary retry space, derived SQLite, manifests, logs, and safety margin.
- `raw_mirror`: 150-180 GiB recommended locally to support download verification and upload retry.
- `raw_plus_selectors`: 180-220 GiB recommended locally.
- full PubMed/PubTator/PMC mirror: at least 1 TiB local staging; not recommended.

Upload policy:

- Use private `eamos-source-assets` Storage only.
- Use existing S3 multipart tooling for large files.
- Upload generated SQLite artifacts under `generated/eamos_pubmed_local/...` and `generated/eamos_literature_embeddings/...`.
- Upload raw FTP mirrors only under a separate approved prefix such as `pubmed_raw/pubmed_2026_baseline_update/...`.
- Do not create public buckets, signed frontend URLs, or browser-readable raw-source paths.

Render-disk policy:

- No Render one-off job seeding.
- No startup download.
- Sync generated SQLite to `/var/data/eamos/...` only through a committed runtime sync CLI from the web service runtime or an approved shell/SCP process.
- Verify provider-cache after sync; file presence alone is not acceptance.

## Decisions

### D1: Pause PubMed full materialization now

Choice: Pause PubMed full materialization and proceed to Tier 2 next.

Alternatives:

- Promote the 200-PMID cache artifact: rejected because it is only a proof.
- Upload PubMed raw mirror now: rejected because current Storage headroom is too tight for version overlap and it needs explicit logistics approval.
- Build filtered PubMed now: rejected until staging disk, seed scope, and source retention are approved.

Why: The current task discovered that PubMed is a data logistics project, not a small generated artifact. A wrong upload would create misleading readiness signals.

Reversible: Yes. PubMed can resume from this spec once a corpus scope and staging volume are approved.

### D2: Prefer filtered generated artifacts over raw mirror

Choice: Default to `filtered_pubmed`: generated SQLite and manifests are durable artifacts; raw FTP mirror is optional and separately approved.

Alternatives:

- Raw mirror in Supabase for full reproducibility.
- Postgres table import.
- Full PMC/PubTator mirror.

Why: Eamos runtime needs local SQLite retrieval and RAG, not public raw-source browsing. Filtered generated artifacts reduce Storage, egress, and Render disk pressure.

Reversible: Mostly. A raw mirror can be added later without changing runtime contracts.

### D3: Preserve license-gated abstract handling

Choice: Keep metadata-only rows unless permissive license metadata is present.

Alternatives:

- Store all abstracts from PubMed XML.
- Store snippets only.
- Store embeddings from unlicensed abstracts but not text.

Why: Existing code explicitly gates abstract persistence. RAG must not widen the license surface by embedding or retrieving unlicensed text without review.

Reversible: Only after legal/source policy review.

### D4: Do not store PubMed in Supabase Postgres by default

Choice: Keep PubMed-local and RAG as SQLite artifacts on Render disk.

Alternatives:

- Import PubMed into Supabase Postgres tables.
- Store RAG vectors in pgvector.

Why: Current plan chose local SQLite for Tier 1. Postgres import increases database disk, query performance, RLS/API exposure, migration, and backup concerns.

Reversible: Yes, through a later pgvector/Postgres spec and migration review.

### D5: Tier 2 can proceed while PubMed is paused

Choice: Treat Tier 2 predictor caches as the next implementation lane after this spec review.

Alternatives:

- Block all materialization on PubMed.
- Start Tier 3 dbSNP/phyloP.

Why: Tier 2 has existing runtime scaffolds and health/preflight surfaces. PubMed now needs data-logistics approval, while Tier 2 can move product evidence forward without pretending PubMed is complete.

Reversible: Yes.

## Versions

- PubMed official listing URLs are read from NCBI FTP via `eamos_pubmed_corpus_budget.py`:
  - `https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/`
  - `https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/`
  - `https://ftp.ncbi.nlm.nih.gov/pub/lu/PubTator3/`
  - `https://ftp.ncbi.nlm.nih.gov/pub/pmc/`
- Supabase Storage size pricing source: `https://supabase.com/docs/guides/platform/manage-your-usage/storage-size`.
- Supabase database disk pricing source: `https://supabase.com/docs/guides/platform/compute-and-disk`.
- Supabase egress pricing source: `https://supabase.com/pricing`.
- Current corpus numbers must be regenerated before any approval because PubMed updatefiles change over time.

## Invariants

- `LLM_PROVIDER=mock` remains unchanged.
- `RAG_ENABLED=false` remains unchanged until literature embeddings are materialized and verified.
- `PUBMED_LOCAL_ENABLED=false` remains unchanged until the runtime SQLite exists on Render disk and provider-cache is green.
- `LOCAL_EVIDENCE_ENABLED=false` remains unchanged until the broader local-evidence batch is verified.
- `eamos_pubmed_local_materialize` must remain offline/operator-only and must not download source payloads internally.
- Generated artifact upload and sync must not mutate Supabase metadata rows unless separately approved.
- Provider-cache/preflight outputs must not expose local paths, abstracts, secrets, object URIs, signed URLs, or raw source snippets.

## Error Behavior

- If official listing fetch fails, the budget step fails closed and no upload can proceed.
- If staging disk free space is below the selected scope requirement, the build must not start.
- If any PubMed XML md5 sidecar mismatches, that shard is rejected and the previous generated artifact remains untouched.
- If materialization produces zero rows, the CLI returns not-ready and must not upload.
- If materialization produces only metadata-only rows, the artifact may be valid for publication counts/title retrieval but must be reported as no licensed abstract coverage for RAG.
- If embedding generation fails, keep PubMed-local intact and do not upload partial RAG SQLite.
- If upload fails mid-multipart, abort/ignore stale multipart IDs per existing Storage upload guardrails and retry explicitly.
- If Render disk sync checksum fails, leave the existing runtime file in place.

## Testing Strategy

Budget and planning:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_corpus_budget --fetch-official-listings --compact
```

Materialization proof:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_local_materialize `
  --from-xml-dir <staged-pubmed-xml-dir> `
  --query-file <approved-seed.tsv> `
  --output <staging>\pubmed-local.sqlite `
  --manifest <staging>\pubmed-local.manifest.json `
  --verify-md5-sidecars `
  --coverage-completeness partial `
  --compact `
  --require-ready
```

Preflight:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_local_preflight `
  --db-path <staging>\pubmed-local.sqlite `
  --manifest-path <staging>\pubmed-local.manifest.json `
  --compact `
  --require-ready
```

Focused regression tests:

```powershell
cd app/backend
python -m pytest tests/test_pubmed_corpus_budget.py tests/test_pubmed_local.py tests/test_pubmed_pubtator_edges.py tests/test_pubmed_litvar_edges.py tests/test_literature_retrieval.py tests/test_generated_source_artifacts.py -q
```

Upload planning only:

```powershell
cd app/backend
python -m app.cli.eamos_generated_artifact_upload --artifact pubmed_local --compact
python -m app.cli.eamos_generated_artifact_upload --artifact literature_embeddings --compact
```

Acceptance:

- Budget output says `ready_for_upload=false` until explicit approval.
- Materialization output reports the chosen corpus scope and row/license coverage truthfully.
- Preflight is green and sanitized.
- Upload plan sees the intended generated SQLite files and no proof artifacts.
- No runtime/provider flags are changed.

## Out of Scope

- Uploading PubMed raw FTP mirrors.
- Uploading the 200-PMID cache proof artifact.
- Supabase metadata registration rows.
- Render disk sync.
- Enabling PubMed-local or RAG in production.
- Moving literature embeddings to pgvector.
- Full PMC/PubTator raw mirroring.
- Tier 2 implementation details; Tier 2 should proceed under its own focused task/spec if Steven approves the pivot.
