import type { Metadata } from 'next'
import { AccountClient } from '@/components/account/AccountClient'

export const metadata: Metadata = {
  title: 'My account — Eamos',
  description: 'Your saved variants and ClinVar evidence submissions.',
}

export default function AccountPage() {
  return <AccountClient />
}
