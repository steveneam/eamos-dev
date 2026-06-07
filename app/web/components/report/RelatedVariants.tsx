'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { WorkRailSection } from '@/components/layout/WorkRail'
import { tierFromText } from '@/components/library/tier'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import { reportHrefForQuery } from '@/lib/variant-search'
import { MOCK_PANELS, getMockPanel, panelBadge } from '@/lib/panels.mock'
import type { LookupResponse, NearbyVariant } from '@/lib/backend'

// Reuse the same classification ramp tokens as the call cards / hero strip so the
// mini chips match by construction. Unknown tier → neutral grey.
const TIER_TO_COLOR: Record<string, string> = {
  pathogenic: 'var(--cls-path-text)',
  likely_pathogenic: 'var(--cls-lpath-text)',
  vus: 'var(--cls-vus-text)',
  likely_benign: 'var(--cls-lben-text)',
  benign: 'var(--cls-ben-text)',
}
const TIER_LABEL_FULL: Record<string, string> = {
  pathogenic: 'Pathogenic',
  likely_pathogenic: 'Likely pathogenic',
  vus: 'VUS',
  likely_benign: 'Likely benign',
  benign: 'Benign',
}
const REL_MOCK_TIP =
  'Preview — per-axis calls, view counts and recency are illustrative and update once the data source is connected.'

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

  const nearbyRow = (nv: NearbyVariant) => {
    const clinColor = (nv.classification && TIER_TO_COLOR[nv.classification]) || 'var(--cls-na-text)'
    const clsLabel = nv.classification ? TIER_LABEL_FULL[nv.classification] ?? null : null
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
            <span className="rel-tag" title={`New to Eamos. ${REL_MOCK_TIP}`}>New</span>
            <span className="rel-gene">{gene}</span>
            <span className="rel-cdna">{nv.hgvs}</span>
          </span>
          {clsLabel && <ClassificationBadge classification={clsLabel} />}
        </div>
        {/* Bottom — views · exact date (left) + 4 axis squares (right) */}
        <div className="rel-card-bottom">
          <span className="rel-meta" title={REL_MOCK_TIP}>1,043 views · added 5 Jun 2026</span>
          <span
            className="rel-chips"
            role="img"
            aria-label="Evidence axes: Computational, Clinical, Population, Lab & Functional"
            title="Evidence axes (Computational · Clinical · Population · Lab & Functional). Only the clinical classification is known per variant today; the rest fill in when wired."
          >
            {[0, 1, 2, 3].map((i) => (
              <span
                key={i}
                className={i === 1 ? 'rel-chip' : 'rel-chip ghost'}
                style={i === 1 ? { background: clinColor } : undefined}
              />
            ))}
          </span>
        </div>
      </button>
    )
  }

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
        .rel-gene { font-family: var(--mono); font-size: 12.5px; font-weight: 600; color: var(--ink); flex-shrink: 0; }
        .rel-cdna { font-family: var(--mono); font-size: 12px; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .rel-card-bottom { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 7px; }
        .rel-meta { font-size: 10.5px; color: var(--ink-4); border-bottom: 1px dotted var(--ink-5); cursor: help; }
        .rel-chips { display: inline-flex; gap: 3px; flex-shrink: 0; }
        .rel-chip { width: 10px; height: 10px; border-radius: 2px; }
        .rel-chip.ghost { background: transparent; border: 1px dashed var(--ink-5); }
      `}</style>
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
