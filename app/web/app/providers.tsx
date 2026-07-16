'use client'
import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import { Suspense, useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { AuthProvider } from '@/components/auth/AuthProvider'
import { LibrarySync } from '@/components/library/LibrarySync'
import { scrubAnalyticsEvent } from '@/lib/product-analytics'

export function Providers({ children }: { children: React.ReactNode }) {
  // Initialize PostHog once, inside the React lifecycle. Env-gated: with no
  // NEXT_PUBLIC_POSTHOG_KEY this is a no-op and nothing is sent.
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return
    if ((posthog as unknown as { __loaded?: boolean }).__loaded) return
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
      // First-party reverse proxy (next.config.mjs rewrites /ingest/* → PostHog
      // US cloud) so ad/tracking blockers don't drop events. ui_host is the real
      // host for toolbar/links.
      api_host: '/ingest',
      ui_host: 'https://us.posthog.com',
      // App Router does full pageviews only on first load; captured manually below.
      capture_pageview: false,
      // Genomic query strings and rendered report text must never reach
      // analytics implicitly. Keep telemetry to the explicit route-only event
      // below; product interactions can add named, content-free events later.
      capture_pageleave: false,
      autocapture: false,
      disable_session_recording: true,
      disable_surveys: true,
      disable_external_dependency_loading: true,
      advanced_disable_flags: true,
      // Aggregate product discovery only. Memory persistence gives one
      // anonymous browser-page identity and never reads a previously stored
      // account-linked UUID from PostHog cookies/localStorage.
      persistence: 'memory',
      person_profiles: 'never',
      ip: false,
      save_campaign_params: false,
      save_referrer: false,
      respect_dnt: true,
      before_send: scrubAnalyticsEvent,
    })
  }, [])

  return (
    <PostHogProvider client={posthog}>
      <AuthProvider>
        <Suspense fallback={null}>
          <PostHogPageView />
        </Suspense>
        <LibrarySync />
        {children}
      </AuthProvider>
    </PostHogProvider>
  )
}

/** Capture a $pageview on every App Router client-side navigation. */
function PostHogPageView() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return
    // Privacy: never send the queried variant to analytics. Capture the route
    // only — the query string (gene/cdna/q) is dropped from $current_url.
    // searchParams stays in the deps so a new lookup on the same /report path
    // still counts as a view, but its value is never transmitted.
    posthog.capture('$pageview', { $current_url: window.location.origin + pathname })
  }, [pathname, searchParams])
  return null
}
