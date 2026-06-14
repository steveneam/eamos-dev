-- ============================================================================
-- Eamos - Account-synced whole-document variant library
-- ============================================================================
-- Scope: v1 sync contract for the shared FE library store:
--   { variants, folders, updated_at }
--
-- Guardrails:
-- - One row per authenticated user.
-- - Browser clients can only read/write their own row through RLS.
-- - Backend service_role retains DML access for the FastAPI mirror route.
-- - Existing normalized collection/saved_variant tables remain for legacy
--   granular endpoints and popularity metrics.
-- ============================================================================

create table if not exists public.user_library (
    user_id uuid primary key references auth.users(id) on delete cascade,
    variants jsonb not null default '[]'::jsonb,
    folders jsonb not null default '[]'::jsonb,
    updated_at timestamp with time zone not null default timezone('utc'::text, now()),
    constraint user_library_variants_array check (jsonb_typeof(variants) = 'array'),
    constraint user_library_folders_array check (jsonb_typeof(folders) = 'array')
);

create index if not exists idx_user_library_updated_at
on public.user_library(updated_at desc);

alter table public.user_library enable row level security;

revoke all on public.user_library from public, anon, authenticated;

grant usage on schema public to authenticated;
grant select, insert, update, delete on public.user_library to authenticated;
grant select, insert, update, delete on public.user_library to service_role;

drop policy if exists "Allow users to manage their own library document"
on public.user_library;

create policy "Allow users to manage their own library document"
on public.user_library
for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

comment on table public.user_library is
    'One-row-per-user JSONB mirror of the Eamos variant library local store.';
