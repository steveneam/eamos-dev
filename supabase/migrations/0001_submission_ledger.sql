-- ============================================================================
-- Eamos — Variant Submission Context Ledger (the "Messenger Feature")
-- ============================================================================
-- Source of truth: the user's design doc
--   "Supabase Database Architecture - Variant Submission Context Ledger".
-- Scope: this database holds ONLY user/submission metadata. It does NOT hold
--   genomic reference tracks (gnomAD / SpliceAI / ClinVar) — those stay live via
--   the FastAPI backend's public-API orchestration.
--
-- How to apply (pick one):
--   A) Supabase Dashboard → SQL Editor → paste this file → Run.
--   B) Supabase CLI:  supabase db push   (after `supabase link`).
--
-- Prereq dashboard toggles (per the architecture doc, Database Access Guardrails):
--   • Data API: ON       • Auto-expose new tables: OFF
--   • Automatic RLS: ON   • Region: ap-southeast-2 (Sydney)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. PROFILES — isolates submission origins via Supabase Auth
-- ----------------------------------------------------------------------------
CREATE TABLE public.profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT NOT NULL,
    company_group TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Auto-create a profile row on signup.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, company_group)
    VALUES (new.id, new.email, 'Independent Researcher');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ----------------------------------------------------------------------------
-- 2. SAVED VARIANTS — bookmarks tracked for reclassification review
-- ----------------------------------------------------------------------------
CREATE TABLE public.saved_variants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    variant_hgvs TEXT NOT NULL,
    custom_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX idx_saved_variants_user ON public.saved_variants(user_id);
CREATE INDEX idx_saved_variants_hgvs ON public.saved_variants(variant_hgvs);

-- ----------------------------------------------------------------------------
-- 3. SUBMISSION LEDGER — immutable audit trail of Messenger API actions
-- ----------------------------------------------------------------------------
CREATE TABLE public.user_evidence_submissions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    variant_hgvs TEXT NOT NULL,                          -- e.g. NM_000257.4:c.1208G>A
    submitted_pmid TEXT NOT NULL,                        -- PMID supporting PS3/BS3
    curator_notes TEXT,                                  -- rationale paragraph
    clinvar_tracking_id TEXT DEFAULT 'PENDING' NOT NULL, -- external transaction ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE INDEX idx_submissions_user ON public.user_evidence_submissions(user_id);
CREATE INDEX idx_submissions_hgvs ON public.user_evidence_submissions(variant_hgvs);

-- ----------------------------------------------------------------------------
-- 4. ROW LEVEL SECURITY — multi-tenant isolation (users see only their own rows)
-- ----------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_evidence_submissions ENABLE ROW LEVEL SECURITY;

-- Profiles
CREATE POLICY "Allow users to view their own profile metadata"
ON public.profiles FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Allow users to modify their own profile data fields"
ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Saved variants
CREATE POLICY "Allow users to save variants to their tracking queue"
ON public.saved_variants FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow users to retrieve their monitored variants"
ON public.saved_variants FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Allow users to clear monitored variants"
ON public.saved_variants FOR DELETE USING (auth.uid() = user_id);

-- Submission ledger
CREATE POLICY "Allow users to write to the submission log context"
ON public.user_evidence_submissions FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow users to audit their unique transaction history"
ON public.user_evidence_submissions FOR SELECT USING (auth.uid() = user_id);
