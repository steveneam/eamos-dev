import type {
  LovdBasicObservation,
  LovdBasicRecordsSection,
  LovdInstallationSource,
  SourcePolicyAction,
  SourcePolicyDecision,
} from '@/lib/backend'

const SOURCE_ID = 'lovd_global_variome_shared_fixture' as const
const INSTALLATION_ID = 'global_variome_shared_lovd' as const
const BASE_URL = 'https://databases.lovd.nl/shared' as const
export const LOVD_PRESENCE_NOTICE =
  'Matching LOVD basic record; presence is not a classification.'
const POLICY_EXPECTATIONS = new Map<
  SourcePolicyAction,
  { outcome: 'allowed' | 'denied'; reason: string }
>([
  ['acquire', { outcome: 'denied', reason: 'acquisition_not_approved' }],
  ['normalize', { outcome: 'allowed', reason: 'allowed_by_source_allowlist' }],
  ['public_serialize', { outcome: 'allowed', reason: 'allowed_by_source_allowlist' }],
  ['cache', { outcome: 'denied', reason: 'field_not_allowlisted' }],
  ['product_export', { outcome: 'denied', reason: 'action_not_allowlisted' }],
  ['log', { outcome: 'denied', reason: 'action_not_allowlisted' }],
  ['analyze', { outcome: 'denied', reason: 'action_not_allowlisted' }],
  ['backup', { outcome: 'denied', reason: 'action_not_allowlisted' }],
  ['stage', { outcome: 'denied', reason: 'action_not_allowlisted' }],
  ['restore', { outcome: 'denied', reason: 'action_not_allowlisted' }],
  ['raw_debug', { outcome: 'denied', reason: 'action_not_allowlisted' }],
])

export function safeLovdBasicObservations(value: unknown): LovdBasicObservation[] {
  if (!isRecord(value) || value.status !== 'matched' || value.live_request_performed !== false) {
    return []
  }
  const installation = safeInstallation(value.installation)
  if (!installation || !Array.isArray(value.observations) || value.observations.length !== 1) {
    return []
  }
  const observation = safeObservation(value.observations[0], installation)
  return observation ? [observation] : []
}

function safeInstallation(value: unknown): LovdInstallationSource | null {
  if (!isRecord(value)) return null
  if (
    value.source_id !== SOURCE_ID ||
    value.installation_id !== INSTALLATION_ID ||
    value.display_name !== 'Global Variome shared LOVD' ||
    value.base_url !== BASE_URL ||
    value.live_access_enabled !== false ||
    value.positive_cache_policy !== 'not_approved' ||
    value.record_license_mode !== 'record_level_required' ||
    value.installation_permission_is_record_license !== false ||
    !isFiniteNumber(value.maximum_requests_per_second) ||
    value.maximum_requests_per_second <= 0 ||
    value.maximum_requests_per_second > 5 ||
    !isFiniteNumber(value.minimum_negative_cache_ttl_seconds) ||
    !Number.isInteger(value.minimum_negative_cache_ttl_seconds) ||
    value.minimum_negative_cache_ttl_seconds < 14_400
  ) {
    return null
  }
  return {
    source_id: SOURCE_ID,
    installation_id: INSTALLATION_ID,
    display_name: 'Global Variome shared LOVD',
    base_url: BASE_URL,
    live_access_enabled: false,
    maximum_requests_per_second: value.maximum_requests_per_second,
    minimum_negative_cache_ttl_seconds: value.minimum_negative_cache_ttl_seconds,
    positive_cache_policy: 'not_approved',
    record_license_mode: 'record_level_required',
    installation_permission_is_record_license: false,
  }
}

