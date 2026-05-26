'use client'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useState } from 'react'
import { LandingH2 } from '@/components/landing/ui/LandingHeading'

function FaqStyles() {
  return (
    <style>{`
      .faq-row-btn:hover { background: color-mix(in oklab, var(--em) 5%, transparent) !important; }
      .faq-row-btn:focus-visible {
        box-shadow: inset 0 0 0 2px color-mix(in oklab, var(--em) 35%, transparent);
      }
    `}</style>
  )
}

interface QA {
  q: string
  a: string
}

const ITEMS: QA[] = [
  {
    q: 'Where does the functional literature count come from?',
    a: 'Eamos queries ClinGen, ClinVar sub-ledgers, and PubMed concurrently, then passes the extracted PMIDs through a hash set to strictly eliminate duplication before counting.',
  },
  {
    q: 'Does Eamos store private patient data?',
    a: 'No. Eamos functions strictly as an evidence aggregator. No genetic sequence files (VCFs) are retained in our database pipelines; records are pulled live, per query.',
  },
  {
    q: 'Which databases does a single search cover?',
    a: 'ClinVar, gnomAD, Ensembl, SpliceAI, and PubMed (plus ClinicalTrials.gov for active trials), with the ACMG/AMP rules engine applied on top of the aggregated evidence.',
  },
  {
    q: 'How current is the data?',
    a: 'Every search fetches live from each source. A cached fallback is shown only when a source is briefly unavailable, and the report flags when that happens.',
  },
]

export function Faq() {
  return (
    <section
      id="faq"
      className="py-28"
      style={{
        background: 'var(--page-bg-deep)',
        borderTop: '0.5px solid var(--page-line)',
        borderBottom: '0.5px solid var(--page-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 760 }}>
        <header className="mb-12 text-center">
          <LandingH2 className="mx-auto">Questions, answered.</LandingH2>
        </header>

        <FaqStyles />
        <div
          style={{
            background: 'var(--page-card)',
            border: '0.5px solid var(--page-line)',
            borderRadius: 14,
            overflow: 'hidden',
          }}
        >
          {ITEMS.map((item, i) => (
            <FaqRow key={item.q} item={item} last={i === ITEMS.length - 1} />
          ))}
        </div>
      </div>
    </section>
  )
}

function FaqRow({ item, last }: { item: QA; last: boolean }) {
  const [open, setOpen] = useState(false)
  const reduce = useReducedMotion()

  return (
    <div style={{ borderBottom: last ? 'none' : '0.5px solid var(--page-line)' }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="faq-row-btn flex w-full items-center justify-between gap-4 text-left"
        style={{
          padding: '20px 22px',
          background: open ? 'rgba(29,158,117,0.04)' : 'transparent',
          border: 'none',
          cursor: 'pointer',
          outline: 'none',
          transition: 'background var(--dur-1) var(--ease-standard)',
        }}
      >
        <span style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--hero-ink)' }}>{item.q}</span>
        <motion.span
          aria-hidden
          animate={reduce ? undefined : { rotate: open ? 45 : 0 }}
          transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}
          style={{ color: open ? 'var(--em-bright)' : 'var(--hero-ink-3)', flexShrink: 0, lineHeight: 0 }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={reduce ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.26, ease: [0.2, 0, 0, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <p style={{ padding: '0 22px 20px', margin: 0, fontSize: 13.5, lineHeight: 1.65, color: 'var(--hero-ink-2)' }}>
              {item.a}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
