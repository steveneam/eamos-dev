import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Eamos Genomics — Variant Intelligence',
  description:
    'Aggregates ClinVar, VEP, SpliceAI, gnomAD and PubMed for genomic variant interpretation. Research use only.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
