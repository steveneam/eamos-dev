import { afterEach, describe, expect, it, vi } from 'vitest'

import { RPE65_NEGATIVE_CONTROL_SAMPLE } from '@/lib/sample-report'

import {
  deriveClassificationVerdict,
  parseLazyOverrides,
  readCachedReport,
  reportRequestKey,
  reportSummaryRequest,
  reportViewQueryId,
  writeCachedReport,
  type ReportQueryInput,
} from './reportClientModel'

const BASE_QUERY: ReportQueryInput = {
  cdna: ' c.260A>G ',
  demo: false,
  fixture: false,
  gene: 'rpe65',
  proteinChange: 'p.Asp87Gly',
  q: '',
  transcript: 'NM_000329.3',
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('report route model', () => {
  it('normalizes lookup identity while keeping redirect and fixture modes isolated', () => {
    expect(reportRequestKey(BASE_QUERY)).toBe(
      'lookup|RPE65|c.260A>G|NM_000329.3|p.Asp87Gly',
    )
    expect(reportRequestKey({ ...BASE_QUERY, gene: '', cdna: '', q: 'RPE65 c.260A>G' })).toBe(
      'q:RPE65 c.260A>G',
    )
    expect(reportRequestKey({ ...BASE_QUERY, demo: true })).toBe('demo:live-redirect')
    expect(reportRequestKey({ ...BASE_QUERY, fixture: true })).toBe(
      'fixture:rpe65-negative',
    )
  })

  it('builds the exact lookup-summary request for structured and raw searches', () => {
    expect(reportSummaryRequest(BASE_QUERY)).toEqual({
      gene: 'rpe65',
      cdna: 'c.260A>G',
      transcript: 'NM_000329.3',
      protein_change: 'p.Asp87Gly',
      species: 'human',
    })
    expect(
      reportSummaryRequest({ ...BASE_QUERY, gene: '', cdna: '', q: 'RPE65 c.260A>G' }),
    ).toEqual({ search_text: 'RPE65 c.260A>G', species: 'human' })
    expect(reportSummaryRequest({ ...BASE_QUERY, fixture: true })).toBeUndefined()
  })

  it('accepts only registered lazy-section overrides', () => {
    expect(
      Array.from(
        parseLazyOverrides(
          'publications, therapies_trials,not-a-section,publications, clingen_vcep',
        ),
      ),
    ).toEqual(['publications', 'therapies_trials', 'clingen_vcep'])
  })
})

describe('report cache and presentation model', () => {
  it('round-trips a fresh report through session storage and skips fixture keys', () => {
    const values = new Map<string, string>()
    const sessionStorage = {
      getItem: vi.fn((key: string) => values.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => values.set(key, value)),
      removeItem: vi.fn((key: string) => values.delete(key)),
    }
    vi.stubGlobal('window', { sessionStorage })
    vi.spyOn(Date, 'now').mockReturnValue(100_000)

    writeCachedReport('lookup|RPE65|c.260A>G||', RPE65_NEGATIVE_CONTROL_SAMPLE)
    expect(readCachedReport('lookup|RPE65|c.260A>G||')).toEqual(
      RPE65_NEGATIVE_CONTROL_SAMPLE,
    )

    writeCachedReport('fixture:rpe65-negative', RPE65_NEGATIVE_CONTROL_SAMPLE)
    expect(sessionStorage.setItem).toHaveBeenCalledTimes(1)
    expect(readCachedReport('fixture:rpe65-negative')).toBeNull()
  })

  it('derives the report-view identity and clinical verdict without widening unknown states', () => {
    expect(reportViewQueryId(RPE65_NEGATIVE_CONTROL_SAMPLE, 'fallback')).toBe('RPE65 c.260A>G')
    expect(deriveClassificationVerdict('Likely pathogenic')).toBe('Likely pathogenic')
    expect(deriveClassificationVerdict('variant of uncertain significance')).toBe('VUS')
    expect(deriveClassificationVerdict('classification unavailable')).toBeNull()
    expect(deriveClassificationVerdict('conflicting')).toBeNull()
  })
})
