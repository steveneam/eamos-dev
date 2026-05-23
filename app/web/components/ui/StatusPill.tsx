import { cn } from '@/lib/utils'

type PillVariant = 'recruit' | 'active' | 'phase' | 'default'

interface StatusPillProps {
  variant?: PillVariant
  children: React.ReactNode
  className?: string
}

const STYLES: Record<PillVariant, React.CSSProperties> = {
  recruit: {
    background: 'var(--teal-tint)',
    color: 'var(--teal-deep)',
    borderColor: '#cbe3d8',
  },
  active: {
    background: 'var(--warn-tint)',
    color: '#633806',
    borderColor: 'var(--warn-bdr)',
  },
  phase: {
    background: 'var(--bg)',
    color: 'var(--ink-3)',
    borderColor: 'var(--line)',
  },
  default: {
    background: 'var(--bg-soft)',
    color: 'var(--ink-3)',
    borderColor: 'var(--line)',
  },
}

const DOT_COLORS: Partial<Record<PillVariant, string>> = {
  recruit: 'var(--teal)',
  active: 'var(--warn)',
}

export function StatusPill({ variant = 'default', children, className }: StatusPillProps) {
  const styles = STYLES[variant]
  const dotColor = DOT_COLORS[variant]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.06em]',
        className,
      )}
      style={{ ...styles, borderWidth: '0.5px' }}
    >
      {dotColor && (
        <span
          className="shrink-0 rounded-full"
          style={{ width: 5, height: 5, background: dotColor }}
        />
      )}
      {children}
    </span>
  )
}
