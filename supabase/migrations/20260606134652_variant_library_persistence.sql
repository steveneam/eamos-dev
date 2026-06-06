-- ============================================================================
-- Eamos - Durable variant library persistence
-- ============================================================================
-- Scope: per-account saved variant worklist/folders for the Phase 3+4
-- variant-library rail, plus an aggregate popularity counter for the future
-- "Frequently reviewed" related-variants lane.
--
-- Guardrails:
-- - collection and saved_variant are user-owned via RLS.
-- - variant_view_count is aggregate-only: public read, backend/service_role
--   writes through a narrowly granted RPC.
-- - The legacy public.saved_variants bookmark table is left untouched.
-- ============================================================================

create table if not exists public.collection (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    constraint collection_name_present check (length(trim(name)) > 0)
);

create unique index if not exists idx_collection_user_name_lower
on public.collection(user_id, lower(name));

create index if not exists idx_collection_user_created
on public.collection(user_id, created_at);

create table if not exists public.saved_variant (
    id text not null,
    user_id uuid not null references auth.users(id) on delete cascade,
    gene text,
    variant text,
    query text not null,
    raw text not null default '',
    folder_id uuid references public.collection(id) on delete set null,
    saved_at bigint not null,
    classification text,
    hgvs_full text,
    primary key (id, user_id),
    constraint saved_variant_id_present check (length(trim(id)) > 0),
    constraint saved_variant_query_present check (length(trim(query)) > 0),
    constraint saved_variant_saved_at_valid check (saved_at >= 0),
    constraint saved_variant_classification_valid check (
        classification is null
        or classification in (
            'pathogenic',
            'likely_pathogenic',
            'vus',
            'likely_benign',
            'benign'
        )
    )
);

create index if not exists idx_saved_variant_user_saved
on public.saved_variant(user_id, saved_at desc);

create index if not exists idx_saved_variant_user_folder
on public.saved_variant(user_id, folder_id);

create index if not exists idx_saved_variant_query
on public.saved_variant(id);

create table if not exists public.variant_view_count (
    query_id text primary key,
    view_count bigint not null default 0,
    last_viewed timestamp with time zone not null default timezone('utc'::text, now()),
    constraint variant_view_count_query_present check (length(trim(query_id)) > 0),
    constraint variant_view_count_nonnegative check (view_count >= 0)
);

create index if not exists idx_variant_view_count_popular
on public.variant_view_count(view_count desc, last_viewed desc);

alter table public.collection enable row level security;
alter table public.saved_variant enable row level security;
alter table public.variant_view_count enable row level security;

revoke all on public.collection from public, anon, authenticated;
revoke all on public.saved_variant from public, anon, authenticated;
revoke all on public.variant_view_count from public, anon, authenticated;

grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on public.collection to authenticated;
grant select, insert, update, delete on public.saved_variant to authenticated;
grant select on public.variant_view_count to anon, authenticated;

grant select, insert, update, delete on public.collection to service_role;
grant select, insert, update, delete on public.saved_variant to service_role;
grant select, insert, update, delete on public.variant_view_count to service_role;

drop policy if exists "Allow users to manage their own library folders"
on public.collection;

create policy "Allow users to manage their own library folders"
on public.collection
for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Allow users to manage their own saved variants"
on public.saved_variant;

create policy "Allow users to manage their own saved variants"
on public.saved_variant
for all
to authenticated
using ((select auth.uid()) = user_id)
with check (
    (select auth.uid()) = user_id
    and (
        folder_id is null
        or exists (
            select 1
            from public.collection c
            where c.id = folder_id
              and c.user_id = (select auth.uid())
        )
    )
);

drop policy if exists "Allow public read aggregate variant view counts"
on public.variant_view_count;

create policy "Allow public read aggregate variant view counts"
on public.variant_view_count
for select
to anon, authenticated
using (view_count >= 0);

create or replace function public.increment_variant_view_count(p_query_id text)
returns table(query_id text, view_count bigint, last_viewed timestamp with time zone)
language sql
set search_path = public
as $$
    insert into public.variant_view_count as vc (query_id, view_count, last_viewed)
    select lower(trim(p_query_id)), 1, timezone('utc'::text, now())
    where length(trim(p_query_id)) > 0
    on conflict (query_id) do update
    set view_count = vc.view_count + 1,
        last_viewed = excluded.last_viewed
    returning vc.query_id, vc.view_count, vc.last_viewed;
$$;

revoke execute on function public.increment_variant_view_count(text)
from public, anon, authenticated;

grant execute on function public.increment_variant_view_count(text)
to service_role;

comment on table public.collection is
    'User-owned folders for the Eamos variant library rail.';

comment on table public.saved_variant is
    'User-owned saved variants using query.toLowerCase() as the per-user dedupe key.';

comment on table public.variant_view_count is
    'Aggregate variant review popularity counts; contains no per-user rows.';
