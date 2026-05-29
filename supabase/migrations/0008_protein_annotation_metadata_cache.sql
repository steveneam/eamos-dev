-- ============================================================================
-- Eamos - Backend-only protein annotation metadata and cache tables
-- ============================================================================
-- LOCAL ONLY: drafted for later application via Supabase tooling. It was not
-- applied to any live Supabase project as part of this implementation pass.
--
-- Scope: cache/provenance metadata for the proprietary Eamos protein annotation
-- orchestration. Upstream databases/tools keep their own licenses; these tables
-- store source versions, checksums, job state, and normalized annotation results.
--
-- Guardrail: backend service-role access only. No anon/authenticated grants, no
-- public genomic/protein buckets, no direct frontend SQL over these tables.
-- ============================================================================

create schema if not exists eamos_private;

revoke all on schema eamos_private from public;
revoke all on schema eamos_private from anon;
revoke all on schema eamos_private from authenticated;
grant usage on schema eamos_private to service_role;

create table if not exists eamos_private.protein_annotation_source_versions (
    source_version_id uuid primary key default gen_random_uuid(),
    source_id text not null,
    source_name text not null,
    source_release text,
    source_url text,
    checksum_md5 text,
    checksum_sha256 text,
    license_status text not null,
    asset_role text,
    asset_path text,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.protein_annotation_jobs (
    annotation_job_id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete set null,
    sequence_hash text not null,
    sequence_hash_algorithm text not null default 'sha256',
    sequence_label text,
    gene_symbol text,
    transcript text,
    protein_accession text,
    protein_length integer,
    pfam_release text,
    hmmer_release text,
    uniprot_release text,
    status text not null,
    fail_closed_reason text,
    cache_key text,
    warnings jsonb not null default '[]'::jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.protein_annotation_cache (
    cache_id uuid primary key default gen_random_uuid(),
    sequence_hash text not null,
    sequence_hash_algorithm text not null default 'sha256',
    protein_length integer not null,
    pfam_release text,
    hmmer_release text,
    uniprot_release text,
    cache_key text not null,
    track jsonb not null,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create unique index if not exists idx_protein_annotation_source_versions_unique
on eamos_private.protein_annotation_source_versions (
    source_id,
    coalesce(source_release, ''),
    coalesce(checksum_sha256, '')
);

create unique index if not exists idx_protein_annotation_cache_unique
on eamos_private.protein_annotation_cache (
    sequence_hash,
    coalesce(pfam_release, ''),
    coalesce(hmmer_release, ''),
    coalesce(uniprot_release, '')
);

create index if not exists idx_protein_annotation_jobs_sequence_hash
on eamos_private.protein_annotation_jobs(sequence_hash);

create index if not exists idx_protein_annotation_jobs_gene_symbol
on eamos_private.protein_annotation_jobs(gene_symbol);

create index if not exists idx_protein_annotation_cache_sequence_hash
on eamos_private.protein_annotation_cache(sequence_hash);

alter table eamos_private.protein_annotation_source_versions enable row level security;
alter table eamos_private.protein_annotation_jobs enable row level security;
alter table eamos_private.protein_annotation_cache enable row level security;

revoke all on all tables in schema eamos_private from public;
revoke all on all tables in schema eamos_private from anon;
revoke all on all tables in schema eamos_private from authenticated;

grant select, insert, update, delete on eamos_private.protein_annotation_source_versions
to service_role;

grant select, insert, update, delete on eamos_private.protein_annotation_jobs
to service_role;

grant select, insert, update, delete on eamos_private.protein_annotation_cache
to service_role;
