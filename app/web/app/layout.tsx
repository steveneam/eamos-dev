import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'

// metadataBase: prefer the explicit site URL env var; fall back to the
// production domain. NEXT_PUBLIC_SITE_URL is safe to expose because it is
// just a URL, not a secret.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
  ? new URL(process.env.NEXT_PUBLIC_SITE_URL)
  : new URL('https://eamos.com.au')

const defaultTitle = 'Eamos — Genomic Intelligence Platform'
const defaultDescription =
  'Aggregates ClinVar, VEP, SpliceAI, gnomAD and PubMed for genomic variant evidence. Research use only.'

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
    // NOTE: og-image.png (1200×630) must be placed at
    // E:\eamos\app\web\public\og-image.png — the human supplies this file.
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
    type: 'website',
    locale: 'en_AU',
  },
  twitter: {
    card: 'summary_large_image',
    title: defaultTitle,
    description: defaultDescription,
    images: ['/og-image.png'],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
