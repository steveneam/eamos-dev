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

type PopulationTab = 'map' | 'ancestry' | 'age'

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
  const [activeTab, setActiveTab] = useState<PopulationTab>('map')
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
    <div id={section.section_id} className="scroll-mt-24" data-panel-id={section.panel_id}>
      <div
        className="flex flex-wrap items-center justify-between gap-3"
        style={{ marginBottom: 14 }}
      >
        <div
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11.5,
            color: 'var(--ink-3)',
            overflowWrap: 'anywhere',
          }}
        >
          {section.variant_id || 'Variant ID unavailable'} · {section.sequencing_type}
        </div>
        <div className="inline-flex gap-1 rounded-lg border border-[var(--line)] bg-[var(--bg-soft)] p-1">
          <TabButton active={activeTab === 'map'} onClick={() => setActiveTab('map')}>
            World map
          </TabButton>
          <TabButton active={activeTab === 'ancestry'} onClick={() => setActiveTab('ancestry')}>
            Ancestry group frequencies
          </TabButton>
          <TabButton active={activeTab === 'age'} onClick={() => setActiveTab('age')}>
            Age distribution
          </TabButton>
        </div>
      </div>

      <div id={section.panel_id}>
        <div>{/* tab content begins */}
          {activeTab === 'map' ? (
            <MapOverviewTab
              groups={groups}
              activeGroup={activeGroup}
              maxFrequency={section.visual_scale?.max_value ?? maxGroupFrequency(groups)}
              onActiveGroup={setActiveGroupId}
            />
          ) : activeTab === 'ancestry' ? (
            <AncestryFrequencyTab
              groups={groups}
              activeGroup={activeGroup}
              maxFrequency={section.visual_scale?.max_value ?? maxGroupFrequency(groups)}
              sourceUrl={section.source_url}
              onActiveGroup={setActiveGroupId}
            />
          ) : (
            <AgeDistributionTab
              groups={groups}
              activeGroup={activeGroup}
              maxFrequency={section.visual_scale?.max_value ?? maxGroupFrequency(groups)}
              histograms={section.age_histograms ?? []}
              onActiveGroup={setActiveGroupId}
            />
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
                    color: 'var(--warn-text)',
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
      data-active={active}
      className="pop-tab-btn"
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
        transition:
          'background var(--dur-1) var(--ease-standard),' +
          'border-color var(--dur-1) var(--ease-standard),' +
          'color var(--dur-1) var(--ease-standard)',
      }}
    >
      <style>{`
        .pop-tab-btn[data-active="false"]:hover {
          background: var(--bg);
          color: var(--ink);
          border-color: var(--ink-5);
        }
        .pop-tab-btn:focus-visible {
          outline: none;
          box-shadow: 0 0 0 3px rgba(29, 158, 117, 0.18);
        }
        .pop-tab-btn:active {
          transform: translateY(0.5px);
          transition-duration: 80ms;
        }
      `}</style>
      {children}
    </button>
  )
}

