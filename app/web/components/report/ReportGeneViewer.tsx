'use client'

import { useEffect, useMemo, useState } from 'react'
import { getGeneViewer } from '@/lib/api'
import { adaptGeneViewer } from '@/lib/workbench/gene-viewer-adapter'
import type { GeneWindowData } from '@/lib/workbench/gene-window'

interface ReportGeneViewerProps {
  gene: string
  cdna: string
  transcript?: string | null
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

export function ReportGeneViewer({ gene, cdna, transcript }: ReportGeneViewerProps) {
  const [data, setData] = useState<GeneWindowData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getGeneViewer({
      gene,
      cdna,
      transcript: transcript ?? null,
      species: 'human',
    })
      .then((resp) => {
        if (cancelled) return
        setData(adaptGeneViewer(resp))
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
  }, [gene, cdna, transcript])

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
          stroke="#cbd5e1"
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
                stroke="#94a3b8"
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
                  fill="#fff"
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
              fill={CLASS_COLOR[m.cls] ?? '#94a3b8'}
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
          fill="#64748b"
          fontWeight="700"
        >
          5′
        </text>
        <text
          x={TRACK_LEFT + TRACK_W}
          y={VIEW_H - 14}
          textAnchor="end"
          fontSize="10.5"
          fill="#64748b"
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
    </div>
  )
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
