import type {
  CanonicalVariantRefV1,
  ClassificationTier,
  ConsequenceBucketV1,
  CuratedVariantPageV1,
  LookupResponse,
  RelatedVariantGroupV1,
} from './backend'
import { saveVariant, type SavedVariant } from './variant-library'
import { stashCompareVariants } from './variant-file'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''
const PAPER_TARGET_KEY = 'eamos.paper-target.v1'
const PAPER_TARGET_TTL_MS = 2 * 60 * 60 * 1000

export class ReportWorkflowError extends Error {
  constructor(public readonly code: 'unavailable' | 'invalid_response') {
    super(
      code === 'invalid_response'
        ? 'The server returned an invalid workflow response.'
        : 'This workflow data is temporarily unavailable.',
    )
    this.name = 'ReportWorkflowError'
  }
}

async function readJson<T>(response: Response, isValid: (value: unknown) => boolean): Promise<T> {
  if (!response.ok) throw new ReportWorkflowError('unavailable')
  const value: unknown = await response.json().catch(() => null)
  if (!isValid(value)) throw new ReportWorkflowError('invalid_response')
  return value as T
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export async function getRelatedVariants(
  input: { gene: string; cdna: string; transcript?: string | null },
  signal?: AbortSignal,
): Promise<RelatedVariantGroupV1> {
  const params = new URLSearchParams({ gene: input.gene, cdna: input.cdna })
  if (input.transcript) params.set('transcript', input.transcript)
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/lookup/related?${params.toString()}`, { signal })
    return await readJson<RelatedVariantGroupV1>(
      response,
      (value) => isObject(value) && Array.isArray(value.items) && Array.isArray(value.warnings),
    )
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    if (error instanceof ReportWorkflowError) throw error
    throw new ReportWorkflowError('unavailable')
  }
}

export async function getCuratedVariants(
  input: {
    gene: string
    classification: ClassificationTier
    consequence: ConsequenceBucketV1
    limit?: number
    cursor?: string | null
  },
  signal?: AbortSignal,
): Promise<CuratedVariantPageV1> {
  const params = new URLSearchParams({
    gene: input.gene,
    classification: input.classification,
    consequence: input.consequence,
    limit: String(Math.min(100, Math.max(1, input.limit ?? 20))),
  })
  if (input.cursor) params.set('cursor', input.cursor)
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/lookup/curated?${params.toString()}`, { signal })
    return await readJson<CuratedVariantPageV1>(
      response,
      (value) =>
        isObject(value) &&
        Array.isArray(value.items) &&
        typeof value.total === 'number' &&
        Array.isArray(value.warnings),
    )
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    if (error instanceof ReportWorkflowError) throw error
    throw new ReportWorkflowError('unavailable')
  }
}

export function canonicalVariantFromReport(data: LookupResponse): CanonicalVariantRefV1 | null {
  const payload = data.report_payload
  const header = payload.report_profile?.header
  const snapshot = payload.report_profile?.gene_context_snapshot
  const row = payload.variant_summary_rows[0]
  const gene = header?.gene ?? snapshot?.gene ?? row?.gene ?? null
  const transcriptHgvs = row?.transcript_hgvs ?? snapshot?.variant?.hgvs_c ?? null
  const cdna = header?.cdna ?? transcriptHgvs?.split(':').at(-1) ?? null
  const transcript =
    header?.transcript ??
    snapshot?.transcript ??
    (transcriptHgvs?.includes(':') ? transcriptHgvs.split(':')[0] : null)
  const genomic = header?.genomic_hg38 ?? row?.genomic_hg38 ?? snapshot?.variant?.genomic_hg38 ?? null
  if (!gene || !cdna) return null

  const auditKey = data.search_interpretation?.coordinate_resolution_audit?.canonical_variant_id ?? null
  const variantKey = auditKey ?? genomic ?? `${gene}:${transcript ?? ''}:${cdna}`.toLowerCase()
  const sourceSupport = auditKey
    ? ['coordinate_resolution_audit']
    : genomic
      ? ['report_lookup', 'genomic_hg38']
      : ['report_lookup']
  const warnings = auditKey || genomic ? [] : ['server_variant_key_unavailable']

  return {
    schema_version: 'canonical_variant_ref.v1',
    gene,
    cdna,
    transcript,
    protein_hgvs: header?.protein_change ?? row?.protein_change ?? snapshot?.variant?.hgvs_p ?? null,
    genomic_hg38: genomic,
    variant_key: variantKey,
    species: 'human',
    genome_build: 'GRCh38',
    resolution_status: genomic && transcript ? 'resolved' : genomic ? 'ambiguous' : 'unresolved',
    source_support: sourceSupport,
    warnings,
  }
}

