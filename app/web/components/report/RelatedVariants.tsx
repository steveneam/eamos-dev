'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { WorkRailSection } from '@/components/layout/WorkRail'
import { IconRelated } from '@/components/icons/Icon'
import { tierFromText } from '@/components/library/tier'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import { CARD_ORDER, themeForCallCard } from '@/components/report/CallCardsGrid'
import { reportHrefForQuery } from '@/lib/variant-search'
import { getReportView, type VariantViewMetric } from '@/lib/report-views'
import type { LookupResponse, NearbyVariant } from '@/lib/backend'

const TIER_LABEL_FULL: Record<string, string> = {
  pathogenic: 'Pathogenic',
  likely_pathogenic: 'Likely pathogenic',
  vus: 'VUS',
  likely_benign: 'Likely benign',
  benign: 'Benign',
}
/**
 * Evidence-grounded related-variants feed (Phase 4). Lanes come from data the
 * report already computes: in-gene and same-class rows from
 * locus_context.nearby_variants, plus same-condition rows from
 * associated_conditions. Closed by default (spec §5 guardrail).
 * Design: phase-3-4-design.md §4.
 */
export function RelatedVariants({
  data,
  viewMetricsEnabled = true,
}: {
  data: LookupResponse
  viewMetricsEnabled?: boolean
}) {
  const router = useRouter()
  const payload = data.report_payload
  const locus = payload.locus_context
  const header = payload.report_profile?.header
  const gene = header?.gene ?? locus?.gene ?? payload.variant_summary_rows[0]?.gene ?? null
  const queriedTier = tierFromText(header?.classification)

  const goReport = (hgvs: string) => {
    if (!gene) return
    const href = reportHrefForQuery(`${gene} ${hgvs}`)
    if (href) router.push(href)
  }

  const nearby = useMemo(() => locus?.nearby_variants ?? [], [locus])
  const sameClass = useMemo(
    () => (queriedTier ? nearby.filter((nv) => nv.classification === queriedTier) : []),
    [nearby, queriedTier],
  )
  const conditions = payload.associated_conditions ?? []
  const populationAf = payload.report_profile?.population_frequency?.overall?.total?.allele_frequency ?? null
  const callCards = payload.call_cards?.cards ?? []
  const railAxisThemes = CARD_ORDER.map((cardId) => {
    const card = callCards.find((candidate) => candidate.card_id === cardId)
    return card ? themeForCallCard(card, populationAf) : null
  })
  const relatedQueryIds = useMemo(() => {
    if (!gene) return []
    return Array.from(new Set(nearby.map((nv) => relatedVariantQueryId(gene, nv))))
  }, [gene, nearby])
  const relatedQueryKey = relatedQueryIds.join('\u001f')
  const [viewMetrics, setViewMetrics] = useState<Record<string, VariantViewMetric | null>>({})

  useEffect(() => {
    let cancelled = false
    if (!viewMetricsEnabled || relatedQueryIds.length === 0) return () => {
      cancelled = true
    }
    void Promise.all(
      relatedQueryIds.map(async (queryId) => [queryId.toLowerCase(), await getReportView(queryId)] as const),
    ).then((entries) => {
      if (!cancelled) setViewMetrics(Object.fromEntries(entries))
    })
    return () => {
      cancelled = true
    }
  }, [relatedQueryKey, relatedQueryIds, viewMetricsEnabled])

  const hasAny = nearby.length > 0 || conditions.length > 0
  if (!hasAny) return null

  const nearbyRow = (nv: NearbyVariant, relationLabel: string) => {
    const clsLabel = nv.classification ? TIER_LABEL_FULL[nv.classification] ?? null : null
    const queryId = gene ? relatedVariantQueryId(gene, nv) : null
    const metricKey = queryId?.toLowerCase() ?? ''
    const metricLoaded = viewMetricsEnabled && metricKey ? Object.prototype.hasOwnProperty.call(viewMetrics, metricKey) : false
    const metric = metricKey ? viewMetrics[metricKey] ?? null : null
    return (
      <button
        type="button"
        className="rel-card"
        key={`${nv.cds_pos}-${nv.hgvs}`}
        onClick={() => goReport(nv.hgvs)}
        title={`Open the report for ${gene} ${nv.hgvs}`}
      >
        {/* Top — New tag (left) + variant, classification pill (right) */}
        <div className="rel-card-top">
          <span className="rel-id">
            <span className="rel-tag">{relationLabel}</span>
            <span className="rel-gene">{gene}</span>
            <span className="rel-cdna">{nv.hgvs}</span>
          </span>
          {clsLabel && <ClassificationBadge classification={clsLabel} />}
        </div>
        {/* Bottom — views · exact date (left) + 4 axis squares (right) */}
        <div className="rel-card-bottom">
          <span className="rel-meta" title={queryId ? `Backend view metadata for ${queryId}` : undefined}>
            {formatVariantViewMetric(metric, metricLoaded, viewMetricsEnabled)}
          </span>
          <span
            className="rel-chips"
            role="img"
            aria-label="Evidence axes: Computational, Clinical, Population, Lab & Functional"
            title="Evidence axes match the report call cards: Computational, Clinical, Population, Lab & Functional."
          >
            {railAxisThemes.map((theme, i) => (
              <span
                key={i}
                className={theme ? 'rel-chip' : 'rel-chip ghost'}
                style={theme ? { background: theme.bg, borderColor: theme.border } : undefined}
              />
            ))}
          </span>
        </div>
      </button>
    )
  }

  return (
    <WorkRailSection title="Related variants" icon={<IconRelated size={14} />} defaultOpen={false}>
      {nearby.length > 0 && (
        <Lane label="In this gene" count={nearby.length}>
          {nearby.map((nv) => nearbyRow(nv, 'Gene'))}
        </Lane>
      )}

      {sameClass.length > 0 && (
        <Lane label="Same class · region" count={sameClass.length}>
          {sameClass.map((nv) => nearbyRow(nv, 'Class'))}
        </Lane>
      )}

      {conditions.length > 0 && (
        <Lane label="Same condition" count={conditions.length}>
          {conditions.map((c) => (
            <div className="lib-cond-row" key={c.name}>
              <span className="cond-n">{c.case_count}</span>
              <span className="cond-name" title={c.name}>{c.name}</span>
              <span className="cond-ev">{c.evidence_level}</span>
            </div>
          ))}
        </Lane>
      )}

      <p className="lib-guardrail">
        Suggestions are based on real genomic relationships in this report — shared gene, condition,
        genomic region, or variant class — not popularity.
      </p>

      <style>{`
        .rel-card {
          display: block; width: 100%; text-align: left;
          border: 0.5px solid var(--line);
          border-radius: var(--r-md);
          background: var(--bg);
          padding: 9px 11px;
          margin-bottom: 7px;
          box-shadow: var(--elev-1);
          cursor: pointer;
          font: inherit;
          transition: border-color var(--dur-1) var(--ease-standard), box-shadow var(--dur-1) var(--ease-standard);
        }
        .rel-card:hover { border-color: var(--ink-5); box-shadow: var(--elev-2); }
        .rel-card:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); border-color: var(--teal); }
        .rel-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .rel-id { display: inline-flex; align-items: center; gap: 6px; min-width: 0; }
        .rel-tag {
          flex-shrink: 0;
          font-size: 8.5px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
          color: var(--teal-deep); background: var(--teal-tint);
          border: 0.5px solid var(--teal-bdr); border-radius: 4px;
          padding: 1px 5px;
        }
        .rel-gene { font-family: var(--body); font-size: 12.5px; font-weight: 600; color: var(--ink); flex-shrink: 0; }
        .rel-cdna { font-family: var(--body); font-variant-numeric: tabular-nums; font-size: 12px; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .rel-card-bottom { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 7px; }
        .rel-meta { font-size: 10.5px; color: var(--ink-4); }
        .rel-chips { display: inline-flex; gap: 3px; flex-shrink: 0; }
        .rel-chip { width: 10px; height: 10px; border-radius: 2px; border: 1px solid transparent; }
        .rel-chip.ghost { background: transparent; border: 1px dashed var(--ink-5); }
      `}</style>
    </WorkRailSection>
  )
}

function relatedVariantQueryId(gene: string, variant: NearbyVariant): string {
  return `${gene} ${variant.hgvs}`.trim()
}

function formatVariantViewMetric(
  metric: VariantViewMetric | null,
  loaded: boolean,
  enabled: boolean,
): string {
  if (!enabled) return 'Views unavailable · Updated unavailable'
  if (!loaded) return 'Views loading · Updated loading'
  if (!metric) return 'Views unavailable · Updated unavailable'
  const views = `${metric.view_count.toLocaleString()} ${metric.view_count === 1 ? 'view' : 'views'}`
  const updated = metric.last_viewed ? `Updated ${formatDate(metric.last_viewed)}` : 'Updated unavailable'
  return `${views} · ${updated}`
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

function Lane({ label, count, children }: { label: string; count: number; children: React.ReactNode }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="lib-lane" data-open={open ? 'true' : 'false'}>
      <button type="button" className="lib-lane-head" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <span className="lib-lane-chev" aria-hidden>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" width="11" height="11">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
        <span className="lib-lane-label">{label}</span>
        <span className="lib-count">{count}</span>
      </button>
      <div className="lib-lane-body">
        <div className="lib-lane-rows">{children}</div>
      </div>
    </div>
  )
}
