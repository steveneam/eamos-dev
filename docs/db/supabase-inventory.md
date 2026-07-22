# Supabase Inventory

Last consolidated: 2026-07-22 14:52 UTC by Codex.

This is the durable project and schema inventory salvaged from the retired
`agent_handoff/database_webserver/` handoff. It is not a live service-status
page. Migration application state below was verified against the remote ledger
on 2026-07-22; re-verify it before making later operational changes.

## Project

- Project: `eamos-dev`
- Project ref: `cpdjxsgasaesysvxkpmi`
- Region: `ap-southeast-2`
- Private schema: `eamos_private`
- Private Storage bucket: `eamos-source-assets`

Do not record database URLs, service-role keys, JWT secrets, S3 credentials,
signed URLs, or deployment tokens in this document.

## Applied Migration Ledger

The remote `eamos-dev` ledger reported these entries on 2026-07-22:

- `20260525130733` · `0003_evidence_submission_payload`
- `20260525130917` · `0004_harden_handle_new_user`
- `20260525135123` · `0005_grant_service_role_dml`
- `20260525135844` · `0006_supabase_advisor_hardening`
- `20260529164415` · `0007_optimize_rls_auth_uid_initplan`
- `20260529164444` · `0008_protein_annotation_metadata_cache`
- `20260529164508` · `0009_local_model_cache_perimeter`
- `20260529164639` · `0010_private_cache_advisor_hardening`
- `20260529170234` · `0011_private_clinical_source_tables`
- `20260529171120` · `0012_private_source_asset_storage_metadata`
- `20260530120420` · `private_source_asset_bucket`
- `20260606051729` · `variant_library_persistence`
- `20260606052901` · `variant_library_folder_fk_index`
- `20260722144613` · `user_library_document`
- `20260722144619` · `product_workflow_runs`

The SQL files under `supabase/migrations/` remain the canonical definitions.
Remote timestamps and names do not always match the local filename prefix, so
compare both the ledger and exact SQL before any reuse. Do not blindly push all
local migrations.

## Task F Application Receipt

Applied to `eamos-dev` on 2026-07-22 after Steven approved the filled exact
mutation card:

- `20260614195800_user_library_document.sql` created `public.user_library`;
- `20260719113620_product_workflow_runs.sql` created
  `public.product_workflow_run` and `public.product_workflow_item`.

The preflight proved all three target tables were absent. Post-apply checks
matched the reviewed tables, constraints, owner/expiry indexes, policies, and
grants. RLS is enabled on all three tables and forced on both workflow tables;
policies scope authenticated access with `(select auth.uid()) = user_id`.
Authenticated users may manage only their own library document, read their own
workflow rows/items, and delete their own workflow runs. Backend `service_role`
retains server-side lifecycle DML.

A transaction-scoped two-principal probe proved owner-only visibility, blocked
cross-owner library updates and workflow deletes, allowed an owner delete with
item cascade, and blocked direct authenticated workflow inserts. The transaction
was rolled back and all three tables returned to zero rows. Security advisors
remained clear. Performance advisors reported only informational unused-index
notices, expected for newly created empty tables, plus the pre-existing Auth
absolute-connection allocation notice. No deploy, provider/env, Storage/source,
Render, or Phase 7 mutation accompanied this application.

## Public Account-Owned Tables

- `public.user_library`
- `public.product_workflow_run`
- `public.product_workflow_item`

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
