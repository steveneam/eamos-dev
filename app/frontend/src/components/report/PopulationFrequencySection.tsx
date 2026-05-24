'use client'

import { useMemo, useState } from 'react'
import type {
  PopulationAgeHistogramView,
  PopulationFrequencyReportSection,
  PopulationFrequencyVisualGroup,
} from '@/lib/backend'
import {
  GNOMAD_ANCESTRY_MAP_VERSION,
  gnomadMapAnchor,
} from './gnomadAncestryMap'

interface PopulationFrequencySectionProps {
  section?: PopulationFrequencyReportSection | null
}

type PopulationTab = 'ancestry' | 'age'

function formatInteger(value: number | null | undefined): string {
  return value == null ? 'Not reported' : new Intl.NumberFormat('en-US').format(value)
}

function formatFrequency(value: number | null | undefined): string {
  if (value == null) return 'Not reported'
  if (value === 0) return '0%'
  const pct = value * 100
  if (pct < 0.001) return `${pct.toExponential(2)}%`
  if (pct < 0.1) return `${pct.toPrecision(2)}%`
  return `${pct.toFixed(2)}%`
}

function compactLabel(label: string): string {
  return label.replace(' genetic ancestry', '')
}

function formatWarning(warning: string): string {
  return warning.replace(/_/g, ' ').replace(/:/g, ': ')
}

function groupContext(group: PopulationFrequencyVisualGroup): string {
  return gnomadMapAnchor(group.id).context
}

function heatRatio(value: number | null | undefined, maxFrequency: number): number {
  if (!value || value <= 0 || maxFrequency <= 0) return 0
  return Math.max(0, Math.min(1, value / maxFrequency))
}

function heatColor(value: number | null | undefined, maxFrequency: number, dataState?: string): string {
  if (dataState === 'zero_observed' || !value || value <= 0) return '#cbd5e1'
  const ratio = heatRatio(value, maxFrequency)
  if (ratio >= 0.82) return '#d84f3f'
  if (ratio >= 0.55) return '#e89241'
  if (ratio >= 0.25) return '#d6b649'
  return '#1D9E75'
}

function maxGroupFrequency(groups: PopulationFrequencyVisualGroup[]): number {
  return Math.max(0, ...groups.map((group) => group.allele_frequency ?? 0))
}

