import { describe, expect, it } from 'vitest'

import {
  LOVD_PRESENCE_NOTICE,
  safeLovdBasicObservations,
} from './lovd-basic-observation'

function policyDecisions() {
  const decided_at = '2026-07-17T13:39:00Z'
  return [
    { action: 'acquire', outcome: 'denied', reason: 'acquisition_not_approved' },
    { action: 'normalize', outcome: 'allowed', reason: 'allowed_by_source_allowlist' },
    { action: 'public_serialize', outcome: 'allowed', reason: 'allowed_by_source_allowlist' },
    { action: 'cache', outcome: 'denied', reason: 'field_not_allowlisted' },
    { action: 'product_export', outcome: 'denied', reason: 'action_not_allowlisted' },
    { action: 'log', outcome: 'denied', reason: 'action_not_allowlisted' },
    { action: 'analyze', outcome: 'denied', reason: 'action_not_allowlisted' },
    { action: 'backup', outcome: 'denied', reason: 'action_not_allowlisted' },
    { action: 'stage', outcome: 'denied', reason: 'action_not_allowlisted' },
    { action: 'restore', outcome: 'denied', reason: 'action_not_allowlisted' },
    { action: 'raw_debug', outcome: 'denied', reason: 'action_not_allowlisted' },
  ].map((item) => ({ ...item, field: 'basic_record', decided_at }))
}

function section(): Record<string, unknown> {
  const installation = {
    source_id: 'lovd_global_variome_shared_fixture',
    installation_id: 'global_variome_shared_lovd',
    display_name: 'Global Variome shared LOVD',
    base_url: 'https://databases.lovd.nl/shared',
    live_access_enabled: false,
    maximum_requests_per_second: 5,
    minimum_negative_cache_ttl_seconds: 14_400,
    positive_cache_policy: 'not_approved',
    record_license_mode: 'record_level_required',
    installation_permission_is_record_license: false,
  }
  return {
    installation,
    status: 'matched',
    live_request_performed: false,
    warnings: ['synthetic_fixture_only'],
    observations: [
      {
        source_id: 'lovd_global_variome_shared_fixture',
        source_record_id: 'global_variome_shared_lovd:variant:fixture-rpe65-c260ag',
        source_version: 'LOVD 3 basic API synthetic schema fixture v1',
        source_url:
          'https://databases.lovd.nl/shared/variants/fixture-rpe65-c260ag',
        retrieved_at: null,
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
        decision_reason: 'acquire:basic_record:acquisition_not_approved',
        decision_at: '2026-07-17T13:39:00Z',
        policy_decisions: policyDecisions(),
        installation,
        presence: true,
        genome_build: 'GRCh38',
        transcript_accession: 'NM_000329.3',
        hgvs_c: 'c.260A>G',
        source_edited_at: '2026-07-17T00:00:00Z',
        evidence_role: 'presence_only',
      },
    ],
  }
}

const UNSAFE_MUTATIONS: Array<[
  string,
  (raw: Record<string, unknown>) => void,
]> = [
  ['unknown record license', (raw) => {
    ((raw.observations as Record<string, unknown>[])[0]).record_license = 'unknown'
  }],
  ['arbitrary host', (raw) => {
    ((raw.observations as Record<string, unknown>[])[0]).source_url =
      'https://databases.lovd.nl.attacker.example/shared/variants/fixture-rpe65-c260ag'
  }],
  ['versionless transcript', (raw) => {
    ((raw.observations as Record<string, unknown>[])[0]).transcript_accession = 'NM_000329'
  }],
  ['unsafe rate policy', (raw) => {
    (raw.installation as Record<string, unknown>).maximum_requests_per_second = 6
  }],
  ['short negative-cache floor', (raw) => {
    (raw.installation as Record<string, unknown>).minimum_negative_cache_ttl_seconds = 60
  }],
  ['allowed log sink', (raw) => {
    const observation = (raw.observations as Record<string, unknown>[])[0]
    const logDecision = (observation.policy_decisions as Record<string, unknown>[]).find(
      (item) => item.action === 'log',
    )
    if (logDecision) logDecision.outcome = 'allowed'
  }],
]

describe('LOVD basic-record safety boundary', () => {
  it('keeps the required non-classification notice exact', () => {
    expect(LOVD_PRESENCE_NOTICE).toBe(
      'Matching LOVD basic record; presence is not a classification.',
    )
  })

  it('admits the reviewed exact fixture contract', () => {
    const observations = safeLovdBasicObservations(section())

    expect(observations).toHaveLength(1)
    expect(observations[0].transcript_accession).toBe('NM_000329.3')
    expect(observations[0].hgvs_c).toBe('c.260A>G')
    expect(observations[0].record_license).toBe('CC-BY-4.0')
  })

  it('projects only safe fields even if an untrusted payload carries prohibited extras', () => {
    const raw = section()
    const observation = (raw.observations as Record<string, unknown>[])[0]
    observation.patient = 'sensitive-patient-value'
    observation.phenotype = 'sensitive-phenotype-value'
    observation.classification = 'Pathogenic'
    observation.Times_reported = 42
    observation.raw_payload = { creator: 'sensitive-creator-value' }

    const serialized = JSON.stringify(safeLovdBasicObservations(raw))

    expect(serialized).not.toContain('sensitive-patient-value')
    expect(serialized).not.toContain('sensitive-phenotype-value')
    expect(serialized).not.toContain('Pathogenic')
    expect(serialized).not.toContain('Times_reported')
    expect(serialized).not.toContain('raw_payload')
  })

  it.each(UNSAFE_MUTATIONS)('fails closed for %s', (_label, mutate) => {
    const raw = section()
    mutate(raw)

    expect(safeLovdBasicObservations(raw)).toEqual([])
  })
})
