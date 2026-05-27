-- ============================================================================
-- Eamos - Optimize RLS auth.uid() predicates for Supabase advisors
-- ============================================================================
-- LOCAL ONLY: this migration is drafted for later application via the Supabase
-- Dashboard SQL Editor or Supabase CLI. It was not applied to any live
-- Supabase project as part of this task.
--
-- WHY: Supabase performance advisor lint 0003_auth_rls_initplan warns when
--   auth helper calls inside RLS policies are evaluated once per scanned row.
--   Wrapping auth.uid() as (select auth.uid()) lets Postgres evaluate it once
--   as an initPlan while preserving the same ownership checks.
--
-- SCOPE: Recreate the seven RLS policies originally created in 0001 with the
--   same policy names, tables, commands, and default role scope. Only direct
--   auth.uid() predicates are changed to (select auth.uid()).
--
-- SAFE TO RE-RUN: DROP POLICY IF EXISTS + CREATE POLICY leaves the same target
--   policy definitions. Apply AFTER 0006.
-- ============================================================================

-- Profiles
drop policy if exists "Allow users to view their own profile metadata"
on public.profiles;

create policy "Allow users to view their own profile metadata"
on public.profiles for select
using ((select auth.uid()) = id);

drop policy if exists "Allow users to modify their own profile data fields"
on public.profiles;

create policy "Allow users to modify their own profile data fields"
on public.profiles for update
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

-- Saved variants
drop policy if exists "Allow users to save variants to their tracking queue"
on public.saved_variants;

create policy "Allow users to save variants to their tracking queue"
on public.saved_variants for insert
with check ((select auth.uid()) = user_id);

drop policy if exists "Allow users to retrieve their monitored variants"
on public.saved_variants;

create policy "Allow users to retrieve their monitored variants"
on public.saved_variants for select
using ((select auth.uid()) = user_id);

drop policy if exists "Allow users to clear monitored variants"
on public.saved_variants;

create policy "Allow users to clear monitored variants"
on public.saved_variants for delete
using ((select auth.uid()) = user_id);

-- Submission ledger
drop policy if exists "Allow users to write to the submission log context"
on public.user_evidence_submissions;

create policy "Allow users to write to the submission log context"
on public.user_evidence_submissions for insert
with check ((select auth.uid()) = user_id);

drop policy if exists "Allow users to audit their unique transaction history"
on public.user_evidence_submissions;

create policy "Allow users to audit their unique transaction history"
on public.user_evidence_submissions for select
using ((select auth.uid()) = user_id);
