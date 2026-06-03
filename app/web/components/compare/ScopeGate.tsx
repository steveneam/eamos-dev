'use client'

import { useEffect, useRef, useState } from 'react'
import { MOCK_PANELS, PANEL_SOURCE_LABEL } from '@/lib/panels.mock'
import type { ParsedVariant } from '@/lib/variant-file'
import type { Panel } from '@/lib/backend'
import {
  applyFilters,
  DEFAULT_MAX_AF,
  FILTER_META,
  filterChipLabel,
  formatDuration,
  makeFilter,
  resolveFilterPanel,
  type ActiveFilter,
  type FilterKind,
} from '@/lib/compare-filters'
import { KeywordPanelBuilder, LlmPanelComingSoon } from './CustomPanelBuilder'

/**
 * P3 scope bar (spec §5.3 + §6.5). Left column: active filters as removable chips
 * + a slim summary. Right rail: a tabbed box — "Presets" (panel list + quality /
 * region / frequency) and "Custom panel" (the scratchpad builder). Panel chips
 * filter live (mock); PASS/Region/AF apply server-side. Filtering is live.
 */
const DT = 'text/plain'
type DragPayload = { t: 'new'; kind: FilterKind; panelSlug?: string } | { t: 'chip'; index: number }
type RailTab = 'panels' | 'keywords' | 'llm'

interface ScopeGateProps {
  variants: ParsedVariant[]
  filters: ActiveFilter[]
  onChange: (filters: ActiveFilter[]) => void
}

function move<T>(arr: T[], from: number, to: number): T[] {
  const copy = arr.slice()
  const [item] = copy.splice(from, 1)
  copy.splice(to, 0, item)
  return copy
}

