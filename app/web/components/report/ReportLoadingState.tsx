'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

/**
 * ReportLoadingState — the /report wait surface.
 *
 * Replaces the old source-checklist spinner. The backend variant lookup is a
 * real multi-source fan-out that takes ~8-10s every time (measured 2026-06-03:
 * cold 10.7s, warm 7.8-9.4s), so this state is load-bearing, not cosmetic.
 *
 * Honest-motion model (PRODUCT.md lynchpin / DESIGN.md "motion reflects real
 * state only"): the live elapsed counter is REAL state. The twin-strand anneal
 * is an ELAPSED-TIME estimate eased asymptotically toward ~90% against the
 * measured ~9s median; it never claims completion. The component unmounts when
 * the real payload lands, which is the only thing that reads as 100%.
 * `prefers-reduced-motion` collapses the drift to a calm determinate bar that
 * still advances with elapsed time (state, not decoration).
 *
 * Design: Steven's "twin-strand current" direction. Two loose strands (a current
 * echoing the landing DNA variant map) phase-lock into a tight paired double-strand,
 * left to right, as the lookup progresses. Rendered as a clinical instrument,
 * NOT a glowing helix (PRODUCT.md anti-reference: no cutesy/neon helix).
 */

const P50_MS = 9000 // measured median lookup wall time
const PROGRESS_CAP = 0.92 // never visually "complete" while still fetching
const SLOW_MS = 20000 // copy shifts to a "still working" reassurance past this

// elapsed -> eased fraction, asymptotic toward PROGRESS_CAP. 1 - e^(-t/tau)
// approaches 1; tau is tuned so the anneal sits ~0.66 at the p50 then creeps.
function annealFraction(elapsedMs: number): number {
  const tau = P50_MS / 1.4
  return PROGRESS_CAP * (1 - Math.exp(-elapsedMs / tau))
}

// ---------------------------------------------------------------------------
// Strand geometry (viewBox 1000 x 120; strokes use non-scaling-stroke so the
// horizontal stretch never thickens them).
// ---------------------------------------------------------------------------

const VB_W = 1000
const VB_H = 120
const Y_MID = VB_H / 2
const LAMBDA = 84 // wavelength
const PENDING_AMP = 9 // loose strands, small wobble
const PENDING_SEP = 22 // vertical gap between the two loose strands
const ANNEAL_AMP = 15 // tight braid amplitude around the midline

function sinePath(amp: number, baseline: number, phase: number, x0 = 0, x1 = VB_W): string {
  const step = 6
  let d = ''
  for (let x = x0; x <= x1; x += step) {
    const y = baseline + amp * Math.sin((2 * Math.PI * x) / LAMBDA + phase)
    d += `${x === x0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(2)} `
  }
  return d.trim()
}

// Base-pair rungs at the anti-nodes of the braid (where the two annealed strands
// reach max separation), connecting annealed strand A (phase 0) and B (phase pi).
function rungXs(): number[] {
  const xs: number[] = []
  for (let x = LAMBDA / 4; x < VB_W; x += LAMBDA / 2) xs.push(x)
  return xs
}

interface ReportLoadingStateProps {
  /** What the user searched: "GENE c.xxx" or a raw query. */
  query: string
  gene?: string
  cdna?: string
}

