'use client'

import { useMemo, useState, type KeyboardEvent } from 'react'
import { classLabel, clinClassFromText, type ClinClass, type GeneWindowData } from '@/lib/workbench/gene-window'
import { ProvenanceNote } from '@/components/report/ProvenanceNote'
import { ReportProteinView } from './gene-viewer/ReportProteinView'
import {
  CLASS_COLOR,
  SvgVariantMarker,
  clamp,
  clinvarMarkerKind,
  formatInt,
  queriedVariantMarkerKind,
  StatPill,
  toggleLabelStyle,
  trackScrollStyle,
  variantMarkerKindLabel,
  type GeneClinvarMarkerKind,
} from './gene-viewer/geneViewerPresentation'
import {
  useReportGeneViewer,
  type ReportGeneViewerControllerInput,
} from './gene-viewer/useReportGeneViewer'

type ReportGeneViewerProps = ReportGeneViewerControllerInput

// Slice B build 1 — read-only "report mode" genomic track for §4.
//
// Replaces the redundant gene-snapshot SVG + expandable transcript figures
// inside the old GeneContextSnapshotSection. The report lookup may already
// carry a source-backed gene_context_snapshot, so first paint uses that seed and
// only fetches /api/v1/viewer when an unseeded or expanded track needs it. The
// shared gene-viewer adapter still owns the canonical `GeneWindowData` shape.
// The Workbench's full SequenceViewerV2 (edit hub,
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

const VIEW_W = 920
const TRACK_LEFT = 36
const TRACK_RIGHT = 28
const TRACK_Y = 96
const EXON_H = 26
const UTR_H = 16
const GENE_SCALE_Y = 156
const VIEW_H = 218
const TRACK_MAX_W = 4200

interface OverviewSeg {
  key: string
  kind: 'utr5' | 'exon' | 'intron' | 'utr3'
  num: number
  leftPct: number
  widthPct: number
  bp: number
  /** CDS-coordinate start of the segment (exons only) for variant projection. */
  cdsStart?: number
  cdsEnd?: number
  transcriptStart: number
  transcriptEnd: number
}

function buildSegments(data: GeneWindowData): OverviewSeg[] {
  const raw: Array<Omit<OverviewSeg, 'leftPct' | 'widthPct'> & { units: number }> = []
  const minExon = 14
  const minUtr = 18
  const maxIntron = 60
  let transcriptCursor = 1

  if (data.utr5Length > 0) {
    raw.push({
      key: 'utr5',
      kind: 'utr5',
      num: 5,
      bp: data.utr5Length,
      transcriptStart: transcriptCursor,
      transcriptEnd: transcriptCursor + data.utr5Length - 1,
      units: Math.max(minUtr, Math.sqrt(data.utr5Length) * 2),
    })
    transcriptCursor += data.utr5Length
  }

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
      transcriptStart: transcriptCursor,
      transcriptEnd: transcriptCursor + bp - 1,
      units: Math.max(minExon, Math.sqrt(bp) * 2.4),
    })
    transcriptCursor += bp
    const intron = data.introns[i]
    if (intron) {
      raw.push({
        key: `i-${intron.num}`,
        kind: 'intron',
        num: intron.num,
        bp: intron.lenBp,
        transcriptStart: transcriptCursor,
        transcriptEnd: transcriptCursor + intron.lenBp - 1,
        units: Math.min(maxIntron, Math.max(10, Math.log10(intron.lenBp + 1) * 14)),
      })
      transcriptCursor += intron.lenBp
    }
  })

  if (data.utr3Length > 0) {
    raw.push({
      key: 'utr3',
      kind: 'utr3',
      num: 3,
      bp: data.utr3Length,
      transcriptStart: transcriptCursor,
      transcriptEnd: transcriptCursor + data.utr3Length - 1,
      units: Math.max(minUtr, Math.sqrt(data.utr3Length) * 2),
    })
  }

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
      transcriptStart: r.transcriptStart,
      transcriptEnd: r.transcriptEnd,
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

function segmentKindLabel(seg: OverviewSeg): string {
  if (seg.kind === 'utr5') return "5' UTR"
  if (seg.kind === 'utr3') return "3' UTR"
  if (seg.kind === 'intron') return `Intron ${seg.num}`
  return `Exon ${seg.num}`
}

