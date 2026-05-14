import { Link, useSearchParams } from 'react-router-dom'
import { cn } from '@/lib/utils'

type Surface = 'report' | 'workbench'

interface ModePillProps {
  current: Surface
  className?: string
}

const ITEMS: Array<{ key: Surface; label: string; path: string }> = [
  { key: 'report',    label: 'Report',    path: '/report' },
  { key: 'workbench', label: 'Workbench', path: '/workbench' },
]

export function ModePill({ current, className }: ModePillProps) {
  const [params] = useSearchParams()
  const query = params.toString()
  const qs = query ? `?${query}` : ''

  return (
    <div
      role="group"
      aria-label="View mode"
      className={cn('inline-flex items-center', className)}
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 100,
        padding: 3,
      }}
    >
      {ITEMS.map((item) => {
        const active = item.key === current
        return (
          <Link
            key={item.key}
            to={`${item.path}${qs}`}
            aria-current={active ? 'page' : undefined}
            className="inline-flex items-center gap-1.5 font-semibold transition-colors"
            style={{
              padding: '6px 12px',
              fontSize: 12,
              borderRadius: 100,
              color: active ? '#ffffff' : 'var(--ink-3)',
              background: active ? 'var(--ink-2)' : 'transparent',
              textDecoration: 'none',
            }}
          >
            {item.label}
          </Link>
        )
      })}
    </div>
  )
}
