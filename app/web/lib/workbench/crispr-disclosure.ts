import type { CrisprResponse } from '@/lib/backend'
import type { CrisprTideResult } from './crispr-tide-sample'
import { disclosureView } from './source-disclosure'

type UnknownRecord = Record<string, unknown>

const PLATFORM_GATED_MODELS = 'DeepHF, DeepCpf1, and enPAM+GB'

export interface CrisprDesignDisclosure {
  providerLabel: string
  statusLine: string
  scoreLine: string
  platformLine: string
  sourceBacked: boolean
}

export interface CrisprOutcomeDisclosure {
  sourceLabel: string
  fitLabel: string
  predictionLine: string
  seriesLabel: string
  observedLegendLabel: string
  showPredicted: boolean
  sourceBacked: boolean
}

function asRecord(value: unknown): UnknownRecord {
  return value && typeof value === 'object' ? (value as UnknownRecord) : {}
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return null
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value
        .filter(
          (item): item is string =>
            typeof item === 'string' && item.trim().length > 0,
        )
        .map((item) => item.trim())
    : []
}

/**
 * Additive backend fields this frontend is ready to consume without changing
 * the current shared `backend.ts` contract: provider_id/provider_label,
 * source_backed, score_sources, analysis_kind, predicted_source, warnings.
 */
export function designProviderDisclosure(
  result: CrisprResponse | null | undefined,
): CrisprDesignDisclosure {
  const disclosure = disclosureView(result?.source_disclosure, {
    source_status: 'local_provider',
    provider_id: 'local_deterministic_spcas9',
    provider_label: 'Local deterministic SpCas9 provider',
    warnings: ['advanced_crispr_scoring_gated'],
    requirements: ['spcas9_ngg'],
  })
  if (result?.source_disclosure) {
    const sourceBacked = disclosure.operational
    return {
      providerLabel: disclosure.providerLabel,
      sourceBacked,
      statusLine: `${disclosure.statusLabel}. ${disclosure.caveat}`,
      scoreLine:
        disclosure.status === 'source_backed'
          ? 'Provider metadata came from a resolved source-backed backend response.'
          : disclosure.status === 'local_provider'
            ? 'Scores are local/provider-reported and should not be read as genome-wide DeepHF or CFD output.'
            : 'Scores are fixture or fallback values and should not be read as completed backend analysis.',
      platformLine: `${PLATFORM_GATED_MODELS} remain gated unless the backend marks them available.`,
    }
  }

  const meta = asRecord(result)
  const providerLabel = firstString(
    meta.provider_label,
    meta.provider_name,
    meta.provider,
    meta.provider_id,
  )
  const sourceBacked = meta.source_backed === true
  const scoreSources = stringList(meta.score_sources).concat(
    stringList(meta.scoring_sources),
  )

  if (sourceBacked) {
    const label = providerLabel ?? 'Source-backed CRISPR provider'
    return {
      providerLabel: label,
      sourceBacked: true,
      statusLine: 'Provider details came from the backend response.',
      scoreLine:
        scoreSources.length > 0
          ? `Backend-reported score sources: ${scoreSources.join(', ')}.`
          : 'Backend marked the response source-backed but did not name score sources.',
      platformLine: `${PLATFORM_GATED_MODELS} should appear only when the backend marks them available for this platform.`,
    }
  }

  return {
    providerLabel: 'Local deterministic SpCas9',
    sourceBacked: false,
    statusLine:
      'No source-backed provider metadata was returned, so this is shown as the local deterministic SpCas9 surface.',
    scoreLine:
      'Scores are heuristic/local: GC/poly-T/PAM-proximal on-target plus an in-context Hsu/MIT specificity scan, not genome-wide DeepHF/CFD output.',
    platformLine: `${PLATFORM_GATED_MODELS} are platform-gated and not Windows-safe here.`,
  }
}

export function hasPredictedOutcomeData(
  result: CrisprTideResult | null | undefined,
): boolean {
  return Boolean(
    result?.predicted_available &&
      result.spectrum.some(
        (bin) =>
          typeof bin.predicted === 'number' && Number.isFinite(bin.predicted),
      ),
  )
}

export function outcomeDisclosure(
  result: CrisprTideResult | null | undefined,
): CrisprOutcomeDisclosure {
  const disclosure = disclosureView(result?.source_disclosure, {
    source_status: result?.source_backed ? 'local_provider' : 'fallback',
    provider_id: result?.source_backed ? 'observed_only_tide' : 'frontend_tide_sample',
    provider_label: result?.provider_label ?? 'Frontend sample/fallback',
  })
  if (result?.source_disclosure) {
    const showPredicted = hasPredictedOutcomeData(result)
    return {
      sourceBacked: disclosure.operational,
      sourceLabel: disclosure.providerLabel,
      fitLabel: disclosure.operational ? 'Fit R2' : 'Sample R2',
      seriesLabel: showPredicted ? 'observed + predicted' : 'observed-only',
      observedLegendLabel:
        disclosure.status === 'fallback' || disclosure.status === 'fixture'
          ? 'Observed sample'
          : 'Observed (TIDE)',
      showPredicted,
      predictionLine: showPredicted
        ? 'Predicted bins are shown because the response includes numeric predicted values.'
        : disclosure.operational
          ? 'No predicted repair series is shown; the response contains observed values only.'
          : 'Predicted repair series is hidden for fixture or fallback output.',
    }
  }

  const meta = asRecord(result)
  const analysisKind = firstString(
    meta.analysis_kind,
    meta.analysis_source,
    meta.provider,
  )?.toLowerCase()
  const sourceBacked =
    meta.source_backed === true ||
    analysisKind === 'tide' ||
    analysisKind === 'lindel'
  const showPredicted = hasPredictedOutcomeData(result)
  const providerLabel = firstString(meta.provider_label, meta.provider)

  if (sourceBacked) {
    const kindLabel =
      analysisKind === 'lindel'
        ? 'Lindel'
        : analysisKind === 'tide'
          ? 'TIDE'
          : 'source-backed'
    return {
      sourceBacked: true,
      sourceLabel: providerLabel ?? kindLabel,
      fitLabel: 'Fit R2',
      seriesLabel: showPredicted ? 'observed + predicted' : 'observed-only',
      observedLegendLabel:
        analysisKind === 'tide' ? 'Observed (TIDE)' : 'Observed',
      showPredicted,
      predictionLine: showPredicted
        ? 'Predicted bins are shown because the response includes numeric predicted values.'
        : 'No predicted repair series is shown; the response contains observed values only.',
    }
  }

  return {
    sourceBacked: false,
    sourceLabel: 'Frontend sample/fallback',
    fitLabel: 'Sample R2',
    seriesLabel: 'observed-only',
    observedLegendLabel: 'Observed sample',
    showPredicted: false,
    predictionLine:
      'Predicted repair/Lindel series is hidden until the backend returns source-backed TIDE or Lindel data with numeric predicted bins.',
  }
}
