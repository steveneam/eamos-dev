'use client'

import { useEffect, useState } from 'react'
import { WorkRailSection } from '@/components/layout/WorkRail'
import { IconList } from '@/components/icons/Icon'
import { REPORT_SECTION_NAV_ITEMS } from '@/lib/report-section-registry'

/**
 * Scroll-spy "On this page" jump-list over the report module anchors that
 * ReportBody renders (`<div id className="scroll-mt-24" />`). Anchors are
 * unconditional on the ready state (population_frequency may be an empty anchor
 * — still a valid scroll target), so we list the fixed set and let an
 * IntersectionObserver drive the active highlight. Design §2.6 / ground-truth §6.
 */
export function ReportSectionNav() {
  const [active, setActive] = useState<string | null>(null)

  useEffect(() => {
    const els = REPORT_SECTION_NAV_ITEMS
      .map((a) => document.getElementById(a.id))
      .filter((el): el is HTMLElement => Boolean(el))
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
    <WorkRailSection title="On this page" icon={<IconList size={14} />} defaultOpen={false}>
      <nav className="lib-pagenav" aria-label="Report sections">
        {REPORT_SECTION_NAV_ITEMS.map((a) => (
          <button
            key={a.id}
            type="button"
            className="lib-pagenav-item"
            aria-current={active === a.id ? 'location' : undefined}
            onClick={() => document.getElementById(a.id)?.scrollIntoView({ behavior: 'smooth' })}
          >
            {a.label}
          </button>
        ))}
      </nav>
    </WorkRailSection>
  )
}
