'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

// ReportRail — sticky right-side navigation rail at xl+ viewports.
//
// Three jobs:
//   1. TOC + scroll-spy so a long report scrolls predictably.
//   2. Cite button (sets `?cite=1`, picked up by CiteChip's modal effect).
//   3. Lightweight provenance footer.
//
// Hidden by Tailwind `hidden xl:block` at the call site so mobile/tablet
// layouts are unchanged; the report on those viewports continues to use the
// bottom-left Feedback chip as the only persistent action.

export interface RailSection {
  /** DOM element id (must match the anchor div on the page). */
  id: string
  /** Section number shown as a leading chip. Falsy → no chip rendered. */
  num?: number | null
  /** Display label. */
  label: string
}

const DEFAULT_SECTIONS: RailSection[] = [
  { id: 'population_frequency', num: 1, label: 'Population frequency' },
  { id: 'evidence_by_source', num: 2, label: 'Evidence by source' },
  { id: 'expert_panel', num: null, label: 'Expert panel' },
  { id: 'gene_context', num: 3, label: 'Gene context' },
  { id: 'associated_conditions', num: 4, label: 'Disease & conditions' },
  { id: 'publications', num: 5, label: 'Publications' },
  { id: 'trials', num: 6, label: 'Trials & therapies' },
  { id: 'ai_summary', num: 7, label: 'AI summary' },
]

interface ReportRailProps {
  sections?: RailSection[]
  reportVersion?: string
}

export function ReportRail({ sections = DEFAULT_SECTIONS, reportVersion }: ReportRailProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [activeId, setActiveId] = useState<string | null>(null)

  // Scroll-spy via IntersectionObserver. Track which section anchor sits
  // closest to the top of the viewport (with --ctx-h offset for the sticky
  // top nav). One observer reused across all anchors; the section whose
  // top crosses the rootMargin band wins.
  useEffect(() => {
    const elements = sections
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => el !== null)
    if (elements.length === 0) return

    // First fold offset roughly matches the sticky variant ribbon's pin position.
    const observer = new IntersectionObserver(
      (entries) => {
        // Pick the entry with the smallest positive `top` (just below the band).
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) {
          setActiveId(visible[0].target.id)
        }
      },
      { rootMargin: '-100px 0px -55% 0px', threshold: [0, 1] },
    )
    for (const el of elements) observer.observe(el)
    return () => observer.disconnect()
  }, [sections])

  const jumpTo = useCallback((id: string) => {
    const el = document.getElementById(id)
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const openCite = useCallback(() => {
    const params = new URLSearchParams(searchParams?.toString() ?? '')
    params.set('cite', '1')
    router.replace(`?${params.toString()}`, { scroll: false })
  }, [router, searchParams])

  return (
    <nav
      aria-label="Report sections"
      style={{
        position: 'sticky',
        top: 'calc(var(--nav-h, 60px) + var(--ctx-h, 48px) + 12px)',
        alignSelf: 'flex-start',
        width: 'var(--rail-w, 240px)',
        display: 'flex',
        flexDirection: 'column',
        gap: 18,
        paddingTop: 6,
      }}
    >
      <div>
        <div
          style={{
            fontSize: 10.5,
            fontWeight: 700,
            color: 'var(--ink-4)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: 10,
            paddingLeft: 2,
          }}
        >
          On this report
        </div>
        <ol
          style={{
            listStyle: 'none',
            margin: 0,
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
          }}
        >
          {sections.map((s) => {
            const isActive = activeId === s.id
            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => jumpTo(s.id)}
                  aria-current={isActive ? 'true' : undefined}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    width: '100%',
                    padding: '7px 10px 7px 12px',
                    background: isActive ? 'var(--bg-soft2, var(--bg-soft))' : 'transparent',
                    border: 'none',
                    borderLeft: isActive ? '2px solid var(--teal, #1d9e75)' : '2px solid transparent',
                    color: isActive ? 'var(--ink)' : 'var(--ink-3)',
                    fontFamily: 'var(--body)',
                    fontSize: 12.5,
                    textAlign: 'left',
                    cursor: 'pointer',
                    borderRadius: '0 6px 6px 0',
                    transition: 'background 120ms ease, color 120ms ease, border-color 120ms ease',
                  }}
                >
                  {s.num != null && (
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 18,
                        height: 18,
                        borderRadius: 999,
                        fontSize: 10.5,
                        fontWeight: 600,
                        fontFamily: 'var(--mono)',
                        background: isActive ? 'var(--teal, #1d9e75)' : 'var(--bg-soft, #f0e9dc)',
                        color: isActive ? '#fff' : 'var(--ink-4)',
                        flexShrink: 0,
                      }}
                    >
                      {s.num}
                    </span>
                  )}
                  <span style={{ flex: '1 1 auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {s.label}
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
      </div>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          paddingLeft: 12,
          paddingRight: 4,
        }}
      >
        <button
          type="button"
          onClick={openCite}
          className="eamos-toggle-btn"
          style={{
            justifyContent: 'flex-start',
            width: '100%',
            padding: '7px 10px',
            fontSize: 12,
          }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M4 7V4h7" />
            <path d="M4 20v-3" />
            <path d="M17 4h3v3" />
            <path d="M20 20h-3" />
            <rect x="8" y="8" width="8" height="8" rx="1" />
          </svg>
          Cite this report
        </button>
      </div>

      {reportVersion && (
        <div
          style={{
            fontSize: 10.5,
            color: 'var(--ink-4)',
            paddingLeft: 12,
            paddingTop: 8,
            borderTop: '0.5px solid var(--line)',
          }}
        >
          Eamos report · v{reportVersion}
        </div>
      )}
    </nav>
  )
}
