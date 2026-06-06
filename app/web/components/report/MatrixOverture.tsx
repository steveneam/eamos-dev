'use client'

import { useEffect, useMemo, useState } from 'react'
import { CarouselDots } from '@/components/ui/CarouselDots'
import { MatrixTile } from '@/components/report/MatrixTile'
import { lookupSummary } from '@/lib/api'
import type { LookupRequest, LookupSummaryTile, ReportPayload } from '@/lib/backend'

interface MatrixOvertureProps {
  /**
   * Tiles to render. If omitted, MatrixOverture fetches `lookupSummary(request)`
   * and falls back to synthesizing tiles from the local ReportPayload when no
   * request is supplied or the network call fails (TypeError = backend down,
   * same pattern as designPrimers / designGuides). Pass `tiles` explicitly if
   * the parent has already resolved them.
   */
  tiles?: LookupSummaryTile[]
  payload: ReportPayload
  /**
   * The same LookupRequest the parent sent to `variantLookup()`. When provided,
   * the overture upgrades its synthesized tiles with the backend tile array as
   * soon as the network call returns. When omitted (e.g. demo/sample mode),
   * the overture stays mock-only.
   */
  request?: LookupRequest
}

const SCROLL_OFFSET = 68 // matches CallCardsGrid — clears the 60px sticky nav.

// The matrix is a section overview. A four-item summary is the call-card shape,
// so do not swap it in here or the report top renders duplicate summaries.
const MIN_MATRIX_TILE_COUNT = 8

function scrollToTile(tile: LookupSummaryTile) {
  const targetId = tile.target_panel_id ?? tile.target_section_id
  if (!targetId || typeof document === 'undefined') return
  const el = document.getElementById(targetId)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - SCROLL_OFFSET
  window.scrollTo({ top, behavior: 'smooth' })
  // URL fragment for shareable deep-links.
  if (typeof history !== 'undefined') {
    history.replaceState(null, '', `#${targetId}`)
  }
}

/**
 * MatrixOverture — lookahead summary grid above the numbered evidence sections.
 *
 * Renders 10-12 tiles (NOT Varsome's 24 — DL-004). Mobile: horizontal swipe
 * carousel; sm: 3-up; lg+: 4-up. Tiles deep-link to their target section via
 * URL fragment + smooth scroll. DL-017: premium-gated tiles get a distinct
 * surface from no-data tiles — never identical grey (enforced in MatrixTile).
 */
export function MatrixOverture({ tiles, payload, request }: MatrixOvertureProps) {
  const synthesized = useMemo(() => synthesizeTilesFromPayload(payload), [payload])
  const requestKey = useMemo(() => (request ? JSON.stringify(request) : ''), [request])
  const [liveTiles, setLiveTiles] = useState<{
    requestKey: string
    tiles: LookupSummaryTile[]
  } | null>(null)

  useEffect(() => {
    // Parent already resolved tiles, or we have no request to send — stay mock.
    if (tiles || !request) return
    let cancelled = false
    lookupSummary(request)
      .then((response) => {
        if (cancelled) return
        if (response.tiles && response.tiles.length >= MIN_MATRIX_TILE_COUNT) {
          setLiveTiles({ requestKey, tiles: response.tiles })
        }
      })
      .catch((err: unknown) => {
        // TypeError = backend unreachable (offline / dev server down). Stay
        // mock-first, same fallback shape as designPrimers / designGuides.
        // Other errors (4xx/5xx body, JSON parse) → stay mock; log for debug.
        if (!(err instanceof TypeError) && typeof console !== 'undefined') {
          console.warn('MatrixOverture: lookupSummary failed, using synthesized tiles', err)
        }
      })
    return () => {
      cancelled = true
    }
  }, [request, requestKey, tiles])

  const effectiveTiles =
    tiles ?? (request && liveTiles?.requestKey === requestKey ? liveTiles.tiles : null) ?? synthesized

  if (effectiveTiles.length === 0) return null

  return (
    <section aria-label="Variant evidence matrix overture" className="mb-4">
      <div
        id="matrix-overture-scroller"
        className="flex snap-x snap-mandatory items-stretch gap-2 overflow-x-auto pb-3 sm:grid sm:grid-cols-3 sm:gap-2 sm:overflow-visible sm:pb-0 lg:grid-cols-4"
      >
        {effectiveTiles.map((tile) => (
          <MatrixTile key={tile.tile_id} tile={tile} onNavigate={scrollToTile} />
        ))}
      </div>
      <CarouselDots
        containerId="matrix-overture-scroller"
        tone="light"
        className="mt-3 sm:hidden"
      />
    </section>
  )
}

// ---------------------------------------------------------------------------
// Mock-first tile synthesis from existing ReportPayload.
//
// Each tile mirrors LookupSummaryTile so the live-wire swap-in is mechanical:
// replace synthesizeTilesFromPayload(payload) with the response.tiles[] from
// lookupSummary(). target_section_id values map to the existing section root
// IDs CallCardsGrid already scrolls to (gene_context_snapshot, etc.).
// ---------------------------------------------------------------------------

function safeCount(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  return null
}

