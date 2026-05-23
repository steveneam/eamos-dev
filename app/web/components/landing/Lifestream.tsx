'use client'
import { motion, useReducedMotion } from 'framer-motion'

/**
 * The "Lifestream" — an animated emerald current behind the dark hero. A few
 * soft glow blobs drift, and bright pulses travel along flowing curves to
 * suggest a live stream of genomic evidence. Purely decorative (aria-hidden);
 * all motion freezes under prefers-reduced-motion.
 */

const CURVES = [
  { d: 'M -150 180 C 250 80, 500 300, 760 200 S 1150 90, 1400 200', delay: 0 },
  { d: 'M -150 320 C 220 240, 520 420, 780 320 S 1180 230, 1400 320', delay: 1.4 },
  { d: 'M -150 460 C 260 380, 480 560, 760 460 S 1160 360, 1400 470', delay: 2.6 },
  { d: 'M -150 80 C 240 20, 540 200, 800 110 S 1180 40, 1400 110', delay: 3.4 },
  { d: 'M -150 560 C 240 500, 520 640, 800 560 S 1160 470, 1400 560', delay: 0.8 },
]

export function Lifestream() {
  const reduce = useReducedMotion()

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Soft drifting glow blobs */}
      <motion.div
        className="absolute"
        style={{
          top: '-20%',
          left: '8%',
          width: 520,
          height: 520,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(16,185,129,0.32), rgba(16,185,129,0) 70%)',
          filter: 'blur(36px)',
        }}
        animate={reduce ? undefined : { x: [0, 60, -20, 0], y: [0, 30, -10, 0], scale: [1, 1.08, 0.96, 1] }}
        transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute"
        style={{
          top: '20%',
          right: '2%',
          width: 460,
          height: 460,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(52,211,153,0.22), rgba(52,211,153,0) 70%)',
          filter: 'blur(44px)',
        }}
        animate={reduce ? undefined : { x: [0, -50, 20, 0], y: [0, 40, -20, 0], scale: [1, 1.1, 0.94, 1] }}
        transition={{ duration: 26, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Flowing current */}
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 1250 640"
        preserveAspectRatio="xMidYMid slice"
        fill="none"
      >
        <defs>
          <linearGradient id="ls-pulse" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#34d399" stopOpacity="0" />
            <stop offset="50%" stopColor="#6ee7b7" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
          </linearGradient>
        </defs>

        {CURVES.map((curve, i) => (
          <g key={i}>
            {/* faint base ribbon */}
            <path d={curve.d} stroke="rgba(110,231,183,0.10)" strokeWidth={1.25} />
            {/* travelling bright pulse */}
            <motion.path
              d={curve.d}
              stroke="url(#ls-pulse)"
              strokeWidth={2}
              strokeLinecap="round"
              strokeDasharray="120 1900"
              initial={{ strokeDashoffset: 2020 }}
              animate={reduce ? { strokeDashoffset: 1000 } : { strokeDashoffset: [2020, 0] }}
              transition={
                reduce
                  ? { duration: 0 }
                  : { duration: 7.5, repeat: Infinity, ease: 'linear', delay: curve.delay }
              }
            />
          </g>
        ))}
      </svg>

      {/* Fine top sheen + bottom fade into the white content below */}
      <div
        className="absolute inset-x-0 top-0"
        style={{
          height: 160,
          background: 'linear-gradient(to bottom, rgba(110,231,183,0.06), transparent)',
        }}
      />
      <div
        className="absolute inset-x-0 bottom-0"
        style={{
          height: 180,
          background: 'linear-gradient(to bottom, rgba(2,17,12,0), var(--hero-bot))',
        }}
      />
    </div>
  )
}
