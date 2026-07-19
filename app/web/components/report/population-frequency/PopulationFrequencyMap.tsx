'use client'

import { useEffect, useRef } from 'react'

import type { PopulationFrequencyVisualGroup } from '@/lib/backend'
import { InfoPopover } from '@/components/ui/InfoHint'

import { GNOMAD_ANCESTRY_MAP_VERSION } from '../gnomadAncestryMap'
import {
  GNOMAD_MAP_LAND,
  GNOMAD_MAP_REGIONS,
  GNOMAD_MAP_VIEW_BOX,
} from '../gnomadMapGeometry.generated'
import {
  GNOMAD_AF_BANDS,
  GNOMAD_MAP_HOVER,
  GNOMAD_MAP_SURFACE,
} from '../gnomadMapTheme'
import { PopulationUnavailablePanel } from './PopulationUnavailablePanel'
import {
  FOOTER_CHIP_DESC_STYLE,
  FOOTER_CHIP_MIN_HEIGHT,
  FOOTER_CHIP_WIDTH,
  GEOGRAPHIC_GROUP_IDS,
  bandFill,
  compactLabel,
  formatFrequency,
  formatInteger,
  groupContext,
  offMapOriginCopy,
} from './populationFrequencyModel'

interface PopulationGroupInteractionProps {
  groups: PopulationFrequencyVisualGroup[]
  hoveredId: string | null
  selectedId: string | null
  onHoverGroup: (id: string | null) => void
  onSelectGroup: (id: string | null) => void
}

export function MapOverviewTab(props: PopulationGroupInteractionProps) {
  if (props.groups.length === 0) {
    return <PopulationUnavailablePanel title="Genetic ancestry group frequencies unavailable" />
  }

  return (
    <div
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 8,
        background: 'var(--bg-soft)',
        overflow: 'hidden',
      }}
    >
      <WorldFrequencyMap {...props} layout="full" />
    </div>
  )
}

export function WorldFrequencyMap({
  groups,
  hoveredId,
  selectedId,
  layout = 'side',
  showOffMap = true,
  onHoverGroup,
  onSelectGroup,
}: PopulationGroupInteractionProps & {
  layout?: 'full' | 'side'
  showOffMap?: boolean
}) {
  const isFull = layout === 'full'
  const { width, height } = GNOMAD_MAP_VIEW_BOX
  const byGroup = new Map(groups.map((group) => [group.id, group]))
  const offMapGroups = groups.filter((group) => !GEOGRAPHIC_GROUP_IDS.has(group.id))
  const selectedOnMap =
    selectedId != null && GNOMAD_MAP_REGIONS.some((region) => region.group === selectedId)
  const popoverRegion = isFull && selectedId
    ? GNOMAD_MAP_REGIONS.find((region) => region.group === selectedId) ?? null
    : null
  const popoverGroup = popoverRegion ? byGroup.get(popoverRegion.group) ?? null : null
  const labelSize = isFull ? 22 : 18
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isFull || selectedId == null) return
    const handlePointerDown = (event: PointerEvent) => {
      const root = rootRef.current
      if (root && event.target instanceof Node && !root.contains(event.target)) {
        onSelectGroup(null)
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [isFull, selectedId, onSelectGroup])

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <style>{`
        .gnomad-region { transition: fill 160ms var(--ease-standard), fill-opacity 160ms var(--ease-standard); }
        .gnomad-region-g { transition: opacity 160ms var(--ease-standard); }
        .gnomad-region-g:focus { outline: none; }
        .gnomad-halo { transition: stroke-opacity 200ms var(--ease-standard); }
        @keyframes gnomadPopIn { from { opacity: 0; } to { opacity: 1; } }
        .gnomad-map-pop { animation: gnomadPopIn 160ms var(--ease-standard); }
        @media (prefers-reduced-motion: reduce) { .gnomad-region, .gnomad-region-g, .gnomad-halo { transition: none; } .gnomad-map-pop { animation: none; } }
      `}</style>
      <div style={{ position: 'relative' }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="World map of gnomAD genetic ancestry group allele frequencies"
          style={{ width: '100%', aspectRatio: `${width} / ${height}`, display: 'block' }}
        >
          <rect
            x="0"
            y="0"
            width={width}
            height={height}
            fill={GNOMAD_MAP_SURFACE.ocean}
            onClick={() => onSelectGroup(null)}
          />
          <path
            d={GNOMAD_MAP_LAND}
            fill={GNOMAD_MAP_SURFACE.baseLand}
            stroke="none"
            onClick={() => onSelectGroup(null)}
          />
          {GNOMAD_MAP_REGIONS.map((region) => {
            const group = byGroup.get(region.group)
            const interactive = Boolean(group)
            const isSelected = selectedId === region.group
            const isHovered = hoveredId === region.group
            const emphasized = isSelected || isHovered
            const dimmed = selectedOnMap && !isSelected && !isHovered
            const fill = group
              ? bandFill(group.allele_frequency, group.data_state)
              : GNOMAD_MAP_SURFACE.noData
            const code = region.group.toUpperCase()
            return (
              <g
                key={region.group}
                className="gnomad-region-g"
                tabIndex={interactive ? 0 : undefined}
                role={interactive ? 'button' : undefined}
                data-gnomad-region={region.group}
                aria-label={
                  group
                    ? `${group.label}: ${formatFrequency(group.allele_frequency)}, allele number ${formatInteger(group.allele_number)}. ${groupContext(group)}`
                    : `${code}: not reported in this cohort`
                }
                onMouseEnter={interactive ? () => onHoverGroup(region.group) : undefined}
                onMouseLeave={interactive ? () => onHoverGroup(null) : undefined}
                onFocus={interactive ? () => onHoverGroup(region.group) : undefined}
                onBlur={interactive ? () => onHoverGroup(null) : undefined}
                onClick={interactive ? () => onSelectGroup(region.group) : undefined}
                style={{ cursor: interactive ? 'pointer' : 'default', opacity: dimmed ? 0.45 : 1 }}
              >
                <path
                  className="gnomad-region"
                  d={region.d}
                  data-active={emphasized ? 'true' : 'false'}
                  fill={fill}
                  fillOpacity={emphasized ? 1 : 0.92}
                  stroke={GNOMAD_MAP_SURFACE.regionStroke}
                  strokeWidth={0.6}
                  strokeLinejoin="round"
                />
                <text
                  x={region.labelX}
                  y={region.labelY}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={labelSize}
                  fontFamily="var(--mono)"
                  fontWeight={emphasized ? 700 : 600}
                  fill={GNOMAD_MAP_SURFACE.label}
                  paintOrder="stroke"
                  stroke={GNOMAD_MAP_SURFACE.regionStroke}
                  strokeWidth={3}
                  strokeLinejoin="round"
                  style={{ pointerEvents: 'none' }}
                >
                  {code}
                </text>
              </g>
            )
          })}
          <g style={{ pointerEvents: 'none' }}>
            {GNOMAD_MAP_REGIONS.map((region) => {
              const emphasized = region.group === selectedId || region.group === hoveredId
              return (
                <g key={`halo-${region.group}`}>
                  <path
                    className="gnomad-halo"
                    d={region.d}
                    fill="none"
                    stroke={GNOMAD_MAP_HOVER.haloDark}
                    strokeWidth={6}
                    strokeLinejoin="round"
                    style={{ strokeOpacity: emphasized ? 1 : 0 }}
                  />
                  <path
                    className="gnomad-halo"
                    d={region.d}
                    fill="none"
                    stroke={GNOMAD_MAP_HOVER.haloLight}
                    strokeWidth={2.75}
                    strokeLinejoin="round"
                    style={{ strokeOpacity: emphasized ? 1 : 0 }}
                  />
                </g>
              )
            })}
          </g>
        </svg>
        {popoverRegion && popoverGroup && (
          <MapSelectionPopover
            region={popoverRegion}
            group={popoverGroup}
            viewWidth={width}
            viewHeight={height}
          />
        )}
      </div>

      <MapLegendFooter />

      {showOffMap && offMapGroups.length > 0 && (
        <OffMapCohorts
          groups={offMapGroups}
          hoveredId={hoveredId}
          selectedId={selectedId}
          onHoverGroup={onHoverGroup}
          onSelectGroup={onSelectGroup}
        />
      )}
    </div>
  )
}

const POPOVER_ANCHORS: Record<string, { x: number; y: number }> = {
  afr: { x: 1300, y: 615 },
  amr: { x: 300, y: 560 },
  eas: { x: 1600, y: 505 },
  fin: { x: 775, y: 180 },
  mid: { x: 1235, y: 495 },
  nfe: { x: 800, y: 255 },
  sas: { x: 1390, y: 565 },
}

