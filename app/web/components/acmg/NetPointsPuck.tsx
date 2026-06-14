'use client'

// Draggable net-points puck — the shared interaction at the heart of the ACMG
// "what-if" surfaces. A banded net-points line (the five Tavtigian tiers) with a
// grabbable thumb: drag it (or arrow-key it) and the tier/posterior recompute
// live. Productionizes the vault `acmg-explainer.html` net-points ruler
// (Explore mode), reused by both the report Card-4 Explore drag-card and the
// full /account explainer.
//
// It RECOMPUTES NOTHING the engine owns: it only maps a *hypothetical* net to a
// tier (lib/acmg/points.ts ADR-0022 cuts) + posterior (2.08^net). All real
// verdicts come from the payload; this is a sandbox. `computedNet` paints a faint
// ghost anchor so the hypothetical always reads against the real call.
//
// A11y (spec bar): role="slider" + aria-valuetext, full keyboard operation
// (←/→ ±1, PageUp/Down ±5, Home/End), prefers-reduced-motion → no eased thumb.

import { useCallback, useId, useRef, type KeyboardEvent, type PointerEvent } from 'react'
import type { EamosComputedBenignCut } from '@/lib/backend'
import {
  gaugeBands,
  POINTS_FORMULA_STAMP,
  posterior,
  tierByNet,
  tierTokens,
} from '@/lib/acmg/points'

const TIER_SHORT: Record<string, string> = {
  Pathogenic: 'P',
  'Likely Pathogenic': 'LP',
  VUS: 'VUS',
  'Likely Benign': 'LB',
  Benign: 'B',
}
const signed = (n: number) => `${n >= 0 ? '+' : ''}${n}`
const pct = (p: number) => `${(p * 100).toFixed(1)}%`

export interface NetPointsPuckProps {
  /** Current (hypothetical) net score the thumb sits at. */
  net: number
  /** Called with the snapped integer net on drag / keyboard. */
  onChange: (net: number) => void
  benignCut: EamosComputedBenignCut
  /** The real computed net — drawn as a faint ghost anchor + "computed" tick. */
  computedNet?: number | null
  /** Domain overrides; defaults expand to keep both thumb + ghost in view. */
  min?: number
  max?: number
  /** Mute the thumb (illustrative / not-yet-wired). */
  mock?: boolean
  /** aria-label prefix, e.g. "Hypothetical net points". */
  label?: string
  /** Hide the formula stamp when a host already shows one. */
  hideStamp?: boolean
}

