import type { CaptureResult } from 'posthog-js'
import { describe, expect, it } from 'vitest'

import { PRODUCT_DISCOVERY_EVENTS, scrubAnalyticsEvent } from './product-analytics'

function event(name: string, properties: CaptureResult['properties']): CaptureResult {
  return {
    uuid: '00000000-0000-4000-8000-000000000001',
    event: name,
    properties,
  }
}

describe('scrubAnalyticsEvent', () => {
  it('keeps only a fixed example slot and strips every URL query or identity lead', () => {
    const scrubbed = scrubAnalyticsEvent({
      ...event(PRODUCT_DISCOVERY_EVENTS.exampleSelected, {
        token: 'public-project-key',
        distinct_id: 'anonymous-device',
        example_slot: 2,
        query: 'USH2A c.2276G>T',
        gene: 'USH2A',
        arbitrary_note: 'must not leave the browser',
        $current_url: 'https://eamos.com.au/report?gene=USH2A&cdna=c.2276G%3ET#section',
        $session_entry_url: 'https://eamos.com.au/?q=RPE65+c.260A%3EG',
        $referrer: 'https://search.example/?q=genomic+query',
        $set: { email: 'person@example.test' },
        $anon_distinct_id: 'previous-account-link',
        utm_content: 'RPE65 c.260A>G',
      }),
      $set: { email: 'person@example.test' },
      $set_once: { account_name: 'Example' },
    })

    expect(scrubbed).toEqual(
      expect.objectContaining({
        event: PRODUCT_DISCOVERY_EVENTS.exampleSelected,
        properties: {
          token: 'public-project-key',
          distinct_id: 'anonymous-device',
          example_slot: 2,
          $current_url: 'https://eamos.com.au/report',
          $session_entry_url: 'https://eamos.com.au/',
          $referrer: 'https://search.example/',
        },
      }),
    )
    expect(scrubbed).not.toHaveProperty('$set')
    expect(scrubbed).not.toHaveProperty('$set_once')
  })

  it('preserves a route-only manual pageview and drops unexpected events', () => {
    const pageview = scrubAnalyticsEvent(
      event('$pageview', {
        token: 'public-project-key',
        distinct_id: 'anonymous-device',
        $current_url: 'https://eamos.com.au/workbench?gene=RPE65&cdna=c.260A%3EG',
        title: 'Rendered report content',
      }),
    )

    expect(pageview?.properties).toEqual({
      token: 'public-project-key',
      distinct_id: 'anonymous-device',
      $current_url: 'https://eamos.com.au/workbench',
    })
    expect(scrubAnalyticsEvent(event('$autocapture', { token: 'public-project-key' }))).toBeNull()
  })
})
