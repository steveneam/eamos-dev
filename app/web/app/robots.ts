import type { MetadataRoute } from 'next'

// SITE_PUBLIC controls the stealth ↔ public switch.
// This is a plain server-side env var (NOT prefixed NEXT_PUBLIC_) so it is
// never exposed to the browser and cannot be toggled client-side.
// Absent or any value other than 'true' = STEALTH (block all crawlers).
// Set SITE_PUBLIC=true on the Vercel project at launch to go public.
const isPublic = process.env.SITE_PUBLIC === 'true'

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://eamos.com.au'

export default function robots(): MetadataRoute.Robots {
  if (!isPublic) {
    // Stealth: instruct all crawlers to stay out entirely.
    return {
      rules: {
        userAgent: '*',
        disallow: '/',
      },
    }
  }

  // Public: allow crawling and advertise the sitemap.
  return {
    rules: {
      userAgent: '*',
      allow: '/',
    },
    sitemap: `${siteUrl}/sitemap.xml`,
  }
}
