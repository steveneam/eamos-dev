'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { WorkRailSection } from '@/components/layout/WorkRail'
import { IconRelated } from '@/components/icons/Icon'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import { CARD_ORDER, themeForCallCard } from '@/components/report/CallCardsGrid'
import { useLibrary } from '@/components/library/useLibrary'
import {
  buildReportHrefV1,
  buildWorkbenchHrefV1,
  type RelatedVariantItemV1,
  type RelatedVariantRelationshipV1,
} from '@/lib/backend'
import {
  getRelatedVariants,
  saveCanonicalVariant,
  sendCanonicalVariantToBatch,
  stashPaperTarget,
} from '@/lib/report-workflow'
import type { LookupResponse } from '@/lib/backend'

const TIER_LABEL_FULL: Record<string, string> = {
  pathogenic: 'Pathogenic',
  likely_pathogenic: 'Likely pathogenic',
  vus: 'VUS',
  likely_benign: 'Likely benign',
  benign: 'Benign',
}

const RELATION_LABEL: Record<RelatedVariantRelationshipV1, string> = {
  nearby: 'Nearby',
  same_gene: 'Same gene',
  same_class: 'Same class',
  same_condition: 'Same condition',
}

interface MergedRelated {
  item: RelatedVariantItemV1
  relationships: RelatedVariantRelationshipV1[]
}

function backendReportHref(item: RelatedVariantItemV1): string {
  const href = item.report_href.trim()
  if (href.startsWith('/report?') && !href.startsWith('//')) {
    return href.includes('from=') ? href : `${href}&from=report`
  }
  return buildReportHrefV1(item.variant, 'report')
}

/** Backend-derived related variants only. The former same-condition summary
 *  rows and frontend reclassification lanes were removed because neither was a
 *  variant identity that could safely hand off to another surface. */