function MapOverviewTab({
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
  if (groups.length === 0) {
    return <UnavailablePanel title="Genetic ancestry group frequencies unavailable" />
  }

  return (
    <div
      style={{
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
        layout="full"
        onActiveGroup={onActiveGroup}
      />
    </div>
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
          flex: '1.2 1 360px',
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
          layout="side"
          onActiveGroup={onActiveGroup}
        />
      </div>

      <aside
        style={{
          flex: '0.9 1 250px',
          minWidth: 0,
          border: '0.5px solid var(--line)',
          borderRadius: 8,
          background: 'var(--bg)',
          padding: 12,
        }}
      >
        <div className="eamos-kicker">
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
        <div className="mt-3 flex flex-col gap-1.5">
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
                  padding: '7px 8px',
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
                      fontSize: 10.8,
                      fontWeight: 700,
                      color: isActive ? '#111827' : 'var(--ink-2)',
                      textShadow: isActive ? `0 0 11px ${barColor}99` : 'none',
                    }}
                  >
                    {compactLabel(group.label)}
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10.4, color: 'var(--ink-3)' }}>
                    {formatFrequency(group.allele_frequency)}
                  </span>
                </div>
                <div
                  className="mt-2"
                  aria-hidden
                  style={{
                    height: 5,
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
  layout = 'side',
  onActiveGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  activeGroup: PopulationFrequencyVisualGroup | null
  maxFrequency: number
  layout?: 'full' | 'side'
  onActiveGroup: (id: string | null) => void
}) {
  const isFull = layout === 'full'
  return (
    <div style={{ position: 'relative' }}>
      <svg
        viewBox="0 0 2000 857"
        role="img"
        aria-label="World map of gnomAD genetic ancestry group allele frequencies"
        style={{ width: '100%', aspectRatio: '2000 / 857', display: 'block' }}
      >
        <defs>
          <linearGradient id="population-map-ocean" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#f7fbfd" />
            <stop offset="100%" stopColor="#eef5f8" />
          </linearGradient>
          <mask id="population-map-land-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="2000" height="857">
            <image href="/world.svg" x="0" y="0" width="2000" height="857" opacity="1" />
          </mask>
          <filter id="population-map-region-glow" x="-35%" y="-35%" width="170%" height="170%">
            <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor="#fef08a" floodOpacity="0.9" />
            <feDropShadow dx="0" dy="0" stdDeviation="12" floodColor="#111827" floodOpacity="0.22" />
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
                  data-active={active ? 'true' : 'false'}
                  fill={fill}
                  fillOpacity={fillOpacity}
                  mask="url(#population-map-land-mask)"
                  stroke="transparent"
                  strokeOpacity="0"
                  strokeWidth="0"
                  strokeLinejoin="round"
                  style={{
                    mixBlendMode: 'multiply',
                    transition:
                      'fill-opacity 140ms ease, stroke-width 140ms ease, stroke-opacity 140ms ease',
                  }}
                />
                <text
                  x={anchor.x}
                  y={anchor.y + 14}
                  textAnchor="middle"
                  fontSize={isFull ? '23' : '19'}
                  fontFamily="JetBrains Mono, monospace"
                  fill={active ? '#0b1a2b' : '#475569'}
                  fontWeight={active ? 700 : 600}
                  paintOrder="stroke"
                  stroke={active ? '#fef9c3' : '#ffffff'}
                  strokeWidth={active ? 6 : 4.5}
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
            Basemap from SimpleMaps. Regional fills are clipped to land silhouettes and orient
            gnomAD genetic ancestry groups; frequency values come from source-group data, not
            race, ethnicity, patient ancestry, or exact geography. Algorithm {GNOMAD_ANCESTRY_MAP_VERSION}.
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

function AgeDistributionTab({
  groups,
  activeGroup,
  maxFrequency,
  histograms,
  onActiveGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  activeGroup: PopulationFrequencyVisualGroup | null
  maxFrequency: number
  histograms: PopulationAgeHistogramView[]
  onActiveGroup: (id: string | null) => void
}) {
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
          flex: '0.72 1 260px',
          minWidth: 0,
          border: '0.5px solid var(--line)',
          borderRadius: 8,
          background: 'linear-gradient(180deg, #f8fbfd 0%, #f1f6f8 100%)',
          overflow: 'hidden',
        }}
      >
        {groups.length === 0 ? (
          <UnavailablePanel title="Genetic ancestry group frequencies unavailable" />
        ) : (
          <WorldFrequencyMap
            groups={groups}
            activeGroup={activeGroup}
            maxFrequency={maxFrequency}
            layout="side"
            onActiveGroup={onActiveGroup}
          />
        )}
      </div>

      <aside
        style={{
          flex: '1.28 1 390px',
          minWidth: 0,
          border: '0.5px solid var(--line)',
          borderRadius: 8,
          background: 'var(--bg)',
          padding: 12,
        }}
      >
        <div className="eamos-kicker">
          Source age distribution
        </div>
        <div style={{ marginTop: 6, fontSize: 11, lineHeight: 1.45, color: 'var(--ink-4)' }}>
          Exact gnomAD age-bin counts split by sequencing type. Variant-carrier panels use the
          variant age_distribution payload; all-individual panels use gnomAD v4 dataset metadata.
        </div>
        <AgeHistogramGrid histograms={histograms} />
      </aside>
    </div>
  )
}

