import type { Metadata } from 'next'
import { Suspense } from 'react'
import { CheckoutSuccessClient } from '@/components/pricing/CheckoutSuccessClient'

export const metadata: Metadata = {
  title: 'Payment successful — Eamos',
}

export default function CheckoutSuccessPage() {
  return (
    <Suspense fallback={null}>
      <CheckoutSuccessClient />
    </Suspense>
  )
}
