import { withSentryConfig } from '@sentry/nextjs'

// Backend stays the FastAPI contract authority (see plans/v2-nextjs-migration/
// design.md). The browser calls same-origin `/api/*`; this rewrite proxies to
// the FastAPI dev server on Eamos's private backend lane (`/api → :8532`) and
// sidestepping CORS. Override the backend origin with API_PROXY_TARGET.
const API_TARGET = process.env.API_PROXY_TARGET ?? 'http://localhost:8532'

/** @type {import('next').NextConfig} */
const nextConfig = {
  // PostHog needs trailing-slash paths (e.g. /ingest/flags/) passed through
  // untouched by Next's trailing-slash redirect.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${API_TARGET}/api/:path*` },
      // PostHog reverse proxy (US cloud): events go first-party via /ingest/*
      // so ad/tracking blockers don't drop them. providers.tsx sets
      // posthog api_host = '/ingest'.
      { source: '/ingest/static/:path*', destination: 'https://us-assets.i.posthog.com/static/:path*' },
      { source: '/ingest/:path*', destination: 'https://us.i.posthog.com/:path*' },
    ]
  },
}

export default withSentryConfig(nextConfig, {
  // Source-map upload (readable stack traces) only runs when these are set,
  // e.g. on Vercel/CI; local builds without a token just skip the upload.
  org: process.env.SENTRY_ORG ?? 'eamos',
  project: process.env.SENTRY_PROJECT ?? 'javascript-nextjs',
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !process.env.CI,
})
