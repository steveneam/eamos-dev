import { describe, expect, it } from 'vitest'
import type { CrisprResponse } from '@/lib/backend'
import { CRISPR_SAMPLE } from './crispr-sample'
import {
  designProviderDisclosure,
  hasPredictedOutcomeData,
  outcomeDisclosure,
} from './crispr-disclosure'
import { CRISPR_TIDE_SAMPLE, type CrisprTideResult } from './crispr-tide-sample'

describe('designProviderDisclosure', () => {
  it('honors the bundled fixture disclosure', () => {
    const disclosure = designProviderDisclosure(CRISPR_SAMPLE)
    expect(disclosure.sourceBacked).toBe(false)
    expect(disclosure.providerLabel).toBe('Workbench CRISPR fixture')
    expect(disclosure.statusLine).toContain('Fixture')
    expect(disclosure.platformLine).toContain('DeepCpf1')
  })

  it('does not trust a provider name unless source_backed is explicit', () => {
    const disclosure = designProviderDisclosure({
      ...CRISPR_SAMPLE,
      source_disclosure: null,
      provider_label: 'DeepHF service',
    } as CrisprResponse)
    expect(disclosure.sourceBacked).toBe(false)
    expect(disclosure.providerLabel).toBe('Verified CRISPR provider required')
  })

  it('surfaces backend source-backed provider details when present', () => {
    const disclosure = designProviderDisclosure({
      ...CRISPR_SAMPLE,
      provider_label: 'crisprScore SpCas9',
      source_backed: true,
      score_sources: ['RuleSet3', 'CFD'],
      source_disclosure: {
        source_status: 'source_backed',
        provider_id: 'crisprscore_spcas9',
        provider_label: 'crisprScore SpCas9',
        source_version: 'test-v1',
        cache_status: null,
        warnings: [],
        requirements: [],
      },
    } as CrisprResponse)
    expect(disclosure.sourceBacked).toBe(true)
    expect(disclosure.providerLabel).toBe('crisprScore SpCas9')
    expect(disclosure.scoreLine).toContain('resolved source-backed')
  })
})

describe('outcomeDisclosure', () => {
  it('keeps the bundled outcome sample observed-only', () => {
    expect(hasPredictedOutcomeData(CRISPR_TIDE_SAMPLE)).toBe(false)
    expect(outcomeDisclosure(CRISPR_TIDE_SAMPLE)).toMatchObject({
      sourceBacked: false,
      showPredicted: false,
      seriesLabel: 'observed-only',
    })
  })

  it('requires numeric predicted bins before showing a predicted series', () => {
    const flaggedWithoutData: CrisprTideResult = {
      ...CRISPR_TIDE_SAMPLE,
      predicted_available: true,
    }
    expect(hasPredictedOutcomeData(flaggedWithoutData)).toBe(false)
    expect(outcomeDisclosure(flaggedWithoutData).showPredicted).toBe(false)
  })

  it('shows predicted bins only for source-backed outcome data with values', () => {
    const tideWithPrediction = {
      ...CRISPR_TIDE_SAMPLE,
      source_backed: true,
      analysis_kind: 'tide',
      provider_label: 'Backend TIDE',
      source_disclosure: {
        source_status: 'source_backed',
        provider_id: 'backend_tide',
        provider_label: 'Backend TIDE',
        source_version: 'test-v1',
        cache_status: null,
        warnings: [],
        requirements: [],
      },
      predicted_available: true,
      spectrum: CRISPR_TIDE_SAMPLE.spectrum.map((bin) => ({
        ...bin,
        predicted: bin.observed,
      })),
    } satisfies CrisprTideResult

    const disclosure = outcomeDisclosure(tideWithPrediction)
    expect(disclosure.sourceBacked).toBe(true)
    expect(disclosure.showPredicted).toBe(true)
    expect(disclosure.sourceLabel).toBe('Backend TIDE')
  })
})
