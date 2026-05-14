import { Card } from '@/components/ui/Card'

interface VariantDecoderProps {
  decoder: string | null | undefined
  number?: number
}

export function VariantDecoder({ decoder, number }: VariantDecoderProps) {
  if (!decoder?.trim()) return null

  return (
    <Card number={number} title="Variant decoder" meta="plain-language translation">
      <p
        style={{
          fontSize: 14,
          lineHeight: 1.7,
          color: 'var(--ink-2)',
          margin: 0,
        }}
      >
        {decoder}
      </p>
    </Card>
  )
}
