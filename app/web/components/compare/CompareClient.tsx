'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { reportHrefForQuery } from '@/lib/variant-search'
import { readCompareVariants, type CompareStash } from '@/lib/variant-file'
import { ScopeGate } from './ScopeGate'
import type { Panel } from '@/lib/backend'
import { PANEL_SOURCE_LABEL, scopeVariantsToPanel } from '@/lib/panels.mock'

/**
 * Multi-variant view (`/compare`). Slice 1: renders the variant list parsed
 * from a file dropped on the search bar, one row per variant, each linking to
 * its full single-variant report. Live key-metric columns + in-place row-expand
 * (the full comparison table from report-export-and-multi-vcf) are Slice 2 — they
 * need the per-variant lookup orchestration + the column-set decision.
 */
export function CompareClient() {
  const [stash, setStash] = useState<CompareStash | null>(null)
  const [hydrated, setHydrated] = useState(false)
  const [selectedPanel, setSelectedPanel] = useState<Panel | null>(null)
  const [applied, setApplied] = useState(false)

  useEffect(() => {
    setStash(readCompareVariants())
    setHydrated(true)
  }, [])

  const variants = stash?.variants ?? []
  const activePanel = applied ? selectedPanel : null
  const scope = scopeVariantsToPanel(variants, activePanel)
  const shownVariants = activePanel ? scope.matched : variants

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<ModePill current="report" />} />
      <main
        className="mx-auto"
        style={{ width: '100%', maxWidth: 'var(--maxw-report-frame)', padding: '32px 32px 80px' }}
      >
        <nav
          aria-label="Breadcrumb"
          className="mb-4 flex items-center gap-2"
          style={{ fontSize: 12, color: 'var(--ink-4)' }}
        >
          <Link href="/" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
            Search
          </Link>
          <span style={{ color: 'var(--ink-5)' }}>/</span>
          <span>Compare variants</span>
        </nav>

        <header className="mb-5">
          <h1
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 30,
              letterSpacing: '-0.02em',
              color: 'var(--ink)',
              margin: 0,
            }}
          >
            Compare variants
          </h1>
          {hydrated && variants.length > 0 && (
            <p style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink-3)', margin: '6px 0 0' }}>
              {variants.length} variant{variants.length === 1 ? '' : 's'}
              {stash?.source ? ` · from ${stash.source}` : ''}
              {activePanel
                ? ` · scoped to ${activePanel.name} (${PANEL_SOURCE_LABEL[activePanel.source]} ${activePanel.version})`
                : ''}
            </p>
          )}
        </header>

        {!hydrated ? null : variants.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <ScopeGate
              variants={variants}
              selectedPanel={selectedPanel}
              onSelectPanel={(p) => {
                setSelectedPanel(p)
                if (!p) setApplied(false)
              }}
              applied={applied}
              onApply={() => setApplied(true)}
              onClear={() => {
                setApplied(false)
                setSelectedPanel(null)
              }}
            />
            {shownVariants.length === 0 ? (
              <EmptyScope
                onClear={() => {
                  setApplied(false)
                  setSelectedPanel(null)
                }}
              />
            ) : (
            <>
            <section
              style={{
                background: 'var(--bg)',
                border: '0.5px solid var(--line)',
                borderRadius: 14,
                overflow: 'hidden',
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-soft)' }}>
                    <Th style={{ width: 44, textAlign: 'right' }}>#</Th>
                    <Th>Gene</Th>
                    <Th>Variant</Th>
                    <Th>Source line</Th>
                    <Th style={{ textAlign: 'right' }}>Report</Th>
                  </tr>
                </thead>
                <tbody>
                  {shownVariants.map((v, i) => {
                    const href = reportHrefForQuery(v.query)
                    return (
                      <tr key={`${v.query}-${i}`} style={{ borderTop: '0.5px solid var(--line)' }}>
                        <Td style={{ textAlign: 'right', color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>
                          {i + 1}
                        </Td>
                        <Td style={{ fontWeight: 600, color: 'var(--ink)' }}>{v.gene ?? '—'}</Td>
                        <Td style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>
                          {v.variant ?? v.query}
                        </Td>
                        <Td style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
                          {v.raw}
                        </Td>
                        <Td style={{ textAlign: 'right' }}>
                          {href ? (
                            <Link
                              href={href}
                              style={{
                                fontSize: 12,
                                fontWeight: 600,
                                color: 'var(--teal-deep)',
                                textDecoration: 'none',
                              }}
                            >
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
            </section>
            <p style={{ fontSize: 12, color: 'var(--ink-4)', margin: '12px 2px 0', lineHeight: 1.5 }}>
              Per-variant key metrics (gnomAD AF, predictors, classification) and in-place expansion
              are coming. For now, open each variant&apos;s full report from its row.
            </p>
            </>
            )}
          </>
        )}
      </main>
    </div>
  )
}

function EmptyState() {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '28px 28px',
        color: 'var(--ink-2)',
      }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 16, margin: 0, color: 'var(--ink)' }}>
        No variants to compare yet
      </h2>
      <p style={{ fontSize: 13.5, lineHeight: 1.6, margin: '10px 0 0' }}>
        Attach a variant file from the search bar — a VCF, or a CSV/TSV/plain-text list with one
        variant per line — and the parsed variants will appear here.
      </p>
      <Link
        href="/"
        style={{
          display: 'inline-block',
          marginTop: 16,
          padding: '7px 14px',
          borderRadius: 10,
          border: '0.5px solid var(--ink-2)',
          background: 'var(--ink-2)',
          color: '#fff',
          fontSize: 12.5,
          fontWeight: 600,
          textDecoration: 'none',
        }}
      >
        Back to search
      </Link>
    </section>
  )
}

function EmptyScope({ onClear }: { onClear: () => void }) {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '24px 24px',
        color: 'var(--ink-2)',
      }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 15, margin: 0, color: 'var(--ink)' }}>
        No variants in this panel
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, margin: '8px 0 0' }}>
        None of the named-gene variants fall in this panel. Genomic variants without a gene symbol are
        filtered server-side (interval intersection) once the batch engine lands — pick a different panel
        or clear the scope to see the full cohort.
      </p>
      <button
        type="button"
        onClick={onClear}
        style={{
          marginTop: 14,
          padding: '7px 14px',
          borderRadius: 10,
          border: '0.5px solid var(--line-2)',
          background: 'var(--bg)',
          color: 'var(--ink-2)',
          fontSize: 12.5,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Clear scope
      </button>
    </section>
  )
}

function Th({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <th
      scope="col"
      style={{
        textAlign: 'left',
        padding: '10px 14px',
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        color: 'var(--ink-4)',
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
