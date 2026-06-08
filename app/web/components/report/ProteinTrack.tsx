'use client'

import { useMemo } from 'react'
import type { ProteinDomainTrack } from '@/lib/backend'

// Custom lightweight inline-SVG protein track for §4 Gene & locus context.
// Three stacked lanes on one residue axis:
//   1. variant lollipops  (query = pin, others = circles coloured by class)
//   2. domain / family / active-site track
//   3. AlphaMissense per-residue heatmap — the per-residue MEAN AM score painted
//      green (tolerant) → red (intolerant) so you can see at a glance whether the
//      variant sits in a region the model thinks can't change.
//
// Renders the live `ProteinDomainTrack` contract when it carries features; until
// Codex wires UniProt/InterPro (+ the new `am_per_residue` field) the lanes are
// illustrative mock, explicitly tagged. Chosen over the Nightingale web-component
// library for Next 16 / React 19 (no custom-element hydration cost).

interface RenderDomain {
  start: number
  end: number
  label: string
  short: string
  kind: string
}
interface RenderSite {
  pos: number
  label: string
}
interface RenderMarker {
  pos: number
  label: string
  classification: string
  isQuery: boolean
}
interface RenderTrack {
  length: number
  domains: RenderDomain[]
  sites: RenderSite[]
  markers: RenderMarker[]
  am: number[]
  domainsMock: boolean
  markersMock: boolean
  source: string
}

// ── AlphaMissense per-residue mock ───────────────────────────────────────────
// Deterministic (SSR-safe): a tolerant→intolerant bell peaking through the
// catalytic core, bumped near active sites, with a small fixed ripple.
function buildAmMock(length: number, sites: number[]): number[] {
  const arr: number[] = []
  for (let i = 1; i <= length; i += 1) {
    const rel = i / length
    let v = 0.34 + 0.34 * Math.sin(Math.PI * rel)
    for (const s of sites) {
      const d = Math.abs(i - s)
      if (d < 14) v += 0.32 * (1 - d / 14)
    }
    v += 0.07 * Math.sin(i * 0.7)
    arr.push(Math.max(0.03, Math.min(0.97, v)))
  }
  return arr
}

// RPE65 (533 aa) illustrative track: carotenoid-oxygenase fold + the four
// Fe(II)-coordinating histidines, with the query c.260A>G (p.Asp87Gly) plus a
// couple of well-known LCA2 variants for context.
function buildMockTrack(gene: string | null): RenderTrack {
  if ((gene ?? '').toUpperCase() === 'RPE65') {
    const sites = [180, 241, 313, 527]
    return {
      length: 533,
      domains: [
        {
          start: 28,
          end: 520,
          label: 'Retinoid isomerohydrolase — carotenoid-oxygenase fold (Pfam PF03055 / InterPro IPR004294)',
          short: 'RPE65 / carotenoid oxygenase',
          kind: 'family',
        },
      ],
      sites: [
        { pos: 180, label: 'Fe(II)-coordinating His180 (active site)' },
        { pos: 241, label: 'Fe(II)-coordinating His241 (active site)' },
        { pos: 313, label: 'Fe(II)-coordinating His313 (active site)' },
        { pos: 527, label: 'Fe(II)-coordinating His527 (active site)' },
      ],
      markers: [
        { pos: 87, label: 'p.Asp87Gly — this variant (c.260A>G)', classification: 'uncertain', isQuery: true },
        { pos: 91, label: 'p.Arg91Trp', classification: 'pathogenic', isQuery: false },
        { pos: 368, label: 'p.Tyr368His', classification: 'pathogenic', isQuery: false },
        { pos: 44, label: 'p.Glu44Lys', classification: 'likely_benign', isQuery: false },
      ],
      am: buildAmMock(533, sites),
      domainsMock: true,
      markersMock: true,
      source: 'Illustrative (RPE65 P53811)',
    }
  }
  // Generic fallback: one central domain + a mid-protein query marker.
  const length = 400
  const q = Math.round(length / 2)
  return {
    length,
    domains: [{ start: Math.round(length * 0.12), end: Math.round(length * 0.88), label: 'Protein domain', short: 'Domain', kind: 'domain' }],
    sites: [],
    markers: [{ pos: q, label: 'This variant', classification: 'uncertain', isQuery: true }],
    am: buildAmMock(length, []),
    domainsMock: true,
    markersMock: true,
    source: 'Illustrative',
  }
}

