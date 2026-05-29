-- ============================================================================
-- Eamos - Private source asset storage metadata
-- ============================================================================
-- Scope: metadata-only hardening for large Tier 1 and Tier 2 source assets
-- before any private Storage bucket or upload is approved. These tables track
-- object paths, checksums, sidecars, approval state, and backend local-cache
-- materialization status.
--
-- Guardrail: no bucket creation, no raw object upload, no browser grants, and
-- no frontend direct access. Backend jobs must verify checksum/size before a
-- source reader can mark an asset ready.
-- ============================================================================

create schema if not exists eamos_private;

revoke all on schema eamos_private from public;
revoke all on schema eamos_private from anon;
revoke all on schema eamos_private from authenticated;
grant usage on schema eamos_private to service_role;

create table if not exists eamos_private.source_asset_objects (
    source_asset_object_id uuid primary key default gen_random_uuid(),
    source_version_id uuid references eamos_private.local_source_versions(source_version_id)
        on delete set null,
    source_id text not null,
    asset_role text not null,
    storage_provider text not null default 'supabase_storage_private',
    bucket_id text not null default 'eamos-source-assets',
    object_path text not null,
    object_version text,
    content_type text,
    byte_size bigint,
    checksum_algorithm text not null,
    checksum_value text not null,
    sidecar_of_asset_id uuid references eamos_private.source_asset_objects(source_asset_object_id)
        on delete set null,
    immutable boolean not null default true,
    upload_status text not null default 'metadata_only',
    approval_status text not null default 'pending_storage_approval',
    license_status text not null default 'recorded',
    public_access_allowed boolean not null default false,
    frontend_direct_access_allowed boolean not null default false,
    materialization_required boolean not null default true,
    metadata jsonb not null default '{}'::jsonb,
    warnings jsonb not null default '[]'::jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now()),
    constraint source_asset_objects_private_only check (
        public_access_allowed = false
        and frontend_direct_access_allowed = false
    ),
    constraint source_asset_objects_checksum_present check (
        length(trim(checksum_algorithm)) > 0
        and length(trim(checksum_value)) > 0
    ),
    constraint source_asset_objects_upload_status_valid check (
        upload_status in (
            'metadata_only',
            'upload_pending',
            'uploaded',
            'verified',
            'quarantined',
            'retired'
        )
    ),
    constraint source_asset_objects_approval_status_valid check (
        approval_status in (
            'pending_storage_approval',
            'approved',
            'blocked',
            'retired'
        )
    )
);

create table if not exists eamos_private.source_asset_materializations (
    source_asset_materialization_id uuid primary key default gen_random_uuid(),
    source_asset_object_id uuid not null references eamos_private.source_asset_objects(
        source_asset_object_id
    ) on delete cascade,
    environment text not null,
    backend_runtime text not null default 'render_backend',
    local_cache_path text not null,
    materialization_status text not null default 'not_materialized',
    byte_size bigint,
    checksum_algorithm text,
    checksum_value text,
    ready_marker text,
    verified_at timestamp with time zone,
    last_attempt_at timestamp with time zone,
    fail_closed_reason text,
    stale_allowed boolean not null default false,
    metadata jsonb not null default '{}'::jsonb,
    warnings jsonb not null default '[]'::jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now()),
    constraint source_asset_materializations_status_valid check (
        materialization_status in (
            'not_materialized',
            'download_pending',
            'verifying',
            'ready',
            'failed',
            'quarantined',
            'retired'
        )
    ),
    constraint source_asset_materializations_ready_requires_verified_at check (
        materialization_status <> 'ready'
        or verified_at is not null
    ),
    constraint source_asset_materializations_stale_blocked check (
        stale_allowed = false
    )
);

create unique index if not exists idx_source_asset_objects_unique_path
on eamos_private.source_asset_objects(bucket_id, object_path);

create index if not exists idx_source_asset_objects_source_id
on eamos_private.source_asset_objects(source_id, asset_role, upload_status);

create index if not exists idx_source_asset_objects_source_version_id
on eamos_private.source_asset_objects(source_version_id);

create index if not exists idx_source_asset_objects_sidecar_of_asset_id
on eamos_private.source_asset_objects(sidecar_of_asset_id);

create unique index if not exists idx_source_asset_materializations_unique_env_path
on eamos_private.source_asset_materializations(
    source_asset_object_id,
    environment,
    local_cache_path
);

create index if not exists idx_source_asset_materializations_status
on eamos_private.source_asset_materializations(environment, materialization_status);

alter table eamos_private.source_asset_objects enable row level security;
alter table eamos_private.source_asset_materializations enable row level security;

revoke all on all tables in schema eamos_private from public;
revoke all on all tables in schema eamos_private from anon;
revoke all on all tables in schema eamos_private from authenticated;

grant select, insert, update, delete on eamos_private.source_asset_objects
to service_role;

grant select, insert, update, delete on eamos_private.source_asset_materializations
to service_role;

drop policy if exists "Deny browser roles on source asset objects"
on eamos_private.source_asset_objects;

create policy "Deny browser roles on source asset objects"
on eamos_private.source_asset_objects
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on source asset materializations"
on eamos_private.source_asset_materializations;

create policy "Deny browser roles on source asset materializations"
on eamos_private.source_asset_materializations
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

comment on table eamos_private.source_asset_objects is
    'Backend-only metadata for private large source assets; no public bucket or frontend direct access.';

comment on table eamos_private.source_asset_materializations is
    'Backend-only local-cache materialization state for private source assets.';
