-- ============================================================================
-- Eamos - Private cache advisor hardening
-- ============================================================================
-- Scope: make the private cache tables explicit to Supabase advisors:
-- browser roles have deny-all policies, service_role remains the only granted
-- backend role, and new private foreign keys have covering indexes.
-- ============================================================================

create index if not exists idx_protein_annotation_jobs_user_id
on eamos_private.protein_annotation_jobs(user_id);

create index if not exists idx_local_model_jobs_result_cache_id
on eamos_private.local_model_jobs(result_cache_id);

drop policy if exists "Deny browser roles on protein annotation source versions"
on eamos_private.protein_annotation_source_versions;

create policy "Deny browser roles on protein annotation source versions"
on eamos_private.protein_annotation_source_versions
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on protein annotation jobs"
on eamos_private.protein_annotation_jobs;

create policy "Deny browser roles on protein annotation jobs"
on eamos_private.protein_annotation_jobs
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on protein annotation cache"
on eamos_private.protein_annotation_cache;

create policy "Deny browser roles on protein annotation cache"
on eamos_private.protein_annotation_cache
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on local source versions"
on eamos_private.local_source_versions;

create policy "Deny browser roles on local source versions"
on eamos_private.local_source_versions
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on local model cache entries"
on eamos_private.local_model_cache_entries;

create policy "Deny browser roles on local model cache entries"
on eamos_private.local_model_cache_entries
as restrictive
for all
to anon, authenticated
using (false)
with check (false);

drop policy if exists "Deny browser roles on local model jobs"
on eamos_private.local_model_jobs;

create policy "Deny browser roles on local model jobs"
on eamos_private.local_model_jobs
as restrictive
for all
to anon, authenticated
using (false)
with check (false);
