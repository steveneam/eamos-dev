-- ============================================================================
-- Eamos - Durable account-owned product workflow runs
-- ============================================================================
-- Scope: normalized lifecycle metadata and sanitized result rows for Batch,
-- Paper, and Workbench. Raw VCF/PDF/text/trace/sequence inputs are deliberately
-- absent from this schema and are rejected by the backend persistence adapter.
--
-- Browser roles may read and delete only their own durable records. Creation,
-- lifecycle updates, item replacement, expiry, and cancellation are performed
-- by the verified FastAPI service through service_role.
-- ============================================================================

create table if not exists public.product_workflow_run (
    run_id text not null,
    user_id uuid not null references auth.users(id) on delete cascade,
    owner_provider text not null,
    kind text not null,
    status text not null,
    owner_scope text not null default 'account',
    context jsonb not null default '{}'::jsonb,
    done integer not null default 0,
    total integer not null default 0,
    warnings jsonb not null default '[]'::jsonb,
    source_disclosures jsonb not null default '[]'::jsonb,
    processing_disclosure jsonb,
    artifacts jsonb not null default '[]'::jsonb,
    result_payload jsonb,
    n_input integer,
    n_to_lookup integer,
    n_after_filters integer,
    est_seconds double precision,
    created_at timestamp with time zone not null default timezone('utc'::text, now()),
    updated_at timestamp with time zone not null default timezone('utc'::text, now()),
    expires_at timestamp with time zone,
    primary key (run_id, user_id, owner_provider),
    constraint product_workflow_run_id_shape check (
        run_id ~ '^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$'
    ),
    constraint product_workflow_owner_provider_shape check (
        owner_provider ~ '^[A-Za-z0-9][A-Za-z0-9._~-]{0,31}$'
    ),
    constraint product_workflow_kind_allowed check (
        kind in ('batch', 'paper', 'workbench')
    ),
    constraint product_workflow_status_allowed check (
        status in (
            'draft', 'queued', 'running', 'completed', 'partial',
            'failed', 'cancelled', 'expired'
        )
    ),
    constraint product_workflow_owner_scope_allowed check (
        owner_scope in ('account', 'anonymous_session')
    ),
    constraint product_workflow_progress_nonnegative check (
        done >= 0 and total >= 0 and done <= total
    ),
    constraint product_workflow_metrics_nonnegative check (
        (n_input is null or n_input >= 0)
        and (n_to_lookup is null or n_to_lookup >= 0)
        and (n_after_filters is null or n_after_filters >= 0)
        and (est_seconds is null or est_seconds >= 0)
    ),
    constraint product_workflow_context_object check (jsonb_typeof(context) = 'object'),
    constraint product_workflow_warnings_array check (jsonb_typeof(warnings) = 'array'),
    constraint product_workflow_sources_array check (
        jsonb_typeof(source_disclosures) = 'array'
    ),
    constraint product_workflow_processing_object check (
        processing_disclosure is null
        or jsonb_typeof(processing_disclosure) = 'object'
    ),
    constraint product_workflow_artifacts_array check (jsonb_typeof(artifacts) = 'array'),
    constraint product_workflow_result_object check (
        result_payload is null or jsonb_typeof(result_payload) = 'object'
    ),
    constraint product_workflow_expiry_after_creation check (
        expires_at is null or expires_at > created_at
    )
);

create table if not exists public.product_workflow_item (
    run_id text not null,
    user_id uuid not null,
    owner_provider text not null,
    position integer not null,
    payload jsonb not null,
    primary key (run_id, user_id, owner_provider, position),
    constraint product_workflow_item_run_fk
        foreign key (run_id, user_id, owner_provider)
        references public.product_workflow_run(run_id, user_id, owner_provider)
        on delete cascade,
    constraint product_workflow_item_position_nonnegative check (position >= 0),
    constraint product_workflow_item_payload_object check (jsonb_typeof(payload) = 'object')
);

create index if not exists idx_product_workflow_run_owner_kind_updated
on public.product_workflow_run(
    user_id,
    owner_provider,
    kind,
    updated_at desc,
    run_id desc
);

create index if not exists idx_product_workflow_run_owner_updated
on public.product_workflow_run(
    user_id,
    owner_provider,
    updated_at desc,
    run_id desc
);

create index if not exists idx_product_workflow_run_expires
on public.product_workflow_run(expires_at)
where expires_at is not null;

create index if not exists idx_product_workflow_item_owner_run_position
on public.product_workflow_item(user_id, owner_provider, run_id, position);

alter table public.product_workflow_run enable row level security;
alter table public.product_workflow_run force row level security;
alter table public.product_workflow_item enable row level security;
alter table public.product_workflow_item force row level security;

revoke all on public.product_workflow_run from public, anon, authenticated;
revoke all on public.product_workflow_item from public, anon, authenticated;

grant usage on schema public to authenticated;
grant select, delete on public.product_workflow_run to authenticated;
grant select on public.product_workflow_item to authenticated;
grant select, insert, update, delete on public.product_workflow_run to service_role;
grant select, insert, update, delete on public.product_workflow_item to service_role;

drop policy if exists "Allow users to read their own product workflow runs"
on public.product_workflow_run;
drop policy if exists "Allow users to delete their own product workflow runs"
on public.product_workflow_run;
drop policy if exists "Allow users to read their own product workflow items"
on public.product_workflow_item;

create policy "Allow users to read their own product workflow runs"
on public.product_workflow_run
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "Allow users to delete their own product workflow runs"
on public.product_workflow_run
for delete
to authenticated
using ((select auth.uid()) = user_id);

create policy "Allow users to read their own product workflow items"
on public.product_workflow_item
for select
to authenticated
using ((select auth.uid()) = user_id);

comment on table public.product_workflow_run is
    'Account-owned normalized lifecycle metadata for Batch, Paper, and Workbench workflows; raw inputs are prohibited.';

comment on table public.product_workflow_item is
    'Owner-scoped sanitized paginated workflow result rows; raw inputs are prohibited.';
