import { cn } from '@/lib/utils'

interface HairlineProps {
  className?: string
  vertical?: boolean
}

export function Hairline({ className, vertical = false }: HairlineProps) {
  if (vertical) {
    return (
      <span
        className={cn('block self-stretch', className)}
        style={{ width: '0.5px', background: 'var(--line)' }}
        aria-hidden
      />
    )
  }
  return (
    <hr
      className={cn('border-none', className)}
      style={{ height: '0.5px', background: 'var(--line)' }}
      aria-hidden
    />
  )
}