function synthesizeTilesFromPayload(payload: ReportPayload): LookupSummaryTile[] {
  const tiles: LookupSummaryTile[] = []

  // 1. Population (gnomAD)
  const popFreq = payload.population_frequency_detail
  const popLabel = popFreq && typeof popFreq === 'object' && 'allele_frequency_overall' in popFreq
    ? formatAlleleFreq((popFreq as { allele_frequency_overall?: unknown }).allele_frequency_overall)
    : 'gnomAD overall'
  tiles.push({
    tile_id: 'population_frequency',
    title: 'Population (gnomAD)',
    primary_label: popLabel,
    support_badges: ['v4'],
    source_status: popFreq ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'population_frequency',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 2. ClinVar classification — lives in §3 Clinical evidence after Slice A.
  const classification = payload.report_profile?.header?.classification ?? payload.acmg_classification ?? ''
  tiles.push({
    tile_id: 'clinvar_classification',
    title: 'ClinVar verdict',
    primary_label: classification || 'Not classified',
    support_badges: ['ClinVar'],
    source_status: classification ? 'available' : 'unavailable',
    ui_color_theme: 'classification',
    target_section_id: 'clinical_evidence',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 3. In-silico ensemble
  const predictors = payload.in_silico_predictions?.cards?.filter((c) => c.name !== 'AlphaMissense') ?? []
  const damagingN = predictors.filter((c) => c.verdict === 'damaging').length
  tiles.push({
    tile_id: 'in_silico',
    title: 'In-silico ensemble',
    primary_label: predictors.length
      ? `${damagingN}/${predictors.length} damaging`
      : 'No predictors',
    support_badges: ['SpliceAI · REVEL · CADD'],
    source_status: predictors.length ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'evidence_by_source',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 4. Publications
  const pubsTotal = safeCount(payload.publications_literature?.total_count)
    ?? safeCount(payload.publications_callout?.total_count)
  tiles.push({
    tile_id: 'publications',
    title: 'Publications',
    primary_label: pubsTotal != null ? `${pubsTotal.toLocaleString()} papers` : 'No publications',
    support_badges: ['PubMed · LitVar2'],
    source_status: pubsTotal && pubsTotal > 0 ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'publications',
    target_panel_id: null,
    fetch_section_id: 'publications',
    warnings: [],
  })

  // 5. Curated variants
  const curated = payload.curated_variants_distribution
  tiles.push({
    tile_id: 'curated_variants',
    title: 'Curated variants',
    primary_label: curated ? `${curated.total.toLocaleString()} variants` : 'No data',
    support_badges: ['ClinVar curated'],
    source_status: curated ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'curated_variants',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 6. Active trials
  const trials = payload.report_profile?.therapies_trials?.trial_rows ?? []
  tiles.push({
    tile_id: 'trials',
    title: 'Active trials',
    primary_label: trials.length ? `${trials.length} trial${trials.length === 1 ? '' : 's'}` : 'No active trials',
    support_badges: ['ClinicalTrials.gov'],
    source_status: trials.length ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'trials',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 7. Associated conditions
  const conditions = payload.associated_conditions
  const conditionsCount = Array.isArray(conditions) ? conditions.length : 0
  tiles.push({
    tile_id: 'conditions',
    title: 'Conditions',
    primary_label: conditionsCount ? `${conditionsCount} associated` : 'No conditions',
    support_badges: ['OMIM · MONDO'],
    source_status: conditionsCount ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'associated_conditions',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 8. Gene context
  const gcs = payload.report_profile?.gene_context_snapshot
  tiles.push({
    tile_id: 'gene_context',
    title: 'Gene context',
    primary_label: gcs?.gene ?? 'Gene profile',
    support_badges: ['Ensembl · MANE'],
    source_status: gcs ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'gene_context',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 9. ACMG criteria — lives in §3 Clinical evidence after Slice A
  // restructure.
  const acmg = payload.acmg_criteria_scaffold
  const acmgCount = acmg?.criteria?.length ?? 0
  tiles.push({
    tile_id: 'acmg',
    title: 'ACMG criteria',
    primary_label: acmgCount ? `${acmgCount} criteria` : 'Not scaffolded',
    support_badges: ['Eamos scaffold'],
    source_status: acmgCount ? 'available' : 'unavailable',
    ui_color_theme: 'neutral',
    target_section_id: 'clinical_evidence',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 10. AI summary
  tiles.push({
    tile_id: 'ai_summary',
    title: 'AI summary',
    primary_label: 'Deterministic synthesis',
    support_badges: ['Cited · sourced'],
    source_status: 'available',
    ui_color_theme: 'neutral',
    target_section_id: 'ai_summary',
    target_panel_id: null,
    fetch_section_id: null,
    warnings: [],
  })

  // 11. Premium-gated — ClinGen VCEP narrative (Wave-3 M-005 surface).
  tiles.push({
    tile_id: 'clingen_vcep',
    title: 'ClinGen VCEP',
    primary_label: 'Expert-panel narrative',
    support_badges: ['Premium'],
    source_status: 'premium_gated',
    ui_color_theme: 'premium',
    target_section_id: 'clinical_evidence',
    target_panel_id: null,
    fetch_section_id: 'clingen_vcep',
    warnings: [],
  })

  // 12. Premium-gated — Computational deep dive (Wave-3 M-004 surface).
  tiles.push({
    tile_id: 'computational_deep_dive',
    title: 'Deep dive',
    primary_label: 'Computational details',
    support_badges: ['Premium'],
    source_status: 'premium_gated',
    ui_color_theme: 'premium',
    target_section_id: 'evidence_by_source',
    target_panel_id: null,
    fetch_section_id: 'computational_deep_dive',
    warnings: [],
  })

  return tiles
}

function formatAlleleFreq(v: unknown): string {
  if (typeof v !== 'number' || !Number.isFinite(v)) return 'No AF'
  if (v === 0) return 'AF 0'
  if (v < 1e-5) return `AF <1e-5`
  if (v < 1e-3) return `AF ${(v * 1e5).toFixed(1)}e-5`
  return `AF ${(v * 100).toFixed(v >= 0.01 ? 2 : 3)}%`
}
