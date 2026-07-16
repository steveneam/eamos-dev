'use client'
import { useState, type ReactNode } from 'react'
import { CarouselDots } from '@/components/ui/CarouselDots'
import { EvidenceChip } from '@/components/ui/EvidenceChip'
import type { ReportCallBadgeKind, ReportCallCard, ReportPayload } from '@/lib/backend'
import { visibleProductWarnings } from '@/lib/product-warnings'

interface CallCardsGridProps {
  payload: ReportPayload
  /** Joint AF (gnomAD) — used to colour the Population card by its frequency
   *  band, since the backend currently emits a neutral theme for it. */
  populationAf?: number | null
}

// AF → verdict-state for the Population card, mirroring the §3 thermometer:
// BA1/BS1 (≥1%) benign-green, 0.1–1% intermediate yellow, <0.1% / absent →
// PM2-supporting (orange/lpath). Absence is suggestive, not diagnostic — never red.
function afToState(af: number): string {
  if (af >= 0.01) return 'safe_green_state'
  if (af >= 0.001) return 'caution_yellow_state'
  return 'caution_orange_state'
}

// Verdict label → ACMG-ramp state for the Computational + Clinical cards, so each
// is coloured by its OWN call (VUS → yellow, Pathogenic → red, Likely path →
// orange, Benign → green) instead of whatever theme the backend happens to send.
// One ramp shared with the hero badge + §1-§3, so a clinician reads colour + word
// + dot consistently down the whole report. No-data / N/A returns null and the
// card falls back to the neutral backend theme. (Order matters: the more specific
// "likely …" cases are tested before the bare tier.)
function verdictToState(label: string | null | undefined): string | null {
  const l = (label ?? '').toLowerCase()
  if (!l || l.includes('no ') || l.includes('unavailable') || l.includes('not applicable')) return null
  if (l.includes('conflict')) return 'neutral_slate_state'
  if (l.includes('uncertain') || l.includes('vus')) return 'caution_yellow_state'
  if (l.includes('likely pathogenic')) return 'caution_orange_state'
  if (l.includes('pathogenic')) return 'danger_red_state'
  if (l.includes('benign') || l.includes('tolerated')) return 'safe_green_state'
  if (l.includes('damaging') || l.includes('deleterious')) return 'caution_orange_state'
  return null
}

const BADGE_TONES: Record<ReportCallBadgeKind, { bg: string; border: string; color: string }> = {
  acmg: { bg: 'var(--teal-tint)', border: 'var(--teal-bdr)', color: 'var(--teal-deep)' },
  metric: { bg: 'var(--bg-soft)', border: 'var(--line)', color: 'var(--ink-2)' },
  source: { bg: 'var(--bg-soft2)', border: 'var(--line-2)', color: 'var(--ink-2)' },
  warning: { bg: 'var(--warn-tint)', border: 'var(--warn-bdr)', color: 'var(--warn-text)' },
  neutral: { bg: 'var(--bg-soft)', border: 'var(--line)', color: 'var(--ink-3)' },
}

// Functional-evidence state → badge colour. The Lab & Functional verdict badge
// is coloured by the functional STATE (curator's PS3/BS3 direction, conflict,
// uncurated, or none) rather than the generic "acmg" teal, so a clinician reads
// the wet-lab call at a glance. Maps onto the design-system ACMG ramp + grey NA,
// plus the off-ramp info-blue for "uncurated". See plans/functional-card/spec.md.
// Verdict-state → card theme. v3 applies this to ALL FOUR cards (was functional-
// only) so each evidence axis is read at a glance by colour + word + dot. Covers
// all 7 backend states; `caution_orange_state` (e.g. the clinical card) maps onto
// the likely-pathogenic ramp (orange, leaning-risk) — a missing key here silently
// renders a white card.
export const STATE_THEME: Record<string, { bg: string; border: string; color: string }> = {
  danger_red_state: { bg: 'var(--cls-path-bg)', border: 'var(--cls-path-bdr)', color: 'var(--cls-path-text)' },
  risk_red_state: { bg: 'var(--cls-lpath-bg)', border: 'var(--cls-lpath-bdr)', color: 'var(--cls-lpath-text)' },
  caution_orange_state: { bg: 'var(--cls-lpath-bg)', border: 'var(--cls-lpath-bdr)', color: 'var(--cls-lpath-text)' },
  caution_yellow_state: { bg: 'var(--cls-vus-bg)', border: 'var(--cls-vus-bdr)', color: 'var(--cls-vus-text)' },
  safe_green_state: { bg: 'var(--cls-ben-bg)', border: 'var(--cls-ben-bdr)', color: 'var(--cls-ben-text)' },
  info_blue_state: { bg: 'var(--info-bg)', border: 'var(--info-bdr)', color: 'var(--info-text)' },
  neutral_slate_state: { bg: 'var(--cls-na-bg)', border: 'var(--cls-na-bdr)', color: 'var(--cls-na-text)' },
}

