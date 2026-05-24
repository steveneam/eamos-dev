import type { Metadata } from 'next'
import { Suspense } from 'react'
import { CheckoutClient } from '@/components/pricing/CheckoutClient'

export const metadata: Metadata = {
  title: 'Checkout — Eamos',
  description: 'Review your plan and subscribe. Payments secured by Stripe.',
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={null}>
      <CheckoutClient />
    </Suspense>
  )
}