function MapSelectionPopover({
  region,
  group,
  viewWidth,
  viewHeight,
}: {
  region: (typeof GNOMAD_MAP_REGIONS)[number]
  group: PopulationFrequencyVisualGroup
  viewWidth: number
  viewHeight: number
}) {
  const anchor = POPOVER_ANCHORS[region.group] ?? { x: region.labelX, y: region.labelY }
  const leftPct = (anchor.x / viewWidth) * 100
  const topPct = (anchor.y / viewHeight) * 100
  const dot = bandFill(group.allele_frequency, group.data_state)
  return (
    <div
      className="gnomad-map-pop"
      role="status"
      style={{
        position: 'absolute',
        left: `${leftPct}%`,
        top: `${topPct}%`,
        transform: 'translate(-50%, -50%)',
        width: 190,
        maxWidth: '70%',
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 9,
        boxShadow: '0 8px 22px rgba(0,0,0,0.18)',
        padding: '8px 11px',
        pointerEvents: 'none',
        zIndex: 5,
      }}
    >
      <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.25 }}>
        {compactLabel(group.label)}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 7, marginTop: 4 }}>
        <span
          aria-hidden
          style={{
            width: 9,
            height: 9,
            borderRadius: 3,
            background: dot,
            border: '0.5px solid rgba(0,0,0,0.12)',
            flex: '0 0 auto',
            transform: 'translateY(1px)',
          }}
        />
        <span
          style={{
            fontFamily: 'var(--body)',
            fontVariantNumeric: 'tabular-nums',
            fontSize: 16,
            fontWeight: 700,
            color: 'var(--ink)',
          }}
        >
          {formatFrequency(group.allele_frequency)}
        </span>
        <span
          style={{
            fontSize: 9.5,
            color: 'var(--ink-4)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          allele freq
        </span>
      </div>
    </div>
  )
}

