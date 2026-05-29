'use client'
import { useState, type ReactNode } from 'react'
import { CarouselDots } from '@/components/ui/CarouselDots'
import type { ReportCallBadgeKind, ReportCallCard, ReportPayload } from '@/lib/backend'

interface CallCardsGridProps {
  payload: ReportPayload
}

const BADGE_TONES: Record<ReportCallBadgeKind, { bg: string; border: string; color: string }> = {
  acmg: { bg: 'var(--teal-tint)', border: 'var(--teal-bdr)', color: 'var(--teal-deep)' },
  metric: { bg: 'var(--bg-soft)', border: 'var(--line)', color: 'var(--ink-2)' },
  source: { bg: 'var(--bg-soft2)', border: 'var(--line-2)', color: 'var(--ink-2)' },
  warning: { bg: 'var(--warn-tint)', border: 'var(--warn-bdr)', color: 'var(--warn-text)' },
  neutral: { bg: 'var(--bg-soft)', border: 'var(--line)', color: 'var(--ink-3)' },
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

// Sticky TopNav is 60px; leave a small breathing buffer so the target heading
// lands just below the nav, not under it.
const SCROLL_OFFSET = 68

function scrollToInteraction(card: ReportCallCard) {
  const targetId = card.interaction?.target_panel_id ?? card.interaction?.target_section_id
  if (!targetId || typeof document === 'undefined') return
  const el = document.getElementById(targetId)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - SCROLL_OFFSET
  window.scrollTo({ top, behavior: 'smooth' })
}

function cardCanNavigate(card: ReportCallCard): boolean {
  return Boolean(
    card.interaction &&
      card.interaction.action !== 'none' &&
      (card.interaction.target_panel_id || card.interaction.target_section_id),
  )
}

// Warning codes that should never surface in the rendered UI.
const SUPPRESSED_WARNINGS = new Set(['alphamissense_on_hold'])

function cardMeta(card: ReportCallCard): string {
  const provenance = card.provenance ?? []
  if (provenance.length > 0) return provenance.slice(0, 2).join(' | ')
  return card.source_status ? formatWarning(card.source_status) : 'Source status unavailable'
}

export function CallCardsGrid({ payload }: CallCardsGridProps) {
  const cards = payload.call_cards?.cards ?? []
  if (cards.length === 0) return null

  return (
    <section aria-label="Variant evidence call cards" className="mb-4">
      {/* Mobile: horizontal swipe carousel (peek next card). sm: 2-up grid.
          lg+: all four across. */}
      <div id="call-cards-scroller" className="flex snap-x snap-mandatory items-stretch gap-3 overflow-x-auto pb-3 sm:grid sm:grid-cols-2 sm:gap-3 sm:overflow-visible sm:pb-0 lg:grid-cols-4">
        {cards.map((card) => {
          const navigates = cardCanNavigate(card)
          const badges = card.support_badges ?? []
          const cardWarnings = (card.warnings ?? []).filter((w) => !SUPPRESSED_WARNINGS.has(w))
          const cardBody = (
            <>
              <div className="eamos-kicker">
                {card.title}
              </div>
              <div
                style={{
                  marginTop: 10,
                  minHeight: 50,
                  fontFamily: 'var(--display)',
                  fontSize: 18,
                  fontWeight: 600,
                  lineHeight: 1.15,
                  color: 'var(--ink)',
                }}
              >
                {card.primary_label || 'No source data'}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {badges.length > 0 ? (
                  badges.slice(0, 3).map((badge) => {
                    const tone = BADGE_TONES[badge.kind] ?? BADGE_TONES.neutral
                    return (
                      <span
                        key={`${card.card_id}-${badge.text}`}
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
                        {badge.text}
                      </span>
                    )
                  })
                ) : (
                  <span
                    style={{
                      color: 'var(--ink-4)',
                      fontSize: 11,
                    }}
                  >
                    No badges reported
                  </span>
                )}
              </div>
              <div
                style={{
                  marginTop: 12,
                  minHeight: 28,
                  fontSize: 10.5,
                  lineHeight: 1.35,
                  color: cardWarnings.length > 0 ? 'var(--warn-text)' : 'var(--ink-4)',
                  overflowWrap: 'anywhere',
                }}
              >
                {cardWarnings.length > 0 ? formatWarning(cardWarnings[0]) : cardMeta(card)}
              </div>
            </>
          )

          if (!navigates) {
            return (
              <article
                key={card.card_id}
                className="w-[72vw] max-w-[250px] shrink-0 snap-center sm:w-auto sm:max-w-none"
                style={{
                  minHeight: 158,
                  border: '0.5px solid var(--line)',
                  borderRadius: 10,
                  background: 'var(--bg)',
                  padding: '15px 16px',
                  boxShadow: 'var(--elev-1)',
                }}
              >
                {cardBody}
              </article>
            )
          }

          return (
            <InteractiveCard
              key={card.card_id}
              card={card}
              cardBody={cardBody}
              onNavigate={() => scrollToInteraction(card)}
            />
          )
        })}
      </div>
      <CarouselDots containerId="call-cards-scroller" tone="light" className="mt-3 sm:hidden" />
    </section>
  )
}

interface InteractiveCardProps {
  card: ReportCallCard
  cardBody: ReactNode
  onNavigate: () => void
}

function InteractiveCard({ card, cardBody, onNavigate }: InteractiveCardProps) {
  const [hovered, setHovered] = useState(false)
  const label = `${card.title}: ${card.primary_label ?? 'view detail'}`
  return (
    <button
      type="button"
      onClick={onNavigate}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={label}
      className="call-card-btn w-[72vw] max-w-[250px] shrink-0 snap-center sm:w-auto sm:max-w-none"
      style={{
        minHeight: 158,
        border: `0.5px solid ${hovered ? 'var(--ink-5)' : 'var(--line)'}`,
        borderRadius: 10,
        background: 'var(--bg)',
        padding: '15px 16px',
        textAlign: 'left',
        cursor: 'pointer',
        boxShadow: hovered ? 'var(--elev-2)' : 'var(--elev-1)',
        transition: `box-shadow var(--dur-2) var(--ease-standard), border-color var(--dur-2) var(--ease-standard)`,
      }}
    >
      {cardBody}
      <span
        className="mt-3 inline-flex"
        style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--teal-deep)' }}
        aria-hidden
      >
        View detail
      </span>
      <style>{`
        .call-card-btn:focus-visible {
          outline: none;
          box-shadow: 0 0 0 3px rgba(29,158,117,0.14), var(--elev-2) !important;
          border-color: var(--teal) !important;
        }
        .call-card-btn:active {
          transform: scale(0.985);
          transition-duration: 80ms;
        }
      `}</style>
    </button>
  )
}
