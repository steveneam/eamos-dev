'use client'

import { useEffect, useState } from 'react'
import { WorkRailSection } from '@/components/layout/WorkRail'

/**
 * Scroll-spy "On this page" jump-list over the report module anchors that
 * ReportBody renders (`<div id className="scroll-mt-24" />`). Anchors are
 * unconditional on the ready state (population_frequency may be an empty anchor
 * — still a valid scroll target), so we list the fixed set and let an
 * IntersectionObserver drive the active highlight. Design §2.6 / ground-truth §6.
 */
const ANCHORS: { id: string; label: string }[] = [
  { id: 'clinical_evidence', label: 'Clinical evidence' },
  { id: 'evidence_by_source', label: 'In-silico predictions' },
  { id: 'population_frequency', label: 'Population frequency' },
  { id: 'gene_context', label: 'Gene & locus' },
  { id: 'associated_conditions', label: 'Disease & conditions' },
  { id: 'publications', label: 'Publications' },
  { id: 'trials', label: 'Trials' },
  { id: 'ai_summary', label: 'AI summary' },
]

export function ReportSectionNav() {
  const [active, setActive] = useState<string | null>(null)

  useEffect(() => {
    const els = ANCHORS.map((a) => document.getElementById(a.id)).filter((el): el is HTMLElement => Boolean(el))
    if (els.length === 0) return
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length === 0) return
        visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        setActive(visible[0].target.id)
      },
      { rootMargin: '-80px 0px -70% 0px', threshold: 0 },
    )
    for (const el of els) obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <WorkRailSection title="On this page" defaultOpen={false}>
      <nav className="lib-pagenav" aria-label="Report sections">
        {ANCHORS.map((a) => (
          <button
            key={a.id}
            type="button"
            className="lib-pagenav-item"
            aria-current={active === a.id ? 'true' : undefined}
            onClick={() => document.getElementById(a.id)?.scrollIntoView({ behavior: 'smooth' })}
          >
            {a.label}
          </button>
        ))}
      </nav>
    </WorkRailSection>
  )
}
