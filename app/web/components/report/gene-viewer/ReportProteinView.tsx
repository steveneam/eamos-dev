'use client'

import { useMemo, useState, type CSSProperties } from 'react'

import type { ProteinAlphaMissenseHeatmap, ProteinDomainTrack } from '@/lib/backend'
import { classLabel, type ClinClass, type GeneWindowData } from '@/lib/workbench/gene-window'

import {
  CLASS_COLOR,
  StatPill,
  SvgVariantMarker,
  clamp,
  formatInt,
  queriedVariantMarkerKind,
  toggleLabelStyle,
  trackScrollStyle,
  variantMarkerKindLabel,
} from './geneViewerPresentation'
import {
  DEFAULT_VISIBLE_PROTEIN_LANES,
  HEAT_MAX_BINS,
  PROTEIN_HEAT_H,
  PROTEIN_LANE_H,
  PROTEIN_LANE_TOP,
  PROTEIN_LEFT,
  PROTEIN_MARKER_Y,
  PROTEIN_RIGHT,
  alphaColor,
  categorySwatchStyle,
  featureCategoryLegendItems,
  featureColor,
  featureLegendItems,
  featureTitle,
  featuresFromTrack,
  featuresFromViewer,
  isPointProteinFeature,
  labelForFeatureWidth,
  packProteinFeatures,
  proteinArchitectureFeatures,
  proteinCanvasWidth,
  proteinFeaturePatternId,
  proteinLanesFor,
  proteinScaleTicks,
  proteinSourceLabel,
  type ProteinLaneId,
} from './proteinViewModel'

interface ReportProteinViewProps {
  data: GeneWindowData
  track: ProteinDomainTrack | null
  alphaHeatmap: ProteinAlphaMissenseHeatmap | null
  includeAlphaMissense: boolean
  onToggleAlphaMissense: (value: boolean) => void
  markerClassification: ClinClass
}

