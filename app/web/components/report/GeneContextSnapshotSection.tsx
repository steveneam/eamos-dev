'use client'

import { useMemo } from 'react'
import { Card } from '@/components/ui/Card'
import { Disclosure } from '@/components/ui/Disclosure'
import type {
  GeneContextSnapshot,
  GeneContextTranscriptExon,
  GeneContextTranscriptIntron,
  GeneContextVariantProjection,
  ReportExtractionSectionTarget,
  ViewerSegment,
} from '@/lib/backend'

interface GeneContextSnapshotSectionProps {
  snapshot?: GeneContextSnapshot | null
  sectionTarget?: ReportExtractionSectionTarget | null
}

interface OverviewSegment {
  key: string
  kind: 'exon' | 'intron'
  label: string
  leftPct: number
  widthPct: number
  centerPct: number
  bp: number
  exonNumber?: number
  intronNumber?: number
  transcriptStart?: number | null
  transcriptEnd?: number | null
}

const VIEWBOX_WIDTH = 920
const TRACK_LEFT = 46
const TRACK_WIDTH = 828

export function GeneContextSnapshotSection({
  snapshot,
  sectionTarget,
}: GeneContextSnapshotSectionProps) {
  const allWarnings = useMemo(() => {
    if (!snapshot) return sectionTarget?.warnings ?? []
    return dedupe([
      ...snapshot.warnings,
      ...snapshot.render_hints.warnings,
      ...(sectionTarget?.warnings ?? []),
    ])
  }, [sectionTarget?.warnings, snapshot])

  if (!snapshot) return null

  const unavailableByPlan = sectionTarget?.match_level === 'unavailable'
  const hasTranscriptModel = snapshot.exons.length > 0
  const canRenderFigures = hasTranscriptModel && !unavailableByPlan
  const defaultOpenFromHash = shouldOpenFromHash(snapshot)
  const meta = [
    snapshot.gene,
    snapshot.transcript,
    snapshot.genome_build,
    `${snapshot.exons.length} exons`,
  ]
    .filter(Boolean)
    .join(' | ')

  return (
    <section id={snapshot.section_id} className="scroll-mt-24">
      <Card title={snapshot.title || 'Gene context snapshot'} meta={meta}>
        <div className="flex flex-wrap gap-2">
          <StatusPill label={snapshot.source_status} />
          {sectionTarget?.match_level && <StatusPill label={formatWarning(sectionTarget.match_level)} />}
          {snapshot.render_hints.large_gene_compression_applied && (
            <StatusPill label="compressed introns" />
          )}
        </div>
        <p style={{ margin: '12px 0 0', fontSize: 13, lineHeight: 1.6, color: 'var(--ink-2)' }}>
          Static transcript context for {snapshot.gene}
          {snapshot.variant?.hgvs_c ? ` ${snapshot.variant.hgvs_c}` : ''}. The overview uses
          source transcript coordinates where available; introns are compressed for report
          readability.
        </p>

        <Disclosure
          id={snapshot.panel_id}
          kicker="Transcript figures"
          showLabel={canRenderFigures ? 'Show transcript figures' : 'Show details'}
          hideLabel="Hide figures"
          summary={canRenderFigures ? `${snapshot.exons.length} exons · zoom window` : undefined}
          defaultOpen={defaultOpenFromHash}
        >
          <div className="flex flex-col gap-3.5">
            {canRenderFigures ? (
              <>
                <TranscriptOverview snapshot={snapshot} />
                <ZoomWindowFigure snapshot={snapshot} />
              </>
            ) : (
              <UnavailableSnapshot snapshot={snapshot} unavailableByPlan={unavailableByPlan} />
            )}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                {allWarnings.slice(0, 4).map((warning) => (
                  <WarningPill key={warning} warning={warning} />
                ))}
              </div>
              {snapshot.workbench_link?.url && (
                <a
                  href={snapshot.workbench_link.url}
                  className="eamos-toggle-btn"
                  style={{
                    background: 'var(--ink-2)',
                    color: '#fff',
                    borderColor: 'var(--ink-2)',
                    fontWeight: 600,
                    textDecoration: 'none',
                    whiteSpace: 'nowrap',
                  }}
                >
                  Open in Workbench
                </a>
              )}
            </div>
          </div>
        </Disclosure>
      </Card>
    </section>
  )
}

