// Sentry init for the Next.js server runtime. Loaded by instrumentation.ts.
import * as Sentry from '@sentry/nextjs'
import { baseSentryOptions } from './lib/sentry.shared'

Sentry.init(baseSentryOptions)