export function ScopeGate({ variants, filters, onChange }: ScopeGateProps) {
  const [tab, setTab] = useState<RailTab>('panels')
  // The builder rail minimises once a filter is applied (output generated), and
  // re-expands when the scope is cleared. The user can also toggle it manually.
  const [railOpen, setRailOpen] = useState(true)
  const prevCount = useRef(0)
  useEffect(() => {
    if (prevCount.current === 0 && filters.length > 0) setRailOpen(false)
    else if (filters.length === 0) setRailOpen(true)
    prevCount.current = filters.length
  }, [filters.length])

  const add = (kind: FilterKind, init?: Partial<ActiveFilter>) => onChange([...filters, makeFilter(kind, init)])
  const remove = (id: string) => onChange(filters.filter((f) => f.id !== id))
  const update = (id: string, patch: Partial<ActiveFilter>) =>
    onChange(filters.map((f) => (f.id === id ? { ...f, ...patch } : f)))
  const addCustom = (panel: Panel) => onChange([...filters, makeFilter('panel', { customPanel: panel })])

  const onDropPayload = (raw: string, atIndex: number | null) => {
    let p: DragPayload
    try {
      p = JSON.parse(raw)
    } catch {
      return
    }
    if (p.t === 'new') {
      add(p.kind, p.kind === 'panel' ? { panelSlug: p.panelSlug } : undefined)
    } else if (p.t === 'chip' && atIndex !== null && atIndex !== p.index) {
      onChange(move(filters, p.index, atIndex))
    }
  }

  const res = applyFilters(variants, filters)

  return (
    <section aria-label="Scope this cohort" style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
        {/* LEFT: active filters + summary */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {filters.length === 0 ? (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => onDropPayload(e.dataTransfer.getData(DT), null)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                minHeight: 44,
                padding: '0 14px',
                borderRadius: 11,
                border: '1px dashed var(--line-2)',
                background: 'var(--bg-soft)',
                color: 'var(--ink-4)',
                fontSize: 12.5,
              }}
            >
              <span aria-hidden style={{ fontSize: 14 }}>⌬</span>
              Add a filter from the right, or drag one here, to scope this cohort.
            </div>
          ) : (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => onDropPayload(e.dataTransfer.getData(DT), filters.length)}
              style={{ display: 'flex', flexWrap: 'wrap', gap: 8, minHeight: 36, alignContent: 'center' }}
            >
              {filters.map((f, i) => (
                <FilterChip
                  key={f.id}
                  filter={f}
                  index={i}
                  onRemove={() => remove(f.id)}
                  onUpdate={(patch) => update(f.id, patch)}
                  onReorderDrop={(raw) => onDropPayload(raw, i)}
                />
              ))}
            </div>
          )}

          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 10,
              alignItems: 'center',
              marginTop: 10,
              fontSize: 12,
              color: 'var(--ink-3)',
              fontFamily: 'var(--mono)',
            }}
          >
            <span style={{ color: 'var(--ink)', fontWeight: 600 }}>
              {res.activePanels.length > 0 ? `${res.shown.length} / ${res.total} in scope` : `${res.total} variants`}
            </span>
            <Dot />
            <span>{formatDuration(res.estSeconds)} est. lookup</span>
            {res.serverSideCount > 0 && (
              <>
                <Dot />
                <span>
                  {res.serverSideCount} server-side filter{res.serverSideCount === 1 ? '' : 's'}
                </span>
              </>
            )}
            {res.intervalPending > 0 && (
              <>
                <Dot />
                <span title="Genomic variants without a gene symbol — filtered server-side via the MANE→hg38 BED interval map.">
                  {res.intervalPending} need interval filter
                </span>
              </>
            )}
            {filters.length > 0 && (
              <button
                type="button"
                onClick={() => onChange([])}
                style={{
                  marginLeft: 'auto',
                  background: 'none',
                  border: 'none',
                  color: 'var(--ink-4)',
                  fontSize: 11.5,
                  fontFamily: 'var(--mono)',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                Clear all
              </button>
            )}
          </div>
        </div>

        {/* RIGHT: builder rail — minimises once filters are applied */}
        <div style={{ flexShrink: 0, width: railOpen ? 320 : 'auto' }}>
          {railOpen ? (
            <div style={{ background: 'var(--bg)', border: '0.5px solid var(--line)', borderRadius: 12, overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'stretch', borderBottom: '0.5px solid var(--line)' }}>
                <div role="tablist" aria-label="Add a filter" style={{ display: 'flex', flex: 1 }}>
                  <TabButton active={tab === 'panels'} onClick={() => setTab('panels')}>
                    Gene panels
                  </TabButton>
                  <TabButton active={tab === 'keywords'} onClick={() => setTab('keywords')}>
                    Keywords
                  </TabButton>
                  <TabButton active={tab === 'llm'} onClick={() => setTab('llm')}>
                    LLM
                  </TabButton>
                </div>
                <button
                  type="button"
                  aria-label="Minimize filter builder"
                  title="Hide"
                  onClick={() => setRailOpen(false)}
                  style={{
                    padding: '0 12px',
                    border: 'none',
                    borderLeft: '0.5px solid var(--line)',
                    background: 'var(--bg-soft)',
                    color: 'var(--ink-4)',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  ▴
                </button>
              </div>
              <div style={{ padding: 10 }}>
                {tab === 'panels' && <PresetList filters={filters} onAdd={add} />}
                {tab === 'keywords' && <KeywordPanelBuilder onCreate={addCustom} />}
                {tab === 'llm' && <LlmPanelComingSoon />}
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setRailOpen(true)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '9px 14px',
                borderRadius: 10,
                border: '0.5px solid var(--line-2)',
                background: 'var(--bg)',
                color: 'var(--ink-2)',
                fontSize: 12.5,
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              + Add or edit filters{filters.length ? ` · ${filters.length}` : ''}{' '}
              <span aria-hidden style={{ fontSize: 10, opacity: 0.7 }}>▾</span>
            </button>
          )}
        </div>
      </div>
    </section>
  )
}

function PresetList({ filters, onAdd }: { filters: ActiveFilter[]; onAdd: (kind: FilterKind, init?: Partial<ActiveFilter>) => void }) {
  const activePanelSlugs = new Set(filters.filter((f) => f.kind === 'panel').map((f) => f.panelSlug))
  const hasPass = filters.some((f) => f.kind === 'pass')
  const hasAf = filters.some((f) => f.kind === 'af')
  return (
    <div>
      <MenuLabel>Gene panel</MenuLabel>
      {MOCK_PANELS.map((p) => {
        const taken = activePanelSlugs.has(p.slug)
        return (
          <MenuItem
            key={p.slug}
            disabled={taken}
            draggable={!taken}
            onDragStart={(e) => e.dataTransfer.setData(DT, JSON.stringify({ t: 'new', kind: 'panel', panelSlug: p.slug }))}
            onClick={() => onAdd('panel', { panelSlug: p.slug })}
          >
            <span>{p.name}</span>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>
              {taken ? 'added' : `${p.gene_count} genes`}
            </span>
          </MenuItem>
        )
      })}
      <div style={{ height: 1, background: 'var(--line)', margin: '6px 4px' }} />
      <MenuLabel>Quality &amp; frequency · server-side</MenuLabel>
      <MenuItem
        disabled={hasPass}
        draggable={!hasPass}
        onDragStart={(e) => e.dataTransfer.setData(DT, JSON.stringify({ t: 'new', kind: 'pass' }))}
        onClick={() => onAdd('pass')}
      >
        {FILTER_META.pass.label}
        <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{hasPass ? 'added' : ''}</span>
      </MenuItem>
      <MenuItem
        draggable
        onDragStart={(e) => e.dataTransfer.setData(DT, JSON.stringify({ t: 'new', kind: 'region' }))}
        onClick={() => onAdd('region')}
      >
        {FILTER_META.region.label}
      </MenuItem>
      <MenuItem
        disabled={hasAf}
        draggable={!hasAf}
        onDragStart={(e) => e.dataTransfer.setData(DT, JSON.stringify({ t: 'new', kind: 'af' }))}
        onClick={() => onAdd('af')}
      >
        {FILTER_META.af.label}
        <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{hasAf ? 'added' : ''}</span>
      </MenuItem>
    </div>
  )
}

function FilterChip({
  filter,
  index,
  onRemove,
  onUpdate,
  onReorderDrop,
}: {
  filter: ActiveFilter
  index: number
  onRemove: () => void
  onUpdate: (patch: Partial<ActiveFilter>) => void
  onReorderDrop: (raw: string) => void
}) {
  const serverSide = FILTER_META[filter.kind].serverSide
  const panel = filter.kind === 'panel' ? resolveFilterPanel(filter) : null
  return (
    <span
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => onReorderDrop(e.dataTransfer.getData(DT))}
      title={panel ? `${PANEL_SOURCE_LABEL[panel.source]} · ${panel.version}` : undefined}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 7px 5px 4px',
        borderRadius: 9,
        border: `0.5px solid ${serverSide ? 'var(--line-2)' : 'var(--teal-bdr)'}`,
        background: serverSide ? 'var(--bg-soft)' : 'var(--teal-tint)',
        fontSize: 12,
        color: 'var(--ink)',
      }}
    >
      <span
        draggable
        onDragStart={(e) => e.dataTransfer.setData(DT, JSON.stringify({ t: 'chip', index }))}
        aria-hidden
        style={{ cursor: 'grab', color: 'var(--ink-5)', fontSize: 12, lineHeight: 1, userSelect: 'none' }}
      >
        ⠿
      </span>
      {serverSide && (
        <span
          aria-hidden
          title="Applies server-side when the batch engine runs"
          style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--warn)', flexShrink: 0 }}
        />
      )}
      {filter.kind === 'region' ? (
        <>
          <span style={{ color: 'var(--ink-3)' }}>Region</span>
          <input
            value={filter.region ?? ''}
            onChange={(e) => onUpdate({ region: e.target.value })}
            placeholder="chr1:1-2,000"
            draggable={false}
            style={{
              width: 96,
              padding: '1px 5px',
              borderRadius: 6,
              border: '0.5px solid var(--line-2)',
              background: 'var(--bg)',
              fontSize: 11.5,
              fontFamily: 'var(--mono)',
              color: 'var(--ink)',
            }}
          />
        </>
      ) : filter.kind === 'af' ? (
        <>
          <span style={{ color: 'var(--ink-3)' }}>AF ≤</span>
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={filter.maxAf ?? DEFAULT_MAX_AF}
            onChange={(e) => onUpdate({ maxAf: Number(e.target.value) })}
            draggable={false}
            style={{
              width: 56,
              padding: '1px 5px',
              borderRadius: 6,
              border: '0.5px solid var(--line-2)',
              background: 'var(--bg)',
              fontSize: 11.5,
              fontFamily: 'var(--mono)',
              color: 'var(--ink)',
            }}
          />
        </>
      ) : (
        <span style={{ fontWeight: filter.kind === 'panel' ? 600 : 400 }}>{filterChipLabel(filter)}</span>
      )}
      <button
        type="button"
        aria-label={`Remove ${filterChipLabel(filter)} filter`}
        onClick={onRemove}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 16,
          height: 16,
          borderRadius: 5,
          border: 'none',
          background: 'transparent',
          color: 'var(--ink-4)',
          fontSize: 13,
          lineHeight: 1,
          cursor: 'pointer',
        }}
      >
        ✕
      </button>
    </span>
  )
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      style={{
        flex: 1,
        padding: '9px 10px',
        border: 'none',
        borderBottom: `2px solid ${active ? 'var(--ink-2)' : 'transparent'}`,
        background: active ? 'var(--bg)' : 'var(--bg-soft)',
        color: active ? 'var(--ink)' : 'var(--ink-4)',
        fontSize: 12,
        fontWeight: 600,
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  )
}

function MenuLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: '6px 8px 4px',
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        color: 'var(--ink-4)',
      }}
    >
      {children}
    </div>
  )
}

function MenuItem({
  children,
  disabled,
  onClick,
  draggable,
  onDragStart,
}: {
  children: React.ReactNode
  disabled?: boolean
  onClick: () => void
  draggable?: boolean
  onDragStart?: (e: React.DragEvent) => void
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      draggable={draggable}
      onDragStart={onDragStart}
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 10,
        width: '100%',
        textAlign: 'left',
        padding: '8px 9px',
        borderRadius: 8,
        border: 'none',
        background: 'transparent',
        color: disabled ? 'var(--ink-5)' : 'var(--ink)',
        fontSize: 12.5,
        cursor: disabled ? 'not-allowed' : 'grab',
      }}
    >
      {children}
    </button>
  )
}

function Dot() {
  return <span aria-hidden style={{ color: 'var(--ink-5)' }}>·</span>
}
