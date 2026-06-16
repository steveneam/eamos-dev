// Shared Sentry configuration + privacy scrubbing for the Next.js app, used by
// every runtime (client, server, edge). Env-gated: with no
// NEXT_PUBLIC_SENTRY_DSN the SDK is disabled and nothing is sent — mirrors the
// PostHog posture in app/providers.tsx.
//
// Privacy: Eamos URLs carry the queried variant (?q=GENE:c.cdna). We strip every
// query string + hash before an event leaves the client/server so the variant
// and any params never reach Sentry — matching the analytics rule that only the
// route (never the query) is transmitted.
import type { Breadcrumb, ErrorEvent } from '@sentry/nextjs'

export const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN
export const SENTRY_ENABLED = Boolean(SENTRY_DSN)

/** Drop everything from the first `?` or `#` onward, keeping origin + path. */
function stripQuery(value: string): string {
  const cut = value.search(/[?#]/)
  return cut === -1 ? value : value.slice(0, cut)
}

/** Scrub variant/PII-bearing query strings from a breadcrumb's URL fields. */
export function scrubBreadcrumb(crumb: Breadcrumb): Breadcrumb {
  const data = crumb.data
  if (data) {
    for (const key of ['url', 'from', 'to'] as const) {
      const value = data[key]
      if (typeof value === 'string') data[key] = stripQuery(value)
    }
  }
  return crumb
}

/** Scrub query strings from an event's request URL, transaction, breadcrumbs. */
export function scrubEvent(event: ErrorEvent): ErrorEvent {
  if (event.request) {
    if (event.request.url) event.request.url = stripQuery(event.request.url)
    delete event.request.query_string
  }
  if (event.transaction) event.transaction = stripQuery(event.transaction)
  event.breadcrumbs?.forEach(scrubBreadcrumb)
  return event
}

/** Options shared by every runtime's Sentry.init(). */
export const baseSentryOptions = {
  dsn: SENTRY_DSN,
  enabled: SENTRY_ENABLED,
  // Client bundles only inline NEXT_PUBLIC_* vars, so set
  // NEXT_PUBLIC_SENTRY_ENVIRONMENT in prod for correct client-side tagging.
  environment:
    process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? process.env.VERCEL_ENV ?? 'development',
  // Modest tracing — errors are the priority; keep Sentry quota/cost low.
  tracesSampleRate: 0.1,
  // Never attach cookies/headers/IP or other default PII.
  sendDefaultPii: false,
  beforeSend: scrubEvent,
  beforeBreadcrumb: scrubBreadcrumb,
}
