import { BatchRequestError } from '@/lib/batch'
import type { ActiveFilter } from '@/lib/compare-filters'
import type {
  BatchFilters,
  BatchJob,
  BatchJobStatus,
  ParsedVariant as BatchVariant,
} from '@/lib/backend'
import type { ParsedVariant } from '@/lib/variant-file'

export type RunStatus = 'idle' | 'running' | 'done'

export type BatchProgressStage =
  | 'uploading'
  | BatchJobStatus
  | 'auth'
  | 'expired'
  | 'rate_limited'
  | 'validation'
  | 'unavailable'
  | 'stalled'

export type BatchProgress = {
  stage: BatchProgressStage
  status?: BatchJobStatus
  jobId?: string
  done: number
  total: number
  nInput?: number
  nToLookup?: number
  nAfterFilters?: number
  estSeconds?: number
  usedUpload?: boolean
  warnings?: string[]
  error?: string
}

/** Map a browser-parsed cohort row to the backend batch variant shape. */
export function toBatchVariant(variant: ParsedVariant): BatchVariant {
  return {
    raw: variant.raw,
    query: variant.query,
    gene: variant.gene,
    variant: variant.variant,
    chrom: variant.chrom,
    pos: variant.pos,
    ref: variant.ref,
    alt: variant.alt,
    filter: variant.filter,
    info_af: variant.info_af,
    warnings: variant.warnings ?? [],
  }
}

/** Translate the active scope chips into the batch filter payload. */
export function toBatchFilters(filters: ActiveFilter[]): BatchFilters {
  const out: BatchFilters = {}
  const panel = filters.find((filter) => filter.kind === 'panel' && filter.panelSlug)
  if (panel?.panelSlug) out.panel_slug = panel.panelSlug
  if (filters.some((filter) => filter.kind === 'pass')) out.pass_only = true
  const regions = filters
    .filter((filter) => filter.kind === 'region' && filter.region)
    .map((filter) => filter.region as string)
  if (regions.length) out.regions = regions
  const af = filters.find((filter) => filter.kind === 'af')
  if (af?.maxAf != null) out.max_af = af.maxAf
  return out
}

export function progressFromJob(job: BatchJob, usedUpload: boolean): BatchProgress {
  const error =
    job.status === 'failed'
      ? 'Batch lookup failed. Review the warnings, then regenerate the run.'
      : job.status === 'cancelled'
        ? 'Batch lookup was cancelled before completion.'
        : undefined
  return {
    stage: job.status,
    status: job.status,
    jobId: job.job_id,
    done: job.done,
    total: job.total,
    nInput: job.n_input,
    nToLookup: job.n_to_lookup,
    nAfterFilters: job.n_after_filters ?? undefined,
    estSeconds: job.est_seconds,
    usedUpload,
    warnings: job.warnings,
    error,
  }
}

export function progressFromError(
  error: unknown,
  previous: BatchProgress | null,
  fallbackTotal: number,
): BatchProgress {
  const base = {
    done: previous?.done ?? 0,
    total: previous?.total ?? fallbackTotal,
    jobId: previous?.jobId,
    nInput: previous?.nInput,
    nToLookup: previous?.nToLookup,
    nAfterFilters: previous?.nAfterFilters,
    estSeconds: previous?.estSeconds,
    usedUpload: previous?.usedUpload,
    warnings: previous?.warnings,
  }
  if (error instanceof BatchRequestError) {
    if (error.code === 'auth_required' || error.code === 'auth_expired') {
      return { ...base, stage: 'auth', error: error.message }
    }
    if (error.code === 'not_found') {
      return {
        ...base,
        stage: 'expired',
        error: 'This Batch run is no longer available. Regenerate it to run the current cohort again.',
      }
    }
    if (error.code === 'rate_limited') {
      return { ...base, stage: 'rate_limited', error: error.message }
    }
    if (error.code === 'validation') {
      return { ...base, stage: 'validation', error: error.message }
    }
    if (error.code === 'unavailable') {
      return { ...base, stage: 'unavailable', error: error.message }
    }
    return { ...base, stage: 'failed', error: error.message }
  }
  const message = error instanceof Error ? error.message : 'Batch lookup failed.'
  if (message === 'Batch lookup is still running') {
    return {
      ...base,
      stage: 'stalled',
      error: 'Batch is still running. Try again in a moment, or reduce the cohort size.',
    }
  }
  return { ...base, stage: 'failed', error: message }
}

export function isBatchIssue(stage?: BatchProgressStage): boolean {
  return (
    stage === 'failed' ||
    stage === 'cancelled' ||
    stage === 'auth' ||
    stage === 'expired' ||
    stage === 'rate_limited' ||
    stage === 'validation' ||
    stage === 'unavailable' ||
    stage === 'stalled'
  )
}

export function issueCopy(
  progress: BatchProgress,
): { title: string; body: string; tone: 'warn' | 'error' } {
  if (progress.stage === 'auth') {
    return {
      title: 'Sign-in required',
      body: progress.error ?? 'Sign in, then regenerate the Batch run.',
      tone: 'warn',
    }
  }
  if (progress.stage === 'expired') {
    return {
      title: 'Batch run expired',
      body:
        progress.error ??
        'This run is no longer available. Regenerate it to annotate the current cohort again.',
      tone: 'warn',
    }
  }
  if (progress.stage === 'rate_limited') {
    return {
      title: 'Batch run limit reached',
      body: progress.error ?? 'Wait a moment, then regenerate the Batch run.',
      tone: 'warn',
    }
  }
  if (progress.stage === 'validation') {
    return {
      title: 'Batch input was not accepted',
      body: progress.error ?? 'Check the uploaded VCF or variant list, then regenerate.',
      tone: 'warn',
    }
  }
  if (progress.stage === 'unavailable') {
    return {
      title: 'Batch service unavailable',
      body:
        progress.error ??
        'The backend could not accept the run. Try again after the service is available.',
      tone: 'error',
    }
  }
  if (progress.stage === 'cancelled') {
    return {
      title: 'Batch lookup was cancelled',
      body: progress.error ?? 'The run stopped before completion. Regenerate to start a new run.',
      tone: 'warn',
    }
  }
  if (progress.stage === 'stalled') {
    return {
      title: 'Batch lookup is still running',
      body: progress.error ?? 'Try again in a moment, or reduce the cohort size.',
      tone: 'warn',
    }
  }
  return {
    title: 'Batch lookup failed',
    body:
      progress.error ??
      'The backend returned a failed Batch status. Regenerate after checking the warnings.',
    tone: 'error',
  }
}
