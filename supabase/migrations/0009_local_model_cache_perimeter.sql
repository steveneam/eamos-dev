-- ============================================================================
-- Eamos - Backend-only local model/source cache perimeter
-- ============================================================================
-- Scope: private Supabase tables for backend-owned local model/cache metadata:
-- source versions/checksums, cache entries, provenance, freshness, warnings,
-- and job state for fixture/local-cache outputs promoted to dev-cache testing.
--
-- Guardrail: backend service-role access only. No anon/authenticated grants, no
-- public genomic/protein buckets, no direct frontend SQL over these tables.
-- ============================================================================

create schema if not exists eamos_private;

revoke all on schema eamos_private from public;
revoke all on schema eamos_private from anon;
revoke all on schema eamos_private from authenticated;
grant usage on schema eamos_private to service_role;

create table if not exists eamos_private.local_source_versions (
    source_version_id uuid primary key default gen_random_uuid(),
    source_id text not null,
    source_name text not null,
    source_release text,
    source_url text,
    checksum_md5 text,
    checksum_sha256 text,
    license_status text not null default 'recorded',
    asset_role text,
    asset_path text,
    row_count bigint,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.local_model_cache_entries (
    cache_id uuid primary key default gen_random_uuid(),
    cache_family text not null,
    source_id text not null,
    cache_key text not null,
    normalized_identity jsonb not null default '{}'::jsonb,
    request_identity jsonb not null default '{}'::jsonb,
    status text not null,
    payload jsonb not null default '{}'::jsonb,
    raw_payload jsonb,
    provenance jsonb not null default '{}'::jsonb,
    warnings jsonb not null default '[]'::jsonb,
    source_url text,
    source_release text,
    source_checksum_sha256 text,
    restricted_fields_stripped boolean not null default true,
    public_serialization_policy text not null default 'backend_only_private_cache',
    fetched_at timestamp with time zone not null default timezone('utc'::text, now()),
    expires_at timestamp with time zone,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.local_model_jobs (
    local_model_job_id uuid primary key default gen_random_uuid(),
    job_type text not null,
    cache_family text not null,
    cache_key text,
    status text not null,
    fail_closed_reason text,
    input_payload jsonb not null default '{}'::jsonb,
    result_cache_id uuid references eamos_private.local_model_cache_entries(cache_id)
        on delete set null,
    provenance jsonb not null default '{}'::jsonb,
    warnings jsonb not null default '[]'::jsonb,
    started_at timestamp with time zone not null default timezone('utc'::text, now()),
    completed_at timestamp with time zone,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create unique index if not exists idx_local_source_versions_unique
on eamos_private.local_source_versions (
    source_id,
    coalesce(source_release, ''),
    coalesce(checksum_sha256, '')
);

create unique index if not exists idx_local_model_cache_entries_unique
on eamos_private.local_model_cache_entries (
    cache_family,
    source_id,
    cache_key
);

create index if not exists idx_local_model_cache_entries_source_status
on eamos_private.local_model_cache_entries(source_id, status);

create index if not exists idx_local_model_cache_entries_freshness
on eamos_private.local_model_cache_entries(cache_family, expires_at);

create index if not exists idx_local_model_cache_entries_payload_gin
on eamos_private.local_model_cache_entries using gin (payload);

create index if not exists idx_local_model_jobs_family_status
on eamos_private.local_model_jobs(cache_family, status);

create index if not exists idx_local_model_jobs_cache_key
on eamos_private.local_model_jobs(cache_key);

alter table eamos_private.local_source_versions enable row level security;
alter table eamos_private.local_model_cache_entries enable row level security;
alter table eamos_private.local_model_jobs enable row level security;

revoke all on all tables in schema eamos_private from public;
revoke all on all tables in schema eamos_private from anon;
revoke all on all tables in schema eamos_private from authenticated;

grant select, insert, update, delete on eamos_private.local_source_versions
to service_role;

grant select, insert, update, delete on eamos_private.local_model_cache_entries
to service_role;

grant select, insert, update, delete on eamos_private.local_model_jobs
to service_role;

comment on table eamos_private.local_source_versions is
    'Backend-only source version/checksum manifest for local model and source-cache data.';

comment on table eamos_private.local_model_cache_entries is
    'Backend-only cache rows for Eamos local models/source outputs. Browser roles cannot access this table.';

comment on table eamos_private.local_model_jobs is
    'Backend-only local model/source cache job state and fail-closed result tracking.';
