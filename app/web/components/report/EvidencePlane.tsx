'use client'

// A1 — Evidence Plane. Plots the classification decision in 2D: benign points
// (ΣB) on x, pathogenic points (ΣP) on y. Net = ΣP − ΣB, so lines of constant net
// are anti-diagonals and the five tiers are diagonal bands (Pathogenic top-left →
// Benign bottom-right). The variant sits at (ΣB, ΣP).
//
// Clinical-accuracy contract (spec §7, binding not cosmetic): a conflict is a
// HATCHED marker (never a tidy "net 0" dot — conflicting evidence is not the same
// as balanced evidence), and BA1 is an OVERRIDE called out in the legend, never a
// summand folded into ΣB.

import { useRef, type KeyboardEvent, type PointerEvent } from 'react'
import type { EamosComputedClassification, EamosComputedTier } from '@/lib/backend'
import { netBoundaries, POINTS_FORMULA_STAMP, tierTokens } from '@/lib/acmg/points'

// ── geometry: clip a polygon by the half-plane a·x + b·y ≤ c (Sutherland–Hodgman)
type Pt = { x: number; y: number }
function clipHalfPlane(poly: Pt[], a: number, b: number, c: number): Pt[] {
  const out: Pt[] = []
  const inside = (p: Pt) => a * p.x + b * p.y <= c + 1e-9
  for (let i = 0; i < poly.length; i++) {
    const cur = poly[i]
    const prev = poly[(i + poly.length - 1) % poly.length]
    const curIn = inside(cur)
    const prevIn = inside(prev)
    if (curIn) {
      if (!prevIn) out.push(intersect(prev, cur, a, b, c))
      out.push(cur)
    } else if (prevIn) {
      out.push(intersect(prev, cur, a, b, c))
    }
  }
  return out
}
function intersect(p: Pt, q: Pt, a: number, b: number, c: number): Pt {
  const dp = a * p.x + b * p.y - c
  const dq = a * q.x + b * q.y - c
  const t = dp / (dp - dq)
  return { x: p.x + t * (q.x - p.x), y: p.y + t * (q.y - p.y) }
}
function centroid(poly: Pt[]): Pt {
  const s = poly.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 })
  return { x: s.x / poly.length, y: s.y / poly.length }
}

const TIER_SHORT: Record<EamosComputedTier, string> = {
  Pathogenic: 'P',
  'Likely Pathogenic': 'LP',
  VUS: 'VUS',
  'Likely Benign': 'LB',
  Benign: 'B',
}