function OffMapCohorts({
  groups,
  hoveredId,
  selectedId,
  onHoverGroup,
  onSelectGroup,
}: PopulationGroupInteractionProps) {
  return (
    <div
      style={{
        borderTop: '0.5px solid var(--line)',
        background: 'var(--bg-soft)',
        padding: '10px 12px',
      }}
    >
      <div>
        {groups.length > 0 && (
          <div style={{ minWidth: 0 }}>
            <div className="eamos-kicker">Non-geographic cohorts</div>
            <div
              style={{
                marginTop: 3,
                fontSize: 10.5,
                color: 'var(--ink-4)',
                lineHeight: 1.4,
              }}
            >
              Defined by genetic similarity rather than geography, so they are shown off the map.
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {groups.map((group) => {
                const isSelected = selectedId === group.id
                const isHovered = hoveredId === group.id
                const emphasized = isSelected || isHovered
                const dot = bandFill(group.allele_frequency, group.data_state)
                return (
                  <button
                    key={group.id}
                    type="button"
                    data-gnomad-offmap={group.id}
                    aria-pressed={isSelected}
                    title={`${group.label}; ${groupContext(group)}`}
                    onMouseEnter={() => onHoverGroup(group.id)}
                    onMouseLeave={() => onHoverGroup(null)}
                    onFocus={() => onHoverGroup(group.id)}
                    onBlur={() => onHoverGroup(null)}
                    onClick={() => onSelectGroup(group.id)}
                    style={{
                      border: '0.5px solid',
                      borderColor: emphasized ? '#fde047' : 'var(--line)',
                      background: emphasized ? 'rgba(254, 249, 195, 0.72)' : 'var(--bg)',
                      boxShadow: isSelected ? '0 0 0 2px rgba(253, 224, 71, 0.9)' : 'none',
                      borderRadius: 'var(--r-sm)',
                      padding: '4px 8px',
                      textAlign: 'left',
                      cursor: 'pointer',
                      width: FOOTER_CHIP_WIDTH,
                      minHeight: FOOTER_CHIP_MIN_HEIGHT,
                      boxSizing: 'border-box',
                      transition:
                        'border-color 140ms ease, background 140ms ease, box-shadow 160ms var(--ease-standard)',
                    }}
                  >
                    <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                      <span
                        aria-hidden
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: 3,
                          background: dot,
                          border: '0.5px solid rgba(0,0,0,0.12)',
                          flex: '0 0 auto',
                          marginTop: 3,
                        }}
                      />
                      <div style={{ minWidth: 0 }}>
                        <div className="flex items-baseline gap-1.5">
                          <span
                            style={{
                              fontFamily: 'var(--mono)',
                              fontSize: 10.5,
                              fontWeight: 700,
                              color: 'var(--ink-2)',
                            }}
                          >
                            {group.id.toUpperCase()}
                          </span>
                          <span
                            style={{
                              fontFamily: 'var(--body)',
                              fontVariantNumeric: 'tabular-nums',
                              fontSize: 9.6,
                              color: 'var(--ink-3)',
                            }}
                          >
                            {formatFrequency(group.allele_frequency)}
                          </span>
                        </div>
                        <div style={FOOTER_CHIP_DESC_STYLE}>{offMapOriginCopy(group.id)}</div>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const BAND_TAG_MEANING: Record<string, string> = {
  BA1: 'General BA1 reference band (allele frequency ≥ 5%); active gene/disease policy may differ',
  BS1: 'General BS1 reference band; active gene/disease policy may differ',
  PM2: 'General PM2 reference band; active policy and data-quality gates determine scoring',
  Intermediate:
    'Intermediate — too rare to call benign (below BS1), too common for PM2; allele frequency gives no ACMG evidence either way.',
}

function MapLegendFooter() {
  return (
    <div
      style={{
        borderTop: '0.5px solid var(--line)',
        background: 'var(--bg)',
        padding: '9px 12px',
        fontSize: 11,
        color: 'var(--ink-3)',
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div
          className="flex flex-wrap items-center gap-x-3 gap-y-1"
          aria-label="Allele frequency bands"
        >
          {GNOMAD_AF_BANDS.map((band) => (
            <LegendSwatch
              key={band.id}
              color={band.color}
              label={band.label}
              tag={band.acmg ?? (band.id === 'uncommon' ? 'Intermediate' : null)}
            />
          ))}
          <LegendSwatch color={GNOMAD_MAP_SURFACE.noData} label="Not observed" tag={null} />
        </div>
        <InfoPopover label="How to read this map">
          <div
            style={{
              fontWeight: 700,
              color: 'var(--ink)',
              fontSize: 11.5,
              marginBottom: 6,
            }}
          >
            Reading the colours
          </div>
          <div>
            Colour is the variant’s <strong>absolute allele frequency</strong> in each gnomAD
            group, against fixed general ACMG-style reference cutoffs. The EAMOS advisory uses its
            version-pinned gene/disease policy, which may differ:
          </div>
          <ul
            style={{
              margin: '6px 0 10px',
              paddingLeft: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
            }}
          >
            <li><strong>BA1 / BS1</strong> (green) — common; supports a benign call.</li>
            <li><strong>Intermediate</strong> (amber) — frequency gives no evidence either way.</li>
            <li><strong>PM2</strong> (red) — very rare or absent; supports a pathogenic call.</li>
            <li><strong>Not observed</strong> (grey) — cohort is covered, variant not seen.</li>
          </ul>
          <div
            style={{
              fontWeight: 700,
              color: 'var(--ink)',
              fontSize: 11.5,
              marginBottom: 6,
            }}
          >
            Method &amp; sources
          </div>
          <div>
            Basemap from Natural Earth (public domain); regions are dissolved from member countries
            and land-clipped. gnomAD groups describe genetic-similarity cohorts — not race,
            ethnicity, patient ancestry, or exact geography. Algorithm {GNOMAD_ANCESTRY_MAP_VERSION}.
          </div>
        </InfoPopover>
      </div>
    </div>
  )
}

function LegendSwatch({
  color,
  label,
  tag,
}: {
  color: string
  label: string
  tag: string | null
}) {
  return (
    <span className="inline-flex items-center gap-1.5" style={{ fontSize: 10.5 }}>
      <span
        aria-hidden
        style={{
          width: 12,
          height: 12,
          borderRadius: 3,
          background: color,
          border: '0.5px solid rgba(0,0,0,0.12)',
          flex: '0 0 auto',
        }}
      />
      <span style={{ color: 'var(--ink-2)' }}>{label}</span>
      {tag && (
        <span
          title={BAND_TAG_MEANING[tag] ?? tag}
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 9,
            fontWeight: 700,
            color: 'var(--ink-4)',
            border: '0.5px solid var(--line)',
            borderRadius: 4,
            padding: '0 3px',
            cursor: 'help',
          }}
        >
          {tag}
        </span>
      )}
    </span>
  )
}
