'use client'

import posthog, { type CaptureResult } from 'posthog-js'

export const PRODUCT_DISCOVERY_EVENTS = {
  exampleSelected: 'eamos_free_example_selected',
  reportOpened: 'eamos_free_report_opened',
  workbenchOpened: 'eamos_free_workbench_opened',
  batchSampleLoaded: 'eamos_free_batch_sample_loaded',
} as const

export type LandingExampleSlot = 1 | 2 | 3

const ALLOWED_EVENTS = new Set<string>(['$pageview', ...Object.values(PRODUCT_DISCOVERY_EVENTS)])
const ALLOWED_CUSTOM_PROPERTIES: Record<string, ReadonlySet<string>> = {
  [PRODUCT_DISCOVERY_EVENTS.exampleSelected]: new Set(['example_slot']),
  [PRODUCT_DISCOVERY_EVENTS.reportOpened]: new Set(),
  [PRODUCT_DISCOVERY_EVENTS.workbenchOpened]: new Set(),
  [PRODUCT_DISCOVERY_EVENTS.batchSampleLoaded]: new Set(),
  $pageview: new Set(),
}

const URL_PROPERTY = /(?:url|href|referrer|from|to)$/i
const CAMPAIGN_PROPERTY = /^(?:\$?(?:initial_|session_entry_)?utm_|gclid|dclid|fbclid|msclkid)/i
const SENSITIVE_PROPERTY = /(?:account|cdna|email|gene|hgvs|name|query|transcript|user_id|variant)/i
const REQUIRED_INGEST_PROPERTIES = new Set(['token', 'distinct_id'])
const PERSON_MUTATION_PROPERTIES = new Set(['$set', '$set_once', '$unset', '$anon_distinct_id'])

function stripQueryAndHash(value: string): string {
  const cut = value.search(/[?#]/)
  return cut === -1 ? value : value.slice(0, cut)
}

/**
 * Final telemetry boundary. PostHog adds browser/session properties to every
 * capture call, so callers cannot guarantee privacy by omitting query data
 * alone. This hook allows only the four product-discovery events plus the
 * manual pageview, strips URL queries/hashes, rejects person mutations, and
 * removes every non-system property outside the event's tiny allowlist.
 */
export function scrubAnalyticsEvent(event: CaptureResult | null): CaptureResult | null {
  if (!event || !ALLOWED_EVENTS.has(event.event)) return null

  const allowedCustom = ALLOWED_CUSTOM_PROPERTIES[event.event] ?? new Set<string>()
  const properties = { ...event.properties }

  for (const [key, value] of Object.entries(properties)) {
    if (
      PERSON_MUTATION_PROPERTIES.has(key)
      || CAMPAIGN_PROPERTY.test(key)
      || SENSITIVE_PROPERTY.test(key)
    ) {
      delete properties[key]
      continue
    }
    if (typeof value === 'string' && URL_PROPERTY.test(key)) {
      properties[key] = stripQueryAndHash(value)
      continue
    }

    const systemProperty = key.startsWith('$') || REQUIRED_INGEST_PROPERTIES.has(key)
    if (!systemProperty && !allowedCustom.has(key)) delete properties[key]
  }

  // Person-property writes would re-link anonymous navigation to an account.
  // Drop them even if a future caller accidentally adds capture options.
  const { $set: _set, $set_once: _setOnce, $unset: _unset, ...safeEvent } = event
  return { ...safeEvent, properties }
}

function captureProductEvent(event: string, properties?: Record<string, string | number | boolean>) {
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return
  posthog.capture(event, {
    ...properties,
    $process_person_profile: false,
  })
}

export function captureExampleSelection(exampleSlot: LandingExampleSlot) {
  captureProductEvent(PRODUCT_DISCOVERY_EVENTS.exampleSelected, { example_slot: exampleSlot })
}

export function captureReportOpen() {
  captureProductEvent(PRODUCT_DISCOVERY_EVENTS.reportOpened)
}

export function captureWorkbenchOpen() {
  captureProductEvent(PRODUCT_DISCOVERY_EVENTS.workbenchOpened)
}

export function captureBatchSampleLoad() {
  captureProductEvent(PRODUCT_DISCOVERY_EVENTS.batchSampleLoaded)
}
