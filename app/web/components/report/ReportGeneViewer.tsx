'use client'

import { useEffect, useMemo, useState } from 'react'
import { getGeneViewer } from '@/lib/api'
import { adaptGeneViewer, geneViewerScaffoldWarnings } from '@/lib/workbench/gene-viewer-adapter'
import { GENE_VIEWER_SAMPLE } from '@/lib/workbench/gene-viewer-sample'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import type {
  GeneViewerResponse,
  ProteinAlphaMissenseHeatmap,
  ProteinDomainTrack,
  ProteinDomainTrackFeature,
} from '@/lib/backend'
import { ProvenanceNote } from '@/components/report/ProvenanceNote'

interface ReportGeneViewerProps {
  gene: string
  cdna: string
  transcript?: string | null
  proteinDomainTrack?: ProteinDomainTrack | null
  /** Offline fixture mode — render from the bundled GENE_VIEWER_SAMPLE without
   *  a network call, matching the explicit fixture report. */
  demo?: boolean
}

// Slice B build 1 — read-only "report mode" genomic track for §4.
//
// Replaces the redundant gene-snapshot SVG + expandable transcript figures
// inside the old GeneContextSnapshotSection. Fetches the same backend
// /api/v1/viewer payload the Workbench uses, then projects it through the
// shared gene-viewer adapter so the renderer reads the canonical
// `GeneWindowData` shape. The Workbench's full SequenceViewerV2 (edit hub,
// scratch, codon detail, popover, history) is deliberately NOT embedded —
// the report wants a static visual, not an editor.
//
// What this renders today:
//   - compressed exon/intron track with queried-variant marker above
//   - ClinVar variant density along the track (color-ramp by class)
//   - gene-summary header (strand · length · exon count · ClinVar count)
//   - small legend
// Density toggle + variant-label collision-avoid land in a later slice
// once the protein-domain backend ships (CAR for Codex).

const CLASS_COLOR: Record<string, string> = {
  p: 'var(--cls-path-dot)',
  lp: 'var(--cls-lpath-dot)',
  vus: 'var(--cls-vus-dot)',
  lb: 'var(--cls-lben-dot)',
  b: 'var(--cls-ben-dot)',
}

const VIEW_W = 920
const TRACK_LEFT = 36
const TRACK_RIGHT = 28
const TRACK_Y = 96
const EXON_H = 26
const VIEW_H = 184
const TRACK_MAX_W = 4200

interface OverviewSeg {
  key: string
  kind: 'exon' | 'intron'
  num: number
  leftPct: number
  widthPct: number
  bp: number
  /** CDS-coordinate start of the segment (exons only) for variant projection. */
  cdsStart?: number
  cdsEnd?: number
}

function buildSegments(data: GeneWindowData): OverviewSeg[] {
  const raw: Array<Omit<OverviewSeg, 'leftPct' | 'widthPct'> & { units: number }> = []
  const minExon = 14
  const maxIntron = 60

  // Interleave exons + introns (intron N follows exon N).
  data.exons.forEach((exon, i) => {
    const bp = Math.max(1, exon.cdsEnd - exon.cdsStart + 1)
    raw.push({
      key: `e-${exon.num}`,
      kind: 'exon',
      num: exon.num,
      bp,
      cdsStart: exon.cdsStart,
      cdsEnd: exon.cdsEnd,
      units: Math.max(minExon, Math.sqrt(bp) * 2.4),
    })
    const intron = data.introns[i]
    if (intron) {
      raw.push({
        key: `i-${intron.num}`,
        kind: 'intron',
        num: intron.num,
        bp: intron.lenBp,
        units: Math.min(maxIntron, Math.max(10, Math.log10(intron.lenBp + 1) * 14)),
      })
    }
  })

  const total = raw.reduce((s, r) => s + r.units, 0) || 1
  let cursor = 0
  return raw.map((r) => {
    const leftPct = (cursor / total) * 100
    const widthPct = (r.units / total) * 100
    cursor += r.units
    return {
      key: r.key,
      kind: r.kind,
      num: r.num,
      bp: r.bp,
      cdsStart: r.cdsStart,
      cdsEnd: r.cdsEnd,
      leftPct,
      widthPct,
    }
  })
}

function projectCdsToPct(cdsPos: number, segments: OverviewSeg[]): number | null {
  const seg = segments.find(
    (s) => s.kind === 'exon' && s.cdsStart != null && s.cdsEnd != null && cdsPos >= s.cdsStart && cdsPos <= s.cdsEnd,
  )
  if (!seg || seg.cdsStart == null || seg.cdsEnd == null) return null
  const ratio = (cdsPos - seg.cdsStart) / Math.max(1, seg.cdsEnd - seg.cdsStart + 1)
  return seg.leftPct + seg.widthPct * Math.min(1, Math.max(0, ratio))
}

function formatInt(n: number): string {
  return n.toLocaleString('en-US')
}

function geneTrackWidth(data: GeneWindowData, totalClinvar: number): number {
  const exonUnits = data.exons.length * 34
  const intronUnits = data.introns.length * 10
  const markerUnits = Math.min(900, totalClinvar * 3)
  return Math.round(Math.min(TRACK_MAX_W, Math.max(VIEW_W, TRACK_LEFT + TRACK_RIGHT + exonUnits + intronUnits + markerUnits)))
}

function warningsForViewer(resp: GeneViewerResponse): string[] {
  const trackWarnings = resp.tracks.protein_features.domain_track?.warnings ?? []
  const alphamissenseWarnings = resp.tracks.alphamissense_heatmap?.warnings ?? []
  return Array.from(new Set([...geneViewerScaffoldWarnings(resp), ...trackWarnings, ...alphamissenseWarnings]))
}

