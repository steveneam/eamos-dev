-- ============================================================================
-- Eamos - Supabase advisor cleanup + service_role default privileges
-- ============================================================================
-- WHY (1): the security advisor flagged public.rls_auto_enable() as a
--   SECURITY DEFINER function callable by anon/authenticated via /rest/v1/rpc.
--   It is an internal admin helper, not an end-user RPC, so revoke external
--   EXECUTE (the owner/postgres retains EXECUTE). Codex-recommended minimal fix;
--   deliberately NOT switching to SECURITY INVOKER (would change the effective
--   role the trigger/function runs under).
--
-- WHY (2): the 0002/0005 grant gap (service_role lacked table DML) happened
--   because default privileges did not cover service_role. Set default
--   privileges so future public tables/sequences auto-grant the trusted backend
--   service_role role and the gap can't recur. Affects objects created AFTER
--   this runs by the executing role.
--
-- SAFE TO RE-RUN: REVOKE + ALTER DEFAULT PRIVILEGES are idempotent. Apply AFTER 0005.
-- How to apply: Supabase Dashboard -> SQL Editor -> paste -> Run.
-- ============================================================================

revoke execute on function public.rls_auto_enable() from public, anon, authenticated;

alter default privileges in schema public
  grant select, insert, update, delete on tables to service_role;
alter default privileges in schema public
  grant usage, select, update on sequences to service_role;
