# Supabase Inventory

Last consolidated: 2026-07-15 11:19 UTC by Codex.

This is the durable project and schema inventory salvaged from the retired
`agent_handoff/database_webserver/` handoff. It is not a live service-status
page. Migration application state below is the last reported state from
2026-06-01; verify the remote migration list before making operational changes.

## Project

- Project: `eamos-dev`
- Project ref: `cpdjxsgasaesysvxkpmi`
- Region: `ap-southeast-2`
- Private schema: `eamos_private`
- Private Storage bucket: `eamos-source-assets`

Do not record database URLs, service-role keys, JWT secrets, S3 credentials,
signed URLs, or deployment tokens in this document.

## Reported Applied Migrations

The retired handoff reported these migrations applied to the dev project:

- `0007_optimize_rls_auth_uid_initplan`
- `0008_protein_annotation_metadata_cache`
- `0009_local_model_cache_perimeter`
- `0010_private_cache_advisor_hardening`
- `0011_private_clinical_source_tables`
- `0012_private_source_asset_storage_metadata`
- `20260530120420_private_source_asset_bucket`

The SQL files under `supabase/migrations/` remain the canonical definitions.
Some file headers describe their original local-only drafting state; the list
above records the later remote-application report and should be checked against
the remote migration ledger before reuse.

## Private Tables

Protein annotation and local cache:

- `eamos_private.local_source_versions`
- `eamos_private.local_model_cache_entries`
- `eamos_private.local_model_jobs`
- `eamos_private.protein_annotation_source_versions`
- `eamos_private.protein_annotation_jobs`
- `eamos_private.protein_annotation_cache`

Clinical relational sources:

- `eamos_private.clinical_mondo_diseases`
- `eamos_private.clinical_hpo_terms`
- `eamos_private.clinical_hpo_disease_phenotypes`
- `eamos_private.clinical_hpo_gene_phenotypes`
- `eamos_private.clinical_clingen_gene_validity`
- `eamos_private.clinical_gencc_assertions`

Source asset metadata:

- `eamos_private.source_asset_objects`
- `eamos_private.source_asset_materializations`

## Access Boundary

- Treat every `eamos_private` table and source asset as backend-owned.
- Keep RLS enabled as defense in depth and grant DML only to `service_role`.
- Revoke `public`, `anon`, and `authenticated` access to the private schema and
  its tables. Do not expose it as a frontend contract.
- Frontend and Vercel code must obtain source/cache data through backend APIs;
  never query private tables or raw Storage object paths from the browser.
- Keep genomic, protein, and source-data buckets private. Do not create public
  objects, unrestricted uploads, or signed raw-source URLs for frontend use.
- Backend readers must accept only verified, approved materializations whose
  size and checksum match the registry.
- Run Supabase security and performance advisors plus a bounded smoke query
  after DDL, import, policy, or Storage changes.

Detailed historical smokes, imports, object checksums, and the superseded Render
service narrative are preserved in
`agent_handoff/archive/2026-07-15-database-webserver-current.md`.
