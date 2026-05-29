-- ============================================================================
-- Eamos - Private clinical source relational tables
-- ============================================================================
-- Scope: backend-only Supabase tables for the DOCX Tier 3 relational sources:
-- MONDO disease ontology, HPO disease/gene phenotype links, ClinGen gene
-- validity, and GenCC assertions.
--
-- Guardrail: service-role access only. Browser roles receive no grants and
-- restrictive deny-all policies. Frontend access must go through backend APIs,
-- not direct SQL over these source tables.
-- ============================================================================

create schema if not exists eamos_private;

revoke all on schema eamos_private from public;
revoke all on schema eamos_private from anon;
revoke all on schema eamos_private from authenticated;
grant usage on schema eamos_private to service_role;

create table if not exists eamos_private.clinical_mondo_diseases (
    mondo_disease_id uuid primary key default gen_random_uuid(),
    source_version_id uuid references eamos_private.local_source_versions(source_version_id)
        on delete set null,
    mondo_id text not null,
    name text not null,
    xrefs text[] not null default '{}'::text[],
    definition text,
    provenance jsonb not null default '{}'::jsonb,
    raw_payload jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.clinical_hpo_terms (
    hpo_term_id uuid primary key default gen_random_uuid(),
    source_version_id uuid references eamos_private.local_source_versions(source_version_id)
        on delete set null,
    hpo_id text not null,
    label text not null,
    provenance jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.clinical_hpo_disease_phenotypes (
    hpo_disease_phenotype_id uuid primary key default gen_random_uuid(),
    source_version_id uuid references eamos_private.local_source_versions(source_version_id)
        on delete set null,
    disease_id text not null,
    disease_name text not null,
    hpo_id text not null,
    hpo_label text not null,
    evidence text,
    frequency text,
    provenance jsonb not null default '{}'::jsonb,
    raw_payload jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.clinical_hpo_gene_phenotypes (
    hpo_gene_phenotype_id uuid primary key default gen_random_uuid(),
    source_version_id uuid references eamos_private.local_source_versions(source_version_id)
        on delete set null,
    gene_symbol text not null,
    gene_id text,
    hpo_id text not null,
    hpo_label text not null,
    provenance jsonb not null default '{}'::jsonb,
    raw_payload jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.clinical_clingen_gene_validity (
    clingen_gene_validity_id uuid primary key default gen_random_uuid(),
    source_version_id uuid references eamos_private.local_source_versions(source_version_id)
        on delete set null,
    gene_symbol text not null,
    gene_hgnc_id text,
    disease_label text not null,
    disease_id text not null,
    mode_of_inheritance text,
    classification text not null,
    source_date date,
    report_url text,
    provenance jsonb not null default '{}'::jsonb,
    raw_payload jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create table if not exists eamos_private.clinical_gencc_assertions (
    gencc_assertion_id uuid primary key default gen_random_uuid(),
    source_version_id uuid references eamos_private.local_source_versions(source_version_id)
        on delete set null,
    gene_symbol text not null,
    gene_curie text,
    disease_title text not null,
    disease_curie text not null,
    assertion text not null,
    submitter text not null,
    source_date date,
    report_url text,
    provenance jsonb not null default '{}'::jsonb,
    raw_payload jsonb,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now())
);

create unique index if not exists idx_clinical_mondo_diseases_mondo_id
on eamos_private.clinical_mondo_diseases(mondo_id);

create index if not exists idx_clinical_mondo_diseases_xrefs_gin
on eamos_private.clinical_mondo_diseases using gin (xrefs);

create index if not exists idx_clinical_mondo_diseases_source_version_id
on eamos_private.clinical_mondo_diseases(source_version_id);

create unique index if not exists idx_clinical_hpo_terms_hpo_id
on eamos_private.clinical_hpo_terms(hpo_id);

create index if not exists idx_clinical_hpo_terms_source_version_id
on eamos_private.clinical_hpo_terms(source_version_id);

create unique index if not exists idx_clinical_hpo_disease_phenotypes_unique
on eamos_private.clinical_hpo_disease_phenotypes(disease_id, hpo_id);

create index if not exists idx_clinical_hpo_disease_phenotypes_hpo_id
on eamos_private.clinical_hpo_disease_phenotypes(hpo_id);

create index if not exists idx_clinical_hpo_disease_phenotypes_source_version_id
on eamos_private.clinical_hpo_disease_phenotypes(source_version_id);

create unique index if not exists idx_clinical_hpo_gene_phenotypes_unique
on eamos_private.clinical_hpo_gene_phenotypes(gene_symbol, hpo_id);

create index if not exists idx_clinical_hpo_gene_phenotypes_hpo_id
on eamos_private.clinical_hpo_gene_phenotypes(hpo_id);

create index if not exists idx_clinical_hpo_gene_phenotypes_source_version_id
on eamos_private.clinical_hpo_gene_phenotypes(source_version_id);

create unique index if not exists idx_clinical_clingen_gene_validity_unique
on eamos_private.clinical_clingen_gene_validity(gene_symbol, disease_id, classification);

create index if not exists idx_clinical_clingen_gene_validity_source_version_id
on eamos_private.clinical_clingen_gene_validity(source_version_id);

create unique index if not exists idx_clinical_gencc_assertions_unique
on eamos_private.clinical_gencc_assertions(gene_symbol, disease_curie, submitter, assertion);

create index if not exists idx_clinical_gencc_assertions_source_version_id
on eamos_private.clinical_gencc_assertions(source_version_id);

alter table eamos_private.clinical_mondo_diseases enable row level security;
alter table eamos_private.clinical_hpo_terms enable row level security;
alter table eamos_private.clinical_hpo_disease_phenotypes enable row level security;
alter table eamos_private.clinical_hpo_gene_phenotypes enable row level security;
alter table eamos_private.clinical_clingen_gene_validity enable row level security;
alter table eamos_private.clinical_gencc_assertions enable row level security;

revoke all on all tables in schema eamos_private from public;
revoke all on all tables in schema eamos_private from anon;
revoke all on all tables in schema eamos_private from authenticated;

grant select, insert, update, delete on eamos_private.clinical_mondo_diseases
to service_role;

grant select, insert, update, delete on eamos_private.clinical_hpo_terms
to service_role;

grant select, insert, update, delete on eamos_private.clinical_hpo_disease_phenotypes
to service_role;

grant select, insert, update, delete on eamos_private.clinical_hpo_gene_phenotypes
to service_role;

grant select, insert, update, delete on eamos_private.clinical_clingen_gene_validity
to service_role;

grant select, insert, update, delete on eamos_private.clinical_gencc_assertions
to service_role;

drop policy if exists "Deny browser roles on clinical MONDO diseases"
on eamos_private.clinical_mondo_diseases;

create policy "Deny browser roles on clinical MONDO diseases"
on eamos_private.clinical_mondo_diseases
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on clinical HPO terms"
on eamos_private.clinical_hpo_terms;

create policy "Deny browser roles on clinical HPO terms"
on eamos_private.clinical_hpo_terms
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on clinical HPO disease phenotypes"
on eamos_private.clinical_hpo_disease_phenotypes;

create policy "Deny browser roles on clinical HPO disease phenotypes"
on eamos_private.clinical_hpo_disease_phenotypes
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on clinical HPO gene phenotypes"
on eamos_private.clinical_hpo_gene_phenotypes;

create policy "Deny browser roles on clinical HPO gene phenotypes"
on eamos_private.clinical_hpo_gene_phenotypes
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on clinical ClinGen gene validity"
on eamos_private.clinical_clingen_gene_validity;

create policy "Deny browser roles on clinical ClinGen gene validity"
on eamos_private.clinical_clingen_gene_validity
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on clinical GenCC assertions"
on eamos_private.clinical_gencc_assertions;

create policy "Deny browser roles on clinical GenCC assertions"
on eamos_private.clinical_gencc_assertions
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

comment on table eamos_private.clinical_mondo_diseases is
    'Backend-only MONDO disease ontology rows with xrefs and provenance.';

comment on table eamos_private.clinical_hpo_terms is
    'Backend-only HPO term labels used to validate phenotype source rows.';

comment on table eamos_private.clinical_hpo_disease_phenotypes is
    'Backend-only HPO disease phenotype links.';

comment on table eamos_private.clinical_hpo_gene_phenotypes is
    'Backend-only HPO gene phenotype links.';

comment on table eamos_private.clinical_clingen_gene_validity is
    'Backend-only ClinGen gene-disease validity source rows.';

comment on table eamos_private.clinical_gencc_assertions is
    'Backend-only GenCC cross-lab gene-disease assertion source rows.';
