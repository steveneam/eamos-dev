'use client'
import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import { Suspense, useEffect, useRef } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { AuthProvider, useAuth } from '@/components/auth/AuthProvider'
import { LibrarySync } from '@/components/library/LibrarySync'

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
      capture_pageleave: true,
      person_profiles: 'identified_only',
    })
  }, [])

  return (
    <PostHogProvider client={posthog}>
      <AuthProvider>
        <Suspense fallback={null}>
          <PostHogPageView />
        </Suspense>
        <PostHogIdentify />
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

/** Tie analytics identity to the Supabase user; reset on sign-out. */
function PostHogIdentify() {
  const { user } = useAuth()
  const prevId = useRef<string | null>(null)
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return
    if (user) {
      // Privacy: identify by opaque Supabase UUID only — no email/PII to analytics.
      posthog.identify(user.id)
      prevId.current = user.id
    } else if (prevId.current) {
      // Real sign-out (not the initial anonymous load) → drop the identity.
      posthog.reset()
      prevId.current = null
    }
  }, [user])
  return null
}
