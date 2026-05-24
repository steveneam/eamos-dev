-- ============================================================================
-- Eamos — Grant the `authenticated` role access to its own rows
-- ============================================================================
-- WHY: migration 0001 enables Row Level Security and writes the per-row policies,
--   but RLS only *filters* rows a role can already touch. With no table GRANT, the
--   `authenticated` role has zero privileges, so even a signed-in user gets
--   "permission denied for table ...". This migration is the deliberate
--   "expose to logged-in users" step — it grants table privileges to
--   `authenticated` only; the RLS policies from 0001 still restrict every
--   statement to rows where auth.uid() = user_id (or id, for profiles).
--   `anon` is intentionally NOT granted anything — logged-out users see nothing.
--
-- SAFE TO RE-RUN: GRANT is idempotent.
--
-- How to apply: Supabase Dashboard → SQL Editor → paste → Run
--   (or `supabase db push` after `supabase link`). Apply AFTER 0001.
-- ============================================================================

-- Schema usage (usually already present for authenticated in Supabase; explicit
-- here so the migration is self-contained).
GRANT USAGE ON SCHEMA public TO authenticated;

-- Profiles: view + update own row only (RLS policies in 0001 enforce auth.uid()=id).
-- No INSERT grant needed — handle_new_user() runs SECURITY DEFINER on signup.
-- No DELETE — profile lifecycle follows auth.users via ON DELETE CASCADE.
GRANT SELECT, UPDATE ON public.profiles TO authenticated;

-- Saved variants: read / add / clear own bookmarks.
GRANT SELECT, INSERT, DELETE ON public.saved_variants TO authenticated;

-- Submission ledger: read own audit trail + write new submissions.
-- No UPDATE/DELETE — the ledger is an immutable audit trail by design.
GRANT SELECT, INSERT ON public.user_evidence_submissions TO authenticated;
