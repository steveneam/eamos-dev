import type { Metadata } from 'next'
import { AuthPageClient } from '@/components/auth/AuthPageClient'

export const metadata: Metadata = {
  title: 'Sign in — Eamos',
  description: 'Sign in or create your Eamos account.',
}

export default function AuthPage() {
  return <AuthPageClient />
}
