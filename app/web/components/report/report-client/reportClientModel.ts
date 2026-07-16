import type { Verdict } from '@/components/ui/Card'
import type {
  LookupRequest,
  LookupResponse,
  LookupSectionId,
  SearchInputInterpretation,
} from '@/lib/backend'
import { REPORT_LAZY_SECTION_IDS } from '@/lib/report-section-registry'
import { cleanQuery } from '@/lib/variant-format'

const LAZY_OVERRIDE_VALID_IDS: readonly LookupSectionId[] = REPORT_LAZY_SECTION_IDS
const REPORT_CACHE_PREFIX = 'eamos.report.lookup.v1:'
const REPORT_CACHE_MAX_AGE_MS = 30 * 60 * 1000

export const LIVE_SAMPLE_REPORT_HREF = '/report?gene=USH2A&cdna=c.2276G%3ET'

export type ReportLoadState =
  | { kind: 'idle' }
  | { kind: 'loading'; requestKey: string }
  | { kind: 'ready'; requestKey: string; data: LookupResponse }
  | { kind: 'malformed'; requestKey: string; query: string; detail?: string }
  | { kind: 'unresolved'; requestKey: string; query: string }
  | {
      kind: 'interpretation'
      requestKey: string
      query: string
      interpretation: SearchInputInterpretation
      detail?: string | null
    }
  | { kind: 'error'; requestKey: string; message: string }
  | { kind: 'offline'; requestKey: string }

export interface ReportQueryInput {
  cdna: string
  demo: boolean
  fixture: boolean
  gene: string
  proteinChange: string
  q: string
  transcript: string
}

export function parseLazyOverrides(raw: string | null): Set<LookupSectionId> {
  const out = new Set<LookupSectionId>()
  if (!raw) return out
  for (const token of raw.split(',').map((value) => value.trim()).filter(Boolean)) {
    if ((LAZY_OVERRIDE_VALID_IDS as readonly string[]).includes(token)) {
      out.add(token as LookupSectionId)
    }
  }
  return out
}

export function reportRequestKey({
  cdna,
  demo,
  fixture,
  gene,
  proteinChange,
  q,
  transcript,
}: ReportQueryInput): string {
  if (fixture) return 'fixture:rpe65-negative'
  if (demo) return 'demo:live-redirect'
  if (!gene && !cdna && q) return `q:${q}`
  if (gene || cdna) {
    return ['lookup', gene.toUpperCase(), cleanQuery(cdna), transcript, proteinChange].join('|')
  }
  return 'empty'
}

export function reportSummaryRequest({
  cdna,
  demo,
  fixture,
  gene,
  proteinChange,
  q,
  transcript,
}: ReportQueryInput): LookupRequest | undefined {
  if (demo || fixture) return undefined
  if (!gene && !cdna && q) {
    return { search_text: q, species: 'human' }
  }
  if (gene && cdna) {
    return {
      gene,
      cdna: cleanQuery(cdna),
      transcript: transcript || null,
      protein_change: proteinChange || null,
      species: 'human',
    }
  }
  return undefined
}

export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

export function readCachedReport(requestKey: string): LookupResponse | null {
  if (
    typeof window === 'undefined' ||
    requestKey === 'empty' ||
    requestKey.startsWith('demo:') ||
    requestKey.startsWith('fixture:')
  ) {
    return null
  }
  const key = `${REPORT_CACHE_PREFIX}${requestKey}`
  try {
    const raw = window.sessionStorage.getItem(key)
    if (!raw) return null
    const cached = JSON.parse(raw) as { savedAt?: unknown; data?: unknown }
    if (typeof cached.savedAt !== 'number' || !cached.data) {
      window.sessionStorage.removeItem(key)
      return null
    }
    if (Date.now() - cached.savedAt > REPORT_CACHE_MAX_AGE_MS) {
      window.sessionStorage.removeItem(key)
      return null
    }
    return cached.data as LookupResponse
  } catch {
    try {
      window.sessionStorage.removeItem(key)
    } catch {
      // Ignore storage APIs that are unavailable in private contexts.
    }
    return null
  }
}

export function writeCachedReport(requestKey: string, data: LookupResponse): void {
  if (
    typeof window === 'undefined' ||
    requestKey === 'empty' ||
    requestKey.startsWith('demo:') ||
    requestKey.startsWith('fixture:')
  ) {
    return
  }
  try {
    window.sessionStorage.setItem(
      `${REPORT_CACHE_PREFIX}${requestKey}`,
      JSON.stringify({ savedAt: Date.now(), data }),
    )
  } catch {
    // Quota/private-mode failures should never block rendering the report.
  }
}

export function reportViewQueryId(data: LookupResponse, query: string): string | null {
  const payload = data.report_payload
  const header = payload.report_profile?.header
  const row0 = payload.variant_summary_rows[0]
  const gene = header?.gene ?? row0?.gene ?? null
  const transcriptHgvs = row0?.transcript_hgvs ?? null
  const cdna = header?.cdna ?? transcriptHgvs?.split(':').pop() ?? null
  if (!gene || !cdna) return null
  return `${gene} ${cdna}`.trim() || query.trim() || data.query
}

export function deriveClassificationVerdict(
  acmg: string | null | undefined,
): Verdict | null {
  if (!acmg) return null
  const raw = acmg.toLowerCase()
  if (raw.includes('unavailable') || raw.includes('not found')) return null
  if (raw.includes('likely pathogenic')) return 'Likely pathogenic'
  if (raw.includes('likely benign')) return 'Likely benign'
  if (raw.includes('pathogenic')) return 'Pathogenic'
  if (raw.includes('benign')) return 'Benign'
  if (raw.includes('vus') || raw.includes('uncertain')) return 'VUS'
  return null
}
