# Database / Webserver Current State

Last updated: 2026-05-31 01:07 +1000 by Codex.
Cache-fix + Oregon→SG cutover verified: 2026-05-30 19:45 +1000 by Claude (see
Smoke Results / Render Services / Next Safe Steps below).

## Supabase Project

- Dev project: `eamos-dev`
- Project ref/id: `cpdjxsgasaesysvxkpmi`
- Region: `ap-southeast-2`
- Status at discovery: `ACTIVE_HEALTHY`
- Guardrail: Codex performed no Render deploy/env mutation. Live private-table
  DML for the Tier 3 fixture import and hg38 Storage metadata pilot was applied
  through the Supabase SQL connector only; no secrets were written to docs/env
  files or repeated in chat.

## Render Services

- Current target backend: `eamos-dev-sg`
  - Service id: `srv-d8ctvoh9rddc73a27nb0`
  - Region: Singapore
  - Plan: Starter
  - URL: `https://eamos-dev-sg.onrender.com`
  - Docker root: `app/backend`
  - Auto-deploy: off
  - Live commit: `f5eb33e`. **FE/Vercel cutover DONE 2026-05-30** — the live
    `eamos-dev.vercel.app` now proxies `/api/*` here (via Vercel env
    `API_PROXY_TARGET`, set in `app/web/next.config.mjs` rewrites — not
    `NEXT_PUBLIC_API_BASE_URL`). `SUPABASE_SERVICE_ROLE_KEY` now set.
- Old backend still running: `eamos-dev`
  - Service id: `srv-d896ie77f7vs73brs140`
  - Region: Oregon
  - **No longer serving the FE** (cutover 2026-05-30). Kept running ~1 day as
    rollback fallback; **delete ~2026-05-31** once SG proves stable. Rollback =
    point Vercel `API_PROXY_TARGET` back to the Oregon URL + redeploy.

## Applied Private Migrations

Remote migration list now includes:

- `0007_optimize_rls_auth_uid_initplan`
- `0008_protein_annotation_metadata_cache`
- `0009_local_model_cache_perimeter`
- `0010_private_cache_advisor_hardening`
- `0011_private_clinical_source_tables`
- `0012_private_source_asset_storage_metadata`
- `private_source_asset_bucket` (`20260530120420` in Supabase dev history; local
  migration filename reconciled to
  `20260530120420_private_source_asset_bucket.sql`)

All private tables are under `eamos_private`, have RLS enabled, revoke browser roles, and grant DML only to `service_role`.

## Private Tables

Cache/source/protein:

- `eamos_private.local_source_versions`
- `eamos_private.local_model_cache_entries`
- `eamos_private.local_model_jobs`
- `eamos_private.protein_annotation_source_versions`
- `eamos_private.protein_annotation_jobs`
- `eamos_private.protein_annotation_cache`

Tier 3 clinical relational sources:

- `eamos_private.clinical_mondo_diseases`
- `eamos_private.clinical_hpo_terms`
- `eamos_private.clinical_hpo_disease_phenotypes`
- `eamos_private.clinical_hpo_gene_phenotypes`
- `eamos_private.clinical_clingen_gene_validity`
- `eamos_private.clinical_gencc_assertions`

Tier 1/Tier 2 source asset metadata:

- `eamos_private.source_asset_objects`
- `eamos_private.source_asset_materializations`

Current row counts after rollback smokes and real-API lookup attempts: the
cache wiring code was pushed to `main` in `e7f8ab6`; the cache write
observability/fail-fast fix was pushed in `3412d91`.

**RESOLVED + VERIFIED 2026-05-30 19:45 +1000 (Claude, with Steven).** The
silent-fail was a bad session-pooler credential. Deploying `f5eb33e` to
`eamos-dev-sg` + one real-API RPE65 lookup surfaced the exact error via Render
`list_logs` (no SSH needed):
`OperationalError: connection failed ... FATAL: password authentication failed
for user "postgres"`. Steven reset the Supabase DB password and corrected
`SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL` (session pooler, user
`postgres.<project-ref>`). A clean RPE65 lookup then wrote **9/9 rows** to
`eamos_private.local_model_cache_entries` (7 `source_cache` + `vep` +
`variant_cache`) with **zero** cache warnings. The instrumentation in `3412d91`
is what made the diagnosis a one-shot. (`local_source_versions` was 0 before
the source-import CLI/connector apply below; the web lookup path does not write
source-version rows.)

