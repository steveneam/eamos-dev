import type { Metadata } from 'next'
import localFont from 'next/font/local'
import './globals.css'
import { Providers } from './providers'

// Repository-local Google Fonts keep builds independent of the Google Fonts
// CDN. Each font exposes the same CSS variable and weight range as before;
// display:'swap' and metric-adjusted fallbacks keep text visible and stable.
const spectral = localFont({
  src: [
    { path: './fonts/spectral/spectral-latin-400.woff2', weight: '400', style: 'normal' },
    { path: './fonts/spectral/spectral-latin-500.woff2', weight: '500', style: 'normal' },
    { path: './fonts/spectral/spectral-latin-600.woff2', weight: '600', style: 'normal' },
    { path: './fonts/spectral/spectral-latin-700.woff2', weight: '700', style: 'normal' },
  ],
  display: 'swap',
  variable: '--display',
  fallback: ['Georgia', 'Times New Roman', 'serif'],
  adjustFontFallback: 'Times New Roman',
  preload: true,
})
const inter = localFont({
  src: [
    {
      path: './fonts/inter/inter-latin-variable.woff2',
      weight: '400 700',
      style: 'normal',
    },
  ],
  display: 'swap',
  variable: '--body',
  fallback: ['system-ui', 'sans-serif'],
  adjustFontFallback: 'Arial',
  preload: true,
})
// IBM Plex Mono replaces JetBrains Mono (2026-06-03, Steven): JetBrains ships a
// dotted zero that reads as "8" at 11-14px on HGVS/coords. IBM Plex Mono has a
// clear zero and pairs with Inter. Single-token swap; all `var(--mono)` consumers
// inherit it (report + account + Workbench sequence viewer).
const ibmPlexMono = localFont({
  src: [
    {
      path: './fonts/ibm-plex-mono/ibm-plex-mono-latin-400.woff2',
      weight: '400',
      style: 'normal',
    },
    {
      path: './fonts/ibm-plex-mono/ibm-plex-mono-latin-500.woff2',
      weight: '500',
      style: 'normal',
    },
  ],
  display: 'swap',
  variable: '--mono',
  fallback: ['ui-monospace', 'monospace'],
  adjustFontFallback: 'Arial',
  preload: true,
})

// metadataBase: prefer the explicit site URL env var; fall back to the
// production domain. NEXT_PUBLIC_SITE_URL is safe to expose because it is
// just a URL, not a secret.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
  ? new URL(process.env.NEXT_PUBLIC_SITE_URL)
  : new URL('https://eamos.com.au')

const defaultTitle = 'Eamos: Genetic Variant Search Engine'
const defaultDescription =
  'Search a genetic variant across clinical evidence, 11 in-silico predictors, and version-pinned ACMG/AMP criteria in one traceable research report.'
const socialImageAlt =
  'Eamos free genomic variant evidence search: trace one variant through 11 predictor engines, Workbench, and Batch.'

export const metadata: Metadata = {
  metadataBase: siteUrl,
  title: {
    default: defaultTitle,
    template: '%s · Eamos',
  },
  description: defaultDescription,
  openGraph: {
    title: defaultTitle,
    description: defaultDescription,
    url: siteUrl.toString(),
    siteName: 'Eamos',
    images: [{ url: '/og-image.png', width: 1200, height: 630, alt: socialImageAlt }],
    type: 'website',
    locale: 'en_AU',
  },
  twitter: {
    card: 'summary_large_image',
    title: defaultTitle,
    description: defaultDescription,
    images: [{ url: '/og-image.png', alt: socialImageAlt }],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${spectral.variable} ${inter.variable} ${ibmPlexMono.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