export function ReportGeneViewer({
  gene,
  cdna,
  transcript,
  proteinDomainTrack = null,
  demo = false,
}: ReportGeneViewerProps) {
  // Fixture/offline mode renders the bundled sample synchronously, so the
  // explicit negative-control fixture never depends on a live backend.
  const [data, setData] = useState<GeneWindowData | null>(() =>
    demo ? adaptGeneViewer(GENE_VIEWER_SAMPLE, 'variant') : null,
  )
  const [proteinTrack, setProteinTrack] = useState<ProteinDomainTrack | null>(() =>
    demo ? GENE_VIEWER_SAMPLE.tracks.protein_features.domain_track ?? null : null,
  )
  const [alphaHeatmap, setAlphaHeatmap] = useState<ProteinAlphaMissenseHeatmap | null>(() =>
    demo ? GENE_VIEWER_SAMPLE.tracks.alphamissense_heatmap ?? null : null,
  )
  const [includeAlphaMissense, setIncludeAlphaMissense] = useState(false)
  // Provenance warnings (sample-bounded / not-live-hydrated / RPE65 scaffold)
  // surfaced as a per-section note so non-live data is never silent.
  const [warnings, setWarnings] = useState<string[]>(() =>
    demo ? warningsForViewer(GENE_VIEWER_SAMPLE) : [],
  )
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!demo)

  useEffect(() => {
    let cancelled = false
    if (demo) {
      void Promise.resolve().then(() => {
        if (cancelled) return
        setData(adaptGeneViewer(GENE_VIEWER_SAMPLE, 'variant'))
        setProteinTrack(GENE_VIEWER_SAMPLE.tracks.protein_features.domain_track ?? null)
        setAlphaHeatmap(
          includeAlphaMissense ? GENE_VIEWER_SAMPLE.tracks.alphamissense_heatmap ?? null : null,
        )
        setWarnings(warningsForViewer(GENE_VIEWER_SAMPLE))
        setError(null)
        setLoading(false)
      })
      return () => {
        cancelled = true
      }
    }
    void Promise.resolve().then(() => {
      if (cancelled) return
      setLoading(true)
      setError(null)
    })
    getGeneViewer({
      gene,
      cdna,
      transcript: transcript ?? null,
      species: 'human',
      allele_mode: 'variant',
      window: {
        kind: 'around_variant',
        cds_flank_bp: 120,
        intron_flank_bp: 30,
      },
      tracks: includeAlphaMissense
        ? ['sequence', 'exons', 'clinvar', 'protein_features', 'alphamissense', 'restriction']
        : ['sequence', 'exons', 'clinvar', 'protein_features', 'restriction'],
    })
      .then((resp) => {
        if (cancelled) return
        setData(adaptGeneViewer(resp, 'variant'))
        setProteinTrack(resp.tracks.protein_features.domain_track ?? null)
        setAlphaHeatmap(resp.tracks.alphamissense_heatmap ?? null)
        setWarnings(warningsForViewer(resp))
        setLoading(false)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [gene, cdna, transcript, demo, includeAlphaMissense])

  const segments = useMemo(() => (data ? buildSegments(data) : []), [data])
  const variantPct = useMemo(() => {
    if (!data || segments.length === 0) return null
    return projectCdsToPct(data.queriedVariant.cdsPos, segments)
  }, [data, segments])

  // ClinVar variants live on CDS coords (or are intronic — skip those without
  // numeric cdsPos). Cluster by class for the legend.
  const clinvarMarks = useMemo(() => {
    if (!data) return []
    return data.clinvar
      .filter((v) => typeof v.cdsPos === 'number' && !v.queried)
      .map((v) => {
        const pct = projectCdsToPct(v.cdsPos as number, segments)
        if (pct == null) return null
        return { pct, cls: v.cls, label: v.hgvsP || v.hgvsC, cv: v.cv }
      })
      .filter((m): m is NonNullable<typeof m> => m != null)
  }, [data, segments])

  const clinvarCounts = useMemo(() => {
    const counts: Record<string, number> = { p: 0, lp: 0, vus: 0, lb: 0, b: 0 }
    for (const m of clinvarMarks) counts[m.cls] = (counts[m.cls] ?? 0) + 1
    return counts
  }, [clinvarMarks])
  const renderedProteinTrack = proteinDomainTrack ?? proteinTrack
  const renderedWarnings = useMemo(
    () => Array.from(new Set([...warnings, ...(proteinDomainTrack?.warnings ?? [])])),
    [warnings, proteinDomainTrack],
  )

  if (loading) {
    return (
      <div style={cardShellStyle}>
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--ink-4)' }}>Loading gene viewer…</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={cardShellStyle}>
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--ink-4)' }}>
          Gene viewer unavailable{error ? ` — ${error}` : ''}.
        </p>
      </div>
    )
  }

  const variantLabel = data.queriedVariant.hgvsP || data.queriedVariant.hgvsC || 'Variant'
  const totalClinvar = clinvarMarks.length
  const geneWidth = geneTrackWidth(data, totalClinvar)
  const geneTrackW = geneWidth - TRACK_LEFT - TRACK_RIGHT

  return (
    <div style={cardShellStyle}>
      <div style={headerRow}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', minWidth: 0 }}>
          <span style={titleStyle}>{data.gene}</span>
          <span style={subStyle}>{data.transcript}</span>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <StatPill label={data.nativeStrand === 'reverse' ? 'reverse strand' : 'forward strand'} />
          {data.geneLength > 0 && <StatPill label={`${formatInt(data.geneLength)} bp`} />}
          <StatPill label={`${data.exons.length} exons`} />
          {totalClinvar > 0 && <StatPill label={`${totalClinvar} ClinVar`} />}
        </div>
      </div>

      <div style={trackScrollStyle}>
      <svg
        viewBox={`0 0 ${geneWidth} ${VIEW_H}`}
        role="img"
        aria-label={`${data.gene} ${data.transcript} gene track with queried variant and ClinVar markers`}
        style={{ display: 'block', width: geneWidth, maxWidth: 'none', height: 'auto' }}
      >
        <rect x="0" y="0" width={geneWidth} height={VIEW_H} rx="8" fill="var(--bg-soft)" />

        {/* baseline line for introns */}
        <line
          x1={TRACK_LEFT}
          y1={TRACK_Y + EXON_H / 2}
          x2={TRACK_LEFT + geneTrackW}
          y2={TRACK_Y + EXON_H / 2}
          stroke="var(--line-2)"
          strokeWidth="1.5"
        />

        {segments.map((seg) => {
          const x = TRACK_LEFT + (seg.leftPct / 100) * geneTrackW
          const w = Math.max(3, (seg.widthPct / 100) * geneTrackW)
          if (seg.kind === 'intron') {
            return (
              <line
                key={seg.key}
                x1={x}
                y1={TRACK_Y + EXON_H / 2}
                x2={x + w}
                y2={TRACK_Y + EXON_H / 2}
                stroke="var(--ink-5)"
                strokeWidth="1.5"
              />
            )
          }
          return (
            <g key={seg.key}>
              <rect
                x={x}
                y={TRACK_Y}
                width={w}
                height={EXON_H}
                rx="3"
                fill="var(--teal)"
                opacity="0.86"
              />
              {w > 18 && (
                <text
                  x={x + w / 2}
                  y={TRACK_Y + EXON_H / 2 + 4}
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight="700"
                  fill="var(--bg)"
                  fontFamily="var(--mono)"
                >
                  {seg.num}
                </text>
              )}
            </g>
          )
        })}

        {/* ClinVar markers BELOW the track — small triangles, color by class */}
        {clinvarMarks.map((m, i) => {
          const x = TRACK_LEFT + (m.pct / 100) * geneTrackW
          const y = TRACK_Y + EXON_H + 6
          return (
            <polygon
              key={`cv-${i}`}
              points={`${x - 3.5},${y + 7} ${x + 3.5},${y + 7} ${x},${y}`}
              fill={CLASS_COLOR[m.cls] ?? 'var(--cls-na-dot)'}
              opacity="0.85"
            >
              <title>{`${m.label} — ${m.cv}`}</title>
            </polygon>
          )
        })}

        {/* Queried variant marker ABOVE the track — bold lollipop */}
        {variantPct !== null && (
          <g>
            <line
              x1={TRACK_LEFT + (variantPct / 100) * geneTrackW}
              y1={TRACK_Y - 26}
              x2={TRACK_LEFT + (variantPct / 100) * geneTrackW}
              y2={TRACK_Y - 4}
              stroke="var(--ink)"
              strokeWidth="2"
            />
            <circle
              cx={TRACK_LEFT + (variantPct / 100) * geneTrackW}
              cy={TRACK_Y - 30}
              r="6"
              fill="var(--cls-path-dot)"
              stroke="var(--ink)"
              strokeWidth="1.5"
            />
            <text
              x={clamp(
                TRACK_LEFT + (variantPct / 100) * geneTrackW,
                TRACK_LEFT + 50,
                TRACK_LEFT + geneTrackW - 50,
              )}
              y={TRACK_Y - 44}
              textAnchor="middle"
              fontSize="12"
              fontWeight="700"
              fill="var(--ink)"
              fontFamily="var(--mono)"
            >
              {variantLabel}
            </text>
          </g>
        )}

        {/* axis labels */}
        <text
          x={TRACK_LEFT}
          y={VIEW_H - 14}
          fontSize="10.5"
          fill="var(--ink-4)"
          fontWeight="700"
        >
          5′
        </text>
        <text
          x={TRACK_LEFT + geneTrackW}
          y={VIEW_H - 14}
          textAnchor="end"
          fontSize="10.5"
          fill="var(--ink-4)"
          fontWeight="700"
        >
          3′
        </text>
      </svg>
      </div>

      <div style={legendRow}>
        <span style={legendLabel}>ClinVar:</span>
        <LegendDot color={CLASS_COLOR.p} label={`P (${clinvarCounts.p})`} />
        <LegendDot color={CLASS_COLOR.lp} label={`LP (${clinvarCounts.lp})`} />
        <LegendDot color={CLASS_COLOR.vus} label={`VUS (${clinvarCounts.vus})`} />
        <LegendDot color={CLASS_COLOR.lb} label={`LB (${clinvarCounts.lb})`} />
        <LegendDot color={CLASS_COLOR.b} label={`B (${clinvarCounts.b})`} />
      </div>

      <ReportProteinView
        data={data}
        track={renderedProteinTrack}
        alphaHeatmap={alphaHeatmap}
        includeAlphaMissense={includeAlphaMissense}
        onToggleAlphaMissense={setIncludeAlphaMissense}
      />

      <ProvenanceNote warnings={renderedWarnings} />
    </div>
  )
}

