'use client'

import { useEffect, useState } from 'react'
import { WorkRailSection } from '@/components/layout/WorkRail'
import { MOCK_PANELS, PANEL_SOURCE_LABEL } from '@/lib/panels.mock'
import { getPanels } from '@/lib/panels'
import type { ParsedVariant } from '@/lib/variant-file'
import type { Panel, PanelSummary } from '@/lib/backend'
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
 * Scope controls for /compare, rendered as <WorkRail> content (left rail).
 * "Active scope" holds the applied filters as removable chips + a slim summary;
 * "Add a filter" is the tabbed builder — Gene panels (preset list + quality /
 * region / frequency), Keywords (the custom-panel builder), and LLM (coming
 * soon). Panel chips filter live (mock); PASS/Region/AF apply server-side.
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
  const [dragOver, setDragOver] = useState(false)
  // Panel catalog for the preset list — mock-first, replaced by the live
  // GET /panels catalogue once it loads (falls back to mocks when offline).
  const [catalog, setCatalog] = useState<PanelSummary[]>(MOCK_PANELS)
  useEffect(() => {
    let stale = false
    getPanels().then((p) => {
      if (!stale) setCatalog(p)
    })
    return () => {
      stale = true
    }
  }, [])

  // Shared drag-over tracking for the scope drop zone. Guard dragLeave against
  // child elements so the highlight doesn't flicker as you move across chips.
  const enterZone = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }
  const leaveZone = (e: React.DragEvent) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false)
  }

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
    <>
      <WorkRailSection title="Active scope">
        {filters.length === 0 ? (
          <div
            onDragOver={enterZone}
            onDragEnter={enterZone}
            onDragLeave={leaveZone}
            onDrop={(e) => {
              setDragOver(false)
              onDropPayload(e.dataTransfer.getData(DT), null)
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              gap: 8,
              minHeight: 60,
              padding: '12px 14px',
              borderRadius: 12,
              border: dragOver ? '1.5px solid var(--teal)' : '1.5px dashed var(--line-2)',
              background: dragOver ? 'var(--teal-tint)' : 'var(--bg-soft)',
              color: dragOver ? 'var(--teal-deep)' : 'var(--ink-4)',
              fontSize: 12.5,
              fontWeight: dragOver ? 600 : 400,
              lineHeight: 1.4,
              transform: dragOver ? 'scale(1.015)' : 'scale(1)',
              transition: 'border-color .15s ease, background .15s ease, color .15s ease, transform .15s ease',
            }}
          >
            <span aria-hidden style={{ fontSize: 15 }}>{dragOver ? '⤓' : '⌬'}</span>
            {dragOver ? 'Drop to add this filter' : 'Pick a filter below, or drag one here, to scope this cohort.'}
          </div>
        ) : (
          <div
            onDragOver={enterZone}
            onDragEnter={enterZone}
            onDragLeave={leaveZone}
            onDrop={(e) => {
              setDragOver(false)
              onDropPayload(e.dataTransfer.getData(DT), filters.length)
            }}
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 8,
              minHeight: 40,
              alignContent: 'center',
              alignItems: 'center',
              padding: 6,
              borderRadius: 10,
              border: dragOver ? '1.5px dashed var(--teal)' : '1.5px dashed transparent',
              background: dragOver ? 'var(--teal-tint)' : 'transparent',
              transition: 'border-color .15s ease, background .15s ease',
            }}
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
            {dragOver && (
              <span style={{ fontSize: 11.5, fontFamily: 'var(--mono)', color: 'var(--teal-deep)', fontWeight: 600 }}>
                + drop to add
              </span>
            )}
          </div>
        )}

        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            alignItems: 'center',
            marginTop: 10,
            fontSize: 11.5,
            color: 'var(--ink-3)',
            fontFamily: 'var(--mono)',
          }}
        >
          <span style={{ color: 'var(--ink)', fontWeight: 600 }}>
            {res.activePanels.length > 0 ? `${res.shown.length} / ${res.total} in scope` : `${res.total} variants`}
          </span>
          <Dot />
          <span>{formatDuration(res.estSeconds)} est.</span>
          {res.serverSideCount > 0 && (
            <>
              <Dot />
              <span>{res.serverSideCount} server-side</span>
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
        </div>

        {filters.length > 0 && (
          <button
            type="button"
            onClick={() => onChange([])}
            style={{
              marginTop: 8,
              background: 'none',
              border: 'none',
              padding: 0,
              color: 'var(--ink-4)',
              fontSize: 11.5,
              fontFamily: 'var(--mono)',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Clear all filters
          </button>
        )}
      </WorkRailSection>

      <WorkRailSection title="Add a filter">
        <div role="tablist" aria-label="Add a filter" style={{ display: 'flex', gap: 2, marginBottom: 10 }}>
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
        {tab === 'panels' && <PresetList filters={filters} catalog={catalog} onAdd={add} />}
        {tab === 'keywords' && <KeywordPanelBuilder onCreate={addCustom} />}
        {tab === 'llm' && <LlmPanelComingSoon />}
      </WorkRailSection>
    </>
  )
}

function PresetList({
  filters,
  catalog,
  onAdd,
}: {
  filters: ActiveFilter[]
  catalog: PanelSummary[]
  onAdd: (kind: FilterKind, init?: Partial<ActiveFilter>) => void
}) {
  const activePanelSlugs = new Set(filters.filter((f) => f.kind === 'panel').map((f) => f.panelSlug))
  const hasPass = filters.some((f) => f.kind === 'pass')
  const hasAf = filters.some((f) => f.kind === 'af')
  return (
    <div>
      <MenuLabel>Gene panel</MenuLabel>
      {catalog.map((p) => {
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
