import { cva, type VariantProps } from 'class-variance-authority'
import type * as React from 'react'
import { cn } from '../../lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]',
  {
    variants: {
      variant: {
        default: 'border-[color:var(--line)] bg-white text-[color:var(--muted-ink)]',
        success: 'border-transparent bg-[color:var(--teal-faint)] text-[color:var(--teal)]',
        danger: 'border-transparent bg-[color:var(--danger-soft)] text-[color:var(--danger)]',
        warning: 'border-transparent bg-[color:var(--report-soft)] text-[color:var(--report)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
