// Sentry init for the browser. Env-gated via baseSentryOptions. No Session
// Replay — replay lives in PostHog (app/providers.tsx); avoid duplicate capture.
import * as Sentry from '@sentry/nextjs'
import { baseSentryOptions } from './lib/sentry.shared'

Sentry.init(baseSentryOptions)

// Instrument App Router client-side navigations for tracing.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart
