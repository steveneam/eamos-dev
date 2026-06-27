# Task F Supabase Production Readiness Runbook

Last updated: 2026-06-26 01:10 +1000 - Codex.
Status: Planning/runbook only. No Supabase mutation, Render env mutation,
deploy, Vercel command, storage upload, or materialization job has run.

## Scope

Use this before any production Supabase schema, RLS, grant, storage, or source
asset change for Eamos.

This runbook is deliberately read-only until Steven explicitly approves the
specific mutation. Approval to plan or inventory does not approve:

- `supabase db push`, `supabase migration up`, `apply_migration`, or
  `execute_sql` with DDL/DML;
- private Storage bucket creation, policy changes, object upload/delete/copy;
- service-role key use outside backend/operator-only code;
- S3 credential creation/rotation or Render env mutation;
- large source sync or materialization.

## Current Docs Checked

Official Supabase references checked for this runbook:

- Supabase changelog: `https://supabase.com/changelog`
- Securing the Data API: `https://supabase.com/docs/guides/api/securing-your-api`
- Row Level Security: `https://supabase.com/docs/guides/database/postgres/row-level-security`
- Database advisors: `https://supabase.com/docs/guides/database/database-advisors`
- CLI database advisors: `https://supabase.com/docs/reference/cli/supabase-db-advisors`
- Storage access control: `https://supabase.com/docs/guides/storage/security/access-control`
- Storage S3 uploads: `https://supabase.com/docs/guides/storage/uploads/s3-uploads`

Before executing this runbook, re-check the changelog and command help because
Supabase CLI and exposed-schema behavior change over time.

## Preflight Inputs

Record these before connecting to any remote project:

| Field | Value |
| --- | --- |
| Supabase project ref | TBD |
| Environment | production / staging / local |
| Target schemas | `public`, `eamos_private`, storage schemas as applicable |
| Data API exposed schemas | TBD from dashboard/API settings |
| Service-role holder | backend/operator only |
| Expected mutation | none for read-only pass |
| Rollback owner | TBD |

## CLI Discovery

Do not guess Supabase CLI command shape. Run help first:

```powershell
supabase --version
supabase --help
supabase db --help
supabase db advisors --help
```

If the installed CLI cannot run read-only advisors, use the authenticated
Supabase MCP advisor tool if available. If neither is available, mark the
advisor gate blocked instead of substituting mutation SQL.

## Read-Only Checks

### 1. Remote Schema and Table Inventory

Run read-only SQL only:

```sql
select table_schema, table_name, table_type
from information_schema.tables
where table_schema not in ('pg_catalog', 'information_schema')
order by table_schema, table_name;
```

Record which tables are Eamos app/user/cache metadata, which are source
metadata, and which should never be exposed through the Data API.

### 2. RLS Coverage

Every table in an exposed schema must have RLS enabled unless it is intentionally
blocked from public roles by grants and schema exposure.

```sql
select
  n.nspname as schema_name,
  c.relname as table_name,
  c.relrowsecurity as rls_enabled,
  c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'r'
  and n.nspname not in ('pg_catalog', 'information_schema')
order by n.nspname, c.relname;
```

Policy review query:

```sql
select
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
from pg_policies
order by schemaname, tablename, policyname;
```

Fail conditions:

- exposed table with RLS disabled;
- `TO authenticated` policies without row ownership or source-scope predicate;
- `UPDATE` policy missing `WITH CHECK`;
- authorization based on user-editable metadata;
- broad `USING (true)` policies on user-owned or mutable tables;
- RLS policies that call `auth.uid()` directly in row predicates instead of
  wrapping it as `(select auth.uid())` for large tables.

### 3. Grants and Exposed API Access

RLS controls rows; grants and exposed schemas control whether the Data API can
reach a table at all. Inspect both.

```sql
select
  grantee,
  table_schema,
  table_name,
  privilege_type
from information_schema.role_table_grants
where grantee in ('anon', 'authenticated', 'service_role')
order by table_schema, table_name, grantee, privilege_type;
```

Fail conditions:

- `anon`/`authenticated` has broad table privileges on private source metadata
  or operator tables;
- `PUBLIC` retains privileges that should be revoked;
- service-role access is used from browser/client code;
- a newly created table is expected to be available through the Data API but
  has no explicit grants in projects that require explicit access.

### 4. FK and Hot-Path Indexes

Local Task A found no SQLAlchemy FK index gaps. Re-check the remote schema
because migrations/manual SQL can drift:

```sql
select
  conrelid::regclass as table_name,
  a.attname as fk_column
from pg_constraint c
join pg_attribute a on a.attrelid = c.conrelid and a.attnum = any(c.conkey)
where c.contype = 'f'
  and not exists (
    select 1
    from pg_index i
    where i.indrelid = c.conrelid
      and a.attnum = any(i.indkey)
  )
order by table_name::text, fk_column;
```

Also verify composite indexes for Eamos hot filters:

- report/source cache: `normalized_variant_id`, `section_id`, `source_id`,
  `schema_version`, `query_string`, `stale_after`;
- user-owned rows: `user_id` plus common sort/filter columns;
- RLS policy columns such as `user_id` or `owner_id`;
- source metadata release keys and object identifiers.

Use partial indexes only where the workload consistently filters the same
subset, such as active/non-deleted rows or pending jobs.

### 5. Advisors

Run read-only advisors and attach sanitized output:

```powershell
supabase db advisors
```

Required result before production sign-off:

- no unresolved security advisor findings for RLS, exposed views, function
  search paths, or broad grants;
- no unresolved performance advisor findings for missing FK indexes on hot
  paths;
- any accepted residual has an owner, severity, and reason.

### 6. Views, Functions, and Privileged Code

Inspect views:

```sql
select schemaname, viewname, definition
from pg_views
where schemaname not in ('pg_catalog', 'information_schema')
order by schemaname, viewname;
```

Inspect `SECURITY DEFINER` functions:

```sql
select
  n.nspname as schema_name,
  p.proname as function_name,
  pg_get_functiondef(p.oid) as definition
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where p.prosecdef
order by n.nspname, p.proname;
```

Fail conditions:

- exposed view bypasses RLS and is not `security_invoker` on supported Postgres;
- `SECURITY DEFINER` function lives in an exposed schema without explicit
  identity checks and revoked `EXECUTE`;
- function omits a pinned `search_path`;
- privileged function was added to work around a permission error instead of
  fixing grants/RLS.

### 7. Storage Buckets and Large Source Assets

Inspect buckets and policies before upload:

```sql
select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets
order by id;

select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'storage'
order by tablename, policyname;
```

Eamos requirements:

- `eamos-source-assets` remains private;
- no public genomic/protein/literature source buckets;
- browser roles do not receive raw source-object read/write policies;
- large uploads use S3-compatible multipart/resumable flow where credentials
  are server/operator-only;
- object paths include source ID, asset ID, checksum/version segment, and file
  name;
- rollback records the previous object/version or current pointer.

### 8. Secret Exposure Scan

Before production sign-off:

```powershell
git ls-files | rg "(^|/)\.env($|\.|/)"
rg -n "service_role|SUPABASE_SERVICE|SUPABASE_STORAGE_S3|postgresql://|NEXT_PUBLIC_.*(SECRET|SERVICE|PRIVATE|S3)" .
```

Expected:

- Supabase anon/publishable keys may be public where intended;
- service-role, S3, database URLs, pooler passwords, JWT secrets, and provider
  keys are backend/operator-only;
- no service-role or S3 key appears in `NEXT_PUBLIC_*`, frontend bundles,
  committed docs, screenshots, logs, or transcript-derived artifacts.

### 9. Sanitized Health Proof

After an approved mutation, the proof must show readiness without leaking:

- local filesystem paths;
- object URIs for private source assets;
- secret values;
- raw source rows or full article text;
- service-role/S3 presence beyond boolean/configured status.

Use `/api/v1/health/provider-cache` and source-specific preflight CLIs only
after deployment is explicitly approved.

## Mutation Approval Template

Paste this before any remote action:

```text
Requesting approval for Supabase mutation:
- Project ref:
- Environment:
- Exact command or SQL:
- Expected objects/tables/policies affected:
- Rollback command/object/version:
- Read-only evidence already captured:
- Secrets redaction plan:
```

Without that approval, stop at read-only findings.

## Production Sign-Off Criteria

Task F is ready only when all are attached:

- changelog/docs rechecked on the execution date;
- schema/table inventory;
- RLS and policy inventory;
- grants inventory and Data API exposure decision;
- storage bucket/policy inventory;
- advisors output and disposition;
- FK/composite index review;
- secret exposure scan;
- sanitized health/preflight output;
- rollback object/version or migration rollback.

## Eamos-Specific Notes

- Supabase Postgres owns metadata, app/user state, source/version manifests,
  cache tables that need SQL semantics, and job status.
- Private Storage owns large immutable source objects and Parquet releases.
- Render persistent disk owns only the current approved runtime subset and
  compact serving indexes.
- PubMed/PMC full text, genomic VCFs, PDFs, media, and multi-GB source blobs do
  not belong in Supabase Postgres.
