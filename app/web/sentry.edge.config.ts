// Sentry init for the Next.js edge runtime (middleware, edge routes).
import * as Sentry from '@sentry/nextjs'
import { baseSentryOptions } from './lib/sentry.shared'

Sentry.init(baseSentryOptions)