export function canonicalVariantFromSaved(variant: SavedVariant): CanonicalVariantRefV1 | null {
  if (!variant.gene || !variant.variant) return null
  const transcript = variant.hgvs_full?.includes(':') ? variant.hgvs_full.split(':')[0] : null
  return {
    schema_version: 'canonical_variant_ref.v1',
    gene: variant.gene,
    cdna: variant.variant,
    transcript,
    protein_hgvs: null,
    genomic_hg38: null,
    variant_key: variant.id,
    species: 'human',
    genome_build: 'GRCh38',
    resolution_status: 'unresolved',
    source_support: ['library'],
    warnings: ['genomic_resolution_not_stored'],
  }
}

export function saveCanonicalVariant(
  variant: CanonicalVariantRefV1,
  classification?: ClassificationTier | null,
): boolean {
  return saveVariant(
    {
      gene: variant.gene,
      variant: variant.cdna,
      query: `${variant.gene} ${variant.cdna}`,
      raw: `${variant.gene} ${variant.cdna}`,
    },
    {
      classification: classification ?? undefined,
      hgvs_full: variant.transcript ? `${variant.transcript}:${variant.cdna}` : undefined,
    },
  )
}

export function sendCanonicalVariantToBatch(variant: CanonicalVariantRefV1, source: string): void {
  const query = `${variant.gene} ${variant.cdna}`
  stashCompareVariants(
    [{ gene: variant.gene, variant: variant.cdna, query, raw: query }],
    source,
  )
}

export interface PaperTargetEnvelope {
  schema_version: 'paper_target.v1'
  variant: CanonicalVariantRefV1
  expires_at: number
}

export function stashPaperTarget(variant: CanonicalVariantRefV1): void {
  if (typeof window === 'undefined') return
  const envelope: PaperTargetEnvelope = {
    schema_version: 'paper_target.v1',
    variant,
    expires_at: Date.now() + PAPER_TARGET_TTL_MS,
  }
  try {
    window.sessionStorage.setItem(PAPER_TARGET_KEY, JSON.stringify(envelope))
  } catch {
    // The Paper surface remains usable without browser session storage.
  }
}

export function readPaperTarget(): PaperTargetEnvelope | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(PAPER_TARGET_KEY)
    if (!raw) return null
    const value: unknown = JSON.parse(raw)
    if (!isObject(value) || value.schema_version !== 'paper_target.v1' || !isObject(value.variant)) return null
    if (typeof value.expires_at !== 'number' || value.expires_at <= Date.now()) {
      window.sessionStorage.removeItem(PAPER_TARGET_KEY)
      return null
    }
    const variant = value.variant
    if (
      variant.schema_version !== 'canonical_variant_ref.v1' ||
      typeof variant.gene !== 'string' ||
      typeof variant.cdna !== 'string' ||
      typeof variant.variant_key !== 'string'
    ) {
      return null
    }
    return value as unknown as PaperTargetEnvelope
  } catch {
    return null
  }
}

export function clearPaperTarget(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(PAPER_TARGET_KEY)
  } catch {
    // Nothing else to clear.
  }
}