function fromContract(track: ProteinDomainTrack): RenderTrack | null {
  const length = track.protein_length ?? 0
  if (!length || track.features.length === 0) return null
  const domains: RenderDomain[] = []
  const sites: RenderSite[] = []
  for (const f of track.features) {
    if (f.kind === 'site' || f.kind === 'motif') {
      sites.push({ pos: f.aa_start, label: f.label })
    } else {
      domains.push({ start: f.aa_start, end: f.aa_end, label: f.label, short: f.short_label ?? f.label, kind: f.kind })
    }
  }
  const markers: RenderMarker[] = track.variant_markers.map((m) => ({
    pos: m.aa_start,
    label: m.hgvs_p ?? m.label,
    classification: m.classification ?? 'uncertain',
    isQuery: m.is_query,
  }))
  return {
    length,
    domains,
    sites,
    markers,
    am: buildAmMock(length, sites.map((s) => s.pos)),
    domainsMock: false,
    markersMock: false,
    source: track.uniprot_release ? `UniProt ${track.uniprot_release}` : 'UniProt / InterPro',
  }
}

// classification → shared class-ramp dot token
function classDot(classification: string): string {
  const c = classification.toLowerCase()
  if (c.includes('likely_path') || c.includes('likely path')) return 'var(--cls-lpath-dot)'
  if (c.includes('path')) return 'var(--cls-path-dot)'
  if (c.includes('likely_ben') || c.includes('likely ben')) return 'var(--cls-lben-dot)'
  if (c.includes('ben')) return 'var(--cls-ben-dot)'
  return 'var(--cls-vus-dot)'
}

// AlphaMissense mean → 5-band class-ramp dot (green tolerant → red intolerant)
function amColor(v: number): string {
  if (v < 0.2) return 'var(--cls-ben-dot)'
  if (v < 0.4) return 'var(--cls-lben-dot)'
  if (v < 0.6) return 'var(--cls-vus-dot)'
  if (v < 0.8) return 'var(--cls-lpath-dot)'
  return 'var(--cls-path-dot)'
}

const W = 720
const PAD_L = 8
const PAD_R = 8
const plotW = W - PAD_L - PAD_R
const MARKER_Y = 14
const DOMAIN_Y = 60
const DOMAIN_H = 22
const HEAT_Y = DOMAIN_Y + DOMAIN_H + 10
const HEAT_H = 12
const AXIS_Y = HEAT_Y + HEAT_H + 4
const H = AXIS_Y + 22