export type ReportCallCardTheme = { bg: string; border: string; color: string }

export function themeForCallCard(
  card: ReportCallCard,
  populationAf?: number | null,
): ReportCallCardTheme | null {
  const backendTheme = STATE_THEME[card.ui_color_theme] ?? null
  if (card.card_id === 'population_frequency' && populationAf != null) {
    return STATE_THEME[afToState(populationAf)] ?? backendTheme
  }
  if (card.card_id === 'computational' || card.card_id === 'clinical_consensus') {
    const derived = verdictToState(card.primary_label)
    if (derived) return STATE_THEME[derived] ?? backendTheme
  }
  return backendTheme
}

// Locked L→R display order (Computational · Clinical · Population · Lab &
// Functional). The backend payload array order is not guaranteed, so the FE
// sorts deterministically; unknown ids sort last.
export const CARD_ORDER: string[] = [
  'computational',
  'clinical_consensus',
  'population_frequency',
  'lab_functional',
]

// Plain-language hover help per card (intuitiveness pass) — explains what the
// axis means, not just the label.
const CARD_TOOLTIP: Record<string, string> = {
  computational:
    "Eamos's combined call from the in-silico predictors (REVEL, CADD, SpliceAI, …). 'Damaging' means the tools agree the change is likely harmful to the protein.",
  clinical_consensus:
    'The clinical classification (ACMG / ClinGen / ClinVar): Pathogenic through Benign, or VUS when the evidence is uncertain.',
  population_frequency:
    'How common this variant is in the general population (gnomAD). Common variants are usually benign; very rare or absent variants can support a pathogenic call.',
  lab_functional:
    "What wet-lab experiments show about the variant's effect on protein function, and who curated that evidence (ClinGen / ClinVar).",
}

