import type { MetadataRoute } from 'next'

// Sitemap lists public, indexable routes only.
// Excluded (auth-gated or flow pages): /account, /checkout, /checkout/success
// Excluded (legacy, frozen): /runs
// Pricing lives on the landing page (/) — no separate /pricing route exists.

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://eamos.com.au'

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${siteUrl}/report`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${siteUrl}/workbench`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${siteUrl}/terms`,
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${siteUrl}/privacy`,
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ]
}