export function PopulationFrequencySection({ section }: PopulationFrequencySectionProps) {
  const [activeTab, setActiveTab] = useState<PopulationTab>('ancestry')
  const warnings = section?.warnings ?? []
  const groups = useMemo(
    () => [...(section?.visual_groups ?? [])].sort((a, b) => (a.sort_order ?? 99) - (b.sort_order ?? 99)),
    [section?.visual_groups],
  )
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null)
  const activeGroup =
    groups.find((group) => group.id === activeGroupId) ??
    groups.find((group) => group.is_popmax) ??
    groups[0] ??
    null

  if (!section) return null

  return (
    <div id={section.section_id} className="scroll-mt-24">
      <div
        id={section.panel_id}
        style={{
          border: '0.5px solid var(--line)',
          borderRadius: 10,
          background: 'var(--bg)',
          overflow: 'hidden',
        }}
      >
        <div
          className="flex flex-wrap items-center justify-between gap-3"
          style={{
            padding: '14px 16px',
            borderBottom: '0.5px solid var(--line)',
            background: 'var(--bg-soft)',
          }}
        >
          <div className="min-w-0">
            <div
              className="uppercase"
              style={{
                fontSize: 10.5,
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: 'var(--ink-4)',
              }}
            >
              {section.dataset || 'gnomAD'} | {section.genome_build || 'GRCh38'}
            </div>
            <div
              style={{
                marginTop: 3,
                fontFamily: 'var(--mono)',
                fontSize: 12,
                color: 'var(--ink-2)',
                overflowWrap: 'anywhere',
              }}
            >
              {section.variant_id || 'Variant ID unavailable'} | {section.sequencing_type}
            </div>
          </div>
          <div className="inline-flex gap-1 rounded-lg border border-[var(--line)] bg-[var(--bg)] p-1">
            <TabButton active={activeTab === 'ancestry'} onClick={() => setActiveTab('ancestry')}>
              Genetic ancestry group frequencies
            </TabButton>
            <TabButton active={activeTab === 'age'} onClick={() => setActiveTab('age')}>
              Age distribution
            </TabButton>
          </div>
        </div>

        <div style={{ padding: '16px' }}>
          {activeTab === 'ancestry' ? (
            <AncestryFrequencyTab
              groups={groups}
              activeGroup={activeGroup}
              maxFrequency={section.visual_scale?.max_value ?? maxGroupFrequency(groups)}
              sourceUrl={section.source_url}
              onActiveGroup={setActiveGroupId}
            />
          ) : (
            <AgeDistributionTab histograms={section.age_histograms ?? []} />
          )}

          {warnings.length > 0 && (
            <div
              className="mt-4 flex flex-wrap gap-2"
              aria-label="gnomAD section warnings"
            >
              {warnings.slice(0, 3).map((warning) => (
                <span
                  key={warning}
                  title={warning}
                  style={{
                    border: '0.5px solid var(--warn-bdr)',
                    background: 'var(--warn-tint)',
                    color: '#633806',
                    borderRadius: 7,
                    padding: '5px 8px',
                    fontSize: 10.5,
                    fontWeight: 600,
                    maxWidth: '100%',
                    overflowWrap: 'break-word',
                    whiteSpace: 'normal',
                  }}
                >
                  {formatWarning(warning)}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      style={{
        border: '0.5px solid',
        borderColor: active ? 'var(--teal)' : 'transparent',
        background: active ? 'var(--teal-tint)' : 'transparent',
        color: active ? 'var(--teal-deep)' : 'var(--ink-3)',
        borderRadius: 7,
        padding: '7px 10px',
        fontSize: 11.5,
        fontWeight: 700,
        cursor: 'pointer',
        maxWidth: 220,
        whiteSpace: 'normal',
        lineHeight: 1.2,
      }}
    >
      {children}
    </button>
  )
}

function AncestryFrequencyTab({
  groups,
  activeGroup,
  maxFrequency,
  sourceUrl,
  onActiveGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  activeGroup: PopulationFrequencyVisualGroup | null
  maxFrequency: number
  sourceUrl?: string | null
  onActiveGroup: (id: string | null) => void
}) {
  if (groups.length === 0) {
    return <UnavailablePanel title="Genetic ancestry group frequencies unavailable" />
  }

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'flex-start',
        gap: 16,
      }}
    >
      <div
        style={{
          flex: '1.35 1 360px',
          minWidth: 0,
          border: '0.5px solid var(--line)',
          borderRadius: 8,
          background: 'linear-gradient(180deg, #f8fbfd 0%, #f1f6f8 100%)',
          overflow: 'hidden',
        }}
      >
        <WorldFrequencyMap
          groups={groups}
          activeGroup={activeGroup}
          maxFrequency={maxFrequency}
          onActiveGroup={onActiveGroup}
        />
      </div>

      <aside
        style={{
          flex: '1 1 300px',
          minWidth: 0,
          border: '0.5px solid var(--line)',
          borderRadius: 8,
          background: 'var(--bg)',
          padding: 12,
        }}
      >
        <div
          className="uppercase"
          style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--ink-4)' }}
        >
          Allele frequency by gnomAD group
        </div>
        {activeGroup && (
          <div
            className="mt-2"
            style={{
              border: '0.5px solid var(--line)',
              borderRadius: 7,
              padding: '9px 10px',
              background: 'var(--bg-soft)',
            }}
          >
            <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--ink)' }}>
              {compactLabel(activeGroup.label)}
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1" style={{ fontSize: 11, color: 'var(--ink-3)' }}>
              <span>AF {formatFrequency(activeGroup.allele_frequency)}</span>
              <span>AN {formatInteger(activeGroup.allele_number)}</span>
              <span>AC {formatInteger(activeGroup.allele_count)}</span>
            </div>
            <div style={{ marginTop: 5, fontSize: 10.5, color: 'var(--ink-4)' }}>
              {groupContext(activeGroup)}
            </div>
          </div>
        )}
        <div className="mt-3 flex flex-col gap-2">
          {groups.map((group) => {
            const value = group.allele_frequency ?? 0
            const width = maxFrequency > 0 && value > 0 ? Math.max(2, (value / maxFrequency) * 100) : 0
            const isActive = activeGroup?.id === group.id
            const barColor = heatColor(group.allele_frequency, maxFrequency, group.data_state)
            return (
              <button
                key={group.id}
                type="button"
                data-gnomad-row={group.id}
                title={`${group.label}; allele number ${formatInteger(group.allele_number)}; ${groupContext(group)}`}
                onMouseEnter={() => onActiveGroup(group.id)}
                onFocus={() => onActiveGroup(group.id)}
                onClick={() => onActiveGroup(group.id)}
                style={{
                  border: '0.5px solid',
                  borderColor: isActive ? '#fde047' : 'var(--line)',
                  background: isActive ? 'rgba(254, 249, 195, 0.72)' : 'var(--bg)',
                  borderRadius: 7,
                  padding: '8px 9px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  boxShadow: isActive
                    ? `0 0 0 2px rgba(253, 224, 71, 0.42), 0 0 18px ${barColor}55`
                    : 'none',
                  transition: 'border-color 140ms ease, background 140ms ease, box-shadow 140ms ease',
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    style={{
                      fontSize: 11.5,
                      fontWeight: 700,
                      color: isActive ? '#111827' : 'var(--ink-2)',
                      textShadow: isActive ? `0 0 11px ${barColor}99` : 'none',
                    }}
                  >
                    {compactLabel(group.label)}
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-3)' }}>
                    {formatFrequency(group.allele_frequency)}
                  </span>
                </div>
                <div
                  className="mt-2"
                  aria-hidden
                  style={{
                    height: 6,
                    borderRadius: 999,
                    background: 'var(--bg-soft2)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${width}%`,
                      height: '100%',
                      borderRadius: 999,
                      background: barColor,
                    }}
                  />
                </div>
              </button>
            )
          })}
        </div>
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex"
            style={{ fontSize: 11.5, color: 'var(--ink-3)', textUnderlineOffset: 3 }}
          >
            Open source record
          </a>
        )}
      </aside>
    </div>
  )
}