function safeObservation(
  value: unknown,
  installation: LovdInstallationSource,
): LovdBasicObservation | null {
  if (!isRecord(value)) return null
  if (
    value.source_id !== SOURCE_ID ||
    typeof value.source_record_id !== 'string' ||
    value.source_version !== 'LOVD 3 basic API synthetic schema fixture v1' ||
    typeof value.source_url !== 'string' ||
    value.origin_kind !== 'derived' ||
    value.match_level !== 'exact_normalized_hgvs' ||
    value.record_license !== 'CC-BY-4.0' ||
    value.terms_version_or_hash !== 'lovd-doc-review-2026-07-17' ||
    value.license_gate !== 'synthetic_fixture_record_license_example' ||
    value.launch_gate !== 'live_access_disabled_pending_written_permission' ||
    value.public_serialization_allowed !== true ||
    value.export_allowed !== false ||
    value.cache_allowed !== false ||
    value.attribution !== 'Global Variome shared LOVD (synthetic fixture)' ||
    value.policy_version !== 'lovd-fixture-policy-v1' ||
    value.decision_reason !== 'acquire:basic_record:acquisition_not_approved' ||
    value.presence !== true ||
    (value.genome_build !== 'GRCh37' && value.genome_build !== 'GRCh38') ||
    typeof value.transcript_accession !== 'string' ||
    !/^(?:NM|NR)_\d+\.\d+$/.test(value.transcript_accession) ||
    typeof value.hgvs_c !== 'string' ||
    !/^c\.[^\s:]{1,120}$/.test(value.hgvs_c) ||
    typeof value.source_edited_at !== 'string' ||
    !isTimestamp(value.source_edited_at) ||
    !isOptionalTimestamp(value.retrieved_at) ||
    !isOptionalTimestamp(value.decision_at) ||
    value.evidence_role !== 'presence_only' ||
    !sameInstallation(value.installation, installation)
  ) {
    return null
  }

  const recordPrefix = `${INSTALLATION_ID}:variant:`
  if (!value.source_record_id.startsWith(recordPrefix)) return null
  const recordId = value.source_record_id.slice(recordPrefix.length)
  if (!/^[a-z0-9][a-z0-9-]{0,79}$/.test(recordId)) return null
  if (!isCanonicalRecordUrl(value.source_url, recordId)) return null

  const policyDecisions = safePolicyDecisions(value.policy_decisions)
  if (!policyDecisions) return null

  return {
    source_id: SOURCE_ID,
    source_record_id: value.source_record_id,
    source_version: 'LOVD 3 basic API synthetic schema fixture v1',
    source_url: value.source_url,
    retrieved_at: optionalString(value.retrieved_at),
    origin_kind: 'derived',
    match_level: 'exact_normalized_hgvs',
    record_license: 'CC-BY-4.0',
    terms_version_or_hash: 'lovd-doc-review-2026-07-17',
    license_gate: 'synthetic_fixture_record_license_example',
    launch_gate: 'live_access_disabled_pending_written_permission',
    public_serialization_allowed: true,
    export_allowed: false,
    cache_allowed: false,
    attribution: 'Global Variome shared LOVD (synthetic fixture)',
    policy_version: 'lovd-fixture-policy-v1',
    decision_reason: optionalString(value.decision_reason),
    decision_at: optionalString(value.decision_at),
    policy_decisions: policyDecisions,
    installation,
    presence: true,
    genome_build: value.genome_build,
    transcript_accession: value.transcript_accession,
    hgvs_c: value.hgvs_c,
    source_edited_at: value.source_edited_at,
    evidence_role: 'presence_only',
  }
}

function safePolicyDecisions(value: unknown): SourcePolicyDecision[] | null {
  if (!Array.isArray(value) || value.length !== POLICY_EXPECTATIONS.size) return null
  const projected: SourcePolicyDecision[] = []
  const seen = new Set<SourcePolicyAction>()
  for (const item of value) {
    const action =
      isRecord(item) && typeof item.action === 'string'
        ? (item.action as SourcePolicyAction)
        : null
    const expectation = action ? POLICY_EXPECTATIONS.get(action) : null
    if (
      !isRecord(item) ||
      !action ||
      !expectation ||
      seen.has(action) ||
      item.field !== 'basic_record' ||
      item.outcome !== expectation.outcome ||
      item.reason !== expectation.reason ||
      item.decided_at !== '2026-07-17T13:39:00Z'
    ) {
      return null
    }
    seen.add(action)
    projected.push({
      action,
      field: 'basic_record',
      outcome: expectation.outcome,
      reason: expectation.reason,
      decided_at: item.decided_at,
    })
  }
  return projected
}

function sameInstallation(value: unknown, expected: LovdInstallationSource): boolean {
  const projected = safeInstallation(value)
  return projected !== null && JSON.stringify(projected) === JSON.stringify(expected)
}

function isCanonicalRecordUrl(value: string, recordId: string): boolean {
  try {
    const parsed = new URL(value)
    return (
      parsed.protocol === 'https:' &&
      parsed.hostname === 'databases.lovd.nl' &&
      parsed.port === '' &&
      parsed.username === '' &&
      parsed.password === '' &&
      parsed.pathname === `/shared/variants/${recordId}` &&
      parsed.search === '' &&
      parsed.hash === ''
    )
  } catch {
    return false
  }
}

function isTimestamp(value: string): boolean {
  return /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value))
}

function isOptionalTimestamp(value: unknown): boolean {
  return value == null || (typeof value === 'string' && isTimestamp(value))
}

function optionalString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export type { LovdBasicRecordsSection }
