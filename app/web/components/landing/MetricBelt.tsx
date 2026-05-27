'use client'

/**
 * Specimen strip — the "open page" of an Eamos variant report on the landing.
 *
 * Drives off the SAME report payload the live `CallCardsGrid` consumes
 * (`RPE65_SAMPLE.report_payload.call_cards.cards`), captured verbatim from a
 * real RPE65 c.260A>G lookup on eamos-dev. The cream landing is the journal
 * cover; this inset is an open page from inside.
 *
 * Static (compile-time JSON import) but no longer hand-crafted: any change to
 * the call-card backend now flows through here automatically.
 */

import { LandingH2 } from '@/components/landing/ui/LandingHeading'
import { RPE65_SAMPLE } from '@/lib/sample-report'
import type { ReportCallBadgeKind, ReportCallCard } from '@/lib/backend'

const BADGE_TONES: Record<ReportCallBadgeKind, { bg: string; border: string; color: string }> = {
  acmg:    { bg: 'var(--teal-tint)',   border: '#cbe3d8', color: 'var(--teal-deep)' },
  metric:  { bg: 'var(--bg-soft)',     border: 'var(--line)', color: 'var(--ink-2)' },
  source:  { bg: '#eef6ff',            border: '#c9ddf5', color: '#1d4f7a' },
  warning: { bg: 'var(--warn-tint)',   border: 'var(--warn-bdr)', color: '#633806' },
  neutral: { bg: 'var(--bg-soft)',     border: 'var(--line)', color: 'var(--ink-3)' },
}

// Mirror CallCardsGrid's policy. AlphaMissense is hidden per project policy
// ([[project_alphamissense_plan]]) — its warning surfaces here too if backend
// emits it, so suppress at render.
const SUPPRESSED_WARNINGS = new Set(['alphamissense_on_hold'])

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function cardMeta(card: ReportCallCard): string {
  const provenance = card.provenance ?? []
  if (provenance.length > 0) return provenance.slice(0, 2).join(' · ')
  return card.source_status ? formatWarning(card.source_status) : 'Source status unavailable'
}

export function MetricBelt() {
  const payload = RPE65_SAMPLE.report_payload
  const cards: ReportCallCard[] = payload.call_cards?.cards ?? []
  const header = payload.variant_summary_rows[0] ?? null

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
            Four call cards at the top of every report: clinical consensus, population
            frequency, computational, functional. Each citing the source it came from.
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
              Live demo · sourced
            </span>
          </div>

          {/* Four call cards — same min-height + tone + badge map as the live grid. */}
          <div
            className="grid grid-cols-1 gap-px sm:grid-cols-2 lg:grid-cols-4"
            style={{ background: 'var(--line)' }}
          >
            {cards.map((card) => {
              const visibleWarnings = (card.warnings ?? []).filter(
                (w) => !SUPPRESSED_WARNINGS.has(w),
              )
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
                  <div
                    className="uppercase"
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: '0.08em',
                      color: 'var(--ink-4)',
                    }}
                  >
                    {card.title}
                  </div>
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
          Captured from a live RPE65 c.260A&gt;G lookup · every value cites its source
          (ClinVar · gnomAD v4 · SpliceAI · REVEL · ClinGen · PubMed).
        </p>
      </div>
    </section>
  )
}
