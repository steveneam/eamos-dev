import { createClient } from '@/utils/supabase/client'

// Data helpers for the "Messenger" submission ledger + saved-variant tracking.
// These map 1:1 to supabase/migrations/0001_submission_ledger.sql. RLS scopes
// every row to auth.uid(); inserts must set user_id to the signed-in user.
//
// NOTE: until supabase/migrations/0002_grant_authenticated.sql is applied the
// `authenticated` role has no table grants, so these calls return a
// permission-denied error — the UI surfaces that gracefully rather than crashing.
//
// Evidence submissions have two persistence paths:
//   • flag OFF (default): written directly to the Supabase ledger (stable
//     columns only) — mock-first; tracking id stays PENDING.
//   • flag ON (NEXT_PUBLIC_EVIDENCE_API_ENABLED=true): POSTed to Codex's
//     `POST /api/v1/evidence-submissions`, which validates HGVS+PMID, builds the
//     draft ClinVar payload + a real EAMOS-EVS-… tracking id, and (when its
//     Supabase write-through env is set) records the row so listSubmissions()
//     reflects it. Keep OFF until Steven confirms Supabase migration 0003 +
//     Render env (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_JWT_SECRET).
//
// Contract source of truth: plans/auth-pricing/backend-contracts.md. The
// EvidenceSubmission* request/response types below are a local mirror of that
// contract; promote them into app/web/lib/backend.ts (backend-led, under a
// Shared File Lock) at integration.

/** Live API path on/off. Default OFF → current mock-first direct-Supabase write. */
export const EVIDENCE_API_ENABLED = process.env.NEXT_PUBLIC_EVIDENCE_API_ENABLED === 'true'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

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

// ── Evidence-submission API contract mirror (plans/auth-pricing/backend-contracts.md) ──
export type CollectionMethod = 'in vivo' | 'in vitro'
export type FunctionalEffect =
  | 'functionally abnormal'
  | 'function uncertain'
  | 'functionally normal'
export type EvidenceCode = 'PS3' | 'BS3' | 'PS3_Supporting' | 'BS3_Supporting' | 'Other'

export interface EvidenceSubmissionInput {
  variant_hgvs: string
  submitted_pmid: string
  curator_notes?: string
  // Optional ClinVar functional-data fields. Present-ness of the required set
  // (see REQUIRED_DRY_RUN_FIELDS) is what flips the backend payload_status from
  // "draft_needs_curator_fields" to "ready_for_clinvar_dry_run".
  condition_name?: string
  assay_type?: string
  collection_method?: CollectionMethod
  functional_effect?: FunctionalEffect
  functional_consequence?: string[]
  method?: string
  result?: string
  evidence_codes?: EvidenceCode[]
}

export interface EvidenceSubmissionResponse {
  pubmed?: { status?: string; warning?: string | null }
  clinvar_tracking_id: string
  clinvar_payload?: unknown
  payload_status: 'ready_for_clinvar_dry_run' | 'draft_needs_curator_fields'
  ledger_status?: string
}

/** Result surfaced to the UI regardless of which persistence path ran. */
export interface SubmitEvidenceResult {
  trackingId: string
  /** null in the flag-off path (no backend payload built). */
  payloadStatus: EvidenceSubmissionResponse['payload_status'] | null
}

/** Fields the backend requires before payload_status = ready_for_clinvar_dry_run. */
export const REQUIRED_DRY_RUN_FIELDS = [
  'condition_name',
  'assay_type',
  'method',
  'result',
  'functional_consequence',
] as const

export interface ClinvarReadiness {
  ready: boolean
  /** Human labels for the still-missing required fields. */
  missing: string[]
}

const FIELD_LABELS: Record<(typeof REQUIRED_DRY_RUN_FIELDS)[number], string> = {
  condition_name: 'Condition',
  assay_type: 'Assay type',
  method: 'Method',
  result: 'Result',
  functional_consequence: 'Functional consequence',
}

/** Client-side mirror of the backend's ready_for_clinvar_dry_run gate. */
export function clinvarReadiness(input: EvidenceSubmissionInput): ClinvarReadiness {
  const missing = REQUIRED_DRY_RUN_FIELDS.filter((field) => {
    const value = input[field]
    return Array.isArray(value) ? value.length === 0 : !String(value ?? '').trim()
  }).map((field) => FIELD_LABELS[field])
  return { ready: missing.length === 0, missing }
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

/**
 * Record an evidence submission. Branches on EVIDENCE_API_ENABLED:
 *   • OFF → direct Supabase insert (stable columns), tracking id PENDING.
 *   • ON  → POST to the backend with the Supabase bearer token (no user_id;
 *           the backend derives it from the JWT sub), returning the real
 *           EAMOS-EVS-… id + payload_status.
 */
export async function submitEvidence(
  userId: string,
  input: EvidenceSubmissionInput,
): Promise<SubmitEvidenceResult> {
  if (!EVIDENCE_API_ENABLED) {
    const { error } = await createClient().from('user_evidence_submissions').insert({
      user_id: userId,
      variant_hgvs: input.variant_hgvs,
      submitted_pmid: input.submitted_pmid,
      curator_notes: input.curator_notes || null,
    })
    if (error) throw new Error(error.message)
    return { trackingId: 'PENDING', payloadStatus: null }
  }

  const { data, error: sessionError } = await createClient().auth.getSession()
  const accessToken = data.session?.access_token
  if (sessionError || !accessToken) {
    throw new Error('Your session expired — sign in again to submit evidence.')
  }

  // Send only the populated fields. Crucially, never send user_id: the backend
  // derives the owner from the bearer token's JWT sub.
  const body: Record<string, unknown> = {
    variant_hgvs: input.variant_hgvs,
    submitted_pmid: input.submitted_pmid,
  }
  if (input.curator_notes?.trim()) body.curator_notes = input.curator_notes.trim()
  if (input.condition_name?.trim()) body.condition_name = input.condition_name.trim()
  if (input.assay_type?.trim()) body.assay_type = input.assay_type.trim()
  if (input.collection_method) body.collection_method = input.collection_method
  if (input.functional_effect) body.functional_effect = input.functional_effect
  if (input.functional_consequence?.length) body.functional_consequence = input.functional_consequence
  if (input.method?.trim()) body.method = input.method.trim()
  if (input.result?.trim()) body.result = input.result.trim()
  if (input.evidence_codes?.length) body.evidence_codes = input.evidence_codes

  const response = await fetch(`${API_BASE_URL}/api/v1/evidence-submissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Submission failed with status ${response.status}`)
  }
  const result = (await response.json()) as EvidenceSubmissionResponse
  return { trackingId: result.clinvar_tracking_id, payloadStatus: result.payload_status }
}
