import { type ReactNode } from 'react'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { cn } from '@/lib/utils'

interface TopNavProps {
  children?: ReactNode
  right?: ReactNode
  className?: string
}

export function TopNav({ children, right, className }: TopNavProps) {
  return (
    <div
      className={cn('sticky top-0 z-50', className)}
      style={{
        // Opaque warm-paper — backdrop-filter:blur on a sticky element repaints
        // on every keystroke anywhere on the page (mobile typing lag).
        background: 'var(--nav-bg)',
        borderBottom: '0.5px solid var(--line)',
      }}
    >
      <div
        className="mx-auto flex flex-wrap items-center gap-3 px-4 py-2 sm:flex-nowrap sm:gap-6 sm:px-8"
        style={{ maxWidth: 1180, minHeight: 56 }}
      >
        <a
          href="/"
          aria-label="Eamos home"
          className="flex shrink-0 items-center"
          style={{ textDecoration: 'none' }}
        >
          <EamosLogo size={18} />
        </a>
        {children && <div className="order-3 min-w-full flex-1 sm:order-none sm:min-w-0">{children}</div>}
        <div className="flex shrink-0 items-center gap-2">
          {right ?? (
            <a
              href="/runs"
              className="inline-flex items-center rounded-[10px] px-3.5 py-1.5 text-[12.5px] font-semibold transition-colors"
              style={{
                color: 'var(--ink-2)',
                background: 'var(--bg)',
                border: '0.5px solid var(--line-2)',
              }}
            >
              Patient reports
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