// "via ClinGen / ClinVar / ClinGen + ClinVar" — the authority of a PS3/BS3 hinges
// on whether a VCEP or a lone submitter asserted it, so the verdict badge always
// names its curator source. Conflict / uncurated / none carry no curator code and
// so get no attribution.
function verdictAttribution(verdictSource: string | undefined): string | null {
  switch (verdictSource) {
    case 'clingen':
      return 'via ClinGen'
    case 'clinvar':
      return 'via ClinVar'
    case 'clingen+clinvar':
      return 'via ClinGen + ClinVar'
    default:
      return null
  }
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

function cardMeta(card: ReportCallCard): string {
  const provenance = card.provenance ?? []
  if (provenance.length > 0) return provenance.slice(0, 2).join(' | ')
  return card.source_status ? formatWarning(card.source_status) : 'Source status unavailable'
}

export function CallCardsGrid({ payload, populationAf }: CallCardsGridProps) {
  const cards = [...(payload.call_cards?.cards ?? [])].sort(
    (a, b) => {
      const ai = CARD_ORDER.indexOf(a.card_id)
      const bi = CARD_ORDER.indexOf(b.card_id)
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
    },
  )
  if (cards.length === 0) return null

  return (
    <section aria-label="Variant evidence call cards" className="mb-4">
      {/* Mobile: horizontal swipe carousel (peek next card). sm: 2-up grid.
          lg+: all four across. */}
      <div id="call-cards-scroller" className="flex snap-x snap-mandatory items-stretch gap-3 overflow-x-auto pb-3 sm:grid sm:grid-cols-2 sm:gap-3 sm:overflow-visible sm:pb-0 lg:grid-cols-4">
        {cards.map((card) => {
          const navigates = cardCanNavigate(card)
          const badges = card.support_badges ?? []
          const cardWarnings = visibleProductWarnings(card.warnings)
          // Lab & Functional is colour-coded by functional STATE across the WHOLE
          // card surface (scan the report, read the wet-lab call at a glance):
          // red deficit / green normal / yellow conflict / blue uncurated / grey
          // none. The verdict badge also names its curator source ("via ClinGen/
          // ClinVar") and a "code rests on N of M studies" micro-note surfaces when
          // the count dwarfs the cited papers. Source attribution + note come from
          // functional_evidence.display_metrics, which the generic ReportCallCard
          // contract doesn't carry. plans/functional-card/spec.md.
          const isFunctionalCard = card.card_id === 'lab_functional'
          // v3: colour EVERY card by its verdict-state (was functional-only). The
          // functional card additionally carries display_metrics extras below.
          // Population is re-derived from the AF band (backend emits neutral today).
          // Colour every card by its own verdict, on one FE-owned ramp:
          //   • Population  → AF band (afToState)
          //   • Computational / Clinical → classification label (verdictToState)
          //   • Functional  → backend display_metrics state (kept; richest signal)
          // Each falls back to the backend theme when it can't derive one.
          const cardTheme = themeForCallCard(card, populationAf)
          const fnMetrics = isFunctionalCard
            ? payload.functional_evidence?.display_metrics ?? null
            : null
          const verdictAttr = verdictAttribution(fnMetrics?.verdict_source)
          const cardHelp = CARD_TOOLTIP[card.card_id] ?? null
          // On a state-tinted card the badges become crisp chips on the page-white
          // surface so they stay legible: the verdict chip keeps the state colour
          // (text + border), the rest go neutral.
          const renderBadges = badges.slice(0, 3).map((badge, i) => {
            let tone = BADGE_TONES[badge.kind] ?? BADGE_TONES.neutral
            if (cardTheme) {
              tone =
                i === 0
                  ? { bg: 'var(--bg)', border: cardTheme.border, color: cardTheme.color }
                  : { bg: 'var(--bg)', border: 'var(--line)', color: 'var(--ink-2)' }
            }
            const text =
              cardTheme && i === 0 && verdictAttr ? `${badge.text} · ${verdictAttr}` : badge.text
            return { key: `${card.card_id}-${i}`, text, tone }
          })
          const fnNote =
            fnMetrics?.code_rests_on != null
              ? `Code rests on ${fnMetrics.code_rests_on.cited} of ${fnMetrics.code_rests_on.total} studies`
              : null
          const cardBody = (
            <>
              <div
                className="eamos-kicker"
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                title={cardHelp ?? undefined}
              >
                <span
                  aria-hidden
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 999,
                    flexShrink: 0,
                    background: cardTheme ? cardTheme.color : 'var(--ink-5)',
                  }}
                />
                {card.title}
              </div>
              <div
                style={{
                  marginTop: 10,
                  minHeight: 50,
                  fontFamily: 'var(--display)',
                  fontSize: 18,
                  fontWeight: 400,
                  lineHeight: 1.15,
                  color: 'var(--ink)',
                }}
              >
                {card.primary_label || 'No source data'}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {renderBadges.length > 0 ? (
                  renderBadges.map((badge) => (
                    <EvidenceChip
                      key={badge.key}
                      size="sm"
                      shape="rect"
                      tone={{ bg: badge.tone.bg, border: badge.tone.border, text: badge.tone.color }}
                    >
                      {badge.text}
                    </EvidenceChip>
                  ))
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
                {cardWarnings.length > 0
                  ? formatWarning(cardWarnings[0])
                  : fnNote ?? cardMeta(card)}
              </div>
            </>
          )

          if (!navigates) {
            return (
              <article
                key={card.card_id}
                className="w-[72vw] max-w-[250px] shrink-0 snap-center sm:w-auto sm:max-w-none"
                aria-label={`${card.title}: ${card.primary_label ?? 'no data'}`}
                title={cardHelp ?? undefined}
                style={{
                  minHeight: 158,
                  border: `0.5px solid ${cardTheme ? cardTheme.border : 'var(--line)'}`,
                  borderRadius: 'var(--r-md)',
                  background: cardTheme ? cardTheme.bg : 'var(--bg)',
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
              theme={cardTheme}
              help={cardHelp}
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
  theme: { bg: string; border: string; color: string } | null
  help: string | null
  onNavigate: () => void
}

function InteractiveCard({ card, cardBody, theme, help, onNavigate }: InteractiveCardProps) {
  const [hovered, setHovered] = useState(false)
  const label = `${card.title}: ${card.primary_label ?? 'view detail'}`
  return (
    <button
      type="button"
      onClick={onNavigate}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={label}
      title={help ?? undefined}
      className="call-card-btn w-[72vw] max-w-[250px] shrink-0 snap-center sm:w-auto sm:max-w-none"
      style={{
        minHeight: 158,
        border: `0.5px solid ${hovered ? 'var(--ink-5)' : theme ? theme.border : 'var(--line)'}`,
        borderRadius: 'var(--r-md)',
        background: theme ? theme.bg : 'var(--bg)',
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
