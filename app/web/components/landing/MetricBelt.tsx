'use client'

/**
 * Specimen strip — the "open page" of an Eamos variant report on the landing.
 *
 * Documented USH2A c.2276G>T lookup snapshot captured on 2026-06-01.
 * Population facts are independently recorded by the Eamos press truth-printer
 * contract. The cream landing is the journal cover; this inset is an open page.
 */

import { LandingH2 } from '@/components/landing/ui/LandingHeading'
import { LandingEyebrow } from '@/components/landing/ui/LandingEyebrow'
import type { ReportCallBadgeKind, ReportCallCard } from '@/lib/backend'
import { visibleProductWarnings } from '@/lib/product-warnings'

type SpecimenCard = Pick<
  ReportCallCard,
  'card_id' | 'title' | 'primary_label' | 'support_badges' | 'warnings' | 'provenance' | 'source_status'
>

const SPECIMEN_HEADER = {
  gene: 'USH2A',
  transcript_hgvs: 'c.2276G>T',
  protein_change: null,
  genomic_hg38: '1-216247118-C-A',
}

const SPECIMEN_CARDS: SpecimenCard[] = [
  {
    card_id: 'clinical_consensus',
    title: 'Clinical Consensus',
    primary_label: 'Pathogenic',
    support_badges: [
      { kind: 'source', text: 'ClinGen/VCEP' },
      { kind: 'source', text: 'Expert panel' },
    ],
    provenance: ['ClinGen', 'ClinVar'],
    source_status: 'cache',
    warnings: [],
  },
  {
    card_id: 'population_frequency',
    title: 'Population Frequency',
    primary_label: 'Max AF 0.182%',
    support_badges: [
      { kind: 'metric', text: 'AMR maximum' },
      { kind: 'metric', text: 'AC 2,357' },
      { kind: 'source', text: 'gnomAD v4' },
    ],
    provenance: ['gnomAD v4'],
    source_status: 'cache',
    warnings: [],
  },
  {
    card_id: 'computational',
    title: 'Computational',
    primary_label: 'No Computational Data',
    support_badges: [{ kind: 'warning', text: 'Missing source' }],
    provenance: [],
    source_status: 'missing',
    warnings: ['computational_annotations_not_found'],
  },
  {
    card_id: 'lab_functional',
    title: 'Lab & Functional',
    primary_label: 'PS3 Supporting',
    support_badges: [
      { kind: 'acmg', text: 'Source assertion' },
      { kind: 'source', text: 'Functional evidence' },
    ],
    provenance: ['functional evidence'],
    source_status: 'cache',
    warnings: [],
  },
]

