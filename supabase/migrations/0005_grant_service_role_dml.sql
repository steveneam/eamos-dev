-- ============================================================================
-- Eamos - Grant service_role table-level DML on the app tables
-- ============================================================================
-- WHY: service_role is the trusted backend role and bypasses Row Level
--   Security, but RLS-bypass does NOT include table GRANTS. 0002 granted
--   privileges to `authenticated` (and `anon` got none) but never granted
--   `service_role`, so it only had REFERENCES/TRIGGER/TRUNCATE. The backend
--   evidence write-through uses the service_role key, so every insert into
--   user_evidence_submissions was rejected by Postgres with "permission
--   denied for table" -> surfaced as HTTP 403 -> the API returned 503
--   "Evidence submission ledger write failed." This grants service_role the
--   DML it needs on all three app tables.
--
-- SAFE TO RE-RUN: GRANT is idempotent. Takes effect immediately (no redeploy).
-- How to apply: Supabase Dashboard -> SQL Editor -> paste -> Run. Apply AFTER 0004.
-- ============================================================================

grant select, insert, update, delete on public.user_evidence_submissions to service_role;
grant select, insert, update, delete on public.profiles to service_role;
grant select, insert, update, delete on public.saved_variants to service_role;
