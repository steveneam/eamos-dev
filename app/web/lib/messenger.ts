import { createClient } from '@/utils/supabase/client'

// Data helpers for the "Messenger" submission ledger + saved-variant tracking.
// These map 1:1 to supabase/migrations/0001_submission_ledger.sql. RLS scopes
// every row to auth.uid(); inserts must set user_id to the signed-in user.
//
// NOTE: until supabase/migrations/0002_grant_authenticated.sql is applied the
// `authenticated` role has no table grants, so these calls return a
// permission-denied error — the UI surfaces that gracefully rather than crashing.
//
// Evidence submissions are written directly to the ledger here (mock-first). When
// Codex's evidence-submission backend lands (HGVS+PMID validation → ClinVar
// payload → tracking id), addSubmission() should POST to that endpoint instead.

export interface SavedVariant {
  id: string
  variant_hgvs: string
  custom_notes: string | null
  created_at: string
}

export interface EvidenceSubmission {
  id: string
  variant_hgvs: string
  submitted_pmid: string
  curator_notes: string | null
  clinvar_tracking_id: string
  created_at: string
}

export async function listSavedVariants(): Promise<SavedVariant[]> {
  const { data, error } = await createClient()
    .from('saved_variants')
    .select('id, variant_hgvs, custom_notes, created_at')
    .order('created_at', { ascending: false })
  if (error) throw new Error(error.message)
  return data ?? []
}

export async function addSavedVariant(userId: string, hgvs: string, notes: string): Promise<void> {
  const { error } = await createClient()
    .from('saved_variants')
    .insert({ user_id: userId, variant_hgvs: hgvs, custom_notes: notes || null })
  if (error) throw new Error(error.message)
}

export async function deleteSavedVariant(id: string): Promise<void> {
  const { error } = await createClient().from('saved_variants').delete().eq('id', id)
  if (error) throw new Error(error.message)
}

export async function listSubmissions(): Promise<EvidenceSubmission[]> {
  const { data, error } = await createClient()
    .from('user_evidence_submissions')
    .select('id, variant_hgvs, submitted_pmid, curator_notes, clinvar_tracking_id, created_at')
    .order('created_at', { ascending: false })
  if (error) throw new Error(error.message)
  return data ?? []
}

export async function addSubmission(
  userId: string,
  input: { variant_hgvs: string; submitted_pmid: string; curator_notes: string },
): Promise<void> {
  const { error } = await createClient().from('user_evidence_submissions').insert({
    user_id: userId,
    variant_hgvs: input.variant_hgvs,
    submitted_pmid: input.submitted_pmid,
    curator_notes: input.curator_notes || null,
  })
  if (error) throw new Error(error.message)
}