**Tier 3 fixture import + hg38 Storage metadata pilot applied 2026-05-30 21:47
+1000 and hg38 private object verified/materialized 2026-05-31 00:13 +1000
(Codex + Steven).** This workstation was configured ephemerally from Render
env, but direct Postgres egress to the Supabase pooler timed out on
`5432`/`6543`. PostgREST access to `eamos_private` is not exposed, which is the
intended private-schema posture. Codex applied backend-only DML through the
Supabase SQL connector and verified: `local_source_versions=7`,
`clinical_mondo_diseases=2`, `clinical_hpo_terms=3`,
`clinical_hpo_disease_phenotypes=2`, `clinical_hpo_gene_phenotypes=3`,
`clinical_clingen_gene_validity=2`, `clinical_gencc_assertions=2`,
`source_asset_objects=1`, and `source_asset_materializations=1`. Steven then
uploaded/moved `hg38.2bit` in the private bucket `eamos-source-assets`; Codex
verified the clean object key
`ucsc_hg38_2bit/hg38/md5-dcc3ea27079aa6dc3f9deccd7275e0f8/hg38.2bit`, size
`835393456`, MD5/ETag `dcc3ea27079aa6dc3f9deccd7275e0f8`, and bucket
`public=false`. Private metadata now has `source_asset_objects.upload_status =
'verified'`, `public_access_allowed=false`,
`frontend_direct_access_allowed=false`, and
`source_asset_materializations.materialization_status='ready'` with
`fail_closed_reason=null`. No signed raw-source URL, public bucket, frontend
direct access, browser-role grant, Render/Vercel mutation, or S3 tooling
recreation was performed.

**Backend materialization reader/probe path implemented 2026-05-31 01:07 +1000
(Codex).** The backend now has a fail-closed
`resolve_hg38_materialized_runtime_asset(...)` path that reads private
`eamos_private.source_asset_objects` + `source_asset_materializations` metadata
through the existing backend-only Supabase Postgres store and accepts only
`verified` + `approved` + `ready` rows whose size/checksum match the registry
and local cache file while public/frontend access flags remain false. Public
provider-cache health now exposes only sanitized hg38 readiness/status, not
local paths, object paths, secrets, or frontend-readable URLs. This is a reader
and verification layer only: no runtime Storage download/materialization job,
request-time local-source wiring, new object, public URL, Render/Vercel change,
or Supabase DDL/DML was performed.

## Advisor Status

- Security advisors after latest DDL: no lints.
- Performance advisors after latest DDL: INFO-only unused-index findings on empty/new tables plus existing Auth connection strategy note.
- Remediation links:
  - Unused indexes: https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index
  - Auth connection strategy: https://supabase.com/docs/guides/deployment/going-into-prod

## Smoke Results

- Generic local-model/protein cache rollback smokes passed earlier and left no rows.
- Clinical source table DDL advisor checks passed; dev fixture rows are now
  applied in the private clinical tables (counts below).
- Source-asset metadata rollback smoke inserted one `source_asset_objects` row and one verified `source_asset_materializations` row, proved RLS enabled, proved public-access and ready-without-verification constraints reject bad rows, then rolled back.
- Earlier follow-up count query after rollback showed `source_asset_objects=0`,
  `source_asset_materializations=0`, `clinical_mondo_diseases=0`,
  `clinical_hpo_terms=0`, and `local_source_versions=0`; the Codex import
  below is the later durable source-table apply.
- Codex direct SQL smoke against `eamos_private.local_model_cache_entries` on
  2026-05-30 validated the same insert/upsert shape used by the app; the smoke
  row was deleted immediately. This indicates the table DDL/upsert SQL is not
  the blocker.
- Codex SSH attempt to `srv-d8ctvoh9rddc73a27nb0@ssh.singapore.render.com`
  timed out locally before producing a banner or command output, so Codex did
  not run the Render one-off job.
- Codex added `python -m app.cli.eamos_source_import` on 2026-05-30 21:28
  +1000. Local dry-run passed and plans 2 MONDO rows, 3 HPO terms, 2 HPO
  disease phenotype rows, 3 HPO gene phenotype rows, 2 ClinGen validity rows,
  2 GenCC assertion rows, and an hg38 metadata-only private Storage pilot.
  After Steven asked to configure the shell, Codex sourced the required Render
  env values only into the current PowerShell process; direct Postgres still
  timed out at the network layer. The rows were applied through the Supabase
  SQL connector and verified with the counts above.

## Frontend / Claude Boundary

- Do not query `eamos_private` from Vercel/frontend.
- Do not put Supabase service-role keys in `NEXT_PUBLIC_*` variables or frontend bundles.
- Do not build UI against private table or Storage object paths.
- Ask for backend endpoints/lazy sections when UI needs source/cache data.
- Vercel is not part of the large binary source path except as a caller of backend APIs.

## Storage Design

Authoritative draft: `docs/private-source-storage/design.md`.

Current decision:

