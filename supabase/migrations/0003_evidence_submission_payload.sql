-- ============================================================================
-- Eamos - Add backend evidence-submission payload storage
-- ============================================================================
-- WHY: the frontend ledger already reads the core Messenger columns from
--   user_evidence_submissions. The backend evidence endpoint now produces
--   richer PubMed validation and ClinVar draft payloads. Keep existing reads
--   stable by adding one additive JSONB column instead of reshaping the table.
--
-- SAFE TO RE-RUN: ADD COLUMN IF NOT EXISTS is idempotent.
--
-- How to apply: Supabase Dashboard -> SQL Editor -> paste -> Run
--   (or `supabase db push` after `supabase link`). Apply AFTER 0002.
-- ============================================================================

ALTER TABLE public.user_evidence_submissions
ADD COLUMN IF NOT EXISTS submission_payload JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.user_evidence_submissions.submission_payload IS
    'Backend-generated evidence submission details: PubMed validation, ClinVar draft, payload status, optional curator fields, and warnings.';
