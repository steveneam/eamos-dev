import { describe, expect, it } from 'vitest'

import type { OmimCrossReference, SourcePolicyDecision } from './backend'
import {
  omimCrossReferenceOrigins,
  safeOmimCrossReferenceHref,
} from './omim-cross-reference'

const allowedDecision: SourcePolicyDecision = {
  action: 'public_serialize',
  field: 'cross_references',
  outcome: 'allowed',
  reason: 'allowed_by_source_allowlist',
  decided_at: '2026-07-19T00:00:00Z',
}

function reference(overrides: Partial<OmimCrossReference> = {}): OmimCrossReference {
  return {
    source_id: 'mondo_disease_ontology',
    source_record_id: 'MONDO:0008765',
    origin_kind: 'cross_reference',
    public_serialization_allowed: true,
    attribution: 'Mondo Disease Ontology',
    policy_decisions: [allowedDecision],
    identifier_namespace: 'OMIM',
    identifier: 'OMIM:204100',
    entry_type: 'phenotype',
    external_link_provider: 'omim_web',
    external_url: 'https://omim.org/entry/204100',
    evidence_role: 'identifier_only',
    ...overrides,
  }
}

describe('OMIM identifier-only links', () => {
  it('returns the canonical link only for an explicitly permitted supplier-owned reference', () => {
    expect(safeOmimCrossReferenceHref('OMIM:204100', [reference()])).toBe(
      'https://omim.org/entry/204100',
    )
    expect(omimCrossReferenceOrigins(['OMIM:204100'], [reference()])).toEqual([
      'Mondo Disease Ontology',
    ])
  })

  it('fails closed for a bare identifier, a denied decision, or a substituted URL', () => {
    expect(safeOmimCrossReferenceHref('OMIM:204100', [])).toBeNull()
    expect(
      safeOmimCrossReferenceHref('OMIM:204100', [
        reference({
          policy_decisions: [{ ...allowedDecision, outcome: 'denied' }],
        }),
      ]),
    ).toBeNull()
    expect(
      safeOmimCrossReferenceHref('OMIM:204100', [
        reference({ external_url: 'https://example.test/redirect' }),
      ]),
    ).toBeNull()
    expect(
      safeOmimCrossReferenceHref('OMIM:204100', [
        reference({ source_id: 'omim_licensed_api' }),
      ]),
    ).toBeNull()
  })

  it('rejects noncanonical or type-confused identifiers', () => {
    expect(safeOmimCrossReferenceHref('OMIM #204100', [reference()])).toBeNull()
    expect(safeOmimCrossReferenceHref('OMIM:20410', [reference()])).toBeNull()
    expect(
      safeOmimCrossReferenceHref('OMIM:204100', [
        reference({ identifier_namespace: 'OMIM', identifier: 'OMIM:613794' }),
      ]),
    ).toBeNull()
  })
})