type AgeChartSequencingType = 'exome' | 'genome'
type AgeChartSeriesKind = 'variant_carriers' | 'all_individuals'

function AgeHistogramGrid({ histograms }: { histograms: PopulationAgeHistogramView[] }) {
  const panels: Array<{
    key: string
    title: string
    sequencingType: AgeChartSequencingType
    seriesKind: AgeChartSeriesKind
    fill: string
    unit: string
  }> = [
    {
      key: 'exome-carriers',
      title: 'Exome variant carriers',
      sequencingType: 'exome',
      seriesKind: 'variant_carriers',
      fill: '#3d7dbf',
      unit: 'carriers',
    },
    {
      key: 'exome-all',
      title: 'Exome all individuals',
      sequencingType: 'exome',
      seriesKind: 'all_individuals',
      fill: '#31a68f',
      unit: 'individuals',
    },
    {
      key: 'genome-carriers',
      title: 'Genome variant carriers',
      sequencingType: 'genome',
      seriesKind: 'variant_carriers',
      fill: '#8059b7',
      unit: 'carriers',
    },
    {
      key: 'genome-all',
      title: 'Genome all individuals',
      sequencingType: 'genome',
      seriesKind: 'all_individuals',
      fill: '#d07a33',
      unit: 'individuals',
    },
  ]

  return (
    <div
      className="mt-3"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: 10,
        maxWidth: 540,
      }}
    >
      {panels.map((panel) => (
        <AgeHistogramCard
          key={panel.key}
          title={panel.title}
          histogram={findAgeHistogram(histograms, panel.sequencingType, panel.seriesKind)}
          fill={panel.fill}
          unit={panel.unit}
        />
      ))}
    </div>
  )
}

function findAgeHistogram(
  histograms: PopulationAgeHistogramView[],
  sequencingType: AgeChartSequencingType,
  seriesKind: AgeChartSeriesKind,
): PopulationAgeHistogramView | null {
  return (
    histograms.find(
      (histogram) =>
        histogram.sequencing_type === sequencingType && histogram.series_kind === seriesKind,
    ) ?? null
  )
}

