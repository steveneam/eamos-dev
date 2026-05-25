-- ============================================================================
-- Eamos - Harden handle_new_user() (pin search_path, restrict EXECUTE)
-- ============================================================================
-- WHY: public.handle_new_user() is a SECURITY DEFINER trigger function (fired
--   by trigger on_auth_user_created on auth.users to seed public.profiles on
--   signup). A SECURITY DEFINER function without a fixed search_path is a
--   privilege-escalation risk (search_path injection) and is flagged by the
--   Supabase linter ("Function Search Path Mutable"). This pins search_path
--   and revokes EXECUTE from PUBLIC. Behaviour is unchanged (same INSERT).
--
-- SAFE TO RE-RUN: CREATE OR REPLACE + REVOKE are idempotent. Apply AFTER 0003.
-- How to apply: Supabase Dashboard -> SQL Editor -> paste -> Run.
-- ============================================================================

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
    insert into public.profiles (id, email, company_group)
    values (new.id, new.email, 'Independent Researcher');
    return new;
end;
$$;

revoke execute on function public.handle_new_user() from public;
