# Database / Webserver Current State

Last updated: 2026-05-30 05:14 +1000 by Codex.

## Supabase Project

- Dev project: `eamos-dev`
- Project ref/id: `cpdjxsgasaesysvxkpmi`
- Region: `ap-southeast-2`
- Status at discovery: `ACTIVE_HEALTHY`
- Guardrail: Codex performed no Render deploy/env mutation. Claude/Steven are
  coordinating Render env/deploy after code push.

## Render Services

- Current target backend: `eamos-dev-sg`
  - Service id: `srv-d8ctvoh9rddc73a27nb0`
  - Region: Singapore
  - Plan: Starter
  - URL: `https://eamos-dev-sg.onrender.com`
  - Docker root: `app/backend`
  - Auto-deploy: off
  - Last reported live commit before this debug patch: `a94ec37`
- Old backend still running: `eamos-dev`
  - Service id: `srv-d896ie77f7vs73brs140`
  - Region: Oregon
  - FE/Vercel was still pointed here at Claude handoff time.

## Applied Private Migrations

Remote migration list now includes:

- `0007_optimize_rls_auth_uid_initplan`
- `0008_protein_annotation_metadata_cache`
- `0009_local_model_cache_perimeter`
- `0010_private_cache_advisor_hardening`
- `0011_private_clinical_source_tables`
- `0012_private_source_asset_storage_metadata`

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

Current row counts after rollback smokes and real-API lookup attempts: cache
tables remain empty. The cache wiring code was pushed to `main` in `e7f8ab6`;
the cache write observability/fail-fast fix was pushed in `3412d91`.

## Advisor Status

- Security advisors after latest DDL: no lints.
- Performance advisors after latest DDL: INFO-only unused-index findings on empty/new tables plus existing Auth connection strategy note.
- Remediation links:
  - Unused indexes: https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index
  - Auth connection strategy: https://supabase.com/docs/guides/deployment/going-into-prod

## Smoke Results

- Generic local-model/protein cache rollback smokes passed earlier and left no rows.
- Clinical source table DDL advisor checks passed; rows remain empty.
- Source-asset metadata rollback smoke inserted one `source_asset_objects` row and one verified `source_asset_materializations` row, proved RLS enabled, proved public-access and ready-without-verification constraints reject bad rows, then rolled back.
- Follow-up count query showed `source_asset_objects=0`, `source_asset_materializations=0`, `clinical_mondo_diseases=0`, `clinical_hpo_terms=0`, and `local_source_versions=0`.
- Codex direct SQL smoke against `eamos_private.local_model_cache_entries` on
  2026-05-30 validated the same insert/upsert shape used by the app; the smoke
  row was deleted immediately. This indicates the table DDL/upsert SQL is not
  the blocker.
- Codex SSH attempt to `srv-d8ctvoh9rddc73a27nb0@ssh.singapore.render.com`
  timed out locally before producing a banner or command output, so Codex did
  not run the Render one-off job.

## Frontend / Claude Boundary

- Do not query `eamos_private` from Vercel/frontend.
- Do not put Supabase service-role keys in `NEXT_PUBLIC_*` variables or frontend bundles.
- Do not build UI against private table or Storage object paths.
- Ask for backend endpoints/lazy sections when UI needs source/cache data.
- Vercel is not part of the large binary source path except as a caller of backend APIs.

## Storage Design

Authoritative draft: `docs/private-source-storage/design.md`.

Current decision:

- Tier 1 large assets and Tier 2 production-sized source files are metadata-only until bucket/object upload approval.
- Proposed bucket name: `eamos-source-assets`, private.
- Proposed object path convention: `source_id/release/checksum/file-name`.
- Backend readers use verified local materialization paths, not browser URLs or startup downloads.
- No public buckets, unrestricted uploads, or signed raw-source URLs to frontend.

## Next Safe Steps

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

## Claude Coordination Note

Steven asked to coordinate with Claude before proceeding because the env/deploy
explanation was confusing.

Plain-language state:

- It is now safe to proceed to the Render env/deploy step from a code-state
  perspective. The cache wiring code is on `main` in `e7f8ab6`.
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