function AgeHistogramCard({
  title,
  histogram,
  fill,
  unit,
}: {
  title: string
  histogram: PopulationAgeHistogramView | null
  fill: string
  unit: string
}) {
  const bins = histogram ? ageChartBins(histogram) : []
  const maxCount = Math.max(0, ...bins.map((bin) => bin.count))
  const yMax = niceMaxCount(maxCount)
  const chartWidth = 340
  const chartHeight = 192
  const padLeft = 44
  const padRight = 10
  const padTop = 14
  const padBottom = 38
  const plotWidth = chartWidth - padLeft - padRight
  const plotHeight = chartHeight - padTop - padBottom
  const groupWidth = bins.length > 0 ? plotWidth / bins.length : plotWidth
  const barWidth = Math.max(4, Math.min(18, groupWidth * 0.58))
  const ticks = yAxisTicks(yMax)

  return (
    <div
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 8,
        background: 'var(--bg-soft)',
        padding: 10,
        minWidth: 0,
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.2 }}>
          {title}
        </div>
        {histogram && (
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-3)' }}>
            n={formatInteger(histogramTotal(histogram))}
          </div>
        )}
      </div>

      {!histogram || bins.length === 0 ? (
        <div
          style={{
            minHeight: 154,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--ink-4)',
            fontSize: 11.5,
            textAlign: 'center',
            padding: 10,
          }}
        >
          Age distribution not reported
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          role="img"
          aria-label={`${title} age histogram`}
          style={{ width: '100%', minHeight: 174, display: 'block' }}
        >
          {ticks.map((tick) => {
            const y = padTop + plotHeight - (yMax > 0 ? (tick / yMax) * plotHeight : 0)
            return (
              <g key={tick}>
                <line x1={padLeft} y1={y} x2={chartWidth - padRight} y2={y} stroke="#e2e8f0" strokeWidth="0.8" />
                <text x={padLeft - 7} y={y + 3} textAnchor="end" fontSize="8.2" fill="#64748b" fontFamily="JetBrains Mono, monospace">
                  {formatInteger(tick)}
                </text>
              </g>
            )
          })}
          <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + plotHeight} stroke="#94a3b8" strokeWidth="0.8" />
          <line x1={padLeft} y1={padTop + plotHeight} x2={chartWidth - padRight} y2={padTop + plotHeight} stroke="#94a3b8" strokeWidth="0.8" />

          {bins.map((bin, binIndex) => {
            const height = yMax > 0 ? (bin.count / yMax) * plotHeight : 0
            const visibleHeight = bin.count > 0 ? Math.max(2, height) : 0
            const x = padLeft + binIndex * groupWidth + groupWidth / 2 - barWidth / 2
            const y = padTop + plotHeight - visibleHeight
            const showLabel =
              bins.length <= 9 || binIndex % 2 === 0 || bin.label.startsWith('<') || bin.label.endsWith('+')
            return (
              <g key={`${bin.label}-${binIndex}`}>
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={visibleHeight}
                  rx="1.5"
                  fill={fill}
                  opacity={bin.count > 0 ? 0.88 : 0}
                >
                  <title>{`${title}, age ${bin.label}: ${formatInteger(bin.count)} ${unit}`}</title>
                </rect>
                {showLabel && (
                  <text x={padLeft + binIndex * groupWidth + groupWidth / 2} y={chartHeight - 20} textAnchor="middle" fontSize="7.6" fill="#64748b" fontFamily="JetBrains Mono, monospace">
                    {bin.label}
                  </text>
                )}
              </g>
            )
          })}

          <text x={padLeft + plotWidth / 2} y={chartHeight - 6} textAnchor="middle" fontSize="9.5" fill="#475569">
            Age
          </text>
          <text x="12" y={padTop + plotHeight / 2} textAnchor="middle" fontSize="9.5" fill="#475569" transform={`rotate(-90 12 ${padTop + plotHeight / 2})`}>
            Count
          </text>
        </svg>
      )}
    </div>
  )
}

function ageChartBins(histogram: PopulationAgeHistogramView): Array<{ label: string; count: number }> {
  const bins: Array<{ label: string; count: number }> = []
  if (histogram.n_smaller != null) {
    bins.push({ label: '<30', count: histogram.n_smaller })
  }
  bins.push(...histogram.bins.map((bin) => ({ label: bin.label, count: bin.count })))
  if (histogram.n_larger != null) {
    bins.push({ label: '80+', count: histogram.n_larger })
  }
  return bins
}

function histogramTotal(histogram: PopulationAgeHistogramView): number {
  return histogram.bins.reduce((sum, bin) => sum + bin.count, 0) + (histogram.n_smaller ?? 0) + (histogram.n_larger ?? 0)
}

function niceMaxCount(maxCount: number): number {
  if (maxCount <= 1) return 1
  const exponent = 10 ** Math.floor(Math.log10(maxCount))
  const fraction = maxCount / exponent
  const niceFraction = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10
  return niceFraction * exponent
}

function yAxisTicks(maxCount: number): number[] {
  if (maxCount <= 1) return [0, 1]
  if (maxCount <= 4) return Array.from({ length: maxCount + 1 }, (_, index) => index)
  return Array.from(new Set([0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(maxCount * ratio))))
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