export function ReportProteinView({
  data,
  track,
  alphaHeatmap,
  includeAlphaMissense,
  onToggleAlphaMissense,
  markerClassification,
}: ReportProteinViewProps) {
  const [selectedFeatureKeys, setSelectedFeatureKeys] = useState<Set<string>>(() => new Set())
  const [visibleFeatureLanes, setVisibleFeatureLanes] = useState<Set<ProteinLaneId>>(
    () => new Set(DEFAULT_VISIBLE_PROTEIN_LANES),
  )
  const [showProteinScale, setShowProteinScale] = useState(true)
  const trackFeatures = track?.features ?? []
  const trackRanges = trackFeatures.length > 0 ? featuresFromTrack(trackFeatures) : []
  const viewerRanges = featuresFromViewer(data)
  const rawRanges = trackRanges.length > 0 ? [...trackRanges, ...viewerRanges] : viewerRanges
  const sourceFeatureCount = trackRanges.length > 0 ? trackRanges.length : rawRanges.length
  const architectureRanges = proteinArchitectureFeatures(rawRanges)
  const ranges = architectureRanges.filter((feature) => visibleFeatureLanes.has(feature.lane))
  const summarizedFeatureCount = Math.max(0, rawRanges.length - architectureRanges.length)
  const hiddenFeatureCount = Math.max(0, architectureRanges.length - ranges.length)
  const proteinLength = Math.max(
    1,
    track?.protein_length ??
      alphaHeatmap?.protein_length ??
      data.proteinProduct?.referenceProteinLength ??
      data.proteinLength ??
      1,
  )
  const proteinWidth = proteinCanvasWidth(proteinLength, architectureRanges.length)
  const proteinTrackW = proteinWidth - PROTEIN_LEFT - PROTEIN_RIGHT
  const product = data.proteinProduct
  const queriedAa = clamp(
    data.queriedVariant.codonNumber || Math.ceil(data.queriedVariant.cdsPos / 3) || 1,
    1,
    proteinLength,
  )
  const queriedMarkerKind = queriedVariantMarkerKind(data.queriedVariant)
  const queriedMarkerFill = CLASS_COLOR[markerClassification] ?? 'var(--cls-vus-dot)'
  const xFor = (aa: number) =>
    PROTEIN_LEFT +
    ((clamp(aa, 1, proteinLength) - 1) / Math.max(1, proteinLength - 1)) * proteinTrackW
  const scaleTicks = proteinScaleTicks(proteinLength)
  const sourceLabel = proteinSourceLabel(track, ranges.length > 0)
  const lanes = proteinLanesFor(architectureRanges)
  const { packedFeatures } = packProteinFeatures(ranges, lanes, xFor)
  const proteinBackboneY = PROTEIN_LANE_TOP + 28
  const proteinBackboneH = PROTEIN_LANE_H
  const proteinHeatY = proteinBackboneY + proteinBackboneH + 24
  const proteinScaleY = proteinHeatY + PROTEIN_HEAT_H + 24
  const proteinHeight = proteinScaleY + 34
  const legendItems = featureLegendItems(ranges)
  const categoryItems = featureCategoryLegendItems(architectureRanges)
  const toggleFeatureKey = (key: string) => {
    setSelectedFeatureKeys((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }
  const toggleVisibleLane = (lane: ProteinLaneId) => {
    setVisibleFeatureLanes((current) => {
      const next = new Set(current)
      if (next.has(lane)) next.delete(lane)
      else next.add(lane)
      return next
    })
  }
  const alphaAvailable =
    includeAlphaMissense &&
    alphaHeatmap != null &&
    (alphaHeatmap.status === 'available' || alphaHeatmap.status === 'partial') &&
    alphaHeatmap.residues.length > 0
  const alphaUnavailable = includeAlphaMissense && !alphaAvailable
  const alphaBins = useMemo(() => {
    const residues = alphaHeatmap?.residues ?? []
    if (residues.length === 0) return []
    const groupSize = Math.max(1, Math.ceil(residues.length / HEAT_MAX_BINS))
    const bins: { aaStart: number; aaEnd: number; score: number; variants: number }[] = []
    for (let index = 0; index < residues.length; index += groupSize) {
      const end = Math.min(index + groupSize, residues.length)
      let sum = 0
      let scored = 0
      let variants = 0
      for (let residueIndex = index; residueIndex < end; residueIndex += 1) {
        const score = residues[residueIndex].mean_score
        if (score != null) {
          sum += score
          scored += 1
        }
        variants += residues[residueIndex].scored_variant_count ?? 0
      }
      if (scored === 0) continue
      bins.push({
        aaStart: residues[index].aa,
        aaEnd: residues[end - 1].aa,
        score: sum / scored,
        variants,
      })
    }
    return bins
  }, [alphaHeatmap])

  return (
    <div style={proteinShellStyle}>
      <div style={proteinHeadStyle}>
        <div style={{ minWidth: 0 }}>
          <span className="eamos-kicker">Protein architecture &amp; features</span>
          <div style={proteinTitleStyle}>
            {product?.label ?? (data.queriedVariant.hgvsP || data.queriedVariant.hgvsC)}
          </div>
        </div>
        <div style={proteinControlsStyle}>
          <StatPill label={`${formatInt(proteinLength)} aa`} />
          <StatPill label={`${ranges.length} visible features`} />
          {sourceFeatureCount > 0 && <StatPill label={`${sourceFeatureCount} source hits`} />}
          <label style={toggleLabelStyle}>
            <input
              type="checkbox"
              checked={includeAlphaMissense}
              onChange={(event) => onToggleAlphaMissense(event.target.checked)}
              style={{ accentColor: 'var(--teal)' }}
            />
            AlphaMissense
          </label>
          <label style={toggleLabelStyle}>
            <input
              type="checkbox"
              checked={showProteinScale}
              onChange={(event) => setShowProteinScale(event.target.checked)}
              style={{ accentColor: 'var(--teal)' }}
            />
            Scale
          </label>
        </div>
      </div>
      {categoryItems.length > 0 && (
        <div style={featureToggleRowStyle} aria-label="Protein feature visibility">
          {categoryItems.map((item) => (
            <label
              key={item.lane}
              style={categoryToggleStyle(visibleFeatureLanes.has(item.lane), item.color)}
            >
              <input
                type="checkbox"
                checked={visibleFeatureLanes.has(item.lane)}
                onChange={() => toggleVisibleLane(item.lane)}
                style={{ accentColor: item.color.stroke }}
              />
              <span style={categorySwatchStyle(item.lane, item.color)} />
              {item.label}
            </label>
          ))}
        </div>
      )}

      <div style={trackScrollStyle}>
        <svg
          viewBox={`0 0 ${proteinWidth} ${proteinHeight}`}
          role="img"
          aria-label={`${data.gene} protein view with architecture feature annotations`}
          style={{ display: 'block', width: proteinWidth, maxWidth: 'none', height: 'auto' }}
        >
          <defs>
            <pattern id="protein-pattern-topology" width="8" height="8" patternUnits="userSpaceOnUse">
              <path d="M-2 8 L8 -2 M2 10 L10 2" stroke="rgba(155, 87, 34, 0.46)" strokeWidth="1" />
            </pattern>
            <pattern id="protein-pattern-motifs" width="7" height="7" patternUnits="userSpaceOnUse">
              <path d="M1 0 V7 M5 0 V7" stroke="rgba(111, 82, 164, 0.42)" strokeWidth="0.9" />
            </pattern>
            <pattern id="protein-pattern-sites" width="7" height="7" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1.1" fill="rgba(172, 132, 34, 0.52)" />
            </pattern>
            <pattern id="protein-pattern-other" width="8" height="8" patternUnits="userSpaceOnUse">
              <path d="M0 2 H8 M0 6 H8" stroke="rgba(92, 107, 122, 0.36)" strokeWidth="0.9" />
            </pattern>
          </defs>
          <rect x="0" y="0" width={proteinWidth} height={proteinHeight} rx="8" fill="var(--bg-soft)" />

          <g>
            <text x={PROTEIN_LEFT} y={proteinBackboneY - 16} fontSize="9.5" fontWeight="800" fill="var(--ink-5)">
              Protein
            </text>
            <rect
              x={PROTEIN_LEFT}
              y={proteinBackboneY}
              width={proteinTrackW}
              height={proteinBackboneH}
              rx="2"
              fill="var(--bg)"
              stroke="var(--ink)"
              strokeWidth="1.35"
            />
          </g>

          {packedFeatures.map((feature, index) => {
            const pointFeature = isPointProteinFeature(feature)
            const width = pointFeature ? Math.max(5, feature.width) : feature.width
            const x = pointFeature
              ? clamp(feature.x - width / 2, PROTEIN_LEFT, PROTEIN_LEFT + proteinTrackW - width)
              : feature.x
            const color = featureColor(feature)
            const label = labelForFeatureWidth(feature, width)
            const patternId = proteinFeaturePatternId(feature)
            const highlighted = selectedFeatureKeys.has(feature.legendKey)
            const stroke = highlighted ? 'rgba(225, 164, 35, 0.96)' : 'var(--ink)'
            const strokeWidth = highlighted ? 3 : 0.85
            return (
              <g
                key={`${feature.kind}-${feature.start}-${feature.end}-${index}`}
                role="button"
                tabIndex={0}
                aria-label={featureTitle(feature)}
                aria-pressed={highlighted}
                style={{ cursor: 'pointer' }}
                onClick={() => toggleFeatureKey(feature.legendKey)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    toggleFeatureKey(feature.legendKey)
                  }
                }}
              >
                <rect
                  x={x}
                  y={proteinBackboneY}
                  width={width}
                  height={proteinBackboneH}
                  rx="2"
                  fill={color.fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                />
                {patternId && (
                  <rect
                    x={x}
                    y={proteinBackboneY}
                    width={width}
                    height={proteinBackboneH}
                    rx="2"
                    fill={`url(#${patternId})`}
                    pointerEvents="none"
                  />
                )}
                {label && (
                  <text
                    x={x + width / 2}
                    y={proteinBackboneY + proteinBackboneH / 2 + 3.8}
                    textAnchor="middle"
                    fontSize="10.5"
                    fontWeight="800"
                    fill={color.text}
                  >
                    {label}
                  </text>
                )}
                <title>{featureTitle(feature)}</title>
              </g>
            )
          })}

          {alphaAvailable &&
            alphaBins.map((bin) => {
              const x = xFor(bin.aaStart)
              const width = Math.max(2, xFor(bin.aaEnd + 1) - x)
              const range = bin.aaStart === bin.aaEnd ? `aa ${bin.aaStart}` : `aa ${bin.aaStart}–${bin.aaEnd}`
              return (
                <rect
                  key={`am-${bin.aaStart}`}
                  x={x}
                  y={proteinHeatY}
                  width={width}
                  height={PROTEIN_HEAT_H}
                  fill={alphaColor(bin.score)}
                >
                  <title>{`AlphaMissense mean ${bin.score.toFixed(3)} | ${range} | ${bin.variants} substitutions`}</title>
                </rect>
              )
            })}
          {includeAlphaMissense && (
            <rect
              x={PROTEIN_LEFT}
              y={proteinHeatY}
              width={proteinTrackW}
              height={PROTEIN_HEAT_H}
              fill="none"
              stroke="var(--line)"
              strokeWidth="0.6"
            />
          )}

          <line
            x1={xFor(queriedAa)}
            y1={PROTEIN_MARKER_Y + 6}
            x2={xFor(queriedAa)}
            y2={proteinBackboneY}
            stroke="var(--ink)"
            strokeWidth="1.6"
          />
          <SvgVariantMarker
            kind={queriedMarkerKind}
            x={xFor(queriedAa)}
            y={PROTEIN_MARKER_Y}
            size={6}
            fill={queriedMarkerFill}
            stroke="var(--ink)"
            strokeWidth={1.4}
            title={`${data.queriedVariant.hgvsP || `aa ${queriedAa}`} | ${classLabel(markerClassification)} | ${variantMarkerKindLabel(queriedMarkerKind)}`}
          />
          <text
            x={clamp(xFor(queriedAa), PROTEIN_LEFT + 58, PROTEIN_LEFT + proteinTrackW - 58)}
            y={PROTEIN_MARKER_Y - 11}
            textAnchor="middle"
            fontSize="11.5"
            fontFamily="var(--mono)"
            fontWeight="700"
            fill="var(--ink)"
          >
            {data.queriedVariant.hgvsP || `aa ${queriedAa}`}
          </text>

          {showProteinScale && (
            <g aria-hidden="true">
              <line
                x1={PROTEIN_LEFT}
                y1={proteinScaleY}
                x2={PROTEIN_LEFT + proteinTrackW}
                y2={proteinScaleY}
                stroke="var(--ink-3)"
                strokeWidth="0.8"
              />
              {scaleTicks.map((tick) => {
                const x = xFor(tick.aa)
                const terminalTick = scaleTicks.find((candidate) => candidate.terminal)
                const closeToTerminal =
                  !tick.terminal && terminalTick != null && Math.abs(x - xFor(terminalTick.aa)) < 46
                const label =
                  tick.aa === 1
                    ? '1'
                    : tick.terminal
                      ? `${tick.aa} aa`
                      : tick.major && !closeToTerminal
                        ? String(tick.aa)
                        : null
                return (
                  <g key={tick.aa}>
                    <line
                      x1={x}
                      y1={proteinScaleY - (tick.major ? 7 : 4)}
                      x2={x}
                      y2={proteinScaleY + (tick.major ? 8 : 5)}
                      stroke={tick.major ? 'var(--ink-3)' : 'var(--ink-5)'}
                      strokeWidth={tick.major ? 0.85 : 0.55}
                    />
                    {label && (
                      <text
                        x={x}
                        y={proteinScaleY + 21}
                        textAnchor={tick.aa === 1 ? 'start' : tick.terminal ? 'end' : 'middle'}
                        fontSize="10"
                        fill="var(--ink-4)"
                        fontFamily="var(--mono)"
                      >
                        {label}
                      </text>
                    )}
                  </g>
                )
              })}
            </g>
          )}
        </svg>
      </div>

      {ranges.length > 0 && (
        <div style={proteinLegendStyle}>
          {lanes
            .filter((lane, index) => ranges.length > 0 && index === 0)
            .map((lane) => {
              const color = { fill: 'var(--bg)', stroke: 'var(--ink)' }
              return (
                <span key={lane.id} style={proteinLegendItemStyle}>
                  <span
                    style={{
                      width: 12,
                      height: 7,
                      borderRadius: 2,
                      background: color.fill,
                      border: `0.5px solid ${color.stroke}`,
                      display: 'inline-block',
                    }}
                  />
                  Protein backbone
                </span>
              )
            })}
          {featureCategoryLegendItems(ranges).map((item) => (
            <span key={item.label} style={proteinLegendItemStyle}>
              <span style={categorySwatchStyle(item.lane, item.color)} />
              {item.label}
            </span>
          ))}
          <span style={proteinLegendItemStyle}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: 'var(--ink)',
                display: 'inline-block',
              }}
            />
            Query
          </span>
        </div>
      )}

      <div style={proteinFootStyle}>
        <span>{sourceLabel}</span>
        {summarizedFeatureCount > 0 && (
          <span>{`${summarizedFeatureCount} broad, overlapping, alternate, or weak source hit${summarizedFeatureCount === 1 ? '' : 's'} retained as provenance outside the primary architecture figure.`}</span>
        )}
        {hiddenFeatureCount > 0 && (
          <span>{`${hiddenFeatureCount} feature${hiddenFeatureCount === 1 ? '' : 's'} hidden by category filters.`}</span>
        )}
        {product?.description && <span>{product.description}</span>}
        {alphaAvailable && (
          <span>
            AlphaMissense {alphaHeatmap.aa_start}-{alphaHeatmap.aa_end ?? proteinLength} aa
            {alphaHeatmap.queried_score != null
              ? ` | query ${alphaHeatmap.queried_score.toFixed(3)}${alphaHeatmap.queried_calibrated_label ? ` ${alphaHeatmap.queried_calibrated_label}` : ''}`
              : ''}
          </span>
        )}
        {alphaUnavailable && (
          <span>AlphaMissense unavailable: {alphaHeatmap?.fail_closed_reason ?? 'not returned'}</span>
        )}
      </div>

      {legendItems.length > 0 && (
        <div style={featureGridStyle}>
          {legendItems.map((item) => (
            <button
              key={item.key}
              type="button"
              style={featureChipStyle(selectedFeatureKeys.has(item.key), item.color)}
              title={item.title}
              onClick={() => toggleFeatureKey(item.key)}
              aria-pressed={selectedFeatureKeys.has(item.key)}
            >
              <span style={featureKindStyle}>{item.kindLabel}</span>
              <span style={featureLabelStyle}>
                {item.short}
                {item.count > 1 ? ` x${item.count}` : ''}
              </span>
              {item.description && <span style={featureDescriptionStyle}>{item.description}</span>}
              <span style={featureCoordStyle}>{item.coordLabel}</span>
              {selectedFeatureKeys.has(item.key) && item.ranges.length > 1 && (
                <span style={featureRangeListStyle}>
                  {item.ranges.map((range, index) => (
                    <span
                      key={`${item.key}-${range.start}-${range.end}-${index}`}
                      style={featureRangePillStyle}
                    >
                      {range.start === range.end ? range.start : `${range.start}-${range.end}`}
                    </span>
                  ))}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

const proteinShellStyle: CSSProperties = {
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg)',
  padding: 12,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const proteinHeadStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
  flexWrap: 'wrap',
}

const proteinTitleStyle: CSSProperties = {
  marginTop: 4,
  fontSize: 12.5,
  fontWeight: 700,
  color: 'var(--ink)',
}

const proteinControlsStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: 6,
  flexWrap: 'wrap',
}

const featureToggleRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  flexWrap: 'wrap',
}

function categoryToggleStyle(
  active: boolean,
  color: { fill: string; stroke: string; text: string },
): CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    border: `0.5px solid ${active ? color.stroke : 'var(--line)'}`,
    borderRadius: 999,
    background: active ? color.fill : 'var(--bg-soft)',
    color: active ? color.text : 'var(--ink-4)',
    padding: '3px 9px',
    fontSize: 10.5,
    fontWeight: 700,
    whiteSpace: 'nowrap',
  }
}

const proteinFootStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexWrap: 'wrap',
  fontSize: 10.5,
  color: 'var(--ink-4)',
}

const proteinLegendStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexWrap: 'wrap',
  fontSize: 10.5,
  color: 'var(--ink-4)',
}

const proteinLegendItemStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 5,
  fontWeight: 700,
}

const featureGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
  gap: 6,
}

function featureChipStyle(
  selected: boolean,
  color: { fill: string; stroke: string },
): CSSProperties {
  return {
    border: '0.5px solid var(--line)',
    borderRadius: 6,
    background: selected ? 'rgba(225, 164, 35, 0.13)' : 'var(--bg-soft)',
    padding: '7px 8px',
    display: 'grid',
    gap: 2,
    minWidth: 0,
    textAlign: 'left',
    cursor: 'pointer',
    appearance: 'none',
    font: 'inherit',
    color: 'inherit',
    boxShadow: selected
      ? `inset 0 0 0 1.5px rgba(225, 164, 35, 0.88), 3px 0 0 ${color.stroke}`
      : `3px 0 0 ${color.stroke}`,
  }
}

const featureKindStyle: CSSProperties = {
  fontSize: 9.5,
  color: 'var(--ink-5)',
  textTransform: 'uppercase',
  letterSpacing: 0,
  fontWeight: 800,
}

const featureLabelStyle: CSSProperties = {
  fontSize: 11,
  color: 'var(--ink-2)',
  fontWeight: 700,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
}

const featureDescriptionStyle: CSSProperties = {
  fontSize: 10,
  color: 'var(--ink-3)',
  lineHeight: 1.25,
}

const featureCoordStyle: CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: 10,
  color: 'var(--ink-4)',
}

const featureRangeListStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 4,
  paddingTop: 4,
}

const featureRangePillStyle: CSSProperties = {
  border: '0.5px solid rgba(225, 164, 35, 0.44)',
  borderRadius: 999,
  background: 'rgba(255, 247, 218, 0.74)',
  color: 'rgb(104, 71, 18)',
  fontFamily: 'var(--mono)',
  fontSize: 9.5,
  fontWeight: 700,
  padding: '2px 5px',
}