export function ReportLoadingState({ query, gene, cdna }: ReportLoadingStateProps) {
  const startRef = useRef<number>(0)
  const rafRef = useRef<number | null>(null)
  const revealRef = useRef<SVGRectElement>(null)
  const frontRef = useRef<SVGLineElement>(null)
  const [elapsedS, setElapsedS] = useState(0)
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  const geo = useMemo(() => {
    const pendingTop = sinePath(PENDING_AMP, Y_MID - PENDING_SEP, 0, -LAMBDA, VB_W + LAMBDA)
    const pendingBot = sinePath(PENDING_AMP, Y_MID + PENDING_SEP, Math.PI, -LAMBDA, VB_W + LAMBDA)
    const annealA = sinePath(ANNEAL_AMP, Y_MID, 0)
    const annealB = sinePath(ANNEAL_AMP, Y_MID, Math.PI)
    const rungs = rungXs().map((x) => ({
      x,
      y1: Y_MID + ANNEAL_AMP * Math.sin((2 * Math.PI * x) / LAMBDA),
      y2: Y_MID + ANNEAL_AMP * Math.sin((2 * Math.PI * x) / LAMBDA + Math.PI),
    }))
    return { pendingTop, pendingBot, annealA, annealB, rungs }
  }, [])

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    startRef.current = performance.now()

    // Reduced motion: discrete 1s updates, no continuous drift; still honest.
    if (reduced) {
      const id = window.setInterval(() => {
        const elapsed = performance.now() - startRef.current
        setElapsedS(Math.floor(elapsed / 1000))
        const f = annealFraction(elapsed)
        if (revealRef.current) revealRef.current.setAttribute('width', String(f * VB_W))
        if (frontRef.current) {
          frontRef.current.setAttribute('x1', String(f * VB_W))
          frontRef.current.setAttribute('x2', String(f * VB_W))
        }
      }, 1000)
      return () => window.clearInterval(id)
    }

    let lastSecond = -1
    const tick = () => {
      const elapsed = performance.now() - startRef.current
      const f = annealFraction(elapsed)
      const frontX = f * VB_W
      if (revealRef.current) revealRef.current.setAttribute('width', String(frontX))
      if (frontRef.current) {
        frontRef.current.setAttribute('x1', String(frontX))
        frontRef.current.setAttribute('x2', String(frontX))
      }
      const sec = Math.floor(elapsed / 1000)
      if (sec !== lastSecond) {
        lastSecond = sec
        setElapsedS(sec)
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [reduced])

  const slow = elapsedS * 1000 >= SLOW_MS
  const statusText = slow ? 'Taking longer than usual, still working' : 'Assembling the evidence'

  return (
    <section
      role="status"
      aria-busy="true"
      aria-live="polite"
      aria-label={`Building the variant report for ${query || 'your search'}. Assembling the evidence, typically about ten seconds.`}
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '32px 32px 28px',
        animation: reduced ? undefined : 'eamos-loading-enter var(--dur-3) var(--ease-standard)',
      }}
    >
      {/* Query header: what the user searched, mirroring VariantHeader. */}
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span
          className="uppercase"
          style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: '0.12em', color: 'var(--ink-4)' }}
        >
          Variant report
        </span>
        {gene ? (
          <span
            style={{
              fontFamily: 'var(--display)',
              fontSize: 26,
              fontWeight: 500,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
              lineHeight: 1.1,
            }}
          >
            {gene}
          </span>
        ) : null}
        {cdna ? (
          <span style={{ fontFamily: 'var(--mono)', fontSize: 15, color: 'var(--ink-3)' }}>{cdna}</span>
        ) : !gene ? (
          <span style={{ fontFamily: 'var(--mono)', fontSize: 15, color: 'var(--ink-2)' }}>{query}</span>
        ) : null}
      </div>

      {/* Twin-strand anneal. Pending loose strands underneath; the paired braid
          is revealed left-to-right by a growing clip as elapsed time advances. */}
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="none"
        aria-hidden="true"
        style={{ display: 'block', width: '100%', height: 120, margin: '22px 0 18px', overflow: 'visible' }}
      >
        <defs>
          <clipPath id="eamos-anneal-clip">
            <rect ref={revealRef} x="0" y="0" width="0" height={VB_H} />
          </clipPath>
        </defs>

        {/* Pending: two loose strands (the un-annealed "current"). */}
        <g
          style={{
            animation: reduced ? undefined : 'eamos-strand-drift 3.4s linear infinite',
            opacity: 0.55,
          }}
        >
          <path
            d={geo.pendingTop}
            fill="none"
            stroke="var(--ink-5)"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
          <path
            d={geo.pendingBot}
            fill="none"
            stroke="var(--ink-5)"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
        </g>

        {/* Annealed: tight paired braid + base-pair rungs, revealed by the clip. */}
        <g clipPath="url(#eamos-anneal-clip)">
          {geo.rungs.map((r) => (
            <line
              key={r.x}
              x1={r.x}
              y1={r.y1}
              x2={r.x}
              y2={r.y2}
              stroke="var(--teal)"
              strokeWidth={1}
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
              opacity={0.5}
            />
          ))}
          <path
            d={geo.annealA}
            fill="none"
            stroke="var(--teal)"
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
          />
          <path
            d={geo.annealB}
            fill="none"
            stroke="var(--teal-deep)"
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
          />
        </g>

        {/* Anneal front: the leading edge where strands are pairing now. */}
        <line
          ref={frontRef}
          x1="0"
          y1={Y_MID - ANNEAL_AMP - 6}
          x2="0"
          y2={Y_MID + ANNEAL_AMP + 6}
          stroke="var(--teal)"
          strokeWidth={1.5}
          vectorEffect="non-scaling-stroke"
          opacity={0.65}
        />
      </svg>

      {/* Honest status line: real elapsed counter + typical-duration anchor. */}
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span style={{ fontSize: 13, color: 'var(--ink-3)' }}>{statusText}</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-4)' }}>
          ~10s typical
          <span style={{ color: 'var(--ink-3)' }}> · {elapsedS}s</span>
        </span>
      </div>

      <style>{`
        @keyframes eamos-strand-drift { to { transform: translateX(-${LAMBDA}px); } }
        @keyframes eamos-loading-enter {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </section>
  )
}
