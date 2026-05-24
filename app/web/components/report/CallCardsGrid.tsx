import type { ReportCallBadgeKind, ReportCallCard, ReportPayload } from '@/lib/backend'

interface CallCardsGridProps {
  payload: ReportPayload
}

const BADGE_TONES: Record<ReportCallBadgeKind, { bg: string; border: string; color: string }> = {
  acmg: { bg: 'var(--teal-tint)', border: '#cbe3d8', color: 'var(--teal-deep)' },
  metric: { bg: 'var(--bg-soft)', border: 'var(--line)', color: 'var(--ink-2)' },
  source: { bg: '#eef6ff', border: '#c9ddf5', color: '#1d4f7a' },
  warning: { bg: 'var(--warn-tint)', border: 'var(--warn-bdr)', color: '#633806' },
  neutral: { bg: 'var(--bg-soft)', border: 'var(--line)', color: 'var(--ink-3)' },
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function scrollToInteraction(card: ReportCallCard) {
  const targetId = card.interaction?.target_panel_id ?? card.interaction?.target_section_id
  if (!targetId || typeof document === 'undefined') return
  document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function cardCanNavigate(card: ReportCallCard): boolean {
  return Boolean(
    card.interaction &&
      card.interaction.action !== 'none' &&
      (card.interaction.target_panel_id || card.interaction.target_section_id),
  )
}

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
      <div className="flex snap-x snap-mandatory items-stretch gap-3 overflow-x-auto pb-3 sm:grid sm:grid-cols-2 sm:gap-3 sm:overflow-visible sm:pb-0 lg:grid-cols-4">
        {cards.map((card) => {
          const navigates = cardCanNavigate(card)
          const badges = card.support_badges ?? []
          const cardWarnings = card.warnings ?? []
          const cardBody = (
            <>
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
                  minHeight: 50,
                  fontFamily: 'var(--display)',
                  fontSize: 18,
                  fontWeight: 650,
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
                  color: cardWarnings.length > 0 ? '#7a4b10' : 'var(--ink-4)',
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
                }}
              >
                {cardBody}
              </article>
            )
          }

          return (
            <button
              key={card.card_id}
              type="button"
              onClick={() => scrollToInteraction(card)}
              className="w-[72vw] max-w-[250px] shrink-0 snap-center sm:w-auto sm:max-w-none"
              style={{
                minHeight: 158,
                border: '0.5px solid var(--line)',
                borderRadius: 10,
                background: 'var(--bg)',
                padding: '15px 16px',
                textAlign: 'left',
                cursor: 'pointer',
              }}
            >
              {cardBody}
              <span
                className="mt-3 inline-flex"
                style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--teal-deep)' }}
              >
                View detail
              </span>
            </button>
          )
        })}
      </div>
      <p
        className="mt-2 text-center sm:hidden"
        style={{ fontSize: 10.5, color: 'var(--ink-4)' }}
      >
        Swipe for more →
      </p>
    </section>
  )
}
