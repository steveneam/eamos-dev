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
const TRACK_W = VIEW_W - TRACK_LEFT - TRACK_RIGHT
const TRACK_Y = 96
const EXON_H = 26
const VIEW_H = 184

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

function warningsForViewer(resp: GeneViewerResponse): string[] {
  const trackWarnings = resp.tracks.protein_features.domain_track?.warnings ?? []
  const alphamissenseWarnings = resp.tracks.alphamissense_heatmap?.warnings ?? []
  return Array.from(new Set([...geneViewerScaffoldWarnings(resp), ...trackWarnings, ...alphamissenseWarnings]))
}

export function ReportGeneViewer({ gene, cdna, transcript, demo = false }: ReportGeneViewerProps) {
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

      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-label={`${data.gene} ${data.transcript} gene track with queried variant and ClinVar markers`}
        style={{ display: 'block', width: '100%', height: 'auto' }}
      >
        <rect x="0" y="0" width={VIEW_W} height={VIEW_H} rx="8" fill="var(--bg-soft)" />

        {/* baseline line for introns */}
        <line
          x1={TRACK_LEFT}
          y1={TRACK_Y + EXON_H / 2}
          x2={TRACK_LEFT + TRACK_W}
          y2={TRACK_Y + EXON_H / 2}
          stroke="var(--line-2)"
          strokeWidth="1.5"
        />

        {segments.map((seg) => {
          const x = TRACK_LEFT + (seg.leftPct / 100) * TRACK_W
          const w = Math.max(3, (seg.widthPct / 100) * TRACK_W)
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
          const x = TRACK_LEFT + (m.pct / 100) * TRACK_W
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
              x1={TRACK_LEFT + (variantPct / 100) * TRACK_W}
              y1={TRACK_Y - 26}
              x2={TRACK_LEFT + (variantPct / 100) * TRACK_W}
              y2={TRACK_Y - 4}
              stroke="var(--ink)"
              strokeWidth="2"
            />
            <circle
              cx={TRACK_LEFT + (variantPct / 100) * TRACK_W}
              cy={TRACK_Y - 30}
              r="6"
              fill="var(--cls-path-dot)"
              stroke="var(--ink)"
              strokeWidth="1.5"
            />
            <text
              x={clamp(
                TRACK_LEFT + (variantPct / 100) * TRACK_W,
                TRACK_LEFT + 50,
                TRACK_LEFT + TRACK_W - 50,
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
          x={TRACK_LEFT + TRACK_W}
          y={VIEW_H - 14}
          textAnchor="end"
          fontSize="10.5"
          fill="var(--ink-4)"
          fontWeight="700"
        >
          3′
        </text>
      </svg>

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
        track={proteinTrack}
        alphaHeatmap={alphaHeatmap}
        includeAlphaMissense={includeAlphaMissense}
        onToggleAlphaMissense={setIncludeAlphaMissense}
      />

      <ProvenanceNote warnings={warnings} />
    </div>
  )
}

interface ProteinFeatureRender {
  start: number
  end: number
  label: string
  short: string
  kind: string
  source?: string | null
  accession?: string | null
}

const PROTEIN_W = 920
const PROTEIN_LEFT = 42
const PROTEIN_RIGHT = 34
const PROTEIN_TRACK_W = PROTEIN_W - PROTEIN_LEFT - PROTEIN_RIGHT
const PROTEIN_MARKER_Y = 28
const PROTEIN_BAR_Y = 78
const PROTEIN_BAR_H = 24
const PROTEIN_HEAT_Y = 112
const PROTEIN_HEAT_H = 12
const PROTEIN_AXIS_Y = 142
const PROTEIN_H = 168

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
  const product = data.proteinProduct
  const queriedAa = clamp(
    data.queriedVariant.codonNumber || Math.ceil(data.queriedVariant.cdsPos / 3) || 1,
    1,
    proteinLength,
  )
  const xFor = (aa: number) =>
    PROTEIN_LEFT + ((clamp(aa, 1, proteinLength) - 1) / Math.max(1, proteinLength - 1)) * PROTEIN_TRACK_W
  const ticks = proteinTicks(proteinLength)
  const sourceLabel = proteinSourceLabel(track, ranges.length > 0)
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
          <StatPill label={`${ranges.length} domains/features`} />
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

      <svg
        viewBox={`0 0 ${PROTEIN_W} ${PROTEIN_H}`}
        role="img"
        aria-label={`${data.gene} protein view with domain annotations`}
        style={{ display: 'block', width: '100%', height: 'auto' }}
      >
        <rect x="0" y="0" width={PROTEIN_W} height={PROTEIN_H} rx="8" fill="var(--bg-soft)" />
        <line
          x1={PROTEIN_LEFT}
          y1={PROTEIN_BAR_Y + PROTEIN_BAR_H / 2}
          x2={PROTEIN_LEFT + PROTEIN_TRACK_W}
          y2={PROTEIN_BAR_Y + PROTEIN_BAR_H / 2}
          stroke="var(--line-2)"
          strokeWidth="2"
        />

        {ranges.map((feature, index) => {
          const x = xFor(feature.start)
          const width = Math.max(3, xFor(feature.end) - x)
          const color = featureColor(feature.kind)
          return (
            <g key={`${feature.kind}-${feature.start}-${feature.end}-${index}`}>
              <rect
                x={x}
                y={PROTEIN_BAR_Y}
                width={width}
                height={PROTEIN_BAR_H}
                rx="4"
                fill={color.fill}
                stroke={color.stroke}
                strokeWidth="0.8"
              />
              {width > 92 && (
                <text
                  x={x + width / 2}
                  y={PROTEIN_BAR_Y + PROTEIN_BAR_H / 2 + 4}
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight="700"
                  fill={color.text}
                >
                  {feature.short}
                </text>
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
                y={PROTEIN_HEAT_Y}
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
            y={PROTEIN_HEAT_Y}
            width={PROTEIN_TRACK_W}
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
          y2={PROTEIN_BAR_Y}
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
          x={clamp(xFor(queriedAa), PROTEIN_LEFT + 58, PROTEIN_LEFT + PROTEIN_TRACK_W - 58)}
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
          y1={PROTEIN_AXIS_Y}
          x2={PROTEIN_LEFT + PROTEIN_TRACK_W}
          y2={PROTEIN_AXIS_Y}
          stroke="var(--ink-4)"
          strokeWidth="1"
        />
        {ticks.map((tick) => {
          const x = xFor(tick)
          return (
            <g key={tick}>
              <line x1={x} y1={PROTEIN_AXIS_Y} x2={x} y2={PROTEIN_AXIS_Y + 5} stroke="var(--ink-4)" />
              <text
                x={x}
                y={PROTEIN_AXIS_Y + 18}
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

      {ranges.length > 0 && (
        <div style={featureGridStyle}>
          {ranges.slice(0, 6).map((feature, index) => (
            <div key={`${feature.label}-${index}`} style={featureChipStyle} title={feature.label}>
              <span style={featureKindStyle}>{feature.kind.replace(/_/g, ' ')}</span>
              <span style={featureLabelStyle}>{feature.short}</span>
              <span style={featureCoordStyle}>aa {feature.start}-{feature.end}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function featuresFromTrack(features: ProteinDomainTrackFeature[]): ProteinFeatureRender[] {
  return features
    .filter((feature) => feature.kind !== 'site')
    .map((feature) => ({
      start: feature.aa_start,
      end: feature.aa_end,
      label: feature.label,
      short: feature.short_label ?? shortLabel(feature.label),
      kind: feature.kind,
      source: feature.source,
      accession: feature.accession ?? feature.source_accession,
    }))
}

function featuresFromViewer(data: GeneWindowData): ProteinFeatureRender[] {
  return [
    ...data.proteinFeatures.domains.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'domain',
      source: 'viewer protein_features',
    })),
    ...data.proteinFeatures.transmembrane.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'transmembrane',
      source: 'viewer protein_features',
    })),
    ...data.proteinFeatures.membraneBinding.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'region',
      source: 'viewer protein_features',
    })),
  ]
}

function shortLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 31)}...` : label
}

function proteinTicks(length: number): number[] {
  return Array.from(
    new Set([1, Math.round(length / 4), Math.round(length / 2), Math.round((length * 3) / 4), length].map((tick) => clamp(tick, 1, length))),
  ).sort((a, b) => a - b)
}

function featureColor(kind: string): { fill: string; stroke: string; text: string } {
  if (kind === 'transmembrane' || kind === 'topological_domain') {
    return { fill: 'rgba(170, 92, 44, 0.18)', stroke: 'rgba(170, 92, 44, 0.55)', text: 'var(--ink-2)' }
  }
  if (kind === 'signal_peptide' || kind === 'motif' || kind === 'repeat') {
    return { fill: 'rgba(136, 104, 190, 0.16)', stroke: 'rgba(136, 104, 190, 0.5)', text: 'var(--ink-2)' }
  }
  return { fill: 'var(--teal-tint)', stroke: 'var(--teal-bdr)', text: 'var(--teal-deep)' }
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

const featureGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
  gap: 6,
}

const featureChipStyle: React.CSSProperties = {
  border: '0.5px solid var(--line)',
  borderRadius: 6,
  background: 'var(--bg-soft)',
  padding: '7px 8px',
  display: 'grid',
  gap: 2,
  minWidth: 0,
}

const featureKindStyle: React.CSSProperties = {
  fontSize: 9.5,
  color: 'var(--ink-5)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
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

const featureCoordStyle: React.CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: 10,
  color: 'var(--ink-4)',
}
