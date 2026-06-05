'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { WorkRailSection } from '@/components/layout/WorkRail'
import { VariantCardRow } from '@/components/library/VariantCardRow'
import { tierFromText } from '@/components/library/tier'
import { reportHrefForQuery } from '@/lib/variant-search'
import { saveVariant } from '@/lib/variant-library'
import { MOCK_PANELS, getMockPanel, panelBadge } from '@/lib/panels.mock'
import type { LookupResponse, NearbyVariant } from '@/lib/backend'

/**
 * Evidence-grounded related-variants feed (Phase 4). Four lanes from data the
 * report already computes — no new fetch: In this gene + Same class·region from
 * locus_context.nearby_variants, Same condition from associated_conditions, Same
 * panel from the bundled panel catalogue. Closed by default (spec §5 guardrail).
 * Design: phase-3-4-design.md §4.
 */
export function RelatedVariants({ data }: { data: LookupResponse }) {
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
  const saveNearby = (nv: NearbyVariant) => {
    if (!gene) return
    const q = `${gene} ${nv.hgvs}`
    saveVariant({ gene, variant: nv.hgvs, query: q, raw: q }, { classification: nv.classification })
  }

  const nearby = useMemo(() => locus?.nearby_variants ?? [], [locus])
  const sameClass = useMemo(
    () => (queriedTier ? nearby.filter((nv) => nv.classification === queriedTier) : []),
    [nearby, queriedTier],
  )
  const conditions = payload.associated_conditions ?? []
  const panels = useMemo(
    () =>
      gene
        ? MOCK_PANELS.map((s) => getMockPanel(s.slug))
            .filter((p): p is NonNullable<typeof p> => Boolean(p))
            .filter((p) => p.genes.some((g) => g.symbol.toUpperCase() === gene.toUpperCase()))
        : [],
    [gene],
  )

  const hasAny = nearby.length > 0 || conditions.length > 0 || panels.length > 0
  if (!hasAny) return null

  const nearbyRow = (nv: NearbyVariant) => (
    <div className="lib-related-row" key={`${nv.cds_pos}-${nv.hgvs}`}>
      <VariantCardRow
        gene={gene}
        hgvs={nv.hgvs}
        classification={nv.classification}
        onOpen={() => goReport(nv.hgvs)}
      />
      <button
        type="button"
        className="lib-related-add"
        title="Save to library"
        aria-label={`Save ${gene} ${nv.hgvs} to library`}
        onClick={() => saveNearby(nv)}
      >
        +
      </button>
    </div>
  )

  return (
    <WorkRailSection title="Related variants" defaultOpen={false}>
      {nearby.length > 0 && (
        <Lane label="In this gene" count={nearby.length}>
          {nearby.map(nearbyRow)}
        </Lane>
      )}

      {sameClass.length > 0 && (
        <Lane label="Same class · region" count={sameClass.length}>
          {sameClass.map(nearbyRow)}
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

      {panels.length > 0 && (
        <Lane label="Same panel" count={panels.length}>
          <div className="lib-panel-row">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {panels.map((p) => {
                const b = panelBadge(p)
                return (
                  <span
                    key={p.slug}
                    style={{
                      display: 'inline-block',
                      padding: '1px 7px',
                      borderRadius: 6,
                      fontSize: 10.5,
                      fontWeight: 700,
                      background: b.bg,
                      color: b.text,
                      border: `0.5px solid ${b.border}`,
                    }}
                    title={p.name}
                  >
                    {p.name}
                  </span>
                )
              })}
            </div>
          </div>
        </Lane>
      )}

      <p className="lib-guardrail">
        Suggestions are based on real genomic relationships in this report — shared gene, condition,
        panel, or variant class — not popularity.
      </p>
    </WorkRailSection>
  )
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
