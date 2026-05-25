import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface CardProps {
  number?: number
  title: string
  meta?: ReactNode
  children: ReactNode
  className?: string
}

export function Card({ number, title, meta, children, className }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-[14px] bg-[var(--bg)] border border-[var(--line)] overflow-hidden',
        className,
      )}
      style={{ borderWidth: '0.5px', boxShadow: 'var(--elev-1)' }}
    >
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--line)]" style={{ borderBottomWidth: '0.5px' }}>
        <div className="flex items-center gap-3">
          {number !== undefined && (
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-white"
              style={{ background: 'var(--teal)', fontFamily: 'var(--mono)' }}
            >
              {number}
            </span>
          )}
          <h2
            className="text-[18px] font-medium tracking-[-0.01em]"
            style={{ color: 'var(--ink)', fontFamily: 'var(--display)' }}
          >
            {title}
          </h2>
        </div>
        {meta && (
          <span className="text-[12px]" style={{ color: 'var(--ink-4)' }}>
            {meta}
          </span>
        )}
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  )
}