interface ProteinFeatureRender {
  start: number
  end: number
  label: string
  short: string
  kind: string
  lane: ProteinLaneId
  description?: string | null
  source?: string | null
  accession?: string | null
}

interface PackedProteinFeature extends ProteinFeatureRender {
  legendKey: string
  row: number
  x: number
  width: number
}

type ProteinLaneId = 'topology' | 'domains' | 'motifs' | 'sites' | 'other'

interface ProteinLaneDef {
  id: ProteinLaneId
  label: string
}

const PROTEIN_W = 920
const PROTEIN_LEFT = 42
const PROTEIN_RIGHT = 34
const PROTEIN_MAX_W = 5600
const PROTEIN_MARKER_Y = 28
const PROTEIN_LANE_TOP = 64
const PROTEIN_LANE_H = 20
const PROTEIN_LANE_ROW_GAP = 5
const PROTEIN_LANE_GAP = 22
const PROTEIN_HEAT_H = 12

const PROTEIN_LANES: ProteinLaneDef[] = [
  { id: 'topology', label: 'Topology' },
  { id: 'domains', label: 'Domains' },
  { id: 'motifs', label: 'Motifs' },
  { id: 'sites', label: 'Sites' },
  { id: 'other', label: 'Other' },
]

function ReportProteinView({
  data,
  track,
  alphaHeatmap,
  includeAlphaMissense,
  onToggleAlphaMissense,
}: {
  data: GeneWindowData
  track: ProteinDomainTrack | null
  alphaHeatmap: ProteinAlphaMissenseHeatmap | null
  includeAlphaMissense: boolean
  onToggleAlphaMissense: (value: boolean) => void
}) {
  const [selectedFeatureKeys, setSelectedFeatureKeys] = useState<Set<string>>(() => new Set())
  const trackFeatures = track?.features ?? []
  const ranges = trackFeatures.length > 0 ? featuresFromTrack(trackFeatures) : featuresFromViewer(data)
  const proteinLength = Math.max(
    1,
    track?.protein_length ??
      alphaHeatmap?.protein_length ??
      data.proteinProduct?.referenceProteinLength ??
      data.proteinLength ??
      1,
  )
  const proteinWidth = proteinCanvasWidth(proteinLength, ranges.length)
  const proteinTrackW = proteinWidth - PROTEIN_LEFT - PROTEIN_RIGHT
  const product = data.proteinProduct
  const queriedAa = clamp(
    data.queriedVariant.codonNumber || Math.ceil(data.queriedVariant.cdsPos / 3) || 1,
    1,
    proteinLength,
  )
  const xFor = (aa: number) =>
    PROTEIN_LEFT + ((clamp(aa, 1, proteinLength) - 1) / Math.max(1, proteinLength - 1)) * proteinTrackW
  const ticks = proteinTicks(proteinLength)
  const sourceLabel = proteinSourceLabel(track, ranges.length > 0)
  const lanes = proteinLanesFor(ranges)
  const { packedFeatures, laneOffsets, laneRowCounts, totalHeight: laneBlockHeight } = packProteinFeatures(
    ranges,
    lanes,
    xFor,
  )
  const laneY = (lane: ProteinLaneId) => laneOffsets.get(lane) ?? PROTEIN_LANE_TOP
  const featureY = (feature: PackedProteinFeature) =>
    laneY(feature.lane) + feature.row * (PROTEIN_LANE_H + PROTEIN_LANE_ROW_GAP)
  const firstLaneY = PROTEIN_LANE_TOP
  const lastLaneBottom = PROTEIN_LANE_TOP + laneBlockHeight
  const proteinHeatY = lastLaneBottom + 18
  const proteinAxisY = proteinHeatY + (includeAlphaMissense ? PROTEIN_HEAT_H + 24 : 12)
  const proteinHeight = proteinAxisY + 28
  const legendItems = featureLegendItems(ranges)
  const toggleFeatureKey = (key: string) => {
    setSelectedFeatureKeys((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }
  const alphaAvailable =
    includeAlphaMissense &&
    alphaHeatmap != null &&
    (alphaHeatmap.status === 'available' || alphaHeatmap.status === 'partial') &&
    alphaHeatmap.residues.length > 0
  const alphaUnavailable = includeAlphaMissense && !alphaAvailable

  return (
    <div style={proteinShellStyle}>
      <div style={proteinHeadStyle}>
        <div style={{ minWidth: 0 }}>
          <span className="eamos-kicker">Protein product &amp; domains</span>
          <div style={proteinTitleStyle}>
            {product?.label ?? (data.queriedVariant.hgvsP || data.queriedVariant.hgvsC)}
          </div>
        </div>
        <div style={proteinControlsStyle}>
          <StatPill label={`${formatInt(proteinLength)} aa`} />
          <StatPill label={`${ranges.length} features`} />
          <label style={toggleLabelStyle}>
            <input
              type="checkbox"
              checked={includeAlphaMissense}
              onChange={(event) => onToggleAlphaMissense(event.target.checked)}
              style={{ accentColor: 'var(--teal)' }}
            />
            AlphaMissense
          </label>
        </div>
      </div>

      <div style={trackScrollStyle}>
        <svg
          viewBox={`0 0 ${proteinWidth} ${proteinHeight}`}
          role="img"
          aria-label={`${data.gene} protein view with domain annotations`}
          style={{ display: 'block', width: proteinWidth, maxWidth: 'none', height: 'auto' }}
        >
          <rect x="0" y="0" width={proteinWidth} height={proteinHeight} rx="8" fill="var(--bg-soft)" />

        {lanes.map((lane) => {
          const y = laneY(lane.id)
          const rowCount = laneRowCounts.get(lane.id) ?? 1
          return (
            <g key={lane.id}>
              <text
                x={PROTEIN_LEFT}
                y={y - 8}
                fontSize="9.5"
                fontWeight="800"
                fill="var(--ink-5)"
              >
                {lane.label}
              </text>
              {Array.from({ length: rowCount }, (_, row) => {
                const rowY = y + row * (PROTEIN_LANE_H + PROTEIN_LANE_ROW_GAP)
                return (
                  <line
                    key={row}
                    x1={PROTEIN_LEFT}
                    y1={rowY + PROTEIN_LANE_H / 2}
                    x2={PROTEIN_LEFT + proteinTrackW}
                    y2={rowY + PROTEIN_LANE_H / 2}
                    stroke="var(--line-2)"
                    strokeWidth="1.5"
                  />
                )
              })}
            </g>
          )
        })}

        {packedFeatures.map((feature, index) => {
          const x = feature.x
          const width = feature.width
          const y = featureY(feature)
          const color = featureColor(feature)
          const label = labelForFeatureWidth(feature, width)
          const pointFeature = feature.start === feature.end || feature.kind === 'site'
          const highlighted = selectedFeatureKeys.has(feature.legendKey)
          const stroke = highlighted ? 'rgba(225, 164, 35, 0.96)' : color.stroke
          const strokeWidth = highlighted ? 2.2 : 0.8
          return (
            <g key={`${feature.kind}-${feature.start}-${feature.end}-${index}`}>
              {pointFeature ? (
                <>
                  <line
                    x1={x}
                    y1={y - 3}
                    x2={x}
                    y2={y + PROTEIN_LANE_H + 3}
                    stroke={stroke}
                    strokeWidth={highlighted ? 2 : 1}
                  />
                  <circle
                    cx={x}
                    cy={y + PROTEIN_LANE_H / 2}
                    r="4.2"
                    fill={color.fill}
                    stroke={stroke}
                    strokeWidth={highlighted ? 2 : 1}
                  />
                </>
              ) : (
                <>
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={PROTEIN_LANE_H}
                    rx="4"
                    fill={color.fill}
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                  />
                  {label && (
                    <text
                      x={x + width / 2}
                      y={y + PROTEIN_LANE_H / 2 + 3.5}
                      textAnchor="middle"
                      fontSize="9.5"
                      fontWeight="800"
                      fill={color.text}
                    >
                      {label}
                    </text>
                  )}
                </>
              )}
              <title>{featureTitle(feature)}</title>
            </g>
          )
        })}

        {alphaAvailable &&
          alphaHeatmap.residues.map((residue, index) => {
            const score = residue.mean_score
            if (score == null) return null
            const next = alphaHeatmap.residues[index + 1]
            const width = Math.max(2, (next ? xFor(next.aa) : xFor(residue.aa + 1)) - xFor(residue.aa))
            return (
              <rect
                key={`am-${residue.aa}`}
                x={xFor(residue.aa)}
                y={proteinHeatY}
                width={width}
                height={PROTEIN_HEAT_H}
                fill={alphaColor(score)}
              >
                <title>{`AlphaMissense mean ${score.toFixed(3)} | aa ${residue.aa} | ${residue.scored_variant_count} substitutions`}</title>
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
          y2={firstLaneY}
          stroke="var(--ink)"
          strokeWidth="1.6"
        />
        <circle
          cx={xFor(queriedAa)}
          cy={PROTEIN_MARKER_Y}
          r="6"
          fill={CLASS_COLOR[data.queriedVariant.classification] ?? 'var(--cls-vus-dot)'}
          stroke="var(--ink)"
          strokeWidth="1.4"
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

        <line
          x1={PROTEIN_LEFT}
          y1={proteinAxisY}
          x2={PROTEIN_LEFT + proteinTrackW}
          y2={proteinAxisY}
          stroke="var(--ink-4)"
          strokeWidth="1"
        />
        {ticks.map((tick) => {
          const x = xFor(tick)
          return (
            <g key={tick}>
              <line x1={x} y1={proteinAxisY} x2={x} y2={proteinAxisY + 5} stroke="var(--ink-4)" />
              <text
                x={x}
                y={proteinAxisY + 18}
                textAnchor={tick === 1 ? 'start' : tick === proteinLength ? 'end' : 'middle'}
                fontSize="10"
                fill="var(--ink-4)"
                fontFamily="var(--mono)"
              >
                {tick}
              </text>
            </g>
          )
        })}
        </svg>
      </div>

      {ranges.length > 0 && (
        <div style={proteinLegendStyle}>
          {lanes
            .filter((lane) => ranges.some((feature) => feature.lane === lane.id))
            .map((lane) => {
              const color = laneColor(lane.id)
              return (
                <span key={lane.id} style={proteinLegendItemStyle}>
                  <span
                    style={{
                      width: 12,
                      height: 7,
                      borderRadius: 3,
                      background: color.fill,
                      border: `0.5px solid ${color.stroke}`,
                      display: 'inline-block',
                    }}
                  />
                  {lane.label}
                </span>
              )
            })}
          <span style={proteinLegendItemStyle}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--ink)', display: 'inline-block' }} />
            Query
          </span>
        </div>
      )}

      <div style={proteinFootStyle}>
        <span>{sourceLabel}</span>
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
          <span>
            AlphaMissense unavailable: {alphaHeatmap?.fail_closed_reason ?? 'not returned'}
          </span>
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
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function featuresFromTrack(features: ProteinDomainTrackFeature[]): ProteinFeatureRender[] {
  return features
    .map((feature) => ({
      start: feature.aa_start,
      end: Math.max(feature.aa_start, feature.aa_end),
      label: feature.label,
      short: feature.short_label ?? shortLabel(feature.label),
      kind: feature.kind,
      lane: normalizeProteinLane(feature.lane, feature.kind),
      description: feature.description,
      source: feature.source,
      accession: feature.accession ?? feature.source_accession,
    }))
    .sort((a, b) => laneRank(a.lane) - laneRank(b.lane) || a.start - b.start || a.end - b.end)
}

function featuresFromViewer(data: GeneWindowData): ProteinFeatureRender[] {
  return [
    ...(data.proteinFeatures.signalPeptide
      ? [
          {
            start: data.proteinFeatures.signalPeptide.aaStart,
            end: data.proteinFeatures.signalPeptide.aaEnd,
            label: 'Signal peptide',
            short: 'SP',
            kind: 'signal_peptide',
            lane: 'topology' as const,
            source: 'viewer protein_features',
          },
        ]
      : []),
    ...data.proteinFeatures.domains.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'domain',
      lane: 'domains' as const,
      source: 'viewer protein_features',
    })),
    ...data.proteinFeatures.transmembrane.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'transmembrane',
      lane: 'topology' as const,
      source: 'viewer protein_features',
    })),
    ...data.proteinFeatures.membraneBinding.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'region',
      lane: 'motifs' as const,
      source: 'viewer protein_features',
    })),
    ...data.proteinFeatures.activeSites.map((feature) => ({
      start: feature.aa,
      end: feature.aa,
      label: feature.label,
      short: feature.residue ? `${feature.residue}${feature.aa}` : `aa ${feature.aa}`,
      kind: 'site',
      lane: 'sites' as const,
      source: 'viewer protein_features',
    })),
    ...data.proteinFeatures.palmitoylation.map((feature) => ({
      start: feature.aa,
      end: feature.aa,
      label: feature.label,
      short: feature.residue ? `${feature.residue}${feature.aa}` : `aa ${feature.aa}`,
      kind: 'site',
      lane: 'sites' as const,
      source: 'viewer protein_features',
    })),
  ].sort((a, b) => laneRank(a.lane) - laneRank(b.lane) || a.start - b.start || a.end - b.end)
}

function shortLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 31)}...` : label
}

function proteinTicks(length: number): number[] {
  return Array.from(
    new Set([1, Math.round(length / 4), Math.round(length / 2), Math.round((length * 3) / 4), length].map((tick) => clamp(tick, 1, length))),
  ).sort((a, b) => a - b)
}

function proteinCanvasWidth(proteinLength: number, featureCount: number): number {
  const lengthWidth = PROTEIN_LEFT + PROTEIN_RIGHT + proteinLength * 0.95
  const densityWidth = PROTEIN_LEFT + PROTEIN_RIGHT + featureCount * 42
  return Math.round(Math.min(PROTEIN_MAX_W, Math.max(PROTEIN_W, lengthWidth, densityWidth)))
}

function packProteinFeatures(
  features: ProteinFeatureRender[],
  lanes: ProteinLaneDef[],
  xFor: (aa: number) => number,
): {
  packedFeatures: PackedProteinFeature[]
  laneOffsets: Map<ProteinLaneId, number>
  laneRowCounts: Map<ProteinLaneId, number>
  totalHeight: number
} {
  const laneFeatures = new Map<ProteinLaneId, PackedProteinFeature[]>()
  const laneRowCounts = new Map<ProteinLaneId, number>()

  lanes.forEach((lane) => {
    const rowEnds: number[] = []
    const packed = features
      .filter((feature) => feature.lane === lane.id)
      .sort((a, b) => a.start - b.start || b.end - a.end)
      .map((feature) => {
        const x = xFor(feature.start)
        const width = Math.max(3, xFor(feature.end) - x)
        const paddedEnd = x + width + 8
        let row = rowEnds.findIndex((end) => x >= end)
        if (row === -1) {
          row = rowEnds.length
          rowEnds.push(paddedEnd)
        } else {
          rowEnds[row] = paddedEnd
        }
        return {
          ...feature,
          legendKey: featureLegendKey(feature),
          row,
          x,
          width,
        }
      })
    laneFeatures.set(lane.id, packed)
    laneRowCounts.set(lane.id, Math.max(1, rowEnds.length))
  })

  const laneOffsets = new Map<ProteinLaneId, number>()
  let cursor = PROTEIN_LANE_TOP
  lanes.forEach((lane) => {
    laneOffsets.set(lane.id, cursor)
    const rows = laneRowCounts.get(lane.id) ?? 1
    cursor += rows * PROTEIN_LANE_H + Math.max(0, rows - 1) * PROTEIN_LANE_ROW_GAP + PROTEIN_LANE_GAP
  })

  return {
    packedFeatures: lanes.flatMap((lane) => laneFeatures.get(lane.id) ?? []),
    laneOffsets,
    laneRowCounts,
    totalHeight: Math.max(PROTEIN_LANE_H, cursor - PROTEIN_LANE_TOP - PROTEIN_LANE_GAP),
  }
}

function proteinLanesFor(features: ProteinFeatureRender[]): ProteinLaneDef[] {
  const present = new Set(features.map((feature) => feature.lane))
  const lanes = PROTEIN_LANES.filter((lane) => present.has(lane.id))
  return lanes.length > 0 ? lanes : PROTEIN_LANES.filter((lane) => lane.id === 'domains')
}

function normalizeProteinLane(lane: string | null | undefined, kind: string): ProteinLaneId {
  if (lane === 'topology' || lane === 'domains' || lane === 'motifs' || lane === 'sites') return lane
  if (kind === 'signal_peptide' || kind === 'transmembrane' || kind === 'topological_domain') return 'topology'
  if (kind === 'motif' || kind === 'repeat' || kind === 'coiled_coil' || kind === 'low_complexity') return 'motifs'
  if (kind === 'site' || kind === 'epitope') return 'sites'
  if (kind === 'domain' || kind === 'family' || kind === 'region') return 'domains'
  return 'other'
}

function laneRank(lane: ProteinLaneId): number {
  const index = PROTEIN_LANES.findIndex((entry) => entry.id === lane)
  return index === -1 ? PROTEIN_LANES.length : index
}

function laneColor(lane: ProteinLaneId): { fill: string; stroke: string; text: string } {
  if (lane === 'topology') {
    return { fill: 'rgba(191, 116, 58, 0.18)', stroke: 'rgba(155, 87, 34, 0.58)', text: 'var(--ink-2)' }
  }
  if (lane === 'motifs') {
    return { fill: 'rgba(136, 104, 190, 0.16)', stroke: 'rgba(111, 82, 164, 0.52)', text: 'var(--ink-2)' }
  }
  if (lane === 'sites') {
    return { fill: 'rgba(216, 179, 82, 0.24)', stroke: 'rgba(172, 132, 34, 0.58)', text: 'var(--ink-2)' }
  }
  if (lane === 'other') {
    return { fill: 'rgba(92, 107, 122, 0.13)', stroke: 'rgba(92, 107, 122, 0.42)', text: 'var(--ink-2)' }
  }
  return { fill: 'var(--teal-tint)', stroke: 'var(--teal-bdr)', text: 'var(--teal-deep)' }
}

function featureColor(feature: ProteinFeatureRender): { fill: string; stroke: string; text: string } {
  if (feature.lane === 'domains') {
    return domainPaletteColor(feature)
  }
  if (feature.kind === 'coiled_coil') {
    return { fill: 'rgba(47, 125, 121, 0.13)', stroke: 'rgba(47, 125, 121, 0.48)', text: 'var(--teal-deep)' }
  }
  if (feature.kind === 'low_complexity' || feature.kind === 'repeat') {
    return { fill: 'rgba(121, 137, 153, 0.14)', stroke: 'rgba(92, 107, 122, 0.4)', text: 'var(--ink-2)' }
  }
  return laneColor(feature.lane)
}

function domainPaletteColor(feature: Pick<ProteinFeatureRender, 'short' | 'label'>): { fill: string; stroke: string; text: string } {
  const palette = [
    ['rgba(44, 123, 182, 0.18)', 'rgba(44, 123, 182, 0.58)', 'rgb(22, 78, 121)'],
    ['rgba(86, 160, 103, 0.18)', 'rgba(72, 137, 87, 0.58)', 'rgb(39, 96, 55)'],
    ['rgba(196, 118, 62, 0.18)', 'rgba(173, 93, 42, 0.58)', 'rgb(123, 66, 29)'],
    ['rgba(129, 102, 181, 0.18)', 'rgba(111, 82, 164, 0.58)', 'rgb(78, 56, 125)'],
    ['rgba(196, 87, 112, 0.16)', 'rgba(174, 66, 93, 0.56)', 'rgb(125, 45, 65)'],
    ['rgba(37, 151, 143, 0.16)', 'rgba(26, 126, 120, 0.56)', 'rgb(20, 92, 88)'],
    ['rgba(184, 143, 50, 0.18)', 'rgba(158, 118, 31, 0.58)', 'rgb(113, 83, 20)'],
    ['rgba(89, 111, 173, 0.17)', 'rgba(70, 91, 151, 0.55)', 'rgb(50, 66, 112)'],
    ['rgba(159, 104, 70, 0.17)', 'rgba(138, 82, 49, 0.55)', 'rgb(96, 58, 37)'],
    ['rgba(90, 138, 156, 0.16)', 'rgba(70, 116, 135, 0.54)', 'rgb(47, 83, 98)'],
  ] as const
  const key = domainPaletteKey(feature)
  const [fill, stroke, text] = palette[hashString(key) % palette.length]
  return { fill, stroke, text }
}

function domainPaletteKey(feature: Pick<ProteinFeatureRender, 'short' | 'label'>): string {
  const short = feature.short.trim().toLowerCase()
  if (short && short.length <= 18 && !short.endsWith('...')) return short
  return feature.label.trim().toLowerCase()
}

function hashString(value: string): number {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

function labelForFeatureWidth(feature: ProteinFeatureRender, width: number): string | null {
  if (feature.start === feature.end || feature.kind === 'site' || width < 28) return null
  const maxChars = Math.max(3, Math.floor(width / 6.4))
  if (feature.short.length <= maxChars) return feature.short
  if (maxChars <= 5) return feature.short.slice(0, maxChars)
  return `${feature.short.slice(0, maxChars - 3)}...`
}

function featureLegendItems(features: ProteinFeatureRender[]): Array<{
  key: string
  short: string
  kindLabel: string
  description: string | null
  coordLabel: string
  count: number
  title: string
  color: { fill: string; stroke: string; text: string }
}> {
  const groups = new Map<
    string,
    {
      short: string
      kindLabel: string
      description: string | null
      features: ProteinFeatureRender[]
    }
  >()

  features.forEach((feature) => {
    const description = feature.description || (feature.label !== feature.short ? feature.label : null)
    const key = featureLegendKey(feature)
    const existing = groups.get(key)
    if (existing) {
      existing.features.push(feature)
      return
    }
    groups.set(key, {
      short: feature.short,
      kindLabel: `${feature.lane} / ${feature.kind}`.replace(/_/g, ' '),
      description,
      features: [feature],
    })
  })

  return Array.from(groups.entries()).map(([key, group]) => {
    const sorted = group.features.sort((a, b) => a.start - b.start || a.end - b.end)
    const min = Math.min(...sorted.map((feature) => feature.start))
    const max = Math.max(...sorted.map((feature) => feature.end))
    const coords = sorted
      .slice(0, 5)
      .map((feature) => `aa ${feature.start}${feature.start === feature.end ? '' : `-${feature.end}`}`)
      .join(', ')
    const overflow = sorted.length > 5 ? `, +${sorted.length - 5} more` : ''
    return {
      key,
      short: group.short,
      kindLabel: group.kindLabel,
      description: group.description,
      coordLabel: sorted.length === 1 ? coords : `${sorted.length}x | aa ${min}-${max}`,
      count: sorted.length,
      title: sorted.map(featureTitle).join('\n') + overflow,
      color: featureColor(sorted[0]),
    }
  })
}

function featureLegendKey(feature: Pick<ProteinFeatureRender, 'lane' | 'kind' | 'short' | 'label' | 'description'>): string {
  const description = feature.description || (feature.label !== feature.short ? feature.label : null)
  return [feature.lane, feature.kind, feature.short, description ?? ''].join('|')
}

function alphaColor(score: number): string {
  if (score < 0.2) return 'var(--cls-ben-dot)'
  if (score < 0.4) return 'var(--cls-lben-dot)'
  if (score < 0.6) return 'var(--cls-vus-dot)'
  if (score < 0.8) return 'var(--cls-lpath-dot)'
  return 'var(--cls-path-dot)'
}

function featureTitle(feature: ProteinFeatureRender): string {
  return [
    feature.label,
    `aa ${feature.start}-${feature.end}`,
    feature.source,
    feature.accession,
  ].filter(Boolean).join(' | ')
}

function proteinSourceLabel(track: ProteinDomainTrack | null, hasFallbackFeatures: boolean): string {
  if (!track) return hasFallbackFeatures ? 'Viewer protein_features' : 'No protein domain features returned'
  if (track.status !== 'available' && track.status !== 'cache_hit') {
    return track.fail_closed_reason ? `Protein domains unavailable: ${track.fail_closed_reason}` : `Protein domains unavailable: ${track.status}`
  }
  const sources = Array.from(new Set(track.features.map((feature) => feature.source).filter(Boolean)))
  const release = track.pfam_release ?? track.uniprot_release ?? track.hmmer_release
  return ['Source-backed', sources.slice(0, 2).join(' + '), release].filter(Boolean).join(' | ')
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v))
}

function StatPill({ label }: { label: string }) {
  return (
    <span
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 999,
        background: 'var(--bg)',
        color: 'var(--ink-3)',
        padding: '3px 9px',
        fontSize: 10.5,
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, display: 'inline-block' }} />
      <span style={{ fontSize: 10.5, color: 'var(--ink-4)', fontWeight: 600 }}>{label}</span>
    </span>
  )
}

const cardShellStyle: React.CSSProperties = {
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg)',
  padding: 14,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const headerRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
  flexWrap: 'wrap',
}

const titleStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 700,
  color: 'var(--ink)',
}

const subStyle: React.CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: 11.5,
  color: 'var(--ink-4)',
}

const trackScrollStyle: React.CSSProperties = {
  width: '100%',
  overflowX: 'auto',
  overflowY: 'hidden',
  borderRadius: 8,
  scrollbarWidth: 'thin',
}

const legendRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  flexWrap: 'wrap',
  fontSize: 10.5,
  color: 'var(--ink-4)',
}

const legendLabel: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  color: 'var(--ink-4)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
}

const proteinShellStyle: React.CSSProperties = {
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg)',
  padding: 12,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const proteinHeadStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
  flexWrap: 'wrap',
}

const proteinTitleStyle: React.CSSProperties = {
  marginTop: 4,
  fontSize: 12.5,
  fontWeight: 700,
  color: 'var(--ink)',
}

const proteinControlsStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: 6,
  flexWrap: 'wrap',
}

const toggleLabelStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  border: '0.5px solid var(--line)',
  borderRadius: 999,
  background: 'var(--bg-soft)',
  color: 'var(--ink-3)',
  padding: '3px 9px',
  fontSize: 10.5,
  fontWeight: 700,
  whiteSpace: 'nowrap',
}

const proteinFootStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexWrap: 'wrap',
  fontSize: 10.5,
  color: 'var(--ink-4)',
}

const proteinLegendStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexWrap: 'wrap',
  fontSize: 10.5,
  color: 'var(--ink-4)',
}

const proteinLegendItemStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 5,
  fontWeight: 700,
}

const featureGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
  gap: 6,
}

function featureChipStyle(selected: boolean, color: { fill: string; stroke: string }): React.CSSProperties {
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
    boxShadow: selected ? `inset 0 0 0 1.5px rgba(225, 164, 35, 0.88), 3px 0 0 ${color.stroke}` : `3px 0 0 ${color.stroke}`,
  }
}

const featureKindStyle: React.CSSProperties = {
  fontSize: 9.5,
  color: 'var(--ink-5)',
  textTransform: 'uppercase',
  letterSpacing: 0,
  fontWeight: 800,
}

const featureLabelStyle: React.CSSProperties = {
  fontSize: 11,
  color: 'var(--ink-2)',
  fontWeight: 700,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
}

const featureDescriptionStyle: React.CSSProperties = {
  fontSize: 10,
  color: 'var(--ink-3)',
  lineHeight: 1.25,
}

const featureCoordStyle: React.CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: 10,
  color: 'var(--ink-4)',
}
