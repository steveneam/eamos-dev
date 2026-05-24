import type { Metadata } from 'next'
import { PricingClient } from '@/components/pricing/PricingClient'

export const metadata: Metadata = {
  title: 'Pricing — Eamos',
  description: 'Eamos plans for researchers, clinicians, and diagnostic labs. AUD, GST inclusive.',
}

export default function PricingPage() {
  return <PricingClient />
}
