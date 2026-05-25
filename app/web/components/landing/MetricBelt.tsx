'use client'
import { animate, useInView, useReducedMotion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'

interface Metric {
  value: number
  display: (n: number) => string
  label: string
  hint: string
}

// Approximate totals from the public sources Eamos unifies (May 2026):
// ClinVar >3M classified variants; gnomAD v4 ~909M variants; ClinicalTrials.gov
// ~586K studies; PubMed >40M citations. Counters animate to these figures.
const abbrPlus = (n: number): string => {
  const v = Math.round(n)
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1).replace(/\.0$/, '')}B+`
  if (v >= 1_000_000) return `${Math.round(v / 1_000_000)}M+`
  if (v >= 1_000) return `${Math.round(v / 1_000)}K+`
  return `${v}`
}

const METRICS: Metric[] = [
  {
    value: 3_000_000,
    display: abbrPlus,
    label: 'Clinically interpreted variants',
    hint: 'ClinVar',
  },
  {
    value: 909_000_000,
    display: abbrPlus,
    label: 'Population variants',
    hint: 'gnomAD v4',
  },
  {
    value: 586_000,
    display: abbrPlus,
    label: 'Clinical trials indexed',
    hint: 'ClinicalTrials.gov',
  },
  {
    value: 40_000_000,
    display: abbrPlus,
    label: 'Publications searchable',
    hint: 'PubMed',
  },
]

export function MetricBelt() {
  return (
    <section
      className="py-16"
      style={{
        background: 'var(--d-bg)',
        borderTop: '0.5px solid var(--d-line)',
        borderBottom: '0.5px solid var(--d-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <p className="mb-10 text-center text-[13px]" style={{ color: 'var(--hero-ink-2)' }}>
          Every Eamos report draws on the public databases clinical genetics already trusts:
        </p>
        <div className="grid grid-cols-2 gap-px lg:grid-cols-4" style={{ background: 'var(--d-line)' }}>
          {METRICS.map((m) => (
            <div
              key={m.label}
              className="flex flex-col items-center px-6 py-6 text-center"
              style={{ background: 'var(--d-bg)' }}
            >
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 'clamp(30px, 4vw, 42px)',
                  fontWeight: 500,
                  color: 'var(--hero-ink)',
                  letterSpacing: '-0.02em',
                  lineHeight: 1,
                }}
              >
                <CountUp value={m.value} format={m.display} />
              </span>
              <span
                className="mt-3 text-[12px] font-semibold uppercase tracking-[0.08em]"
                style={{ color: 'var(--hero-ink-2)' }}
              >
                {m.label}
              </span>
              <span className="mt-1 text-[11.5px]" style={{ color: 'var(--hero-ink-3)' }}>
                {m.hint}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
          Approximate totals from public sources, May 2026 · ClinVar · gnomAD v4 · ClinicalTrials.gov · PubMed.
        </p>
      </div>
    </section>
  )
}

function CountUp({ value, format }: { value: number; format: (n: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  const reduce = useReducedMotion()
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (!inView) return
    if (reduce) {
      setDisplay(value)
      return
    }
    const controls = animate(0, value, {
      duration: 1.6,
      ease: [0.2, 0, 0, 1],
      onUpdate: (v) => setDisplay(v),
    })
    return () => controls.stop()
  }, [inView, value, reduce])

  return <span ref={ref}>{format(display)}</span>
}