function segmentTitle(seg: OverviewSeg): string {
  if (seg.kind === 'exon') {
    return `${segmentKindLabel(seg)} | ${formatInt(seg.bp)} bp CDS | c.${seg.cdsStart}-${seg.cdsEnd} | transcript bp ${formatInt(seg.transcriptStart)}-${formatInt(seg.transcriptEnd)}`
  }
  if (seg.kind === 'intron') {
    return `${segmentKindLabel(seg)} | ${formatInt(seg.bp)} bp | transcript bp ${formatInt(seg.transcriptStart)}-${formatInt(seg.transcriptEnd)}`
  }
  return `${segmentKindLabel(seg)} | ${formatInt(seg.bp)} bp | transcript bp ${formatInt(seg.transcriptStart)}-${formatInt(seg.transcriptEnd)}`
}

interface GeneScaleTick {
  bp: number
  major: boolean
  terminal: boolean
}

function niceStep(value: number): number {
  const exponent = Math.floor(Math.log10(Math.max(1, value)))
  const magnitude = 10 ** exponent
  const normalized = value / magnitude
  if (normalized <= 1) return magnitude
  if (normalized <= 2) return 2 * magnitude
  if (normalized <= 5) return 5 * magnitude
  return 10 * magnitude
}

function geneScaleTicks(length: number): GeneScaleTick[] {
  const clampedLength = Math.max(1, Math.round(length))
  const majorStep = niceStep(clampedLength / 4)
  const minorStep = Math.max(1, Math.round(majorStep / 5))
  const ticks = new Map<number, GeneScaleTick>()
  const setTick = (bp: number, major: boolean, terminal = false) => {
    const clampedBp = clamp(Math.round(bp), 1, clampedLength)
    const existing = ticks.get(clampedBp)
    ticks.set(clampedBp, {
      bp: clampedBp,
      major: major || existing?.major === true,
      terminal: terminal || existing?.terminal === true,
    })
  }

  setTick(1, true)
  for (let bp = minorStep; bp < clampedLength; bp += minorStep) {
    setTick(bp, bp % majorStep === 0)
  }
  setTick(clampedLength, true, true)

  return Array.from(ticks.values()).sort((a, b) => a.bp - b.bp)
}

function geneTrackWidth(data: GeneWindowData, totalClinvar: number): number {
  const exonUnits = data.exons.length * 34
  const intronUnits = data.introns.length * 10
  const markerUnits = Math.min(900, totalClinvar * 3)
  return Math.round(Math.min(TRACK_MAX_W, Math.max(VIEW_W, TRACK_LEFT + TRACK_RIGHT + exonUnits + intronUnits + markerUnits)))
}

