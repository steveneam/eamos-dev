import { describe, expect, it } from 'vitest'

import type { ReportCallCard } from '@/lib/backend'

import {
  STATE_THEME,
  callCardAccessibleLabel,
  themeForCallCard,
} from './CallCardsGrid'
import { computationalAccountingItems } from './CompositeVerdictBar'

function card(
  cardId: ReportCallCard['card_id'],
  primaryLabel: string,
  uiColorTheme: string,
): ReportCallCard {
  return {
    card_id: cardId,
    title: cardId === 'computational' ? 'Computational' : 'Evidence',
    primary_label: primaryLabel,
    support_badges: [],
    ui_color_theme: uiColorTheme,
    source_status: 'fixture',
    provenance: [],
    warnings: [],
  }
}

describe('call-card evidence ownership', () => {
  it('uses the backend computational theme even when alternate-looking copy is extreme', () => {
    const computational = card('computational', 'REVEL · Indeterminate', 'neutral_slate_state')

    expect(themeForCallCard(computational)).toBe(STATE_THEME.neutral_slate_state)
  })

  it('keeps the other evidence axes independent', () => {
    expect(
      themeForCallCard(card('clinical_consensus', 'Pathogenic', 'neutral_slate_state')),
    ).toBe(STATE_THEME.danger_red_state)
    expect(
      themeForCallCard(card('population_frequency', 'Rare', 'neutral_slate_state'), 0.02),
    ).toBe(STATE_THEME.safe_green_state)
    expect(
      themeForCallCard(card('lab_functional', 'Functional deficit', 'risk_red_state')),
    ).toBe(STATE_THEME.risk_red_state)
  })

  it('maps both benign calibrated strengths to the clinical ramp', () => {
    expect(
      themeForCallCard(card('computational', 'REVEL · BP4 Supporting', 'support_green_state')),
    ).toBe(STATE_THEME.support_green_state)
    expect(
      themeForCallCard(card('computational', 'REVEL · BP4 Moderate', 'benign_green_state')),
    ).toBe(STATE_THEME.benign_green_state)
  })

  it('announces the selected score, code, points, and source status', () => {
    const computational = card('computational', 'REVEL · PP3 Moderate', 'caution_orange_state')
    computational.support_badges = [
      { text: 'Score 0.78', kind: 'metric' },
      { text: 'PP3', kind: 'acmg' },
      { text: '+2 points', kind: 'metric' },
    ]

    expect(callCardAccessibleLabel(computational)).toBe(
      'Computational. REVEL · PP3 Moderate. Score 0.78. PP3. +2 points. fixture. Source status fixture',
    )
  })

  it('keeps visible provenance and action copy inside an interactive card name', () => {
    const population = card('population_frequency', 'Rare', 'support_green_state')
    population.provenance = ['gnomAD joint']
    population.interaction = {
      action: 'scroll_and_expand',
      target_section_id: 'population',
    }

    expect(callCardAccessibleLabel(population)).toBe(
      'Evidence. Rare. gnomAD joint. Source status fixture. View detail',
    )
  })
})

describe('computational evidence accounting', () => {
  it('renders each backend accounting clause as its own readable item', () => {
    expect(
      computationalAccountingItems(
        'REVEL counted | AlphaMissense/ESM-1b context only | SpliceAI separate mechanism',
      ),
    ).toEqual([
      'REVEL counted',
      'AlphaMissense/ESM-1b context only',
      'SpliceAI separate mechanism',
    ])
  })
})
