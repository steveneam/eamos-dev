'use client'
import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

/**
 * The hero backdrop: an abstract flowing "twin-strand" current — symbolic of DNA
 * without the literal helix or nucleotide letters (both category-reflex cliches).
 * Two woven ribbons, a cool navy and a warm teal, flow down the right of the hero
 * behind the content: a cool counterpoint to the warm cream. Pushed to the
 * background; a soft warm halo lifts the (left-aligned) search shell into the
 * foreground. The strands draw on load, then one slow river-pulse flows along the
 * warm strand. Fully static under prefers-reduced-motion and on small screens.
 */

// Two strands that swap sides as they fall (they cross ~y=290 and ~y=690), which
// reads as a woven pair without drawing the literal ladder. A third, fainter,
// outer strand adds depth. Right-weighted, since the hero content sits left.
const STRANDS = [
  { d: 'M 760 -40 C 640 130, 980 290, 840 450 C 720 590, 1000 690, 860 840', stroke: 'var(--flow-cool)', w: 2, o: 0.18, delay: 0 },
  { d: 'M 850 -40 C 980 130, 660 290, 920 450 C 1040 590, 740 690, 900 840', stroke: 'var(--flow-warm)', w: 2, o: 0.16, delay: 0.18 },
  { d: 'M 1012 -40 C 930 170, 1110 370, 990 560 C 910 710, 1060 800, 1000 900', stroke: 'var(--flow-cool)', w: 1.4, o: 0.1, delay: 0.36 },
]

export function GenomicFlow() {
  const reduce = useReducedMotion()
  const [isSmall, setIsSmall] = useState(false)
  useEffect(() => {
    const m = window.matchMedia('(max-width: 640px)')
    const update = () => setIsSmall(m.matches)
    update()
    m.addEventListener('change', update)
    return () => m.removeEventListener('change', update)
  }, [])
  const still = reduce || isSmall

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Warm halo behind the left-aligned search — static radial (no blur filter,
          so it never repaints per-frame on mobile). Lifts the search off the flow. */}
      <div
        className="absolute"
        style={{
          left: '34%',
          top: '58%',
          width: 780,
          height: 780,
          transform: 'translate(-50%, -50%)',
          background:
            'radial-gradient(circle, color-mix(in oklab, var(--hero-top) 88%, white) 0%, transparent 60%)',
        }}
      />

      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 1200 760"
        preserveAspectRatio="xMidYMid slice"
        fill="none"
      >
        {STRANDS.map((s, i) => (
          <motion.path
            key={i}
            d={s.d}
            stroke={s.stroke}
            strokeWidth={s.w}
            strokeLinecap="round"
            initial={still ? { pathLength: 1, opacity: s.o } : { pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: s.o }}
            transition={
              still ? { duration: 0 } : { duration: 1.3, delay: 0.1 + s.delay, ease: [0.16, 1, 0.3, 1] }
            }
          />
        ))}

        {/* One slow current pulse travelling along the warm strand (the "river"). */}
        {!still && (
          <motion.path
            d={STRANDS[1].d}
            stroke="var(--flow-warm)"
            strokeWidth={2.6}
            strokeLinecap="round"
            strokeOpacity={0.42}
            strokeDasharray="70 1600"
            initial={{ strokeDashoffset: 1670 }}
            animate={{ strokeDashoffset: -70 }}
            transition={{ duration: 9, repeat: Infinity, ease: 'linear', delay: 1.4 }}
          />
        )}
      </svg>

      {/* Fade the flow into the content below the hero. */}
      <div
        className="absolute inset-x-0 bottom-0"
        style={{ height: 200, background: 'linear-gradient(to bottom, transparent, var(--hero-bot))' }}
      />
    </div>
  )
}