export function EvidencePlane({
  computed,
  onChange,
}: {
  computed: EamosComputedClassification
  /** When provided, the marker becomes draggable (2-D reverse-calculator): drag
   *  sets ΣP (y) and ΣB (x) independently → net = ΣP − ΣB. Static when omitted. */
  onChange?: (sumPathogenic: number, sumBenign: number) => void
}) {
  const ba1Criterion = computed.per_criterion.find(
    (criterion) => criterion.code === 'BA1' && criterion.triggered,
  )
  const b = netBoundaries(computed.benign_cut)
  const sp = computed.sum_pathogenic
  const sb = computed.sum_benign
  const interactive = typeof onChange === 'function'
  const svgRef = useRef<SVGSVGElement>(null)
  const draggingRef = useRef(false)
  // Data domain padded BELOW the origin so a marker on an axis (ΣB or ΣP = 0)
  // sits inside the plane, never jammed in the corner. Interactive mode uses a
  // FIXED domain so the scale doesn't rescale under the cursor while dragging.
  const domMax = interactive ? 16 : Math.max(12, Math.ceil(sp) + 3, Math.ceil(sb) + 3)
  const domMin = -1.5
  const dom = domMax - domMin

  // Tier strips in net = (y − x) space, capped to the square's reachable net range.
  const strips: { tier: EamosComputedTier; lo: number; hi: number }[] = [
    { tier: 'Pathogenic', lo: b.pathogenic, hi: dom },
    { tier: 'Likely Pathogenic', lo: b.likelyPathogenic, hi: b.pathogenic },
    { tier: 'VUS', lo: b.vus, hi: b.likelyPathogenic },
    { tier: 'Likely Benign', lo: b.likelyBenign, hi: b.vus },
    { tier: 'Benign', lo: -dom, hi: b.likelyBenign },
  ]

  const S = 100 // viewBox units
  const X = (dx: number) => ((dx - domMin) / dom) * S
  const Y = (dy: number) => S - ((dy - domMin) / dom) * S // flip: data-y up → screen-y down

  // ── interactive drag (reverse-calculator): pointer → (ΣP, ΣB) ───────────────
  const clampPt = (n: number) => Math.max(0, Math.min(domMax, Math.round(n)))
  const fromPointer = (clientX: number, clientY: number) => {
    const el = svgRef.current
    if (!el || !onChange) return
    const rect = el.getBoundingClientRect()
    if (!rect.width || !rect.height) return
    const px = ((clientX - rect.left) / rect.width) * S
    const py = ((clientY - rect.top) / rect.height) * S
    const dxB = domMin + (px / S) * dom // invert X → ΣB
    const dyP = domMin + ((S - py) / S) * dom // invert Y → ΣP
    onChange(clampPt(dyP), clampPt(dxB))
  }
  const onPointerDown = (e: PointerEvent<SVGSVGElement>) => {
    if (!interactive) return
    draggingRef.current = true
    try {
      svgRef.current?.setPointerCapture(e.pointerId)
    } catch {
      /* capture can throw on detached nodes — drag still works via move */
    }
    fromPointer(e.clientX, e.clientY)
  }
  const onPointerMove = (e: PointerEvent<SVGSVGElement>) => {
    if (draggingRef.current) fromPointer(e.clientX, e.clientY)
  }
  const endDrag = () => {
    draggingRef.current = false
  }
  const onKeyDown = (e: KeyboardEvent<SVGSVGElement>) => {
    if (!onChange) return
    switch (e.key) {
      case 'ArrowLeft':
        onChange(sp, Math.max(0, sb - 1))
        break
      case 'ArrowRight':
        onChange(sp, Math.min(domMax, sb + 1))
        break
      case 'ArrowDown':
        onChange(Math.max(0, sp - 1), sb)
        break
      case 'ArrowUp':
        onChange(Math.min(domMax, sp + 1), sb)
        break
      default:
        return
    }
    e.preventDefault()
  }

  const square: Pt[] = [
    { x: domMin, y: domMin },
    { x: domMax, y: domMin },
    { x: domMax, y: domMax },
    { x: domMin, y: domMax },
  ]

  const bands = strips
    .map((strip) => {
      // net = y − x. Clip to (y − x ≤ hi): (−x + y ≤ hi); and (y − x ≥ lo): (x − y ≤ −lo).
      let poly = clipHalfPlane(square, -1, 1, strip.hi)
      poly = clipHalfPlane(poly, 1, -1, -strip.lo)
      if (poly.length < 3) return null
      const c = centroid(poly)
      return { ...strip, poly, c }
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)

  const markerNet = `${computed.net_points >= 0 ? '+' : ''}${computed.net_points}`
  const ariaLabel = `Evidence plane: ${sp} pathogenic points versus ${sb} benign points place this variant in the ${computed.tier} band at net ${markerNet}.${computed.conflict.is_conflicting ? ' Marker is hatched to flag conflicting evidence.' : ''}${computed.ba1_override ? ' A BA1 stand-alone benign override applies.' : ''}`

  return (
    <figure role={interactive ? 'group' : 'img'} aria-label={ariaLabel} style={{ margin: 0 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
        <span className="eamos-kicker">Evidence plane{interactive ? ' — drag the marker' : ''}</span>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        {/* y-axis caption */}
        <div
          aria-hidden
          style={{
            writingMode: 'vertical-rl',
            transform: 'rotate(180deg)',
            fontSize: 9.5,
            color: 'var(--ink-4)',
            textAlign: 'center',
            paddingBottom: 14,
          }}
        >
          Pathogenic points (ΣP) →
        </div>

        <div style={{ flex: 1, maxWidth: 280 }}>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${S} ${S}`}
            width="100%"
            style={{ display: 'block', borderRadius: 6, border: '0.5px solid var(--line)', cursor: interactive ? 'grab' : undefined, touchAction: interactive ? 'none' : undefined }}
            aria-hidden={interactive ? undefined : true}
            role={interactive ? 'application' : undefined}
            aria-label={interactive ? `${ariaLabel} Drag the marker, or use arrow keys: left/right adjust benign points, up/down adjust pathogenic points.` : undefined}
            tabIndex={interactive ? 0 : undefined}
            onPointerDown={interactive ? onPointerDown : undefined}
            onPointerMove={interactive ? onPointerMove : undefined}
            onPointerUp={interactive ? endDrag : undefined}
            onPointerCancel={interactive ? endDrag : undefined}
            onKeyDown={interactive ? onKeyDown : undefined}
          >
            <defs>
              <pattern id="conflict-hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="4" height="4" fill="var(--cls-na-bg)" />
                <line x1="0" y1="0" x2="0" y2="4" stroke="var(--ink-3)" strokeWidth="1.4" />
              </pattern>
            </defs>

            {bands.map((band) => (
              <polygon
                key={band.tier}
                points={band.poly.map((p) => `${X(p.x)},${Y(p.y)}`).join(' ')}
                fill={tierTokens(band.tier).band}
                stroke="var(--bg)"
                strokeWidth={0.6}
              />
            ))}

            {/* Tier labels at band centroids (skip slivers). */}
            {bands.map((band) => {
              const area = polyArea(band.poly)
              if (area < dom * dom * 0.012) return null
              return (
                <text
                  key={`l-${band.tier}`}
                  x={X(band.c.x)}
                  y={Y(band.c.y)}
                  fontSize={5}
                  fontWeight={600}
                  fill={tierTokens(band.tier).ink}
                  textAnchor="middle"
                  dominantBaseline="middle"
                >
                  {TIER_SHORT[band.tier]}
                </text>
              )
            })}

            {/* Crosshair guides so the marker's (ΣB, ΣP) reads even on an axis. */}
            <line x1={X(sb)} y1={0} x2={X(sb)} y2={S} stroke="var(--ink-3)" strokeWidth={0.5} strokeDasharray="2 2" opacity={0.5} />
            <line x1={0} y1={Y(sp)} x2={S} y2={Y(sp)} stroke="var(--ink-3)" strokeWidth={0.5} strokeDasharray="2 2" opacity={0.5} />

            {/* The variant marker at (ΣB, ΣP): halo + ring + dot. */}
            <circle cx={X(sb)} cy={Y(sp)} r={6} fill="var(--bg)" opacity={0.85} />
            <circle cx={X(sb)} cy={Y(sp)} r={4.6} fill="var(--bg)" stroke={tierTokens(computed.tier).ink} strokeWidth={0.7} />
            <circle
              cx={X(sb)}
              cy={Y(sp)}
              r={3.4}
              fill={computed.conflict.is_conflicting ? 'url(#conflict-hatch)' : tierTokens(computed.tier).ink}
              stroke={computed.conflict.is_conflicting ? 'var(--ink-2)' : 'var(--bg)'}
              strokeWidth={0.8}
            />
            {/* Net callout beside the puck (flips to the inside near the right edge). */}
            <text
              x={X(sb) + (X(sb) > 72 ? -7 : 7)}
              y={Y(sp) - 6}
              fontSize={5.2}
              fontWeight={700}
              fill={tierTokens(computed.tier).ink}
              stroke="var(--bg)"
              strokeWidth={1.4}
              paintOrder="stroke"
              textAnchor={X(sb) > 72 ? 'end' : 'start'}
            >
              net {markerNet}
            </text>
          </svg>

          <div aria-hidden style={{ fontSize: 9.5, color: 'var(--ink-4)', textAlign: 'center', marginTop: 2 }}>
            ← Benign points (ΣB)
          </div>
        </div>
      </div>

      {(computed.conflict.is_conflicting || computed.ba1_override) && (
        <p role="note" style={{ margin: '8px 0 0', fontSize: 10.5, lineHeight: 1.45, color: 'var(--warn-text)' }}>
          {computed.ba1_override
            ? `BA1: the active ${ba1Criterion?.policy_id ?? 'population'} policy threshold${ba1Criterion?.threshold ? ` (${ba1Criterion.threshold})` : ''} triggers a stand-alone benign override and is not summed into ΣB.`
            : `Hatched marker: pathogenic and benign evidence conflict — advisory capped to VUS${computed.conflict.reason ? ` (${computed.conflict.reason})` : ''}.`}
        </p>
      )}

      <table className="sr-only">
        <caption>EAMOS evidence plane coordinates</caption>
        <tbody>
          <tr>
            <th scope="row">Pathogenic points (ΣP)</th>
            <td>{sp}</td>
          </tr>
          <tr>
            <th scope="row">Benign points (ΣB)</th>
            <td>{sb}</td>
          </tr>
          <tr>
            <th scope="row">Net</th>
            <td>{markerNet}</td>
          </tr>
          <tr>
            <th scope="row">Tier</th>
            <td>{computed.tier}</td>
          </tr>
        </tbody>
      </table>

      <p style={{ margin: '8px 0 0', fontSize: 9.5, color: 'var(--ink-5)' }}>{POINTS_FORMULA_STAMP}</p>
    </figure>
  )
}

function polyArea(poly: Pt[]): number {
  let a = 0
  for (let i = 0; i < poly.length; i++) {
    const p = poly[i]
    const q = poly[(i + 1) % poly.length]
    a += p.x * q.y - q.x * p.y
  }
  return Math.abs(a) / 2
}
