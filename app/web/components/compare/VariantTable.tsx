'use client'

import { useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { reportHrefForQuery } from '@/lib/variant-search'
import type { ParsedVariant } from '@/lib/variant-file'
import type { Panel } from '@/lib/backend'
import { panelBadge, type PanelBadge } from '@/lib/panels.mock'

type PanelMembership = { slug: string; badge: PanelBadge; symbols: Set<string> }

/**
 * Variant cohort table. Sticky header + an Excel-style split-pane: toggle "Split
 * view" to get two independently-scrolling viewports over the SAME rows, with a
 * draggable divider (compare row 5 against row 950 without losing your place).
 * Row virtualization is the follow-up for true 1000+ row performance.
 */
const PANE_HEIGHT = 560

function withFromCompare(href: string | null): string | null {
  if (!href) return null
  return href.includes('?') ? `${href}&from=compare` : `${href}?from=compare`
}

export function VariantTable({ rows, activePanels }: { rows: ParsedVariant[]; activePanels: Panel[] }) {
  const membership = useMemo<PanelMembership[]>(
    () =>
      activePanels.map((p) => ({
        slug: p.slug,
        badge: panelBadge(p),
        symbols: new Set(p.genes.map((g) => g.symbol.toUpperCase())),
      })),
    [activePanels],
  )
  const [split, setSplit] = useState(false)
  const [topFrac, setTopFrac] = useState(0.5)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const onPointerDown = (e: React.PointerEvent) => {
    dragging.current = true
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const frac = (e.clientY - rect.top) / rect.height
    setTopFrac(Math.min(0.85, Math.max(0.15, frac)))
  }
  const onPointerUp = (e: React.PointerEvent) => {
    dragging.current = false
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch {
      // capture may already be released
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
        {rows.length >= 2 && (
          <button
            type="button"
            aria-pressed={split}
            onClick={() => setSplit((s) => !s)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 11px',
              borderRadius: 8,
              border: `0.5px solid ${split ? 'var(--teal-bdr)' : 'var(--line-2)'}`,
              background: split ? 'var(--teal-tint)' : 'var(--bg)',
              color: split ? 'var(--teal-deep)' : 'var(--ink-2)',
              fontSize: 11.5,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <span aria-hidden>⊟</span> {split ? 'Single view' : 'Split view'}
          </button>
        )}
      </div>

      {split ? (
        <div
          ref={containerRef}
          style={{
            height: PANE_HEIGHT,
            display: 'flex',
            flexDirection: 'column',
            border: '0.5px solid var(--line)',
            borderRadius: 14,
            overflow: 'hidden',
          }}
        >
          <div style={{ flex: `${topFrac} 1 0`, overflow: 'auto', minHeight: 0 }}>
            <Table rows={rows} membership={membership} />
          </div>
          <div
            role="separator"
            aria-orientation="horizontal"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            style={{
              height: 12,
              flexShrink: 0,
              cursor: 'row-resize',
              background: 'var(--bg-soft2)',
              borderTop: '0.5px solid var(--line)',
              borderBottom: '0.5px solid var(--line)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              touchAction: 'none',
            }}
          >
            <span aria-hidden style={{ width: 34, height: 3, borderRadius: 2, background: 'var(--ink-5)' }} />
          </div>
          <div style={{ flex: `${1 - topFrac} 1 0`, overflow: 'auto', minHeight: 0 }}>
            <Table rows={rows} membership={membership} />
          </div>
        </div>
      ) : (
        <div
          style={{
            maxHeight: PANE_HEIGHT,
            overflow: 'auto',
            border: '0.5px solid var(--line)',
            borderRadius: 14,
          }}
        >
          <Table rows={rows} membership={membership} />
        </div>
      )}
    </div>
  )
}

function Table({ rows, membership }: { rows: ParsedVariant[]; membership: PanelMembership[] }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr>
          <Th style={{ width: 44, textAlign: 'right' }}>#</Th>
          <Th>Gene</Th>
          <Th>Variant</Th>
          <Th>Source line</Th>
          <Th style={{ textAlign: 'right' }}>Report</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((v, i) => {
          const href = withFromCompare(reportHrefForQuery(v.query))
          return (
            <tr key={`${v.query}-${i}`} style={{ borderTop: '0.5px solid var(--line)' }}>
              <Td style={{ textAlign: 'right', color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>{i + 1}</Td>
              <Td style={{ fontWeight: 600, color: 'var(--ink)' }}>
                <span style={{ display: 'inline-flex', flexWrap: 'wrap', alignItems: 'center', gap: 5 }}>
                  <span>{v.gene ?? '—'}</span>
                  {v.gene
                    ? membership
                        .filter((m) => m.symbols.has((v.gene as string).toUpperCase()))
                        .map((m) => <PanelTag key={m.slug} badge={m.badge} />)
                    : null}
                </span>
              </Td>
              <Td style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>{v.variant ?? v.query}</Td>
              <Td style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>{v.raw}</Td>
              <Td style={{ textAlign: 'right' }}>
                {href ? (
                  <Link href={href} style={{ fontSize: 12, fontWeight: 600, color: 'var(--teal-deep)', textDecoration: 'none' }}>
                    Open report →
                  </Link>
                ) : (
                  <span style={{ fontSize: 12, color: 'var(--ink-5)' }}>—</span>
                )}
              </Td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Th({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <th
      scope="col"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 1,
        textAlign: 'left',
        padding: '10px 14px',
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        color: 'var(--ink-4)',
        background: 'var(--bg-soft)',
        ...style,
      }}
    >
      {children}
    </th>
  )
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ padding: '10px 14px', verticalAlign: 'top', ...style }}>{children}</td>
}

function PanelTag({ badge }: { badge: PanelBadge }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '0.5px 6px',
        borderRadius: 5,
        fontFamily: 'var(--sans, inherit)',
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '0.01em',
        lineHeight: 1.5,
        background: badge.bg,
        color: badge.text,
        border: `0.5px solid ${badge.border}`,
      }}
    >
      {badge.short}
    </span>
  )
}