export function ReportGeneViewer({
  gene,
  cdna,
  transcript,
  initialData = null,
  geneContextSnapshot = null,
  proteinDomainTrack = null,
  markerClassification = null,
  demo = false,
}: ReportGeneViewerProps) {
  const {
    data,
    proteinTrack,
    alphaHeatmap,
    includeAlphaMissense,
    setIncludeAlphaMissense,
    warnings,
    error,
    loading,
  } = useReportGeneViewer({
    gene,
    cdna,
    transcript,
    initialData,
    geneContextSnapshot,
    proteinDomainTrack,
    markerClassification,
    demo,
  })
  const [showGeneScale, setShowGeneScale] = useState(true)
  const [selectedGeneFeatureKey, setSelectedGeneFeatureKey] = useState<string | null>(null)

  const segments = useMemo(() => (data ? buildSegments(data) : []), [data])
  const variantPct = useMemo(() => {
    if (!data || segments.length === 0) return null
    return projectCdsToPct(data.queriedVariant.cdsPos, segments)
  }, [data, segments])
  const queriedMarkerKind = data ? queriedVariantMarkerKind(data.queriedVariant) : 'missense'
  const queriedMarkerClassification = data
    ? (clinClassFromText(markerClassification) ?? data.queriedVariant.classification)
    : 'vus'
  const queriedMarkerFill = data
    ? (CLASS_COLOR[queriedMarkerClassification] ?? 'var(--cls-vus-dot)')
    : 'var(--cls-vus-dot)'

  // ClinVar variants live on CDS coords (or are intronic — skip those without
  // numeric cdsPos). Cluster by class for the legend.
  const clinvarMarks = useMemo(() => {
    if (!data) return []
    return data.clinvar
      .filter((v) => typeof v.cdsPos === 'number' && !v.queried)
      .map((v) => {
        const pct = projectCdsToPct(v.cdsPos as number, segments)
        if (pct == null) return null
        return { pct, cls: v.cls, label: v.hgvsC || v.hgvsP, cv: v.cv, kind: clinvarMarkerKind(v) }
      })
      .filter((m): m is NonNullable<typeof m> => m != null)
  }, [data, segments])

  const clinvarCounts = useMemo(() => {
    const counts: Record<string, number> = { p: 0, lp: 0, vus: 0, lb: 0, b: 0 }
    for (const m of clinvarMarks) counts[m.cls] = (counts[m.cls] ?? 0) + 1
    return counts
  }, [clinvarMarks])
  const selectedGeneFeature = useMemo(
    () => segments.find((seg) => seg.key === selectedGeneFeatureKey) ?? null,
    [segments, selectedGeneFeatureKey],
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

  const transcriptVariantLabel = data.queriedVariant.hgvsC || 'Variant'
  const totalClinvar = clinvarMarks.length
  const architectureIsTranscript = data.architectureScope === 'transcript'
  const exonPillLabel =
    data.totalExons > data.exons.length
      ? architectureIsTranscript
        ? `${formatInt(data.exons.length)} coding / ${formatInt(data.totalExons)} exons`
        : `${formatInt(data.exons.length)} shown / ${formatInt(data.totalExons)} exons`
      : `${formatInt(data.totalExons || data.exons.length)} exons`
  const geneWidth = geneTrackWidth(data, totalClinvar)
  const geneTrackW = geneWidth - TRACK_LEFT - TRACK_RIGHT
  const geneScaleEnd = segments.length > 0 ? segments[segments.length - 1].transcriptEnd : data.geneLength
  const geneTicks = geneScaleTicks(geneScaleEnd)
  const xForGeneBp = (bp: number) =>
    TRACK_LEFT + ((clamp(bp, 1, geneScaleEnd) - 1) / Math.max(1, geneScaleEnd - 1)) * geneTrackW
  const toggleGeneFeatureKey = (key: string) => {
    setSelectedGeneFeatureKey((current) => (current === key ? null : key))
  }

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
          {data.utr5Length > 0 && <StatPill label={`5' UTR ${formatInt(data.utr5Length)} bp`} />}
          {data.utr3Length > 0 && <StatPill label={`3' UTR ${formatInt(data.utr3Length)} bp`} />}
          <StatPill label={architectureIsTranscript ? 'transcript architecture' : 'selected range'} />
          <StatPill label={exonPillLabel} />
          {totalClinvar > 0 && <StatPill label={`${totalClinvar} ClinVar`} />}
          <label style={toggleLabelStyle}>
            <input
              type="checkbox"
              checked={showGeneScale}
              onChange={(event) => setShowGeneScale(event.currentTarget.checked)}
            />
            bp scale
          </label>
        </div>
      </div>

      <div style={trackScrollStyle}>
      <svg
        viewBox={`0 0 ${geneWidth} ${VIEW_H}`}
        role="img"
        aria-label={`${data.gene} ${data.transcript} ${
          architectureIsTranscript ? 'transcript architecture' : 'selected-range'
        } track with queried variant and ClinVar markers`}
        style={{ display: 'block', width: geneWidth, maxWidth: 'none', height: 'auto' }}
      >
        <style>{`
          .gv-feature { cursor: pointer; outline: none; }
          .gv-feature-box,
          .gv-intron-line {
            transition: fill var(--dur-1) var(--ease-standard),
              stroke var(--dur-1) var(--ease-standard),
              stroke-width var(--dur-1) var(--ease-standard),
              filter var(--dur-1) var(--ease-standard);
          }
          .gv-feature:hover .gv-feature-box,
          .gv-feature:focus-visible .gv-feature-box,
          .gv-feature.is-selected .gv-feature-box {
            fill: var(--warn-tint);
            stroke: var(--warn);
            stroke-width: 2;
            filter: drop-shadow(0 1px 3px rgba(186, 117, 23, 0.18));
          }
          .gv-feature:hover .gv-intron-line,
          .gv-feature:focus-visible .gv-intron-line,
          .gv-feature.is-selected .gv-intron-line {
            stroke: var(--warn);
            stroke-width: 3;
          }
        `}</style>
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
          const title = segmentTitle(seg)
          const selected = selectedGeneFeatureKey === seg.key
          const onKeyDown = (event: KeyboardEvent<SVGGElement>) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              toggleGeneFeatureKey(seg.key)
            }
          }
          if (seg.kind === 'intron') {
            return (
              <g
                key={seg.key}
                className={`gv-feature gv-intron${selected ? ' is-selected' : ''}`}
                role="button"
                tabIndex={0}
                aria-pressed={selected}
                aria-label={title}
                onClick={() => toggleGeneFeatureKey(seg.key)}
                onKeyDown={onKeyDown}
              >
                <rect
                  x={x}
                  y={TRACK_Y - 8}
                  width={w}
                  height={EXON_H + 16}
                  fill="transparent"
                  pointerEvents="all"
                />
                <line
                  className="gv-intron-line"
                  x1={x}
                  y1={TRACK_Y + EXON_H / 2}
                  x2={x + w}
                  y2={TRACK_Y + EXON_H / 2}
                  stroke="var(--ink-5)"
                  strokeWidth="1.5"
                />
                <title>{title}</title>
              </g>
            )
          }
          const isUtr = seg.kind === 'utr5' || seg.kind === 'utr3'
          const featureH = isUtr ? UTR_H : EXON_H
          const featureY = isUtr ? TRACK_Y + (EXON_H - UTR_H) / 2 : TRACK_Y
          const fill = isUtr ? 'var(--bg-soft2)' : 'var(--bg)'
          const label = isUtr ? (seg.kind === 'utr5' ? "5'" : "3'") : String(seg.num)
          return (
            <g
              key={seg.key}
              className={`gv-feature gv-${seg.kind}${selected ? ' is-selected' : ''}`}
              role="button"
              tabIndex={0}
              aria-pressed={selected}
              aria-label={title}
              onClick={() => toggleGeneFeatureKey(seg.key)}
              onKeyDown={onKeyDown}
            >
              <rect
                className="gv-feature-box"
                x={x}
                y={featureY}
                width={w}
                height={featureH}
                rx={isUtr ? 2 : 3}
                fill={fill}
                stroke="var(--ink)"
                strokeWidth={isUtr ? 0.9 : 1.25}
              />
              {w > (isUtr ? 16 : 18) && (
                <text
                  x={x + w / 2}
                  y={TRACK_Y + EXON_H / 2 + 4}
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight="700"
                  fill={isUtr ? 'var(--ink-3)' : 'var(--ink)'}
                  fontFamily="var(--mono)"
                  pointerEvents="none"
                >
                  {label}
                </text>
              )}
              <title>{title}</title>
            </g>
          )
        })}

        {/* ClinVar markers BELOW the track — small triangles, color by class */}
        {clinvarMarks.map((m, i) => {
          const x = TRACK_LEFT + (m.pct / 100) * geneTrackW
          const y = TRACK_Y + EXON_H + 6
          const fill = CLASS_COLOR[m.cls] ?? 'var(--cls-na-dot)'
          if (m.kind === 'truncating') {
            return (
              <circle key={`cv-${i}`} cx={x} cy={y + 4} r="4.3" fill={fill} opacity="0.86">
                <title>{`${m.label} | ${m.cv} | truncating variant`}</title>
              </circle>
            )
          }
          if (m.kind === 'splice') {
            return (
              <rect key={`cv-${i}`} x={x - 4} y={y} width="8" height="8" fill={fill} opacity="0.86">
                <title>{`${m.label} | ${m.cv} | splice-site variant`}</title>
              </rect>
            )
          }
          return (
            <polygon
              key={`cv-${i}`}
              points={`${x - 3.5},${y + 7} ${x + 3.5},${y + 7} ${x},${y}`}
              fill={fill}
              opacity="0.85"
            >
              <title>{`${m.label} | ${m.cv} | missense/coding variant`}</title>
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
            <SvgVariantMarker
              kind={queriedMarkerKind}
              x={TRACK_LEFT + (variantPct / 100) * geneTrackW}
              y={TRACK_Y - 30}
              size={6}
              fill={queriedMarkerFill}
              stroke="var(--ink)"
              strokeWidth={1.5}
              title={`${transcriptVariantLabel} | ${classLabel(queriedMarkerClassification)} | ${variantMarkerKindLabel(queriedMarkerKind)}`}
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
              {transcriptVariantLabel}
            </text>
          </g>
        )}

        {showGeneScale && (
          <g aria-label="Transcript feature scale">
            <line
              x1={TRACK_LEFT}
              y1={GENE_SCALE_Y}
              x2={TRACK_LEFT + geneTrackW}
              y2={GENE_SCALE_Y}
              stroke="var(--ink-3)"
              strokeWidth="0.8"
            />
            {geneTicks.map((tick) => {
              const x = xForGeneBp(tick.bp)
              const terminalTick = geneTicks.find((candidate) => candidate.terminal)
              const closeToTerminal =
                !tick.terminal && terminalTick != null && Math.abs(x - xForGeneBp(terminalTick.bp)) < 112
              const label =
                tick.bp === 1
                  ? '1'
                  : tick.terminal
                    ? `${formatInt(tick.bp)} bp model`
                    : tick.major && !closeToTerminal
                      ? formatInt(tick.bp)
                      : null
              return (
                <g key={`gene-scale-${tick.bp}`}>
                  <line
                    x1={x}
                    y1={GENE_SCALE_Y - (tick.major ? 7 : 4)}
                    x2={x}
                    y2={GENE_SCALE_Y + (tick.major ? 8 : 5)}
                    stroke={tick.major ? 'var(--ink-3)' : 'var(--ink-5)'}
                    strokeWidth={tick.major ? 0.85 : 0.55}
                  />
                  {label && (
                    <text
                      x={x}
                      y={GENE_SCALE_Y + 21}
                      textAnchor={tick.bp === 1 ? 'start' : tick.terminal ? 'end' : 'middle'}
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
        <span style={legendLabel}>Shape:</span>
        <LegendShape kind="missense" label="Missense/coding" />
        <LegendShape kind="truncating" label="Truncating" />
        <LegendShape kind="splice" label="Splice site" />
      </div>

      {selectedGeneFeature && (
        <div style={geneFeaturePanelStyle} aria-label="Selected gene feature details">
          <div style={geneFeaturePanelHeadStyle}>
            <div>
              <span style={geneFeatureKindStyle}>{segmentKindLabel(selectedGeneFeature)}</span>
              <div style={geneFeatureTitleStyle}>{formatInt(selectedGeneFeature.bp)} bp</div>
            </div>
            <button
              type="button"
              style={geneFeatureCloseStyle}
              aria-label="Close gene feature details"
              onClick={() => setSelectedGeneFeatureKey(null)}
            >
              Close
            </button>
          </div>
          <dl style={geneFeatureDlStyle}>
            <dt style={geneFeatureDtStyle}>Transcript span</dt>
            <dd style={geneFeatureDdStyle}>
              {formatInt(selectedGeneFeature.transcriptStart)}-{formatInt(selectedGeneFeature.transcriptEnd)} bp
            </dd>
            {selectedGeneFeature.kind === 'exon' && (
              <>
                <dt style={geneFeatureDtStyle}>CDS span</dt>
                <dd style={geneFeatureDdStyle}>
                  c.{selectedGeneFeature.cdsStart}-{selectedGeneFeature.cdsEnd}
                </dd>
              </>
            )}
            <dt style={geneFeatureDtStyle}>Feature class</dt>
            <dd style={geneFeatureDdStyle}>
              {selectedGeneFeature.kind === 'intron'
                ? 'Intron'
                : selectedGeneFeature.kind === 'exon'
                  ? 'Exon'
                  : 'Untranslated region'}
            </dd>
          </dl>
        </div>
      )}

      <ReportProteinView
        data={data}
        track={proteinTrack}
        alphaHeatmap={alphaHeatmap}
        includeAlphaMissense={includeAlphaMissense}
        onToggleAlphaMissense={setIncludeAlphaMissense}
        markerClassification={queriedMarkerClassification}
      />

      <ProvenanceNote warnings={warnings} />
    </div>
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

function LegendShape({ kind, label }: { kind: GeneClinvarMarkerKind; label: string }) {
  const swatch =
    kind === 'truncating'
      ? { borderRadius: '50%' }
      : kind === 'splice'
        ? { borderRadius: 1 }
        : { clipPath: 'polygon(50% 0, 0 100%, 100% 100%)' }
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span
        style={{
          width: 9,
          height: 9,
          background: 'var(--ink-4)',
          display: 'inline-block',
          ...swatch,
        }}
      />
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

const geneFeaturePanelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  border: '0.5px solid var(--warn-bdr)',
  borderRadius: 8,
  background: 'var(--warn-tint)',
  color: 'var(--ink-2)',
  padding: '10px 12px',
}

const geneFeaturePanelHeadStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
}

const geneFeatureKindStyle: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  color: 'var(--warn)',
}

const geneFeatureTitleStyle: React.CSSProperties = {
  marginTop: 2,
  fontSize: 15,
  fontWeight: 700,
  color: 'var(--ink)',
  fontVariantNumeric: 'tabular-nums',
}

const geneFeatureCloseStyle: React.CSSProperties = {
  border: '0.5px solid var(--warn-bdr)',
  borderRadius: 7,
  background: 'var(--bg)',
  color: 'var(--ink-3)',
  padding: '4px 8px',
  fontSize: 11,
  fontWeight: 600,
  cursor: 'pointer',
}

const geneFeatureDlStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'auto 1fr',
  gap: '5px 12px',
  margin: 0,
}

const geneFeatureDtStyle: React.CSSProperties = {
  fontSize: 11,
  color: 'var(--ink-4)',
}

const geneFeatureDdStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 11.5,
  fontWeight: 600,
  color: 'var(--ink-2)',
  fontVariantNumeric: 'tabular-nums',
}