function WorldFrequencyMap({
  groups,
  activeGroup,
  maxFrequency,
  onActiveGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  activeGroup: PopulationFrequencyVisualGroup | null
  maxFrequency: number
  onActiveGroup: (id: string | null) => void
}) {
  return (
    <div style={{ position: 'relative' }}>
      <svg
        viewBox="0 0 2000 857"
        role="img"
        aria-label="World map of gnomAD genetic ancestry group allele frequencies"
        style={{ width: '100%', minHeight: 238, display: 'block' }}
      >
        <defs>
          <linearGradient id="population-map-ocean" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#f7fbfd" />
            <stop offset="100%" stopColor="#eef5f8" />
          </linearGradient>
          <filter id="population-map-region-glow" x="-35%" y="-35%" width="170%" height="170%">
            <feDropShadow dx="0" dy="0" stdDeviation="12" floodColor="#fef08a" floodOpacity="0.95" />
            <feDropShadow dx="0" dy="0" stdDeviation="22" floodColor="#111827" floodOpacity="0.32" />
          </filter>
        </defs>
        <g transform="translate(-120 -40) scale(1.12)">
          <rect x="0" y="0" width="2000" height="857" fill="url(#population-map-ocean)" />
          <g opacity="0.48">
            <line x1="250" y1="0" x2="250" y2="857" stroke="#dbe6ec" strokeWidth="1" />
            <line x1="750" y1="0" x2="750" y2="857" stroke="#dbe6ec" strokeWidth="1" />
            <line x1="1250" y1="0" x2="1250" y2="857" stroke="#dbe6ec" strokeWidth="1" />
            <line x1="1750" y1="0" x2="1750" y2="857" stroke="#dbe6ec" strokeWidth="1" />
            <line x1="0" y1="214" x2="2000" y2="214" stroke="#dbe6ec" strokeWidth="1" />
            <line x1="0" y1="429" x2="2000" y2="429" stroke="#dbe6ec" strokeWidth="1" />
            <line x1="0" y1="643" x2="2000" y2="643" stroke="#dbe6ec" strokeWidth="1" />
          </g>
          <image href="/world.svg" x="0" y="0" width="2000" height="857" opacity="0.78" />
          <rect
            x="0"
            y="0"
            width="2000"
            height="857"
            fill="#ffffff"
            opacity={activeGroup ? 0.28 : 0.14}
          />
          {groups.map((group) => {
            const anchor = gnomadMapAnchor(group.id)
            const normalized = heatRatio(group.allele_frequency, maxFrequency)
            const fill = heatColor(group.allele_frequency, maxFrequency, group.data_state)
            const active = activeGroup?.id === group.id
            const fillOpacity = group.data_state === 'zero_observed'
              ? active ? 0.68 : 0.4
              : active ? 0.82 : 0.5 + normalized * 0.2
            return (
              <g
                key={group.id}
                tabIndex={0}
                role="button"
                data-gnomad-region={group.id}
                aria-label={`${group.label}: ${formatFrequency(group.allele_frequency)}, allele number ${formatInteger(group.allele_number)}. ${groupContext(group)}`}
                onMouseEnter={() => onActiveGroup(group.id)}
                onFocus={() => onActiveGroup(group.id)}
                onClick={() => onActiveGroup(group.id)}
                style={{ cursor: 'pointer' }}
              >
                <path
                  d={anchor.regionPath}
                  fill={fill}
                  fillOpacity={fillOpacity}
                  stroke={active ? '#fde047' : '#111827'}
                  strokeOpacity={active ? 0.95 : 0.56}
                  strokeWidth={active ? 7 : 3}
                  strokeLinejoin="round"
                  filter={active ? 'url(#population-map-region-glow)' : undefined}
                  style={{
                    transition:
                      'fill-opacity 140ms ease, stroke-width 140ms ease, stroke-opacity 140ms ease',
                  }}
                />
                <text
                  x={anchor.x}
                  y={anchor.y + 14}
                  textAnchor="middle"
                  fontSize="31"
                  fontFamily="JetBrains Mono, monospace"
                  fill={active ? '#0b1a2b' : '#475569'}
                  fontWeight={active ? 700 : 600}
                  paintOrder="stroke"
                  stroke={active ? '#fef9c3' : '#ffffff'}
                  strokeWidth={active ? 8 : 5}
                  strokeLinejoin="round"
                  style={{
                    textShadow: active ? `0 0 14px ${fill}` : 'none',
                    pointerEvents: 'none',
                  }}
                >
                  {group.id.toUpperCase()}
                </text>
              </g>
            )
          })}
        </g>
      </svg>
      <div
        style={{
          borderTop: '0.5px solid rgba(226,232,240,0.95)',
          background: 'rgba(255,255,255,0.76)',
          padding: '9px 12px',
          fontSize: 11,
          color: 'var(--ink-3)',
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span style={{ flex: '1 1 260px' }}>
            Basemap from SimpleMaps. Regional anchors orient gnomAD genetic ancestry groups;
            frequency values come from inferred source-group data, not race, ethnicity, patient
            ancestry, or exact geography. Algorithm {GNOMAD_ANCESTRY_MAP_VERSION}.
          </span>
          <span className="flex items-center gap-2" style={{ flex: '0 0 auto', fontSize: 10.5 }}>
            <span>Lower AF</span>
            <span
              aria-hidden
              style={{
                width: 96,
                height: 7,
                borderRadius: 999,
                background: 'linear-gradient(90deg, #1D9E75 0%, #d6b649 38%, #e89241 68%, #d84f3f 100%)',
                border: '0.5px solid rgba(148,163,184,0.8)',
              }}
            />
            <span>Higher AF</span>
          </span>
        </div>
      </div>
    </div>
  )
}

function AgeDistributionTab({ histograms }: { histograms: PopulationAgeHistogramView[] }) {
  const het = histograms.find((histogram) => histogram.genotype === 'heterozygous_alternate') ?? null
  const hom = histograms.find((histogram) => histogram.genotype === 'homozygous_alternate') ?? null
  const panels = [
    {
      title: 'Heterozygous alternate carriers',
      meta: 'overall source-release samples',
      histogram: het,
    },
    {
      title: 'Homozygous alternate carriers',
      meta: 'overall source-release samples',
      histogram: hom,
    },
    {
      title: 'Exome all individuals',
      meta: 'baseline not in current payload',
      histogram: null,
    },
    {
      title: 'Genome all individuals',
      meta: 'baseline not in current payload',
      histogram: null,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {panels.map((panel) => (
        <AgeHistogramCard
          key={panel.title}
          title={panel.title}
          meta={panel.meta}
          histogram={panel.histogram}
        />
      ))}
    </div>
  )
}

function AgeHistogramCard({
  title,
  meta,
  histogram,
}: {
  title: string
  meta: string
  histogram: PopulationAgeHistogramView | null
}) {
  const bins = histogram?.bins ?? []
  const maxCount = Math.max(0, ...bins.map((bin) => bin.count))
  const chartWidth = 180
  const chartHeight = 86
  const padX = 10
  const padTop = 8
  const padBottom = 18
  const plotHeight = chartHeight - padTop - padBottom
  const barGap = 2
  const barWidth = bins.length > 0 ? (chartWidth - padX * 2 - barGap * (bins.length - 1)) / bins.length : 0
  const points = bins
    .map((bin, index) => {
      const x = padX + index * (barWidth + barGap) + barWidth / 2
      const y = padTop + plotHeight - (maxCount > 0 ? (bin.count / maxCount) * plotHeight : 0)
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div
      style={{
        minWidth: 0,
        border: '0.5px solid var(--line)',
        borderRadius: 8,
        background: 'var(--bg)',
        padding: 11,
      }}
    >
      <div style={{ minHeight: 42 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)' }}>{title}</div>
        <div style={{ marginTop: 2, fontSize: 10.5, color: 'var(--ink-4)' }}>{meta}</div>
      </div>
      {bins.length === 0 ? (
        <UnavailablePanel title="Not reported" compact />
      ) : (
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={{ width: '100%', height: 118, display: 'block' }}>
          <line x1={padX} y1={padTop + plotHeight} x2={chartWidth - padX} y2={padTop + plotHeight} stroke="#dbe5ec" strokeWidth="0.8" />
          {bins.map((bin, index) => {
            const height = maxCount > 0 ? (bin.count / maxCount) * plotHeight : 0
            const x = padX + index * (barWidth + barGap)
            const y = padTop + plotHeight - height
            return (
              <g key={bin.label}>
                <rect x={x} y={y} width={barWidth} height={height} rx="1.5" fill="#8fb9aa" />
                {index % 2 === 0 && (
                  <text x={x + barWidth / 2} y={chartHeight - 5} textAnchor="middle" fontSize="6.5" fill="#64748b" fontFamily="JetBrains Mono, monospace">
                    {bin.label.split('-')[0]}
                  </text>
                )}
              </g>
            )
          })}
          {points && maxCount > 0 && (
            <polyline points={points} fill="none" stroke="#1D9E75" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          )}
        </svg>
      )}
      {histogram && (
        <div className="mt-1 flex justify-between gap-2" style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>
          <span>Below range {formatInteger(histogram.n_smaller)}</span>
          <span>Above range {formatInteger(histogram.n_larger)}</span>
        </div>
      )}
    </div>
  )
}

function UnavailablePanel({ title, compact = false }: { title: string; compact?: boolean }) {
  return (
    <div
      style={{
        minHeight: compact ? 118 : 180,
        border: '0.5px dashed var(--line-2)',
        borderRadius: 8,
        background: 'var(--bg-soft)',
        color: 'var(--ink-4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: 14,
        fontSize: 12,
      }}
    >
      {title}
    </div>
  )
}
