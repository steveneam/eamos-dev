import { Card } from '@/components/ui/Card'

interface LimitationsSectionProps {
  text: string | null | undefined
  number?: number
}

export function LimitationsSection({ text, number }: LimitationsSectionProps) {
  if (!text?.trim()) return null

  return (
    <Card number={number} title="Limitations & disclaimer">
      <p
        style={{
          margin: 0,
          fontStyle: 'italic',
          fontSize: 13,
          lineHeight: 1.65,
          color: 'var(--ink-3)',
        }}
      >
        {text}
      </p>
    </Card>
  )
}
