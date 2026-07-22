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
    q: 'What can I try before using my own data?',
    a: 'Choose any example under the search bar to open a variant report, or load the bundled sample VCF to explore Batch. The sample links work in a fresh browser and contain no account details or patient records.',
  },
  {
    q: 'Does Eamos store private patient data?',
    a: 'Eamos is designed for variant evidence, not identifiable patient records. The sample comparison starts in your browser, while saved variants and evidence submissions follow the Privacy Policy. Do not submit identifiable patient information unless you are authorised to do so.',
  },
  {
    q: 'Which databases and predictors does a search cover?',
    a: 'The current catalog includes ClinVar, gnomAD, Ensembl, PubMed, and ClinicalTrials.gov plus AlphaMissense, ESM1b, REVEL, PrimateAI-3D, MetaLR, CI-SpliceAI, SpliceAI, Pangolin, CADD, GPN-MSA, and CAPICE. Each report shows which sources returned evidence for that variant.',
  },
  {
    q: 'How does Eamos stay current as standards change?',
    a: 'Predictor scores and ACMG/AMP criteria keep their source, release, or ruleset version visible, so reviewed updates can be added without silently rewriting earlier reports. Eamos is tracking the forthcoming SVC v4 framework and ongoing ClinGen guidance; until a standard is final and activated, the current ruleset label remains visible.',
  },
  {
    q: 'Is Eamos really free?',
    a: 'Yes. Eamos is one free product with no paid tiers or checkout. Every wired source and predictor is included. If a score is missing, the report says so; it is never hidden behind an upgrade.',
  },
]

export function Faq() {
  return (
    <section
      id="faq"
      className="py-24"
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