export function RelatedVariants({
  data,
  viewMetricsEnabled = true,
}: {
  data: LookupResponse
  viewMetricsEnabled?: boolean
}) {
  const router = useRouter()
  const { variants: savedVariants } = useLibrary()
  const payload = data.report_payload
  const header = payload.report_profile?.header
  const row = payload.variant_summary_rows[0]
  const transcriptHgvs = row?.transcript_hgvs ?? null
  const gene = header?.gene ?? row?.gene ?? null
  const cdna = header?.cdna ?? transcriptHgvs?.split(':').at(-1) ?? null
  const transcript =
    header?.transcript ?? (transcriptHgvs?.includes(':') ? transcriptHgvs.split(':')[0] : null)
  const requestKey = `${gene ?? ''}\u001f${cdna ?? ''}\u001f${transcript ?? ''}`
  const [state, setState] = useState<
    | { kind: 'loading' }
    | { kind: 'ready'; requestKey: string; items: RelatedVariantItemV1[]; warnings: string[] }
    | { kind: 'error'; requestKey: string }
  >({ kind: 'loading' })

  useEffect(() => {
    if (!viewMetricsEnabled || !gene || !cdna) return
    const controller = new AbortController()
    void getRelatedVariants({ gene, cdna, transcript }, controller.signal)
      .then((result) => setState({ kind: 'ready', requestKey, items: result.items, warnings: result.warnings }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({ kind: 'error', requestKey })
      })
    return () => controller.abort()
  }, [cdna, gene, requestKey, transcript, viewMetricsEnabled])

  const activeState = state.kind !== 'loading' && state.requestKey !== requestKey ? { kind: 'loading' as const } : state

  const items: MergedRelated[] = (() => {
    if (activeState.kind !== 'ready') return []
    const merged = new Map<string, MergedRelated>()
    for (const item of activeState.items) {
      const existing = merged.get(item.variant.variant_key)
      if (existing) {
        if (!existing.relationships.includes(item.relationship)) existing.relationships.push(item.relationship)
      } else {
        merged.set(item.variant.variant_key, { item, relationships: [item.relationship] })
      }
    }
    return [...merged.values()]
  })()

  const openPaper = (item: RelatedVariantItemV1) => {
    stashPaperTarget(item.variant)
    router.push('/paper')
  }

  const openBatch = (item: RelatedVariantItemV1) => {
    sendCanonicalVariantToBatch(item.variant, 'Related variants')
    router.push('/compare')
  }

  return (
    <WorkRailSection title="Related variants" icon={<IconRelated size={14} />} defaultOpen={false} meta={items.length}>
      {!viewMetricsEnabled ? (
        <p className="lib-guardrail">Related variants are unavailable in the offline fixture.</p>
      ) : !gene || !cdna ? (
        <p className="lib-guardrail">A resolved gene and cDNA change are required.</p>
      ) : activeState.kind === 'loading' ? (
        <p className="lib-guardrail" role="status">Loading source-backed relationships…</p>
      ) : activeState.kind === 'error' ? (
        <p className="lib-guardrail" role="status">Related variants are temporarily unavailable.</p>
      ) : items.length === 0 ? (
        <p className="lib-guardrail">No source-backed related variants were returned.</p>
      ) : (
        <div className="rel-list">
          {items.map(({ item, relationships }) => {
            const variant = item.variant
            const identity = `${variant.gene} ${variant.cdna}`.toLowerCase()
            const saved = savedVariants.some((candidate) => candidate.id === identity)
            const themes = CARD_ORDER.map((cardId) => {
              const card = item.evidence_axis_summary?.cards.find((candidate) => candidate.card_id === cardId)
              return card ? themeForCallCard(card) : null
            })
            return (
              <article className="rel-card" key={variant.variant_key}>
                <Link
                  className="rel-card-main"
                  href={backendReportHref(item)}
                  title={`Open the report for ${variant.gene} ${variant.cdna}`}
                >
                  <div className="rel-card-top">
                    <span className="rel-id">
                      <span className="rel-gene">{variant.gene}</span>
                      <span className="rel-cdna">{variant.cdna}</span>
                    </span>
                    {item.classification && (
                      <ClassificationBadge classification={TIER_LABEL_FULL[item.classification]} />
                    )}
                  </div>
                  <div className="rel-card-bottom">
                    <span className="rel-tags">
                      {relationships.map((relationship) => (
                        <span className="rel-tag" key={relationship}>{RELATION_LABEL[relationship]}</span>
                      ))}
                    </span>
                    <span className="rel-chips" aria-label="Available evidence axes">
                      {themes.map((theme, index) => (
                        <span
                          key={CARD_ORDER[index]}
                          className={theme ? 'rel-chip' : 'rel-chip ghost'}
                          style={theme ? { background: theme.bg, borderColor: theme.border } : undefined}
                        />
                      ))}
                    </span>
                  </div>
                </Link>
                <div className="rel-actions" aria-label={`Actions for ${variant.gene} ${variant.cdna}`}>
                  <Link href={buildWorkbenchHrefV1(variant, { tool: 'viewer' })}>Workbench</Link>
                  <button type="button" onClick={() => openPaper(item)}>Papers</button>
                  <button type="button" onClick={() => openBatch(item)}>Batch</button>
                  <button
                    type="button"
                    disabled={saved}
                    onClick={() => saveCanonicalVariant(variant, item.classification)}
                  >
                    {saved ? 'Saved' : 'Save'}
                  </button>
                </div>
                <p className="rel-source">
                  {item.source_disclosure.provider_label} · {item.source_disclosure.source_status}
                </p>
              </article>
            )
          })}
          {activeState.kind === 'ready' && activeState.warnings.length > 0 && (
            <p className="lib-guardrail">Some related records carry source warnings.</p>
          )}
        </div>
      )}

      <p className="lib-guardrail">
        Relationships and evidence axes come from the typed backend response. They are not popularity rankings.
      </p>

      <style>{`
        .rel-list { display: grid; gap: 8px; }
        .rel-card { border: 0.5px solid var(--line); border-radius: var(--r-md); background: var(--bg); box-shadow: var(--elev-1); overflow: hidden; }
        .rel-card-main { display: block; padding: 9px 11px 7px; color: inherit; text-decoration: none; }
        .rel-card-main:hover { background: var(--bg-soft); }
        .rel-card-main:focus-visible, .rel-actions a:focus-visible, .rel-actions button:focus-visible { outline: 2px solid var(--teal); outline-offset: -2px; }
        .rel-card-top, .rel-card-bottom { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .rel-id, .rel-tags, .rel-chips { display: inline-flex; align-items: center; gap: 5px; min-width: 0; }
        .rel-gene { font-size: 12.5px; font-weight: 650; color: var(--ink); }
        .rel-cdna { font-size: 12px; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .rel-card-bottom { margin-top: 7px; }
        .rel-tag { font-size: 8.5px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: var(--teal-deep); background: var(--teal-tint); border: 0.5px solid var(--teal-bdr); border-radius: 4px; padding: 1px 4px; }
        .rel-chip { width: 10px; height: 10px; border-radius: 2px; border: 1px solid transparent; }
        .rel-chip.ghost { background: transparent; border-style: dashed; border-color: var(--ink-5); }
        .rel-actions { display: flex; flex-wrap: wrap; border-top: 0.5px solid var(--line); }
        .rel-actions a, .rel-actions button { min-height: 44px; flex: 1 1 auto; display: inline-flex; align-items: center; justify-content: center; padding: 5px 7px; border: 0; border-right: 0.5px solid var(--line); background: transparent; color: var(--ink-3); font: 600 10.5px var(--body); text-decoration: none; cursor: pointer; }
        .rel-actions a:hover, .rel-actions button:hover:not(:disabled) { background: var(--bg-soft); color: var(--ink); }
        .rel-actions button:disabled { color: var(--ink-5); cursor: default; }
        .rel-source { margin: 0; padding: 5px 9px; background: var(--bg-soft); color: var(--ink-4); font-size: 9.5px; }
      `}</style>
    </WorkRailSection>
  )
}