- Tier 1 large assets and Tier 2 production-sized source files are metadata-only until bucket/object upload approval; hg38.2bit is the first approved private Storage pilot and is verified in dev.
- Proposed bucket name: `eamos-source-assets`, private.
- Proposed object path convention: `source_id/release/checksum/file-name`.
- Backend readers use verified local materialization paths, not browser URLs or startup downloads.
- No public buckets, unrestricted uploads, or signed raw-source URLs to frontend.

## Next Safe Steps

> **Steps 1–4 DONE / VERIFIED 2026-05-30 (Claude + Steven).** `f5eb33e` is live
> on SG and the web lookup path itself surfaced + (after the credential fix)
> succeeded — 9/9 rows landed — so the `warm_source_cache` smoke (step 2) was
> not needed to diagnose. **Steps 5–8 are now implemented for dev fixtures; the
> hg38 private Storage pilot is uploaded, verified, and marked ready in dev
> metadata.**

1. Deploy `main` at or after `3412d91` to `eamos-dev-sg`.
2. Run `python -m app.cli.warm_source_cache --real-apis` on `eamos-dev-sg`.
   The CLI now performs a Supabase cache write/read/delete smoke first and
   should fail loudly if the session-pooler URL, password, SSL, schema, or
   privileges are wrong.
3. If the web lookup path still falls back locally, check Render logs for
   `Supabase local model cache write failed; using local fallback`. The log
   includes cache family/source and sanitized DB error details, but not raw
   cache keys.
4. Verify durable rows in `eamos_private.local_model_cache_entries`.
5. Add/import job code for Tier 3 source tables using existing parsers, with source-version rows and idempotent upserts.
6. Load dev fixture rows first, then consider real MONDO/HPO/ClinGen/GenCC imports only after explicit download/import approval.
7. Add metadata-only source rows for Tier 1/Tier 2 assets from the DOCX matrix.
8. Decide whether `hg38.2bit` or ClinVar VCF is the first private Storage pilot.

Codex update 2026-05-31 00:13 +1000: step 5 code is implemented as
`python -m app.cli.eamos_source_import`; step 8 is decided in code as
`hg38.2bit` because ClinVar VCF lacks an approved local checksum/materialized
file. Dev fixture rows and source-asset rows have been applied to the private
dev tables through the Supabase SQL connector. The local shell was configured
ephemerally from Render env, but direct Postgres egress to the Supabase pooler
timed out; use a Postgres-egress-capable environment such as Render SG for a
direct CLI apply proof if needed. The hg38 Storage pilot is now verified in the
private bucket and marked ready in private metadata. Runtime object
materialization/download jobs and request-time reader wiring remain approval
gated.

Codex update 2026-05-31 01:07 +1000: the reviewed local-cache/materialization
reader/probe path now exists and is tested. Request-time use remains gated until
Steven explicitly approves wiring a live endpoint/tool flow to this local source
path and, separately, any Render env/deploy mutation needed to use it on SG.

## Claude Coordination Note (Historical / Resolved)

Steven asked to coordinate with Claude before proceeding because the env/deploy
explanation was confusing.

Plain-language state:

- This credential/cutover issue is resolved as of 2026-05-30 19:45 +1000 by
  Claude/Steven. The notes below are retained as operational context and should
  not be treated as a request to repeat secret handling in chat.

- It was safe to proceed to the Render env/deploy step from a code-state
  perspective after `e7f8ab6`; SG is now cut over and verified at `f5eb33e`.
- The screenshot shows `SUPABASE_LOCAL_MODEL_CACHE_ENABLED=true` and
  `SUPABASE_LOCAL_MODEL_CACHE_SCHEMA=eamos_private`, which is conceptually
  correct for the backend only.
- The `SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL` value must be a real Supabase
  Postgres connection string, not the project API URL, not the service-role
  key, and not a placeholder.
- GitHub login does not provide the Postgres password. The database password is
  separate in Supabase. If unknown, reset/copy it from the Supabase dashboard.
- Recommended Render value is the Supabase **Session pooler** string converted
  for SQLAlchemy/psycopg, roughly:
  `postgresql+psycopg://postgres.<project-ref>:<db-password>@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres?sslmode=require`
- Direct DB form also works only if Render can reach it:
  `postgresql+psycopg://postgres:<db-password>@db.cpdjxsgasaesysvxkpmi.supabase.co:5432/postgres?sslmode=require`
- After Render is redeployed with the real DB URL, run/wire
  `python -m app.cli.warm_source_cache --real-apis`; then verify rows in
  `eamos_private.local_model_cache_entries`.

Do not ask Steven to paste secrets in chat. If he is in the Render dashboard,
he can paste the DB URL directly into Render's masked env field.