function shouldOpenFromHash(snapshot?: GeneContextSnapshot | null): boolean {
  if (!snapshot || typeof window === 'undefined') return false
  const target = window.location.hash.replace(/^#/, '')
  return target === snapshot.section_id || target === snapshot.panel_id
}

function TranscriptOverview({ snapshot }: { snapshot: GeneContextSnapshot }) {
  const segments = useMemo(() => buildOverviewSegments(snapshot), [snapshot])
  const variantPct = variantOverviewPct(snapshot.variant ?? null, segments)
  const variantLabel = compactVariantLabel(snapshot.variant)

  return (
    <figure style={figureStyle}>
      <figcaption style={captionStyle}>
        Full transcript overview | {snapshot.strand === '-' ? 'reverse strand' : 'forward strand'} |
        {snapshot.gene_length ? ` ${formatInteger(snapshot.gene_length)} bp gene` : ' gene length unavailable'}
      </figcaption>
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} 172`}
        role="img"
        aria-label={`${snapshot.gene} transcript overview with variant position`}
        style={{ display: 'block', width: '100%', minHeight: 150 }}
      >
        <rect x="0" y="0" width={VIEWBOX_WIDTH} height="172" rx="8" fill="#f8fbfd" />
        <line x1={TRACK_LEFT} y1="86" x2={TRACK_LEFT + TRACK_WIDTH} y2="86" stroke="#cbd5e1" strokeWidth="2" />
        {segments.map((segment) => {
          const x = TRACK_LEFT + (segment.leftPct / 100) * TRACK_WIDTH
          const width = Math.max(3, (segment.widthPct / 100) * TRACK_WIDTH)
          if (segment.kind === 'intron') {
            return (
              <g key={segment.key}>
                <line x1={x} y1="86" x2={x + width} y2="86" stroke="#94a3b8" strokeWidth="2" />
                {width > 44 && (
                  <text x={x + width / 2} y="118" textAnchor="middle" fontSize="10" fill="#64748b">
                    i{segment.intronNumber}
                  </text>
                )}
              </g>
            )
          }
          return (
            <g key={segment.key}>
              <rect x={x} y="66" width={width} height="40" rx="5" fill="#1D9E75" opacity="0.86" />
              {width > 20 && (
                <text x={x + width / 2} y="90" textAnchor="middle" fontSize="11" fontWeight="700" fill="#fff">
                  {segment.exonNumber}
                </text>
              )}
            </g>
          )
        })}
        {variantPct !== null && (
          <g>
            <line
              x1={TRACK_LEFT + (variantPct / 100) * TRACK_WIDTH}
              y1="32"
              x2={TRACK_LEFT + (variantPct / 100) * TRACK_WIDTH}
              y2="126"
              stroke="#0b1a2b"
              strokeWidth="2"
            />
            <path
              d={`M ${TRACK_LEFT + (variantPct / 100) * TRACK_WIDTH - 7} 32 L ${
                TRACK_LEFT + (variantPct / 100) * TRACK_WIDTH + 7
              } 32 L ${TRACK_LEFT + (variantPct / 100) * TRACK_WIDTH} 45 Z`}
              fill="#0b1a2b"
            />
            <text
              x={Math.min(860, Math.max(70, TRACK_LEFT + (variantPct / 100) * TRACK_WIDTH))}
              y="24"
              textAnchor="middle"
              fontSize="12"
              fontWeight="700"
              fill="#0b1a2b"
            >
              {variantLabel}
            </text>
          </g>
        )}
        <text x={TRACK_LEFT} y="150" fontSize="11" fill="#475569" fontWeight="700">
          5 prime
        </text>
        <text x={TRACK_LEFT + TRACK_WIDTH} y="150" textAnchor="end" fontSize="11" fill="#475569" fontWeight="700">
          3 prime
        </text>
      </svg>
    </figure>
  )
}

function ZoomWindowFigure({ snapshot }: { snapshot: GeneContextSnapshot }) {
  const sequence = (
    snapshot.zoom_sequences?.display_window_sequence ||
    snapshot.zoom_sequences?.reference_window_sequence ||
    ''
  ).toUpperCase()
  const windowStart = snapshot.zoom_window?.display_cds_start ?? 1
  const totalBases = snapshot.zoom_window?.total_display_bases ?? sequence.length
  const variantIndex = variantSequenceIndex(snapshot.variant ?? null, snapshot)
  const view = sliceSequence(sequence, variantIndex)

  return (
    <figure style={figureStyle}>
      <figcaption style={captionStyle}>
        Local variant window | {snapshot.zoom_window?.kind ?? 'window'} | {snapshot.render_hints.zoom_flank_bp} bp flank
      </figcaption>
      {sequence ? (
        <svg
          viewBox={`0 0 ${VIEWBOX_WIDTH} 170`}
          role="img"
          aria-label={`${snapshot.gene} local sequence window`}
          style={{ display: 'block', width: '100%', minHeight: 150 }}
        >
          <rect x="0" y="0" width={VIEWBOX_WIDTH} height="170" rx="8" fill="#fbfcfd" />
          <ZoomSegmentTrack
            segments={snapshot.zoom_segments}
            windowStart={windowStart}
            totalBases={totalBases}
          />
          {view.bases.map((base, index) => {
            const x = 42 + index * 19
            const isVariant = view.variantVisibleIndex === index
            return (
              <g key={`${base}-${index}`}>
                <rect
                  x={x}
                  y="72"
                  width="17"
                  height="28"
                  rx="4"
                  fill={isVariant ? '#0b1a2b' : '#eef6f3'}
                  stroke={isVariant ? '#0b1a2b' : '#d6e5df'}
                  strokeWidth="1"
                />
                <text
                  x={x + 8.5}
                  y="91"
                  textAnchor="middle"
                  fontFamily="JetBrains Mono, monospace"
                  fontSize="13"
                  fontWeight="700"
                  fill={isVariant ? '#fff' : '#1f2937'}
                >
                  {base}
                </text>
              </g>
            )
          })}
          <text x="42" y="124" fontSize="11" fill="#64748b" fontFamily="JetBrains Mono, monospace">
            c.{windowStart + view.start}
          </text>
          <text x="878" y="124" textAnchor="end" fontSize="11" fill="#64748b" fontFamily="JetBrains Mono, monospace">
            c.{windowStart + view.start + view.bases.length - 1}
          </text>
          {view.variantVisibleIndex !== null && (
            <text
              x={42 + view.variantVisibleIndex * 19 + 8.5}
              y="145"
              textAnchor="middle"
              fontSize="11"
              fontWeight="700"
              fill="#0b1a2b"
            >
              {variantAltLabel(snapshot.variant)}
            </text>
          )}
        </svg>
      ) : (
        <div style={unavailableStyle}>Sequence window unavailable for this snapshot.</div>
      )}
    </figure>
  )
}

function ZoomSegmentTrack({
  segments,
  windowStart,
  totalBases,
}: {
  segments: ViewerSegment[]
  windowStart: number
  totalBases: number
}) {
  if (segments.length === 0) return null
  const windowEnd = windowStart + Math.max(1, totalBases)
  return (
    <g>
      <line x1="42" y1="44" x2="878" y2="44" stroke="#cbd5e1" strokeWidth="2" />
      {segments.map((segment, index) => {
        const start = segment.cds_start ?? windowStart + index * 12
        const end = segment.cds_end ?? start + Math.max(4, segment.sequence.length)
        const x = 42 + (Math.max(0, start - windowStart) / Math.max(1, windowEnd - windowStart)) * 836
        const width = Math.max(18, ((end - start + 1) / Math.max(1, windowEnd - windowStart)) * 836)
        if (segment.kind === 'intron') {
          return <line key={segment.id} x1={x} y1="44" x2={x + width} y2="44" stroke="#94a3b8" strokeWidth="2" />
        }
        return (
          <g key={segment.id}>
            <rect x={x} y="34" width={width} height="20" rx="4" fill="#8fb9aa" />
            {width > 36 && (
              <text x={x + width / 2} y="49" textAnchor="middle" fontSize="9" fontWeight="700" fill="#fff">
                {segment.label || `exon ${segment.exon_number ?? ''}`}
              </text>
            )}
          </g>
        )
      })}
    </g>
  )
}

function UnavailableSnapshot({
  snapshot,
  unavailableByPlan,
}: {
  snapshot: GeneContextSnapshot
  unavailableByPlan: boolean
}) {
  return (
    <div style={unavailableStyle}>
      {unavailableByPlan
        ? 'Variant-level transcript context is unavailable for this search interpretation.'
        : `Transcript model unavailable for ${snapshot.gene}.`}
    </div>
  )
}

function StatusPill({ label }: { label: string }) {
  return (
    <span
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 999,
        background: 'var(--bg-soft)',
        color: 'var(--ink-3)',
        padding: '3px 8px',
        fontSize: 10.5,
        fontWeight: 700,
      }}
    >
      {label}
    </span>
  )
}

function WarningPill({ warning }: { warning: string }) {
  return (
    <span
      title={warning}
      style={{
        border: '0.5px solid var(--warn-bdr)',
        background: 'var(--warn-tint)',
        color: '#633806',
        borderRadius: 7,
        padding: '5px 8px',
        fontSize: 10.5,
        fontWeight: 600,
        overflowWrap: 'anywhere',
      }}
    >
      {formatWarning(warning)}
    </span>
  )
}

function buildOverviewSegments(snapshot: GeneContextSnapshot): OverviewSegment[] {
  const raw: Array<
    Omit<OverviewSegment, 'leftPct' | 'widthPct' | 'centerPct'> & { units: number }
  > = []
  const minExon = snapshot.render_hints.min_exon_width_px || 18
  const maxIntron = snapshot.render_hints.max_intron_width_px || 70
  snapshot.exons.forEach((exon, index) => {
    const bp = exonBp(exon)
    raw.push({
      key: `exon-${exon.number}`,
      kind: 'exon',
      label: `Exon ${exon.number}`,
      bp,
      exonNumber: exon.number,
      transcriptStart: exon.transcript_start ?? exon.cds_start,
      transcriptEnd: exon.transcript_end ?? exon.cds_end,
      units: Math.max(minExon, Math.sqrt(bp) * 3.2),
    })
    const intron = snapshot.introns[index]
    if (intron) {
      const intronLength = intronBp(intron)
      raw.push({
        key: `intron-${intron.number}`,
        kind: 'intron',
        label: `Intron ${intron.number}`,
        bp: intronLength,
        intronNumber: intron.number,
        transcriptStart: intron.transcript_start,
        transcriptEnd: intron.transcript_end,
        units: Math.min(maxIntron, Math.max(14, Math.log10(intronLength + 1) * 18)),
      })
    }
  })

  const total = raw.reduce((sum, segment) => sum + segment.units, 0) || 1
  let cursor = 0
  return raw.map((segment) => {
    const leftPct = (cursor / total) * 100
    const widthPct = (segment.units / total) * 100
    cursor += segment.units
    return {
      ...segment,
      leftPct,
      widthPct,
      centerPct: leftPct + widthPct / 2,
    }
  })
}

function variantOverviewPct(
  variant: GeneContextVariantProjection | null,
  segments: OverviewSegment[],
): number | null {
  if (!variant || segments.length === 0) return null
  if (variant.transcript_offset != null) {
    const segment = segments.find(
      (item) =>
        item.transcriptStart != null &&
        item.transcriptEnd != null &&
        variant.transcript_offset != null &&
        variant.transcript_offset >= Math.min(item.transcriptStart, item.transcriptEnd) &&
        variant.transcript_offset <= Math.max(item.transcriptStart, item.transcriptEnd),
    )
    if (segment?.transcriptStart != null && segment.transcriptEnd != null) {
      const start = Math.min(segment.transcriptStart, segment.transcriptEnd)
      const end = Math.max(segment.transcriptStart, segment.transcriptEnd)
      const ratio = (variant.transcript_offset - start) / Math.max(1, end - start + 1)
      return segment.leftPct + segment.widthPct * clamp(ratio, 0, 1)
    }
  }
  const byExon = segments.find((item) => item.kind === 'exon' && item.exonNumber === variant.exon_number)
  if (byExon) return byExon.centerPct
  const byIntron = segments.find((item) => item.kind === 'intron' && item.intronNumber === variant.intron_number)
  if (byIntron) return byIntron.centerPct
  return null
}

function variantSequenceIndex(
  variant: GeneContextVariantProjection | null,
  snapshot: GeneContextSnapshot,
): number | null {
  const start = snapshot.zoom_window?.display_cds_start
  if (variant?.cds_pos != null && start != null) return variant.cds_pos - start
  return null
}

function sliceSequence(sequence: string, variantIndex: number | null) {
  const maxBases = 44
  if (sequence.length <= maxBases) {
    return {
      bases: sequence.split(''),
      start: 0,
      variantVisibleIndex:
        variantIndex != null && variantIndex >= 0 && variantIndex < sequence.length
          ? variantIndex
          : null,
    }
  }
  const center = variantIndex ?? Math.floor(sequence.length / 2)
  const start = clamp(Math.round(center - maxBases / 2), 0, sequence.length - maxBases)
  return {
    bases: sequence.slice(start, start + maxBases).split(''),
    start,
    variantVisibleIndex:
      variantIndex != null && variantIndex >= start && variantIndex < start + maxBases
        ? variantIndex - start
        : null,
  }
}

function compactVariantLabel(variant?: GeneContextVariantProjection | null): string {
  if (!variant) return 'Variant'
  return variant.hgvs_c || variant.hgvs_p || variant.genomic_hg38 || 'Variant'
}

function variantAltLabel(variant?: GeneContextVariantProjection | null): string {
  if (!variant) return 'variant'
  if (variant.ref || variant.alt) return `${variant.ref ?? '?'}>${variant.alt ?? '?'}`
  return 'variant'
}

function exonBp(exon: GeneContextTranscriptExon): number {
  return (
    spanLength(exon.transcript_start, exon.transcript_end) ??
    spanLength(exon.cds_start, exon.cds_end) ??
    exon.genomic_length ??
    spanLength(exon.genomic_start, exon.genomic_end) ??
    1
  )
}

function intronBp(intron: GeneContextTranscriptIntron): number {
  return (
    intron.length_bp ??
    spanLength(intron.transcript_start, intron.transcript_end) ??
    spanLength(intron.genomic_start, intron.genomic_end) ??
    1
  )
}

function spanLength(start?: number | null, end?: number | null): number | null {
  if (start == null || end == null) return null
  return Math.abs(end - start) + 1
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function dedupe(items: string[]): string[] {
  const result: string[] = []
  for (const item of items) {
    if (item && !result.includes(item)) result.push(item)
  }
  return result
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

const figureStyle = {
  margin: 0,
  border: '0.5px solid var(--line)',
  borderRadius: 8,
  background: 'var(--bg)',
  overflow: 'hidden',
} as const

const captionStyle = {
  borderBottom: '0.5px solid var(--line)',
  background: 'var(--bg-soft)',
  padding: '8px 11px',
  color: 'var(--ink-3)',
  fontSize: 11.5,
  fontWeight: 700,
} as const

const unavailableStyle = {
  border: '0.5px dashed var(--line-2)',
  borderRadius: 8,
  background: 'var(--bg-soft)',
  color: 'var(--ink-4)',
  padding: 18,
  fontSize: 12.5,
  textAlign: 'center',
} as const
