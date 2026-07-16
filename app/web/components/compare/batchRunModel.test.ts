import { describe, expect, it } from 'vitest'

import { BatchRequestError } from '@/lib/batch'
import type { ActiveFilter } from '@/lib/compare-filters'
import type { BatchJob } from '@/lib/backend'
import type { ParsedVariant } from '@/lib/variant-file'

import {
  isBatchIssue,
  issueCopy,
  progressFromError,
  progressFromJob,
  toBatchFilters,
  toBatchVariant,
  type BatchProgress,
} from './batchRunModel'

const BASE_JOB: BatchJob = {
  job_id: 'batch-17',
  status: 'running',
  n_input: 12,
  n_to_lookup: 7,
  n_after_filters: 7,
  est_seconds: 18,
  done: 3,
  total: 7,
  results: [],
  page: { limit: 200, next_cursor: null, total: 0 },
  warnings: ['one row needs review'],
}

describe('compare batch request model', () => {
  it('allowlists the browser variant fields sent to the backend', () => {
    const variant: ParsedVariant = {
      raw: '17 43071077 . A G',
      query: '17-43071077-A-G',
      gene: 'BRCA1',
      variant: 'c.68_69del',
      chrom: '17',
      pos: 43071077,
      ref: 'A',
      alt: 'G',
      filter: 'PASS',
      info_af: 0.001,
    }

    expect(toBatchVariant(variant)).toEqual({
      raw: '17 43071077 . A G',
      query: '17-43071077-A-G',
      gene: 'BRCA1',
      variant: 'c.68_69del',
      chrom: '17',
      pos: 43071077,
      ref: 'A',
      alt: 'G',
      filter: 'PASS',
      info_af: 0.001,
      warnings: [],
    })
  })

  it('translates only supported scope chips into the batch filter contract', () => {
    const filters: ActiveFilter[] = [
      { id: 'panel', kind: 'panel', panelSlug: 'hereditary-cancer' },
      { id: 'pass', kind: 'pass' },
      { id: 'region-1', kind: 'region', region: 'chr17:43000000-43100000' },
      { id: 'region-2', kind: 'region', region: 'chr13:32300000-32400000' },
      { id: 'af', kind: 'af', maxAf: 0.01 },
    ]

    expect(toBatchFilters(filters)).toEqual({
      panel_slug: 'hereditary-cancer',
      pass_only: true,
      regions: ['chr17:43000000-43100000', 'chr13:32300000-32400000'],
      max_af: 0.01,
    })
  })
})

describe('compare batch progress model', () => {
  it('preserves backend progress metadata and terminal failure copy', () => {
    expect(progressFromJob(BASE_JOB, true)).toEqual({
      stage: 'running',
      status: 'running',
      jobId: 'batch-17',
      done: 3,
      total: 7,
      nInput: 12,
      nToLookup: 7,
      nAfterFilters: 7,
      estSeconds: 18,
      usedUpload: true,
      warnings: ['one row needs review'],
      error: undefined,
    })

    expect(progressFromJob({ ...BASE_JOB, status: 'failed' }, false).error).toBe(
      'Batch lookup failed. Review the warnings, then regenerate the run.',
    )
    expect(progressFromJob({ ...BASE_JOB, status: 'cancelled' }, false).error).toBe(
      'Batch lookup was cancelled before completion.',
    )
  })

  it.each([
    ['auth_required', 'auth'],
    ['auth_expired', 'auth'],
    ['not_found', 'expired'],
    ['rate_limited', 'rate_limited'],
    ['validation', 'validation'],
    ['unavailable', 'unavailable'],
    ['request_failed', 'failed'],
  ] as const)('maps %s request errors to the %s UI stage', (code, stage) => {
    const previous: BatchProgress = {
      stage: 'running',
      jobId: 'batch-17',
      done: 3,
      total: 7,
      warnings: ['one row needs review'],
    }
    const error = new BatchRequestError('request message', { code })

    expect(progressFromError(error, previous, 12)).toMatchObject({
      stage,
      jobId: 'batch-17',
      done: 3,
      total: 7,
      warnings: ['one row needs review'],
    })
  })

  it('distinguishes a stalled poll from an ordinary failure', () => {
    expect(progressFromError(new Error('Batch lookup is still running'), null, 12)).toEqual(
      expect.objectContaining({
        stage: 'stalled',
        done: 0,
        total: 12,
        error: 'Batch is still running. Try again in a moment, or reduce the cohort size.',
      }),
    )
    expect(progressFromError('network unavailable', null, 12)).toEqual(
      expect.objectContaining({ stage: 'failed', error: 'Batch lookup failed.' }),
    )
  })

  it('keeps issue detection and user-facing severity aligned', () => {
    expect(isBatchIssue('running')).toBe(false)
    expect(isBatchIssue('completed')).toBe(false)
    expect(isBatchIssue('auth')).toBe(true)
    expect(isBatchIssue('failed')).toBe(true)

    expect(issueCopy({ stage: 'auth', done: 0, total: 1 })).toEqual({
      title: 'Sign-in required',
      body: 'Sign in, then regenerate the Batch run.',
      tone: 'warn',
    })
    expect(issueCopy({ stage: 'failed', done: 0, total: 1 }).tone).toBe('error')
  })
})
