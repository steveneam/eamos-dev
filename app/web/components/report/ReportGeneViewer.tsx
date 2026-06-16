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
  score?: number | null
  eValue?: number | null
  architecturePriority?: number
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
const PROTEIN_LANE_H = 34
const PROTEIN_LANE_GAP = 24
const PROTEIN_HEAT_H = 12
// Cap the AlphaMissense band at a bounded column count. A 5,200-aa protein has
// ~5,200 scored residues; one rect+title per residue is ~10k DOM nodes in one
// SVG. Beyond this budget we aggregate residues into mean-score bins (the band
// is horizontally scrolled, so sub-pixel residues are not separable anyway).
const HEAT_MAX_BINS = 800

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
  const [visibleFeatureLanes, setVisibleFeatureLanes] = useState<Set<ProteinLaneId>>(
    () => new Set(['topology', 'domains', 'motifs']),
  )
  const [showProteinScale, setShowProteinScale] = useState(true)
  const trackFeatures = track?.features ?? []
  const rawRanges = trackFeatures.length > 0 ? featuresFromTrack(trackFeatures) : featuresFromViewer(data)
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
  const xFor = (aa: number) =>
    PROTEIN_LEFT + ((clamp(aa, 1, proteinLength) - 1) / Math.max(1, proteinLength - 1)) * proteinTrackW
  const scaleTicks = proteinScaleTicks(proteinLength)
  const sourceLabel = proteinSourceLabel(track, ranges.length > 0)
  const lanes = proteinLanesFor(architectureRanges)
  const { packedFeatures, laneOffsets, laneRowCounts, totalHeight: laneBlockHeight } = packProteinFeatures(
    ranges,
    lanes,
    xFor,
  )
  const laneY = (lane: ProteinLaneId) => laneOffsets.get(lane) ?? PROTEIN_LANE_TOP
  const featureY = (feature: PackedProteinFeature) =>
    laneY(feature.lane)
  const firstLaneY = PROTEIN_LANE_TOP
  const lastLaneBottom = PROTEIN_LANE_TOP + laneBlockHeight
  // Reserve optional-track space so toggles alter visibility without resizing the figure.
  const proteinHeatY = lastLaneBottom + 18
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
      if (next.has(lane)) {
        next.delete(lane)
      } else {
        next.add(lane)
      }
      return next
    })
  }
  const alphaAvailable =
    includeAlphaMissense &&
    alphaHeatmap != null &&
    (alphaHeatmap.status === 'available' || alphaHeatmap.status === 'partial') &&
    alphaHeatmap.residues.length > 0
  const alphaUnavailable = includeAlphaMissense && !alphaAvailable
  // Aggregate the scored residues into at most HEAT_MAX_BINS mean-score bins so
  // the heatmap stays a bounded number of SVG nodes regardless of protein
  // length. groupSize === 1 (proteins ≤ HEAT_MAX_BINS aa) is the unchanged
  // per-residue band.
  const alphaBins = useMemo(() => {
    const residues = alphaHeatmap?.residues ?? []
    if (residues.length === 0) return []
    const groupSize = Math.max(1, Math.ceil(residues.length / HEAT_MAX_BINS))
    const bins: { aaStart: number; aaEnd: number; score: number; variants: number }[] = []
    for (let i = 0; i < residues.length; i += groupSize) {
      const end = Math.min(i + groupSize, residues.length)
      let sum = 0
      let scored = 0
      let variants = 0
      for (let j = i; j < end; j += 1) {
        const s = residues[j].mean_score
        if (s != null) {
          sum += s
          scored += 1
        }
        variants += residues[j].scored_variant_count ?? 0
      }
      if (scored === 0) continue
      bins.push({ aaStart: residues[i].aa, aaEnd: residues[end - 1].aa, score: sum / scored, variants })
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
          {rawRanges.length > 0 && <StatPill label={`${rawRanges.length} source hits`} />}
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
              <path
                d="M-2 8 L8 -2 M2 10 L10 2"
                stroke="rgba(155, 87, 34, 0.46)"
                strokeWidth="1"
              />
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
                Protein
              </text>
              {Array.from({ length: rowCount }, (_, row) => {
                const rowY = y + row * PROTEIN_LANE_H
                return (
                  <rect
                    key={row}
                    x={PROTEIN_LEFT}
                    y={rowY}
                    width={proteinTrackW}
                    height={PROTEIN_LANE_H}
                    rx="2"
                    fill="var(--bg)"
                    stroke="var(--ink)"
                    strokeWidth="1.35"
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
          const pointFeature = isPointProteinFeature(feature)
          const patternId = proteinFeaturePatternId(feature)
          const highlighted = selectedFeatureKeys.has(feature.legendKey)
          const stroke = highlighted ? 'rgba(225, 164, 35, 0.96)' : 'var(--ink)'
          const strokeWidth = highlighted ? 3 : 0.85
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
                  {patternId && (
                    <circle
                      cx={x}
                      cy={y + PROTEIN_LANE_H / 2}
                      r="4.2"
                      fill={`url(#${patternId})`}
                      pointerEvents="none"
                    />
                  )}
                </>
              ) : (
                <>
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={PROTEIN_LANE_H}
                    rx="2"
                    fill={color.fill}
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                  />
                  {patternId && (
                    <rect
                      x={x}
                      y={y}
                      width={width}
                      height={PROTEIN_LANE_H}
                      rx="2"
                      fill={`url(#${patternId})`}
                      pointerEvents="none"
                    />
                  )}
                  {label && (
                    <text
                      x={x + width / 2}
                      y={y + PROTEIN_LANE_H / 2 + 3.8}
                      textAnchor="middle"
                      fontSize="10.5"
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
            .filter((lane) => ranges.length > 0 && lane.id === 'domains')
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
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--ink)', display: 'inline-block' }} />
            Query
          </span>
        </div>
      )}

      <div style={proteinFootStyle}>
        <span>{sourceLabel}</span>
        {summarizedFeatureCount > 0 && (
          <span>{`${summarizedFeatureCount} overlapping, alternate, or weak source hit${summarizedFeatureCount === 1 ? '' : 's'} summarized outside the primary architecture figure.`}</span>
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
              {selectedFeatureKeys.has(item.key) && item.ranges.length > 1 && (
                <span style={featureRangeListStyle}>
                  {item.ranges.map((range, index) => (
                    <span key={`${item.key}-${range.start}-${range.end}-${index}`} style={featureRangePillStyle}>
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
      score: feature.score,
      eValue: feature.e_value,
    }))
    .map(canonicalProteinFeature)
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
            architecturePriority: 88,
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
      architecturePriority: 90,
    })).map(canonicalProteinFeature),
    ...data.proteinFeatures.transmembrane.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'transmembrane',
      lane: 'topology' as const,
      source: 'viewer protein_features',
      architecturePriority: 88,
    })),
    ...data.proteinFeatures.membraneBinding.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'region',
      lane: 'motifs' as const,
      source: 'viewer protein_features',
      architecturePriority: 82,
    })),
    ...data.proteinFeatures.activeSites.map((feature) => ({
      start: feature.aa,
      end: feature.aa,
      label: feature.label,
      short: feature.residue ? `${feature.residue}${feature.aa}` : `aa ${feature.aa}`,
      kind: 'site',
      lane: 'sites' as const,
      source: 'viewer protein_features',
      architecturePriority: 75,
    })),
    ...data.proteinFeatures.palmitoylation.map((feature) => ({
      start: feature.aa,
      end: feature.aa,
      label: feature.label,
      short: feature.residue ? `${feature.residue}${feature.aa}` : `aa ${feature.aa}`,
      kind: 'site',
      lane: 'sites' as const,
      source: 'viewer protein_features',
      architecturePriority: 75,
    })),
  ].map(canonicalProteinFeature)
    .sort((a, b) => laneRank(a.lane) - laneRank(b.lane) || a.start - b.start || a.end - b.end)
}

function shortLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 31)}...` : label
}

interface ProteinScaleTick {
  aa: number
  major: boolean
  terminal: boolean
}

function proteinScaleTicks(length: number): ProteinScaleTick[] {
  const clampedLength = Math.max(1, Math.round(length))
  const ticks = new Map<number, ProteinScaleTick>()
  const setTick = (aa: number, major: boolean, terminal = false) => {
    const clampedAa = clamp(Math.round(aa), 1, clampedLength)
    const existing = ticks.get(clampedAa)
    ticks.set(clampedAa, {
      aa: clampedAa,
      major: major || existing?.major === true,
      terminal: terminal || existing?.terminal === true,
    })
  }

  setTick(1, true)
  for (let aa = 100; aa < clampedLength; aa += 100) {
    setTick(aa, aa % 200 === 0)
  }
  setTick(clampedLength, true, true)

  return Array.from(ticks.values()).sort((a, b) => a.aa - b.aa)
}

function proteinCanvasWidth(proteinLength: number, featureCount: number): number {
  const lengthWidth = PROTEIN_LEFT + PROTEIN_RIGHT + proteinLength * 0.95
  const densityWidth = PROTEIN_LEFT + PROTEIN_RIGHT + featureCount * 42
  return Math.round(Math.min(PROTEIN_MAX_W, Math.max(PROTEIN_W, lengthWidth, densityWidth)))
}

function proteinArchitectureFeatures(features: ProteinFeatureRender[]): ProteinFeatureRender[] {
  const selectedByLane = new Map<ProteinLaneId, ProteinFeatureRender[]>()

  PROTEIN_LANES.forEach((lane) => {
    const selected: ProteinFeatureRender[] = []
    const laneFeatures = features.filter((feature) => feature.lane === lane.id)
    const hasCanonicalInLane = laneFeatures.some((feature) => architecturePriority(feature) >= 70)
    const candidates = features
      .filter((feature) => feature.lane === lane.id)
      .filter((feature) => isPrimaryArchitectureFeature(feature, hasCanonicalInLane))
      .sort((a, b) => {
        const priorityDelta = architecturePriority(b) - architecturePriority(a)
        if (priorityDelta !== 0) return priorityDelta
        const confidenceDelta = featureConfidence(b) - featureConfidence(a)
        if (confidenceDelta !== 0) return confidenceDelta
        const lengthDelta = featureLength(b) - featureLength(a)
        if (lengthDelta !== 0) return lengthDelta
        return a.start - b.start
      })

    candidates.forEach((candidate) => {
      const overlapsSelected = selected.some((kept) => significantOverlap(candidate, kept))
      if (!overlapsSelected) selected.push(candidate)
    })

    selectedByLane.set(
      lane.id,
      selected.sort((a, b) => a.start - b.start || a.end - b.end),
    )
  })

  return PROTEIN_LANES.flatMap((lane) => selectedByLane.get(lane.id) ?? [])
}

function isPrimaryArchitectureFeature(feature: ProteinFeatureRender, hasCanonicalInLane: boolean): boolean {
  if (feature.kind === 'topological_domain') return false
  if (feature.lane !== 'domains') return true
  if (architecturePriority(feature) >= 70) return true
  if (hasCanonicalInLane) return false
  const source = feature.source?.toLowerCase() ?? ''
  if (!source.includes('hmmer')) return true
  return (feature.score ?? 0) >= 45 && (feature.eValue ?? Number.POSITIVE_INFINITY) <= 1e-8
}

function canonicalProteinFeature(feature: ProteinFeatureRender): ProteinFeatureRender {
  const text = `${feature.short} ${feature.label} ${feature.description ?? ''}`.toLowerCase()
  const withCanonical = (
    short: string,
    label: string,
    description: string,
    architecturePriority: number,
    lane: ProteinLaneId = feature.lane,
  ): ProteinFeatureRender => ({
    ...feature,
    short,
    label,
    description,
    lane,
    architecturePriority,
  })

  if (/(fibronectin|fn3|fn\(iii\)|fn-?iii|fn iii)/.test(text)) {
    return withCanonical('FN3', 'Fibronectin type III domain', 'Fibronectin type III domain', 96)
  }
  if (/(laminin\/attractin egf|laminin egf|laminegf|lamegf|laed)/.test(text)) {
    return withCanonical('LamEGF', 'Laminin EGF-like domain', 'Laminin EGF-like domain', 98)
  }
  if (/(laminin g|lamg)/.test(text)) {
    return withCanonical('LamG', 'Laminin G-like domain', 'Laminin G-like domain', 97)
  }
  if (/(laminin n-terminal|laminin n terminal|lamnt)/.test(text)) {
    return withCanonical('LamNT', 'Laminin N-terminal domain', 'Laminin N-terminal domain', 97)
  }
  if (/(dynamin family|dynamin-type g|dynamin.*g domain)/.test(text)) {
    return withCanonical('G domain', 'Dynamin G domain', 'Dynamin GTPase domain', 98)
  }
  if (/(dynamin central|middle\/stalk|middle domain|stalk domain)/.test(text)) {
    return withCanonical('Stalk', 'Dynamin stalk domain', 'Dynamin middle/stalk domain', 96)
  }
  if (/(gtpase effector|ged)/.test(text)) {
    return withCanonical('GED', 'GTPase effector domain', 'Dynamin GTPase effector domain', 97)
  }
  if (/(pleckstrin|ph domain)/.test(text)) {
    return withCanonical('PH', 'PH domain', 'Pleckstrin homology domain', 97)
  }
  if (/(proline-rich|prd)/.test(text)) {
    return withCanonical('PRD', 'Proline-rich domain', 'Proline-rich domain', 92)
  }
  if (/(fz domain|frizzled.*cysteine|wnt-binding)/.test(text)) {
    return withCanonical('CRD', 'Frizzled cysteine-rich domain', 'WNT-binding cysteine-rich domain', 97)
  }
  if (/(frizzled\/smoothened|frizzled.*membrane)/.test(text)) {
    return withCanonical('7TM', 'Frizzled/Smoothened membrane region', 'Seven-transmembrane receptor region', 94)
  }
  if (/pdz/.test(text)) {
    return withCanonical('PDZ', 'PDZ-binding motif', 'PDZ-binding motif', 90)
  }
  if (feature.kind === 'transmembrane') {
    return { ...feature, short: feature.short.replace(/^helical;\s*/i, 'TM'), architecturePriority: 88 }
  }
  if (feature.kind === 'signal_peptide') {
    return withCanonical('SP', 'Signal peptide', 'Signal peptide', 88)
  }
  if (feature.kind === 'site') {
    return { ...feature, architecturePriority: 70 }
  }
  return { ...feature, architecturePriority: feature.architecturePriority ?? 50 }
}

function architecturePriority(feature: ProteinFeatureRender): number {
  return feature.architecturePriority ?? 50
}

function featureConfidence(feature: ProteinFeatureRender): number {
  const score = feature.score ?? 0
  const eValue = feature.eValue
  const eValueScore =
    eValue == null ? 0 : eValue <= 0 ? 60 : Math.max(-12, Math.min(60, -Math.log10(eValue)))
  return eValueScore * 10 + score
}

function featureLength(feature: ProteinFeatureRender): number {
  return Math.max(1, feature.end - feature.start + 1)
}

function significantOverlap(a: ProteinFeatureRender, b: ProteinFeatureRender): boolean {
  const overlap = Math.min(a.end, b.end) - Math.max(a.start, b.start) + 1
  if (overlap <= 0) return false
  const smaller = Math.min(featureLength(a), featureLength(b))
  return overlap / smaller >= 0.45
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
    const rowFeatures =
      lanes.length === 1
        ? features
        : features.filter((feature) => feature.lane === lane.id)
    const packed = rowFeatures
      .sort((a, b) => a.start - b.start || b.end - a.end)
      .map((feature) => {
        const x = xFor(feature.start)
        const width = Math.max(3, xFor(feature.end) - x)
        return {
          ...feature,
          legendKey: featureLegendKey(feature),
          row: 0,
          x,
          width,
        }
      })
    laneFeatures.set(lane.id, packed)
    laneRowCounts.set(lane.id, 1)
  })

  const laneOffsets = new Map<ProteinLaneId, number>()
  let cursor = PROTEIN_LANE_TOP
  lanes.forEach((lane) => {
    laneOffsets.set(lane.id, cursor)
    const rows = laneRowCounts.get(lane.id) ?? 1
    cursor += rows * PROTEIN_LANE_H + PROTEIN_LANE_GAP
  })

  return {
    packedFeatures: lanes.flatMap((lane) => laneFeatures.get(lane.id) ?? []),
    laneOffsets,
    laneRowCounts,
    totalHeight: Math.max(PROTEIN_LANE_H, cursor - PROTEIN_LANE_TOP - PROTEIN_LANE_GAP),
  }
}

function proteinLanesFor(features: ProteinFeatureRender[]): ProteinLaneDef[] {
  return features.length > 0 ? [{ id: 'domains', label: 'Architecture' }] : []
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
  if (isPointProteinFeature(feature) || width < 28) return null
  const maxChars = Math.max(3, Math.floor(width / 6.4))
  if (feature.short.length <= maxChars) return feature.short
  if (maxChars <= 5) return feature.short.slice(0, maxChars)
  return `${feature.short.slice(0, maxChars - 3)}...`
}

function isPointProteinFeature(feature: ProteinFeatureRender): boolean {
  return feature.start === feature.end || feature.kind === 'site' || (feature.kind === 'motif' && featureLength(feature) <= 5)
}

function proteinFeaturePatternId(feature: Pick<ProteinFeatureRender, 'lane'>): string | null {
  if (feature.lane === 'topology') return 'protein-pattern-topology'
  if (feature.lane === 'motifs') return 'protein-pattern-motifs'
  if (feature.lane === 'sites') return 'protein-pattern-sites'
  if (feature.lane === 'other') return 'protein-pattern-other'
  return null
}

function categorySwatchStyle(
  lane: ProteinLaneId,
  color: { fill: string; stroke: string; text: string },
): React.CSSProperties {
  return {
    width: 13,
    height: 8,
    borderRadius: 2,
    border: `0.5px solid ${color.stroke}`,
    display: 'inline-block',
    flex: '0 0 auto',
    ...categorySwatchBackgroundStyle(lane, color),
  }
}

function categorySwatchBackgroundStyle(
  lane: ProteinLaneId,
  color: { fill: string; stroke: string; text: string },
): React.CSSProperties {
  if (lane === 'domains') {
    return {
      background:
        'linear-gradient(90deg, rgba(44, 123, 182, 0.28) 0 20%, rgba(86, 160, 103, 0.28) 20% 40%, rgba(196, 118, 62, 0.28) 40% 60%, rgba(129, 102, 181, 0.28) 60% 80%, rgba(196, 87, 112, 0.24) 80% 100%)',
    }
  }
  if (lane === 'topology') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `repeating-linear-gradient(135deg, transparent 0 4px, ${color.stroke} 4px 5px, transparent 5px 9px)`,
    }
  }
  if (lane === 'motifs') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `repeating-linear-gradient(90deg, transparent 0 4px, ${color.stroke} 4px 5px, transparent 5px 8px)`,
    }
  }
  if (lane === 'sites') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `radial-gradient(circle at 2px 2px, ${color.stroke} 1.1px, transparent 1.4px)`,
      backgroundSize: '6px 6px',
    }
  }
  if (lane === 'other') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `repeating-linear-gradient(0deg, transparent 0 4px, ${color.stroke} 4px 5px, transparent 5px 8px)`,
    }
  }
  return { background: color.fill }
}

function featureCategoryLegendItems(features: ProteinFeatureRender[]): Array<{
  lane: ProteinLaneId
  label: string
  color: { fill: string; stroke: string; text: string }
}> {
  const categories: Array<{ lane: ProteinLaneId; label: string }> = [
    { lane: 'topology', label: 'Topology' },
    { lane: 'domains', label: 'Domains / regions' },
    { lane: 'motifs', label: 'Motifs' },
    { lane: 'sites', label: 'Sites' },
  ]
  return categories
    .filter((category) => features.some((feature) => feature.lane === category.lane))
    .map((category) => ({ lane: category.lane, label: category.label, color: laneColor(category.lane) }))
}

function featureLegendItems(features: ProteinFeatureRender[]): Array<{
  key: string
  short: string
  kindLabel: string
  description: string | null
  coordLabel: string
  ranges: Array<{ start: number; end: number }>
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
      kindLabel: `architecture / ${feature.kind}`.replace(/_/g, ' '),
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
      ranges: sorted.map((feature) => ({ start: feature.start, end: feature.end })),
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
  if (!track) return hasFallbackFeatures ? 'Viewer protein_features' : 'No protein architecture features returned'
  if (track.status !== 'available' && track.status !== 'cache_hit' && track.status !== 'partial') {
    return track.fail_closed_reason ? `Protein architecture unavailable: ${track.fail_closed_reason}` : `Protein architecture unavailable: ${track.status}`
  }
  const sources = Array.from(new Set(track.features.map((feature) => feature.source).filter(Boolean)))
  const release = track.pfam_release ?? track.uniprot_release ?? track.hmmer_release
  const status = track.status === 'partial' ? 'Source-backed partial' : 'Source-backed'
  return [status, sources.slice(0, 2).join(' + '), release].filter(Boolean).join(' | ')
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

const featureToggleRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  flexWrap: 'wrap',
}

function categoryToggleStyle(
  active: boolean,
  color: { fill: string; stroke: string; text: string },
): React.CSSProperties {
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

const featureRangeListStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 4,
  paddingTop: 4,
}

const featureRangePillStyle: React.CSSProperties = {
  border: '0.5px solid rgba(225, 164, 35, 0.44)',
  borderRadius: 999,
  background: 'rgba(255, 247, 218, 0.74)',
  color: 'rgb(104, 71, 18)',
  fontFamily: 'var(--mono)',
  fontSize: 9.5,
  fontWeight: 700,
  padding: '2px 5px',
}
