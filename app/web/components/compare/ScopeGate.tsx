'use client'

import { useMemo, useState } from 'react'
import type { ParsedVariant } from '@/lib/variant-file'
import type { Panel } from '@/lib/backend'
import { MOCK_PANELS, PANEL_SOURCE_LABEL, getMockPanel, scopeVariantsToPanel } from '@/lib/panels.mock'

/**
 * P3 scope-confirmation gate (spec §5.3) — the guardrail before a batch run.
 * Houses the panel picker (§6.5) and shows the live post-filter count + time
 * estimate + tier note. MOCK-FIRST: the catalogue is `lib/panels.mock`, the
 * intersection is a client-side gene-symbol preview; the authoritative
 * interval-first filter + async job land with Codex's backend (P2/P4).
 */
const SECONDS_PER_VARIANT = 9

interface ScopeGateProps {
  variants: ParsedVariant[]
  selectedPanel: Panel | null
  onSelectPanel: (panel: Panel | null) => void
  applied: boolean
  onApply: () => void
  onClear: () => void
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `~${seconds}s`
  if (seconds < 3600) return `~${Math.round(seconds / 60)} min`
  return `~${(seconds / 3600).toFixed(1)} h`
}

export function ScopeGate({
  variants,
  selectedPanel,
  onSelectPanel,
  applied,
  onApply,
  onClear,
}: ScopeGateProps) {
  const [query, setQuery] = useState('')

  const filteredPanels = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return MOCK_PANELS
    return MOCK_PANELS.filter(
      (p) => p.name.toLowerCase().includes(q) || PANEL_SOURCE_LABEL[p.source].toLowerCase().includes(q),
    )
  }, [query])

  const scope = useMemo(() => scopeVariantsToPanel(variants, selectedPanel), [variants, selectedPanel])
  const lookupCount = selectedPanel ? scope.matched.length : scope.total
  const estSeconds = lookupCount * SECONDS_PER_VARIANT

  return (
    <section
      aria-label="Scope this cohort"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        overflow: 'hidden',
        marginBottom: 18,
      }}
    >
      <div style={{ padding: '18px 20px', borderBottom: '0.5px solid var(--line)' }}>
        <h2
          style={{
            fontFamily: 'var(--display)',
            fontWeight: 600,
            fontSize: 15,
            margin: 0,
            color: 'var(--ink)',
          }}
        >
          Scope this cohort
        </h2>
        <p style={{ fontSize: 12.5, lineHeight: 1.55, color: 'var(--ink-3)', margin: '6px 0 0' }}>
          Apply a gene panel to keep only the variants in genes of interest. Scoping a large VCF to a
          panel is what makes whole-genome input tractable — and clinically focused.
        </p>
      </div>

      {/* Panel picker (§6.5) */}
      <div style={{ padding: '16px 20px' }}>
        <label
          htmlFor="panel-search"
          style={{
            display: 'block',
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: 'var(--ink-4)',
            marginBottom: 8,
          }}
        >
          Gene panel
        </label>
        <input
          id="panel-search"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search panels…"
          style={{
            width: '100%',
            padding: '8px 12px',
            borderRadius: 9,
            border: '0.5px solid var(--line-2)',
            background: 'var(--bg-soft)',
            fontSize: 13,
            color: 'var(--ink)',
            marginBottom: 10,
          }}
        />

        <div role="radiogroup" aria-label="Preloaded panels" style={{ display: 'grid', gap: 8 }}>
          {filteredPanels.map((p) => {
            const active = selectedPanel?.slug === p.slug
            return (
              <button
                key={p.slug}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => onSelectPanel(active ? null : getMockPanel(p.slug))}
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  justifyContent: 'space-between',
                  gap: 12,
                  textAlign: 'left',
                  padding: '11px 13px',
                  borderRadius: 10,
                  border: `0.5px solid ${active ? 'var(--teal-bdr)' : 'var(--line)'}`,
                  background: active ? 'var(--teal-tint)' : 'var(--bg)',
                  cursor: 'pointer',
                  width: '100%',
                }}
              >
                <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink)' }}>{p.name}</span>
                  <span style={{ fontSize: 11.5, color: 'var(--ink-4)' }}>
                    {PANEL_SOURCE_LABEL[p.source]} · {p.version}
                  </span>
                </span>
                <span
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11.5,
                    color: active ? 'var(--teal-deep)' : 'var(--ink-4)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {p.gene_count} genes
                </span>
              </button>
            )
          })}
          {filteredPanels.length === 0 && (
            <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '2px 2px' }}>No panels match “{query}”.</p>
          )}

          <div
            aria-disabled
            style={{
              padding: '11px 13px',
              borderRadius: 10,
              border: '0.5px dashed var(--line-2)',
              background: 'var(--bg-soft)',
              fontSize: 12.5,
              color: 'var(--ink-4)',
            }}
          >
            Build a custom panel — by disease, gene list, or description{' '}
            <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-5)' }}>COMING SOON</span>
          </div>
        </div>
      </div>

      {/* Scope summary (§5.3: N · est time · tier) */}
      <div
        style={{
          padding: '14px 20px',
          borderTop: '0.5px solid var(--line)',
          background: 'var(--bg-soft)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 14,
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, alignItems: 'baseline' }}>
          <Metric
            value={selectedPanel ? `${scope.matched.length} / ${scope.total}` : `${scope.total}`}
            label={selectedPanel ? 'in panel' : 'variants'}
          />
          <Metric value={formatDuration(estSeconds)} label="est. lookup" />
          {selectedPanel && scope.intervalPending.length > 0 && (
            <Metric value={`${scope.intervalPending.length}`} label="need interval filter" muted />
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {applied ? (
            <button type="button" onClick={onClear} style={ghostBtn}>
              Clear scope
            </button>
          ) : (
            <button
              type="button"
              onClick={onApply}
              disabled={!selectedPanel}
              style={{ ...primaryBtn, opacity: selectedPanel ? 1 : 0.45, cursor: selectedPanel ? 'pointer' : 'not-allowed' }}
            >
              Apply panel scope
            </button>
          )}
        </div>
      </div>

      {selectedPanel && scope.intervalPending.length > 0 && (
        <p style={{ fontSize: 11.5, lineHeight: 1.5, color: 'var(--ink-4)', margin: 0, padding: '10px 20px 14px' }}>
          {scope.intervalPending.length} genomic variant{scope.intervalPending.length === 1 ? '' : 's'} (no gene
          symbol) can’t be panel-filtered in the browser — the server-side interval filter (MANE→hg38 BED) handles
          these once the batch engine lands.
        </p>
      )}

      {applied && (
        <p style={{ fontSize: 11.5, lineHeight: 1.5, color: 'var(--ink-4)', margin: 0, padding: '10px 20px 14px' }}>
          Async batch runs with live per-variant results + cohort summaries arrive with the engine. For now, open
          each scoped variant’s full report below.
        </p>
      )}
    </section>
  )
}

function Metric({ value, label, muted }: { value: string; label: string; muted?: boolean }) {
  return (
    <span style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <span
        style={{
          fontFamily: 'var(--mono)',
          fontSize: 16,
          fontWeight: 600,
          color: muted ? 'var(--ink-4)' : 'var(--ink)',
          lineHeight: 1,
        }}
      >
        {value}
      </span>
      <span style={{ fontSize: 10.5, letterSpacing: '0.03em', textTransform: 'uppercase', color: 'var(--ink-4)' }}>
        {label}
      </span>
    </span>
  )
}

const primaryBtn: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: 10,
  border: '0.5px solid var(--ink-2)',
  background: 'var(--ink-2)',
  color: '#fff',
  fontSize: 12.5,
  fontWeight: 600,
}

const ghostBtn: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: 10,
  border: '0.5px solid var(--line-2)',
  background: 'var(--bg)',
  color: 'var(--ink-2)',
  fontSize: 12.5,
  fontWeight: 600,
  cursor: 'pointer',
}
