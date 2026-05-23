'use client'
import { animate, useInView, useReducedMotion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'

interface Metric {
  value: number
  display: (n: number) => string
  label: string
  hint: string
}

const METRICS: Metric[] = [
  {
    value: 1420893,
    display: (n) => Math.round(n).toLocaleString(),
    label: 'Tracked variants indexed',
    hint: 'across the aggregated source graph',
  },
  {
    value: 432910,
    display: (n) => Math.round(n).toLocaleString(),
    label: 'Mined functional papers',
    hint: 'unique PMIDs, deduplicated',
  },
  {
    value: 1204,
    display: (n) => Math.round(n).toLocaleString(),
    label: 'Submissions to ClinVar',
    hint: 'passed through the ledger messenger',
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
          Eamos runs a live, parallel evidence aggregator across global genomics data.
        </p>
        <div className="grid grid-cols-1 gap-px sm:grid-cols-3" style={{ background: 'var(--d-line)' }}>
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
          Sample figures — live counters wire in at launch.
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
