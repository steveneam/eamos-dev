import { describe, expect, it } from 'vitest'

import type {
  AssociatedCondition,
  ReportPayload,
  SourcePolicyDecision,
} from './backend'
import { htmlDiseaseAndConditions } from './report-html'
import { tsvDiseaseAndConditions } from './report-tsv'
import {
  productExportFacts,
  sourceFactActionAllowed,
} from './source-fact-policy'

const DECIDED_AT = '2026-07-17T00:00:00Z'

function decision(
  action: SourcePolicyDecision['action'],
  outcome: SourcePolicyDecision['outcome'],
): SourcePolicyDecision {
  return {
    action,
    field: 'condition.name',
    outcome,
    reason: `test_${outcome}`,
    decided_at: DECIDED_AT,
  }
}

function condition(
  name: string,
  policyDecisions: SourcePolicyDecision[],
  exportAllowed: boolean | null = null,
): AssociatedCondition {
  return {
    source_id: 'test_source',
    origin_kind: 'direct',
    public_serialization_allowed: true,
    export_allowed: exportAllowed,
    policy_decisions: policyDecisions,
    name,
    case_count: 1,
    evidence_level: 'definitive',
    inheritance: 'AR',
    source: 'Test source',
  }
}

const payload = { variant_summary_rows: [] } as unknown as ReportPayload

describe('source fact product-export policy', () => {
  it('recomputes the action projection instead of trusting a stale boolean', () => {
    const stale = condition(
      'Denied condition',
      [decision('product_export', 'denied')],
      true,
    )

    expect(sourceFactActionAllowed(stale, 'product_export')).toBe(false)
    expect(productExportFacts([stale])).toEqual([])
  })

  it('requires an explicit legacy export projection when decisions are absent', () => {
    expect(productExportFacts([condition('Unknown condition', [])])).toEqual([])
    expect(
      productExportFacts([condition('Allowed condition', [], true)]).map(
        (fact) => fact.name,
      ),
    ).toEqual(['Allowed condition'])
  })

  it('handles an omitted legacy decision list and still requires its projection', () => {
    const legacy = condition('Legacy condition', [], true)
    delete (legacy as Partial<AssociatedCondition>).policy_decisions

    expect(sourceFactActionAllowed(legacy, 'product_export')).toBe(true)
    legacy.export_allowed = null
    expect(sourceFactActionAllowed(legacy, 'product_export')).toBe(false)
  })

  it('removes denied conditions from TSV and rich HTML exports', () => {
    const allowed = condition(
      'Allowed condition',
      [decision('product_export', 'allowed')],
    )
    const denied = condition(
      'Denied <condition>',
      [decision('product_export', 'denied')],
      true,
    )

    const tsv = tsvDiseaseAndConditions(payload, null, [allowed, denied])
    const html = htmlDiseaseAndConditions(payload, null, [allowed, denied])

    expect(tsv).toContain('Allowed condition')
    expect(html).toContain('Allowed condition')
    expect(tsv).not.toContain('Denied')
    expect(html).not.toContain('Denied')
  })
})