const BADGE_TONES: Record<ReportCallBadgeKind, { bg: string; border: string; color: string }> = {
  acmg:    { bg: 'var(--teal-tint)',   border: 'var(--teal-bdr)', color: 'var(--teal-deep)' },
  metric:  { bg: 'var(--bg-soft)',     border: 'var(--line)', color: 'var(--ink-2)' },
  source:  { bg: 'var(--info-bg)',     border: 'var(--info-bdr)', color: 'var(--info-text)' },
  warning: { bg: 'var(--warn-tint)',   border: 'var(--warn-bdr)', color: 'var(--warn-text)' },
  neutral: { bg: 'var(--bg-soft)',     border: 'var(--line)', color: 'var(--ink-3)' },
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function cardMeta(card: SpecimenCard): string {
  const provenance = card.provenance ?? []
  if (provenance.length > 0) return provenance.slice(0, 2).join(' · ')
  return card.source_status ? formatWarning(card.source_status) : 'Source status unavailable'
}

export function MetricBelt() {
  const cards = SPECIMEN_CARDS
  const header = SPECIMEN_HEADER

  if (cards.length === 0) return null

  return (
    <section
      aria-label="A specimen of an Eamos variant report"
      className="py-28"
      style={{
        background: 'var(--page-bg)',
        borderTop: '0.5px solid var(--page-line)',
        borderBottom: '0.5px solid var(--page-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-10 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div style={{ maxWidth: 560 }}>
            <LandingH2>How the evidence reads.</LandingH2>
          </div>
          <p
            className="md:max-w-[380px] md:text-right"
            style={{ fontSize: 13.5, lineHeight: 1.55, color: 'var(--hero-ink-2)' }}
          >
            The report opens with four call cards: clinical consensus, population frequency,
            computational, and functional. Provenance or source status stays visible on each.
          </p>
        </header>

        {/* The "open page" — a warm-white inset, like opening a paper journal on a desk. */}
        <div
          className="overflow-hidden"
          style={{
            background: 'var(--bg)',
            border: '0.5px solid var(--line)',
            borderRadius: 14,
            boxShadow: '0 1px 0 rgba(0,0,0,0.02), 0 12px 32px -16px rgba(0,0,0,0.12)',
          }}
        >
          {/* Specimen variant header — same shape as VariantHeader, abbreviated. */}
          <div
            className="flex flex-wrap items-baseline gap-x-5 gap-y-1"
            style={{
              padding: '20px 24px 16px',
              borderBottom: '0.5px solid var(--line)',
            }}
          >
            {header?.transcript_hgvs && (
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 13,
                  fontWeight: 500,
                  letterSpacing: '0.01em',
                  color: 'var(--ink-3)',
                }}
              >
                {header.transcript_hgvs}
              </span>
            )}
            {header?.gene && (
              <span
                style={{
                  fontFamily: 'var(--display)',
                  fontSize: 19,
                  fontWeight: 500,
                  letterSpacing: '-0.01em',
                  color: 'var(--ink)',
                }}
              >
                {header.gene}
                {header.protein_change && (
                  <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>
                    {' · '}
                    {header.protein_change}
                  </span>
                )}
              </span>
            )}
            {header?.genomic_hg38 && (
              <span style={{ fontSize: 12, color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>
                {header.genomic_hg38}
              </span>
            )}
            <span className="ml-auto" style={{ fontSize: 11, color: 'var(--ink-4)' }}>
              Static snapshot · source states shown
            </span>
          </div>

          {/* Four call cards — same min-height + tone + badge map as the live grid. */}
          <div
            className="grid grid-cols-1 gap-px sm:grid-cols-2 lg:grid-cols-4"
            style={{ background: 'var(--line)' }}
          >
            {cards.map((card) => {
              const visibleWarnings = visibleProductWarnings(card.warnings)
              const badges = (card.support_badges ?? []).slice(0, 3)
              return (
                <article
                  key={card.card_id}
                  style={{
                    background: 'var(--bg)',
                    padding: '18px 18px 20px',
                    minHeight: 168,
                  }}
                >
                  <LandingEyebrow style={{ display: 'block', color: 'var(--ink-4)' }}>
                    {card.title}
                  </LandingEyebrow>
                  <div
                    style={{
                      marginTop: 10,
                      fontFamily: 'var(--display)',
                      fontSize: 19,
                      fontWeight: 500,
                      lineHeight: 1.18,
                      letterSpacing: '-0.01em',
                      color: 'var(--ink)',
                    }}
                  >
                    {card.primary_label || 'No source data'}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {badges.length > 0 ? (
                      badges.map((b) => {
                        const tone = BADGE_TONES[b.kind] ?? BADGE_TONES.neutral
                        return (
                          <span
                            key={`${card.card_id}-${b.text}`}
                            style={{
                              border: `0.5px solid ${tone.border}`,
                              background: tone.bg,
                              color: tone.color,
                              borderRadius: 7,
                              padding: '4px 7px',
                              fontSize: 10.5,
                              fontWeight: 700,
                              fontVariantNumeric: 'tabular-nums',
                              lineHeight: 1.15,
                              overflowWrap: 'anywhere',
                            }}
                          >
                            {b.text}
                          </span>
                        )
                      })
                    ) : (
                      <span style={{ color: 'var(--ink-4)', fontSize: 11 }}>
                        No badges reported
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      marginTop: 12,
                      fontSize: 10.5,
                      lineHeight: 1.4,
                      color: visibleWarnings.length > 0 ? '#7a4b10' : 'var(--ink-4)',
                      overflowWrap: 'anywhere',
                    }}
                  >
                    {visibleWarnings.length > 0
                      ? formatWarning(visibleWarnings[0])
                      : cardMeta(card)}
                  </div>
                </article>
              )
            })}
          </div>
        </div>

        <p className="mt-5 text-[11.5px]" style={{ color: 'var(--hero-ink-3)' }}>
          Static USH2A c.2276G&gt;T lookup snapshot captured 1 June 2026 · raw population facts
          are shown without a rarity verdict, with cached and missing states visible.
        </p>
      </div>
    </section>
  )
}