export function ProteinTrack({ track, gene }: { track?: ProteinDomainTrack | null; gene?: string | null }) {
  const model = useMemo(() => {
    const real = track ? fromContract(track) : null
    return real ?? buildMockTrack(gene ?? null)
  }, [track, gene])

  const { length } = model
  const xFor = (aa: number) => PAD_L + (length <= 1 ? 0.5 : (aa - 1) / (length - 1)) * plotW

  // Run-length-merge the heatmap so we emit a handful of rects, not 1 per residue.
  const heatSegs = useMemo(() => {
    const segs: { x0: number; x1: number; color: string }[] = []
    for (let i = 1; i <= length; i += 1) {
      const color = amColor(model.am[i - 1] ?? 0)
      const x0 = PAD_L + ((i - 1) / length) * plotW
      const x1 = PAD_L + (i / length) * plotW
      const last = segs[segs.length - 1]
      if (last && last.color === color) last.x1 = x1
      else segs.push({ x0, x1, color })
    }
    return segs
  }, [model, length])

  const ticks = useMemo(() => {
    const out = [1]
    for (let t = 100; t < length; t += 100) out.push(t)
    out.push(length)
    return out
  }, [length])

  const anyMock = model.domainsMock || model.markersMock

  return (
    <div style={{ marginTop: 'var(--report-subpanel-gap)', border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', background: 'var(--bg-soft)', padding: 'var(--report-subpanel-pad)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
        <span className="eamos-kicker">Protein domains &amp; AlphaMissense</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{model.length} aa · {model.source}</span>
          {anyMock && (
            <span className="eamos-mock" title="Illustrative — protein domains, variant lollipops and the AlphaMissense heatmap are not yet wired to live data.">
              Mock
            </span>
          )}
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`Protein track for ${gene ?? 'this gene'}: ${model.length} residues with domains, variant positions and an AlphaMissense per-residue tolerance heatmap`} style={{ display: 'block' }}>
        {/* domain backbone line */}
        <line x1={PAD_L} y1={DOMAIN_Y + DOMAIN_H / 2} x2={W - PAD_R} y2={DOMAIN_Y + DOMAIN_H / 2} stroke="var(--line)" strokeWidth="1" />

        {/* domains / families / regions */}
        {model.domains.map((d, i) => {
          const x = xFor(d.start)
          const w = Math.max(2, xFor(d.end) - x)
          return (
            <g key={`dom-${i}`}>
              <rect x={x} y={DOMAIN_Y} width={w} height={DOMAIN_H} rx="4" fill="var(--teal-tint)" stroke="var(--teal-bdr)" strokeWidth="0.75" />
              {w > 120 && (
                <text x={x + w / 2} y={DOMAIN_Y + DOMAIN_H / 2 + 3.5} textAnchor="middle" style={{ fontSize: 9.5, fontWeight: 600, fill: 'var(--teal-deep)' }}>
                  {d.short}
                </text>
              )}
              <title>{`${d.label} · aa ${d.start}–${d.end}`}</title>
            </g>
          )
        })}

        {/* active sites — ticks inside the domain bar */}
        {model.sites.map((s, i) => {
          const x = xFor(s.pos)
          return (
            <g key={`site-${i}`}>
              <rect x={x - 1} y={DOMAIN_Y - 2} width={2} height={DOMAIN_H + 4} fill="var(--ink-2)" />
              <circle cx={x} cy={DOMAIN_Y - 4} r={2.5} fill="var(--ink-2)" />
              <title>{s.label}</title>
            </g>
          )
        })}

        {/* AlphaMissense per-residue heatmap */}
        {heatSegs.map((seg, i) => (
          <rect key={`heat-${i}`} x={seg.x0} y={HEAT_Y} width={Math.max(0.6, seg.x1 - seg.x0 + 0.4)} height={HEAT_H} fill={seg.color} />
        ))}
        <rect x={PAD_L} y={HEAT_Y} width={plotW} height={HEAT_H} fill="none" stroke="var(--line)" strokeWidth="0.5" />

        {/* variant lollipops */}
        {model.markers.map((m, i) => {
          const x = xFor(m.pos)
          const color = classDot(m.classification)
          return (
            <g key={`mk-${i}`}>
              <line x1={x} y1={MARKER_Y + 4} x2={x} y2={DOMAIN_Y} stroke={m.isQuery ? 'var(--ink-2)' : 'var(--ink-5)'} strokeWidth={m.isQuery ? 1.25 : 0.75} />
              {m.isQuery ? (
                <>
                  <circle cx={x} cy={MARKER_Y} r={6} fill={color} stroke="var(--ink)" strokeWidth="1.25" />
                  <circle cx={x} cy={MARKER_Y} r={2} fill="var(--bg)" />
                </>
              ) : (
                <circle cx={x} cy={MARKER_Y} r={4} fill={color} stroke="var(--bg)" strokeWidth="1" />
              )}
              <title>{`${m.label} · aa ${m.pos} · ${m.classification.replace(/_/g, ' ')}`}</title>
            </g>
          )
        })}

        {/* residue axis */}
        <line x1={PAD_L} y1={AXIS_Y} x2={W - PAD_R} y2={AXIS_Y} stroke="var(--ink-4)" strokeWidth="1" />
        {ticks.map((t) => {
          const x = xFor(t)
          return (
            <g key={`tick-${t}`}>
              <line x1={x} y1={AXIS_Y} x2={x} y2={AXIS_Y + 4} stroke="var(--ink-4)" strokeWidth="1" />
              <text x={x} y={AXIS_Y + 15} textAnchor={t === 1 ? 'start' : t === length ? 'end' : 'middle'} style={{ fontSize: 9, fill: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>
                {t}
              </text>
            </g>
          )
        })}
      </svg>

      {/* legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', marginTop: 8, fontSize: 10.5, color: 'var(--ink-4)' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 16, height: 8, borderRadius: 2, background: 'var(--teal-tint)', border: '0.5px solid var(--teal-bdr)' }} />
          Domain / family
        </span>
        {model.sites.length > 0 && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 2, height: 10, background: 'var(--ink-2)' }} />
            Active site
          </span>
        )}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }} title="AlphaMissense per-residue mean — average predicted pathogenicity over all amino-acid substitutions at each position.">
          AlphaMissense
          <span style={{ width: 60, height: 8, borderRadius: 2, background: 'linear-gradient(90deg, var(--cls-ben-dot), var(--cls-vus-dot), var(--cls-path-dot))' }} />
          tolerant → intolerant
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'var(--cls-vus-dot)', border: '1px solid var(--ink)' }} />
          This variant
        </span>
      </div>
    </div>
  )
}