export function NetPointsPuck({
  net,
  onChange,
  benignCut,
  computedNet = null,
  min,
  max,
  mock = false,
  label = 'Net points',
  hideStamp = false,
}: NetPointsPuckProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const draggingRef = useRef(false)
  const styleId = useId()

  // Domain padded so both the thumb and the ghost anchor stay on-track.
  const anchor = computedNet ?? net
  const lo = Math.min(min ?? -10, Math.floor(Math.min(net, anchor)) - 1)
  const hi = Math.max(max ?? 13, Math.ceil(Math.max(net, anchor)) + 1)
  const span = hi - lo
  const xNet = (n: number) => ((n - lo) / span) * 100
  const clamp = (n: number) => Math.max(lo, Math.min(hi, n))

  const bands = gaugeBands(benignCut, lo, hi)
  const tier = tierByNet(net, benignCut)
  const tokens = tierTokens(tier)
  const post = posterior(net)

  // Integer net ticks at the four tier dividers + zero.
  const ticks = Array.from(new Set([lo, -7, -1, 0, 6, 10, hi].filter((t) => t >= lo && t <= hi))).sort(
    (a, b) => a - b,
  )

  const setFromClientX = useCallback(
    (clientX: number) => {
      const el = trackRef.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      if (rect.width === 0) return
      const frac = (clientX - rect.left) / rect.width
      onChange(Math.max(lo, Math.min(hi, Math.round(lo + frac * span))))
    },
    [lo, hi, span, onChange],
  )

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    draggingRef.current = true
    try {
      trackRef.current?.setPointerCapture(e.pointerId)
    } catch {
      /* setPointerCapture can throw on detached nodes — drag still works via move */
    }
    setFromClientX(e.clientX)
  }
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (draggingRef.current) setFromClientX(e.clientX)
  }
  const endDrag = () => {
    draggingRef.current = false
  }

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    let next = net
    switch (e.key) {
      case 'ArrowLeft':
      case 'ArrowDown':
        next = net - 1
        break
      case 'ArrowRight':
      case 'ArrowUp':
        next = net + 1
        break
      case 'PageDown':
        next = net - 5
        break
      case 'PageUp':
        next = net + 5
        break
      case 'Home':
        next = lo
        break
      case 'End':
        next = hi
        break
      default:
        return
    }
    e.preventDefault()
    onChange(clamp(next))
  }

  const valueText = `net ${signed(net)}, ${tier}, posterior ${pct(post)}`
  const thumbColor = mock ? 'var(--ink-4)' : tokens.ink

  return (
    <div style={{ userSelect: 'none' }}>
      {/* Reduced-motion-aware thumb glide: only animates when the user allows motion. */}
      <style>{`
        .acmg-puck-thumb-${styleId.replace(/[:]/g, '')} { transition: none; }
        @media (prefers-reduced-motion: no-preference) {
          .acmg-puck-thumb-${styleId.replace(/[:]/g, '')} { transition: left 0.12s var(--ease-standard, ease); }
        }
      `}</style>

      {/* Tier labels above their bands. */}
      <div style={{ position: 'relative', height: 14 }} aria-hidden>
        {bands.map((b) => (
          <span
            key={b.tier}
            style={{
              position: 'absolute',
              left: `${xNet((b.from + b.to) / 2)}%`,
              transform: 'translateX(-50%)',
              fontSize: 9.5,
              fontWeight: 600,
              color: tierTokens(b.tier).ink,
              whiteSpace: 'nowrap',
            }}
          >
            {TIER_SHORT[b.tier]}
          </span>
        ))}
      </div>

      {/* The slider track — focusable, pointer + keyboard operable. */}
      <div
        ref={trackRef}
        role="slider"
        tabIndex={0}
        aria-label={label}
        aria-valuemin={lo}
        aria-valuemax={hi}
        aria-valuenow={net}
        aria-valuetext={valueText}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onKeyDown={onKeyDown}
        style={{
          position: 'relative',
          height: 24,
          marginTop: 2,
          cursor: 'grab',
          touchAction: 'none',
          borderRadius: 6,
          outlineOffset: 3,
        }}
      >
        {/* bands */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 6,
            overflow: 'hidden',
            display: 'flex',
            boxShadow: 'inset 0 0 0 0.5px var(--line)',
          }}
        >
          {bands.map((b) => (
            <span
              key={b.tier}
              title={`${b.tier}: net ${Math.ceil(b.from)}…${Math.floor(b.to)}`}
              style={{ width: `${((b.to - b.from) / span) * 100}%`, background: tierTokens(b.tier).band }}
            />
          ))}
        </div>

        {/* Ghost anchor: the real computed net (where the actual verdict sits). */}
        {computedNet != null && (
          <span aria-hidden style={{ position: 'absolute', left: `${xNet(computedNet)}%`, top: -2, bottom: -2, transform: 'translateX(-50%)' }}>
            <span style={{ position: 'absolute', top: 0, bottom: 0, left: '50%', width: 1.5, transform: 'translateX(-50%)', background: 'var(--ink-3)', opacity: 0.55, borderRadius: 1 }} />
          </span>
        )}

        {/* Draggable thumb. */}
        <span
          aria-hidden
          className={`acmg-puck-thumb-${styleId.replace(/[:]/g, '')}`}
          style={{
            position: 'absolute',
            left: `${xNet(net)}%`,
            top: -6,
            bottom: -6,
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            pointerEvents: 'none',
          }}
        >
          <span
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 9.5,
              fontWeight: 700,
              color: thumbColor,
              background: 'var(--bg)',
              padding: '0 3px',
              borderRadius: 3,
              marginBottom: 1,
              whiteSpace: 'nowrap',
            }}
          >
            net {signed(net)}
          </span>
          <span style={{ flex: 1, width: 2, background: thumbColor, borderRadius: 1 }} />
          <span
            style={{
              width: 13,
              height: 13,
              borderRadius: '50%',
              background: 'var(--bg)',
              border: `2px solid ${thumbColor}`,
              boxShadow: 'var(--elev-1)',
              marginTop: -1,
            }}
          />
        </span>
      </div>

      {/* Net ticks below the track. */}
      <div style={{ position: 'relative', height: 13, marginTop: 3 }} aria-hidden>
        {ticks.map((t) => (
          <span
            key={t}
            style={{
              position: 'absolute',
              left: `${xNet(t)}%`,
              transform: 'translateX(-50%)',
              fontFamily: 'var(--mono)',
              fontSize: 8.5,
              color: 'var(--ink-5)',
            }}
          >
            {signed(t)}
          </span>
        ))}
      </div>

      {computedNet != null && (
        <p aria-hidden style={{ margin: '4px 0 0', fontSize: 9.5, color: 'var(--ink-4)', display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ display: 'inline-block', width: 10, height: 1.5, background: 'var(--ink-3)', opacity: 0.55 }} /> computed verdict (net {signed(computedNet)})
        </p>
      )}

      {!hideStamp && <p style={{ margin: '6px 0 0', fontSize: 9.5, color: 'var(--ink-5)' }}>{POINTS_FORMULA_STAMP}</p>}
    </div>
  )
}
